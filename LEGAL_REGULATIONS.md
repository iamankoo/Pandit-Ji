# Pandit Ji — Legal & Regulatory Baseline

Status: **engineering compliance baseline — NOT legal advice, and NOT a substitute for legal clearance.** This document records what the engineering/product side has prepared for. It does not certify that Pandit Ji is legally cleared to launch.

## Legal Review Gate — REQUIRED before public launch

**Legal counsel sign-off before public launch is a required launch gate.** This baseline must not be treated as, or represented as, "final legal review complete." Actual legal clearance requires qualified legal counsel review before any public launch, covering at minimum:

- India DPDP Act / DPDP Rules
- privacy/data handling
- user deletion/retention
- Terms of Service
- Privacy Policy
- consumer/payment requirements
- Google Play compliance
- Apple App Store compliance
- Swiss Ephemeris license (see below)
- copyright/licensing of astrology sources
- AI-generated content/prediction claims
- palm-image privacy
- applicable international launch jurisdictions

Until that sign-off happens, this remains the only outstanding external gate on public/commercial launch — everything else in the Pre-Phase-1 Foundation package is an engineering/product-side preparation for that review, not a replacement for it.

## India
Baseline includes:
- Digital Personal Data Protection Act, 2023
- Digital Personal Data Protection Rules, 2025
- Information Technology Act, 2000 and applicable rules
- consumer/e-commerce/payment/tax requirements as applicable
- copyright/trademark/IP requirements

The DPDP Rules 2025 were notified on 14 Nov 2025 and use a phased commencement schedule.

## Data
Potential data: name/contact, DOB/time/place, coordinates, account data, chats, palm images, device/diagnostic data and purchases.

Build from day one:
- privacy notice
- purpose limitation
- consent/notice flows where required
- access/correction/deletion mechanisms as applicable
- retention schedules
- encryption
- access controls
- audit logs
- incident response
- vendor/data-processing inventory
- export/delete workflows
- child/minor safeguards

## Palm images (Phase 13 research record, 2026-10-02; not legal advice)
Source of this record: the Digital Personal Data Protection Act, 2023 and the DPDP Rules, 2025 (MeitY PDFs) as extracted and read on 2026-10-02, and the PIB explainer; details in `research/PALM_READING.md` section 12.

**Confirmed from the legal text read**
- The extracted text of the Act and of the Rules contains no category named "biometric" or "sensitive"; the framework does not define a special category.
- Rules 1, 2 and 17 to 21 apply from publication (the Rules were notified on 14 November 2025 per the PIB explainer); Rule 4 one year after; Rules 3, 5 to 16, 22 and 23 eighteen months after.
- Rule 3: a standalone, plain-language notice with an itemised description of the personal data and the specific purposes, and how to withdraw consent as easily as it was given.
- Rule 6: reasonable security safeguards (encryption, obfuscation, masking or tokens; access control; logs and monitoring; backups) and retention of the logs and the personal data for one year to detect and investigate unauthorised access, unless another law requires otherwise.
- Rule 7: breach intimation. Rule 8 and the Third Schedule: timed erasure for the listed classes. Rule 10 and the Act s. 9: verifiable parental consent for a child's data and no tracking or behavioural monitoring of children.

**Unresolved legal interpretation (not decided here)**
- Whether a palm image, or the line geometry extracted from it, is personal data about an identifiable person, and whether it is biometric or sensitive in any applicable law.
- The notice wording and legal basis for storing derived palm facts; how Rule 6's one-year retention coexists with minimum retention of images.
- Whether any Third Schedule class or Significant Data Fiduciary status applies.
- Consent, withdrawal and deletion for dataset use once a model has been trained; minors and age assurance; whether the older Information Technology Act rules on sensitive personal data still apply during the transition.

**Policy and engineering decisions recorded**: minors excluded until counsel clears the workflow; training on user images off by default; the prohibited readings; images referenced by id and never logged (`PRODUCT_POLICIES.md`, standards PM-13, PM-17).

**Production-launch legal review gates (locked 2026-10-02; none is presented as resolved)**: whether palm images constitute personal data in the relevant context; the legal basis and notice and consent requirements; the treatment of derived palm facts; retention and deletion requirements; the interaction between audit logging and deletion; the applicability of the Third Schedule and other relevant DPDP provisions; dataset consent withdrawal after training; minors and children; whether any palm-derived data creates additional regulatory obligations; training-data consent and reuse. Palm reading is not offered publicly until counsel completes the review; minors remain excluded from the initial palm dataset and the production palm-reading scope until counsel clears the workflow. Phase 13 engineering may proceed on synthetic, fixture or internal appropriately governed data. This record does not replace the legal review gate at the top of this document.

## Google Play
Maintain accurate Data Safety disclosures, privacy policy, permission disclosures, compliant payments, and account/data deletion. Apps with account creation must provide an in-app and external account-deletion path.

## Apple
Comply with App Review Guidelines, privacy requirements and in-app purchase rules. Pandit Ji's locked pricing (`PRICING.md`: first month free, then ₹1 per mobile number per 12 hours) is a consumable, time-boxed purchase, not an auto-renewing subscription — treat it under consumable in-app purchase rules, not the auto-renewing-subscription disclosure requirements, and confirm this classification with each store's current policy before launch.

