# Pandit Ji

Self-hosted AI astrology platform. Status: **Phase 5 — Birth Chart / Kundli Engine** (see `Phases.md`).

`Phases.md` is the sole authoritative execution roadmap. `features.md` defines WHAT the product contains. `docs/ASTROLOGY_STANDARDS.md` defines calculation/interpretation standards. `docs/ARCHITECTURE.md` defines technical structure. `TECH_STACK.md` defines locked technology choices. See `SOURCE_OF_TRUTH.md` for the full authority order.

Locked product baseline: self-hosted AI astrology platform; Android+iOS first; English/Hindi/Hinglish; AstroSage+KundliGPT feature baseline; AI palm reading.

Core invariant: **FACTS FLOW ONE DIRECTION; AI ONLY NARRATES.**

## Repository layout

```
apps/           mobile (Flutter), web (Next.js), admin (Next.js)
server/         FastAPI HTTP composition layer (ADR-007)
services/       astro-engine, rule-engine, agent, knowledge, verification (canonical, locked names)
packages/       shared, contracts, ui
datasets/       golden fixtures, backtesting data, palm-reading datasets (foundation only, no data yet)
tests/          cross-cutting integration/contract tests and shared fixtures
docs/           architecture, astrology standards, diagrams, ADRs, development guide
infrastructure/ Docker Compose, Traefik gateway config, Alembic migrations, environment templates
```

Every canonical service/app/package name above is locked (`docs/ARCHITECTURE.md` §"Repository Structure") — do not rename or introduce alternatives (`astrology-engine`, `ai-agent`, `knowledge-base`, etc.).

## Getting started

See `docs/DEVELOPMENT.md` for prerequisites, local setup, running the backend/clients, testing, and linting. See `CONTRIBUTING.md` for the engineering workflow.

This README stays concise and links out — it is not a second source of truth for architecture, standards, or the roadmap.

## Legal

This project is an engineering/product baseline and does not replace legal counsel.
