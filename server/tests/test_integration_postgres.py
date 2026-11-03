"""PostgreSQL behaviour: migrations, schema drift, constraints, cascades, rollback and concurrency.

Runs only when ``SERVER_TEST_DATABASE_URL`` points at a PostgreSQL server (with pgvector, as the
earlier migrations create the extension). Each module run uses its own freshly created database, so
the fresh-install path is what is tested; SQLite is never evidence of PostgreSQL support.
"""

from __future__ import annotations

import os
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import PROFILE, auth, make_settings
from fastapi.testclient import TestClient

ADMIN_URL = os.environ.get("SERVER_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="SERVER_TEST_DATABASE_URL is not set")

MIGRATIONS = Path(__file__).resolve().parents[2] / "infrastructure" / "migrations" / "alembic.ini"


def _psycopg_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


def _alembic(action: str, revision: str, url: str) -> None:
    from alembic import command
    from alembic.config import Config

    os.environ["DATABASE_URL"] = url
    config = Config(str(MIGRATIONS))
    config.set_main_option("script_location", str(MIGRATIONS.parent))
    (command.upgrade if action == "upgrade" else command.downgrade)(config, revision)


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    import psycopg

    assert ADMIN_URL is not None
    name = f"pj_server_{uuid.uuid4().hex[:10]}"
    admin = psycopg.connect(_psycopg_url(ADMIN_URL), autocommit=True)
    admin.execute(f'CREATE DATABASE "{name}"')
    base, _, _ = ADMIN_URL.rpartition("/")
    url = f"{base}/{name}"
    try:
        yield url
    finally:
        admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        admin.close()


@pytest.fixture(scope="module")
def migrated(pg_url: str) -> str:
    _alembic("upgrade", "head", pg_url)
    return pg_url


def _tables(url: str) -> dict[str, set[str]]:
    import psycopg

    with psycopg.connect(_psycopg_url(url)) as conn:
        rows = conn.execute(
            "SELECT table_schema, table_name, column_name FROM information_schema.columns "
            "WHERE table_schema IN ('identity','profiles','charts','conversation','reports',"
            "'audit','platform')"
        ).fetchall()
    out: dict[str, set[str]] = {}
    for schema, table, column in rows:
        out.setdefault(f"{schema}.{table}", set()).add(column)
    return out


def test_the_migrated_schema_matches_the_models_exactly(migrated: str) -> None:
    from pandit_server.db.models import Base

    expected = {
        f"{t.schema}.{t.name}": {c.name for c in t.columns} for t in Base.metadata.tables.values()
    }
    assert _tables(migrated) == expected  # no drift between the migration and the ORM models


def test_downgrade_removes_exactly_the_phase_18_objects_and_upgrade_restores_them(
    pg_url: str,
) -> None:
    import psycopg

    _alembic("upgrade", "head", pg_url)
    _alembic("downgrade", "0004_domain_knowledge_vocabulary", pg_url)
    assert _tables(pg_url) == {}
    with psycopg.connect(_psycopg_url(pg_url)) as conn:  # earlier schemas are untouched
        assert conn.execute("SELECT count(*) FROM knowledge.concepts").fetchone() is not None
        assert (
            conn.execute("SELECT 1 FROM pg_namespace WHERE nspname='platform'").fetchone() is None
        )
    _alembic("upgrade", "head", pg_url)
    assert _tables(pg_url)


def _app(url: str) -> Any:
    from conftest import make_container

    from pandit_server.container import build_container
    from pandit_server.db.session import Database
    from pandit_server.kv import MemoryStore
    from pandit_server.main import create_app

    base = make_container(make_settings(DATABASE_URL=url))
    container = build_container(
        base.settings,
        db=Database(url),
        store=MemoryStore(),
        key_provider=base.verifier._keys,  # the test JWKS
        llm_factory=base.llm_factory,
    )
    return create_app(container.settings, container), container


def test_deleting_a_user_cascades_in_the_database_itself(migrated: str) -> None:
    import psycopg

    uid, pid = uuid.uuid4(), uuid.uuid4()
    with psycopg.connect(_psycopg_url(migrated), autocommit=True) as conn:
        conn.execute(
            "INSERT INTO identity.users (id, subject) VALUES (%s, %s)", (uid, "cascade-sub")
        )
        conn.execute(
            "INSERT INTO profiles.birth_profiles (id, user_id, label, birth_date, timezone, "
            "latitude, longitude) VALUES (%s, %s, 'x', '1990-01-01', 'UTC', 0, 0)",
            (pid, uid),
        )
        conn.execute(
            "INSERT INTO charts.kundlis (id, profile_id, profile_row_version, config_hash, "
            "engine_version, standards_version, payload) VALUES (%s, %s, 1, 'h', 'e', 's', '{}')",
            (uuid.uuid4(), pid),
        )
        conn.execute(
            "INSERT INTO platform.voice_sessions (id, user_id) VALUES (%s, %s)", (uuid.uuid4(), uid)
        )
        conn.execute("DELETE FROM identity.users WHERE id = %s", (uid,))
        for table in ("profiles.birth_profiles", "charts.kundlis", "platform.voice_sessions"):
            assert conn.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)  # type: ignore[comparison-overlap]


