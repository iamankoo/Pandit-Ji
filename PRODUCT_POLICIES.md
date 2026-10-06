# Pandit Ji Product Policies

## Accuracy
Target deterministic calculation accuracy, reproducibility, rule traceability, evidence-backed interpretation and measured predictive performance. Do not claim guaranteed 100% future prediction.

## AI
Use evidence bundles; ask for missing critical data; distinguish fact from interpretation; expose uncertainty; never fabricate chart facts, rules or citations.

Agent and narration (Phase 15, 2026-10-03; `docs/ARCHITECTURE.md` section 37, ADR-010): the agent narrates only evidence it was handed, keeps observed, derived, calculated and rule-evaluation evidence distinct, keeps the astrology and palmistry domains apart, preserves confidence, uncertainty, source profile and knowledge version, and states what the evidence does not cover. Narration is `UNVERIFIED` until Phase 16 verifies it, and always says so. Domain scope of the prohibitions, as **locked by the owner on 2026-10-03**: palmistry refuses and never produces every category listed under Palm images below; astrology gives contextual, traditional interpretation of high-impact topics with a professional-advice disclaimer, never guarantees an outcome, and refuses lifespan and death-timing requests (the Ayurdaya exclusion). A request that tries to override the agent's rules, extract its instructions, alter evidence or have a narration marked verified is refused. Phase 15 checks the structure and reference integrity of a narration only; whether its text is supported by the evidence is decided by Phase 16, the only phase that may mark a claim verified. The agent selects only among allow-listed deterministic evidence tools (no model-chosen function calling), and keeps only in-session conversation context; persistent memory belongs to later infrastructure.

Verification (Phase 16, 2026-10-05; `docs/ARCHITECTURE.md` section 38, ADR-011): the verification layer decides, deterministically and without a model, whether each generated claim is supported by the application's encoded evidence and rule model, and it is the only layer that may mark a claim verified. A verified claim is not a statement that astrology or palmistry is scientifically valid, and it is not a guarantee of any outcome; a claim is never verified because the model said it was true, because it carries a reference id or because it sounds plausible. Every prohibition above is enforced again at verification: a prohibited claim is blocked, never verified. Conflicting source profiles are never merged, and uncertain, not-evaluable or incomplete evidence is never verified. Text the verifier cannot read is reported as unverifiable, not assumed supported. Narration that is not fully verified may be released only in the verified part, or regenerated; the user-facing release flow is composed in Phase 18.

Life-domain intelligence (Phase 17, owner decisions of 2026-10-06; `docs/ASTROLOGY_STANDARDS.md` LD-20 and LD-26, ADR-012; not implemented yet): only source-backed domains reason substantively and the rest say they cannot be evaluated; nothing is invented. **Minors**: no astrology interpretation involving minors until the product and legal policy exists; age is never inferred and there is no minor-specific prediction mode. **Fertility and pregnancy**: no predictive outcomes; historical statements about offspring are not turned into user-facing predictions. **Finance**: traditional or interpretive guidance only, never a guaranteed outcome, investment advice, certainty, guaranteed wealth or guaranteed profit or loss, with the professional-advice disclaimer. **Health**: interpretation only, never a diagnosis, a medically certain prediction, a treatment recommendation or a substitute for medical professionals (separate from the palmistry policy). **Subject sex**: never required or inferred to reproduce a historically gendered method; where a source-backed method needs it and it is unavailable the result is not evaluable. **Historical source statements** about fear, illegitimacy, moral judgment, derogatory character or social stigma are not user-facing claims: provenance is kept and a policy transformation precedes narration. **Spouse longevity**: never used for user-facing lifespan or death prediction; the existing astrology lifespan and death-timing prohibition is not bypassed. Counsel review of all of these remains required.

## Personalization
Saved birth profiles, language preference, explicit preferences and conversation context may personalize responses. Training data remains separate and requires privacy/consent/approval controls.

## Data & Privacy Principles

