"""Pure transit evaluation over positions (Phase 8): natal resolution, body
state, favourable-set readings, Vedha, sign-based contacts and the snapshot.

No ephemeris access here beyond the injected `PositionProvider`. Everything is
a structural fact; nothing is interpreted (docs/ASTROLOGY_STANDARDS.md TR-01).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from pandit_astro_engine.aspects import aspect_offsets
from pandit_astro_engine.dashas.models import BirthTimeStatus
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import nakshatra_position
from pandit_astro_engine.rashi import (
    degree_within_sign,
    rashi_from_index,
    sign_index_from_longitude,
)
from pandit_astro_engine.transits.constants import ALL_BODIES, NODES
from pandit_astro_engine.transits.models import (
    BodyState,
    ContactKind,
    FavourableEvaluation,
    FavourableReadingResult,
    FavourableStatus,
    NatalReference,
    SadeSatiState,
    SectionStatus,
    TransitConfiguration,
    TransitContact,
    TransitReason,
    TransitSnapshot,
    VedhaFact,
)
from pandit_astro_engine.transits.positions import BodyPosition, PositionProvider
from pandit_astro_engine.transits.profiles import (
    SADE_SATI_ID,
    SADE_SATI_PHASE_BY_OFFSET,
    VEDHA_EXEMPT,
    VEDHA_PAIRS,
    VEDHA_PHALADEEPIKA_ID,
    VENUS_VEDHA_ANOMALY_WARNING,
    readings_for,
)

# --------------------------------------------------------------------------
# Natal resolution
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class NatalContext:
    moon_sign: int | None
    moon_reason: TransitReason | None
    lagna_sign: int | None
    lagna_reason: TransitReason | None
    natal_signs: dict[CelestialBody, int] | None
    planets_reason: TransitReason | None


def sign_of(longitude: float) -> int:
    return sign_index_from_longitude(longitude)


def moon_range_width(low: float, high: float) -> float:
    """Forward width of the range low -> high, degrees, in [0, 360)."""
    return (high - low) % 360.0


def value_in_range(value: float, low: float, high: float) -> bool:
    return (value - low) % 360.0 <= moon_range_width(low, high)


def resolve_natal(natal: NatalReference) -> NatalContext:
    """What can be said about the natal chart without guessing. An approximate
    natal time is never treated as exact (docs TR-10)."""
    moon_sign: int | None = None
    moon_reason: TransitReason | None = None
    if natal.precision == BirthTimeStatus.NOT_EVALUABLE:
        moon_reason = TransitReason.NATAL_TIME_UNKNOWN
    elif natal.precision == BirthTimeStatus.EXACT:
        if natal.moon_longitude is None:
            moon_reason = TransitReason.MOON_LONGITUDE_MISSING
        else:
            moon_sign = sign_of(natal.moon_longitude)
    else:  # APPROXIMATE
        low, high = natal.moon_longitude_low, natal.moon_longitude_high
        if low is None or high is None:
            moon_reason = TransitReason.NATAL_RANGE_MISSING
        elif moon_range_width(low, high) >= 30.0 or sign_of(low) != sign_of(high):
            moon_reason = TransitReason.NATAL_MOON_SIGN_AMBIGUOUS
        else:
            moon_sign = sign_of(low)

    exact = natal.precision == BirthTimeStatus.EXACT
    lagna_sign = (
        sign_of(natal.lagna_longitude) if exact and natal.lagna_longitude is not None else None
    )
    lagna_reason = None if lagna_sign is not None else TransitReason.LAGNA_UNAVAILABLE

    natal_signs: dict[CelestialBody, int] | None = None
    planets_reason: TransitReason | None = TransitReason.NATAL_PLANETS_UNAVAILABLE
    if exact and natal.natal_planets:
        natal_signs = {body: sign_of(lon) for body, lon in natal.natal_planets.items()}
        planets_reason = None
    return NatalContext(
        moon_sign, moon_reason, lagna_sign, lagna_reason, natal_signs, planets_reason
    )


def house_from(sign_index: int, reference_sign_index: int) -> int:
    """Whole-sign house of `sign_index` counted from `reference_sign_index` (=1)."""
    return (sign_index - reference_sign_index) % 12 + 1


# --------------------------------------------------------------------------
# Body state
# --------------------------------------------------------------------------


def build_state(body: CelestialBody, position: BodyPosition, ctx: NatalContext) -> BodyState:
    sign_index = sign_of(position.longitude)
    nakshatra = nakshatra_position(position.longitude)
    return BodyState(
        body=body,
        longitude=position.longitude,
        sign=rashi_from_index(sign_index),
        degree_in_sign=degree_within_sign(position.longitude),
        nakshatra=nakshatra.nakshatra,
        pada=nakshatra.pada,
        speed_longitude=position.speed_longitude,
        retrograde=position.retrograde,
        ephemeris_mode=position.ephemeris_mode,
        house_from_moon=(
            house_from(sign_index, ctx.moon_sign) if ctx.moon_sign is not None else None
        ),
        house_from_lagna=None,
    )


# --------------------------------------------------------------------------
# Favourable-set readings (TR-04, TR-05)
# --------------------------------------------------------------------------


def evaluate_favourable(body: CelestialBody, house: int) -> FavourableEvaluation:
    """Each source reading is evaluated separately. Agreement is reported with
    every attesting reading ID; disagreement is `NOT_EVALUABLE(reading_ambiguous)`
    with every outcome kept. A node is single-source and never consolidated."""
    is_node = body in NODES
    results = tuple(
        FavourableReadingResult(
            reading_id=reading.reading_id,
            label=reading.label,
            in_favourable_set=house in reading.houses[body],
            single_source=is_node,
            verification_level=reading.verification_level,
        )
        for reading in readings_for(body)
    )
    if is_node:
        return FavourableEvaluation(
            body=body,
            house_from_moon=house,
            status=FavourableStatus.NOT_EVALUABLE,
            reason_code=TransitReason.NODE_READING_SINGLE_SOURCE,
            readings=results,
        )
    outcomes = {r.in_favourable_set for r in results}
    if len(outcomes) > 1:
        return FavourableEvaluation(
            body=body,
            house_from_moon=house,
            status=FavourableStatus.NOT_EVALUABLE,
            reason_code=TransitReason.READING_AMBIGUOUS,
            readings=results,
        )
    inside = outcomes == {True}
    return FavourableEvaluation(
        body=body,
        house_from_moon=house,
        status=(
            FavourableStatus.IN_FAVOURABLE_SET if inside else FavourableStatus.NOT_IN_FAVOURABLE_SET
        ),
        readings=results,
        attesting_reading_ids=tuple(r.reading_id for r in results),
    )


# --------------------------------------------------------------------------
# Vedha (TR-06)
# --------------------------------------------------------------------------


def evaluate_vedha(
    subject: CelestialBody,
    house: int,
    moon_sign: int,
    signs_by_body: dict[CelestialBody, int],
) -> VedhaFact | None:
    """The Phaladeepika Vedha fact for `subject` in `house` from the natal Moon,
    or None if the source gives no Vedha pair for that house. Occupants are the
    *transiting* planets in the Vedha house's sign, excluding the subject and the
    exempt planet; nodes never decide the result on their own."""
    if subject in NODES:
        return VedhaFact(
            body=subject,
            house_from_moon=house,
            profile_id=VEDHA_PHALADEEPIKA_ID,
            status=SectionStatus.NOT_EVALUABLE,
            reason_code=TransitReason.NOT_SPECIFIED_BY_SOURCE,
        )
    pairs = VEDHA_PAIRS.get(subject, {})
    if house not in pairs:
        return None
    vedha_house = pairs[house]
    vedha_sign = (moon_sign + vedha_house - 1) % 12
    exempt = VEDHA_EXEMPT.get(subject, frozenset())
    in_sign = [b for b in ALL_BODIES if b != subject and signs_by_body[b] == vedha_sign]
    occupants = tuple(b for b in in_sign if b not in exempt and b not in NODES)
    exempt_occupants = tuple(b for b in in_sign if b in exempt)
    node_occupants = tuple(b for b in in_sign if b in NODES)
    warnings = (VENUS_VEDHA_ANOMALY_WARNING,) if subject == CelestialBody.VENUS else ()
    common = dict(
        body=subject,
        house_from_moon=house,
        profile_id=VEDHA_PHALADEEPIKA_ID,
        vedha_house=vedha_house,
        vedha_sign=rashi_from_index(vedha_sign),
        occupants=occupants,
        exempt_occupants=exempt_occupants,
        node_occupants=node_occupants,
        warnings=warnings,
    )
    if occupants:
        return VedhaFact(status=SectionStatus.AVAILABLE, vedha_present=True, **common)  # type: ignore[arg-type]
    if node_occupants:
        return VedhaFact(
            status=SectionStatus.NOT_EVALUABLE,
            reason_code=TransitReason.NODE_PARTICIPATION_UNSPECIFIED,
            **common,  # type: ignore[arg-type]
        )
    return VedhaFact(status=SectionStatus.AVAILABLE, vedha_present=False, **common)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Contacts (TR-07)
# --------------------------------------------------------------------------


def contacts_for(
    body: CelestialBody, sign_index: int, natal_signs: dict[CelestialBody, int]
) -> tuple[TransitContact, ...]:
    """Sign-based contacts of one transiting planet: same-sign conjunction and
    the Phase 5 graha drishti onto a natal planet's sign. No orb."""
    contacts: list[TransitContact] = []
    offsets = aspect_offsets(body)
    for natal_body in ALL_BODIES:
        if natal_body not in natal_signs:
            continue
        natal_sign = natal_signs[natal_body]
        if natal_sign == sign_index:
            contacts.append(
                TransitContact(
                    transit_body=body,
                    natal_body=natal_body,
                    kind=ContactKind.CONJUNCTION,
                    transit_sign=rashi_from_index(sign_index),
                    natal_sign=rashi_from_index(natal_sign),
                )
            )
        for offset in offsets:
            if (sign_index + offset - 1) % 12 == natal_sign:
                contacts.append(
                    TransitContact(
                        transit_body=body,
                        natal_body=natal_body,
                        kind=ContactKind.ASPECT,
                        aspect_house_offset=offset,
                        transit_sign=rashi_from_index(sign_index),
                        natal_sign=rashi_from_index(natal_sign),
                    )
                )
    return tuple(contacts)


