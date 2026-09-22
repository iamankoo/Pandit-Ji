"""Partial/Degree Drishti, Profile A (Phase 9 WP-C) -- BPHS Ch. 26 v. 1-13.
See `profiles.py` for the source citation and `docs/ASTROLOGY_STANDARDS.md`
PD-01 to PD-11 for the full methodology lock. Kept entirely independent of
`uttarakalamrita.py` (Profile B): no shared calculation entry point, no
shared result base, no mergeable profile abstraction.

The rule, in the source's own words (v.2-5): a movable/fixed/dual-style
graduated progression on the 3rd/10th, 4th/8th, 5th/9th and 7th houses from
the aspecting planet, with Saturn/Mars/Jupiter's own special houses
upgraded to full. v.6-9 gives a continuous five-branch formula which this
module implements literally; a project-level derivation (documented, never
presented as BPHS's own claim) shows this formula is algebraically
identical to linear interpolation between the discrete checkpoints v.2-5
themselves state. v.9-12 give Saturn/Mars/Jupiter's own override formulas,
each confirmed to reach exactly 60 (full) at that planet's own special
house; nothing beyond that exact point is resolved.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator

from pandit_astro_engine.models import CelestialBody

from .profiles import BPHS_26_ID

#: Saturn/Mars/Jupiter's own two special houses (BPHS v.2, v.9-12).
_OWN_SPECIAL_HOUSES: dict[CelestialBody, tuple[int, int]] = {
    CelestialBody.SATURN: (3, 10),
    CelestialBody.MARS: (4, 8),
    CelestialBody.JUPITER: (5, 9),
}

#: Houses where BPHS's own literal v.6 reduction contradicts BPHS's own
#: v.2 pairing statement (PD-05) -- disputed only for a planet that does
#: NOT own that house as its special aspect.
_DISPUTED_HOUSES = (9, 10)

_NODES = (CelestialBody.RAHU, CelestialBody.KETU)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BphsDrishtiStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class BphsDrishtiReason(str, Enum):
    REDUCTION_RULE_CONFLICT = "reduction_rule_conflict"
    SPECIAL_FORMULA_INTERIOR_UNRESOLVED = "special_formula_interior_unresolved"
    ASPECTING_NODE_UNRESOLVED = "aspecting_node_unresolved"


class BphsDrishtiRequest(_Model):
    aspecting_body: CelestialBody
    aspecting_longitude: float
    aspected_longitude: float

    @model_validator(mode="after")
    def _validate(self) -> BphsDrishtiRequest:
        for longitude in (self.aspecting_longitude, self.aspected_longitude):
            if not (0.0 <= longitude < 360.0):
                raise ValueError(f"invalid longitude: {longitude}")
        return self


class BphsDrishtiResult(_Model):
    profile_id: str
    status: BphsDrishtiStatus
    reason_code: BphsDrishtiReason | None
    separation_degrees: float
    house: int
    is_own_special_house: bool
    value: float | None

    @model_validator(mode="after")
    def _contract(self) -> BphsDrishtiResult:
        resolved = self.status is BphsDrishtiStatus.SUCCESS
        if resolved and (self.value is None or self.reason_code is not None):
            raise ValueError("a success result must have a value and no reason_code")
        if not resolved and (self.value is not None or self.reason_code is None):
            raise ValueError("a not-evaluable result must have no value and a reason_code")
        return self


def _house_of(delta: float) -> int:
    """1-12, the house the aspected point falls in from the aspecting
    body's own sign (house 1 = same sign, delta in [0,30))."""
    return int(delta // 30.0) + 1


def _general_branch_value(delta: float) -> float:
    """BPHS v.6-9's own five-branch formula, for delta already reduced
    into [0,180]. Algebraically identical to linear interpolation between
    the v.2-5 checkpoints (0/0/15/45/30/0/60 at delta=0/30/60/90/120/150/180)
    -- a project-level derivation, documented in `docs/ASTROLOGY_STANDARDS.md`
    PD-04, never presented as BPHS's own statement."""
    if delta <= 30.0:
        return 0.0
    if delta <= 60.0:
        return (delta - 30.0) / 2.0
    if delta <= 90.0:
        return 15.0 + (delta - 60.0)
    if delta <= 120.0:
        return 30.0 + (120.0 - delta) / 2.0
    if delta <= 150.0:
        return 150.0 - delta
    return (delta - 150.0) * 2.0


def _general_value(delta: float) -> float:
    """The full-circle general formula: BPHS's own branches directly for
    delta in [0,180], BPHS's own literal reduction (v.6, Sanskrit-confirmed
    "10 signs / 300 deg", PD-03) for delta in (180,300], and the
    independently-known never-aspected houses 11-12 for delta in (300,360)."""
    if delta <= 180.0:
        return _general_branch_value(delta)
    if delta <= 300.0:
        return _general_branch_value(300.0 - delta)
    return 0.0


def calculate_bphs_drishti(request: BphsDrishtiRequest) -> BphsDrishtiResult:
    delta = (request.aspected_longitude - request.aspecting_longitude) % 360.0
    house = _house_of(delta)
    own_special_houses = _OWN_SPECIAL_HOUSES.get(request.aspecting_body)
    is_own_special_house = own_special_houses is not None and house in own_special_houses

    if request.aspecting_body in _NODES:
        return BphsDrishtiResult(
            profile_id=BPHS_26_ID,
            status=BphsDrishtiStatus.NOT_EVALUABLE,
            reason_code=BphsDrishtiReason.ASPECTING_NODE_UNRESOLVED,
            separation_degrees=delta,
            house=house,
            is_own_special_house=False,
            value=None,
        )

    if is_own_special_house:
        peak_degrees = (house - 1) * 30.0
        if delta == peak_degrees:
            return BphsDrishtiResult(
                profile_id=BPHS_26_ID,
                status=BphsDrishtiStatus.SUCCESS,
                reason_code=None,
                separation_degrees=delta,
                house=house,
                is_own_special_house=True,
                value=60.0,
            )
        return BphsDrishtiResult(
            profile_id=BPHS_26_ID,
            status=BphsDrishtiStatus.NOT_EVALUABLE,
            reason_code=BphsDrishtiReason.SPECIAL_FORMULA_INTERIOR_UNRESOLVED,
            separation_degrees=delta,
            house=house,
            is_own_special_house=True,
            value=None,
        )

    if house in _DISPUTED_HOUSES:
        return BphsDrishtiResult(
            profile_id=BPHS_26_ID,
            status=BphsDrishtiStatus.NOT_EVALUABLE,
            reason_code=BphsDrishtiReason.REDUCTION_RULE_CONFLICT,
            separation_degrees=delta,
            house=house,
            is_own_special_house=False,
            value=None,
        )

    return BphsDrishtiResult(
        profile_id=BPHS_26_ID,
        status=BphsDrishtiStatus.SUCCESS,
        reason_code=None,
        separation_degrees=delta,
        house=house,
        is_own_special_house=False,
        value=_general_value(delta),
    )
