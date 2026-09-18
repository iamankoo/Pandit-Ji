# datasets

Foundation directory for future golden fixtures, rule test fixtures, and backtesting data (`docs/ARCHITECTURE.md` §"Repository Structure").

## Phase 3 status

Directory structure only — **no data exists here yet**. No fake astrology training data, no invented palm-reading datasets, no copyrighted books or scraped material has been added, per this phase's explicit scope boundary.

## Subdirectories

- `fixtures/` — golden birth-data + independently cross-checked expected outputs, added starting `Phases.md` Phase 4 (astronomical calculation golden fixtures) and used throughout Phases 4–13.
- `backtesting/` — historical prediction/outcome data for the backtesting framework (`docs/ARCHITECTURE.md` §"Verification Architecture"), added starting `Phases.md` Phase 21.
- `palm-reading/` — palm-vision evaluation datasets, added starting `Phases.md` Phase 13, subject to the same privacy handling as live palm images (`PRODUCT_POLICIES.md`).

Every dataset added here must record its source and license/authorization basis (see `research/ASTROLOGY_SOURCES.md`'s source-registry fields) before being used.
