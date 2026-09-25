"""Karakamsa (Phase 9 WP-G; `docs/ASTROLOGY_STANDARDS.md` v1.17.0, JN-16/JN-17)
-- BPHS Ch. 33 v. 1-2: the Navamsa sign occupied by the Atma Karaka.

Profile `KARAKAMSA_BPHS_33_1_2`. The Atma Karaka comes from a Chara Karaka
result computed under the caller's own profile (seven- or eight-body, no
default); the Navamsa from the locked Phase 5 D9 scheme. When the Chara
Karaka result has no Atma Karaka (a top tie), Karakamsa is NOT_EVALUABLE --
never taken from the other profile or from a guess.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine.jaimini.chara_karaka import (
    CharaKarakaResult,
    CharaKarakaRole,
    CharaKarakaStatus,
)
from pandit_astro_engine.jaimini.profiles import KARAKAMSA_PROFILE_ID
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.rashi import Rashi
from pandit_astro_engine.vargas import calculate_varga_sign


class KarakamsaStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class KarakamsaReason(str, Enum):
    ATMA_KARAKA_UNRESOLVED = "atma_karaka_unresolved"


class KarakamsaResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: str = KARAKAMSA_PROFILE_ID
    chara_karaka_profile_id: str
    status: KarakamsaStatus
    atma_karaka: CelestialBody | None = None
    atma_karaka_longitude: float | None = None
    karakamsa: Rashi | None = None
    reason: KarakamsaReason | None = None


def karakamsa(
    chara_karaka: CharaKarakaResult, longitudes: Mapping[CelestialBody, float]
) -> KarakamsaResult:
    """`longitudes` are the same sidereal longitudes the Chara Karaka result
    was computed from."""
    atma = None
    if chara_karaka.status is not CharaKarakaStatus.NOT_EVALUABLE and chara_karaka.roles:
        first = chara_karaka.roles[0]
        if first.role is CharaKarakaRole.ATMA_KARAKA and first.body is not None:
            atma = first.body
    if atma is None:
        return KarakamsaResult(
            chara_karaka_profile_id=chara_karaka.profile_id,
            status=KarakamsaStatus.NOT_EVALUABLE,
            reason=KarakamsaReason.ATMA_KARAKA_UNRESOLVED,
        )
    longitude = longitudes[atma]
    return KarakamsaResult(
        chara_karaka_profile_id=chara_karaka.profile_id,
        status=KarakamsaStatus.SUCCESS,
        atma_karaka=atma,
        atma_karaka_longitude=longitude,
        karakamsa=calculate_varga_sign(9, longitude),
    )
