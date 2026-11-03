"""Public API schemas (request and response models). Internal ORM and agent models are never
exposed directly; every response is built from these or from the deterministic engines' own
contract models.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MIN_BIRTH_DATE = dt.date(1800, 1, 1)
TimePrecision = Literal["exact", "minute", "approximate", "unknown"]
Disambiguation = Literal["strict", "earlier", "later"]
Language = Literal["EN", "HI", "HG"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- users --------------------------------------------------------------------------------------


class UserOut(BaseModel):
    id: uuid.UUID
    display_name: str | None
    locale: str
    memory_consent: bool
    notification_consent: bool
    analytics_consent: bool
    created_at: dt.datetime


class UserUpdate(_Strict):
    display_name: str | None = Field(default=None, max_length=120)
    locale: Literal["en", "hi", "hinglish"] | None = None


class PrivacyUpdate(_Strict):
    memory_consent: bool | None = None
    notification_consent: bool | None = None
    analytics_consent: bool | None = None


# ---- birth profiles -----------------------------------------------------------------------------


class BirthProfileIn(_Strict):
    label: str = Field(min_length=1, max_length=80)
    birth_date: dt.date
    birth_time: dt.time | None = None
    time_precision: TimePrecision = "unknown"
    time_uncertainty_seconds: float | None = Field(default=None, gt=0, le=86400)
    timezone: str = Field(min_length=1, max_length=64)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_m: float = Field(default=0.0, ge=-500, le=9000)
    place_label: str | None = Field(default=None, max_length=160)
    disambiguation: Disambiguation = "strict"

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("label must not be blank")
        return value

    @field_validator("birth_date")
    @classmethod
    def _date(cls, value: dt.date) -> dt.date:
        if value < MIN_BIRTH_DATE:
            raise ValueError("birth_date is before the supported range")
        if value > dt.date.today():
            raise ValueError("birth_date is in the future")
        return value

    @model_validator(mode="after")
    def _precision(self) -> BirthProfileIn:
        # A missing time is never inferred, and a stated time is never labelled 'unknown'.
        if self.birth_time is None and self.time_precision != "unknown":
            raise ValueError("time_precision must be 'unknown' when birth_time is absent")
        if self.birth_time is not None and self.time_precision == "unknown":
            raise ValueError("a supplied birth_time needs an explicit time_precision")
        if self.time_precision == "approximate" and self.time_uncertainty_seconds is None:
            # allowed: the engines then report their own typed NOT_EVALUABLE; nothing is assumed
            pass
        if self.time_precision != "approximate" and self.time_uncertainty_seconds is not None:
            raise ValueError("time_uncertainty_seconds applies only to an approximate time")
        return self


class BirthProfileUpdate(BirthProfileIn):
    expected_version: int = Field(ge=1)


class BirthProfileOut(BaseModel):
    id: uuid.UUID
    label: str
    birth_date: dt.date
    birth_time: dt.time | None
    time_precision: str
    time_uncertainty_seconds: float | None
    timezone: str
    disambiguation: str
    latitude: float
    longitude: float
    altitude_m: float
    place_label: str | None
    birth_utc: dt.datetime | None
    version: int
    created_at: dt.datetime
    updated_at: dt.datetime


# ---- calculations -------------------------------------------------------------------------------


class DashaQuery(_Strict):
    depth: int = Field(default=3, ge=1, le=3)
    at_utc: dt.datetime | None = None


class TransitQuery(_Strict):
    at_utc: dt.datetime | None = None
    window_start_utc: dt.datetime | None = None
    window_end_utc: dt.datetime | None = None
    include_sade_sati: bool = False

    @model_validator(mode="after")
    def _window(self) -> TransitQuery:
        if (self.window_start_utc is None) != (self.window_end_utc is None):
            raise ValueError("a window needs both window_start_utc and window_end_utc")
        if self.window_start_utc and self.window_end_utc:
            if self.window_end_utc <= self.window_start_utc:
                raise ValueError("window_end_utc must be after window_start_utc")
            if (self.window_end_utc - self.window_start_utc).days > 3660:
                raise ValueError("the window is longer than 10 years")
        for value in (self.at_utc, self.window_start_utc, self.window_end_utc):
            if value is not None and value.tzinfo is None:
                raise ValueError("instants must be timezone-aware (UTC)")
        return self


class PanchangQuery(_Strict):
    date: dt.date
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(min_length=1, max_length=64)


class NumerologyQuery(_Strict):
    profile: str | None = Field(default=None, max_length=80)  # an engine profile id; None: default
    date_of_birth: dt.date | None = None
    latin_name: str | None = Field(default=None, max_length=200)
    master_number_policy: str | None = None


class CompatibilityQuery(_Strict):
    profile_a_id: uuid.UUID
    profile_b_id: uuid.UUID
    profile: str = Field(min_length=1, max_length=64)
    participant_consent_attested: Literal[True]


# ---- chat, reports ------------------------------------------------------------------------------


class ChatRequest(_Strict):
    message: str = Field(min_length=1, max_length=2000)
    profile_id: uuid.UUID | None = None
    language: Language = "EN"
    conversation_id: uuid.UUID | None = None
    subject_adult_confirmed: bool | None = None


class ReportCreate(_Strict):
    profile_id: uuid.UUID
    domains: list[str] = Field(min_length=1, max_length=12)
    language: Language = "EN"
    subject_adult_confirmed: bool | None = None


# ---- platform foundations -----------------------------------------------------------------------


class MemoryPut(_Strict):
    value: dict[str, Any]
    kind: Literal["preference", "note"] = "preference"


class SubscriptionIn(_Strict):
    channel: Literal["inapp", "push", "email"]
    topic: str = Field(min_length=1, max_length=48, pattern=r"^[a-z0-9_.-]+$")
    enabled: bool = True


class NotificationIn(_Strict):
    topic: str = Field(min_length=1, max_length=48, pattern=r"^[a-z0-9_.-]+$")
    message: str = Field(min_length=1, max_length=500)
    scheduled_for: dt.datetime

    @field_validator("scheduled_for")
    @classmethod
    def _aware(cls, value: dt.datetime) -> dt.datetime:
        if value.tzinfo is None:
            raise ValueError("scheduled_for must be timezone-aware")
        return value


class VoiceSessionIn(_Strict):
    language: Language = "EN"
