# Phase 17 — Domain Matrix (research lock, 2026-10-06)

Companion to `research/PHASE_17_LIFE_DOMAIN_RESEARCH.md`. Research record only: nothing here is a production mapping, and no data file, rule or contract was changed. Statuses: `SOURCE_SUPPORTED` (a source read states the mapping in its own wording or a labelled bridge), `PARTIALLY_SUPPORTED`, `UNRESOLVED_CONFLICT`, `NOT_EVALUABLE` (no source read states it: a finding about the passages read, not about the classical texts as a whole), `NOT_READ` (a source that might state it was not read), `DEFERRED`, `RESEARCH_PENDING`. Source labels: **B** = BPHS (Santhanam Vol I), **P** = Phaladeepika (Sastri 2nd ed.), **BJ** = Brihat Jataka. Levels: IT = `IMAGE-TRANSLATION`, OT = `OCR-TRANSLATION`. "Bridge" means the product label is not the source's word.

## A. Taxonomy reconciliation (not merged)

Columns: Ph = `Phases.md` Phase 17 list; F = `features.md` (section 11, 12, 13, 20); Intent = agent `Intent` enum values (14: GENERAL, LOVE_RELATIONSHIP, MARRIAGE, CAREER, WEALTH, BUSINESS, DAILY_GUIDANCE, EDUCATION, TRAVEL, LIFE_ANALYSIS, COMPATIBILITY, TRANSIT, DASHA, PALM_OVERVIEW); KB = `services/knowledge/content/domains.yaml` (four domains CAREER, MARRIAGE, FINANCE, EDUCATION; 48 house mappings: 6 `SOURCE_SUPPORTED`, 1 `UNRESOLVED_CONFLICT`, 41 `NOT_EVALUABLE`).

