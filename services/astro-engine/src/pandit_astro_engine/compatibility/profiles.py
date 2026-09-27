"""Compatibility source references and provenance (Phase 11;
`docs/ASTROLOGY_STANDARDS.md` v1.25.0; `research/ASTROLOGY_SOURCES.md` Group 24).

Verification levels are stated per statement. Nothing in either profile is
verified at Sanskrit level by a qualified reviewer.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine.compatibility.constants import CompatibilityProfileId


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLabel(str, Enum):
    """Same vocabulary as the other phase modules' own copies."""

    SOURCE_SUPPORTED = "source_supported"
    TRANSLATOR_NOTE = "translator_note"
    INFERENCE = "inference"
    ENGINEERING_CONVENTION = "engineering_convention"
    DERIVED_CALCULATION = "derived_calculation"
    UNRESOLVED_CONFLICT = "unresolved_conflict"
    MODERN_TRADITION = "modern_tradition"
    ENGINEERING_EVIDENCE = "engineering_evidence"
    #: A classical commentary quoting an older authority (here the
    #: Piyushadhara quoting the Daivajna Manohara), or a modern commentator's
    #: printed table.
    COMMENTARY = "commentary"
    PRODUCT_POLICY = "product_policy"


class SourceReference(_Model):
    source_id: str
    locator: str
    verification_level: str
    note: str = ""


class ProvenanceDef(_Model):
    entry_id: str
    item: str
    label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...]


MC_MAHIDHARA = "SRC-MUHURTA-CHINTAMANI-KHEMRAJ-MAHIDHARA"
MC_PIYUSHADHARA = "SRC-MUHURTA-CHINTAMANI-NIRNAYASAGAR-PIYUSHADHARA"
KALAPRAKASIKA = "SRC-KALAPRAKASIKA-IYER-1917"
BPHS_PHASE6 = "PANDIT-JI-PHASE6-RELATIONSHIPS"

_OCR_SA = "OCR-SOURCE-LANGUAGE (unreviewed)"
_IMG_SA = "IMAGE-SOURCE-LANGUAGE (unreviewed)"


def _mc(locator: str, level: str = _OCR_SA, note: str = "") -> SourceReference:
    return SourceReference(
        source_id=MC_MAHIDHARA, locator=locator, verification_level=level, note=note
    )


def _py(locator: str, note: str = "") -> SourceReference:
    return SourceReference(
        source_id=MC_PIYUSHADHARA, locator=locator, verification_level=_OCR_SA, note=note
    )


def _kp(locator: str, level: str = "IMAGE-TRANSLATION", note: str = "") -> SourceReference:
    return SourceReference(
        source_id=KALAPRAKASIKA, locator=locator, verification_level=level, note=note
    )


_POLICY = ProvenanceDef(
    entry_id="prov.policy",
    item="Product policy",
    label=EvidenceLabel.PRODUCT_POLICY,
    statement=(
        "No gender or role is collected, inferred or assumed; factors the source judges from "
        "a named partner are not evaluable unless both assignments give the same result. "
        "Matching is refused when either person is under 18 on the caller's date. No overall "
        "compatible/incompatible verdict and no statement of effect is produced."
    ),
    references=(),
)

