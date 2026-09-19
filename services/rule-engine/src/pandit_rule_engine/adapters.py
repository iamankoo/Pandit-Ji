"""Adapter from a Phase 5 Kundli to the rule engine's normalized facts.

The adapter reads the JSON-compatible form of a Phase 5 `Kundli`
(`Kundli.model_dump(mode="json")`) -- it does not import `astro-engine`, so
the two services stay decoupled. It maps fields one-to-one and performs no
astronomical or astrological calculation. A missing or malformed required
field raises `FactsError` instead of being defaulted.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pandit_rule_engine.facts import CalculationSnapshot, ChartFacts, PlanetFact
from pandit_rule_engine.vocab import Body, Dignity, Sign


class FactsError(ValueError):
    """The upstream chart is missing or has an invalid required field."""


def _require(mapping: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise FactsError(f"{where}: missing required field {key!r}")
    return mapping[key]


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FactsError(f"{where}: expected an object")
    return value


def _sign(value: Any, where: str) -> Sign:
    try:
        return Sign(value)
    except ValueError as exc:
        raise FactsError(f"{where}: unknown sign {value!r}") from exc


def _body(value: Any, where: str) -> Body:
    try:
        return Body(value)
    except ValueError as exc:
        raise FactsError(f"{where}: unknown body {value!r}") from exc


def facts_from_kundli(kundli: Mapping[str, Any]) -> ChartFacts:
    """Build `ChartFacts` from a Phase 5 Kundli's JSON form."""
    lagna = _mapping(_require(kundli, "lagna", "kundli"), "kundli.lagna")
    lagna_sign = _sign(_require(lagna, "rashi", "kundli.lagna"), "kundli.lagna.rashi")

    sign_lords: dict[Sign, Body] = {}
    for index, house in enumerate(_require(kundli, "houses", "kundli")):
        house_map = _mapping(house, f"kundli.houses[{index}]")
        sign = _sign(_require(house_map, "rashi", "house"), f"kundli.houses[{index}].rashi")
        sign_lords[sign] = _body(
            _require(house_map, "lord", "house"), f"kundli.houses[{index}].lord"
        )

    planets: dict[Body, PlanetFact] = {}
    for index, raw in enumerate(_require(kundli, "planets", "kundli")):
        where = f"kundli.planets[{index}]"
        planet = _mapping(raw, where)
        body = _body(_require(planet, "body", where), where + ".body")
        dignity_value = planet.get("dignity")
        try:
            dignity = None if dignity_value is None else Dignity(dignity_value)
        except ValueError as exc:
            raise FactsError(f"{where}.dignity: unknown dignity {dignity_value!r}") from exc
        planets[body] = PlanetFact(
            body=body,
            sign=_sign(_require(planet, "rashi", where), where + ".rashi"),
            degree_in_sign=_require(planet, "degree_in_sign", where),
            longitude=_require(planet, "longitude", where),
            house=_require(planet, "house", where),
            dignity=dignity,
            retrograde=_require(planet, "retrograde", where),
            combust=planet.get("combust"),
            aspected_houses=tuple(_require(planet, "aspected_houses", where)),
        )

    metadata = _mapping(_require(kundli, "metadata", "kundli"), "kundli.metadata")
    astronomical = kundli.get("astronomical")
    calc_meta: Mapping[str, Any] = {}
    if isinstance(astronomical, Mapping) and isinstance(astronomical.get("metadata"), Mapping):
        calc_meta = astronomical["metadata"]
    config = calc_meta.get("calculation_config") or {}
    time_resolution = calc_meta.get("time_resolution") or {}
    location = calc_meta.get("location") or {}

    snapshot = CalculationSnapshot(
        calculation_engine_version=_require(metadata, "engine_version", "kundli.metadata"),
        standards_version=_require(metadata, "standards_version", "kundli.metadata"),
        zodiac=config.get("zodiac"),
        ayanamsa=config.get("ayanamsa"),
        node_convention=config.get("node_convention"),
        house_system=_require(metadata, "house_system", "kundli.metadata"),
        aspect_standard=metadata.get("aspect_standard"),
        dignity_standard=metadata.get("dignity_standard"),
        varga_scheme=metadata.get("varga_scheme"),
        timezone=time_resolution.get("timezone"),
        input_local_datetime=time_resolution.get("input_local_datetime"),
        utc_datetime=(
            None
            if time_resolution.get("utc_datetime") is None
            else str(time_resolution["utc_datetime"])
        ),
        latitude=location.get("latitude"),
        longitude=location.get("longitude"),
        altitude_meters=location.get("altitude_meters"),
    )
    try:
        return ChartFacts(
            lagna_sign=lagna_sign, sign_lords=sign_lords, planets=planets, snapshot=snapshot
        )
    except ValueError as exc:
        raise FactsError(f"inconsistent chart: {exc}") from exc
