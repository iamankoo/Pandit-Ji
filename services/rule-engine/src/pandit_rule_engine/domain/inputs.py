"""Optional inputs of the domain evaluator that are not part of the Phase 6 ``ChartFacts``.

``VargaPlacements`` is read from the **same Kundli JSON** that ``facts_from_kundli`` already reads
(its ``charts`` section holds every divisional chart astro-engine computed), so no new interface
and no new calculation exist: this module only maps fields, like the other adapters. The Phase 6
``ChartFacts`` is deliberately unchanged (it stays D1-only, and the Phase 6 hash with it).

A missing or malformed divisional chart is reported to the caller as ``None`` /
:class:`FactsError`; the evaluator then answers ``INSUFFICIENT_EVIDENCE`` for any rule that needs
it. A varga fact is never invented.

Only the eight divisional charts of the locked BPHS mappings (``LOCKED_VARGAS``: D2, D3, D7, D9,
D10, D12, D20, D24) are read into the container. Every other chart of the Kundli (D1, D4 and the
rest) is skipped before it is parsed: it is never materialized, hashed or offered to a rule.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.domain.schema import LOCKED_VARGAS
from pandit_rule_engine.vocab import Body, Sign


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VargaChart(_M):
    varga: int
    ascendant: Sign
    planets: dict[Body, Sign]


class VargaPlacements(_M):
    """The divisional charts of one Kundli, as sign placements only."""

    scheme: str
    charts: dict[int, VargaChart]
    facts_hash: str

    def chart(self, varga: int) -> VargaChart | None:
        return self.charts.get(varga)


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


def varga_from_kundli(kundli: Mapping[str, Any]) -> VargaPlacements | None:
    """The approved divisional placements of a Phase 5 Kundli (JSON form).

    ``None`` when the Kundli has no divisional charts at all. Charts outside ``LOCKED_VARGAS`` are
    ignored; if none of the approved eight is present the container is empty (no placement exists).
    """
    charts_raw = kundli.get("charts")
    if not isinstance(charts_raw, Mapping) or not charts_raw:
        return None
    metadata = kundli.get("metadata")
    scheme = (
        str(metadata.get("varga_scheme"))
        if isinstance(metadata, Mapping) and metadata.get("varga_scheme")
        else "unspecified"
    )
    charts: dict[int, VargaChart] = {}
    for key, raw in charts_raw.items():
        where = f"kundli.charts[{key}]"
        if not isinstance(raw, Mapping):
            raise FactsError(f"{where}: expected an object")
        try:
            number = int(raw.get("varga", key))
        except (TypeError, ValueError) as exc:
            raise FactsError(f"{where}: varga is not an integer") from exc
        if number not in LOCKED_VARGAS:
            continue  # an unapproved chart is never read, parsed or hashed
        placements: dict[Body, Sign] = {}
        for index, planet in enumerate(raw.get("planets") or ()):
            if not isinstance(planet, Mapping):
                raise FactsError(f"{where}.planets[{index}]: expected an object")
            body = _body(planet.get("body"), f"{where}.planets[{index}].body")
            placements[body] = _sign(planet.get("rashi"), f"{where}.planets[{index}].rashi")
        charts[number] = VargaChart(
            varga=number,
            ascendant=_sign(raw.get("ascendant_rashi"), f"{where}.ascendant_rashi"),
            planets=placements,
        )
    digest = hashlib.sha256(
        json.dumps(
            {
                "scheme": scheme,
                "charts": {
                    str(n): {
                        "asc": c.ascendant.value,
                        "planets": {b.value: s.value for b, s in sorted(c.planets.items())},
                    }
                    for n, c in sorted(charts.items())
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return VargaPlacements(scheme=scheme, charts=charts, facts_hash=digest)