ASHTAKOOT_PROVENANCE: tuple[ProvenanceDef, ...] = (
    _POLICY,
    ProvenanceDef(
        entry_id="prov.ak.kutas",
        item="The eight kutas and their weights",
        label=EvidenceLabel.COMMENTARY,
        statement=(
            "Verse 21 names Varna, Vashya, Tara, Yoni, Graha Maitri, Gana, Bhakoot and Nadi, "
            "'each greater in gunas'; the Piyushadhara reads this as 1 to 8 gunas (36 in all) "
            "and quotes the Daivajna Manohara for the same allocation."
        ),
        references=(
            _mc("Vivaha Prakarana v. 21, printed p. 81"),
            _py("Vivaha Prakarana v. 21 commentary, printed p. 245"),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.ak.varna",
        item="Varna",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "Cancer, Scorpio, Pisces Brahmin; Aries, Leo, Sagittarius Kshatriya; Taurus, Virgo, "
            "Capricorn Vaishya; Gemini, Libra, Aquarius Shudra (v. 22). One guna when the "
            "groom's varna is equal or higher (Daivajna Manohara; the printed table agrees). "
            "Some authorities give half a guna for equal varnas (reported, not in this profile)."
        ),
        references=(
            _mc("v. 22, p. 81; varna table, p. 85", _IMG_SA),
            _py("v. 22 commentary, p. 245"),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.ak.vashya",
        item="Vashya",
        label=EvidenceLabel.UNRESOLVED_CONFLICT,
        statement=(
            "Verse 23 states only that every sign except Leo is vashya to the human signs, the "
            "water signs are their food, and every sign except Scorpio is vashya to Leo; the "
            "rest is 'to be known from worldly usage'. The Daivajna Manohara's point scheme, "
            "Mahidhara's text (2 when the bride's sign is vashya to the groom's) and Mahidhara's "
            "five-class table disagree, and no source read maps every sign to a class."
        ),
        references=(
            _mc("v. 23, p. 81; vashya table, p. 85", _IMG_SA),
            _py("v. 23 commentary, pp. 245-246"),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.ak.tara",
        item="Tara Kuta (not the Phase 10 Tara Bala)",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "Count from each partner's nakshatra to the other's; the remainder by nine is "
            "unfavourable when 3, 5 or 7 (v. 24). 3 gunas when both counts are favourable, 1.5 "
            "when one is, 0 when neither (Daivajna Manohara; Mahidhara's Tara table agrees). "
            "Both directions are counted, so no role is needed."
        ),
        references=(
            _mc("v. 24, p. 81; Tara table, p. 86", _IMG_SA),
            _py("v. 24 commentary, p. 246"),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.ak.yoni",
        item="Yoni",
        label=EvidenceLabel.COMMENTARY,
        statement=(
            "The fourteen yonis of the nakshatras and the seven great enmities (v. 25-26): "
            "horse-buffalo, lion-elephant, sheep-monkey, mongoose-serpent, deer-dog, cat-rat, "
            "tiger-cow. 4 gunas for the same yoni, 0 for a great enmity; other pairs take "
            "Mahidhara's printed Yoni table where it is symmetric and are not evaluable where "
            "its two cells differ."
        ),
        references=(
            _mc("v. 25-26, pp. 81-82; Yoni table, p. 86", _IMG_SA),
            _py("v. 25-26 commentary, pp. 247-248"),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.ak.graha_maitri",
        item="Graha Maitri",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "The friendships of v. 27-28, identical to the locked Phase 6 BPHS Ch. 3 v. 55 "
            "table (reused, not redefined). 5 gunas for the same lord or mutual friends, 4 "
            "friend-neutral, 3 neutral-neutral, 1 friend-enemy, 0.5 neutral-enemy, 0 mutual "
            "enemies (Daivajna Manohara). Mahidhara's printed table gives 3 for Sun-Mercury, "
            "against the rule and his own text (4); the rule is followed and the slip recorded."
        ),
        references=(
            _mc("v. 27-28, p. 82; Graha Maitri table, p. 87", _IMG_SA),
            _py("v. 27-28 commentary, p. 249"),
            SourceReference(
                source_id=BPHS_PHASE6,
                locator="services/knowledge/rules/bphs/tables/relationships_natural_3_55.yaml",
                verification_level="IMAGE-TRANSLATION",
            ),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.ak.gana",
        item="Gana",
        label=EvidenceLabel.UNRESOLVED_CONFLICT,
        statement=(
            "Deva, Manushya and Rakshasa nakshatras (v. 29-30). 6 gunas for the same gana. "
            "Mixed ganas are scored by the partner's role, and the Daivajna Manohara quote, "
            "Mahidhara's text and Mahidhara's table disagree on those cells."
        ),
        references=(
            _mc("v. 29-30, p. 83; Gana table, p. 86", _IMG_SA),
            _py("v. 29-30 commentary, pp. 249-250"),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.ak.bhakoot",
        item="Bhakoot",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "Moon signs 6/8, 5/9 or 2/12 from each other are unfavourable, others favourable "
            "(v. 31); 7 gunas or 0 (Daivajna Manohara; Mahidhara's Bhakoot table). The "
            "cancellations of v. 32-33 are reported as conditions only: the commentators "
            "dispute how they combine, and the Piyushadhara ends by deferring to local custom."
        ),
        references=(
            _mc("v. 31-33, pp. 83-84; Bhakoot table, p. 87", _IMG_SA),
            _py("v. 31-33 commentary, pp. 251-256"),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.ak.nadi",
        item="Nadi Kuta (not the Phase 9 Nadi Astrology)",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "Three nadis of nine nakshatras each (v. 34). 8 gunas for different nadis, 0 for "
            "the same (Mahidhara's Nadi table). Verse 37: with the same Moon sign and different "
            "nakshatras, the same nakshatra and different signs, or the same nakshatra and "
            "different padas, there is no Nadi or Gana dosha. Regional four- and five-nadi "
            "schemes are not implemented."
        ),
        references=(
            _mc("v. 34, pp. 84-85; v. 37, p. 88; Nadi table, p. 87", _IMG_SA),
            _py(
                "v. 32 commentary, pp. 252-253 (nadi purity required in every cancellation)",
                "The Piyushadhara's own commentary on v. 34 was not read.",
            ),
        ),
    ),
)

TEN_PORUTHAM_PROVENANCE: tuple[ProvenanceDef, ...] = (
    _POLICY,
    ProvenanceDef(
        entry_id="prov.tp.overview",
        item="The ten considerations",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "Dhinam, Ganam, Mahendhram, Sthree-Dheergham, Yoni, Rasi, Rasyadhipathi, Vasyam, "
            "Rajju and Vedhai, judged as agreement or disagreement; the source gives no points. "
            "Its statement that at least five should agree is provenance, not a verdict."
        ),
        references=(_kp("Ch. XIII, printed pp. 69 and 76"),),
    ),
    ProvenanceDef(
        entry_id="prov.tp.role",
        item="Role-dependent considerations",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "Dhinam, Mahendhram and Sthree-Dheergham are counted from the bride's nakshatra to "
            "the groom's, and most Rasi and mixed-Ganam rules name the groom's position: they "
            "are not evaluable without a role."
        ),
        references=(
            _kp("Ch. XIII pp. 69-70", "OCR-TRANSLATION"),
            _kp("Ch. XIII pp. 72-74"),
        ),
    ),
    ProvenanceDef(
        entry_id="prov.tp.ganam",
        item="Ganam",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "The printed Manushya list names only five nakshatras; Uttara Phalguni, Purva "
            "Ashadha, Uttara Ashadha and Purva Bhadrapada are in no list and are not evaluable "
            "(not filled from another text)."
        ),
        references=(_kp("Ch. XIII p. 72"),),
    ),
    ProvenanceDef(
        entry_id="prov.tp.symmetric",
        item="Symmetric considerations",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "Yoni (same: agreement; hostile: disagreement; otherwise neutral), Rasi (opposite "
            "signs), Vasyam (either sign concordant to the other), Rajju (not the same "
            "division) and Vedhai (not in one repellent set) need no role."
        ),
        references=(_kp("Ch. XIII pp. 73-76"),),
    ),
    ProvenanceDef(
        entry_id="prov.tp.rasyadhipathi",
        item="Rasyadhipathi",
        label=EvidenceLabel.INFERENCE,
        statement=(
            "Kalaprakasika gives its own friendship lists (p. 74-75), not the BPHS table, and "
            "states no judgment rule; that mutual friendship is the agreement is inferred from "
            "the exception clause ('they be friendly planets'). Saturn's friends are not listed."
        ),
        references=(_kp("Ch. XIII pp. 74-76"),),
    ),
    ProvenanceDef(
        entry_id="prov.tp.exception",
        item="Exception",
        label=EvidenceLabel.SOURCE_SUPPORTED,
        statement=(
            "The adverse effects of Rajju, Vedhai, Ganam and Rasi 'need not be considered' when "
            "the Moon-sign lords are the same, friendly, or the signs are opposite. Reported as "
            "conditions only."
        ),
        references=(_kp("Ch. XIII p. 76"),),
    ),
)

PROVENANCE: dict[CompatibilityProfileId, tuple[ProvenanceDef, ...]] = {
    CompatibilityProfileId.ASHTAKOOT_MUHURTA_CHINTAMANI: ASHTAKOOT_PROVENANCE,
    CompatibilityProfileId.TEN_PORUTHAM_KALAPRAKASIKA: TEN_PORUTHAM_PROVENANCE,
}
