"""Planet-level Rashi Drishti (Phase 9 WP-G; `docs/ASTROLOGY_STANDARDS.md`
v1.17.0, JN-11/JN-12) -- BPHS Ch. 8 v. 4-5: a planet casts the Rashi
Drishti of the sign it occupies (`rashi_drishti`), on those signs and on the
planets in them.

Profile `RASHI_DRISHTI_PLANET_BPHS_8_4_5`. A separate system from the Phase
5/6 graha drishti (`aspects.py`): it is never merged with it, substituted
for it, or used to fill a graha-drishti question (JN-03, JN-12). Longitudes
are irrelevant; only the occupied signs matter.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine.jaimini.profiles import PLANET_RASHI_DRISHTI_PROFILE_ID
from pandit_astro_engine.jaimini.rashi_drishti import rashi_drishti
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.rashi import Rashi

_ORDER: tuple[CelestialBody, ...] = tuple(CelestialBody)


class PlanetRashiDrishti(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: str = PLANET_RASHI_DRISHTI_PROFILE_ID
    body: CelestialBody
    sign: Rashi
    aspected_signs: tuple[Rashi, ...]
    aspected_bodies: tuple[CelestialBody, ...]


def planet_rashi_drishti(
    placements: Mapping[CelestialBody, Rashi],
) -> tuple[PlanetRashiDrishti, ...]:
    """For every body given, the signs and the given bodies it aspects.
    Bodies are processed and listed in canonical order. Which bodies to pass
    (for example with or without the nodes) is the caller's choice; the
    translator's example includes the nodes."""
    out = []
    for body in _ORDER:
        if body not in placements:
            continue
        sign = placements[body]
        targets = rashi_drishti(sign)
        aspected = tuple(b for b in _ORDER if b in placements and placements[b] in targets)
        out.append(
            PlanetRashiDrishti(
                body=body, sign=sign, aspected_signs=targets, aspected_bodies=aspected
            )
        )
    return tuple(out)
