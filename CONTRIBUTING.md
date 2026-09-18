# Contributing

Pandit Ji is developed strictly phase-by-phase per `Phases.md` (the sole authoritative execution roadmap — see `SOURCE_OF_TRUTH.md` for the full authority order). Before starting any work, read `Phases.md` to confirm the current phase, its deliverables, dependencies, exit criteria, and explicitly excluded work.

## Engineering workflow

1. Branch from `main`.
2. Make focused changes that belong to the current phase only — do not pull work forward from a later phase (see `docs/DEVELOPMENT.md` for the local dev/test loop).
3. Run the relevant checks locally (lint, format, type-check, tests — see `docs/DEVELOPMENT.md`) before opening a pull request. `pre-commit install` once per clone catches the fast subset automatically.
4. Open a pull request against `main`. CI (`.github/workflows/ci.yml`) must pass.
5. Keep canonical service names (`astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`) exactly as locked — never rename or alias them.

## Git identity and attribution

All commits use the project-owner identity `iamankoo <aniketraj00384@gmail.com>`. Do not add AI-assistant/tool attribution (author, committer, commit message, trailers, code comments, or documentation) — the project's contributor history reflects the project owner only.

## Locked decisions

Do not change locked decisions (pricing, astrology standards, product scope, palm-reading inclusion, canonical service names, the self-hosted-AI requirement, the Swiss Ephemeris decision, phase ordering, or Phase 2 architecture decisions) without an explicit project-owner decision. If you find a contradiction between documents, record it (e.g. in `docs/ARCHITECTURE.md` §"Known Contradictions") rather than silently resolving it — see `SOURCE_OF_TRUTH.md`'s conflict rule.

## Where things live

- `features.md` — product scope
- `Phases.md` — execution roadmap
- `docs/ASTROLOGY_STANDARDS.md` — calculation/interpretation standards
- `docs/ARCHITECTURE.md` — technical architecture (see `docs/architecture/` for diagrams and ADRs)
- `TECH_STACK.md` — locked technology choices
- `PRODUCT_POLICIES.md`, `LEGAL_REGULATIONS.md` — product and legal/compliance baselines