Product/technical privacy principles that all Pandit Ji services must follow (this section is the authoritative product-level statement referenced by `docs/ASTROLOGY_STANDARDS.md`'s "Data/privacy rules" requirement; `LEGAL_REGULATIONS.md` remains the detailed legal/compliance baseline these principles must satisfy — this section states product principles and links to that document rather than duplicating its legal text):

- **Data minimization**: collect only what a feature actually needs to function; do not collect birth data, location, or other personal data speculatively for features not yet built.
- **Purpose limitation**: data collected for one purpose (e.g., chart calculation) is not repurposed for another (e.g., model training) without separate, explicit consent.
- **Consent/notice**: present clear notice and obtain consent before collecting sensitive data (birth details, location, palm images, conversation history), per `LEGAL_REGULATIONS.md`'s applicable requirements.
- **Birth-data handling**: date/time/place of birth is high-sensitivity data — encrypted at rest, access-controlled, never shared with third parties beyond what the service requires to function.
- **Location-data handling**: same treatment as birth data; coordinates/timezone are stored only as needed for calculation and Panchang/Muhurta lookups.
- **Conversation-data handling**: retained per a defined retention schedule for personalization and conversation memory (see `docs/ARCHITECTURE.md`'s Memory & Personalization subsystem); never used to train models without separate explicit consent (see Personalization above).
- **Palm-image handling**: see Palm images below — same high-privacy treatment (purpose disclosure, minimum retention, deletion controls, no secondary use without valid authorization).
- **Retention/deletion**: defined retention schedules per data category; user-triggered deletion requests are honored.
- **Access control**: role-based access to sensitive data internally; no broad/default access.
- **Encryption**: at rest and in transit for all sensitive data categories above.
- **Auditability**: access to sensitive data (birth data, palm images, conversations) is logged in an append-only audit trail (see `LEGAL_REGULATIONS.md`'s Data section).
- **Personalization vs. training-data separation**: see Personalization above — saved profiles/preferences/conversation context may personalize a user's own responses; none of it is used as model-training data without separate privacy/consent/approval controls.
- **Third-party/vendor restrictions**: no unnecessary third-party sharing; any vendor/data-processor is tracked in the vendor/data-processing inventory required by `LEGAL_REGULATIONS.md`.
- **User data export/deletion principles**: users can request export and deletion of their own data; self-service where feasible, supported operationally otherwise.
- **Minor/child safeguards**: see Minors below.

## High-impact topics
For health, finance, legal, relationships, pregnancy, death and similar topics, provide contextual/traditional interpretation without presenting astrology as professional advice or a substitute for qualified services.

## Prediction
Include relevant periods where possible. No guaranteed outcomes, fear-based claims, fabricated certainty or coercive upselling.

## Remedies
Never present remedies as medically proven or guaranteed to change destiny. Paid remedies must clearly state deliverable, price, terms and refund/cancellation rules.

## Minors
No sexualized, exploitative or manipulative readings involving minors. Apply age-appropriate controls to relationship/marriage features.

## Palm images
Treat palm images as high-privacy visual data: purpose disclosure, minimum retention, deletion controls, and no secondary use without valid authorization.

Owner decisions of 2026-10-02 (Phase 13; `research/PALM_READING.md`, standards PM-13, PM-17):
- **Minors**: excluded from palm-image collection and analysis until legal counsel clears the workflow.
- **Training on user images**: off by default. A user image becomes training or evaluation data only with a separate, explicit authorisation, never as a side effect of using the service.
- **Prohibited readings**: no medical diagnosis, no disease prediction, no death prediction and no lifespan prediction from a palm image. **Permanently** also prohibited (final owner decision, 2026-10-02; standards PM-25): palmistry interpretation concerning criminality, mental illness or psychiatric diagnosis, fertility, paternity, sexual conduct, ethnic or racial ranking, intellectual superiority or inferiority, moral character labelling, and any claim that a person is inherently good or bad, pure or impure, trustworthy or untrustworthy based on palm features. These categories are never training labels. The vision layer is descriptive and may detect a physical feature for a legitimate technical reason, but that feature is never turned into one of these claims. Palmistry content is presented as traditional and interpretive, not as scientifically established fact.
- **Source and tradition scope**: the initial palmistry methodology is Western only, from source-backed rules (a small fixture set first, broader coverage later by controlled expansion); Indian Hasta Samudrika is `RESEARCH_PENDING` and produces no interpretation; concepts that were not read produce nothing.
- **Dataset**: no user image is silently added to a training or evaluation dataset; production palm images are not training data by default; a separately governed consented adult dataset is the only source; no skin-tone label is mandatory for fairness analysis.
- **Logs and the model**: images are referenced by id; no pixels, landmarks or line geometry in logs; the AI model and agent never receive pixels.
- **Launch gate**: legal counsel review remains required before launch (`LEGAL_REGULATIONS.md`).

## Integrity
No fake astrologer identities, testimonials, success stories or citations.

## Monetization
Do not make predictions scarier or more certain to increase sales. Do not gate critical safety information behind payment. Current locked pricing model: see `PRICING.md` (first month free; thereafter ₹1 per mobile number for 12 hours) — do not restate specific prices/tiers here or elsewhere; reference `PRICING.md` as the single source for pricing figures.

## Licensing & legal gate
Calculation accuracy above depends on Swiss Ephemeris, licensed under the locked Swiss Ephemeris Professional License (see `LEGAL_REGULATIONS.md`); do not distribute or activate public/commercial service before that license is purchased and the agreement is signed. This document is an engineering/product compliance baseline, not legal advice — public launch additionally requires qualified legal counsel sign-off (see `LEGAL_REGULATIONS.md`'s Legal Review Gate), which remains outstanding.
