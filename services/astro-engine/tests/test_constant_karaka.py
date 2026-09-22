"""Phase 9 WP-B-2: Constant Karaka (BPHS Ch. 32 v. 18-21)."""

from __future__ import annotations

from pandit_astro_engine.jaimini.constant_karaka import (
    ConstantKarakaReason,
    ConstantKarakaRelation,
    ConstantKarakaStatus,
    constant_karakas,
)
from pandit_astro_engine.models import CelestialBody


def test_five_direct_significations_match_bphs_exactly() -> None:
    by_relation = {s.relation: s for s in constant_karakas()}
    assert by_relation[ConstantKarakaRelation.SIBLING].body is CelestialBody.MERCURY
    assert by_relation[ConstantKarakaRelation.MATERNAL_RELATIVE].body is CelestialBody.MARS
    assert by_relation[ConstantKarakaRelation.PATERNAL_GRANDFATHER].body is CelestialBody.JUPITER
    assert by_relation[ConstantKarakaRelation.HUSBAND].body is CelestialBody.VENUS
    assert by_relation[ConstantKarakaRelation.SONS].body is CelestialBody.SATURN
    assert by_relation[ConstantKarakaRelation.KETU_GROUP].body is CelestialBody.KETU
    for relation in (
        ConstantKarakaRelation.SIBLING,
        ConstantKarakaRelation.MATERNAL_RELATIVE,
        ConstantKarakaRelation.PATERNAL_GRANDFATHER,
        ConstantKarakaRelation.HUSBAND,
        ConstantKarakaRelation.SONS,
        ConstantKarakaRelation.KETU_GROUP,
    ):
        assert by_relation[relation].status is ConstantKarakaStatus.SUCCESS
        assert by_relation[relation].reason_code is None


def test_father_and_mother_are_not_evaluable_strength_undefined() -> None:
    by_relation = {s.relation: s for s in constant_karakas()}
    for relation in (ConstantKarakaRelation.FATHER, ConstantKarakaRelation.MOTHER):
        entry = by_relation[relation]
        assert entry.status is ConstantKarakaStatus.NOT_EVALUABLE
        assert entry.reason_code is ConstantKarakaReason.STRENGTH_UNDEFINED
        assert entry.body is None


def test_returns_exactly_eight_entries_no_duplicates() -> None:
    entries = constant_karakas()
    assert len(entries) == 8
    assert len({e.relation for e in entries}) == 8


def test_deterministic_and_longitude_independent() -> None:
    # No chart input at all -- always the same eight entries.
    assert constant_karakas() == constant_karakas()
