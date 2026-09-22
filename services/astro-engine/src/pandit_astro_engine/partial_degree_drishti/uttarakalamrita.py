"""Partial/Degree Drishti, Profile B (Phase 9 WP-C) -- Uttara Kalamrita
Ch. 2 Sl. 17.5-19.5, citing "Sripatipaddhati-II". See `profiles.py` for the
source citation and `docs/ASTROLOGY_STANDARDS.md` PD-01 to PD-11 for the
full methodology lock. Kept entirely independent of `bphs.py` (Profile A):
its own request/result/status/reason types, no shared calculation entry
point, no shared result base, no mergeable profile abstraction.

The rule, in the source's own words (Sl.18.5-19.5): "Subtract the
aspecting planet from the aspected one. The result will indicate the
extent in signs, degrees, etc., of the range of aspect. The Drigbala of
the aspected planet (in terms of Rupas) can be accurately ascertained
from these degrees, etc. by rule-of-three process by the addition to, or
subtraction from, as the case may be, of the proportionate difference in
strength between that fixed for that sign and the strength allotted for
the succeeding sign." -- a linear interpolation between the discrete
checkpoints Sl.17.5-18.5 itself states (the same checkpoints BPHS's own
v.2-5 state), applied uniformly around the full circle with no reduction
step -- which is why this profile has no gap at houses 9-10, unlike
Profile A (PD-05, PD-06).

Special-planet handling (PD-07) is **unconditional** here, including at
the exact peak angle: unlike Profile A, this source's interpolation method
was never stated as applying to the Saturn/Mars/Jupiter own-house case at
all, so no exact-angle carve-out is manufactured for Profile B.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator

from pandit_astro_engine.models import CelestialBody

from .profiles import UTTARAKALAMRITA_SRIPATI_ID

#: Saturn/Mars/Jupiter's own two special houses (BPHS v.2, independently
#: restated in Uttara Kalamrita Sl.17.5-18.5).
_OWN_SPECIAL_HOUSES: dict[CelestialBody, tuple[int, int]] = {
    CelestialBody.SATURN: (3, 10),
    CelestialBody.MARS: (4, 8),
    CelestialBody.JUPITER: (5, 9),
}

_NODES = (CelestialBody.RAHU, CelestialBody.KETU)

#: The discrete checkpoint table (Sl.17.5-18.5), independently agreeing
#: with BPHS v.2-5 at every house, including 9 and 10.
_CHECKPOINTS: dict[float, float] = {
    0.0: 0.0,
    30.0: 0.0,
    60.0: 15.0,
    90.0: 45.0,
    120.0: 30.0,
    150.0: 0.0,
    180.0: 60.0,
    210.0: 45.0,
    240.0: 30.0,
    270.0: 15.0,
    300.0: 0.0,
    330.0: 0.0,
}
_BOUNDARIES: tuple[float, ...] = tuple(sorted(_CHECKPOINTS))

#: Mandatory disclosure per PD-08: the method is source-supported directly
#: from Uttara Kalamrita; the further attribution to Sripatipaddhati-II is
#: the translator's own citation, not independently verified by this
#: project (the primary text was unreachable via two independent technical
#: attempts, not a content-based finding).
PROVENANCE_NOTE = (
    "Method stated directly in Uttara Kalamrita Ch. 2; further attributed there "
    "to Sripatipaddhati-II, which has not been independently verified."
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class UkDrishtiStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class UkDrishtiReason(str, Enum):
    SPECIAL_FORMULA_INTERIOR_UNRESOLVED = "special_formula_interior_unresolved"
    ASPECTING_NODE_UNRESOLVED = "aspecting_node_unresolved"


class UkDrishtiRequest(_Model):
    aspecting_body: CelestialBody
    aspecting_longitude: float
    aspected_longitude: float

    @model_validator(mode="after")
    def _validate(self) -> UkDrishtiRequest:
        for longitude in (self.aspecting_longitude, self.aspected_longitude):
            if not (0.0 <= longitude < 360.0):
                raise ValueError(f"invalid longitude: {longitude}")
        return self


class UkDrishtiResult(_Model):
    profile_id: str
    status: UkDrishtiStatus
    reason_code: UkDrishtiReason | None
    separation_degrees: float
    house: int
    is_own_special_house: bool
    value: float | None
    provenance_note: str

    @model_validator(mode="after")
    def _contract(self) -> UkDrishtiResult:
        resolved = self.status is UkDrishtiStatus.SUCCESS
        if resolved and (self.value is None or self.reason_code is not None):
            raise ValueError("a success result must have a value and no reason_code")
        if not resolved and (self.value is not None or self.reason_code is None):
            raise ValueError("a not-evaluable result must have no value and a reason_code")
        if self.provenance_note != PROVENANCE_NOTE:
            raise ValueError("provenance_note must carry the exact disclosure verbatim")
        return self


def _house_of(delta: float) -> int:
    """1-12, the house the aspected point falls in from the aspecting
    body's own sign (house 1 = same sign, delta in [0,30))."""
    return int(delta // 30.0) + 1


def _interpolated_value(delta: float) -> float:
    """Linear interpolation between the two checkpoints bracketing delta,
    wrapping from 330 deg back to 0 deg (house 12 into house 1)."""
    for index, lower in enumerate(_BOUNDARIES):
        upper = _BOUNDARIES[index + 1] if index + 1 < len(_BOUNDARIES) else 360.0
        if lower <= delta <= upper:
            lower_value = _CHECKPOINTS[lower]
            upper_value = _CHECKPOINTS[0.0] if upper == 360.0 else _CHECKPOINTS[upper]
            if upper == lower:
                return lower_value
            fraction = (delta - lower) / (upper - lower)
            return lower_value + fraction * (upper_value - lower_value)
    # pragma: no cover -- unreachable for delta already normalized to [0,360)
    raise ValueError(f"delta out of range: {delta}")


def calculate_uk_drishti(request: UkDrishtiRequest) -> UkDrishtiResult:
    delta = (request.aspected_longitude - request.aspecting_longitude) % 360.0
    house = _house_of(delta)
    own_special_houses = _OWN_SPECIAL_HOUSES.get(request.aspecting_body)
    is_own_special_house = own_special_houses is not None and house in own_special_houses

    if request.aspecting_body in _NODES:
        return UkDrishtiResult(
            profile_id=UTTARAKALAMRITA_SRIPATI_ID,
            status=UkDrishtiStatus.NOT_EVALUABLE,
            reason_code=UkDrishtiReason.ASPECTING_NODE_UNRESOLVED,
            separation_degrees=delta,
            house=house,
            is_own_special_house=False,
            value=None,
            provenance_note=PROVENANCE_NOTE,
        )

    if is_own_special_house:
        # Unconditional, including at the exact peak angle -- see the
        # module docstring and PD-07: no carve-out is manufactured here.
        return UkDrishtiResult(
            profile_id=UTTARAKALAMRITA_SRIPATI_ID,
            status=UkDrishtiStatus.NOT_EVALUABLE,
            reason_code=UkDrishtiReason.SPECIAL_FORMULA_INTERIOR_UNRESOLVED,
            separation_degrees=delta,
            house=house,
            is_own_special_house=True,
            value=None,
            provenance_note=PROVENANCE_NOTE,
        )

    return UkDrishtiResult(
        profile_id=UTTARAKALAMRITA_SRIPATI_ID,
        status=UkDrishtiStatus.SUCCESS,
        reason_code=None,
        separation_degrees=delta,
        house=house,
        is_own_special_house=False,
        value=_interpolated_value(delta),
        provenance_note=PROVENANCE_NOTE,
    )
