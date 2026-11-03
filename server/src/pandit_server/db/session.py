"""Database access: one engine per process, one session per request (transaction per request).

PostgreSQL is the production database (ADR-004). SQLite (schemas translated away) exists only so
the fast unit tests need no server; PostgreSQL behaviour is covered by the PostgreSQL-gated tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from pandit_server.db.models import SCHEMAS, Base


class Database:
    def __init__(self, url: str) -> None:
        self.url = url
        self.is_sqlite = url.startswith("sqlite")
        if self.is_sqlite:
            self.engine: Engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                execution_options={"schema_translate_map": {s: None for s in SCHEMAS}},
            )

            @event.listens_for(self.engine, "connect")
            def _fk(dbapi_connection, _record):  # type: ignore[no-untyped-def]
                dbapi_connection.execute("PRAGMA foreign_keys=ON")
        else:
            self.engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
        self._factory = sessionmaker(self.engine, expire_on_commit=False)

    def create_all(self) -> None:
        """Create the tables (tests only; production uses the Alembic migrations)."""
        Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """A transaction: commit on success, roll back on any error."""
        session = self._factory()
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    def ping(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            return True
        except Exception:  # noqa: BLE001 - readiness must never raise
            return False

    def dispose(self) -> None:
        self.engine.dispose()
