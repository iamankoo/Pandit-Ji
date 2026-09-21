"""Transit calculation service facade -- Phase 8.

    TransitRequest -> TransitCalculationService -> TransitFacts

Wraps the pure calculator with the Swiss-backed position provider (Phase 4
adapter). Ephemeris access stays behind the existing `ephemeris` adapter;
nothing here imports Swiss Ephemeris. Domain failures come back as structured
`TransitFacts` (status plus reason code), never as stack traces.
"""

from __future__ import annotations

import datetime as dt

from pandit_astro_engine import ephemeris
from pandit_astro_engine._version import __version__
from pandit_astro_engine.models import CelestialBody, ZodiacType
from pandit_astro_engine.transits.calculator import calculate_transit
from pandit_astro_engine.transits.models import (
    EventKind,
    NatalReference,
    TransitConfiguration,
    TransitFacts,
    TransitReason,
    TransitRequest,
    TransitStatus,
)
from pandit_astro_engine.transits.positions import PositionProvider, SwissPositionProvider


class TransitCalculationService:
    """Stateless facade, matching the other astro-engine services. A
    `PositionProvider` may be injected (tests use exact synthetic motion)."""

    def __init__(self, provider: PositionProvider | None = None) -> None:
        self._provider = provider

    def calculate(self, request: TransitRequest) -> TransitFacts:
        config = request.config
        if config.calculation.zodiac is not ZodiacType.SIDEREAL:
            return self._failure(
                request, TransitStatus.CONFIGURATION_ERROR, TransitReason.SIDEREAL_ZODIAC_REQUIRED
            )
        provider = self._provider or SwissPositionProvider(config.calculation)
        try:
            return calculate_transit(
                request,
                provider,
                engine_version=__version__,
                swisseph_version=ephemeris.swisseph_version(),
            )
        except Exception:  # never leak a stack trace through a fact result
            return self._failure(
                request, TransitStatus.INTERNAL_ERROR, TransitReason.INTERNAL_ERROR
            )

    # Convenience entry points -------------------------------------------------

    def snapshot(
        self,
        natal: NatalReference,
        at_utc: dt.datetime,
        config: TransitConfiguration | None = None,
    ) -> TransitFacts:
        return self.calculate(
            TransitRequest(natal=natal, config=config or TransitConfiguration(), at_utc=at_utc)
        )

    def events(
        self,
        natal: NatalReference,
        start_utc: dt.datetime,
        end_utc: dt.datetime,
        config: TransitConfiguration | None = None,
    ) -> TransitFacts:
        return self.calculate(
            TransitRequest(
                natal=natal,
                config=config or TransitConfiguration(),
                window_start_utc=start_utc,
                window_end_utc=end_utc,
            )
        )

    def sade_sati(
        self,
        natal: NatalReference,
        start_utc: dt.datetime,
        end_utc: dt.datetime,
        config: TransitConfiguration | None = None,
    ) -> TransitFacts:
        """Sade Sati (MODERN_TRADITION) segments and episodes over a window; only
        Saturn's sign ingress is scanned."""
        base = config or TransitConfiguration()
        focused = base.model_copy(
            update={
                "include_sade_sati": True,
                "bodies": (CelestialBody.SATURN,),
                "event_kinds": (EventKind.SIGN_INGRESS,),
                "include_vedha": False,
                "include_contacts": False,
            }
        )
        return self.calculate(
            TransitRequest(
                natal=natal,
                config=focused,
                window_start_utc=start_utc,
                window_end_utc=end_utc,
            )
        )

    @staticmethod
    def _failure(
        request: TransitRequest, status: TransitStatus, reason: TransitReason
    ) -> TransitFacts:
        from pandit_astro_engine.transits.calculator import _failure

        return _failure(request, status, reason, __version__, None)
