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

This is not legal advice.
