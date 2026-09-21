"""Pure transit evaluation: natal resolution, house counting, favourable readings,
Vedha, contacts and the snapshot (docs/ASTROLOGY_STANDARDS.md TR-02 to TR-07)."""

from __future__ import annotations

import pytest
from transit_helpers import JD0, T0, SyntheticProvider, config, linear, natal, static

from pandit_astro_engine.dashas.models import BirthTimeStatus
from pandit_astro_engine.models import CelestialBody as B
from pandit_astro_engine.rashi import Rashi
from pandit_astro_engine.transits import NatalReference
from pandit_astro_engine.transits import evaluate as E
from pandit_astro_engine.transits import profiles as P
from pandit_astro_engine.transits.models import (
    ContactKind,
    FavourableStatus,
    SectionStatus,
    TransitReason,
)


def sign_longitude(sign_index: int, degree: float = 10.0) -> float:
    return sign_index * 30.0 + degree


# --------------------------------------------------------------------------
# Natal resolution
# --------------------------------------------------------------------------


def test_exact_natal_moon_gives_its_sign() -> None:
    ctx = E.resolve_natal(natal(moon=sign_longitude(4)))
    assert ctx.moon_sign == 4 and ctx.moon_reason is None


def test_exact_without_moon_longitude_is_not_evaluable() -> None:
    ctx = E.resolve_natal(NatalReference(precision=BirthTimeStatus.EXACT))
    assert ctx.moon_sign is None and ctx.moon_reason == TransitReason.MOON_LONGITUDE_MISSING


def test_unknown_natal_time_is_never_guessed() -> None:
    ctx = E.resolve_natal(NatalReference(precision=BirthTimeStatus.NOT_EVALUABLE))
    assert ctx.moon_sign is None and ctx.moon_reason == TransitReason.NATAL_TIME_UNKNOWN


def test_approximate_requires_an_explicit_range() -> None:
    ctx = E.resolve_natal(NatalReference(precision=BirthTimeStatus.APPROXIMATE, moon_longitude=5))
    assert ctx.moon_sign is None and ctx.moon_reason == TransitReason.NATAL_RANGE_MISSING


def test_approximate_range_inside_one_sign_resolves() -> None:
    ref = NatalReference(
        precision=BirthTimeStatus.APPROXIMATE, moon_longitude_low=61.0, moon_longitude_high=88.0
    )
    assert E.resolve_natal(ref).moon_sign == 2


@pytest.mark.parametrize(
    ("low", "high"),
    [(29.0, 31.0), (59.999, 60.0), (350.0, 5.0), (10.0, 40.0), (0.0, 359.0)],
)
def test_approximate_range_reaching_a_sign_boundary_is_ambiguous(low: float, high: float) -> None:
    ref = NatalReference(
        precision=BirthTimeStatus.APPROXIMATE, moon_longitude_low=low, moon_longitude_high=high
    )
    ctx = E.resolve_natal(ref)
    assert ctx.moon_sign is None
    assert ctx.moon_reason == TransitReason.NATAL_MOON_SIGN_AMBIGUOUS


def test_approximate_natal_never_provides_lagna_or_planets() -> None:
    ref = NatalReference(
        precision=BirthTimeStatus.APPROXIMATE,
        moon_longitude_low=61.0,
        moon_longitude_high=70.0,
        lagna_longitude=10.0,
        natal_planets={B.SUN: 12.0},
    )
    ctx = E.resolve_natal(ref)
    assert ctx.lagna_sign is None and ctx.lagna_reason == TransitReason.LAGNA_UNAVAILABLE
    assert ctx.natal_signs is None
    assert ctx.planets_reason == TransitReason.NATAL_PLANETS_UNAVAILABLE


def test_house_counting_is_whole_sign_with_the_reference_as_first() -> None:
    assert E.house_from(4, 4) == 1
    assert E.house_from(5, 4) == 2
    assert E.house_from(3, 4) == 12
    assert E.house_from(0, 11) == 2


def test_range_helpers_wrap_around_zero() -> None:
    assert E.moon_range_width(350.0, 5.0) == pytest.approx(15.0)
    assert E.value_in_range(2.0, 350.0, 5.0)
    assert not E.value_in_range(200.0, 350.0, 5.0)


# --------------------------------------------------------------------------
# Favourable-set readings
# --------------------------------------------------------------------------


