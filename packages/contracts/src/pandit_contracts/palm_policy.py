"""Prohibited palmistry interpretation categories (Phase 13; standards PM-13 and PM-25).

Permanently prohibited, in any rule, knowledge statement, chunk, annotation label, training
target or narration input:

* medical diagnosis and disease claims, death prediction, lifespan prediction (owner decision J);
* criminality, mental illness or psychiatric diagnosis, fertility, paternity, sexual conduct,
  ethnic or racial ranking, intellectual superiority or inferiority, moral character labelling,
  and any claim that a person is inherently good or bad, pure or impure, trustworthy or
  untrustworthy based on palm features (final owner decision A, 2026-10-02);
* event prediction (Phase 13 rule scope: a rule never predicts an event).

The vision pipeline may detect a *physical feature* for a legitimate technical reason; this
module never prevents a visual fact, it prevents an **interpretation** or a **label** in a
prohibited category. It is a closed lexicon scan, a safety net that rejects obvious violations
at validation time. It does not prove a text is acceptable: the real enforcement is that
interpretation tags come from a closed, reviewed vocabulary (rule-engine ``tag_vocabulary``),
every rule cites one read source location, and the owner reviews each rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ProhibitedCategory(str, Enum):
    MEDICAL_DIAGNOSIS = "MEDICAL_DIAGNOSIS"
    DISEASE = "DISEASE"
    DEATH = "DEATH"
    LIFESPAN = "LIFESPAN"
    CRIMINALITY = "CRIMINALITY"
    MENTAL_ILLNESS = "MENTAL_ILLNESS"
    FERTILITY = "FERTILITY"
    PATERNITY = "PATERNITY"
    SEXUAL_CONDUCT = "SEXUAL_CONDUCT"
    ETHNIC_RACIAL_RANKING = "ETHNIC_RACIAL_RANKING"
    INTELLECTUAL_RANKING = "INTELLECTUAL_RANKING"
    MORAL_LABELLING = "MORAL_LABELLING"
    INHERENT_GOOD_BAD = "INHERENT_GOOD_BAD"
    EVENT_PREDICTION = "EVENT_PREDICTION"


# Word stems (matched at a word start, any continuation) and whole phrases. Lower case.
_LEXICON: dict[ProhibitedCategory, tuple[str, ...]] = {
    ProhibitedCategory.MEDICAL_DIAGNOSIS: (
        "diagnos",
        "medical",
        "symptom",
        "syndrome",
        "disorder",
        "prognos",
        "health",
        "unhealth",
        "constitution",
        "digestion",
        "liver",
    ),
    ProhibitedCategory.DISEASE: (
        "disease",
        "illness",
        "sickness",
        "malady",
        "ailment",
        "infirmity",
        "cancer",
        "diabet",
        "epilep",
        "apoplex",
        "palpitation",
        "fever",
        "blindness",
        "deafness",
        "neuralgia",
        "hereditary weakness",
    ),
    ProhibitedCategory.DEATH: (
        "death",
        "die",
        "dies",
        "dying",
        "died",
        "mortal",
        "fatal",
        "fatality",
        "suicid",
        "drown",
        "killed",
    ),
    ProhibitedCategory.LIFESPAN: (
        "lifespan",
        "life span",
        "longevity",
        "long life",
        "short life",
        "length of life",
        "life expectancy",
        "life length",
        "age at death",
    ),
    ProhibitedCategory.CRIMINALITY: (
        "crime",
        "criminal",
        "murder",
        "homicid",
        "theft",
        "thief",
        "steal",
        "scaffold",
        "felon",
        "offender",
        "delinquen",
        "assassin",
        "imprison",
        "violent",
        "violence",
    ),
    ProhibitedCategory.MENTAL_ILLNESS: (
        "madness",
        "insan",
        "lunac",
        "psychos",
        "psychot",
        "psychiatr",
        "schizo",
        "bipolar",
        "depress",
        "hysteri",
        "neuros",
        "mental illness",
        "mental disorder",
        "mental weakness",
        "melanchol",
        "hypochondri",
    ),
    ProhibitedCategory.FERTILITY: (
        "fertil",
        "sterile",
        "sterility",
        "barren",
        "infertil",
        "pregnan",
        "childbirth",
        "conceive",
        "conception",
        "maternity",
        "childless",
        "offspring",
        "progeny",
        "children",
    ),
    ProhibitedCategory.PATERNITY: (
        "paternity",
        "illegitima",
        "legitimacy",
        "bastard",
        "parentage",
        "mystery of birth",
        "birth mystery",
    ),
    ProhibitedCategory.SEXUAL_CONDUCT: (
        "sexual",
        "sensual",
        "adulter",
        "debauch",
        "lascivi",
        "promiscu",
        "lust",
        "libidin",
        "unchast",
        "infidel",
        "faithless",
        "prostitut",
        "licentious",
        "erotic",
    ),
    ProhibitedCategory.ETHNIC_RACIAL_RANKING: (
        "race",
        "racial",
        "racist",
        "ethnic",
        "ethnicity",
        "caste",
        "tribe",
        "savage",
        "primitive people",
        "superior race",
        "inferior race",
    ),
    ProhibitedCategory.INTELLECTUAL_RANKING: (
        "stupid",
        "idiot",
        "imbecil",
        "moron",
        "genius",
        "intellect",
        "intelligen",
        "clever",
        "feeble minded",
        "dull witted",
        "brilliant mind",
        "low mentality",
    ),
    ProhibitedCategory.MORAL_LABELLING: (
        "moral",
        "immoral",
        "evil",
        "wicked",
        "vice",
        "vicious",
        "virtue",
        "virtuous",
        "honest",
        "dishonest",
        "deceit",
        "deceiv",
        "treacher",
        "hypocri",
        "avaric",
        "cunning",
        "cruel",
        "brutal",
        "trustworth",
        "untrustworth",
        "impure",
        "pure",
        "noble",
        "ignoble",
        "selfish",
        "sinful",
        "righteous",
        "corrupt",
    ),
    ProhibitedCategory.INHERENT_GOOD_BAD: (
        "inherently good",
        "inherently bad",
        "born bad",
        "born evil",
        "born good",
        "good person",
        "bad person",
        "good man",
        "bad man",
        "evil person",
        "good character",
        "bad character",
        "good heart",
        "bad heart",
        "bad nature",
        "good nature",
    ),
    ProhibitedCategory.EVENT_PREDICTION: (
        "predict",
        "forecast",
        "foretell",
        "foretold",
        "foreshadow",
        "prophec",
        "will happen",
        "will occur",
        "will come to pass",
        "future event",
        "misfortune",
        "good luck",
        "bad luck",
    ),
}

_NORMALIZE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ProhibitedMatch:
    category: ProhibitedCategory
    term: str


def _normalize(text: str) -> str:
    """Lower case, with every non-alphanumeric run (including ``_`` and ``.``) a single space."""
    return " " + _NORMALIZE.sub(" ", text.lower()).strip() + " "


def find_prohibited(text: str) -> tuple[ProhibitedMatch, ...]:
    """Every lexicon match in ``text`` (empty when none). Stems match at a word start."""
    haystack = _normalize(text)
    matches: list[ProhibitedMatch] = []
    for category, terms in _LEXICON.items():
        for term in terms:
            if " " + term in haystack:
                matches.append(ProhibitedMatch(category, term))
    return tuple(matches)


def is_prohibited_label(label: str) -> bool:
    """True when an annotation or training label would be a prohibited category."""
    return bool(find_prohibited(label))


def prohibited_categories() -> tuple[ProhibitedCategory, ...]:
    return tuple(ProhibitedCategory)
