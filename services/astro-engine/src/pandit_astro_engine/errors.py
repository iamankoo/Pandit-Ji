"""Typed calculation errors.

Domain-layer errors only -- never HTTP-specific (docs/ARCHITECTURE.md
"Failure Architecture": the domain layer fails explicitly, `server/`
translates to HTTP later). Never swallowed, never turned into a
fabricated fallback value.
"""

from __future__ import annotations


class AstroEngineError(Exception):
    """Base class for every astro-engine domain error."""


class InvalidLatitudeError(AstroEngineError):
    def __init__(self, latitude: float) -> None:
        super().__init__(f"Latitude {latitude} is outside the valid range [-90, 90].")
        self.latitude = latitude


class InvalidLongitudeError(AstroEngineError):
    def __init__(self, longitude: float) -> None:
        super().__init__(f"Longitude {longitude} is outside the valid range [-180, 180].")
        self.longitude = longitude


class InvalidTimezoneError(AstroEngineError):
    def __init__(self, timezone_name: str) -> None:
        super().__init__(f"'{timezone_name}' is not a known IANA timezone identifier.")
        self.timezone_name = timezone_name


class InvalidDatetimeError(AstroEngineError):
    """Raised for a structurally invalid local datetime (e.g. day 32)."""


class NonexistentLocalTimeError(AstroEngineError):
    """The given local time falls inside a DST 'spring-forward' gap and does
    not exist for the given timezone; no disambiguation policy was given."""

    def __init__(self, local_datetime_repr: str, timezone_name: str) -> None:
        super().__init__(
            f"Local time {local_datetime_repr} does not exist in timezone "
            f"'{timezone_name}' (DST gap). Provide an explicit disambiguation policy."
        )


class AmbiguousLocalTimeError(AstroEngineError):
    """The given local time occurs twice (DST 'fall-back' overlap); no
    disambiguation policy was given, so both candidate UTC instants are
    reported rather than an arbitrary one being silently chosen."""

    def __init__(
        self, local_datetime_repr: str, timezone_name: str, earlier_utc: str, later_utc: str
    ) -> None:
        super().__init__(
            f"Local time {local_datetime_repr} is ambiguous in timezone "
            f"'{timezone_name}' (DST overlap): could be {earlier_utc} or {later_utc} UTC. "
            "Provide an explicit disambiguation policy."
        )
        self.earlier_utc = earlier_utc
        self.later_utc = later_utc


class UnsupportedConfigurationError(AstroEngineError):
    """The requested calculation configuration is not (yet) supported."""


class EphemerisDataUnavailableError(AstroEngineError):
    """Requested a calculation mode requiring Swiss Ephemeris data files,
    but no usable ephemeris path was configured or found there."""

    def __init__(self, configured_path: str | None) -> None:
        super().__init__(
            "Swiss Ephemeris data files were required but unavailable "
            f"(configured EPHEMERIS_PATH={configured_path!r}). See services/astro-engine/README.md "
            "'Ephemeris data' for how to obtain and configure them, or explicitly allow the "
            "Moshier analytical fallback."
        )


class EphemerisCalculationError(AstroEngineError):
    """The underlying Swiss Ephemeris library reported a fatal calculation error."""


class SolarEventUnavailableError(AstroEngineError):
    """Sunrise/sunset does not occur for the given date/location (e.g. polar
    day/night) -- an explicit, typed non-error result, not a fabricated time."""
