# Research — AI Palm Reading

Status: **Phase 13 research lock (2026-10-02)**. The owner approved decisions A to M on 2026-10-02 (section 1). The methodology locks are `docs/ASTROLOGY_STANDARDS.md` v1.27.0 (PM-01 to PM-24); the source entries are `research/ASTROLOGY_SOURCES.md` Group 26 and section 6.11; the component is `services/palm-vision` (`docs/ARCHITECTURE.md` section 35, ADR-008). No palm-vision code, model, dataset or migration exists; Phase 13 implementation has not started.

Pipeline (unchanged from the Phase 1 research):

image → quality check → hand detection → left/right classification → segmentation → landmarks/lines/mounts/fingers → structured visual evidence → palmistry rule engine → AI explanation → report.

Vision must output observable/estimated structures first. Reasoning maps those structures to traditional palmistry interpretations. The LLM must not invent invisible lines.

Evaluate across lighting, skin tones, hand sizes, camera quality, occlusion, left/right hands and line visibility. Measure detection, segmentation, side classification, landmarks, line precision/recall and interpretation consistency. Palm images require explicit purpose, retention and deletion controls.

## 1. Owner decisions (2026-10-02)

| ID | Decision | Recorded in |
|---|---|---|
| A | The vision component is `services/palm-vision` | `ARCHITECTURE.md` s.35, ADR-008, `CONTRIBUTING.md` |
| B | Phase boundaries: Phase 13 builds palm vision, quality, hand detection, side classification, palm region, landmarks, the palm-line/feature model, the structured `PalmFactSet`, palmistry knowledge and rules, the `PalmEvidenceBundle`, the evaluation harness and the interfaces for later phases. Phase 14 is the self-hosted LLM only; Phase 15 the agent and AI narration; Phase 16 verification; Phase 18 upload, object storage, persistence, consent and retention infrastructure | `Phases.md` Phase 13 |
| C | Palm rules run in the rule engine under a completely separate palm ruleset root; they never touch the Phase 6 Vedic ruleset or its hash | standards PM-20, section 14 |
| D | Western chirology is the first implementation profile; Indian Hasta Samudrika is a separate future profile; the traditions are never merged | PM-03 |
| E | Read Heron-Allen and Cheiro; try to locate a primary scan of Benham; use Benham only once a primary source is obtained; claim no Sanskrit or Indian methodology review without a source and a reviewer | section 3 |
| F | Production training and evaluation use a purpose-built consented internal dataset; public datasets only for research and baselines after licence and provenance verification | section 11 |
| G | Minors are excluded from palm-image collection and analysis until legal counsel clears the workflow | PM-17 |
| H | Training on user images is OFF by default; no user image becomes training data without a separate explicit authorisation | PM-17 |
| I | Fairness is evaluated across skin-tone variation without unjustified personal skin-tone labels; a privacy-preserving evaluation methodology is defined | PM-18, section 13 |
| J | No medical diagnosis, no disease prediction, no death prediction, no lifespan prediction | PM-13 |
| K | A learned palm model is reproducible when a pinned model artifact, preprocessing pipeline, runtime and library versions, input bytes and inference configuration produce equivalent structured facts within an explicitly documented numerical tolerance | PM-15, section 8 |
| L | Palmistry knowledge creates a NEW knowledge version; Phase 12 version `KV-06361d7aba28c1ce` stays valid and must not silently change | PM-20, section 14 |
| M | Legal counsel remains a production launch gate | PM-17, section 12 |

## 2. What was fetched and read, and what could not be

