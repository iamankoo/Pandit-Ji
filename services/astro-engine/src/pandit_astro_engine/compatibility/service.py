"""Compatibility service facade (Phase 11; `docs/ASTROLOGY_STANDARDS.md`
v1.25.0, CM-01 to CM-12).

    CompatibilityRequest -> CompatibilityService.match -> CompatibilityFacts

The minimum-age policy is applied first, from the civil birth dates, before
any astronomy: a blocked request exposes no chart or matching fact. Each
birth Moon comes from the Phase 4 astronomical service (sidereal, the
request's ayanamsa); for an approximate birth time the Moon at both ends of
the interval decides whether the nakshatra, pada and sign are certain. The
selected profile then evaluates its factors; the two profiles never share a
result. Nothing is logged; failures come back as structured statuses.
"""

from __future__ import annotations

import datetime as dt
from typing import TypedDict

from pandit_astro_engine import planets
from pandit_astro_engine._version import __version__
from pandit_astro_engine.compatibility.age_gate import check_participant
from pandit_astro_engine.compatibility.ashtakoot import evaluate_ashtakoot
from pandit_astro_engine.compatibility.constants import (
    COMPATIBILITY_STANDARDS_VERSION,
    METHODOLOGY_VERSION,
    MINIMUM_AGE_YEARS,
    PROFILE_SYSTEM,
    CompatibilityProfileId,
    CompatibilitySystem,
    FactorStatus,
    MatchReason,
    MatchStatus,
    Participant,
)
from pandit_astro_engine.compatibility.models import (
    AshtakootTotal,
    CompatibilityFacts,
    CompatibilityRequest,
    MatchParticipantInput,
    MoonPlacement,
    NotImplementedItem,
    ParticipantPolicyRecord,
    PoruthamSummary,
    ProvenanceEntry,
)
from pandit_astro_engine.compatibility.porutham import evaluate_ten_porutham
from pandit_astro_engine.compatibility.profiles import PROVENANCE
from pandit_astro_engine.dashas.models import BirthTimeStatus
from pandit_astro_engine.errors import (
    AmbiguousLocalTimeError,
    EphemerisDataUnavailableError,
    InvalidTimezoneError,
    NonexistentLocalTimeError,
)
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CelestialBody,
    ZodiacType,
)
from pandit_astro_engine.nakshatra import (
    NAKSHATRA_SPAN_DEGREES,
    PADA_SPAN_DEGREES,
    nakshatra_position,
)
from pandit_astro_engine.rashi import rashi_from_longitude
from pandit_astro_engine.service import AstronomicalCalculationService

_JD_PER_SECOND = 1.0 / 86_400.0
_AK = CompatibilityProfileId.ASHTAKOOT_MUHURTA_CHINTAMANI

ASSUMPTIONS: tuple[str, ...] = (
    "The birth Moon is sidereal under the request's ayanamsa (Lahiri by default), classified "
    "with the Phase 5 half-open nakshatra, pada and sign intervals.",
    "The caller supplies the current civil date for the age check; the engine reads no clock.",
    "No role, gender or relationship of the two people is known or assumed.",
)

UNRESOLVED: dict[CompatibilityProfileId, tuple[str, ...]] = {
    _AK: (
        "Vashya: the verse leaves most sign relations to worldly usage and the point schemes "
        "read disagree (no points given).",
        "Gana: the Daivajna Manohara quote, Mahidhara's text and Mahidhara's table disagree on "
        "mixed-gana cells (role-dependent in any case).",
        "Varna: equal varnas give one guna in this profile; some authorities give half.",
        "Yoni: pairs whose two printed table cells differ are not evaluable.",
        "Bhakoot cancellations: how the v. 32-33 conditions combine is disputed.",
    ),
    CompatibilityProfileId.TEN_PORUTHAM_KALAPRAKASIKA: (
        "Ganam: four nakshatras are in no printed list.",
        "Sthree-Dheergham: beyond the 13th, or 'some writers' the 7th.",
        "Dhinam: the rule names the 2nd, 4th, 6th and 8th as good and the 3rd, 5th and 7th as "
        "bad, and is silent on the 1st and 9th of each cycle.",
        "Rasyadhipathi: no judgment rule is printed; Saturn's friends are not listed.",
    ),
}

