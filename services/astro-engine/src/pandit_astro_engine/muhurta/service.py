"""Muhurta evaluation and window search (Phase 10;
`docs/ASTROLOGY_STANDARDS.md` v1.23.0, MU-01 to MU-14).

    MuhurtaEvaluateRequest -> MuhurtaService.evaluate -> MuhurtaEvaluation
    MuhurtaSearchRequest   -> MuhurtaService.search   -> MuhurtaSearchResult

Every factor of the purpose's rule set is evaluated at the instant and
reported with its source; person-specific factors are evaluated for each
unlabelled participant and are NOT_EVALUABLE when none is given. There is no
overall verdict: the summary counts classifications and says whether any
evaluated factor is unfavourable. The search splits each Hindu day at every
instant where an evaluated fact can change and returns the stretches in
which no evaluated factor is unfavourable.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from zoneinfo import ZoneInfo

from pandit_astro_engine import ephemeris, timezones
from pandit_astro_engine._version import __version__
from pandit_astro_engine.combustion import evaluate_combustion
from pandit_astro_engine.config import Settings
from pandit_astro_engine.models import CelestialBody, Location
from pandit_astro_engine.muhurta.models import (
    FactorResult,
    FactorStatus,
    JanmaInput,
    MomentFacts,
    MuhurtaEvaluateRequest,
    MuhurtaEvaluation,
    MuhurtaSearchRequest,
    MuhurtaSearchResult,
    MuhurtaWindow,
    Summary,
)
from pandit_astro_engine.muhurta.rules import (
    MUHURTA_RULES_VERSION,
    RULES,
    Classification,
    FactorKind,
    FactorRule,
    Purpose,
)
from pandit_astro_engine.nakshatra import NAKSHATRA_ORDER
from pandit_astro_engine.panchang import astro
from pandit_astro_engine.panchang.astro import Sky
from pandit_astro_engine.panchang.constants import (
    KARANA_SPAN_DEGREES,
    NAKSHATRA_SPAN_DEGREES,
    PANCHAKA_BY_REMAINDER,
    TARA_ORDER,
    TITHI_SPAN_DEGREES,
    WEEKDAY_ORDER,
    YOGA_SPAN_DEGREES,
    YogaName,
    karana_name,
)
from pandit_astro_engine.panchang.profiles import (
    PANCHANG_STANDARDS_VERSION,
    PANCHANG_SYSTEM_ID,
    SunriseConvention,
)
from pandit_astro_engine.panchang.service import (
    DayFrame,
    jd_of,
    sunday_zero_weekday,
    to_instant,
)
from pandit_astro_engine.rashi import RASHI_MODALITY, Modality, Rashi, rashi_from_longitude
from pandit_astro_engine.vargas import calculate_varga_sign

_UNSET = object()
_NAVAMSA_SPAN = 30.0 / 9.0
_RANK = {
    Classification.UNFAVOURABLE: 3,
    Classification.MIDDLING: 2,
    Classification.NOT_LISTED: 1,
    Classification.FAVOURABLE: 0,
}
_CHART_BODIES: tuple[tuple[str, int], ...] = (
    ("sun", ephemeris.SWE_BODY_ID["sun"]),
    ("moon", ephemeris.SWE_BODY_ID["moon"]),
    ("mars", ephemeris.SWE_BODY_ID["mars"]),
    ("mercury", ephemeris.SWE_BODY_ID["mercury"]),
    ("jupiter", ephemeris.SWE_BODY_ID["jupiter"]),
    ("venus", ephemeris.SWE_BODY_ID["venus"]),
    ("saturn", ephemeris.SWE_BODY_ID["saturn"]),
    ("rahu", ephemeris.SWE_NODE_ID["mean"]),
)
NOTES = (
    "Factor facts only: the result is not a recommendation and carries no overall verdict.",
    "Statements of effect in the sources are not encoded (PRODUCT_POLICIES.md).",
    "Rahu is the mean node; Ketu is opposite; houses are whole signs from the rising sign.",
)


def tithi_label(index: int) -> str:
    if index <= 15:
        return f"S{index}"
    return "K30" if index == 30 else f"K{index - 15}"


class _Positions:
    def __init__(self, sky: Sky, jd: float, fallback: bool) -> None:
        aya = sky.lahiri(jd)
        self.lon: dict[str, float] = {}
        self.speed: dict[str, float] = {}
        for name, swe_id in _CHART_BODIES:
            raw = ephemeris.calculate_body(
                jd, swe_id, sidereal=False, allow_moshier_fallback=fallback
            )
            self.lon[name] = (raw.longitude - aya) % 360.0
            self.speed[name] = raw.speed_longitude
        self.lon["ketu"] = (self.lon["rahu"] + 180.0) % 360.0
        self.speed["ketu"] = self.speed["rahu"]

    def sign(self, body: str) -> Rashi:
        return rashi_from_longitude(self.lon[body])


def moment_facts(
    sky: Sky, jd: float, frame: DayFrame, location: Location, fallback: bool
) -> tuple[MomentFacts, dict[str, int]]:
    """Facts at `jd` inside `frame`'s Hindu day, and the numeric indices
    the remainder Panchaka and the Tara count need."""
    assert frame.sunrise is not None and frame.sunset is not None
    pos = _Positions(sky, jd, fallback)
    elong = (sky.moon(jd) - sky.sun(jd)) % 360.0
    t_index = astro.part_index(elong, TITHI_SPAN_DEGREES) + 1
    n_index = astro.part_index(pos.lon["moon"], NAKSHATRA_SPAN_DEGREES) + 1
    y_index = astro.part_index((pos.lon["sun"] + pos.lon["moon"]) % 360.0, YOGA_SPAN_DEGREES) + 1
    k_index = astro.part_index(elong, KARANA_SPAN_DEGREES) + 1
    lagna = sky.ascendant_sidereal(jd, latitude=location.latitude, longitude=location.longitude)
    weekday = sunday_zero_weekday(frame.date)
    combust = {}
    for body in ("jupiter", "venus"):
        status = evaluate_combustion(
            CelestialBody(body),
            pos.lon[body],
            pos.lon["sun"],
            is_retrograde=pos.speed[body] < 0,
        )
        combust[body] = bool(status and status.is_combust)
    is_day = frame.sunrise <= jd < frame.sunset
    facts = MomentFacts(
        tithi=tithi_label(t_index),
        paksha="shukla" if t_index <= 15 else "krishna",
        nakshatra=NAKSHATRA_ORDER[n_index - 1],
        yoga=tuple(YogaName)[y_index - 1].value,
        karana=karana_name(k_index).value,
        weekday=WEEKDAY_ORDER[weekday].value,
        lagna_sign=rashi_from_longitude(lagna),
        lagna_navamsa=calculate_varga_sign(9, lagna),
        moon_sign=pos.sign("moon"),
        sun_sign=pos.sign("sun"),
        planet_signs=tuple((b, pos.sign(b)) for b in (*(n for n, _ in _CHART_BODIES), "ketu")),
        jupiter_combust=combust["jupiter"],
        venus_combust=combust["venus"],
        is_daytime=is_day,
        forenoon=is_day and jd <= (frame.sunrise + frame.sunset) / 2.0,
    )
    numbers = {
        "tithi": t_index,
        "nakshatra": n_index,
        "weekday": weekday + 1,
        "lagna": int(lagna // 30.0) % 12 + 1,
    }
    return facts, numbers


def _classify(
    rule: FactorRule, value: str
) -> tuple[FactorStatus, Classification | None, str | None]:
    if value in rule.conditional:
        return FactorStatus.NOT_EVALUABLE, None, rule.condition_reason
    if value in rule.favourable:
        return FactorStatus.SUCCESS, Classification.FAVOURABLE, None
    if value in rule.middling:
        return FactorStatus.SUCCESS, Classification.MIDDLING, None
    if value in rule.unfavourable:
        return FactorStatus.SUCCESS, Classification.UNFAVOURABLE, None
    return FactorStatus.SUCCESS, rule.unlisted, None


def _occupants(facts: MomentFacts, house: int) -> list[str]:
    sign_index = (tuple(Rashi).index(facts.lagna_sign) + house - 1) % 12
    target = tuple(Rashi)[sign_index]
    return [body for body, sign in facts.planet_signs if sign is target]


def _value(rule: FactorRule, facts: MomentFacts, numbers: dict[str, int]) -> str:
    kind = rule.kind
    if kind is FactorKind.SUN_AYANA:
        return facts.sun_sign.value
    if kind is FactorKind.PAKSHA:
        return facts.paksha
    if kind is FactorKind.TITHI:
        return facts.tithi
    if kind is FactorKind.NAKSHATRA:
        return facts.nakshatra.value
    if kind is FactorKind.WEEKDAY:
        return facts.weekday
    if kind is FactorKind.WEEKDAY_PAKSHA:
        return f"{facts.weekday}:{facts.paksha}"
    if kind is FactorKind.LAGNA_SIGN:
        return facts.lagna_sign.value
    if kind is FactorKind.LAGNA_MODALITY_NAVAMSA:
        modality = RASHI_MODALITY[facts.lagna_sign]
        if modality is Modality.MOVABLE and facts.lagna_navamsa is Rashi.TAURUS:
            return "movable_taurus_navamsa"
        return modality.value
    if kind is FactorKind.HOUSE_VACANT:
        assert rule.house is not None
        return "occupied" if _occupants(facts, rule.house) else "vacant"
    if kind is FactorKind.HOUSE_ONLY_VENUS:
        assert rule.house is not None
        occ = _occupants(facts, rule.house)
        if not occ:
            return "vacant"
        return "venus_only" if occ == ["venus"] else "other_planet"
    if kind is FactorKind.TIME_OF_DAY:
        return "day" if facts.is_daytime else "night"
    if kind is FactorKind.FORENOON:
        if not facts.is_daytime:
            return "night"
        return "forenoon_or_noon" if facts.forenoon else "afternoon"
    if kind is FactorKind.MOON_CONJUNCTION:
        others = [b for b, s in facts.planet_signs if b != "moon" and s is facts.moon_sign]
        return "conjunct" if others else "alone"
    if kind is FactorKind.YOGA:
        return facts.yoga
    if kind is FactorKind.BENEFIC_COMBUST:
        return "combust" if facts.jupiter_combust or facts.venus_combust else "none_combust"
    if kind is FactorKind.REMAINDER_PANCHAKA:
        total = numbers["tithi"] + numbers["weekday"] + numbers["nakshatra"] + numbers["lagna"]
        return PANCHAKA_BY_REMAINDER[total % 9].value
    raise ValueError(f"not a moment factor: {kind}")  # pragma: no cover


def _person_value(rule: FactorRule, facts: MomentFacts, person: JanmaInput) -> str:
    if rule.kind in (FactorKind.TARA_COUNT, FactorKind.TARA):
        count = (
            NAKSHATRA_ORDER.index(facts.nakshatra) - NAKSHATRA_ORDER.index(person.janma_nakshatra)
        ) % 27 + 1
        if rule.kind is FactorKind.TARA_COUNT:
            return str(count)
        return TARA_ORDER[(count - 1) % 9].value
    if rule.kind is FactorKind.CHANDRA_HOUSE:
        order = tuple(Rashi)
        return str((order.index(facts.moon_sign) - order.index(person.janma_rasi)) % 12 + 1)
    raise ValueError(f"not a person factor: {rule.kind}")  # pragma: no cover


def evaluate_factors(
    purpose: Purpose,
    facts: MomentFacts,
    numbers: dict[str, int],
    participants: tuple[JanmaInput, ...],
) -> tuple[FactorResult, ...]:
    out: list[FactorResult] = []
    for rule in RULES[purpose]:
        common = dict(
            rule_id=rule.rule_id,
            kind=rule.kind,
            evidence_label=rule.evidence_label,
            reference=rule.reference,
        )
        if rule.kind is FactorKind.NOT_EVALUATED:
            out.append(
                FactorResult(
                    **common,  # type: ignore[arg-type]
                    status=FactorStatus.NOT_EVALUABLE,
                    reason=rule.not_evaluable_reason,
                )
            )
            continue
        if rule.person_specific:
            if not participants:
                out.append(
                    FactorResult(
                        **common,  # type: ignore[arg-type]
                        status=FactorStatus.NOT_EVALUABLE,
                        reason="requires_janma_nakshatra_and_rasi",
                    )
                )
                continue
            for i, person in enumerate(participants):
                value = _person_value(rule, facts, person)
                status, cls, reason = _classify(rule, value)
                out.append(
                    FactorResult(
                        **common,  # type: ignore[arg-type]
                        status=status,
                        participant=i,
                        value=value,
                        classification=cls,
                        reason=reason,
                    )
                )
            continue
        if rule.kind is FactorKind.HOUSE_OCCUPANTS:
            assert rule.house is not None
            occ = [f"{rule.house}:{b}" for b in _occupants(facts, rule.house)]
            if not occ:
                out.append(
                    FactorResult(
                        **common,  # type: ignore[arg-type]
                        status=FactorStatus.SUCCESS,
                        value="vacant",
                        classification=Classification.NOT_LISTED,
                    )
                )
                continue
            classes = [_classify(rule, v)[1] or Classification.NOT_LISTED for v in occ]
            worst = max(classes, key=lambda c: _RANK[c])
            out.append(
                FactorResult(
                    **common,  # type: ignore[arg-type]
                    status=FactorStatus.SUCCESS,
                    value=",".join(occ),
                    classification=worst,
                )
            )
            continue
        value = _value(rule, facts, numbers)
        status, cls, reason = _classify(rule, value)
        out.append(
            FactorResult(
                **common,  # type: ignore[arg-type]
                status=status,
                value=value,
                classification=cls,
                reason=reason,
            )
        )
    return tuple(out)


def summarize(factors: tuple[FactorResult, ...]) -> Summary:
    def count(c: Classification) -> int:
        return sum(1 for f in factors if f.classification is c)

    unfav = tuple(
        dict.fromkeys(f.rule_id for f in factors if f.classification is Classification.UNFAVOURABLE)
    )
    ne = tuple(dict.fromkeys(f.rule_id for f in factors if f.status is FactorStatus.NOT_EVALUABLE))
    return Summary(
        favourable=count(Classification.FAVOURABLE),
        middling=count(Classification.MIDDLING),
        unfavourable=count(Classification.UNFAVOURABLE),
        not_listed=count(Classification.NOT_LISTED),
        not_evaluable=sum(1 for f in factors if f.status is FactorStatus.NOT_EVALUABLE),
        unfavourable_rule_ids=unfav,
        not_evaluable_rule_ids=ne,
        no_unfavourable_factor=not unfav,
    )


def _sign_change(lon: Callable[[float], float], a: float, b: float) -> float | None:
    """Bisection for one sign change of a slow body within [a, b]."""
    sa = int(lon(a) // 30.0)
    if int(lon(b) // 30.0) == sa:
        return None
    lo, hi = a, b
    while hi - lo > 1e-7:
        mid = (lo + hi) / 2.0
        if int(lon(mid) // 30.0) == sa:
            lo = mid
        else:
            hi = mid
    return hi


class MuhurtaService:
    """Stateless facade for Muhurta evaluation and search."""

    def __init__(self, ephemeris_path: str | None = _UNSET) -> None:  # type: ignore[assignment]
        resolved = Settings().ephemeris_path if ephemeris_path is _UNSET else ephemeris_path
        ephemeris.configure_ephemeris_path(resolved)

    def evaluate(self, request: MuhurtaEvaluateRequest) -> MuhurtaEvaluation:
        tz = timezones.resolve_timezone(request.local_datetime.timezone)
        utc, _ = timezones.resolve_local_datetime(request.local_datetime)
        jd = jd_of(utc)
        sky = Sky(allow_moshier_fallback=request.allow_moshier_fallback)
        frame = self._frame_for(jd, utc.astimezone(tz).date(), request.location, tz,
                                request.sunrise_convention)  # fmt: skip
        base = dict(
            system=PANCHANG_SYSTEM_ID,
            standards_version=PANCHANG_STANDARDS_VERSION,
            rules_version=MUHURTA_RULES_VERSION,
            engine_version=__version__,
            purpose=request.purpose,
            sunrise_convention=request.sunrise_convention,
            ayanamsa="lahiri",
            instant=to_instant(jd, tz),
            notes=NOTES,
        )
        if frame is None:
            return MuhurtaEvaluation(
                **base,  # type: ignore[arg-type]
                status=FactorStatus.NOT_EVALUABLE,
                reason="sunrise_not_occurring",
            )
        facts, numbers = moment_facts(
            sky, jd, frame, request.location, request.allow_moshier_fallback
        )
        factors = evaluate_factors(request.purpose, facts, numbers, request.participants)
        return MuhurtaEvaluation(
            **base,  # type: ignore[arg-type]
            status=FactorStatus.SUCCESS,
            facts=facts,
            factors=factors,
            summary=summarize(factors),
        )

    def search(self, request: MuhurtaSearchRequest) -> MuhurtaSearchResult:
        tz = timezones.resolve_timezone(request.timezone)
        sky = Sky(allow_moshier_fallback=request.allow_moshier_fallback)
        loc = request.location
        windows: list[MuhurtaWindow] = []
        skipped: list[dt.date] = []
        examined = 0
        for offset in range(request.days):
            date = request.start_date + dt.timedelta(days=offset)
            frame = DayFrame(date=date, location=loc, tz=tz, convention=request.sunrise_convention)
            if not frame.complete:
                skipped.append(date)
                continue
            assert frame.sunrise is not None and frame.sunset is not None
            assert frame.next_sunrise is not None
            cuts = self._boundaries(sky, frame, loc, request.allow_moshier_fallback)
            current: tuple[float, float, MomentFacts, Summary, tuple[object, ...]] | None = None
            for a, b in zip(cuts, cuts[1:], strict=False):
                if b - a < 1e-6:
                    continue
                examined += 1
                mid = (a + b) / 2.0
                facts, numbers = moment_facts(sky, mid, frame, loc, request.allow_moshier_fallback)
                factors = evaluate_factors(request.purpose, facts, numbers, request.participants)
                summary = summarize(factors)
                key = tuple((f.rule_id, f.participant, f.classification) for f in factors)
                if not summary.no_unfavourable_factor:
                    if current is not None:
                        windows.append(self._window(current, tz))
                        current = None
                    continue
                if current is not None and current[4] == key:
                    current = (current[0], b, current[2], current[3], key)
                else:
                    if current is not None:
                        windows.append(self._window(current, tz))
                    current = (a, b, facts, summary, key)
            if current is not None:
                windows.append(self._window(current, tz))
        return MuhurtaSearchResult(
            system=PANCHANG_SYSTEM_ID,
            standards_version=PANCHANG_STANDARDS_VERSION,
            rules_version=MUHURTA_RULES_VERSION,
            engine_version=__version__,
            purpose=request.purpose,
            sunrise_convention=request.sunrise_convention,
            ayanamsa="lahiri",
            start_date=request.start_date,
            days=request.days,
            timezone=request.timezone,
            location=loc,
            segments_examined=examined,
            days_not_evaluable=tuple(skipped),
            windows=tuple(windows),
            rules=tuple(r.rule_id for r in RULES[request.purpose]),
            notes=NOTES,
        )

    @staticmethod
    def _window(
        current: tuple[float, float, MomentFacts, Summary, tuple[object, ...]], tz: ZoneInfo
    ) -> MuhurtaWindow:
        a, b, facts, summary, _key = current
        return MuhurtaWindow(
            start=to_instant(a, tz), end=to_instant(b, tz), facts_at_midpoint=facts,
            summary=summary,
        )  # fmt: skip

    @staticmethod
    def _frame_for(
        jd: float, local_date: dt.date, location: Location, tz: ZoneInfo, conv: SunriseConvention
    ) -> DayFrame | None:
        frame = DayFrame(date=local_date, location=location, tz=tz, convention=conv)
        if frame.complete and frame.sunrise is not None and jd < frame.sunrise:
            frame = DayFrame(
                date=local_date - dt.timedelta(days=1), location=location, tz=tz, convention=conv
            )
        if not frame.complete:
            return None
        return frame

    @staticmethod
    def _boundaries(sky: Sky, frame: DayFrame, loc: Location, fallback: bool) -> list[float]:
        sr, ss, nsr = frame.sunrise, frame.sunset, frame.next_sunrise
        assert sr is not None and ss is not None and nsr is not None
        cuts = {sr, ss, (sr + ss) / 2.0, nsr}

        def add_all(fn: Callable[[float], float], kin: astro.Kinematics, span: float) -> None:
            t = sr
            while True:
                jd, _ = astro.next_crossing(fn, kin, span, t)
                if jd >= nsr:
                    return
                cuts.add(jd)
                t = jd + 1e-6

        add_all(sky.elongation, astro.ELONGATION, KARANA_SPAN_DEGREES)  # tithis and karanas
        add_all(sky.moon_sidereal, astro.MOON, NAKSHATRA_SPAN_DEGREES / 4.0)  # padas, signs
        add_all(sky.yoga_sum, astro.YOGA, YOGA_SPAN_DEGREES)

        def asc(jd: float) -> float:
            return sky.ascendant_sidereal(jd, latitude=loc.latitude, longitude=loc.longitude)

        add_all(asc, astro.ASCENDANT, _NAVAMSA_SPAN)
        for name, swe_id in _CHART_BODIES:
            if name == "moon":
                continue

            def lon(jd: float, swe_id: int = swe_id) -> float:
                raw = ephemeris.calculate_body(
                    jd, swe_id, sidereal=False, allow_moshier_fallback=fallback
                )
                return (raw.longitude - sky.lahiri(jd)) % 360.0

            change = _sign_change(lon, sr, nsr)
            if change is not None:
                cuts.add(change)
        return sorted(cuts)
