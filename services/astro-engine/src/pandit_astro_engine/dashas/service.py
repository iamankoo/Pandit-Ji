"""Dasha calculation service facade -- Phase 7.

    AstronomicalCalculationRequest -> DashaCalculationService -> DashaFacts

Wraps Phase 4's astronomical service for the birth Moon (and, for an
approximate birth time, the Moon at the two ends of the interval) and hands the
result to the pure Vimshottari calculator. Ephemeris access stays behind the
existing `ephemeris`/`planets` adapters; nothing here imports Swiss Ephemeris.

Domain failures come back as structured `DashaFacts` (status plus reason code),
never as stack traces.
"""

from __future__ import annotations

from pandit_astro_engine import planets
from pandit_astro_engine._version import __version__
from pandit_astro_engine.dashas.models import (
    BirthTimeInput,
    BirthTimeRecord,
    BirthTimeStatus,
    DashaConfiguration,
    DashaFacts,
    DashaReason,
    DashaRequest,
    DashaStatus,
    MoonUncertaintyRange,
    PeriodProfileIds,
    PrecisionAssessment,
)
from pandit_astro_engine.dashas.profiles import SUBPERIOD_PROFILE_ID
from pandit_astro_engine.dashas.vimshottari import calculate_vimshottari
from pandit_astro_engine.errors import (
    AmbiguousLocalTimeError,
    EphemerisDataUnavailableError,
    InvalidTimezoneError,
    NonexistentLocalTimeError,
)
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CalculationResult,
    CelestialBody,
    ZodiacType,
)
from pandit_astro_engine.service import AstronomicalCalculationService

_JD_PER_SECOND = 1.0 / 86_400.0


class DashaCalculationService:
    """Stateless facade, matching the other astro-engine services."""

    def __init__(self, astronomical_service: AstronomicalCalculationService | None = None) -> None:
        self._astronomical = astronomical_service or AstronomicalCalculationService()

    def calculate(
        self,
        request: AstronomicalCalculationRequest,
        config: DashaConfiguration | None = None,
        birth_time: BirthTimeInput | None = None,
    ) -> DashaFacts:
        config = config or DashaConfiguration()
        birth_time = birth_time or BirthTimeInput()
        try:
            return self._calculate(request, config, birth_time)
        except InvalidTimezoneError:
            return _failure(
                config, birth_time, DashaStatus.INVALID_INPUT, DashaReason.INVALID_TIMEZONE
            )
        except AmbiguousLocalTimeError:
            return _failure(
                config, birth_time, DashaStatus.INVALID_INPUT, DashaReason.AMBIGUOUS_LOCAL_TIME
            )
        except NonexistentLocalTimeError:
            return _failure(
                config, birth_time, DashaStatus.INVALID_INPUT, DashaReason.NONEXISTENT_LOCAL_TIME
            )
        except EphemerisDataUnavailableError:
            return _failure(
                config,
                birth_time,
                DashaStatus.CONFIGURATION_ERROR,
                DashaReason.EPHEMERIS_UNAVAILABLE,
            )
        except Exception:  # never leak a stack trace through a fact result
            return _failure(
                config, birth_time, DashaStatus.INTERNAL_ERROR, DashaReason.INTERNAL_ERROR
            )

    # ------------------------------------------------------------------

    def _calculate(
        self,
        request: AstronomicalCalculationRequest,
        config: DashaConfiguration,
        birth_time: BirthTimeInput,
    ) -> DashaFacts:
        if request.config.zodiac is not ZodiacType.SIDEREAL:
            return _failure(
                config,
                birth_time,
                DashaStatus.CONFIGURATION_ERROR,
                DashaReason.SIDEREAL_ZODIAC_REQUIRED,
            )

        moon_request = request.model_copy(
            update={"bodies": [CelestialBody.MOON], "include_solar_events": False}
        )
        try:
            astronomical = self._astronomical.calculate(moon_request)
        except ValueError:
            # e.g. day 31 in a 30-day month, raised by the standard library.
            return _failure(
                config, birth_time, DashaStatus.INVALID_INPUT, DashaReason.INVALID_LOCAL_DATETIME
            )
        moon = astronomical.planets.moon
        if moon is None:
            return _failure(
                config, birth_time, DashaStatus.INVALID_INPUT, DashaReason.MOON_LONGITUDE_MISSING
            )
        resolution = astronomical.metadata.time_resolution

        uncertainty_range: MoonUncertaintyRange | None = None
        seconds = birth_time.uncertainty_seconds
        if (
            birth_time.status is BirthTimeStatus.APPROXIMATE
            and seconds is not None
            and seconds > 0
            and seconds == seconds  # not NaN
            and seconds != float("inf")
        ):
            uncertainty_range = self._moon_range(request, astronomical, moon.longitude, seconds)

        facts = calculate_vimshottari(
            DashaRequest(
                moon_longitude_degrees=moon.longitude,
                birth_utc=resolution.utc_datetime,
                config=config,
                birth_time=birth_time,
                uncertainty_range=uncertainty_range,
            )
        )
        return facts.model_copy(
            update={
                "birth_record": BirthTimeRecord(
                    input_local_datetime=resolution.input_local_datetime,
                    timezone=resolution.timezone,
                    utc_offset_seconds=resolution.utc_offset_seconds,
                    dst_active=resolution.dst_active,
                    was_ambiguous=resolution.was_ambiguous,
                    was_nonexistent=resolution.was_nonexistent,
                    disambiguation_applied=(
                        resolution.disambiguation_applied.value
                        if resolution.disambiguation_applied is not None
                        else None
                    ),
                    utc_datetime=resolution.utc_datetime,
                    julian_day_ut=resolution.julian_day_ut,
                )
            }
        )

    def _moon_range(
        self,
        request: AstronomicalCalculationRequest,
        astronomical: CalculationResult,
        nominal_longitude: float,
        seconds: float,
    ) -> MoonUncertaintyRange:
        """Moon's sidereal longitude at birth -/+ the uncertainty, unwrapped
        around the nominal value so a 360-degree crossing stays continuous."""
        jd_ut = astronomical.metadata.time_resolution.julian_day_ut
        longitudes = []
        for shift in (-seconds, seconds):
            states, _ = planets.calculate_all_bodies(
                jd_ut + shift * _JD_PER_SECOND, request.config, [CelestialBody.MOON]
            )
            longitudes.append(states[CelestialBody.MOON].longitude)
        earliest, latest = (
            nominal_longitude + _signed_delta(value, nominal_longitude) for value in longitudes
        )
        # The Moon is prograde, so earliest <= nominal <= latest; guard against
        # sub-ulp Julian-day rounding for extremely small intervals.
        low = min(earliest, nominal_longitude)
        high = max(latest, nominal_longitude)
        return MoonUncertaintyRange(moon_longitude_at_earliest=low, moon_longitude_at_latest=high)


def _signed_delta(value: float, reference: float) -> float:
    """Shortest signed angular difference value - reference, degrees."""
    return ((value - reference + 180.0) % 360.0) - 180.0


def _failure(
    config: DashaConfiguration,
    birth_time: BirthTimeInput,
    status: DashaStatus,
    reason: DashaReason,
) -> DashaFacts:
    return DashaFacts(
        status=status,
        reason_code=reason,
        engine_version=__version__,
        profile_ids=PeriodProfileIds(
            balance_profile_id=config.balance_profile_id,
            year_length_profile_id=config.year_length_profile_id,
            subperiod_profile_id=SUBPERIOD_PROFILE_ID,
        ),
        precision=PrecisionAssessment(birth_time_status=birth_time.status),
    )


__all__ = ["DashaCalculationService"]
