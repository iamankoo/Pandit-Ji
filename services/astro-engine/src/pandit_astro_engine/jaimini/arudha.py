"""Arudha Pada (Phase 9 WP-G; `docs/ASTROLOGY_STANDARDS.md` v1.17.0,
JN-13 to JN-15) -- BPHS Ch. 29 v. 1-7.

Bhava Pada (v. 1-5, profile `ARUDHA_BHAVA_PADA_BPHS_29_1_5`): count the
signs from a house to its lord (inclusive), and the same number again from
the lord. If that lands on the house itself, the Pada is the 10th from the
house; if it lands on the 7th from the house, the Pada is the 4th from the
house. House lords come from the locked Phase 5 lordship table.

Graha Pada (v. 6-7, profile `ARUDHA_GRAHA_PADA_BPHS_29_6_7`): count from the
planet to its own sign and the same again. Only the Sun and the Moon own a
single sign; for the others the verse says to "consider the stronger" sign,
which it does not define, so they are NOT_EVALUABLE; the nodes own no sign
in the locked lordship table.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine.jaimini.profiles import BHAVA_PADA_PROFILE_ID, GRAHA_PADA_PROFILE_ID
from pandit_astro_engine.lordship import RASHI_LORD
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.rashi import Rashi, offset_sign, rashi_index


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PadaRule(str, Enum):
    BASE = "base"
    SAME_HOUSE_TAKES_TENTH = "same_house_takes_tenth"
    SEVENTH_HOUSE_TAKES_FOURTH = "seventh_house_takes_fourth"


class PadaStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class PadaReason(str, Enum):
    STRONGER_SIGN_UNDEFINED = "stronger_sign_undefined"
    NODE_OWNS_NO_SIGN = "node_owns_no_sign"
    PLANET_MISSING = "planet_missing"


#: Traditional names of the twelve Bhava Padas (Ch. 29 note, p. 295).
PADA_NAMES: tuple[str, ...] = (
    "lagna_pada",
    "dhana_pada",
    "vikrama_pada",
    "matru_pada",
    "mantra_pada",
    "roga_pada",
    "dara_pada",
    "marana_pada",
    "pitru_pada",
    "karma_pada",
    "labha_pada",
    "vyaya_pada",
)


class BhavaPada(_Model):
    profile_id: str = BHAVA_PADA_PROFILE_ID
    house: int
    name: str
    house_sign: Rashi
    lord: CelestialBody
    lord_sign: Rashi
    count: int
    pada: Rashi
    rule: PadaRule


class GrahaPada(_Model):
    profile_id: str = GRAHA_PADA_PROFILE_ID
    body: CelestialBody
    status: PadaStatus
    pada: Rashi | None = None
    reason: PadaReason | None = None


def _count(from_sign: Rashi, to_sign: Rashi) -> int:
    """Inclusive count: a sign is 1 from itself."""
    return (rashi_index(to_sign) - rashi_index(from_sign)) % 12 + 1


def bhava_padas(lagna: Rashi, placements: Mapping[CelestialBody, Rashi]) -> tuple[BhavaPada, ...]:
    """The twelve Bhava Padas from the Lagna sign and the planets' Rasi
    signs (whole-sign houses). Every house lord must be present."""
    out = []
    for house in range(1, 13):
        house_sign = offset_sign(lagna, house)
        lord = RASHI_LORD[house_sign]
        if lord not in placements:
            raise ValueError(f"the lord of house {house}, {lord.value}, has no placement")
        lord_sign = placements[lord]
        count = _count(house_sign, lord_sign)
        pada = offset_sign(lord_sign, count)
        rule = PadaRule.BASE
        if pada == house_sign:
            pada, rule = offset_sign(house_sign, 10), PadaRule.SAME_HOUSE_TAKES_TENTH
        elif pada == offset_sign(house_sign, 7):
            pada, rule = offset_sign(house_sign, 4), PadaRule.SEVENTH_HOUSE_TAKES_FOURTH
        out.append(
            BhavaPada(
                house=house,
                name=PADA_NAMES[house - 1],
                house_sign=house_sign,
                lord=lord,
                lord_sign=lord_sign,
                count=count,
                pada=pada,
                rule=rule,
            )
        )
    return tuple(out)


def graha_padas(placements: Mapping[CelestialBody, Rashi]) -> tuple[GrahaPada, ...]:
    out = []
    for body in CelestialBody:
        if body in (CelestialBody.RAHU, CelestialBody.KETU):
            out.append(
                GrahaPada(
                    body=body, status=PadaStatus.NOT_EVALUABLE, reason=PadaReason.NODE_OWNS_NO_SIGN
                )
            )
            continue
        own = [r for r, lord in RASHI_LORD.items() if lord == body]
        if len(own) != 1:
            out.append(
                GrahaPada(
                    body=body,
                    status=PadaStatus.NOT_EVALUABLE,
                    reason=PadaReason.STRONGER_SIGN_UNDEFINED,
                )
            )
            continue
        if body not in placements:
            out.append(
                GrahaPada(
                    body=body, status=PadaStatus.NOT_EVALUABLE, reason=PadaReason.PLANET_MISSING
                )
            )
            continue
        count = _count(placements[body], own[0])
        out.append(GrahaPada(body=body, status=PadaStatus.SUCCESS, pada=offset_sign(own[0], count)))
    return tuple(out)