| Domain | Ph | F | Intent | KB | Source-backed? | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Birth | yes | "Birth / early life" | none | none | no source term read | NOT_EVALUABLE | undefined as a domain; BPHS Ch. 9 (evils at birth) is lifespan-adjacent and excluded by policy; Ch. 12 not read |
| Personality | yes | yes | LIFE_ANALYSIS | none | house 1 | PARTIALLY_SUPPORTED | bridge: "innate nature", "intellect" (B 11.2) |
| Childhood | yes | yes | none | none | no | NOT_EVALUABLE | minors policy; no source read |
| School | yes | yes | EDUCATION | none | no level distinction | NOT_EVALUABLE | no source separates levels |
| College | yes | yes | EDUCATION | none | no | NOT_EVALUABLE | same |
| Subjects | yes | "Subject suitability" | EDUCATION | none | P XVI 6 (IT) | PARTIALLY_SUPPORTED | proficiency by the planet associated with the 2nd lord (scriptures, politics, arts...); modern subjects not supported |
| Education | yes | yes | EDUCATION | EDUCATION (house 5) | yes | SOURCE_SUPPORTED | house 5, Mercury/Jupiter, D24 |
| Higher education / studies | no | yes | EDUCATION | none | no | NOT_EVALUABLE | no source |
| Competitive examinations, academic patterns, education timing | no | yes | EDUCATION | none | no | NOT_EVALUABLE | |
| Career | yes | yes | CAREER | CAREER (house 10) | yes | SOURCE_SUPPORTED | profile-specific methods |
| Job | yes | yes | CAREER | none | P V 2-8 (livelihood types) | PARTIALLY_SUPPORTED | job vs business not separated by a source |
| Corporate life | yes | yes | CAREER | none | no | NOT_EVALUABLE | modern concept |
| Business | yes | yes | BUSINESS | none | house 7 "trade" (B 11.8) | PARTIALLY_SUPPORTED | |
| Startup | yes | yes | BUSINESS | none | no | NOT_EVALUABLE | |
| Entrepreneurship | no | yes | BUSINESS | none | no | NOT_EVALUABLE | |
| Finance | yes | yes | WEALTH | FINANCE (2, 11, 12) | yes | SOURCE_SUPPORTED | |
| Wealth | yes | yes | WEALTH | FINANCE | yes | SOURCE_SUPPORTED | house 2 wealth |
| Income | no | yes | WEALTH | FINANCE (11) | yes | SOURCE_SUPPORTED | house 11 income |
| Investments | no | "investments-related interpretation" | WEALTH | none | no | NOT_EVALUABLE | high-impact; no source |
| Love | yes | yes | LOVE_RELATIONSHIP | none | Venus "love affairs" (P XV 15-16) | PARTIALLY_SUPPORTED | no house in B 11 lists it |
| GF/BF | yes | yes | LOVE_RELATIONSHIP | none | no | NOT_EVALUABLE | minors policy |
| Relationship | yes | yes | LOVE_RELATIONSHIP | none | house 7 | PARTIALLY_SUPPORTED | the source frame is marital |
| Marriage | yes | yes | MARRIAGE | MARRIAGE (7; 2 conflict) | yes | SOURCE_SUPPORTED | with conflicts and policy gates |
| Spouse | yes | yes | MARRIAGE | MARRIAGE | house 7, Venus, D9 | PARTIALLY_SUPPORTED | the source frame is a man's wife; sex not collected |
| Family | yes | "Family life" | LIFE_ANALYSIS | none | houses 2, 4 | SOURCE_SUPPORTED | B 11.3 "family", 11.5 "relatives" |
| Parents | no | yes | LIFE_ANALYSIS | none | houses 4, 9/10, D12 | PARTIALLY_SUPPORTED | conflict DC-01 |
| Siblings | no | yes | LIFE_ANALYSIS | none | house 3, Mars, D3 | SOURCE_SUPPORTED | |
| Children | yes | yes | none | none | house 5, Jupiter, D7 | SOURCE_SUPPORTED | policy-gated (fertility, paternity) |
| Travel | yes | "Journeys/travel" | TRAVEL | none | houses 3, 7, 9 | PARTIALLY_SUPPORTED | "journey", "travel", "visits to shrines" |
| Foreign travel | yes | yes | TRAVEL | none | house 12 wandering (B 23.11) | PARTIALLY_SUPPORTED | derived |
| Foreign education | yes | yes | none | none | no combined source | NOT_EVALUABLE | a composition of two supported concepts would be an engineering rule, not a source statement |
| Foreign settlement | yes | yes | none | none | house 10 "living in foreign lands" (B 11.11), P V 9 | PARTIALLY_SUPPORTED | |
| Personal life | yes | yes | LIFE_ANALYSIS | none | no | NOT_EVALUABLE | undefined |
| Spirituality | yes | yes | none | none | houses 9, 12, D20 | PARTIALLY_SUPPORTED | no karaka stated |
| Major life transitions | no | yes | none | none | no | NOT_EVALUABLE | undefined |
| General life patterns | no | yes | LIFE_ANALYSIS | none | D1; D45, D60 "all indications" | PARTIALLY_SUPPORTED | |
| Health (as interpretation) | no | yes (with the no-diagnosis rule) | none | none | not mined | DEFERRED | owner decision 11 |
| Vastu | no (standards line 95 says Phase 17) | "Vastu-related guidance" | none | none | not read | RESEARCH_PENDING, DEFERRED | |

Totals for the 27 `Phases.md` domains: 7 `SOURCE_SUPPORTED`, 11 `PARTIALLY_SUPPORTED`, 9 `NOT_EVALUABLE`, 0 `UNRESOLVED_CONFLICT` as a whole domain (conflicts are per mapping: DC-01 to DC-05).

## B. Domain research records (the 27)

