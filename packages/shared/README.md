# pandit-shared

Cross-cutting Python utilities used by `server/` and every `services/*` component: a base typed-settings class (`BaseServiceSettings`: `APP_ENV`, `LOG_LEVEL`) and structured JSON logging (`configure_logging`, `bind_request_id`).

Nothing domain-specific (astrology, agent, verification) lives here — see `docs/ARCHITECTURE.md` §"Repository Structure".

## Install (editable, for local development)

```
pip install -e ".[dev]"
```
