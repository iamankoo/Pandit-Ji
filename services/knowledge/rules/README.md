# Rule source-of-truth (`rules/**/*.yaml`)

This directory is the versioned YAML source-of-truth for astrology rules (`docs/ARCHITECTURE.md` §7), loaded by `services/rule-engine` with a canonical content hash as the ruleset version.

Layout, by source tradition (never merge materially different traditions):

- `ruleset.yaml`: the ruleset manifest (ruleset ID, version, schema version, standards version).
- `bphs/`: Brihat Parasara Hora Sastra profiles and methodology tables (`bphs/tables/`).
- `phaladeepika/`: Phaladeepika profiles (separate traditions of the same yoga).
- `jataka_parijata/`: Jataka Parijata profiles.
- `modern/`: reserved for clearly tagged `MODERN_TRADITION` profiles (none yet; canonical Kaal Sarp is not implemented).

Every document carries its source, edition, translator, source location, source version, tier and verification level (`research/ASTROLOGY_SOURCES.md` §6). Rule IDs are the finalized profile IDs of that registry. A document is one of `ruleset`, `table` or `rule`; multi-document YAML files are allowed. Rules contain declarative conditions only, never code, and interpretation tags only, never prose.