@pytest.mark.parametrize("house", range(1, 13))
def test_non_moon_planets_are_never_ambiguous(house: int) -> None:
    for body in (B.SUN, B.MARS, B.MERCURY, B.JUPITER, B.VENUS, B.SATURN):
        result = E.evaluate_favourable(body, house)
        assert result.status != FavourableStatus.NOT_EVALUABLE
        assert len(result.readings) == 4
        assert result.attesting_reading_ids == P.FAVOURABLE_READING_IDS


def test_non_moon_membership_matches_the_agreed_sets() -> None:
    assert E.evaluate_favourable(B.SUN, 3).status == FavourableStatus.IN_FAVOURABLE_SET
    assert E.evaluate_favourable(B.SUN, 4).status == FavourableStatus.NOT_IN_FAVOURABLE_SET
    assert E.evaluate_favourable(B.VENUS, 12).status == FavourableStatus.IN_FAVOURABLE_SET
    assert E.evaluate_favourable(B.VENUS, 7).status == FavourableStatus.NOT_IN_FAVOURABLE_SET


@pytest.mark.parametrize("house", [5, 6, 9])
def test_moon_from_moon_conflict_houses_are_not_evaluable_with_every_reading(house: int) -> None:
    result = E.evaluate_favourable(B.MOON, house)
    assert result.status == FavourableStatus.NOT_EVALUABLE
    assert result.reason_code == TransitReason.READING_AMBIGUOUS
    assert len(result.readings) == 4
    assert {r.in_favourable_set for r in result.readings} == {True, False}
    assert result.attesting_reading_ids == ()


@pytest.mark.parametrize("house", [1, 3, 7, 10, 11])
def test_moon_houses_in_every_reading_are_in_the_set(house: int) -> None:
    result = E.evaluate_favourable(B.MOON, house)
    assert result.status == FavourableStatus.IN_FAVOURABLE_SET
    assert result.attesting_reading_ids == P.FAVOURABLE_READING_IDS


@pytest.mark.parametrize("house", [2, 4, 8, 12])
def test_moon_houses_in_no_reading_are_not_in_the_set(house: int) -> None:
    assert E.evaluate_favourable(B.MOON, house).status == FavourableStatus.NOT_IN_FAVOURABLE_SET


@pytest.mark.parametrize("node", [B.RAHU, B.KETU])
def test_nodes_are_single_source_and_never_consolidated(node: B) -> None:
    for house in range(1, 13):
        result = E.evaluate_favourable(node, house)
        assert result.status == FavourableStatus.NOT_EVALUABLE
        assert result.reason_code == TransitReason.NODE_READING_SINGLE_SOURCE
        assert [r.reading_id for r in result.readings] == [P.FAV_PHALADEEPIKA_ID]
        assert result.readings[0].single_source is True
    assert E.evaluate_favourable(node, 3).readings[0].in_favourable_set is True
    assert E.evaluate_favourable(node, 4).readings[0].in_favourable_set is False


def test_reading_results_carry_labels_and_levels() -> None:
    result = E.evaluate_favourable(B.SUN, 3)
    labels = {r.reading_id: r.label for r in result.readings}
    assert labels[P.FAV_BPHS_DERIVED_ID] == P.EvidenceLabel.DERIVED_CALCULATION
    assert all(r.verification_level for r in result.readings)


# --------------------------------------------------------------------------
# Vedha
# --------------------------------------------------------------------------


def signs(**by_name: int) -> dict[B, int]:
    """All nine bodies in sign 0 unless overridden (keys are body values)."""
    result = {body: 0 for body in B}
    for name, sign in by_name.items():
        result[B(name)] = sign
    return result


def test_vedha_absent_when_the_vedha_sign_is_empty() -> None:
    # Moon sign 0; Sun in house 3 (sign 2) -> Vedha house 9 = sign 8, empty.
    fact = E.evaluate_vedha(B.SUN, 3, 0, signs(sun=2, moon=0))
    assert fact is not None
    assert fact.status == SectionStatus.AVAILABLE and fact.vedha_present is False
    assert fact.vedha_house == 9 and fact.vedha_sign == Rashi.SAGITTARIUS
    assert fact.occupants == ()


