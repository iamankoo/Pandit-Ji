"""Period lookup over a `DashaFacts` timeline (historical, current, future).

The engine never reads a clock: "current" is whatever instant the caller
passes. Half-open intervals: at a shared boundary the later period owns the
instant; the timeline's own end is exclusive.
"""

from __future__ import annotations

import datetime as dt
from bisect import bisect_right

from pandit_astro_engine.dashas.constants import LEVEL_ORDER, DashaLevel
from pandit_astro_engine.dashas.models import (
    DashaFacts,
    DashaReason,
    DashaStatus,
    LevelPosition,
    PeriodNode,
    PeriodQueryResult,
    PeriodResolution,
    RangePosition,
    Transition,
)
from pandit_astro_engine.models import CelestialBody

_ONE_US = dt.timedelta(microseconds=1)


class DashaTimeline:
    """Indexed view of one successful `DashaFacts` for repeated lookups."""

    def __init__(self, facts: DashaFacts) -> None:
        self.facts = facts
        self._by_level: dict[DashaLevel, list[PeriodNode]] = {level: [] for level in LEVEL_ORDER}
        self._children: dict[str, list[PeriodNode]] = {}
        for node in facts.periods:
            self._by_level[node.level].append(node)
            if node.parent_id is not None:
                self._children.setdefault(node.parent_id, []).append(node)
        self._starts: dict[str, list[dt.datetime]] = {}
        self._top_starts = [node.start_utc for node in self._by_level[DashaLevel.MAHADASHA]]

    # ------------------------------------------------------------------

    def resolve(self, at_utc: dt.datetime) -> PeriodResolution:
        """Mahadasha / Antardasha / Pratyantar owning `at_utc`."""
        if at_utc.tzinfo is None or at_utc.utcoffset() is None:
            return PeriodResolution(
                status=DashaStatus.INVALID_INPUT, reason_code=DashaReason.NAIVE_DATETIME
            )
        if self.facts.status not in (DashaStatus.SUCCESS, DashaStatus.APPROXIMATE):
            return PeriodResolution(status=self.facts.status, reason_code=self.facts.reason_code)
        at = at_utc.astimezone(dt.timezone.utc)
        assert self.facts.timeline_start_utc is not None and self.facts.timeline_end_utc is not None
        if at < self.facts.timeline_start_utc:
            return PeriodResolution(
                status=self.facts.status,
                range_position=RangePosition.BEFORE_TIMELINE,
                at_utc=at,
            )
        if at >= self.facts.timeline_end_utc:
            return PeriodResolution(
                status=self.facts.status,
                range_position=RangePosition.AT_OR_AFTER_TIMELINE_END,
                at_utc=at,
            )

        levels: list[LevelPosition] = []
        node = self._owner(self._by_level[DashaLevel.MAHADASHA], self._top_starts, at)
        while node is not None:
            levels.append(
                LevelPosition(
                    period_id=node.period_id,
                    level=node.level,
                    lord=node.lord,
                    start_utc=node.start_utc,
                    end_utc=node.end_utc,
                    elapsed_microseconds=(at - node.start_utc) // _ONE_US,
                    remaining_microseconds=(node.end_utc - at) // _ONE_US,
                )
            )
            children = self._children.get(node.period_id)
            if not children:
                break
            starts = self._starts.setdefault(node.period_id, [c.start_utc for c in children])
            node = self._owner(children, starts, at)
        return PeriodResolution(
            status=self.facts.status,
            range_position=RangePosition.WITHIN_TIMELINE,
            at_utc=at,
            levels=tuple(levels),
            path=tuple(position.lord.value for position in levels),
        )

    @staticmethod
    def _owner(
        nodes: list[PeriodNode], starts: list[dt.datetime], at: dt.datetime
    ) -> PeriodNode | None:
        """Last node starting at or before `at`, provided `at` < its end."""
        index = bisect_right(starts, at) - 1
        if index < 0:
            return None
        node = nodes[index]
        return node if at < node.end_utc else None

    # ------------------------------------------------------------------

    def periods_in_window(
        self, start_utc: dt.datetime, end_utc: dt.datetime, level: DashaLevel
    ) -> PeriodQueryResult:
        """Periods of `level` overlapping [start_utc, end_utc)."""
        if start_utc.tzinfo is None or end_utc.tzinfo is None:
            return PeriodQueryResult(
                status=DashaStatus.INVALID_INPUT, reason_code=DashaReason.NAIVE_DATETIME
            )
        if end_utc < start_utc:
            return PeriodQueryResult(
                status=DashaStatus.INVALID_INPUT, reason_code=DashaReason.REVERSED_INTERVAL
            )
        matches = tuple(
            node
            for node in self._by_level[level]
            if node.start_utc < end_utc and node.end_utc > start_utc
        )
        return PeriodQueryResult(status=DashaStatus.SUCCESS, periods=matches)

    def periods_for_lord(self, lord_id: str, level: DashaLevel) -> PeriodQueryResult:
        """Every period of `level` ruled by `lord_id`. An unknown lord is rejected."""
        try:
            lord = CelestialBody(lord_id)
        except ValueError:
            return PeriodQueryResult(
                status=DashaStatus.INVALID_INPUT, reason_code=DashaReason.UNKNOWN_LORD
            )
        matches = tuple(node for node in self._by_level[level] if node.lord is lord)
        return PeriodQueryResult(status=DashaStatus.SUCCESS, periods=matches)

    def transitions(self, level: DashaLevel) -> tuple[Transition, ...]:
        """Boundaries between consecutive periods of `level`, in order. A
        zero-length period is passed through, so each transition links
        neighbours."""
        nodes = self._by_level[level]
        return tuple(
            Transition(
                level=level,
                at_utc=current.start_utc,
                from_period_id=previous.period_id,
                to_period_id=current.period_id,
                from_lord=previous.lord,
                to_lord=current.lord,
            )
            for previous, current in zip(nodes, nodes[1:], strict=False)
        )
