"""Chara Karaka (Phase 9 WP-B-2) -- BPHS Ch. 32 v. 1-17: ranking the
classical planets (and, profile-dependent, Rahu) by descending degree
traversed within their own sign to name eight "inconstant" (Chara)
significators. See `profiles.py` for the two body-scope profiles and their
source citations, and `constant_karaka.py` for the separate v. 18-21
Constant Karaka system this module deliberately does not auto-substitute
into a deficit (see both modules' docstrings and
`research/ASTROLOGY_SOURCES.md` Group 13 for why).

The rule, in the source's own words (v. 3-8): "Among the planets from the
Sun etc. whichever has traversed maximum number of degrees in a particular
sign is called Atmakarka. If the degrees are identical, then the one with
more minutes of arc and if the minutes are also identical then the one with
higher seconds of arc will have to be considered... In the case of Rahu,
deduct his longitude in that particular sign from 30." The remaining seven
roles (v. 13-17) follow the same candidates in descending order. A tie
"identical to the second of arc" (v. 13) among two candidates makes "both...
qualified for that particular karakaatwa", which -- because roles are filled
strictly in rank order -- always produces a shortfall at the *lowest* role
in the fixed sequence (never elsewhere), reported here as
`NOT_EVALUABLE(rank_deficit)` for that role. A tie at the very top (Atma
Karaka itself) is treated as a stronger case: since every other Karaka's
significance is judged relative to Atma Karaka (v. 9-12, "just as the
minister cannot go against the king"), an unresolved Atma Karaka is treated
as poisoning the whole result (`NOT_EVALUABLE(tie_unresolved)`, no partial
role list) rather than as an ordinary rank-deficit -- this differentiated
treatment is a Pandit Ji reading bridging v. 3-8 and v. 13, not a single
verse's explicit statement, and is documented as such in
`docs/ASTROLOGY_STANDARDS.md`.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator

from pandit_astro_engine.jaimini.profiles import CHARA_KARAKA_PROFILE_BODIES
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.rashi import degree_within_sign

_ARC_SECOND = 1.0 / 3600.0


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CharaKarakaRole(str, Enum):
    ATMA_KARAKA = "atma_karaka"
    AMATYA_KARAKA = "amatya_karaka"
    BHRATRU_KARAKA = "bhratru_karaka"
    MATRU_KARAKA = "matru_karaka"
    PITRU_KARAKA = "pitru_karaka"
    PUTRA_KARAKA = "putra_karaka"
    GNATI_KARAKA = "gnati_karaka"
    DARA_KARAKA = "dara_karaka"


#: v. 13-17's own listed order, Atma Karaka first, Dara (Stree) Karaka last.
#: The 7-body profile (`profiles.SEVEN_BODY_ID`) only ever fills the first 7
#: of these; Dara Karaka is then always `NOT_EVALUABLE(rank_deficit)` for
#: that profile, since 7 candidates cannot fill 8 roles (the source's own
#: "only seven significators, merging Matru and Putra" alternative is read
#: but not implemented -- see the module docstring and Group 13).
ROLE_ORDER: tuple[CharaKarakaRole, ...] = (
    CharaKarakaRole.ATMA_KARAKA,
    CharaKarakaRole.AMATYA_KARAKA,
    CharaKarakaRole.BHRATRU_KARAKA,
    CharaKarakaRole.MATRU_KARAKA,
    CharaKarakaRole.PITRU_KARAKA,
    CharaKarakaRole.PUTRA_KARAKA,
    CharaKarakaRole.GNATI_KARAKA,
    CharaKarakaRole.DARA_KARAKA,
)


class CharaKarakaStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class CharaKarakaReason(str, Enum):
    TIE_UNRESOLVED = "tie_unresolved"
    RANK_DEFICIT = "rank_deficit"


class CandidateDegree(_Model):
    """One input body's ranking inputs/outputs -- always present for every
    candidate the profile requires, whether or not its role could be
    assigned."""

    body: CelestialBody
    input_longitude: float
    normalized_degree: float
    comparison_degree: float
    rank: int


class RoleAssignment(_Model):
    role: CharaKarakaRole
    rank: int
    body: CelestialBody | None
    tie_group: tuple[CelestialBody, ...] | None
    status: CharaKarakaStatus
    reason_code: CharaKarakaReason | None

    @model_validator(mode="after")
    def _contract(self) -> RoleAssignment:
        resolved = self.status is CharaKarakaStatus.SUCCESS
        if resolved and (self.body is None or self.reason_code is not None):
            raise ValueError("a success role assignment must have a body and no reason_code")
        if not resolved and (self.body is not None or self.reason_code is None):
            raise ValueError("a not-evaluable role assignment must have no body and a reason_code")
        return self


class CharaKarakaRequest(_Model):
    profile_id: str
    longitudes: dict[CelestialBody, float]

    @model_validator(mode="after")
    def _validate(self) -> CharaKarakaRequest:
        if self.profile_id not in CHARA_KARAKA_PROFILE_BODIES:
            raise ValueError(f"unknown Chara Karaka profile_id: {self.profile_id!r}")
        required = CHARA_KARAKA_PROFILE_BODIES[self.profile_id]
        if CelestialBody.KETU in self.longitudes:
            raise ValueError("Ketu is never a Chara Karaka candidate under any BPHS Ch. 32 reading")
        missing = [b for b in required if b not in self.longitudes]
        if missing:
            raise ValueError(f"missing required bodies for {self.profile_id}: {missing}")
        extra = sorted(b.value for b in self.longitudes if b not in required)
        if extra:
            raise ValueError(f"unexpected bodies for {self.profile_id}: {extra}")
        for body, longitude in self.longitudes.items():
            if not (0.0 <= longitude < 360.0):
                raise ValueError(f"invalid longitude for {body}: {longitude}")
        return self


class CharaKarakaResult(_Model):
    profile_id: str
    status: CharaKarakaStatus
    reason_code: CharaKarakaReason | None
    candidates: tuple[CandidateDegree, ...]
    roles: tuple[RoleAssignment, ...] | None

    @model_validator(mode="after")
    def _contract(self) -> CharaKarakaResult:
        resolved = self.status is CharaKarakaStatus.SUCCESS
        if resolved and (self.roles is None or self.reason_code is not None):
            raise ValueError("a success result must have a role list and no reason_code")
        if not resolved and (self.roles is not None or self.reason_code is None):
            raise ValueError("a not-evaluable result must have no role list and a reason_code")
        return self


def _comparison_degree(body: CelestialBody, longitude: float) -> float:
    normalized = degree_within_sign(longitude)
    if body is CelestialBody.RAHU:
        return 30.0 - normalized
    return normalized


def _round_to_arcsecond(degree: float) -> float:
    # Ties are compared "identical to the second of arc" (v. 13) -- rounding
    # to the nearest arc-second before grouping avoids spurious non-ties
    # from float noise while still requiring genuine second-of-arc equality.
    return round(degree / _ARC_SECOND) * _ARC_SECOND


def calculate_chara_karaka(request: CharaKarakaRequest) -> CharaKarakaResult:
    candidates_raw = [
        (body, longitude, degree_within_sign(longitude), _comparison_degree(body, longitude))
        for body, longitude in request.longitudes.items()
    ]
    # Group by rounded comparison degree, descending -- each group is one
    # dense rank, whether it has one member or several (a tie).
    rounded = {body: _round_to_arcsecond(comp) for body, _, _, comp in candidates_raw}
    distinct_desc = sorted(set(rounded.values()), reverse=True)
    group_of: dict[CelestialBody, int] = {}
    for body in rounded:
        group_of[body] = distinct_desc.index(rounded[body])  # 0-based rank index

    candidates = tuple(
        sorted(
            (
                CandidateDegree(
                    body=body,
                    input_longitude=longitude,
                    normalized_degree=normalized,
                    comparison_degree=comparison,
                    rank=group_of[body] + 1,
                )
                for body, longitude, normalized, comparison in candidates_raw
            ),
            key=lambda c: (c.rank, c.body.value),
        )
    )

    top_group = [c.body for c in candidates if c.rank == 1]
    if len(top_group) > 1:
        return CharaKarakaResult(
            profile_id=request.profile_id,
            status=CharaKarakaStatus.NOT_EVALUABLE,
            reason_code=CharaKarakaReason.TIE_UNRESOLVED,
            candidates=candidates,
            roles=None,
        )

    roles: list[RoleAssignment] = []
    for role_index, role in enumerate(ROLE_ORDER):
        rank = role_index + 1
        members = [c.body for c in candidates if c.rank == rank]
        if not members:
            roles.append(
                RoleAssignment(
                    role=role,
                    rank=rank,
                    body=None,
                    tie_group=None,
                    status=CharaKarakaStatus.NOT_EVALUABLE,
                    reason_code=CharaKarakaReason.RANK_DEFICIT,
                )
            )
            continue
        roles.append(
            RoleAssignment(
                role=role,
                rank=rank,
                body=members[0],
                tie_group=tuple(members) if len(members) > 1 else None,
                status=CharaKarakaStatus.SUCCESS,
                reason_code=None,
            )
        )

    return CharaKarakaResult(
        profile_id=request.profile_id,
        status=CharaKarakaStatus.SUCCESS,
        reason_code=None,
        candidates=candidates,
        roles=tuple(roles),
    )
