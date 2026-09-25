"""WP-G Jaimini facts with provenance (Phase 9 closure; `docs/ASTROLOGY_STANDARDS.md`
v1.21.0, JN-19/JN-20).

    JaiminiFactsRequest -> JaiminiFactsService.calculate -> JaiminiFacts

Wraps the WP-G pure functions (planet-level Rashi Drishti, Bhava and Graha
Padas, Karakamsa) and the WP-B-2 Chara Karaka ranking over one Phase 5 Kundli
(Vedic default: Lahiri, whole-sign), so they travel as one versioned,
provenance-carrying facts object (for example into the rule-engine evidence
bundle). No rule is added or changed; the pure functions are unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from pandit_astro_engine._version import __version__
from pandit_astro_engine.jaimini.arudha import BhavaPada, GrahaPada, bhava_padas, graha_padas
from pandit_astro_engine.jaimini.chara_karaka import (
    CharaKarakaRequest,
    CharaKarakaResult,
    calculate_chara_karaka,
)
from pandit_astro_engine.jaimini.karakamsa import KarakamsaResult, karakamsa
from pandit_astro_engine.jaimini.planet_rashi_drishti import (
    PlanetRashiDrishti,
    planet_rashi_drishti,
)
from pandit_astro_engine.jaimini.profiles import (
    BHAVA_PADA_PROFILE,
    CHARA_KARAKA_PROFILE_BODIES,
    CHARA_KARAKA_PROFILES,
    GRAHA_PADA_PROFILE,
    KARAKAMSA_PROFILE,
    PLANET_RASHI_DRISHTI_PROFILE,
    EvidenceLabel,
    SourceReference,
)
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CalculationConfig,
    CelestialBody,
    LocalDateTimeInput,
    Location,
    NodeConvention,
    TimeResolution,
)
from pandit_astro_engine.rashi import Rashi, rashi_from_longitude

JAIMINI_FACTS_STANDARDS_VERSION = "1.21.0"
JAIMINI_SYSTEM_ID = "vedic_jaimini_style"

_NODES = (CelestialBody.RAHU, CelestialBody.KETU)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class JaiminiFactsRequest(_Model):
    """`chara_karaka_profile_id` and `include_nodes_in_rashi_drishti` have no
    default (JN-06, JN-11). The birth time must be known: every WP-G fact
    depends on the Lagna or on exact degrees."""

    local_datetime: LocalDateTimeInput
    location: Location
    chara_karaka_profile_id: str
    include_nodes_in_rashi_drishti: bool
    node_convention: NodeConvention = NodeConvention.MEAN
    allow_moshier_fallback: bool = True

    @model_validator(mode="after")
    def _check(self) -> JaiminiFactsRequest:
        if self.chara_karaka_profile_id not in CHARA_KARAKA_PROFILES:
            raise ValueError(
                f"unknown chara_karaka_profile_id {self.chara_karaka_profile_id!r}; supported: "
                f"{sorted(CHARA_KARAKA_PROFILES)}"
            )
        return self


class JaiminiProvenance(_Model):
    profile_id: str
    evidence_label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...]


class JaiminiFacts(_Model):
    system: str = JAIMINI_SYSTEM_ID
    standards_version: str = JAIMINI_FACTS_STANDARDS_VERSION
    engine_version: str
    time_resolution: TimeResolution
    location: Location
    node_convention: NodeConvention
    lagna_sign: Rashi
    chara_karaka: CharaKarakaResult
    karakamsa: KarakamsaResult
    planet_rashi_drishti: tuple[PlanetRashiDrishti, ...]
    bhava_padas: tuple[BhavaPada, ...]
    graha_padas: tuple[GrahaPada, ...]
    provenance: tuple[JaiminiProvenance, ...]


class JaiminiFactsService:
    def __init__(self, kundli_service: KundliCalculationService | None = None) -> None:
        self._kundli = kundli_service or KundliCalculationService()

    def calculate(self, request: JaiminiFactsRequest) -> JaiminiFacts:
        kundli = self._kundli.calculate(
            AstronomicalCalculationRequest(
                local_datetime=request.local_datetime,
                location=request.location,
                config=CalculationConfig(
                    node_convention=request.node_convention,
                    allow_moshier_fallback=request.allow_moshier_fallback,
                ),
                include_solar_events=False,
            )
        )
        lon = {p.body: p.longitude for p in kundli.planets}
        signs = {b: rashi_from_longitude(v) for b, v in lon.items()}
        bodies = CHARA_KARAKA_PROFILE_BODIES[request.chara_karaka_profile_id]
        chara = calculate_chara_karaka(
            CharaKarakaRequest(
                profile_id=request.chara_karaka_profile_id,
                longitudes={b: lon[b] for b in bodies},
            )
        )
        drishti_signs = (
            signs
            if request.include_nodes_in_rashi_drishti
            else {b: s for b, s in signs.items() if b not in _NODES}
        )
        lagna = rashi_from_longitude(kundli.lagna_longitude)
        chara_profile = CHARA_KARAKA_PROFILES[request.chara_karaka_profile_id]
        return JaiminiFacts(
            engine_version=__version__,
            time_resolution=kundli.astronomical.metadata.time_resolution,
            location=request.location,
            node_convention=request.node_convention,
            lagna_sign=lagna,
            chara_karaka=chara,
            karakamsa=karakamsa(chara, lon),
            planet_rashi_drishti=planet_rashi_drishti(drishti_signs),
            bhava_padas=bhava_padas(lagna, signs),
            graha_padas=graha_padas(signs),
            provenance=(
                JaiminiProvenance(
                    profile_id=chara_profile.profile_id,
                    evidence_label=chara_profile.label,
                    statement=chara_profile.title,
                    references=(chara_profile.reference,),
                ),
                *(
                    JaiminiProvenance(
                        profile_id=p.profile_id,
                        evidence_label=p.label,
                        statement=p.title,
                        references=p.references,
                    )
                    for p in (
                        PLANET_RASHI_DRISHTI_PROFILE,
                        BHAVA_PADA_PROFILE,
                        GRAHA_PADA_PROFILE,
                        KARAKAMSA_PROFILE,
                    )
                ),
            ),
        )
