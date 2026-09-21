"""Transit facts as consumed by the rule engine (Phase 8 -> Phase 6 contract).

`astro-engine` calculates and owns the transit / Gochar facts; the rule engine
only reads them. This module is the adapter: it takes the JSON form of an
astro-engine `TransitFacts` (`TransitFacts.model_dump(mode="json")`), performs
no astronomical or astrological calculation, and preserves the status, profile
IDs, boundary convention, accuracy disclosure, every source reading (including
the unresolved Moon-from-Moon conflict), every Vedha fact, every event and the
Sade Sati segments and episodes with their provenance labels, so a later rule
can cite them and a result stays reproducible.

The rule engine does not import `astro-engine` (facts flow one direction). No
shipped Phase 6 rule reads transit facts yet: this section only makes them
available and reproducible inside the bundle. The records carry structural
facts only (a favourable set is membership in a source's list, never a verdict).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from pandit_rule_engine.adapters import FactsError
from pandit_rule_engine.hashing import canonical_json, sha256_hex
from pandit_rule_engine.vocab import Body

_USABLE = "success"


class _Record(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class ContactRecord(_Record):
    transit_body: Body
    natal_body: Body
    kind: str
    aspect_house_offset: int | None = None
    transit_sign: str
    natal_sign: str


class StateRecord(_Record):
    body: Body
    sign: str
    degree_in_sign: float
    nakshatra: str
    pada: int
    speed_longitude: float
    retrograde: bool
    ephemeris_mode: str
    house_from_moon: int | None = None
    house_from_lagna: int | None = None


class ReadingRecord(_Record):
    reading_id: str
    label: str
    in_favourable_set: bool
    single_source: bool = False
    verification_level: str


class FavourableRecord(_Record):
    body: Body
    house_from_moon: int
    status: str
    reason_code: str | None = None
    readings: tuple[ReadingRecord, ...]
    attesting_reading_ids: tuple[str, ...] = ()


class VedhaRecord(_Record):
    body: Body
    house_from_moon: int
    profile_id: str
    status: str
    reason_code: str | None = None
    vedha_house: int | None = None
    vedha_sign: str | None = None
    vedha_present: bool | None = None
    occupants: tuple[Body, ...] = ()
    exempt_occupants: tuple[Body, ...] = ()
    node_occupants: tuple[Body, ...] = ()
    warnings: tuple[str, ...] = ()


class SadeSatiStateRecord(_Record):
    profile_id: str
    in_band: bool
    phase: int | None = None


class SnapshotRecord(_Record):
    at_utc: str
    julian_day_ut: float
    states: tuple[StateRecord, ...]
    moon_relative_status: str
    moon_relative_reason: str | None = None
    favourable: tuple[FavourableRecord, ...] = ()
    vedha: tuple[VedhaRecord, ...] = ()
    contacts_status: str
    contacts_reason: str | None = None
    contacts: tuple[ContactRecord, ...] = ()
    lagna_status: str
    lagna_reason: str | None = None
    sade_sati: SadeSatiStateRecord | None = None


class EventRecord(_Record):
    event_id: str
    kind: str
    body: Body
    instant_utc: str
    julian_day_ut: float
    from_value: str | None = None
    to_value: str | None = None
    retrograde: bool
    backward_motion: bool | None = None
    contacts_after: tuple[ContactRecord, ...] = ()
    evidence_label: str
    ephemeris_mode: str


class WindowRecord(_Record):
    start_utc: str
    end_utc: str
    event_count: int
    events: tuple[EventRecord, ...]
    start_snapshot: SnapshotRecord


class SegmentRecord(_Record):
    segment_id: str
    sign: str
    phase: int
    phase_name: str
    start_utc: str | None = None
    end_utc: str | None = None
    clipped_at_window_start: bool
    clipped_at_window_end: bool
    entered_by_backward_motion: bool | None = None
    ended_by_backward_motion: bool | None = None


class EpisodeRecord(_Record):
    episode_id: str
    segment_ids: tuple[str, ...]
    start_utc: str | None = None
    end_utc: str | None = None
    clipped_at_window_start: bool
    clipped_at_window_end: bool
    entered_by_backward_motion: bool | None = None
    ended_by_backward_motion: bool | None = None
    retrograde_reentry_of_previous_episode: bool


class SadeSatiRecord(_Record):
    profile_id: str
    evidence_label: str
    classical_status: str
    status: str
    reason_code: str | None = None
    natal_moon_sign: str | None = None
    band_signs: tuple[str, ...] = ()
    window_start_utc: str | None = None
    window_end_utc: str | None = None
    segments: tuple[SegmentRecord, ...] = ()
    episodes: tuple[EpisodeRecord, ...] = ()


class NatalRecord(_Record):
    precision: str
    moon_sign: str | None = None
    moon_sign_status: str
    moon_sign_reason: str | None = None
    lagna_sign: str | None = None
    natal_planet_count: int = 0


class AccuracyRecord(_Record):
    instants_are_exact: bool
    ephemeris_modes: tuple[str, ...]
    zodiac: str
    ayanamsa: str | None = None
    node_convention: str
    search_tolerance_seconds: float
    time_scale_note: str
    ayanamsa_sensitivity_note: str
    engineering_evidence: str
    evidence_label: str


class ProfileIdsRecord(_Record):
    reference_profile_id: str
    favourable_reading_ids: tuple[str, ...]
    vedha_profile_id: str | None = None
    contact_profile_id: str | None = None
    events_profile_id: str | None = None
    boundary_profile_id: str
    sade_sati_profile_id: str | None = None
    lagna_profile_id: str | None = None


class TransitProvenanceRecord(_Record):
    entry_id: str
    item: str
    evidence_label: str
    statement: str


class TransitEvidence(_Record):
    """One transit calculation, as the evidence bundle records it."""

    system_id: str
    status: str
    reason_code: str | None = None
    standards_version: str
    engine_version: str
    boundary_convention: str
    time_base: str
    profile_ids: ProfileIdsRecord
    natal: NatalRecord | None = None
    accuracy: AccuracyRecord | None = None
    snapshot: SnapshotRecord | None = None
    window: WindowRecord | None = None
    sade_sati: SadeSatiRecord | None = None
    warnings: tuple[str, ...] = ()
    provenance: tuple[TransitProvenanceRecord, ...] = ()
    #: SHA-256 of the canonical JSON of the whole facts object, so any field not copied
    #: into a record here (for example the ephemeris library version) still changes it.
    facts_hash: str


def transit_evidence_from_facts(facts: Mapping[str, Any]) -> TransitEvidence:
    """Build `TransitEvidence` from an astro-engine `TransitFacts` in JSON form."""
    if not isinstance(facts, Mapping):
        raise FactsError("transit: expected an object")
    for key in ("system_id", "status", "profile_ids", "boundary_convention", "time_base"):
        if key not in facts:
            raise FactsError(f"transit: missing required field {key!r}")
    status = facts["status"]
    if status != _USABLE:
        if facts.get("reason_code") is None:
            raise FactsError("transit: a non-success result must carry a reason_code")
    else:
        if facts.get("reason_code") is not None:
            raise FactsError("transit: a successful result must not carry a reason_code")
        for key in ("natal", "accuracy"):
            if facts.get(key) is None:
                raise FactsError(f"transit: a successful result must carry {key!r}")
        if facts.get("snapshot") is None and facts.get("window") is None:
            raise FactsError("transit: a successful result must carry a snapshot or a window")
    try:
        return TransitEvidence.model_validate(
            {**facts, "facts_hash": sha256_hex(canonical_json(facts))}
        )
    except ValidationError as exc:
        raise FactsError(f"transit: malformed facts ({exc.error_count()} invalid fields)") from exc
