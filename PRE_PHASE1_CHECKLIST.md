# Pre-Phase-1 Completion Checklist

[x] Astrology standards
[x] Source-of-truth hierarchy
[x] Product policies
[x] Legal/regulatory baseline
[x] Pricing framework
[x] Ephemeris research
[x] Astrology source research
[x] AI model research
[x] Palm-reading research
[x] Backtesting/evaluation research
[x] Competitor research

## Explicit decisions still needed before implementation
1. ~~Ephemeris license: AGPL vs Professional.~~ **RESOLVED — LOCKED**: Swiss Ephemeris Professional License. See `LEGAL_REGULATIONS.md` and `research/EPHEMERIS.md`. Not yet purchased — procurement (purchase + signed Astrodienst agreement) remains a pre-production/legal task before public/commercial distribution.
2. ~~Resolve repository/service naming conflicts between `Phases.md` and `ARCHITECTURE.md`.~~ **RESOLVED — LOCKED**: canonical services are `astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`; canonical apps are `mobile`, `web`, `admin`; canonical packages are `shared`, `contracts`, `ui`. See `Phases.md` Phase 3 and `docs/ARCHITECTURE.md` §11. (Implementation note, not a gate: the locked `apps/` list has no `api` entry, where earlier drafts placed the FastAPI HTTP layer — `docs/ARCHITECTURE.md` §17 records this as a placement detail to settle during Phase 3/9 execution, not a blocker on starting Phase 1.)
3. ~~Resolve standards filename/location conflict.~~ **RESOLVED — LOCKED**: canonical standards document is `docs/ASTROLOGY_STANDARDS.md`; there is no separate `docs/calculation-standards.md`.
4. ~~Final commercial pricing after unit-economics tests.~~ **RESOLVED — LOCKED**: first month free, then ₹1 per mobile number per 12 hours. See `PRICING.md`. Unit-economics monitoring continues, but the price itself is no longer open.
5. **Legal counsel sign-off before public launch — REQUIRED LAUNCH GATE.** Not marked complete and must never be marked complete by this checklist alone: the engineering/legal compliance baseline (`LEGAL_REGULATIONS.md`) is prepared, but actual legal clearance requires qualified legal counsel review before public launch, covering (at minimum) India DPDP Act/Rules, privacy/data handling, user deletion/retention, Terms of Service, Privacy Policy, consumer/payment requirements, Google Play compliance, Apple App Store compliance, the Swiss Ephemeris license, copyright/licensing of astrology sources, AI-generated content/prediction claims, palm-image privacy, and applicable international launch jurisdictions.

Items 1-4 above are now resolved/locked. Start exactly at `Phases.md` → Phase 1 → Step 1. Item 5 (legal counsel sign-off) is a separate, ongoing external gate on **public launch**, not on starting Phase 1 implementation work — it is the only remaining external gate after this reconciliation.
