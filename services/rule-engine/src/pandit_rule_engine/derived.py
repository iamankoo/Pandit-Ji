"""Derived facts (Phase 6F-6H): planetary relationships, natural
benefic/malefic, Moolatrikona and the Ch. 34 functional-nature lookup.

Every value is computed from Phase 5 facts plus the ruleset's methodology
tables (`tables.py`); nothing here is astronomy. Where the source gives no
value the result says so with a structured reason instead of a guess:

- Rahu and Ketu have no relationships, no Moolatrikona and no Ch. 34 cell;
- the Moon exactly on the waxing/waning boundary and Mercury joined by both
  a malefic and a benefic have no natural nature (`reading_ambiguous`);
- a planet missing from the chart makes dependent values
  `missing_dependency`.
"""

from __future__ import annotations

from typing import Any

from pandit_rule_engine.conditions import MoolatrikonaValue, NatureValue, RelationValue
from pandit_rule_engine.facts import ChartFacts, PlanetFact
from pandit_rule_engine.tables import Tables
from pandit_rule_engine.vocab import (
    ALL_BODIES,
    CLASSICAL_BODIES,
    NODES,
    Body,
    Reason,
    house_from,
)


class TableDerivedFacts:
    """`DerivedFacts` implementation over one chart and the methodology tables."""

    def __init__(self, facts: ChartFacts, tables: Tables) -> None:
        self._facts = facts
        self._tables = tables

    # -- natural nature ---------------------------------------------------

    def natural_nature(self, body: Body) -> NatureValue:
        table = self._tables.natural_nature
        if body in table.malefic:
            return NatureValue("malefic")
        if body in table.benefic:
            return NatureValue("benefic")
        if body is Body.MOON:
            return self._moon_nature()
        return self._mercury_nature()

    def _moon_nature(self) -> NatureValue:
        sun = self._facts.planet(Body.SUN)
        moon = self._facts.planet(Body.MOON)
        if sun is None or moon is None:
            missing = "planet.sun" if sun is None else "planet.moon"
            return NatureValue("unavailable", Reason.MISSING_DEPENDENCY, missing)
        conventions = self._tables.natural_nature.conventions
        start, end = conventions.moon_waxing_elongation_degrees
        elongation = (moon.longitude - sun.longitude) % 360.0
        epsilon = conventions.moon_boundary_epsilon_degrees
        near = min(
            abs(elongation - start),
            abs(elongation - end),
            abs(elongation - 360.0),
        )
        if near < epsilon:
            return NatureValue("boundary", Reason.READING_AMBIGUOUS, "moon_phase_boundary")
        return NatureValue("benefic" if start <= elongation < end else "malefic")

    def _associate_nature(self, planet: PlanetFact) -> NatureValue:
        # Mercury's associates: nodes are natural malefics (Ch. 3 v. 11); the
        # Moon's own phase is resolved through `_moon_nature`.
        return self.natural_nature(planet.body)

    def _mercury_nature(self) -> NatureValue:
        mercury = self._facts.planet(Body.MERCURY)
        if mercury is None:
            return NatureValue("unavailable", Reason.MISSING_DEPENDENCY, "planet.mercury")
        others = [body for body in ALL_BODIES if body is not Body.MERCURY]
        missing = [body for body in others if self._facts.planet(body) is None]
        if missing:
            detail = f"planet.{missing[0].value}"
            return NatureValue("unavailable", Reason.MISSING_DEPENDENCY, detail)
        benefic = malefic = False
        for body in others:
            planet = self._facts.planets[body]
            if planet.sign is not mercury.sign:
                continue
            nature = self._associate_nature(planet)
            if nature.value == "benefic":
                benefic = True
            elif nature.value == "malefic":
                malefic = True
            else:
                return NatureValue("unavailable", nature.reason, nature.detail)
        if malefic and benefic:
            return NatureValue("mixed", Reason.READING_AMBIGUOUS, "mercury_mixed_association")
        return NatureValue("malefic" if malefic else "benefic")

    # -- relationships ----------------------------------------------------

    def relationship(self, basis: str, a: Body, b: Body) -> RelationValue:
        if a in NODES or b in NODES:
            return RelationValue(None, Reason.NOT_SPECIFIED_BY_SOURCE, "node_relationship")
        if a is b:
            return RelationValue(None, Reason.NOT_SPECIFIED_BY_SOURCE, "self_relationship")
        natural = self._tables.natural_relationships.kind(a, b)
        if basis == "natural":
            return RelationValue(natural)
        first = self._facts.planet(a)
        second = self._facts.planet(b)
        if first is None or second is None:
            missing = a if first is None else b
            return RelationValue(None, Reason.MISSING_DEPENDENCY, f"planet.{missing.value}")
        house = house_from(first.sign, second.sign)
        friend = house in self._tables.temporal_relationship.friend_houses
        compound = self._tables.compound_relationship
        result = compound.result(natural, "friend") if friend else compound.result(natural, "enemy")
        return RelationValue(result)

    # -- Moolatrikona -----------------------------------------------------

    def moolatrikona(self, body: Body) -> MoolatrikonaValue:
        if body in NODES:
            return MoolatrikonaValue(None, Reason.REQUIRES_MOOLATRIKONA, "node_moolatrikona")
        planet = self._facts.planet(body)
        if planet is None:
            return MoolatrikonaValue(None, Reason.MISSING_DEPENDENCY, f"planet.{body.value}")
        inside = self._tables.moolatrikona.contains(body, planet.sign, planet.degree_in_sign)
        return MoolatrikonaValue(inside)

    # -- snapshot for the evidence bundle ---------------------------------

    def snapshot(self) -> dict[str, Any]:
        """A JSON-compatible view of every derived fact for this chart."""
        nature: dict[str, Any] = {}
        for body in ALL_BODIES:
            value = self.natural_nature(body)
            entry: dict[str, Any] = {"value": value.value}
            if value.reason is not None:
                entry["reason"] = value.reason.value
                entry["detail"] = value.detail
            nature[body.value] = entry
        natural: dict[str, dict[str, str]] = {}
        compound: dict[str, dict[str, str]] = {}
        for a in CLASSICAL_BODIES:
            if self._facts.planet(a) is None:
                continue
            natural[a.value] = {}
            compound[a.value] = {}
            for b in CLASSICAL_BODIES:
                if a is b or self._facts.planet(b) is None:
                    continue
                natural_kind = self.relationship("natural", a, b).kind
                compound_kind = self.relationship("compound", a, b).kind
                if natural_kind is not None:
                    natural[a.value][b.value] = natural_kind
                if compound_kind is not None:
                    compound[a.value][b.value] = compound_kind
        moolatrikona: dict[str, Any] = {}
        for body in ALL_BODIES:
            fact = self.moolatrikona(body)
            moolatrikona[body.value] = (
                fact.value if fact.reason is None else f"not_evaluable:{fact.reason.value}"
            )
        functional: dict[str, Any] = {}
        for body in ALL_BODIES:
            cell = self._tables.functional(self._facts.lagna_sign, body)
            functional[body.value] = {
                "status": cell.status,
                "labels": list(cell.labels),
                "verse": cell.verse,
            }
        return {
            "natural_nature": nature,
            "relationships_natural": natural,
            "relationships_compound": compound,
            "moolatrikona": moolatrikona,
            "functional_nature": {
                "lagna": self._facts.lagna_sign.value,
                "cells": functional,
            },
        }