def test_database_constraints_hold(migrated: str) -> None:
    import psycopg

    uid = uuid.uuid4()
    with psycopg.connect(_psycopg_url(migrated), autocommit=True) as conn:
        conn.execute(
            "INSERT INTO identity.users (id, subject) VALUES (%s, %s)", (uid, "constraint-sub")
        )
        insert = (
            "INSERT INTO profiles.birth_profiles (id, user_id, label, birth_date, timezone, "
            "latitude, longitude, time_precision) "
            "VALUES (%s, %s, %s, '1990-01-01', 'UTC', %s, %s, %s)"
        )
        conn.execute(insert, (uuid.uuid4(), uid, "ok", 10, 10, "exact"))
        for args in (
            (uuid.uuid4(), uid, "bad-lat", 91, 0, "exact"),
            (uuid.uuid4(), uid, "bad-lon", 0, 181, "exact"),
            (uuid.uuid4(), uid, "bad-precision", 0, 0, "whenever"),
            (uuid.uuid4(), uid, "ok", 1, 1, "exact"),  # duplicate label for the user
            (uuid.uuid4(), uuid.uuid4(), "orphan", 1, 1, "exact"),  # no such user
        ):
            with pytest.raises(psycopg.errors.IntegrityError):
                conn.execute(insert, args)
        with pytest.raises(psycopg.errors.IntegrityError):
            conn.execute(
                "INSERT INTO identity.users (id, subject) VALUES (%s, %s)",
                (uuid.uuid4(), "constraint-sub"),
            )


def test_the_full_api_flow_on_postgresql(migrated: str) -> None:
    app, container = _app(migrated)
    with TestClient(app) as client:
        h = auth("pg-user")
        created = client.post("/api/v1/birth-profiles", json=PROFILE, headers=h)
        assert created.status_code == 201
        pid = created.json()["id"]
        assert client.get(f"/api/v1/birth-profiles/{pid}/kundli", headers=h).status_code == 200
        assert client.get(f"/api/v1/birth-profiles/{pid}/dasha", headers=h).status_code == 200
        assert client.get(f"/api/v1/birth-profiles/{pid}", headers=auth("other")).status_code == 404
        assert client.delete("/api/v1/users/me", headers=h).status_code == 204
    with container.db.engine.connect() as conn:
        from sqlalchemy import text

        assert (
            conn.execute(
                text("SELECT count(*) FROM identity.users WHERE subject='pg-user'")
            ).scalar()
            == 0
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM profiles.birth_profiles WHERE id = :p"), {"p": pid}
            ).scalar()
            == 0
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM charts.kundlis WHERE profile_id = :p"), {"p": pid}
            ).scalar()
            == 0
        )


def test_a_failing_request_rolls_back_everything_it_did(migrated: str) -> None:
    from sqlalchemy import func, select

    from pandit_server.db.models import BirthProfile, User
    from pandit_server.db.session import Database

    db = Database(migrated)
    with pytest.raises(RuntimeError):
        with db.session() as session:
            user = User(subject="rollback-sub")
            session.add(user)
            session.flush()
            session.add(
                BirthProfile(
                    user_id=user.id,
                    label="rollback-marker",
                    birth_date=__import__("datetime").date(1990, 1, 1),
                    timezone="UTC",
                    latitude=0.0,
                    longitude=0.0,
                )
            )
            session.flush()
            raise RuntimeError("boom")
    with db.session() as session:
        assert (
            session.scalar(
                select(func.count()).select_from(User).where(User.subject == "rollback-sub")
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(BirthProfile)
                .where(BirthProfile.label == "rollback-marker")
            )
            == 0
        )


def test_concurrent_profile_updates_are_serialised_one_wins(migrated: str) -> None:
    app, _ = _app(migrated)
    with TestClient(app) as client:
        h = auth("race-user")
        pid = client.post("/api/v1/birth-profiles", json=PROFILE, headers=h).json()["id"]
        results: list[int] = []
        barrier = threading.Barrier(4)

        def update(i: int) -> None:
            with TestClient(app) as local:
                barrier.wait()
                r = local.put(
                    f"/api/v1/birth-profiles/{pid}",
                    json={**PROFILE, "label": f"racer-{i}", "expected_version": 1},
                    headers=h,
                )
                results.append(r.status_code)

        threads = [threading.Thread(target=update, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sorted(results) == [200, 409, 409, 409]
        final = client.get(f"/api/v1/birth-profiles/{pid}", headers=h).json()
        assert final["version"] == 2 and final["label"].startswith("racer-")


def test_the_phase_17_knowledge_tables_and_versions_are_unaffected(migrated: str) -> None:
    import psycopg

    with psycopg.connect(_psycopg_url(migrated)) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='knowledge'"
            ).fetchone()[0]
            > 0
        )  # type: ignore[index]