NOT_IMPLEMENTED: dict[CompatibilityProfileId, tuple[NotImplementedItem, ...]] = {
    _AK: (
        NotImplementedItem(
            item="Varga kuta (v. 36)",
            reason="Name-letter based and stated as an eastern opinion; no name is taken.",
        ),
        NotImplementedItem(
            item="Purva, madhya and apara bhaga (v. 35)",
            reason=(
                "A statement of which partner is loved, by role; statements of effect are "
                "not encoded."
            ),
        ),
        NotImplementedItem(
            item=(
                "Four- and five-nadi regional schemes; regional and caste exceptions to Nadi dosha"
            ),
            reason=(
                "Regional conventions not selected; caste-specific rules are excluded by policy."
            ),
        ),
        NotImplementedItem(
            item="Statements of effect (death, poverty, loss of children and the like)",
            reason="PRODUCT_POLICIES.md: no fear-based claims.",
        ),
        NotImplementedItem(
            item="Kuja (Mangal) dosha comparison",
            reason="Given by the rule engine from each person's Phase 6 results, not here.",
        ),
    ),
    CompatibilityProfileId.TEN_PORUTHAM_KALAPRAKASIKA: (
        NotImplementedItem(
            item="Male, female and hermaphrodite asterisms (p. 77)",
            reason="Judged by which partner is the man and which the woman.",
        ),
        NotImplementedItem(
            item="Nakshatra gothram (p. 77)",
            reason="Divides 28 asterisms including Abhijit; the Moon's 27 are not mapped to it.",
        ),
        NotImplementedItem(
            item="Castes of the signs (p. 77)",
            reason="Caste-specific rules are excluded by policy.",
        ),
        NotImplementedItem(
            item="Named nakshatra pairs and common-nakshatra rules (pp. 70-72)",
            reason="Judged by role and stated as effects.",
        ),
        NotImplementedItem(
            item="Statements of effect and the omen rule (p. 76)",
            reason="PRODUCT_POLICIES.md: no fear-based claims; omens are not calculable.",
        ),
    ),
}

CONFIDENCE: dict[CompatibilityProfileId, str] = {
    _AK: (
        "MEDIUM: verses and commentary read in OCR of Sanskrit and Hindi by a non-qualified "
        "reader; the point tables checked on page images; no Sanskrit-level review."
    ),
    CompatibilityProfileId.TEN_PORUTHAM_KALAPRAKASIKA: (
        "HIGH for the tables read on page images (pp. 72-76, translation level); MEDIUM for "
        "pp. 69-71 (OCR); no Sanskrit-level review."
    ),
}


class CompatibilityService:
    """Stateless facade, matching the other astro-engine services."""

    def __init__(self, astronomical_service: AstronomicalCalculationService | None = None) -> None:
        self._astronomical = astronomical_service or AstronomicalCalculationService()

    def match(self, request: CompatibilityRequest) -> CompatibilityFacts:
        try:
            return self._match(request)
        except InvalidTimezoneError:
            return _refusal(request, MatchStatus.INVALID_INPUT, MatchReason.INVALID_TIMEZONE)
        except AmbiguousLocalTimeError:
            return _refusal(request, MatchStatus.INVALID_INPUT, MatchReason.AMBIGUOUS_LOCAL_TIME)
        except NonexistentLocalTimeError:
            return _refusal(request, MatchStatus.INVALID_INPUT, MatchReason.NONEXISTENT_LOCAL_TIME)
        except EphemerisDataUnavailableError:
            return _refusal(request, MatchStatus.INVALID_INPUT, MatchReason.EPHEMERIS_UNAVAILABLE)
        except Exception:  # never leak a stack trace (or birth data) through a result
            return _refusal(request, MatchStatus.INTERNAL_ERROR, MatchReason.INTERNAL_ERROR)

    def _match(self, request: CompatibilityRequest) -> CompatibilityFacts:
        try:
            birth_dates = (
                _civil_date(request.person_a),
                _civil_date(request.person_b),
            )
        except ValueError:
            return _refusal(request, MatchStatus.INVALID_INPUT, MatchReason.INVALID_BIRTH_DATE)

        checks = tuple(
            check_participant(participant, birth_date, request.as_of_date)
            for participant, birth_date in zip(
                (Participant.A, Participant.B), birth_dates, strict=True
            )
        )
        if not all(check.minimum_age_met for check in checks):
            refusal = (
                MatchReason.PARTICIPANT_UNDER_MINIMUM_AGE
                if any(check.minimum_age_met is False for check in checks)
                else MatchReason.AGE_NOT_VERIFIABLE
            )
            return _refusal(request, MatchStatus.BLOCKED_BY_POLICY, refusal, checks)

        if request.config.zodiac is not ZodiacType.SIDEREAL:
            return _refusal(
                request, MatchStatus.INVALID_INPUT, MatchReason.SIDEREAL_ZODIAC_REQUIRED, checks
            )

        a = self._placement(Participant.A, request.person_a, request)
        b = self._placement(Participant.B, request.person_b, request)
        total: AshtakootTotal | None = None
        summary: PoruthamSummary | None = None
        if request.profile is _AK:
            factors, doshas, total = evaluate_ashtakoot(a, b)
        else:
            factors, doshas, summary = evaluate_ten_porutham(a, b)

        evaluated = sum(1 for f in factors if f.status is FactorStatus.EVALUATED)
        reason: MatchReason | None
        if evaluated == len(factors):
            status, reason = MatchStatus.COMPLETE, None
        elif evaluated:
            status, reason = MatchStatus.PARTIAL, None
        else:
            status, reason = MatchStatus.NOT_EVALUABLE, MatchReason.NO_FACTOR_EVALUABLE

        return CompatibilityFacts(
            **_header(request),
            status=status,
            reason=reason,
            policy_checks=checks,
            placements=(a, b),
            factors=factors,
            doshas=doshas,
            assumptions=ASSUMPTIONS,
            unresolved_choices=UNRESOLVED[request.profile],
            not_implemented=NOT_IMPLEMENTED[request.profile],
            source_confidence=CONFIDENCE[request.profile],
            provenance=_provenance(request.profile),
            notes=(
                "Factor-level facts only: no overall compatible or incompatible verdict, and no "
                "claim about the success of a relationship.",
            ),
            ashtakoot_total=total,
            porutham_summary=summary,
        )

    # ------------------------------------------------------------------

    def _placement(
        self,
        participant: Participant,
        person: MatchParticipantInput,
        request: CompatibilityRequest,
    ) -> MoonPlacement:
        status = person.birth_time.status
        if status is BirthTimeStatus.NOT_EVALUABLE:
            return MoonPlacement(
                participant=participant,
                birth_time_status=status,
                nakshatra=None,
                pada=None,
                rashi=None,
            )
        astro_request = AstronomicalCalculationRequest(
            local_datetime=person.local_datetime,
            location=person.location,
            config=request.config,
            bodies=[CelestialBody.MOON],
            include_solar_events=False,
        )
        result = self._astronomical.calculate(astro_request)
        moon = result.planets.moon
        if moon is None:  # pragma: no cover - the Moon was requested
            raise RuntimeError("moon missing")
        nominal = moon.longitude
        low = high = nominal
        seconds = person.birth_time.uncertainty_seconds
        if status is BirthTimeStatus.APPROXIMATE:
            if seconds is None or not (0 < seconds < float("inf")):
                return MoonPlacement(
                    participant=participant,
                    birth_time_status=status,
                    nakshatra=None,
                    pada=None,
                    rashi=None,
                    moon_longitude=nominal,
                )
            jd = result.metadata.time_resolution.julian_day_ut
            ends = []
            for shift in (-seconds, seconds):
                states, _ = planets.calculate_all_bodies(
                    jd + shift * _JD_PER_SECOND, request.config, [CelestialBody.MOON]
                )
                longitude = states[CelestialBody.MOON].longitude
                ends.append(nominal + ((longitude - nominal + 180.0) % 360.0) - 180.0)
            low, high = min(ends[0], nominal), max(ends[1], nominal)
        return _classify(participant, status, nominal, low, high)


