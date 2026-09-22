"""Phase 9 WP-C: a continuous, degree-based refinement of planet-to-house
aspect strength, layered on top of the already-locked Phase 5 discrete
house-offset aspect table (`pandit_astro_engine.aspects`).

Two independent, never-merged profiles, per `docs/ASTROLOGY_STANDARDS.md`
v1.12.0/v1.13.0 (PD-01 to PD-11):

- `bphs` -- BPHS Ch. 26 (`PARTIAL_DEGREE_DRISHTI_BPHS_26`).
- `uttarakalamrita` -- Uttara Kalamrita Ch. 2, citing Sripatipaddhati-II
  (`PARTIAL_DEGREE_DRISHTI_UTTARAKALAMRITA_SRIPATI`). Not implemented by
  this work package.

There is no default profile, no shared calculation entry point and no
mergeable result type between them -- each module owns its own complete
request/result/status/reason types.
"""

from __future__ import annotations
