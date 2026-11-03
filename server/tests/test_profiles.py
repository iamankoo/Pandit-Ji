"""Birth-profile CRUD, validation, ownership, concurrency, idempotency and deletion."""

from __future__ import annotations

from typing import Any

import pytest
from conftest import PROFILE, auth, create_profile
from fastapi.testclient import TestClient

BASE = "/api/v1/birth-profiles"


def _post(client: TestClient, body: dict[str, Any], subject: str = "u1", **headers: str) -> Any:
    return client.post(BASE, json=body, headers={**auth(subject), **headers})


def test_create_get_list_update_delete(client: TestClient) -> None:
    created = create_profile(client)
    assert created["version"] == 1 and created["birth_utc"].startswith("1990-06-15T04:30:00")
    pid = created["id"]
    assert client.get(f"{BASE}/{pid}", headers=auth()).json()["label"] == "Me"
    listing = client.get(BASE, headers=auth()).json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == pid
    body = {**PROFILE, "label": "Me (edited)", "expected_version": 1}
    updated = client.put(f"{BASE}/{pid}", json=body, headers=auth())
    assert updated.status_code == 200 and updated.json()["version"] == 2
    assert client.delete(f"{BASE}/{pid}", headers=auth()).status_code == 204
    assert client.get(f"{BASE}/{pid}", headers=auth()).status_code == 404


def test_original_local_input_and_canonical_utc_are_both_kept(client: TestClient) -> None:
    created = create_profile(client)
    assert created["birth_time"] == "10:00:00" and created["timezone"] == "Asia/Kolkata"
    assert created["birth_utc"].startswith("1990-06-15T04:30:00")


def test_a_missing_birth_time_is_never_inferred(client: TestClient) -> None:
    body = {k: v for k, v in PROFILE.items() if k not in ("birth_time", "time_precision")}
    created = _post(client, body)
    assert created.status_code == 201
    assert created.json()["birth_time"] is None and created.json()["birth_utc"] is None
    assert created.json()["time_precision"] == "unknown"
    # a stated time cannot be labelled unknown, an absent time cannot claim precision
    assert _post(client, {**PROFILE, "label": "x", "time_precision": "unknown"}).status_code == 422
    no_time = {k: v for k, v in PROFILE.items() if k != "birth_time"}
    assert _post(client, {**no_time, "label": "y", "time_precision": "exact"}).status_code == 422


@pytest.mark.parametrize(
    "override",
    [
        {"timezone": "Mars/Olympus"},
        {"timezone": "UTC+5"},
        {"timezone": "../../etc/passwd"},
        {"latitude": 91},
        {"longitude": -181},
        {"birth_date": "2999-01-01"},
        {"birth_date": "1700-01-01"},
        {"label": "   "},
        {"altitude_m": 99999},
        {"unknown_field": 1},
    ],
)
def test_invalid_profiles_are_422(client: TestClient, override: dict[str, Any]) -> None:
    response = _post(client, {**PROFILE, **override})
    assert response.status_code == 422
    assert response.json()["error"]["code"] in {"validation_error", "invalid_timezone"}


def test_dst_ambiguous_and_nonexistent_local_times_are_refused_by_default(
    client: TestClient,
) -> None:
    # US fall-back: 2021-11-07 01:30 happens twice; spring-forward: 2021-03-14 02:30 does not exist
    base = {**PROFILE, "timezone": "America/New_York", "label": "dst"}
    ambiguous = _post(client, {**base, "birth_date": "2021-11-07", "birth_time": "01:30:00"})
    assert (
        ambiguous.status_code == 422 and ambiguous.json()["error"]["code"] == "ambiguous_local_time"
    )
    gap = _post(
        client, {**base, "label": "gap", "birth_date": "2021-03-14", "birth_time": "02:30:00"}
    )
    assert gap.status_code == 422 and gap.json()["error"]["code"] == "nonexistent_local_time"
    earlier = _post(
        client,
        {
            **base,
            "label": "e",
            "birth_date": "2021-11-07",
            "birth_time": "01:30:00",
            "disambiguation": "earlier",
        },
    )
    later = _post(
        client,
        {
            **base,
            "label": "l",
            "birth_date": "2021-11-07",
            "birth_time": "01:30:00",
            "disambiguation": "later",
        },
    )
    assert earlier.status_code == later.status_code == 201
    assert earlier.json()["birth_utc"] != later.json()["birth_utc"]


