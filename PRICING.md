# Pandit Ji — Pricing Framework

Status: **LOCKED** — explicit project-owner decision. This supersedes the previously proposed commercial baseline (see Changelog). Authority: per `SOURCE_OF_TRUTH.md`, an explicitly locked project-owner decision is the highest-authority source in this project, above `features.md`, `Phases.md`, and every other document.

## Locked pricing model

**First month free. Thereafter, ₹1 per mobile number for 12 hours.**

- First 1 month of service: **free**, no payment required.
- After the free month: **₹1 activates the service for exactly 12 hours**, scoped to **one mobile number**.
- Each ₹1 payment buys one 12-hour access window for that mobile number. When the 12 hours end, access ends until the next ₹1 payment.
- To continue after a 12-hour window expires, the user pays ₹1 again to activate the next 12-hour period.
- Access is **per mobile number**, not per account, per device, per conversation, or per feature. One mobile number paying once covers all features/usage for that number for that 12-hour window — there are no separate tiers, credit packs, or per-report charges layered on top.

## Explicitly removed / superseded

The following are no longer valid and must not be used anywhere in the product, marketing, or documentation:

- ₹99/month "Starter" tier
- ₹249/month "Pro" tier
- ₹1,999/year "Annual Pro" tier
- Credit packs (₹49 / ₹99 / ₹199 / ₹499)
- Per-report pricing (short/detailed/comprehensive/specialized report price bands)
- Any framing of pricing as per-account, per-device, per-conversation, or per-feature rather than per mobile number

## Pricing principles

- No hidden recurring charges — this model has no auto-renewal at all; each 12-hour window requires a fresh, explicit ₹1 payment.
- Show the user exactly what a ₹1 payment buys (12 hours of access for that mobile number) before they pay.
- State refund/cancellation terms for the ₹1 payment clearly (e.g., non-refundable once the 12-hour window has started, if that is the policy — confirm with payment/store requirements).
- Never imply payment increases prediction certainty. No fear-based selling.
- Do not gate critical safety information behind payment (see `PRODUCT_POLICIES.md`).

## Implementation notes (non-pricing, for engineering awareness)

- Access control keys off **verified mobile number**, not user account ID alone — requires mobile-number verification (e.g., OTP) as part of the payment/activation flow.
- This is a consumable, time-boxed purchase, not an auto-renewing subscription — app-store compliance treatment differs accordingly (see `LEGAL_REGULATIONS.md`).
- Unit economics (model inference, ephemeris, storage, palm vision, payment/store fees, taxes, refunds, support, acquisition cost) should still be monitored against the locked ₹1/12-hour price to confirm sustainability, even though the price itself is no longer open for the unit-economics gate to change — if margins are unsustainable, that is now a scope/cost problem to solve, not a re-pricing decision.

## Competitor observations (unchanged, informational only)

AstroSage public pages currently show selected paid services/reports around ₹299, ₹399, ₹499 and ₹996. KundliGPT currently uses coins/pay-as-you-go plus a 1-day unlimited-chat pass and says it has no recurring subscription. These are observations about competitors, not Pandit Ji's own pricing, and should be rechecked periodically — they do not affect the locked model above.

## Changelog / Decision Record

- **Locked pricing decision (supersedes prior proposal):** Pandit Ji's commercial model is now **first month free, then ₹1 per mobile number per 12 hours**, replacing the previously proposed hybrid free/₹99/₹249/₹1,999/credits/reports model in its entirety. This is an explicitly locked project-owner decision and takes precedence over the prior "PROPOSED COMMERCIAL BASELINE — not LOCKED" status and its unit-economics gate on the *price itself*.
