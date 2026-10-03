from __future__ import annotations

import pytest

from pandit_contracts.palm_policy import (
    ProhibitedCategory,
    find_prohibited,
    is_prohibited_label,
    prohibited_categories,
)

# One representative phrase per category: the lexicon must catch each.
SAMPLES: dict[ProhibitedCategory, str] = {
    ProhibitedCategory.MEDICAL_DIAGNOSIS: "indicates a medical diagnosis",
    ProhibitedCategory.DISEASE: "a sign of disease",
    ProhibitedCategory.DEATH: "foreshadows sudden death",
    ProhibitedCategory.LIFESPAN: "a short life line",
    ProhibitedCategory.CRIMINALITY: "criminal propensity",
    ProhibitedCategory.MENTAL_ILLNESS: "danger of madness",
    ProhibitedCategory.FERTILITY: "sterility of the subject",
    ProhibitedCategory.PATERNITY: "doubtful paternity",
    ProhibitedCategory.SEXUAL_CONDUCT: "debauchery and adultery",
    ProhibitedCategory.ETHNIC_RACIAL_RANKING: "a racial ranking",
    ProhibitedCategory.INTELLECTUAL_RANKING: "feeble intellect",
    ProhibitedCategory.MORAL_LABELLING: "a dishonest character",
    ProhibitedCategory.INHERENT_GOOD_BAD: "an inherently bad person",
    ProhibitedCategory.EVENT_PREDICTION: "will happen in the future",
}


def test_every_category_has_a_sample() -> None:
    assert set(SAMPLES) == set(prohibited_categories())
    assert len(prohibited_categories()) == 14  # the 13 named categories plus event prediction


@pytest.mark.parametrize("category", list(SAMPLES))
def test_each_category_is_caught(category: ProhibitedCategory) -> None:
    found = {m.category for m in find_prohibited(SAMPLES[category])}
    assert category in found, SAMPLES[category]


@pytest.mark.parametrize(
    "tag",
    [
        "AMBITION_INDICATED",
        "FORTUNE_FROM_PERSONAL_MERIT",
        "LEFT_HAND_INHERITED_TENDENCIES",
        "RIGHT_HAND_DEVELOPED_QUALITIES",
        "LEFT_HAND_NATURAL_MAP",
        "LINE_TRACK",
        "HAND_SIDE",
        "PALM_REGION",
    ],
)
def test_neutral_tags_and_visual_labels_are_not_flagged(tag: str) -> None:
    assert find_prohibited(tag) == ()
    assert not is_prohibited_label(tag)


@pytest.mark.parametrize(
    "label",
    ["DISEASE_RISK", "LIFESPAN_SHORT", "CRIMINAL_TENDENCY", "FERTILITY_SCORE", "MORAL_CHARACTER"],
)
def test_prohibited_training_and_annotation_labels_are_rejected(label: str) -> None:
    assert is_prohibited_label(label)


def test_underscores_and_case_do_not_hide_a_term() -> None:
    assert find_prohibited("DEATH_PREDICTION")
    assert find_prohibited("Sudden-Death")


def test_stems_match_at_a_word_start_only() -> None:
    assert find_prohibited("trace of a line") == ()  # not "race"
    assert find_prohibited("a device") == ()  # not "vice"