def test_a_user_cannot_read_update_or_delete_another_users_profile(client: TestClient) -> None:
    pid = create_profile(client, "owner")["id"]
    other = auth("intruder")
    assert client.get(f"{BASE}/{pid}", headers=other).status_code == 404
    assert (
        client.put(
            f"{BASE}/{pid}", json={**PROFILE, "expected_version": 1}, headers=other
        ).status_code
        == 404
    )
    assert client.delete(f"{BASE}/{pid}", headers=other).status_code == 404
    assert client.get(f"{BASE}/{pid}/kundli", headers=other).status_code == 404
    assert client.get(f"{BASE}/{pid}", headers=auth("owner")).status_code == 200  # untouched


def test_optimistic_concurrency_detects_a_stale_update(client: TestClient) -> None:
    pid = create_profile(client)["id"]
    first = client.put(
        f"{BASE}/{pid}", json={**PROFILE, "label": "A", "expected_version": 1}, headers=auth()
    )
    stale = client.put(
        f"{BASE}/{pid}", json={**PROFILE, "label": "B", "expected_version": 1}, headers=auth()
    )
    assert first.status_code == 200
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "version_conflict"
    assert client.get(f"{BASE}/{pid}", headers=auth()).json()["label"] == "A"


def test_label_must_be_unique_per_user_but_not_across_users(client: TestClient) -> None:
    create_profile(client, "a")
    assert _post(client, PROFILE, "a").status_code == 409
    assert _post(client, PROFILE, "b").status_code == 201
    # the failed insert did not poison the transaction: the user can still list
    assert client.get(BASE, headers=auth("a")).json()["total"] == 1


def test_profile_limit(client: TestClient) -> None:
    from pandit_server.api.v1.profiles import MAX_PROFILES_PER_USER

    for i in range(MAX_PROFILES_PER_USER):
        assert _post(client, {**PROFILE, "label": f"p{i}"}, "many").status_code == 201
    over = _post(client, {**PROFILE, "label": "one-too-many"}, "many")
    assert over.status_code == 409 and over.json()["error"]["code"] == "profile_limit_reached"


def test_pagination(client: TestClient) -> None:
    for i in range(5):
        _post(client, {**PROFILE, "label": f"p{i}"}, "pg")
    page = client.get(BASE, params={"limit": 2, "offset": 2}, headers=auth("pg")).json()
    assert page["total"] == 5 and len(page["items"]) == 2 and page["offset"] == 2
    assert client.get(BASE, params={"limit": 1000}, headers=auth("pg")).status_code == 422


def test_idempotent_create_replays_and_rejects_a_changed_body(client: TestClient) -> None:
    key = {"Idempotency-Key": "key-0001-abcdef"}
    first = _post(client, PROFILE, "idem", **key)
    replay = _post(client, PROFILE, "idem", **key)
    assert first.status_code == replay.status_code == 201
    assert replay.headers["Idempotent-Replayed"] == "true" and replay.json() == first.json()
    assert client.get(BASE, headers=auth("idem")).json()["total"] == 1
    changed = _post(client, {**PROFILE, "label": "different"}, "idem", **key)
    assert changed.status_code == 422 and changed.json()["error"]["code"] == "idempotency_key_reuse"
    assert _post(client, PROFILE, "idem", **{"Idempotency-Key": "short"}).status_code == 422


def test_idempotency_keys_are_scoped_to_the_user(client: TestClient) -> None:
    key = {"Idempotency-Key": "shared-key-12345"}
    a = _post(client, PROFILE, "ua", **key)
    b = _post(client, PROFILE, "ub", **key)
    assert a.json()["id"] != b.json()["id"]


def test_deleting_a_profile_removes_its_stored_charts(client: TestClient, container) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import func, select

    from pandit_server.db.models import StoredKundli

    pid = create_profile(client)["id"]
    assert client.get(f"{BASE}/{pid}/kundli", headers=auth()).status_code == 200
    with container.db.session() as s:
        assert s.scalar(select(func.count()).select_from(StoredKundli)) == 1
    client.delete(f"{BASE}/{pid}", headers=auth())
    with container.db.session() as s:
        assert s.scalar(select(func.count()).select_from(StoredKundli)) == 0


def test_oversized_bodies_are_refused(client: TestClient) -> None:
    response = client.post(
        BASE, content=b"x" * 400000, headers={**auth(), "Content-Type": "application/json"}
    )
    assert response.status_code == 413 and response.json()["error"]["code"] == "payload_too_large"


def test_every_owned_table_is_listed_for_erasure() -> None:
    from pandit_server.db.erase import USER_OWNED
    from pandit_server.db.models import Base

    with_user_id = {
        mapper.class_
        for mapper in Base.registry.mappers
        if "user_id" in mapper.columns and mapper.class_.__name__ != "AuditEvent"
    }
    assert with_user_id == set(USER_OWNED)