def _classify(
    participant: Participant,
    status: BirthTimeStatus,
    nominal: float,
    low: float,
    high: float,
) -> MoonPlacement:
    span = high - low
    first, last = nakshatra_position(low % 360.0), nakshatra_position(high % 360.0)
    nakshatra_stable = first.nakshatra is last.nakshatra and span < NAKSHATRA_SPAN_DEGREES
    pada_stable = nakshatra_stable and first.pada == last.pada and span < PADA_SPAN_DEGREES
    sign_low, sign_high = rashi_from_longitude(low % 360.0), rashi_from_longitude(high % 360.0)
    sign_stable = sign_low is sign_high and span < 30.0
    return MoonPlacement(
        participant=participant,
        birth_time_status=status,
        nakshatra=first.nakshatra if nakshatra_stable else None,
        pada=first.pada if pada_stable else None,
        rashi=sign_low if sign_stable else None,
        moon_longitude=nominal % 360.0,
        moon_longitude_low=None if span == 0 else low,
        moon_longitude_high=None if span == 0 else high,
    )


def _civil_date(person: MatchParticipantInput) -> dt.date:
    local = person.local_datetime
    return dt.date(local.year, local.month, local.day)


class _Header(TypedDict):
    system: CompatibilitySystem
    profile_id: CompatibilityProfileId
    methodology_version: str
    standards_version: str
    engine_version: str
    as_of_date: dt.date
    minimum_age_years: int


def _header(request: CompatibilityRequest) -> _Header:
    return {
        "system": PROFILE_SYSTEM[request.profile],
        "profile_id": request.profile,
        "methodology_version": METHODOLOGY_VERSION[request.profile],
        "standards_version": COMPATIBILITY_STANDARDS_VERSION,
        "engine_version": __version__,
        "as_of_date": request.as_of_date,
        "minimum_age_years": MINIMUM_AGE_YEARS,
    }


def _provenance(profile: CompatibilityProfileId) -> tuple[ProvenanceEntry, ...]:
    return tuple(
        ProvenanceEntry(
            entry_id=d.entry_id,
            item=d.item,
            evidence_label=d.label,
            statement=d.statement,
            references=d.references,
        )
        for d in PROVENANCE[profile]
    )


def _refusal(
    request: CompatibilityRequest,
    status: MatchStatus,
    reason: MatchReason,
    checks: tuple[ParticipantPolicyRecord, ...] = (),
) -> CompatibilityFacts:
    notes: tuple[str, ...] = ()
    if status is MatchStatus.BLOCKED_BY_POLICY:
        notes = (
            f"Marriage matching is not produced unless both people are at least "
            f"{MINIMUM_AGE_YEARS} on the supplied date (PRODUCT_POLICIES.md, Minors).",
        )
    return CompatibilityFacts(
        **_header(request),
        status=status,
        reason=reason,
        policy_checks=checks,
        notes=notes,
    )


__all__ = ["CompatibilityService"]