Houses and varga evidence = source statements as read; rules = existing Phase 6 rules whose own text states the matter (sheet E); dasha and transit = the requirements of the research record, sections 7 and 8; "policy" = section 11. Every houses/karaka/varga item is `direct` (the source's own word) or `derived` (the source states it in an effect chapter, or a labelled bridge).

| Domain | Houses (source, level, direct/derived) | Karakas | Vargas | Rules | Dasha / transit | Conflicts | Policy | Readiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Birth | none | none | D1 "physique from the ascendant" (B 7.1-8, IT) is the body, not "birth" | none | none | none | lifespan-adjacent content excluded | NOT_EVALUABLE |
| Personality | 1: physique, appearance, intellect, innate nature (B 11.2, IT, direct for those words, bridge to "personality") | Sun (1st house karaka, B 32.34, P XV.17); Moon "mind" (B 3.12-13), "character of one's heart" (P XV 15-16) | D1 (physique only) | the five Pancha Mahapurusha rules (B Ch. 75, tagged personality, status in Phase 6) | not defined | none | none specific | PARTIALLY |
| Childhood | none | none | none | none | none | none | minors | NOT_EVALUABLE |
| School | none | none | D24 learning (not level-specific) | none | none | none | minors | NOT_EVALUABLE |
| College | none | none | same | none | none | none | adult/minor undefined | NOT_EVALUABLE |
| Subjects | 2nd lord associated with a planet (P XVI 5-6, IT): Jupiter scriptures and law; Mercury politics; Venus amorous topics; Moon arts; Mars labour; Rahu/Ketu speech faults | Mercury learning, Jupiter knowledge | D24 | none | none | none | the Venus and malefic readings are derogatory in wording | PARTIALLY |
| Education | 5: learning, knowledge (B 11.6, IT, direct); 2nd: knowledge and wealth by the lord's association (P XVI 5, IT) | Mercury (learning, P XV), Jupiter (knowledge, B 3.12-13, BJ II.1, P XV) | D24 "learning" (B 7.1-8, IT, direct); the translator's example with the 2nd and 4th lords is a note, not verse | Lagnadhi (learned in the Sastras, B 36.37, OT); Vosi (learning, B 38.2-3, OT) | domain-relevant dasha: not stated (P XIX-XX unread) | the 4th house for education is not stated (KB records it NOT_EVALUABLE) | none specific | SOURCE_SUPPORTED |
| Career | 10: profession (livelihood), honour (B 11.11, IT, direct); B Ch. 21 v. 1-22 (OT) conditions on the 10th lord | Mercury (B 32.34); Jupiter, Sun, Mercury, Saturn (P XV.17): separate profiles; Saturn livelihood (P XV 15-16) | D10 "power (and position)" (B 7.1-8, IT; "livelihood" is the translator's gloss); P V 1: Navamsa of the 10th lord's sign (separate profile) | Adhi (B 37.5), Vesi, Vosi, Ubhayachari (B 38) for status | P X.13-style dasha rule not stated for career | DC-03, DC-04 | none specific | SOURCE_SUPPORTED |
| Job | 10 (as Career); P V 2-8: livelihood by the Navamsa lord of the 10th lord, including service | Saturn (servants, livelihood) | as Career | as Career | not stated | none | derogatory livelihoods (P V 4, 8) | PARTIALLY |
| Corporate life | none | none | none | none | none | none | none | NOT_EVALUABLE |
| Business | 7: trade (B 11.8, IT); 10 | Mercury (10th karaka) | D10 / Navamsa profiles | none | not stated | none | none | PARTIALLY |
| Startup | none | none | none | none | none | none | none | NOT_EVALUABLE |
| Finance | 2: wealth; 11: income, prosperity; 12: expenses (B 11.3, 11.12, 11.13, IT, direct); B Ch. 22 v. 1-7 (OT) | Jupiter (2nd, 11th, wealth); Saturn (12th) | D2 Hora "wealth" (B 7.1-8, IT, direct) | Dhana (B 37.6, OT: states wealth), Sunapha, Duradhara (partly), Gajakesari (wealth), Kemadruma (penury) | not stated | none | professional-advice disclaimer; BPHS amounts and ages not to be encoded | SOURCE_SUPPORTED |
| Wealth | 2 (as above) | Jupiter | D2 | as Finance | not stated | none | as Finance | SOURCE_SUPPORTED |
| Love | none in B 11 | Venus "love affairs", "pleasures" (P XV 15-16) | none | none | none | none | minors; sexual-content wording in the sources | PARTIALLY |
| GF/BF | none | none | none | none | none | none | minors | NOT_EVALUABLE |
| Relationship | 7 (wife) | Venus | D9 | none | not stated | none | minors | PARTIALLY |
| Marriage | 7: wife (B 11.8, 32.33, IT); 2 (UNRESOLVED_CONFLICT, KB); P X (OT): the 7th house, its lord, Venus, the 5th and 7th conditions | Venus (B 32.34, P XV.17) | D9 spouse (B 7.1-8, IT, direct) | Kuja dosha (B 80.47-49, IT; Jataka Parijata v. 34, OT-source-language): two profiles, conflict group KUJA_DOSHA_TOPIC | P X.13: dasha of the planet in, aspecting or owning the 7th; P X.14: Jupiter's transit trine in that dasha (OT) | DC-02 | spouse death statements; sex not collected; minors | SOURCE_SUPPORTED |
| Spouse | 7; P X 7-8 mirrored for a woman's nativity | Venus (for "wife"); no husband karaka read (NOT_READ) | D9 | as Marriage | as Marriage | DC-02 | sex not collected | PARTIALLY |
| Family | 2: family (B 11.3); 4: relatives (B 11.5) (IT, direct) | Mercury "relatives in general" (P XV 15-16) | D3 (co-born), D12 (parents) | none | not stated | none | none | SOURCE_SUPPORTED |
| Children | 5: sons (B 11.6, IT); progeny (B 32.33); B Ch. 16 v. 1-32 and P XII 1-5 (OT) | Jupiter (5th karaka B 32.34; "sons" P XV 15-16) | D7 "sons and grandsons" (B 7.1-8, IT, direct) | none | not stated | none | fertility, paternity, illegitimacy statements in the sources; minors | SOURCE_SUPPORTED, gated |
| Travel | 3: journey (B 11.4); 7: travel (B 11.8); 9: visits to shrines (B 11.10) (IT, direct) | none stated | none | none | not stated | none | none | PARTIALLY |
| Foreign travel | 12: wandering from country to country vs own country (B 23.11-12, OT, derived) | none | none | none | not stated | none | none | PARTIALLY |
| Foreign education | none | none | none | none | none | none | none | NOT_EVALUABLE |
| Foreign settlement | 10: living in foreign lands (B 11.11, IT, direct); 12 (as above); P V 9: country of acquisition (IT) | none | Navamsa (P V 9) | none | not stated | none | none | PARTIALLY |
| Personal life | none | none | none | none | none | none | none | NOT_EVALUABLE |
| Spirituality | 9: religion, visits to shrines (B 11.10, IT); 12: final emancipation (B 23.10, OT, derived); P XXVII 1-6 (OT) | none stated | D20 "worship" (B 7.1-8, IT, direct) | none | not stated | none | religion-based labels in P XXVII 5 | PARTIALLY |

## C. Divisional chart (varga) mapping — for owner decision 3

| Varga | Source statement (B Ch. 7 v. 1-8, printed p. 92, IT) | Domain it can serve | Direct / derived | Status | Conflict |
| --- | --- | --- | --- | --- | --- |
| D1 | physique from the ascendant | Personality (body only); General | direct | PARTIALLY | none |
| D2 | wealth from Hora | Finance, Wealth | direct | SOURCE_SUPPORTED | none |
| D3 | happiness through co-born from the decanate | Siblings, Family | direct | SOURCE_SUPPORTED | none |
| D4 | fortunes from Chaturthamsa | none of the 27 (no property or residence statement) | direct for "fortunes" | "property/home" and "foreign residence" NOT_SUPPORTED (searched B Ch. 6, 7) | DC-05: standards wording |
| D7 | sons and grandsons from Saptamsa | Children | direct | SOURCE_SUPPORTED | none |
| D9 | spouse from Navamsa | Marriage, Spouse | direct | SOURCE_SUPPORTED; "dharma" NOT_SUPPORTED | DC-05 |
| D10 | power (and position) from Dasamsa | Career (bridge: translator gloss "livelihood") | direct for "power and position" | PARTIALLY_SUPPORTED for Career | DC-04 |
| D12 | parents from Dvadasamsa | Parents, Family | direct | SOURCE_SUPPORTED; "ancestry" NOT_SUPPORTED | DC-05 |
| D16 | conveyances and related happiness | none | direct | not used | none |
| D20 | worship from Vimsamsa | Spirituality | direct | SOURCE_SUPPORTED at "worship" | none |
| D24 | learning from Chaturvimsamsa | Education | direct | SOURCE_SUPPORTED | none |
| D27 | strength and weakness | none | direct | not used | none |
| D30 | evil effects | none (policy: fear statements) | direct | not used | none |
| D40 | auspicious and inauspicious effects | General | direct | not used | none |
| D45 | all indications | General | direct | PARTIALLY | none |
| D60 | all indications | General | direct | PARTIALLY | none |
| Navamsa lord of the 10th lord | P V 1 (IT) | Career, Job, Business | direct | profile `P_V_1` | DC-04 |

## D. House mapping summary (reused Phase 12 records, plus this run's additions)

| House | BPHS Ch. 11 list (IT) | Domains with a direct term |
| --- | --- | --- |
| 1 | physique, appearance, intellect, complexion, vigour, weakness, happiness, grief, innate nature | Personality (bridge) |
| 2 | wealth, grains, family, death, enemies, metals, precious stones | Finance, Wealth, Family |
| 3 | servants, brothers and sisters, initiatory instruction, journey, parents' death | Siblings, Travel |
| 4 | conveyances, relatives, mother, happiness, treasure, lands, houses | Family, Parents (mother) |
| 5 | amulets, sacred spells, learning, knowledge, sons, authority, fall of position | Education, Children |
| 6 | maternal uncle, doubts about death, enemies, ulcers, step mother | none |
| 7 | wife, travel, trade, loss of sight, death | Marriage, Spouse, Business, Travel |
| 8 | longevity, battle, enemies, forts, wealth of the dead, past and future | none (longevity excluded) |
| 9 | fortunes, wife's brother, religion, brother's wife, visits to shrines | Spirituality, Travel, Parents (P) |
| 10 | authority, place, profession (livelihood), honour, father, living in foreign lands, debts | Career, Business, Foreign settlement, Parents |
| 11 | all articles, son's wife, income, prosperity, quadrupeds | Finance, Income |
| 12 | expenses, history of enemies, one's own death | Finance (expenses); Foreign travel and Spirituality by B 23 (derived) |

## E. Existing rules that can legitimately contribute (51 rules inspected; no rule was changed)

| Rule id | Domain | Source and location (level) | Required facts | Why applicable (the source's own words) | Status |
| --- | --- | --- | --- | --- | --- |
| `BPHS_SAN_DHANA_MOON_37_6` | Wealth, Finance | B Ch. 37 v. 6 (OT) | benefics in the 3rd, 6th, 10th, 11th from the Moon | source states "very affluent" with three, medium with two, negligible with one | SOURCE_SUPPORTED (rule tag today: general) |
| `BPHS_SAN_ADHI_MOON_37_5` | Career/status (derived) | B Ch. 37 v. 5 (OT) | benefics in the 6th, 7th, 8th from the Moon | "king, minister or army chief" by strength: position, not career as such | PARTIALLY_SUPPORTED |
| `BPHS_SAN_SUNAPHA_37_7_10`, `..ANAPHA..`, `..DURADHARA..` | Wealth (partly) | B Ch. 37 v. 7-10 (OT) | planets in the 2nd/12th from the Moon | effects mix wealth, fame, intelligence, health, virtue | PARTIALLY_SUPPORTED |
| `BPHS_SAN_VESI_38_1`, `..VOSI..`, `..UBHAYACHARI..` | Wealth, Education, status | B Ch. 38 v. 1-4 (OT) | planets in the 2nd/12th from the Sun | Vesi negligible wealth; Vosi learning and fame; Ubhayachari king-like | PARTIALLY_SUPPORTED |
| `BPHS_SAN_GAJAKESARI_36_3_4`, `PHALADEEPIKA_SASTRI_KESARI` | Wealth, Education (derived) | B Ch. 36 v. 3-4 (OT); the Phaladeepika profile is a separate one | Jupiter in a kendra from the Lagna or Moon, with a benefic | "splendorous, wealthy, intelligent... pleasing the king" | PARTIALLY_SUPPORTED; profiles not merged |
| `BPHS_SAN_LAGNADHI_36_37` | Education (derived) | B Ch. 36 v. 37 (OT) | benefics in the 7th and 8th | "a great person, learned in Sastras" | PARTIALLY_SUPPORTED |
| `BPHS_SAN_KEMADRUMA_37_11_13`, `PHALADEEPIKA_SASTRI_KEMADRUMA` | Wealth, Education | B Ch. 37 v. 11-13 (OT) | no planet with or beside the Moon | "bereft of intelligence and learning... penury": fear and derogatory wording | NOT_ENCODABLE without owner decision |
| five `BPHS_KAPOOR_PMP_75_*` | Personality, status | B Ch. 75 v. 1-2 (IT) | the planet in its sign in a kendra | already tagged personality, status in Phase 6 | SOURCE_SUPPORTED (existing tag) |
| `BPHS_KAPOOR_80_47_49_MARS_HOUSES`, `JP_KUJA_DOSHA` | Marriage | B Ch. 80 v. 47-49 (IT); Jataka Parijata v. 34 (OT, source language) | Mars houses | already tagged marriage; the BPHS tag is `marriage.spouse_longevity` (death-adjacent; owner decision) | SOURCE_SUPPORTED, two profiles, conflict group |
| 31 Nabhasa rules (`BPHS_SAN_NABHASA_*`) | none beyond `general` | B Ch. 35 (OT) | chart-pattern facts | effects were not read in this run | NOT_EVALUABLE for domains |
