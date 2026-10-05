"""The closed-vocabulary text analyzer (Phase 16). It reports what it recognised, no more."""

from __future__ import annotations

from pandit_verification.text import alnum_only, analyze, normalize


def test_placements_bind_to_the_nearest_preceding_planet() -> None:
    a = analyze("Mars is in Aries and Venus is in Libra in the seventh house.")
    assert a.bindings["mars"].signs == {"aries"}
    assert a.bindings["venus"].signs == {"libra"}
    assert a.bindings["venus"].houses == {7}
    assert a.bindings["mars"].houses == set()


def test_sentences_do_not_leak_bindings() -> None:
    a = analyze("Mars is in Aries. Leo is rising.")
    assert a.bindings["mars"].signs == {"aries"}
    assert a.unbound_signs == {"leo"}


def test_house_forms_numbers_and_ordinals() -> None:
    assert analyze("Mars in the 10th house").houses == {10}
    assert analyze("Mars in house 4").houses == {4}
    assert analyze("Mars in the twelfth house").houses == {12}
    assert analyze("Mars in the 13th house").houses == set()  # not a house
    assert "13" in analyze("Mars in the 13th house").numbers


def test_retrograde_and_dignity() -> None:
    assert analyze("Saturn is retrograde").bindings["saturn"].retrograde == {True}
    assert analyze("Saturn is not retrograde").bindings["saturn"].retrograde == {False}
    assert analyze("Saturn is direct").bindings["saturn"].retrograde == {False}
    assert analyze("Sun is exalted").bindings["sun"].dignities == {"exalted"}
    assert analyze("Mars in its own sign").bindings["mars"].dignities == {"own_sign"}


def test_palm_entities() -> None:
    a = analyze("The left hand shows the life line near the mount of Jupiter.")
    assert a.hands == {"LEFT"} and a.lines == {"life"} and a.mounts == {"jupiter"}
    b = analyze("The Venus mount and the line of fate on the right palm")
    assert b.mounts == {"venus"} and b.lines == {"fate"} and b.hands == {"RIGHT"}


def test_the_word_the_before_mount_is_not_a_mount() -> None:
    assert analyze("the mount of Saturn").mounts == {"saturn"}


def test_topics_valence_certainty_and_framing() -> None:
    a = analyze("Tradition reads this as favourable for career and marriage.")
    assert a.topics == {"career", "marriage"} and a.positive and a.framed and not a.negative
    assert analyze("This will definitely happen.").certainty
    assert analyze("You will become rich.").certainty
    assert not analyze("Mars is in Aries.").framed
    assert analyze("It is challenging.").negative


def test_class_language() -> None:
    assert analyze("It was observed in the image.").observation_language
    assert analyze("It was derived from landmarks.").derivation_language


def test_devanagari_words_stay_whole() -> None:
    a = analyze("मंगल मेष राशि में है")
    assert a.planets == {"mars"} and a.signs == {"aries"}


def test_unrecognised_text_is_reported_as_unread() -> None:
    a = analyze("Something happened with the moonlit river.")
    assert a.checkable_atoms == 0 and a.coverage_bp < 3000


def test_normalisation_helpers() -> None:
    assert normalize("  Heron-Allen  Says ") == "heron-allen says"
    assert alnum_only("Heron-Allen") == "heronallen"
