"""`/api/v1` versioning foundation.

No domain routes yet -- `/charts`, `/dashas`, `/transits`, `/panchang`,
`/muhurta`, `/compatibility`, `/numerology`, `/chat`, `/reports`,
`/memory`, `/admin/rules` are added starting the `Phases.md` phase that
implements each corresponding engine (see `docs/ARCHITECTURE.md` §"API
Architecture" for the full category table). A breaking change to this
version introduces `/api/v2`, per that same section's versioning strategy.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")
