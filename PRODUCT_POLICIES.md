# Pandit Ji Product Policies

## Accuracy
Target deterministic calculation accuracy, reproducibility, rule traceability, evidence-backed interpretation and measured predictive performance. Do not claim guaranteed 100% future prediction.

## AI
Use evidence bundles; ask for missing critical data; distinguish fact from interpretation; expose uncertainty; never fabricate chart facts, rules or citations.

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

## Integrity
No fake astrologer identities, testimonials, success stories or citations.

## Monetization
Do not make predictions scarier or more certain to increase sales. Do not gate critical safety information behind payment. Current locked pricing model: see `PRICING.md` (first month free; thereafter ₹1 per mobile number for 12 hours) — do not restate specific prices/tiers here or elsewhere; reference `PRICING.md` as the single source for pricing figures.

## Licensing & legal gate
Calculation accuracy above depends on Swiss Ephemeris, licensed under the locked Swiss Ephemeris Professional License (see `LEGAL_REGULATIONS.md`); do not distribute or activate public/commercial service before that license is purchased and the agreement is signed. This document is an engineering/product compliance baseline, not legal advice — public launch additionally requires qualified legal counsel sign-off (see `LEGAL_REGULATIONS.md`'s Legal Review Gate), which remains outstanding.
