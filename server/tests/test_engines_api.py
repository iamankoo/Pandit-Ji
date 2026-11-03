"""Kundli, Dasha, raw Transit, Panchang, Numerology and Compatibility over the real engines."""

from __future__ import annotations

import datetime as dt
from typing import Any

from conftest import PROFILE, auth, create_profile
from fastapi.testclient import TestClient

BASE = "/api/v1/birth-profiles"


def _no_time(client: TestClient, subject: str = "nt") -> str:
    body = {k: v for k, v in PROFILE.items() if k not in ("birth_time", "time_precision")}
    r = client.post(BASE, json=body, headers=auth(subject))
    return str(r.json()["id"])


# ---- Kundli -------------------------------------------------------------------------------------


def test_kundli_is_the_engines_own_deterministic_result(client: TestClient) -> None:
    from pandit_astro_engine import KundliCalculationService
    from pandit_astro_engine.models import (
        AstronomicalCalculationRequest,
        LocalDateTimeInput,
        Location,
    )

    pid = create_profile(client)["id"]
    body = client.get(f"{BASE}/{pid}/kundli", headers=auth()).json()
    direct = (
        KundliCalculationService()
        .calculate(
            AstronomicalCalculationRequest(
                local_datetime=LocalDateTimeInput(
                    year=1990, month=6, day=15, hour=10, minute=0, timezone="Asia/Kolkata"
                ),
                location=Location(latitude=28.6139, longitude=77.2090),
            )
        )
        .model_dump(mode="json")
    )
    assert body["kundli"] == direct
    assert body["kundli"]["metadata"]["varga_scheme"] and body["versions"]["astro_engine"]
    assert body["time_precision"] == "exact" and body["cached"] is False


def test_kundli_is_cached_and_invalidated_by_a_profile_change(client: TestClient) -> None:
    pid = create_profile(client)["id"]
    first = client.get(f"{BASE}/{pid}/kundli", headers=auth()).json()
    second = client.get(f"{BASE}/{pid}/kundli", headers=auth()).json()
    assert (first["cached"], second["cached"]) == (False, True) and first["kundli"] == second[
        "kundli"
    ]
    client.put(
        f"{BASE}/{pid}",
        json={**PROFILE, "birth_time": "11:00:00", "expected_version": 1},
        headers=auth(),
    )
    third = client.get(f"{BASE}/{pid}/kundli", headers=auth()).json()
    assert third["cached"] is False and third["profile_version"] == 2
    assert third["kundli"]["lagna_longitude"] != first["kundli"]["lagna_longitude"]


def test_the_cache_is_private_per_user(client: TestClient, container) -> None:  # type: ignore[no-untyped-def]
    a = create_profile(client, "ua")
    b = create_profile(client, "ub")
    client.get(f"{BASE}/{a['id']}/kundli", headers=auth("ua"))
    other = client.get(f"{BASE}/{b['id']}/kundli", headers=auth("ub")).json()
    assert other["cached"] is False  # an identical chart for another user is not a cache hit
    assert container.metrics.value("cache_hits_total", namespace="kundli") == 0


def test_kundli_without_a_birth_time_is_a_typed_422(client: TestClient) -> None:
    pid = _no_time(client)
    response = client.get(f"{BASE}/{pid}/kundli", headers=auth("nt"))
    assert response.status_code == 422 and response.json()["error"]["code"] == "birth_time_required"


# ---- Dasha --------------------------------------------------------------------------------------


def test_dasha_levels_boundaries_and_current_periods(client: TestClient) -> None:
    pid = create_profile(client)["id"]
    body = client.get(
        f"{BASE}/{pid}/dasha", params={"at_utc": "2026-01-01T00:00:00+00:00"}, headers=auth()
    ).json()
    facts = body["facts"]
    assert facts["status"] == "success" and facts["time_base"] == "utc"
    assert (
        facts["profile_ids"]["balance_profile_id"]
        and facts["profile_ids"]["year_length_profile_id"]
    )
    levels = {p["level"] for p in facts["periods"]}
    assert len(levels) == 3
    assert set(body["current"]) == levels  # one period of each level contains the instant
    for period in body["current"].values():
        assert period["start_utc"] <= "2026-01-01T00:00:00+00:00" < period["end_utc"]
    # nested periods stay inside their parent
    by_id = {p["period_id"]: p for p in facts["periods"]}
    for p in facts["periods"]:
        if p["parent_id"]:
            parent = by_id[p["parent_id"]]
            assert parent["start_utc"] <= p["start_utc"] and p["end_utc"] <= parent["end_utc"]