Fetched on 2026-10-02 (archive.org downloads of the scanned books' text, the Project Gutenberg text, and page images rendered through the archive.org page-image service). Nothing from these books is copied into the repository beyond short citations and concise notes of what each passage says; all three works were published before 1931.

| Item | Result |
|---|---|
| Heron-Allen, archive.org `manualofcheiroso00heroiala` | OCR text read (about 15,700 lines); four page images read (printed p. 191, p. 202 Plate IX, p. 203, p. 230) |
| Cheiro, *Palmistry for All*, Project Gutenberg #20480 | proofread text downloaded and read in part |
| Benham, archive.org `lawsscientifich00benhgoog` (Google scan of the Stanford Lane Medical Library copy) | OCR text downloaded; contents and Part Second ch. II read; two page images read (printed p. 355, p. 356) |
| Benham, other scans found | `in.ernet.dli.2015.219091`, `in.ernet.dli.2015.200302`, `dli.ministry.16089` (Digital Library of India), `lawsofscientific0000will` and `benhambookofpalm0000benh` (later printings and a 1988 edition, not used) |
| HathiTrust record for Cheiro's *Language of the Hand* | returned HTTP 403; not opened; nothing taken from it |
| Roboflow dataset pages | returned HTTP 403; not opened (section 11) |
| MediaPipe documentation, DPDP Act 2023 and DPDP Rules 2025 (MeitY PDFs), PIB explainer | fetched and read (sections 10 and 12) |

## 3. Sources actually read

All three are English originals (no translation involved), so the reading levels are `OCR-ORIGINAL-ENGLISH`, `IMAGE-ORIGINAL-ENGLISH` and `WEB-TRANSCRIPTION-ORIGINAL-ENGLISH` of the registry vocabulary. No source here is a classical text: all are late nineteenth or early twentieth century treatises on Western chirology (`MODERN_POPULAR` in the registry vocabulary). No Sanskrit or Hindi source was read. The reading level, copyright status and storage permission are in `research/ASTROLOGY_SOURCES.md` Group 26.

### 3.1 Heron-Allen, *A Manual of Cheirosophy* (SRC-HERONALLEN-CHEIROSOPHY)

- **Edition read**: the title page of the scan says "Tenth Edition", London: Ward, Lock and Co., preface dated 20 July 1885, illustrated by Rosamund Brunel Horsley (the Wellcome Collection catalogues its copy as 1885, 319 pp.). Scan: University of California Libraries copy on archive.org, `manualofcheiroso00heroiala`, metadata `NOT_IN_COPYRIGHT`; Wellcome "Public Domain Mark" for its own copy.
- **Structure** (contents, p. 9-12): Section I, Cheirognomy (pp. 97-182: the hand in general, the seven types, the female hand); Section II, Cheiromancy (pp. 183-312): the map of the hand (pp. 186-192), general principles (pp. 193-203), the mounts (pp. 204-228), the lines (pp. 229-270), the signs in the palm (pp. 271-279), signs upon the fingers (pp. 280-284), the triangle, quadrangle and rascette (pp. 285-292), chance lines (pp. 293-300), illustrative types and modus operandi.
- **Read** (OCR): the contents and introduction opening; the palm (pp. 100-102) and the comparative length of the fingers (pp. 106-107); the introduction to the seven types and the Elementary hand (pp. 136-139); the map of the hand (paragraphs 371-395, pp. 184-192); general principles on mounts and lines (paragraphs 396-427, pp. 192-203); the Mount of Jupiter (paragraphs 429-436, pp. 204-206); the Lines of Life, Mars, Heart, Head, Saturn or Fortune, Apollo, Health, the Cephalic Line and the Girdle of Venus (paragraphs 523-648, pp. 229-269); the Star (paragraphs 654-664, pp. 271-273), the Island (paragraphs 677-683, pp. 274-275); the Triangle (paragraphs 739-742, p. 286) and the Quadrangle (paragraphs 755-760, p. 288); the opening of the chance lines (paragraph 778, pp. 293-294).
- **Checked on page images**: printed p. 191 (paragraphs 389-395: the Line of Apollo, the three lesser lines, equivalent names), p. 202 (Plate IX, the signs: star, square, spot, circle, island, triangle, cross, grille), p. 203 (paragraphs 425-427: chained, wavy, broken, capillary lines), p. 230 (paragraphs 523-525: the Life Line). On every page checked the OCR matched the image.
- **Not read**: the joints, finger tips, hairiness, colour, thumb (pp. 108-121), the consistency of the hand and the individual fingers, the nails (pp. 130-135), the Spatulate, Conical, Square, Knotty, Pointed and Mixed hands, the female hand, the Mounts other than Jupiter (pp. 206-228), the Square, Spot, Circle, Triangle (as a sign), Cross and Grille texts, the signs of the planets, signs upon the fingers, the rascette and restreintes text (pp. 289-292), chance lines in detail, illustrative types and modus operandi. These are `NOT_READ` and no concept is claimed from them.

### 3.2 Cheiro, *Palmistry for All* (SRC-CHEIRO-PALMISTRY-FOR-ALL-1916)

- **Edition read**: G. P. Putnam's Sons, New York and London, copyright 1916, "Twenty-second Impression" (as the transcription's title page states); Project Gutenberg eBook #20480, released 29 January 2007, produced by the Online Distributed Proofreading Team ("public domain in the USA"). The text has no page numbers; references below are chapter headings of that text.
- **Read**: the preface "Rules for rapid observation" (opening); Part I, ch. II (opening and the first section of "The Line of Head and its variations"), ch. III (opening and the sections on the Line of Life), ch. IV (the Line of Mars), ch. V (opening and the origins of the Line of Fate), ch. VI (the Line of the Sun, opening), ch. VII (the Line of Heart, opening and origins), ch. X (the Line of Health, opening), ch. XI (the Girdle of Venus, the Ring of Saturn, the Bracelets), ch. XVII (different classes of lines; right and left hands), ch. XVIII (the Great Triangle and the Quadrangle); Part II, ch. II (the Thumb, opening), ch. V (the Mounts, introduction) and ch. VI (the Mount of Mars, opening).
- **Not read**: the history chapter, the remaining parts of the Head, Life, Fate, Sun and Heart chapters, the marriage, children, intuition, Via Lasciva, Ring of Solomon, travel, island/circle/spot/grille, star/cross/square and dating chapters, and Part II chapters on the seven types, fingers, nails, and the mounts of Jupiter, Saturn, the Sun, Mercury and the Moon.

### 3.3 Benham, *The Laws of Scientific Hand Reading* (SRC-BENHAM-SCIENTIFIC-HAND-READING-1901)

- **Primary scan obtained**: archive.org `lawsscientifich00benhgoog`, "Book digitized by Google and uploaded to the Internet Archive", Stanford Lane Medical Library copy; title page G. P. Putnam's Sons, New York and London, The Knickerbocker Press, 1901 ("with 800 illustrations from life"); the archive record notes "Published Dec. 1900; reprinted ... Jan. 1912", xxiv + 635 pages; metadata `NOT_IN_COPYRIGHT`. Google's usage guidelines on the scan ask for non-commercial personal use of the files and no automated querying; they are a condition of the scan file, not a copyright claim over the book, and the project stores only citations and notes.
- **Read**: the table of contents (pp. xi-xii); Part First ch. I opening (pp. 1-2: the science rests on the seven mounts; the planetary names are not used in any astrological sense); Part Second ch. II (pp. 353-360: the working hypothesis, the six Main lines, seven Minor lines, chance lines, proportion, the two hands).
- **Checked on page images**: printed p. 355 and p. 356.
- **Not read**: everything else (the mount types, the nails, fingers, thumb, every individual line chapter, the minor lines chapter). Benham's chapter structure puts the mounts first and the lines second; his "electric current" hypothesis (p. 354-355) is a stated working hypothesis ("whether you believe it true or not") and is recorded as a source assumption, not adopted.

### 3.4 Not obtained

- **Samudrika Shastra / Hasta Samudrika**: no primary or translated text was obtained; the only material is secondary (a Wikipedia article citing K. G. Zysk, *The Indian System of Human Marks*, 2016; the *Samudrika Tilaka* attributed to Durlabha-raja and Jagad-deva, about 1160-1175 CE). No Sanskrit reviewer exists. The Indian tradition is a separate future profile (PM-03); nothing in this lock claims its methodology.
- **Cheiro, *Language of the Hand* (1894)**: record located on HathiTrust, not opened; not used.

## 4. Support status of the taxonomy

`SUPPORTED`: at least one source read defines the concept with a location. `PARTIALLY_SUPPORTED`: the concept is named and described qualitatively only, or the sources read disagree on its definition. `NOT_SUPPORTED`: the sources read contradict or do not allow the concept as a vision output. `NOT_READ`: a source mentions it but the text was not read.

Reference key: **HA** = Heron-Allen paragraph (printed page) or page; **CH** = Cheiro chapter; **BE** = Benham printed page. "Observable" says whether a single 2D palm image can show it. "Layer" is OBSERVED VISUAL FACT, DERIVED GEOMETRIC FACT or PALMISTRY INTERPRETATION (the vision model never outputs the third).

