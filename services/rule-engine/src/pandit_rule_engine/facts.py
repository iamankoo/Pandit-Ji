"""Normalized chart facts consumed by the rule engine.

These models are the rule engine's own view of an upstream chart. They are
built from a Phase 5 Kundli by `adapters.facts_from_kundli` (no direct import
of `astro-engine`: facts flow one direction) and carry only what the approved
Phase 6 rules read. The rule engine never computes astronomical positions;
it only reads facts and does whole-sign counting arithmetic on them.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pandit_rule_engine.vocab import Body, Dignity, Sign, house_from


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlanetFact(_Model):
    body: Body
    sign: Sign
    degree_in_sign: float = Field(ge=0.0, lt=30.0)
    longitude: float = Field(ge=0.0, lt=360.0)
    house: int = Field(ge=1, le=12, description="Whole-sign house from the D1 Lagna.")
    dignity: Dignity | None = Field(
        default=None, description="Phase 5 dignity; None for Rahu/Ketu (not evaluated)."
    )
    retrograde: bool
    combust: bool | None = Field(
        default=None, description="Phase 4/5 combustion; None where not evaluated."
    )
    aspected_houses: tuple[int, ...] = Field(
        description="Houses (1-12) this planet casts a Phase 5 full-sign graha drishti on."
    )


class CalculationSnapshot(_Model):
    """Calculation configuration and versions of the upstream chart, kept in
    the evidence bundle so a result is reproducible
    (`docs/ASTROLOGY_STANDARDS.md` §"Evidence bundle and reproducibility")."""

    calculation_engine_version: str
    standards_version: str = Field(
        description="Standards version the upstream chart was built under (Phase 5: 1.3.0)."
    )
    zodiac: str | None = None
    ayanamsa: str | None = None
    node_convention: str | None = None
    house_system: str
    aspect_standard: str | None = None
    dignity_standard: str | None = None
    varga_scheme: str | None = None
    timezone: str | None = None
    input_local_datetime: str | None = None
    utc_datetime: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_meters: float | None = None


class ChartFacts(_Model):
    lagna_sign: Sign
    sign_lords: dict[Sign, Body] = Field(
        description="Lord of each sign (Phase 5 lordship table); all twelve signs."
    )
    planets: dict[Body, PlanetFact]
    snapshot: CalculationSnapshot

    @model_validator(mode="after")
    def _integrity(self) -> ChartFacts:
        if len(self.sign_lords) != 12:
            raise ValueError("sign_lords must cover all twelve signs")
        for body, planet in self.planets.items():
            if planet.body != body:
                raise ValueError(f"planet key {body.value} holds {planet.body.value}")
            expected = house_from(self.lagna_sign, planet.sign)
            if planet.house != expected:
                raise ValueError(
                    f"{body.value}: house {planet.house} inconsistent with sign "
                    f"{planet.sign.value} from Lagna {self.lagna_sign.value} (expected {expected})"
                )
        return self

    def planet(self, body: Body) -> PlanetFact | None:
        return self.planets.get(body)