def test_dasha_depth_and_boundary_semantics(client: TestClient) -> None:
    pid = create_profile(client)["id"]
    one = client.get(f"{BASE}/{pid}/dasha", params={"depth": 1}, headers=auth()).json()
    assert {p["level"] for p in one["facts"]["periods"]} == {one["facts"]["periods"][0]["level"]}
    mahas = one["facts"]["periods"]
    boundary = mahas[1]["start_utc"]  # start inclusive, end exclusive
    at = client.get(
        f"{BASE}/{pid}/dasha", params={"depth": 1, "at_utc": boundary}, headers=auth()
    ).json()
    assert list(at["current"].values())[0]["period_id"] == mahas[1]["period_id"]
    assert client.get(f"{BASE}/{pid}/dasha", params={"depth": 4}, headers=auth()).status_code == 422


def test_dasha_transitions_in_a_range(client: TestClient) -> None:
    pid = create_profile(client)["id"]
    rows = client.get(
        f"{BASE}/{pid}/dasha/transitions",
        params={
            "start_utc": "2020-01-01T00:00:00+00:00",
            "end_utc": "2030-01-01T00:00:00+00:00",
            "depth": 1,
        },
        headers=auth(),
    ).json()["transitions"]
    assert all("2020-01-01" <= r["start_utc"] < "2030-01-01" for r in rows)
    assert rows == sorted(rows, key=lambda r: (r["start_utc"], r["level"]))
    bad = client.get(
        f"{BASE}/{pid}/dasha/transitions",
        params={"start_utc": "2030-01-01T00:00:00+00:00", "end_utc": "2020-01-01T00:00:00+00:00"},
        headers=auth(),
    )
    assert bad.status_code == 422


def test_dasha_without_birth_time_is_the_engines_typed_not_evaluable(client: TestClient) -> None:
    pid = _no_time(client)
    body = client.get(f"{BASE}/{pid}/dasha", headers=auth("nt")).json()
    assert body["status"] == "not_evaluable" and body["reason_code"] == "birth_time_unknown"


def test_an_approximate_time_without_an_interval_is_not_evaluable_never_guessed(
    client: TestClient,
) -> None:
    pid = create_profile(client, label="approx", time_precision="approximate")["id"]
    body = client.get(f"{BASE}/{pid}/dasha", headers=auth()).json()
    assert body["facts"]["status"] == "not_evaluable"
    assert body["facts"]["reason_code"] == "uncertainty_interval_missing"
    assert body["facts"]["periods"] == []


def test_dasha_utc_is_independent_of_the_birth_timezone(client: TestClient) -> None:
    a = create_profile(client, "tz1", label="ist")  # 10:00 IST = 04:30 UTC
    b = create_profile(client, "tz2", label="utc", timezone="UTC", birth_time="04:30:00")
    da = client.get(f"{BASE}/{a['id']}/dasha", headers=auth("tz1")).json()["facts"]["periods"][0]
    db_ = client.get(f"{BASE}/{b['id']}/dasha", headers=auth("tz2")).json()["facts"]["periods"][0]
    assert da["start_utc"] == db_["start_utc"] and da["lord"] == db_["lord"]


# ---- Transit (raw facts only) -------------------------------------------------------------------


def test_transit_snapshot_is_raw_facts_without_any_interpretation(client: TestClient) -> None:
    pid = create_profile(client)["id"]
    r = client.post(
        f"{BASE}/{pid}/transits", json={"at_utc": "2026-06-01T00:00:00+00:00"}, headers=auth()
    )
    assert r.status_code == 200
    body = r.json()
    assert body["facts"]["status"] == "success"
    assert body["interpretation"]["provided"] is False
    assert "RESEARCH_PENDING" in body["interpretation"]["reason"]
    states = body["facts"]["snapshot"]["states"]
    assert {s["body"] for s in states} >= {"sun", "moon", "jupiter", "saturn"}
    assert all({"sign", "retrograde"} <= set(s) for s in states)


def test_transit_window_and_validation(client: TestClient) -> None:
    pid = create_profile(client)["id"]
    ok = client.post(
        f"{BASE}/{pid}/transits",
        json={
            "window_start_utc": "2026-01-01T00:00:00+00:00",
            "window_end_utc": "2026-03-01T00:00:00+00:00",
        },
        headers=auth(),
    )
    assert ok.status_code == 200 and ok.json()["facts"]["window"] is not None
    for bad in (
        {"window_start_utc": "2026-01-01T00:00:00+00:00"},
        {
            "window_start_utc": "2026-03-01T00:00:00+00:00",
            "window_end_utc": "2026-01-01T00:00:00+00:00",
        },
        {"at_utc": "2026-01-01T00:00:00"},
        {
            "window_start_utc": "1990-01-01T00:00:00+00:00",
            "window_end_utc": "2020-01-01T00:00:00+00:00",
        },
    ):
        assert client.post(f"{BASE}/{pid}/transits", json=bad, headers=auth()).status_code == 422


