# verification

Independent verification layer (`docs/architecture/adr/ADR-006-verification-independent-layer.md`). Canonical service name.

**Responsible for**: fact validation, rule validation, evidence validation, unsupported-claim detection, contradiction detection; regression-test and backtesting framework (see `docs/ARCHITECTURE.md` §"Verification Architecture").

**Not responsible for**: generating narrative content, or being a generic grammar/style checker.

## Phase 3 status

Foundation only: package boundary, config, health check. No verification logic yet — that begins in `Phases.md` Phase 16.

## Local development

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```
