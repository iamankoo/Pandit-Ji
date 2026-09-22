"""Ashtakavarga calculation service facade (Phase 9 WP-A1).

    AshtakavargaRequest -> AshtakavargaCalculationService -> AshtakavargaFacts

Stateless, matching the other astro-engine services. Domain failures come
back as structured `AshtakavargaFacts` (status plus reason code), never as a
stack trace. No ephemeris access: this module needs only natal sign
placements, already available from a Phase 5 Kundli.
"""

from __future__ import annotations

from pandit_astro_engine._version import __version__
from pandit_astro_engine.ashtakavarga.calculator import (
    compute_bhinnashtakavarga,
    compute_lagna_chart,
    compute_sarvashtakavarga,
)
from pandit_astro_engine.ashtakavarga.constants import CONTRIBUTOR_ORDER, Contributor
from pandit_astro_engine.ashtakavarga.models import (
    AshtakavargaFacts,
    AshtakavargaReason,
    AshtakavargaRequest,
    AshtakavargaStatus,
    NatalPositions,
    ProfileSummary,
)
from pandit_astro_engine.ashtakavarga.profiles import PROFILES
from pandit_astro_engine.kundli_models import Kundli
from pandit_astro_engine.rashi import sign_index_from_longitude


def _finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


class AshtakavargaCalculationService:
    def calculate(self, request: AshtakavargaRequest) -> AshtakavargaFacts:
        try:
            return self._calculate(request)
        except Exception:  # never leak a stack trace through a fact result
            return AshtakavargaFacts(
                status=AshtakavargaStatus.INTERNAL_ERROR,
                reason_code=AshtakavargaReason.INTERNAL_ERROR,
                engine_version=__version__,
            )

    def _calculate(self, request: AshtakavargaRequest) -> AshtakavargaFacts:
        profile = PROFILES.get(request.profile_id)
        if profile is None:
            return AshtakavargaFacts(
                status=AshtakavargaStatus.UNSUPPORTED_PROFILE,
                reason_code=AshtakavargaReason.UNSUPPORTED_PROFILE,
                detail=f"unknown profile {request.profile_id!r}",
                engine_version=__version__,
            )

        longitudes = request.natal.longitudes
        if any(not _finite(v) for v in longitudes.values()):
            return AshtakavargaFacts(
                status=AshtakavargaStatus.INVALID_INPUT,
                reason_code=AshtakavargaReason.NON_FINITE_LONGITUDE,
                detail="a natal longitude is not finite",
                engine_version=__version__,
            )

        missing = [c for c in CONTRIBUTOR_ORDER if c not in longitudes]
        if Contributor.LAGNA in missing:
            return AshtakavargaFacts(
                status=AshtakavargaStatus.NOT_EVALUABLE,
                reason_code=AshtakavargaReason.LAGNA_UNAVAILABLE,
                detail=(
                    "the Ascendant is a contributor to every chart under every profile; "
                    f"missing: {[c.value for c in missing]}"
                ),
                engine_version=__version__,
            )
        if missing:
            return AshtakavargaFacts(
                status=AshtakavargaStatus.NOT_EVALUABLE,
                reason_code=AshtakavargaReason.NATAL_POSITIONS_INCOMPLETE,
                detail=f"missing natal longitudes: {[c.value for c in missing]}",
                engine_version=__version__,
            )

        natal_sign_index = {c: sign_index_from_longitude(lon) for c, lon in longitudes.items()}
        charts = compute_bhinnashtakavarga(profile, natal_sign_index)
        sarva = compute_sarvashtakavarga(charts)
        lagna_chart = compute_lagna_chart(profile, natal_sign_index)

        return AshtakavargaFacts(
            status=AshtakavargaStatus.SUCCESS,
            engine_version=__version__,
            profile=ProfileSummary(
                profile_id=profile.profile_id,
                label=profile.label,
                title=profile.title,
                verification_level=profile.verification_level,
                reference=profile.reference,
                has_lagna_chart=profile.has_lagna_chart,
            ),
            charts=charts,
            sarva=sarva,
            lagna_chart=lagna_chart,
        )

    @staticmethod
    def from_kundli_request(kundli: Kundli, profile_id: str) -> AshtakavargaRequest:
        """Convenience: build a request from a Phase 5 `Kundli`."""
        return AshtakavargaRequest(natal=NatalPositions.from_kundli(kundli), profile_id=profile_id)