def test_raw_transit_availability_does_not_activate_the_withheld_domain_rules(
    client: TestClient,
) -> None:
    """The six Phaladeepika XVI records stay non-evaluating whatever transit evidence exists."""
    from pandit_server.compose import chat as pipeline

    pid = create_profile(client)["id"]
    assert client.post(f"{BASE}/{pid}/transits", json={}, headers=auth()).status_code == 200
    kundli = client.get(f"{BASE}/{pid}/kundli", headers=auth()).json()["kundli"]
    for domain in ("CAREER", "MARRIAGE", "WEALTH", "EDUCATION", "INCOME", "SIBLINGS"):
        evidence = pipeline.build_evidence(
            kundli_json=kundli,
            dasha_json=None,
            message="x",
            adult_confirmed=True,
            analysis_id="t",
            forced_domain=__import__("pandit_contracts.domain", fromlist=["LifeDomain"]).LifeDomain[
                domain
            ],
        )
        records = [r for r in evidence.domain_result.rules if "PXVI31" in r.rule_id]  # type: ignore[union-attr]
        assert len(records) == 1
        assert (
            records[0].status.value == "NOT_EVALUABLE"
            and records[0].reason.value == "RESEARCH_PENDING"
        )  # type: ignore[union-attr]
        assert records[0].interpretation is None


# ---- Panchang, Numerology, Compatibility --------------------------------------------------------


def test_panchang_is_public_cached_and_validated(client: TestClient) -> None:
    body = {
        "date": "2026-06-01",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "timezone": "Asia/Kolkata",
    }
    first = client.post("/api/v1/panchang", json=body)
    second = client.post("/api/v1/panchang", json=body)
    assert (
        first.status_code == 200
        and first.json()["cached"] is False
        and second.json()["cached"] is True
    )
    assert first.json()["panchang"]["tithis"] and first.json()["panchang"]["profile_id"]
    assert (
        client.post("/api/v1/panchang", json={**body, "timezone": "Nope/Zone"}).status_code == 422
    )
    assert client.post("/api/v1/panchang", json={**body, "latitude": 200}).status_code == 422


def test_numerology_profiles_and_validation(client: TestClient) -> None:
    body = {"date_of_birth": "1990-06-15", "latin_name": "Asha Rao"}
    r = client.post("/api/v1/numerology", json=body, headers=auth())
    assert r.status_code == 200 and r.json()["numerology"]["profile_id"]
    pyth = client.post(
        "/api/v1/numerology",
        json={
            **body,
            "profile": "NUMEROLOGY_PYTHAGOREAN_BALLIETT_1908_V1",
            "master_number_policy": "keep_11_22",
        },
        headers=auth(),
    )
    assert pyth.status_code in (200, 422)
    assert (
        client.post(
            "/api/v1/numerology", json={**body, "profile": "MADE_UP"}, headers=auth()
        ).status_code
        == 422
    )
    assert client.post("/api/v1/numerology", json={}, headers=auth()).status_code == 422
    assert client.post("/api/v1/numerology", json=body).status_code == 401


def test_compatibility_uses_only_supported_profiles_and_own_profiles(client: TestClient) -> None:
    a = create_profile(client, "cm", label="a")["id"]
    b = create_profile(client, "cm", label="b", birth_date="1992-03-02", birth_time="14:20:00")[
        "id"
    ]
    body = {
        "profile_a_id": a,
        "profile_b_id": b,
        "profile": "ASHTAKOOT_MUHURTA_CHINTAMANI_VIVAHA_21_37_V1",
        "participant_consent_attested": True,
    }
    r = client.post("/api/v1/compatibility", json=body, headers=auth("cm"))
    assert r.status_code == 200, r.text
    assert r.json()["compatibility"]["profile_id"] == body["profile"]
    assert (
        client.post(
            "/api/v1/compatibility", json={**body, "profile": "MADE_UP"}, headers=auth("cm")
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/compatibility",
            json={**body, "participant_consent_attested": False},
            headers=auth("cm"),
        ).status_code
        == 422
    )
    # someone else's profile is a 404, not a match
    assert (
        client.post("/api/v1/compatibility", json=body, headers=auth("stranger")).status_code == 404
    )


def test_dst_and_versions_are_recorded_with_the_result(client: TestClient) -> None:
    pid = create_profile(client)["id"]
    body: dict[str, Any] = client.get(f"{BASE}/{pid}/kundli", headers=auth()).json()
    meta = body["kundli"]["metadata"]
    assert meta["engine_version"] and meta["standards_version"] and meta["house_system"]
    assert dt.datetime.fromisoformat(
        body["kundli"]["astronomical"]["metadata"]["time_resolution"]["utc_datetime"]
    ).tzinfo