def test_vedha_present_when_another_planet_occupies_the_vedha_sign() -> None:
    fact = E.evaluate_vedha(B.SUN, 3, 0, signs(sun=2, mars=8))
    assert fact is not None and fact.vedha_present is True
    assert fact.occupants == (B.MARS,)


def test_saturn_does_not_obstruct_the_sun_and_the_sun_does_not_obstruct_saturn() -> None:
    sun = E.evaluate_vedha(B.SUN, 3, 0, signs(sun=2, saturn=8))
    assert sun is not None and sun.vedha_present is False
    assert sun.exempt_occupants == (B.SATURN,) and sun.occupants == ()
    saturn = E.evaluate_vedha(B.SATURN, 3, 0, signs(saturn=2, sun=11))  # house 12 = sign 11
    assert saturn is not None and saturn.vedha_present is False
    assert saturn.exempt_occupants == (B.SUN,)


def test_moon_and_mercury_do_not_obstruct_each_other() -> None:
    moon = E.evaluate_vedha(B.MOON, 7, 0, signs(moon=6, mercury=1))  # house 2 = sign 1
    assert moon is not None and moon.vedha_present is False
    mercury = E.evaluate_vedha(B.MERCURY, 2, 0, signs(mercury=1, moon=4))  # house 5 = sign 4
    assert mercury is not None and mercury.vedha_present is False


def test_other_planets_do_obstruct_mars_and_jupiter() -> None:
    mars = E.evaluate_vedha(B.MARS, 3, 0, signs(mars=2, sun=11))  # house 12 = sign 11
    assert mars is not None and mars.vedha_present is True and mars.occupants == (B.SUN,)
    jupiter = E.evaluate_vedha(B.JUPITER, 2, 0, signs(jupiter=1, saturn=11))
    assert jupiter is not None and jupiter.vedha_present is True


def test_the_subject_itself_is_never_its_own_occupant() -> None:
    # Sun in house 3 cannot sit in its own Vedha sign (house 9); use house counting anyway.
    fact = E.evaluate_vedha(B.SUN, 3, 0, signs(sun=2))
    assert fact is not None and B.SUN not in fact.occupants


def test_no_vedha_pair_gives_no_fact() -> None:
    assert E.evaluate_vedha(B.SUN, 4, 0, signs()) is None  # house 4 is not in the Sun's table


def test_node_alone_in_the_vedha_sign_is_not_evaluable() -> None:
    fact = E.evaluate_vedha(B.SUN, 3, 0, signs(sun=2, rahu=8))
    assert fact is not None
    assert fact.status == SectionStatus.NOT_EVALUABLE
    assert fact.reason_code == TransitReason.NODE_PARTICIPATION_UNSPECIFIED
    assert fact.vedha_present is None and fact.node_occupants == (B.RAHU,)


def test_node_does_not_change_an_already_present_vedha() -> None:
    fact = E.evaluate_vedha(B.SUN, 3, 0, signs(sun=2, mars=8, ketu=8))
    assert fact is not None and fact.vedha_present is True
    assert fact.node_occupants == (B.KETU,) and fact.status == SectionStatus.AVAILABLE


@pytest.mark.parametrize("node", [B.RAHU, B.KETU])
def test_node_subject_vedha_is_not_specified_by_source(node: B) -> None:
    fact = E.evaluate_vedha(node, 3, 0, signs())
    assert fact is not None
    assert fact.status == SectionStatus.NOT_EVALUABLE
    assert fact.reason_code == TransitReason.NOT_SPECIFIED_BY_SOURCE


def test_venus_vedha_always_carries_the_translation_anomaly_warning() -> None:
    fact = E.evaluate_vedha(B.VENUS, 2, 0, signs(venus=1))
    assert fact is not None and P.VENUS_VEDHA_ANOMALY_WARNING in fact.warnings
    other = E.evaluate_vedha(B.SUN, 3, 0, signs(sun=2))
    assert other is not None and other.warnings == ()


def test_vedha_uses_the_natal_moon_as_house_one() -> None:
    # Moon sign 5: Sun in house 3 = sign 7; Vedha house 9 = sign (5+8)%12 = 1.
    fact = E.evaluate_vedha(B.SUN, 3, 5, signs(sun=7, mars=1))
    assert fact is not None and fact.vedha_sign == Rashi.TAURUS and fact.vedha_present is True


