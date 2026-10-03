# Palm ruleset (`services/rule-engine/palm_rules/`)

The **separate** palmistry ruleset (Phase 13; standards PM-12, PM-20, PM-25 to PM-31; ADR-008). It is
**not** the Phase 6 Vedic ruleset and must never be mixed with it:

- palm rules live **only here**, never under `services/knowledge/rules/` (the knowledge service hashes
  every YAML there and the Vedic loader reads it);
- its own manifest (`ruleset.yaml`, `PANDIT_JI_PALM_WESTERN_PHASE13`), version and content hash;
- its own identifier namespace (`PALMR_`) and document types (`palm_ruleset`, `palm_rule`,
  `palm_tag_vocabulary`, `palm_conflict`): the Vedic loader rejects them and the palm loader rejects
  Vedic documents.

**This is a small source-backed FIXTURE set that proves the architecture, not the production palmistry
rule list** (owner decision B). Each rule belongs to exactly one source profile and one source location,
is backed by the source coverage manifest (`services/knowledge/content/palm/source_coverage.yaml`), emits
only tags from the closed `tag_vocabulary.yaml`, contains no prose and predicts no event. No rule here is
medical, death, lifespan, criminality, mental illness, fertility, paternity, sexual conduct, ethnic or
intellectual ranking, moral labelling, or an inherent good/bad claim. Source conflicts are recorded in
`conflicts.yaml` as `UNRESOLVED_CONFLICT`; no winner is chosen and no tags are merged.

The two line-origin rules need line-role facts that the vision pipeline does not yet produce (no validated
role assignment, no trained palm-line model), so on real pipeline output they evaluate to `NOT_EVALUABLE`.
