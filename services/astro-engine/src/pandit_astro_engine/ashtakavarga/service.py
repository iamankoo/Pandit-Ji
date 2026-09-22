"""Ashtakavarga calculation service facade (Phase 9 WP-A1, extended by
WP-A2/A3).

    AshtakavargaRequest -> AshtakavargaCalculationService -> AshtakavargaFacts
    AshtakavargaReductionRequest -> .calculate_reductions() -> AshtakavargaReductionFacts

Stateless, matching the other astro-engine services. Domain failures come
back as a structured facts result (status plus reason code), never as a
stack trace. No ephemeris access: this module needs only natal sign
placements, already available from a Phase 5 Kundli. `calculate()` and
`AshtakavargaFacts` are completely unchanged by WP-A2/A3 -- reductions are a
separate, additive request/response pair.
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
    AshtakavargaReductionFacts,
    AshtakavargaReductionRequest,
    AshtakavargaRequest,
    AshtakavargaStatus,
    ChartReduction,
    ChartResult,
    NatalPositions,
    PindaResult,
    ProfileSummary,
)
from pandit_astro_engine.ashtakavarga.pinda import compute_pinda
from pandit_astro_engine.ashtakavarga.profiles import BPHS_GRID_ID, BPHS_VERSE_ID, PROFILES
from pandit_astro_engine.ashtakavarga.reductions import (
    apply_ekadhipatya_shodhana,
    apply_trikona_shodhana,
    occupancy_map,
)
from pandit_astro_engine.kundli_models import Kundli
from pandit_astro_engine.rashi import Rashi, rashi_from_index, sign_index_from_longitude

#: WP-A2/A3 (docs/ASTROLOGY_STANDARDS.md v1.8.0 AV-09): no source read gives
#: Brihat Jataka or Phaladeepika a reduction or Pinda procedure at all.
_REDUCTION_SUPPORTED_PROFILES = frozenset({BPHS_GRID_ID, BPHS_VERSE_ID})


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

    # ----------------------------------------------------------------------
    # WP-A2 / WP-A3: Trikona/Ekadhipatya Shodhana and Pinda Sadhana
    # ----------------------------------------------------------------------

    def calculate_reductions(
        self, request: AshtakavargaReductionRequest
    ) -> AshtakavargaReductionFacts:
        try:
            return self._calculate_reductions(request)
        except Exception:  # never leak a stack trace through a fact result
            return AshtakavargaReductionFacts(
                status=AshtakavargaStatus.INTERNAL_ERROR,
                reason_code=AshtakavargaReason.INTERNAL_ERROR,
                engine_version=__version__,
            )

    def _calculate_reductions(
        self, request: AshtakavargaReductionRequest
    ) -> AshtakavargaReductionFacts:
        profile = PROFILES.get(request.profile_id)
        if profile is None:
            return AshtakavargaReductionFacts(
                status=AshtakavargaStatus.UNSUPPORTED_PROFILE,
                reason_code=AshtakavargaReason.UNSUPPORTED_PROFILE,
                detail=f"unknown profile {request.profile_id!r}",
                engine_version=__version__,
            )
        if request.profile_id not in _REDUCTION_SUPPORTED_PROFILES:
            return AshtakavargaReductionFacts(
                status=AshtakavargaStatus.NOT_EVALUABLE,
                reason_code=AshtakavargaReason.REDUCTION_UNSUPPORTED_FOR_PROFILE,
                detail=(
                    f"{request.profile_id!r} has no source-stated reduction procedure "
                    "(Trikona/Ekadhipatya Shodhana and Pinda Sadhana are BPHS Ch. 67-69 only)"
                ),
                engine_version=__version__,
            )

        natal = request.natal
        if any(not _finite(v) for v in natal.all_longitudes()):
            return AshtakavargaReductionFacts(
                status=AshtakavargaStatus.INVALID_INPUT,
                reason_code=AshtakavargaReason.NON_FINITE_LONGITUDE,
                detail="a natal longitude is not finite",
                engine_version=__version__,
            )

        missing = [c for c in CONTRIBUTOR_ORDER if c not in natal.longitudes]
        if Contributor.LAGNA in missing:
            return AshtakavargaReductionFacts(
                status=AshtakavargaStatus.NOT_EVALUABLE,
                reason_code=AshtakavargaReason.LAGNA_UNAVAILABLE,
                detail=f"missing: {[c.value for c in missing]}",
                engine_version=__version__,
            )
        if missing:
            return AshtakavargaReductionFacts(
                status=AshtakavargaStatus.NOT_EVALUABLE,
                reason_code=AshtakavargaReason.NATAL_POSITIONS_INCOMPLETE,
                detail=f"missing natal longitudes: {[c.value for c in missing]}",
                engine_version=__version__,
            )
        if natal.rahu_longitude is None or natal.ketu_longitude is None:
            return AshtakavargaReductionFacts(
                status=AshtakavargaStatus.NOT_EVALUABLE,
                reason_code=AshtakavargaReason.NODE_POSITIONS_REQUIRED,
                detail=(
                    "Ekadhipatya Shodhana's occupancy test needs Rahu/Ketu positions "
                    "(Ch. 68's own worked example treats a Ketu-only sign as occupied)"
                ),
                engine_version=__version__,
            )

        natal_sign_index = {
            c: sign_index_from_longitude(lon) for c, lon in natal.longitudes.items()
        }
        occupancy = occupancy_map(natal_sign_index)
        rahu_sign = rashi_from_index(sign_index_from_longitude(natal.rahu_longitude))
        ketu_sign = rashi_from_index(sign_index_from_longitude(natal.ketu_longitude))

        bhinna_charts = compute_bhinnashtakavarga(profile, natal_sign_index)
        chart_reductions = []
        pinda_results = []
        for chart in bhinna_charts:
            reduction, pinda = self._reduce_and_pinda(chart, occupancy, rahu_sign, ketu_sign)
            chart_reductions.append(reduction)
            pinda_results.append(pinda)

        lagna_reduction = None
        lagna_pinda = None
        lagna_chart = compute_lagna_chart(profile, natal_sign_index)
        if lagna_chart is not None:
            lagna_reduction, lagna_pinda = self._reduce_and_pinda(
                lagna_chart, occupancy, rahu_sign, ketu_sign
            )

        return AshtakavargaReductionFacts(
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
            charts=tuple(chart_reductions),
            lagna_chart=lagna_reduction,
            pinda=tuple(pinda_results),
            lagna_pinda=lagna_pinda,
        )

    @staticmethod
    def from_kundli_reduction_request(
        kundli: Kundli, profile_id: str
    ) -> AshtakavargaReductionRequest:
        """Convenience: build a reduction request from a Phase 5 `Kundli`."""
        return AshtakavargaReductionRequest(
            natal=NatalPositions.from_kundli(kundli), profile_id=profile_id
        )

    @staticmethod
    def _reduce_and_pinda(
        chart: ChartResult,
        occupancy: dict[Rashi, frozenset[Contributor]],
        rahu_sign: Rashi | None,
        ketu_sign: Rashi | None,
    ) -> tuple[ChartReduction, PindaResult]:
        """Trikona then Ekadhipatya Shodhana, then Pinda -- for one chart
        (a planet's Bhinnashtakavarga, or the Ascendant's own BPHS chart).
        If Ekadhipatya Shodhana is itself unresolved for this chart (an
        `EkadhipatyaConflict`), Pinda is never computed from a partial or
        guessed map -- both the reduction and the Pinda result are marked
        `NOT_EVALUABLE(ekadhipatya_equal_value_conflict)` instead."""
        trikona = apply_trikona_shodhana(chart.benefic_count)
        eka, conflicts = apply_ekadhipatya_shodhana(trikona, occupancy, rahu_sign, ketu_sign)
        if eka is None:
            reduction = ChartReduction(
                chart=chart.chart,
                trikona_corrected=trikona,
                status=AshtakavargaStatus.NOT_EVALUABLE,
                reason_code=AshtakavargaReason.EKADHIPATYA_EQUAL_VALUE_CONFLICT,
                ekadhipatya_conflicts=conflicts,
            )
            pinda = PindaResult(
                chart=chart.chart,
                status=AshtakavargaStatus.NOT_EVALUABLE,
                reason_code=AshtakavargaReason.EKADHIPATYA_EQUAL_VALUE_CONFLICT,
            )
            return reduction, pinda
        reduction = ChartReduction(
            chart=chart.chart,
            trikona_corrected=trikona,
            status=AshtakavargaStatus.SUCCESS,
            ekadhipatya_corrected=eka,
        )
        pinda = compute_pinda(chart.chart, eka, occupancy)
        return reduction, pinda