# --------------------------------------------------------------------------
# Contacts
# --------------------------------------------------------------------------


def test_same_sign_is_a_conjunction_and_carries_both_signs() -> None:
    contacts = E.contacts_for(B.SUN, 4, {B.MOON: 4})
    assert [(c.kind, c.natal_body) for c in contacts] == [(ContactKind.CONJUNCTION, B.MOON)]


def test_universal_seventh_aspect() -> None:
    contacts = E.contacts_for(B.MERCURY, 0, {B.MOON: 6})
    assert len(contacts) == 1
    assert contacts[0].kind == ContactKind.ASPECT and contacts[0].aspect_house_offset == 7


@pytest.mark.parametrize(
    ("body", "offset"),
    [(B.MARS, 4), (B.MARS, 8), (B.JUPITER, 5), (B.JUPITER, 9), (B.SATURN, 3), (B.SATURN, 10)],
)
def test_special_aspects_use_the_phase_5_offsets(body: B, offset: int) -> None:
    target = (0 + offset - 1) % 12
    contacts = E.contacts_for(body, 0, {B.SUN: target})
    assert [c.aspect_house_offset for c in contacts] == [offset]


@pytest.mark.parametrize("node", [B.RAHU, B.KETU])
def test_nodes_cast_only_the_seventh_aspect(node: B) -> None:
    natal_signs = {B.SUN: 2, B.MOON: 4, B.MARS: 3, B.SATURN: 6}
    contacts = E.contacts_for(node, 0, natal_signs)
    assert {c.aspect_house_offset for c in contacts} == {7}
    assert [c.natal_body for c in contacts] == [B.SATURN]


def test_no_orb_or_degree_facts_exist_on_a_contact() -> None:
    fields = set(E.contacts_for(B.SUN, 0, {B.MOON: 0})[0].model_dump())
    assert fields == {
        "transit_body",
        "natal_body",
        "kind",
        "aspect_house_offset",
        "transit_sign",
        "natal_sign",
    }


def test_contacts_are_deterministically_ordered() -> None:
    natal_signs = {B.SATURN: 6, B.SUN: 0, B.MOON: 0}
    first = E.contacts_for(B.MARS, 0, natal_signs)
    assert first == E.contacts_for(B.MARS, 0, natal_signs)
    # Natal bodies are visited in the fixed body order (Sun, Moon, ..., Saturn), not dict order.
    assert [(c.natal_body, c.kind) for c in first] == [
        (B.SUN, ContactKind.CONJUNCTION),
        (B.MOON, ContactKind.CONJUNCTION),
        (B.SATURN, ContactKind.ASPECT),
    ]


# --------------------------------------------------------------------------
# Sade Sati state
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("saturn", "moon", "phase"),
    [(10, 11, 1), (11, 11, 2), (0, 11, 3), (1, 11, None), (9, 11, None), (5, 5, 2), (4, 5, 1)],
)
def test_sade_sati_phase_is_a_sign_offset(saturn: int, moon: int, phase: int | None) -> None:
    assert E.sade_sati_phase(saturn, moon) == phase


# --------------------------------------------------------------------------
# Snapshot
# --------------------------------------------------------------------------


def make_provider(**by_name: float) -> SyntheticProvider:
    return SyntheticProvider({B(name): static(lon) for name, lon in by_name.items()})


def snapshot(provider: SyntheticProvider, natal_ref: NatalReference, **cfg: object):  # type: ignore[no-untyped-def]
    ctx = E.resolve_natal(natal_ref)
    return E.build_snapshot(provider, JD0, T0, config(**cfg), ctx)


def test_snapshot_reports_houses_from_the_natal_moon() -> None:
    provider = make_provider(sun=sign_longitude(6), moon=sign_longitude(2))
    snap = snapshot(provider, natal(moon=sign_longitude(0)))
    sun = next(s for s in snap.states if s.body == B.SUN)
    assert sun.sign == Rashi.LIBRA and sun.house_from_moon == 7
    assert snap.moon_relative_status == SectionStatus.AVAILABLE
    assert len(snap.favourable) == 9