| Concept | Status | Source references | Observable from one palm image, and layer |
|---|---|---|---|
| Hand shape (seven types) | PARTIALLY_SUPPORTED | HA types listed pp. 136-139 (Elementary read; others `NOT_READ`); CH Part II ch. I heading only; BE bases its work on mount types instead (pp. 1-2) | Qualitative descriptions only ("short and thick", "palm longer than the fingers", HA 265); no measurable criterion. A shape class is an interpretation-adjacent classification and is **not output** in Phase 13. Ratios (palm length to finger length) may be DERIVED GEOMETRIC FACTS tagged `PROJECT_DERIVED`. HA's text on the Elementary hand ranks intellect and names an ethnic group and is excluded (PM-13) |
| Fingers (length, joints, tips) | PARTIALLY_SUPPORTED | HA pp. 106-107 (short or long relative to the palm and to other fingers); joints and tips `NOT_READ` | Relative finger length is observable; the sources give no threshold. DERIVED, `PROJECT_DERIVED` ratio only |
| Thumb | PARTIALLY_SUPPORTED | CH Part II ch. II (three phalanges, love, logic, will; supple-jointed versus firm-jointed); HA pp. 116-121 `NOT_READ`; BE ch. XVII `NOT_READ` | Joint flexibility is not observable from a static image; phalanx proportions are, with no source threshold. Not output in the first profile |
| Life Line | SUPPORTED | HA 384 (p. 190) "encircles the ball of the thumb", 523-548 (pp. 229-242); CH ch. III (runs round the base of the thumb); BE p. 355-356 (main line; read from under the finger of Jupiter downward) | Observable: existence, path, length, breaks, branches. OBSERVED/DERIVED. HA, CH and BE also attach lifespan, death and illness readings to it (HA 524-529, CH ch. III): **excluded** (PM-13) |
| Head Line | SUPPORTED | HA 385 (p. 190), 571-598 (pp. 247-256); CH ch. II; BE pp. 355-356 | As above; HA and CH attach madness, murder and death readings (HA 583-593): excluded |
| Heart Line | SUPPORTED | HA 386 (p. 190), 551-570 (pp. 242-247); CH ch. VII (five origin positions); BE pp. 355-356 | As above; origin position (Jupiter versus Saturn mount region) is a DERIVED fact; HA 552-553 ties it to sensuality, CH ch. VII to the style of affection: interpretations differ |
| Fate / Fortune / Saturn Line | SUPPORTED, with conflicts | HA 387 (p. 190), 599-613 (pp. 256-261) (three origins); CH ch. V (four origins, including "the middle of the palm"); BE p. 356 (a main line, "frequently absent") | Observable (existence, origin region, end region). Absence is meaningful in HA 609 and BE 356: absence is an observed fact, never a default |
| Sun / Apollo Line (Brilliancy) | SUPPORTED, with a naming difference | HA 389 (p. 191) "Apollo, or Brilliancy", 614-628 (pp. 261-266); CH ch. VI "Sun, Success, Brilliancy"; BE p. 356 "Apollo line" | Observable as above; the label is profile-specific (PM-04) |
| Health / Hepatica / Mercury Line | PARTIALLY_SUPPORTED, location conflict | HA 388 (pp. 190-191), 629-639 (pp. 266-268): starts near the wrist at the base of the Life Line and rises diagonally to the Head Line near the Mount of Mars or the Moon; CH ch. X: "rises at the base of or on the face of the Mount of Mercury" and grows across to the Life Line; BE p. 356 names it the Mercury line and calls "Health" a misnomer | The sources disagree on the line's definition and its origin. Detection may be recorded as an unlabelled line track with a profile-specific label. Its **interpretation is health** (HA 630-638, CH ch. X): excluded (PM-13) |
| Mounts (seven) | SUPPORTED as named regions, PARTIALLY_SUPPORTED as measurable | HA 371-379 (pp. 184-189, Plate VII map); CH Part II ch. V (Plate VI); BE pp. 1-2 (seven mounts, locations shown in an illustration), chs. XIX-XXV `NOT_READ` | Region positions follow the finger bases and are definable from landmarks; boundaries are only drawn in the books' maps (`PROJECT_DERIVED` geometry). **Mount "development"** (high, flat, full; HA 396-402) is a volume property and is **not observable** from one 2D image (`NOT_EVALUABLE`); not output |
| Mount of Mars | PARTIALLY_SUPPORTED, conflict | HA 378 (p. 189): one Mount of Mars below the Mount of Mercury between the Heart and Head Lines, and a Plain of Mars in the centre; CH Part II ch. VI: **two** Mounts of Mars (under the upper Life Line, and between the Heart and Head Lines), with birth-date rules; BE ch. XXIII `NOT_READ` | The two profiles define different regions; neither is preferred. CH's birth-date rule mixes in astrology and is not adopted |
| Branches | SUPPORTED | HA 424 (Plate VIII Fig. 5, p. 202), 537; CH ch. XVII "Ascending Lines", "Descending Lines" | DERIVED geometric fact (direction of a child track relative to its parent). The attached meanings (good or bad) are interpretations |
| Intersections (lines cutting or joining) | PARTIALLY_SUPPORTED | HA (line-specific statements, e.g. 533-534, 567); no general definition | A crossing or junction of two tracks is a DERIVED fact; meanings are line-specific |
| Breaks | SUPPORTED | HA 426 (p. 203, page-image checked): "simple interruptions or cessations of the line, or bars across it"; CH ch. XVII "Broken Lines" | OBSERVED/DERIVED (a gap in a track). Meanings often concern illness or death and are excluded where they do |
| Chained, wavy, capillary, sister, forked and tasselled lines | SUPPORTED | HA 420-427 (pp. 200-203; Plate VIII; p. 203 page-image checked); CH ch. XVII; BE p. 359-360 (defects and repair, `NOT_READ` in detail) | Observable line conditions with figure definitions; not all are robust to detect. Candidates for later experimental facts |
| Island | SUPPORTED (definition), interpretation excluded | HA 677-683 (pp. 274-275), Plate IX Fig. 14 (page-image checked); CH ch. XV `NOT_READ` | The figure is a loop where a line splits and rejoins. HA's meanings are hereditary disease, adultery, murder and theft (excluded) |
| Star | SUPPORTED (definition), interpretation mostly excluded | HA 654-664 (pp. 271-273), Plate IX Fig. 10 (checked); CH ch. XVI `NOT_READ` | Hard to detect reliably; not in the first profile |
| Cross, Square, Spot/Circle, Triangle (sign), Grille | PARTIALLY_SUPPORTED | HA Plate IX (figure definitions checked); texts `NOT_READ` (squares referred to in 530, 602, 669; triangle sign 684); CH ch. XV and XVI `NOT_READ` | Figure definitions exist; meanings were not read; not output |
| Minor lines | PARTIALLY_SUPPORTED, **the sets differ** | HA 390-392 (p. 191, page-image checked): Line of Mars, Girdle of Venus, Via Lasciva; CH chs. IV, XI, XII (Girdle, Ring of Saturn, Bracelets, Intuition, Via Lasciva, Ring of Solomon); BE p. 356 (page-image checked): seven Minor lines (Ring of Solomon, Ring of Saturn, Girdle of Venus, lines of Affection, line of Mars, line of Intuition, the Bracelets) and the Via Lascivia "not entitled to a fixed place" | Three different sets. The Girdle of Venus differs: HA 391 "encloses the Mounts of Saturn and of Apollo"; CH ch. XI "from the base of the first finger to the base of the fourth". Not output as semantic lines in the first profile; unlabelled line tracks may carry a candidate role |
| Triangle (Great Triangle) | SUPPORTED | HA 381 (p. 190), 739-742 (p. 286): enclosed between the Life, Head and Health Lines, with an imaginary side if the Health Line is absent; CH ch. XVIII (Head, Life and Health Lines) | DERIVED geometric region and area ratio. HA ties size and colour to health and courage: the health part is excluded |
| Quadrangle | SUPPORTED | HA 382 (p. 190), 755-760 (p. 288): between the Heart and Head Lines, bounded by perpendiculars from the crevices between the first and second, and third and fourth fingers; CH ch. XVIII (between the Head and Heart Lines) | DERIVED geometric region and width profile; the definitions differ in the lateral bounds |
| Rascette and bracelets | PARTIALLY_SUPPORTED | HA 383 (p. 190) rascette and restreintes ("Bracelets of Life"); CH ch. XI (three Bracelets of health, wealth and happiness; an "arch" of the first is said to show internal malformation: excluded); BE p. 356 (only the upper bracelet worth consideration) | Wrist lines are on the edge of a palm crop; not output |
| Dating events on lines | PARTIALLY_SUPPORTED, conflicts | HA 525 (p. 230, page-image checked: the Life Line divided into five- and ten-year periods; the same page rejects Desbarrolles' diagram), 604 (the Fate Line: thirty, forty-five years); CH ch. XIX `NOT_READ`; BE p. 355 (reads the Life Line from under Jupiter downward; the Saturn line bottom to top) | Reading age from a line is a prediction technique and for the Life Line it is how lifespan, illness and death are read. **Not output**; at most a normalised arc-length position along a track, with no age mapping |
| Nails, colour and texture of the hand, hair | NOT_READ (HA pp. 115-135; CH Part II ch. IV; BE chs. VII-IX) | | Nails are not visible in a palm-facing image. Colour of lines (HA 410-414: pale, red, yellow, livid) is lighting-dependent and is tied by the sources to temperament and health (excluded). Not output |
| Hand side, both hands | SUPPORTED as a requirement to record, **conflicting semantics** | HA 419 (p. 199): a sign must be repeated in both hands to be certain, a single hand gives only presumption; CH ch. XVII: left hand shows inherited tendencies, right the developed; BE p. 359: left the natural map, right how the subject has altered it | Side is OBSERVED/DERIVED. Cross-hand comparison is permitted only inside one source profile; the profiles disagree and are not merged |

## 5. Recorded source conflicts (none resolved)

1. **Health line**: origin and name (HA 388/629, CH ch. X, BE p. 356).
2. **Girdle of Venus**: extent and meaning (HA 391, 645-648, CH ch. XI).
3. **Mounts of Mars**: one mount and a plain (HA 378) against two mounts with birth-date rules (CH Part II ch. VI).
4. **Sun versus Apollo naming** (CH ch. VI, HA 389, BE p. 356).
5. **Which lines are main and which minor**: HA says a complete knowledge of cheiromancy depends on "the three principal lines, head, heart and life" (introduction to Sub-section IV, p. 229) and lists six lines "generally found" plus three lesser lines (384-392, pp. 190-191); Benham counts six Main lines and seven Minor lines (BE p. 356); Cheiro treats the Head Line as "the most important" (CH Part I ch. II).
6. **Via Lasciva / cephalic line**: a distinct rare line (HA 640-644), a minor line (CH ch. XII `NOT_READ`), "no more than a chance line" (BE p. 356).
7. **Left versus right hand** (HA 419, CH ch. XVII, BE p. 359).
8. **Basis of the mount names**: not astrological (HA 371, BE pp. 1-2); linked to planets and to the month of birth with positive and negative mounts (CH Part II ch. V and VI).
9. **Origin counts of the Fate Line**: three (HA 599) against four (CH ch. V).
10. **Age divisions of the Life Line**: HA 525 criticises Desbarrolles' diagram; BE reads the line from under Jupiter downward.

Each is recorded as a `SOURCE_VARIANCE` with status `UNRESOLVED_CONFLICT` in the knowledge version (section 14); no consensus value is derived.

## 6. Content in the sources excluded by policy

Owner decision J excludes medical diagnosis, disease prediction, death prediction and lifespan prediction. The sources read are full of such readings: for example HA 524-529 (ill-health, "sudden death", dating death on the Life Line), 536, 540, 587 (epilepsy, "the scaffold"), 629-638 (the Health Line and illness), 678-682 (hereditary disease); CH ch. III and ch. X (the Life Line "foretells the length of life", the Health Line fixes "the date of death"), ch. XI (bracelets and "delicate internally"). They are recorded as source content and are **not** stored as interpretation or implemented as rules (PM-13).

The reading also found other categories that are unrelated to J but conflict with `PRODUCT_POLICIES.md` (no fear-based or exploitative readings) and `ASTROLOGY_STANDARDS.md` (no unsupported guarantees): criminality and murder (HA 539, 593, 657, 659), madness and mental illness (HA 583-585), fertility and maternity danger (HA 547, 568), illegitimacy and mystery of birth (HA 548, 613), sexual conduct and adultery (HA 391, 645-648, 680), intellectual ranking by ethnicity (HA 267), and moral labelling. The lock **proposes they are excluded by default** (PM-13); nothing in them is implemented unless the owner decides otherwise. This is a proposal beyond decision J, listed as an open decision (section 18).

## 7. Western profile methodology (summary; normative text in standards PM-01 to PM-13)

- **Included concepts**: hand side; landmarks and palm region; unlabelled line tracks; candidate roles for the Life, Head, Heart, Fate and Sun/Apollo tracks under a named profile; line attributes (existence, visibility, continuity, breaks, branches, intersections, curvature, normalised relative length, start and end regions); the Triangle and Quadrangle regions; mount regions as positions only.
- **Excluded concepts**: hand-shape classes, thumb and joint flexibility, nails, colour and texture, mount development, event dating on lines, semantic minor lines, the signs (star, cross, square, circle, spot, grille), islands as an interpretation basis, anything in section 6.
- **Source hierarchy**: three separate source profiles (Heron-Allen, Cheiro, Benham), none ranked above another, ordered by source id for presentation only.
- **Reading-level ceilings**: Heron-Allen and Benham are OCR-level except the page-image checked pages above; Cheiro is a proofread transcription. A concept read in only one OCR source is at most MEDIUM; a concept read on page images in two sources is HIGH only for the item actually checked (the list of main and minor lines at HA p. 190-191 and BE p. 356 and the break definition at HA p. 203).
- **Interpretation boundary**: the first rule set carries descriptive, source-backed tendencies of temperament, communication, affection style and ambition that pass the exclusion filter, each rule drawn from exactly one source profile, output as structured language-neutral tags, never as prose and never as a prediction of an event. The concrete rule list needs the owner's review before it is written (Phase 13 implementation; exit criteria in the Phase 13 block of `Phases.md`).
- **Uncertainty and `NOT_EVALUABLE`**: a concept with no visible track, an occluded or low-quality region, a conflicting source definition without a selected profile, or a volume-only concept returns `NOT_EVALUABLE` with a reason; an absent line is an observation with its own visibility state, not a default value.

## 8. Palm-fact contract (specification for later implementation)

Contracts live in `packages/contracts`; the producers are `services/palm-vision` (facts) and the rule engine (interpretations). Validated against the sources: every semantic label carries a profile and a source location; the model never emits interpretation.

**Classes**: `OBSERVED` (what the image shows, no palmistry term), `DERIVED` (computed from observed facts by a named, versioned method), `INTERPRETED` (only in `PalmRuleEvaluation`, never in a `PalmFact`).

```
PalmFactSet {
  schema_version, analysis_id, image_ref, quality_result, hand,
  facts: [PalmFact], fact_set_hash, provenance
}
PalmFact {
  fact_id,                  // "PF-" + first 16 hex of fact_hash
  fact_hash,                // SHA-256 of the canonical form below, excluding runtime fields
  fact_class: OBSERVED | DERIVED,
  fact_type,                // vocabulary: HAND_SIDE, PALM_REGION, LANDMARK_SET, LINE_TRACK,
                            //   LINE_ROLE_CANDIDATE, LINE_ATTRIBUTE, LINE_BREAK, LINE_BRANCH,
                            //   LINE_INTERSECTION, REGION_GEOMETRY, MOUNT_REGION, RATIO
  hand_side: LEFT | RIGHT | UNDETERMINED,
  region_id,                // e.g. a profile-defined region
  geometry: { frame_id, kind: POINT | POLYLINE | POLYGON, coords_fixed: [[int,int]...],
              sampling_spec },
  value: { kind: INT | ENUM | RATIO_FIXED, v, unit },
  confidence: { score_bp: int(0..10000), calibrated: bool, calibration_id|null },
  uncertainty: { kind: NONE | INTERVAL | SPREAD, lo_fixed, hi_fixed },
  visibility: CLEAR | PARTIAL | OCCLUDED | NOT_VISIBLE | NOT_EVALUABLE(reason),
  quality_ref,              // pointer to the quality result
  derived_from: [fact_id],  // empty for OBSERVED
  derivation: { method_id, method_version } | null,
  labelling: { profile_id, source_id, source_location, rule: "location definition id" } | null,
  provenance_ref            // pointer to the shared provenance block
}
PalmRuleEvaluation {        // INTERPRETED
  rule_id, rule_version, ruleset_id, profile_id, source_id, source_location,
  status: TRIGGERED | NOT_TRIGGERED | NOT_EVALUABLE(reason),
  fact_refs: [fact_id], knowledge_version, standards_version, interpretation_tags: [..]
}
```

- **Canonical serialization**: UTF-8 JSON, keys sorted, no insignificant whitespace, no floating-point numbers (the same `canonical_json` rule as the Phase 12 knowledge service); runtime fields (`created_at`, host, timings) are excluded from every hash.
- **Numeric precision**: coordinates are integers in fixed point at 10^-4 of the palm unit (below); scores are integers in basis points (0 to 10000); ratios are integers at 10^-4. Rounding is round-half-even, applied once at the output of the model post-processing, never inside a hashed field after the fact.
- **Coordinate frame**: the palm-canonical frame `PCF-1`: origin at the wrist landmark, the unit equal to the distance from the wrist landmark to the middle-finger base landmark, the "up" axis along that vector, mirrored for a left hand so a left and a right hand are comparable (the mirroring is recorded). A fact also records the affine transform from image pixels to `PCF-1` and the pixel size of the image. The landmark indices are those of the MediaPipe 21-point hand layout; the exact indices are to be verified against the documentation at the implementation start.
- **Hashing**: `fact_hash` = SHA-256 of the canonical form; `fact_set_hash` = SHA-256 over the sorted list of `fact_hash`. `image_ref.content_sha256` is the SHA-256 of the original received bytes; `normalized_input_sha256` is the SHA-256 of the decoded pixel array after the documented orientation normalisation, so reproducibility is tested on pixels.
- **Model artifact identity**: `artifact_id`, `weights_sha256`, `architecture_id`, `framework` and version, `training_run_id`, `training_manifest_sha256`, `licence_id`. A landmark model is recorded the same way.
- **Preprocessing identity**: `preprocessing_id`, `preprocessing_version`, `parameters_sha256`.
- **Runtime identity**: interpreter, `numpy`, `opencv`, `mediapipe`, `torch` (or the export runtime) versions, device class, thread count, `determinism_mode`, `inference_config_sha256`.
- **Derivation chain**: every `DERIVED` fact lists the fact ids it came from and the method id and version; the chain ends in `OBSERVED` facts and the image reference.
- **Confidence and uncertainty**: `score_bp` is a score; it is a probability only if `calibrated` is true and a `calibration_id` names a calibration report. Uncertainty is stated separately as an interval or a spread; a missing uncertainty is `NONE`, never an implied zero.
- **Visibility states** are mandatory on every line and region fact; `NOT_VISIBLE` (the model looked and found no track) differs from `NOT_EVALUABLE` (the region could not be examined).
- **Reproducibility claim**: no claim of exact reproducibility is made. The statement of decision K is the contract: equivalent facts within a documented tolerance. The tolerances (maximum coordinate deviation in `PCF-1` units, maximum score deviation, identical fact set and ordering) are set after cross-platform runs on the evaluation set and are asserted by tests; until then they are **UNSET**.

## 9. Image-quality methodology

Outcomes: `ACCEPT`, `RETRY` (the image may be usable if retaken, with a reason code), `REJECT` (not analysable, with a reason code). The gate runs before any palm-line analysis and its result is part of the evidence. No numeric threshold is hardcoded in this lock; every threshold is an `EMPIRICAL` value fixed from the calibration dataset (section 11) and owned by a versioned `quality_config`, proposed by the palm-vision maintainers from a calibration report and approved by the owner before a production gate.

| Check | Candidate metric (engineering basis) | Calibration requirement | Threshold owner |
|---|---|---|---|
| Blur | a sharpness measure over the palm region (for example a local gradient or Laplacian variance) | images labelled analysable or not by annotators, across devices and resolutions | `quality_config`, owner-approved |
| Exposure | clipped fraction at both ends of the luminance histogram inside the palm region | images spanning dim, bright and mixed lighting | same |
| Contrast | luminance spread inside the palm region (line visibility depends on it) | same, with line-visibility annotations | same |
| Framing | all hand landmarks inside the frame with a margin; palm region fully inside | images with partial hands | same |
| Occlusion | landmark presence and the fraction of the palm region covered by non-hand pixels | images with objects, jewellery, ink | same |
| Orientation | angle of the wrist-to-middle-finger axis; palm facing the camera (finger landmark ordering and handedness consistency) | images rotated, back-of-hand images | same |
| Resolution | pixels across the palm region (not the image size) | images at several distances and sensors | same |
| Palm visibility | segmentation confidence and landmark confidence together | all of the above | same |
| Background | separation of the hand from the background (clutter near the palm edge) | varied backgrounds | same |

Calibration is valid only for the devices and lighting present in the dataset; the report states its coverage. A threshold that cannot be calibrated stays unset and the check reports `UNCERTAIN`, mapped to `RETRY`.

## 10. Vision pipeline research

- **OpenCV and NumPy**: preprocessing (orientation normalisation, resizing, colour conversion), palm-region cropping, classical line-enhancement filters, geometry and polyline operations.
- **MediaPipe Hand Landmarker** (Google AI Edge documentation read 2026-10-02): outputs handedness, 21 landmarks in image coordinates and 21 in world coordinates; a two-model bundle (palm detector, hand-landmark model); the landmark model was developed with about 30K real-world images and rendered synthetic hands; the documentation page states no fairness evaluation (a model card exists and was not read); code and models are Apache 2.0 according to the documentation page and the model README found. It locates knuckles and finger tips; **it detects no palm lines, mounts or palmistry features** and must never be presented as palmistry interpretation (`TECH_STACK.md`). Whether its handedness output assumes a mirrored image is not verified here and must be checked in its documentation before side classification is built.
- **PyTorch**: a dedicated palm-line segmentation and feature model, trained or fine-tuned on the consented dataset.
- **Approaches** (general engineering knowledge; the papers found in search were not read, so none is cited as a basis): `BASELINE`: classical multi-scale ridge or line enhancement with thresholding, explainable and a bootstrap for annotation; `EXPERIMENTAL`: an encoder-decoder segmentation network fed by the landmark-defined region of interest, with the output vectorised into line tracks; `PRODUCTION-CANDIDATE`: none selected. A model is promoted only after the evaluation in section 13 and the owner's gate; no popular model is locked.
- **Segmentation versus detection**: segmentation masks turned into polylines fit the fact schema better than boxes.
- **Uncertainty and calibration**: per-track scores plus a calibration check on held-out data; the method (for example temperature scaling or an ensemble spread) is an experiment, not a lock.
- **Search results found, not read**: palmprint principal-line feature extraction ([PeerJ CS](https://peerj.com/articles/cs-3109/)), a palmprint segmentation and ROI toolkit ([PalmSeg](https://github.com/AngeloUNIMI/PalmSeg)), a synthetic palmprint generation paper ([arXiv 2505.04922](https://arxiv.org/pdf/2505.04922)).

## 11. Dataset methodology and public datasets

### 11.1 Public datasets reviewed (none suitable for production)

| Dataset | Verified facts | Use |
|---|---|---|
| 11K Hands (Afifi et al.) | 11,076 images of 190 subjects aged 18-75, dorsal and palmar, white background; terms "FREE for reasonable academic fair use" (project page); metadata includes gender, age and skin colour | Hand detection and side baselines for research only; not committable; commercial use not granted by the stated terms; the white background differs from phone photos |
| Roboflow Universe palm-line sets | A search listing described two community sets under CC BY 4.0 (one with 2,959 images; classes such as head, heart and life line); the pages returned HTTP 403 and were not opened | UNVERIFIED. A licence on annotations does not show that the people pictured consented; image provenance unknown. Not usable until verified |
| PolyU II, CASIA, IIT Delhi, Tongji palmprint sets | Sizes reported in a survey ([arXiv 2501.01166](https://arxiv.org/pdf/2501.01166)); licences not found | Built for biometric recognition (often controlled or near-infrared capture) with no palmistry labels; likely research or request-only. UNVERIFIED |
| FreiHAND, InterHand2.6M | Reported research-only and CC BY-NC 4.0 respectively | Non-commercial; not usable commercially |

**Conclusion**: no verified public dataset provides palmistry-labelled line annotations that can be used commercially. Public data may serve hand-detection baselines for research after each licence and provenance is verified and recorded; it is never committed to the repository and never mixed into production training or evaluation without that record.

### 11.2 Internal consented dataset specification

- **Consent**: an itemised notice stating the purposes (DPDP Rule 3), separate consents for (a) evaluation and training use and (b) any later service use; withdrawal as easy as giving consent; each consent records a notice version hash, a timestamp and a pseudonymous contributor identifier; contributors are adults only (G), with the age-assurance method to be settled with counsel.
- **Collection**: written protocol; a pilot first. Coverage strata recorded in the manifest: devices and operating systems; lighting (indoor, outdoor, mixed, low); distances and resolutions; hand size; left and right hands (both hands per contributor); palm shape; line visibility (clear to faint); background; occlusion cases (jewellery, ink, henna, bandage). Minimum sample sizes per stratum are derived before collection from the width of the confidence interval wanted for each metric and approved by the owner; this lock states no numbers.
- **Skin-tone coverage** is obtained by recruitment breadth and checked with the privacy-preserving covariate of section 13, not by asking each contributor for a label.
- **Annotation protocol** (versioned guideline): landmark verification; hand side; line tracks as polylines for the line roles in the profile's included concepts; visibility per line; region masks; image analysability and the reason. Two independent annotators per image, a third adjudicates disagreements; the adjudicated label is the reference.
- **Agreement measurement**: polyline agreement as an F-score or Dice over matched tracks within a distance tolerance defined in the guideline; categorical agreement (side, visibility, analysable) as Cohen's kappa or Krippendorff's alpha; reported per stratum before labels are used.
- **Splits**: train, validation and test split by contributor (all images of a contributor, both hands and all sessions, in one split); stratified so each stratum is present in validation and test; the test set is sealed and used for gate decisions only.
- **Leakage prevention**: contributor-level separation, session-level grouping, near-duplicate detection (perceptual hashing) across splits, no tuning on the test set, the manifest hash recorded with every model.
- **Provenance manifest** (one record per image, stored beside the object store, never in git): image id, SHA-256, contributor pseudonym, consent record id and version, collection date, device model and OS, capture conditions, annotation ids and guideline version, split, retention class, licence/authorisation record.
- **Licensing record**: the dataset's authorisation basis, the consent text versions, the permitted uses, and any restriction, per `datasets/README.md`.
- **Not done in this stage**: no data was collected, no dataset was added to the repository.

## 12. Privacy and legal status

Primary texts read on 2026-10-02: the [Digital Personal Data Protection Act, 2023](https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf), the [DPDP Rules, 2025](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf) and the [PIB explainer](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf). Text was extracted from the PDFs; statements of absence apply to that extracted text.

**Confirmed legal text**
- Neither the Act nor the Rules, in the extracted text, contains the words "biometric" or "sensitive"; the DPDP framework has no special category. Whether a palm image or the line geometry extracted from it is personal data about an identifiable person is **not settled by the text read** and is unresolved.
- Rule 1: Rules 1, 2 and 17 to 21 apply from the date of publication; Rule 4 (Consent Managers) one year after; Rules 3, 5 to 16, 22 and 23 eighteen months after the date of publication. The PIB explainer dates the notification 14 November 2025.
- Rule 3: the notice must stand alone, be in plain language, itemise the personal data and the specific purposes, and state how to withdraw consent with ease comparable to giving it.
- Rule 6: reasonable security safeguards at the minimum include encryption, obfuscation, masking or virtual tokens; access control; logs and monitoring for detecting unauthorised access; backups; and retention of such logs and personal data for one year unless a law requires otherwise.
- Rule 7: breach intimation to affected persons and the Board. Rule 8 and the Third Schedule: timed erasure for the listed classes of fiduciary (not examined for applicability). Rule 10 and Act s. 9: verifiable parental consent for a child's data and no tracking or behavioural monitoring of children.

**Policy requirements already recorded**: `PRODUCT_POLICIES.md` (palm images; no secondary use without authorization), `LEGAL_REGULATIONS.md` (palm-image privacy; child safeguards), and the owner's decisions G, H, J, M above.

**Engineering best practice (proposed)**: no pixels, geometry or tracks in logs; images and derived facts encrypted at rest; images referenced by id; deletion cascades from the image to every derivative; no cross-user deduplication by hash; model training excluded by default.

**Unresolved legal interpretation**: the classification of palm images and derived geometry under the Act; the legal basis and notice wording for storing derived facts; how Rule 6's one-year log retention coexists with minimum retention of the images themselves; whether any Third Schedule class applies; Significant Data Fiduciary status; consent and withdrawal for dataset use once a model has been trained; minors and age assurance; whether the older Information Technology Act rules on sensitive personal data still apply during the transition (their text was not read here).

**Counsel-required launch gate (M)**: the items above, and the existing launch gate in `PRE_PHASE1_CHECKLIST.md` and `LEGAL_REGULATIONS.md`. This research is not legal advice. No legal mechanics are implemented in this stage.

## 13. Fairness and evaluation methodology

- **Stratify** every metric by skin-tone variation (below), hand size, left and right hand, lighting, camera type and resolution, orientation, occlusion and palm shape. Age only where it is lawfully collected.
- **Metrics**: detection precision and recall; side-classification accuracy; segmentation IoU and Dice; landmark error normalised by the palm unit; line detection precision and recall under a distance tolerance; false-positive rate for absent lines; quality-gate accuracy and rejection and retry rates; calibration (reliability) of confidence.
- **Three tiers, no invented targets**: *research benchmark* (reported, no gate); *engineering acceptance threshold* (set after the baseline is measured on the internal set); *production gate* (set by the owner, including bounds on the gap between strata).
- **Skin-tone evaluation without personal labels (decision I)**: no contributor is asked for, and no record stores, a race, ethnicity or personal skin-tone category. The covariate is an **image-derived measurement** computed at evaluation time from the segmented palm skin pixels, for example a lightness and hue measure in a perceptual colour space under a colour-reference card included in the capture session, reported only as aggregate bins with a minimum bin size and never joined to contributor identity, used for evaluation only (never as a training feature, a product feature or an input to a rule). Because lighting confounds colour, bin assignment is valid only for sessions with the reference card; sessions without it are excluded from skin-tone bins and reported separately. Whether this covariate is adequate for palm images is a pilot question; the pilot report decides.
- **Contributor-level metrics**: confidence intervals computed with the contributor, not the image, as the resampling unit.
- **Reports** are versioned and name the dataset manifest hash, model artifact and quality config.

## 14. Knowledge and rule architecture

- **Where palm knowledge goes**: `services/knowledge`, as a new sealed knowledge version (decision L). The Phase 12 version `KV-06361d7aba28c1ce` and its snapshot hash keep their meaning; the new content produces a new identifier and the pinned-hash test is updated deliberately, with the old value kept as a regression constant for the Phase 12 content.
- **Existing vocabulary cannot hold palm content** (`services/knowledge/src/pandit_knowledge/models.py`): `KnowledgeDomain` has `VEDIC` and `TAROT` only; `ConceptType` has `PLANET`, `HOUSE`, `DOMAIN`, `TERM`, `TAROT_CARD`, `CONCEPT`; `RuleKind` has `RULE`, `TABLE`, `PROFILE`; the database check constraints follow these enums and are tested against them. The minimum extension is a forward-only migration `0003` adding the domain `PALMISTRY` and, for rule references, a palm rule kind (new concept types are optional: `CONCEPT` and `TERM` can carry palm concepts). `StatementKind.SIGNIFICATION` and `SOURCE_VARIANCE`, `SupportStatus`, `ReadingLevel`, `Confidence`, `IngestionPermission`, `TextOrigin` and `TextFidelity` are reused unchanged. The migration is **not** created in this stage.
- **Palm rules**: a separate ruleset root with its own manifest (ruleset id for palmistry, never the Vedic `PANDIT_JI_VEDIC_PHASE6`) evaluated by the rule engine. The proposed location is `services/knowledge/palm_rules/`, a sibling of the Phase 6 `rules/` directory (the Phase 6 convention: rule YAML owned beside the knowledge content and loaded by the rule engine from a directory path); `services/rule-engine/palm_rules/` is the alternative; the choice is made at implementation start (section 18). In either case the root is **outside** `services/knowledge/rules/`.
- **Verified isolation facts** (code read 2026-10-02): the knowledge service hashes the Phase 6 rules with `rule_index(rules_dir)`, which walks `rules_dir.rglob("*.yaml")` (`content.py`), so any YAML placed under `services/knowledge/rules/` would change the Phase 6 hash and the knowledge snapshot; the rule-engine loader `load_ruleset(rules_dir)` walks every YAML file under the directory it is given (`loader.py`) and requires exactly one ruleset manifest (it reports `expected exactly one ruleset manifest` otherwise) and one `standards_version` per ruleset, so a palm file inside the Vedic directory would either fail to load or contaminate the Vedic ruleset. A separate root loaded with its own `load_ruleset` call cannot do either. The rule `Rule` schema is specific to astro Facts (`ARCHITECTURE.md` section 7), so a palm fact family is a rule-engine extension to be designed in Phase 13 without changing any Phase 6 rule file, hash or evidence field.
- **Conceptual tests** (written at implementation): the Phase 6 ruleset hash and the Phase 12 snapshot are asserted unchanged after palm rules exist; the palm ruleset root is outside any directory the Vedic loader or the Phase 12 hash walks; a palm rule never loads into the Vedic engine and a Vedic rule never loads into the palm engine.
- **The five concepts stay separate**: calculation (astro-engine; not used for palm), rule (palm rules in the rule engine), knowledge (source-backed palm statements), interpretation (a `PalmRuleEvaluation` tag), narration (Phase 15). Palmistry is not a hidden calculation system: palm-vision produces facts, nothing else computes a palm fact.

## 15. Evidence bundle and verification boundary

A **separate** `PalmEvidenceBundle` (the Phase 6 bundle is untouched):

```
PalmEvidenceBundle {
  bundle_version, analysis_id, standards_version, knowledge_version,
  image_ref { image_id, content_sha256 },       // no bytes, no URL
  quality_result, hand { detected, side, confidence },
  regions, landmarks_ref, line_detections_ref,
  facts: [fact_id], rule_evaluations: [PalmRuleEvaluation],
  source_refs, model_versions, uncertainty_summary, bundle_hash
}
```

Phase 16 can verify a narrated claim only against this bundle: each claim cites a `fact_id` or a `rule_id` that is in the bundle; a claim with no matching id is unsupported. Phase 13 defines this interface and builds no verifier. The agent receives the bundle, never pixels (`ARCHITECTURE.md` section 20); logs carry ids only.

## 16. Storage architecture

- **Object storage (S3-compatible, MinIO by default; private, signed URLs)**: the original image and any short-lived derivatives; model artifacts live in a separate bucket or registry with SHA-256, version and licence record.
- **PostgreSQL**: image metadata (owner, purpose, consent reference, retention class, content hash, storage key, deletion state), facts and bundles; never image bytes. These tables belong to Phase 18; Phase 13 creates no user-data migration.
- **By id only**: images in logs, traces, the agent and the model. **Never logged**: pixels, landmarks, tracks, geometry.
- **Content hash**: SHA-256 of the original bytes computed before preprocessing; no cross-user deduplication.
- **Deletion propagation**: image, derivatives, facts, bundles and the stored agent traces that embed bundles; the audit log holds ids only.
- **Provenance**: every fact carries artifact hashes; the training manifest records dataset lineage.

## 17. Open items

Section 18 lists the owner decisions that remain; all implementation items are in `Phases.md` Phase 13.

## 18. Remaining owner decisions

1. **Additional prohibited reading categories** (section 6, beyond decision J): criminality, mental illness, fertility and pregnancy, paternity and legitimacy, sexual conduct, ethnic or intellectual ranking, moral labelling. Proposed: excluded by default.
2. **First rule list**: the concrete descriptive rules for the first Western profile need the owner's review before they are written.
3. **Palm rule file location**: `services/knowledge/palm_rules/` (proposed) or `services/rule-engine/palm_rules/`.
4. **Access to scans for deeper reading**: the unread chapters (thumb, fingers, nails, other mounts, signs) may be read in a later research step if the owner wants them in the first profile.
5. **A qualified Sanskrit reviewer and a Hasta Samudrika source** before the Indian profile is started.
6. **Counsel items** in section 12.
