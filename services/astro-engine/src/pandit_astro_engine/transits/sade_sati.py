"""Sade Sati sign-band timeline (Phase 8, docs/ASTROLOGY_STANDARDS.md TR-09).

`SADE_SATI_SIGN_BASED_MODERN_V1` is a MODERN_TRADITION construct: it was not
found as a combined unit in the classical texts read. No classical certainty is
implied, no duration ("7.5 years") is asserted, and no Ashtakavarga is mixed in.

Given Saturn's sign timeline over a window (the sign at the window start and its
ingress events), this module builds

* **segments**: maximal intervals of Saturn in one band sign (band = the natal
  Moon sign - 1, 0, +1, phases 1..3); never merged across a gap;
* **episodes**: maximal runs of contiguous segments. An exit and re-entry gives
  a separate episode, flagged `retrograde_reentry_of_previous_episode` when the
  previous episode ended by backward motion or this episode was entered by
  backward motion (retrograde motion bounds the gap at either end).

A boundary before the window start or after the window end is unknown and is
returned as `None` with a clipped flag.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pandit_astro_engine.rashi import rashi_from_index
from pandit_astro_engine.transits.models import SadeSatiEpisode, SadeSatiSegment
from pandit_astro_engine.transits.profiles import SADE_SATI_PHASE_BY_OFFSET, SADE_SATI_PHASE_NAMES


@dataclass(frozen=True)
class SignIngress:
    """One Saturn sign ingress inside the window."""

    julian_day_ut: float
    from_sign: int
    to_sign: int
    retrograde: bool  # speed < 0 at the ingress: the move is backward


@dataclass(frozen=True)
class _Interval:
    sign: int
    start_jd: float | None
    end_jd: float | None
    entered_by_backward_motion: bool | None
    ended_by_backward_motion: bool | None


class InconsistentTimelineError(Exception):
    """The ingress list does not chain from the initial sign (internal error)."""


def band_phase(saturn_sign: int, moon_sign: int) -> int | None:
    return SADE_SATI_PHASE_BY_OFFSET.get((saturn_sign - moon_sign) % 12)


def _intervals(initial_sign: int, ingresses: Sequence[SignIngress]) -> list[_Interval]:
    intervals: list[_Interval] = []
    sign = initial_sign
    start: float | None = None
    entered_backward: bool | None = None
    for ingress in ingresses:
        if ingress.from_sign != sign:
            raise InconsistentTimelineError(f"ingress from {ingress.from_sign}, expected {sign}")
        intervals.append(
            _Interval(sign, start, ingress.julian_day_ut, entered_backward, ingress.retrograde)
        )
        sign = ingress.to_sign
        start = ingress.julian_day_ut
        entered_backward = ingress.retrograde
    intervals.append(_Interval(sign, start, None, entered_backward, None))
    return intervals


def _stamp(instant: dt.datetime | None, fallback: str) -> str:
    return instant.isoformat() if instant is not None else fallback


def build_sade_sati(
    moon_sign: int,
    initial_sign: int,
    ingresses: Sequence[SignIngress],
    to_datetime: Callable[[float], dt.datetime],
) -> tuple[tuple[SadeSatiSegment, ...], tuple[SadeSatiEpisode, ...]]:
    segments: list[SadeSatiSegment] = []
    episodes: list[SadeSatiEpisode] = []
    run: list[tuple[_Interval, SadeSatiSegment]] = []

    def close_run() -> None:
        if not run:
            return
        first_interval, first_segment = run[0]
        last_interval, last_segment = run[-1]
        previous = episodes[-1] if episodes else None
        reentry = previous is not None and bool(
            previous.ended_by_backward_motion or first_interval.entered_by_backward_motion
        )
        episodes.append(
            SadeSatiEpisode(
                episode_id=f"SSE:{_stamp(first_segment.start_utc, 'window_start')}",
                segment_ids=tuple(seg.segment_id for _, seg in run),
                start_utc=first_segment.start_utc,
                end_utc=last_segment.end_utc,
                clipped_at_window_start=first_interval.start_jd is None,
                clipped_at_window_end=last_interval.end_jd is None,
                entered_by_backward_motion=first_interval.entered_by_backward_motion,
                ended_by_backward_motion=last_interval.ended_by_backward_motion,
                retrograde_reentry_of_previous_episode=reentry,
            )
        )
        run.clear()

    for interval in _intervals(initial_sign, ingresses):
        phase = band_phase(interval.sign, moon_sign)
        if phase is None:
            close_run()
            continue
        start = to_datetime(interval.start_jd) if interval.start_jd is not None else None
        end = to_datetime(interval.end_jd) if interval.end_jd is not None else None
        sign = rashi_from_index(interval.sign)
        segment = SadeSatiSegment(
            segment_id=f"SSG:{sign.value}:{_stamp(start, 'window_start')}",
            sign=sign,
            phase=phase,
            phase_name=SADE_SATI_PHASE_NAMES[phase],
            start_utc=start,
            end_utc=end,
            clipped_at_window_start=interval.start_jd is None,
            clipped_at_window_end=interval.end_jd is None,
            entered_by_backward_motion=interval.entered_by_backward_motion,
            ended_by_backward_motion=interval.ended_by_backward_motion,
        )
        segments.append(segment)
        run.append((interval, segment))
    close_run()
    return tuple(segments), tuple(episodes)