def test_snapshot_moon_relative_facts_are_withheld_for_an_ambiguous_natal_moon() -> None:
    ref = NatalReference(
        precision=BirthTimeStatus.APPROXIMATE, moon_longitude_low=29.0, moon_longitude_high=31.0
    )
    snap = snapshot(make_provider(), ref)
    assert snap.moon_relative_status == SectionStatus.NOT_EVALUABLE
    assert snap.moon_relative_reason == TransitReason.NATAL_MOON_SIGN_AMBIGUOUS
    assert snap.favourable == () and snap.vedha == ()
    assert all(state.house_from_moon is None for state in snap.states)
    assert len(snap.states) == 9  # positions never depend on the natal chart


def test_snapshot_lagna_fact_is_opt_in_and_an_engineering_convention() -> None:
    provider = make_provider(sun=sign_longitude(5))
    off = snapshot(provider, natal(lagna=sign_longitude(2)))
    assert off.lagna_status == SectionStatus.NOT_REQUESTED
    assert all(s.house_from_lagna is None for s in off.states)
    on = snapshot(provider, natal(lagna=sign_longitude(2)), include_lagna_fact=True)
    assert on.lagna_status == SectionStatus.AVAILABLE
    sun = next(s for s in on.states if s.body == B.SUN)
    assert sun.house_from_lagna == 4  # sign 5 counted from sign 2
    assert on.favourable == snapshot(provider, natal(lagna=sign_longitude(2))).favourable


def test_snapshot_lagna_unavailable_without_a_lagna() -> None:
    snap = snapshot(make_provider(), natal(lagna=None), include_lagna_fact=True)
    assert snap.lagna_status == SectionStatus.NOT_EVALUABLE
    assert snap.lagna_reason == TransitReason.LAGNA_UNAVAILABLE


def test_snapshot_contacts_need_natal_planets() -> None:
    ref = NatalReference(precision=BirthTimeStatus.EXACT, moon_longitude=15.0)
    snap = snapshot(make_provider(), ref)
    assert snap.contacts_status == SectionStatus.NOT_EVALUABLE
    assert snap.contacts_reason == TransitReason.NATAL_PLANETS_UNAVAILABLE


def test_snapshot_contacts_are_sign_based_facts() -> None:
    provider = make_provider(sun=sign_longitude(4))
    snap = snapshot(provider, natal(planets={B.JUPITER: sign_longitude(4)}))
    assert any(
        c.transit_body == B.SUN and c.natal_body == B.JUPITER and c.kind == ContactKind.CONJUNCTION
        for c in snap.contacts
    )


def test_snapshot_vedha_flag_can_be_turned_off() -> None:
    provider = make_provider(sun=sign_longitude(2))
    assert snapshot(provider, natal(moon=1.0)).vedha
    assert snapshot(provider, natal(moon=1.0), include_vedha=False).vedha == ()


def test_snapshot_states_follow_the_requested_bodies_but_vedha_sees_all_nine() -> None:
    # Moon at sign 0. Sun (requested) in house 3 = sign 2; Mars (NOT requested) sits in the
    # Vedha sign (house 9 = sign 8): the Vedha fact must still see it.
    provider = make_provider(sun=sign_longitude(2), mars=sign_longitude(8))
    snap = snapshot(provider, natal(moon=1.0), bodies=(B.SUN,))
    assert [s.body for s in snap.states] == [B.SUN]
    sun_vedha = next(f for f in snap.vedha if f.body == B.SUN)
    assert sun_vedha.vedha_present is True and sun_vedha.occupants == (B.MARS,)


def test_snapshot_sade_sati_state_only_when_requested() -> None:
    provider = make_provider(saturn=sign_longitude(11))
    assert snapshot(provider, natal(moon=sign_longitude(11))).sade_sati is None
    state = snapshot(provider, natal(moon=sign_longitude(11)), include_sade_sati=True).sade_sati
    assert state is not None and state.in_band and state.phase == 2
    assert state.profile_id == P.SADE_SATI_ID


def test_snapshot_states_carry_nakshatra_pada_speed_and_retrograde() -> None:
    provider = SyntheticProvider({B.SATURN: linear(340.5, -0.05)})
    snap = snapshot(provider, natal())
    saturn = next(s for s in snap.states if s.body == B.SATURN)
    assert saturn.retrograde is True and saturn.speed_longitude == -0.05
    assert saturn.sign == Rashi.PISCES and saturn.pada in (1, 2, 3, 4)
    assert saturn.degree_in_sign == pytest.approx(10.5)
