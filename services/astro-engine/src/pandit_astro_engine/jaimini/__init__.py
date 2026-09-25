"""Phase 9 Jaimini-style systems. See `docs/ASTROLOGY_STANDARDS.md` section
"Jaimini standards" and `research/ASTROLOGY_SOURCES.md` Groups 12, 13 and 18.

- WP-B-1: Rashi Drishti, sign to sign (`rashi_drishti`, BPHS Ch. 8 v. 1-3).
- WP-B-2: Chara Karaka and Constant Karaka (`chara_karaka`, `constant_karaka`,
  BPHS Ch. 32).
- WP-G: planet-level Rashi Drishti (`planet_rashi_drishti`, Ch. 8 v. 4-5),
  Bhava and Graha Arudha Padas (`arudha`, Ch. 29 v. 1-7) and Karakamsa
  (`karakamsa`, Ch. 33 v. 1-2).

Every system here is kept apart from the Phase 5/6 graha drishti. Jaimini
Dashas and the interpretive chapters (Ch. 29 v. 8 onward, Ch. 30-31, Ch. 33
v. 2 onward) are not implemented.
"""

from __future__ import annotations