## Swiss Ephemeris — LOCKED licensing decision

**Locked decision: Pandit Ji will use the Swiss Ephemeris Professional License**, not the AGPL option.

Reasoning:
- Pandit Ji is a proprietary commercial product; the AGPL option would impose copyleft obligations incompatible with that.
- Pandit Ji will eventually operate both distributed mobile applications and server-side calculation services; the Professional License explicitly supports commercial project/server use, where the AGPL option does not fit a closed-source distribution model.

This is a locked architectural/licensing decision, not yet an executed purchase:
- The Professional License has **not** been purchased or contracted as of this writing.
- Procurement (purchase + signed agreement with Astrodienst) is a **pre-production/legal task**, to be completed before public/commercial distribution or public-service activation — not before internal development/testing.
- The signed agreement must be obtained and retained before Pandit Ji is distributed publicly or offered as a commercial server-side service.

Pricing reference (currently published by Astrodienst, **subject to verification at procurement time** since Astrodienst may change published rates): first Professional License fee CHF 750, each additional license by the same licensee CHF 400, unlimited license CHF 1550. Source: [Swiss Ephemeris price list and order](https://www.astro.com/swisseph/swephprice_e.htm) (Astrodienst).

## AI/IP
Maintain a registry for texts, translations, datasets, models, images, voices and code dependencies. Do not ingest/distribute copyrighted material without a valid legal basis/license.

### Self-hosted LLM: model and runtime licence record (Phase 14, 2026-10-03; not legal advice, not legal approval)
Engineering read the licence material below to choose a model; counsel has **not** reviewed it. Status: `LEGAL_REVIEW_REQUIRED`, and it joins the production launch gates.
- **Model**: `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`. The host metadata names Apache-2.0 and the repository's LICENSE file (SHA-256 `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e`) is the standard Apache License 2.0 text with a copyright line for the model's publisher; no use-scale or field-of-use clause was found in it. The model is ungated. Commercial use, redistribution and derivative works are permitted by that text subject to its notice conditions; fine-tuned derivatives are not part of Phase 14 and would be separately versioned and reviewed. The Apache-2.0 patent and trademark provisions were not analysed.
- **Runtime and libraries**: vLLM is Apache-2.0 per its package metadata; `jinja2` is BSD-licensed and `jsonschema` is MIT per their package metadata. No copyleft dependency was added.
- **Other candidates read** (tags only, texts not read): Llama 3.1 (a vendor community licence, gated), Mistral-Nemo (Apache-2.0 tag, ungated), Gemma 3 (the vendor's own terms, gated). Their terms were not analysed and nothing here approves or rejects them (`research/AI_MODELS.md`).
- **Weights provenance**: the weight files' SHA-256 values are the host's published object ids; the repository never contains the weights, and the loader verifies a local copy against the manifest before use. Whether the publisher's training data raises any rights question is not assessed.
- **Data boundary**: a self-hosted model receives only the evidence the caller supplies; no hosted third-party model API is called, so no user content is sent to a model vendor by this layer. No user data is used to train or fine-tune anything in Phase 14.
- **Agent and narration (Phase 15, 2026-10-03)**: the agent adds no dependency, sends no content to any third party and stores no user data (its memory keeps labels in process memory only). Its request and output screens for prohibited readings use the Phase 13 English lexicon plus a small Hindi and Hinglish supplement; that coverage is partial and the domain scoping of the prohibitions (palmistry: all categories; astrology: lifespan refused, high-impact topics interpreted with a disclaimer) is owner-locked (2026-10-03). Counsel review of both remains required: `LEGAL_REVIEW_REQUIRED` and join the launch gates; nothing here resolves whether AI-generated interpretive text on health, finance or relationship topics carries further obligations.

- **Verification (Phase 16, 2026-10-05)**: the verification layer adds no dependency, calls no model or third-party service, stores no user data and logs no claim text, prompt or image reference (a result holds identifiers, reason codes, hashes and versions, and a hash of the claim text). It carries its own copy of the prohibited-category screens (the Phase 13 English lexicon, the agent's Hindi and Hinglish supplement, and an astrology death-timing pattern); a repository test keeps the supplement identical to the agent's. `LEGAL_REVIEW_REQUIRED`: counsel review of those screens and of the wording of `VERIFIED` in any user-facing text (it means supported by the application's encoded evidence, not true, not scientifically validated and not production-grade). Nothing here is legal clearance.
- **Life-domain intelligence (Phase 17 research lock, 2026-10-06; nothing implemented; not legal advice)**: `LEGAL_REVIEW_REQUIRED` items found by the research and not decided: interpretation of children, fertility, pregnancy and paternity in astrology (the sources contain statements the Phase 13 palmistry policy prohibits; the astrology policy is silent); relationship, love, marriage and children readings for minors (no age gate exists); the wording of derogatory or fear-based statements found in the classical sources; finance and wealth interpretation and its disclaimer; health interpretation if the owner adds a health domain. See `research/PHASE_17_LIFE_DOMAIN_RESEARCH.md` section 11.
- **Open items for counsel**: the licence and notice obligations on distribution of the weights or a derivative; whether model outputs about palm or chart evidence engage any of the Phase 13 palm-image items; and the Hindi and Hinglish coverage of the prohibited-output controls (the output scan is English only).

This is not legal advice.