# --------------------------------------------------------------------------
# Sade Sati state (TR-09)
# --------------------------------------------------------------------------


def sade_sati_phase(saturn_sign: int, moon_sign: int) -> int | None:
    return SADE_SATI_PHASE_BY_OFFSET.get((saturn_sign - moon_sign) % 12)


# --------------------------------------------------------------------------
# Snapshot
# --------------------------------------------------------------------------


def build_snapshot(
    provider: PositionProvider,
    julian_day_ut: float,
    at_utc: dt.datetime,
    config: TransitConfiguration,
    ctx: NatalContext,
) -> TransitSnapshot:
    positions = {body: provider.position(julian_day_ut, body) for body in ALL_BODIES}
    signs = {body: sign_of(pos.longitude) for body, pos in positions.items()}
    selected = tuple(dict.fromkeys(config.bodies))

    lagna_status = SectionStatus.NOT_REQUESTED
    lagna_reason: TransitReason | None = None
    if config.include_lagna_fact:
        if ctx.lagna_sign is None:
            lagna_status, lagna_reason = SectionStatus.NOT_EVALUABLE, ctx.lagna_reason
        else:
            lagna_status = SectionStatus.AVAILABLE

    states: list[BodyState] = []
    for body in selected:
        state = build_state(body, positions[body], ctx)
        if lagna_status == SectionStatus.AVAILABLE and ctx.lagna_sign is not None:
            state = state.model_copy(
                update={"house_from_lagna": house_from(signs[body], ctx.lagna_sign)}
            )
        states.append(state)

    favourable: list[FavourableEvaluation] = []
    vedha: list[VedhaFact] = []
    if ctx.moon_sign is None:
        moon_status, moon_reason = SectionStatus.NOT_EVALUABLE, ctx.moon_reason
    else:
        moon_status, moon_reason = SectionStatus.AVAILABLE, None
        for body in selected:
            house = house_from(signs[body], ctx.moon_sign)
            favourable.append(evaluate_favourable(body, house))
            if config.include_vedha:
                fact = evaluate_vedha(body, house, ctx.moon_sign, signs)
                if fact is not None:
                    vedha.append(fact)

    contacts_status = SectionStatus.NOT_REQUESTED
    contacts_reason: TransitReason | None = None
    contacts: list[TransitContact] = []
    if config.include_contacts:
        if ctx.natal_signs is None:
            contacts_status, contacts_reason = SectionStatus.NOT_EVALUABLE, ctx.planets_reason
        else:
            contacts_status = SectionStatus.AVAILABLE
            for body in selected:
                contacts.extend(contacts_for(body, signs[body], ctx.natal_signs))

    sade_sati: SadeSatiState | None = None
    if config.include_sade_sati and ctx.moon_sign is not None:
        phase = sade_sati_phase(signs[CelestialBody.SATURN], ctx.moon_sign)
        sade_sati = SadeSatiState(
            profile_id=config.sade_sati_profile_id or SADE_SATI_ID,
            in_band=phase is not None,
            phase=phase,
        )

    return TransitSnapshot(
        at_utc=at_utc,
        julian_day_ut=julian_day_ut,
        states=tuple(states),
        moon_relative_status=moon_status,
        moon_relative_reason=moon_reason,
        favourable=tuple(favourable),
        vedha=tuple(vedha),
        contacts_status=contacts_status,
        contacts_reason=contacts_reason,
        contacts=tuple(contacts),
        lagna_status=lagna_status,
        lagna_reason=lagna_reason,
        sade_sati=sade_sati,
    )
