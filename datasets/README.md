# datasets

Foundation directory for future golden fixtures, rule test fixtures, and backtesting data (`docs/ARCHITECTURE.md` §"Repository Structure").

## Phase 3 status

Directory structure only — **no data exists here yet**. No fake astrology training data, no invented palm-reading datasets, no copyrighted books or scraped material has been added, per this phase's explicit scope boundary.

## Subdirectories

- `fixtures/` — golden birth-data + independently cross-checked expected outputs, added starting `Phases.md` Phase 4 (astronomical calculation golden fixtures) and used throughout Phases 4–13.
- `backtesting/` — historical prediction/outcome data for the backtesting framework (`docs/ARCHITECTURE.md` §"Verification Architecture"), added starting `Phases.md` Phase 21.
- `palm-reading/` — palm-vision evaluation datasets, added starting `Phases.md` Phase 13, subject to the same privacy handling as live palm images (`PRODUCT_POLICIES.md`). **Specification (Phase 13 research lock, 2026-10-02; `research/PALM_READING.md` section 11, standards PM-19):** production training and evaluation use a purpose-built consented internal dataset (itemised notice, separate consents, adults only until counsel clears minors, diverse devices, lighting, hand sizes, sides and image quality, a versioned annotation guideline, two annotators with adjudication, agreement measured, splits by contributor, leakage prevention, a provenance manifest and a licensing record). **Image files never enter git**: they live in encrypted private object storage; only manifests (hashes and metadata, no pixels) and evaluation reports may be committed. Public datasets (for example 11K Hands, whose stated terms are "free for reasonable academic fair use") are used only for research and baselines after their licence and provenance are verified and recorded, and are never committed. No dataset exists here yet and none has been collected.

Every dataset added here must record its source and license/authorization basis (see `research/ASTROLOGY_SOURCES.md`'s source-registry fields) before being used.
