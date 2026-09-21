"""Sade Sati sign-band segments and episodes (docs/ASTROLOGY_STANDARDS.md TR-09):
a MODERN_TRADITION construct on Saturn's sign timeline."""

from __future__ import annotations

import pytest
from transit_helpers import JD0

from pandit_astro_engine.rashi import Rashi
from pandit_astro_engine.transits.positions import jd_to_datetime
from pandit_astro_engine.transits.sade_sati import (
    InconsistentTimelineError,
    SignIngress,
    band_phase,
    build_sade_sati,
)

MOON = 5  # band signs: 4 (phase 1), 5 (phase 2), 6 (phase 3)


def ing(day: float, from_sign: int, to_sign: int, retro: bool = False) -> SignIngress:
    return SignIngress(JD0 + day, from_sign, to_sign, retro)


def build(initial: int, ingresses: list[SignIngress], moon: int = MOON):  # type: ignore[no-untyped-def]
    return build_sade_sati(moon, initial, ingresses, jd_to_datetime)


def test_band_phase_offsets() -> None:
    assert [band_phase(s, MOON) for s in (3, 4, 5, 6, 7)] == [None, 1, 2, 3, None]
    assert band_phase(11, 0) == 1 and band_phase(0, 11) == 3  # wraps around Pisces/Aries


def test_a_forward_pass_is_three_segments_in_one_episode() -> None:
    segments, episodes = build(3, [ing(10, 3, 4), ing(20, 4, 5), ing(30, 5, 6), ing(40, 6, 7)])
    assert [(s.sign, s.phase) for s in segments] == [
        (Rashi.LEO, 1),
        (Rashi.VIRGO, 2),
        (Rashi.LIBRA, 3),
    ]
    assert [s.phase_name for s in segments] == [
        "twelfth_from_moon",
        "first_from_moon",
        "second_from_moon",
    ]
    (episode,) = episodes
    assert episode.segment_ids == tuple(s.segment_id for s in segments)
    assert episode.start_utc == segments[0].start_utc and episode.end_utc == segments[2].end_utc
    assert episode.retrograde_reentry_of_previous_episode is False
    assert not episode.clipped_at_window_start and not episode.clipped_at_window_end


def test_segments_within_an_episode_tile_with_no_gap_or_overlap() -> None:
    segments, _ = build(3, [ing(10, 3, 4), ing(20, 4, 5), ing(30, 5, 6), ing(40, 6, 7)])
    for left, right in zip(segments, segments[1:], strict=False):
        assert left.end_utc == right.start_utc


def test_no_pass_gives_no_segments_and_no_episodes() -> None:
    assert build(9, [ing(10, 9, 10)]) == ((), ())


def test_saturn_in_the_band_for_the_whole_window_is_clipped_on_both_sides() -> None:
    segments, episodes = build(5, [])
    (segment,) = segments
    assert segment.start_utc is None and segment.end_utc is None
    assert segment.clipped_at_window_start and segment.clipped_at_window_end
    assert segment.segment_id == "SSG:virgo:window_start"
    (episode,) = episodes
    assert episode.start_utc is None and episode.end_utc is None
    assert episode.episode_id == "SSE:window_start"


def test_a_window_starting_inside_the_band_clips_the_first_segment_only() -> None:
    segments, episodes = build(5, [ing(10, 5, 6), ing(20, 6, 7)])
    assert segments[0].clipped_at_window_start and segments[0].start_utc is None
    assert segments[0].end_utc is not None and not segments[0].clipped_at_window_end
    assert episodes[0].clipped_at_window_start and not episodes[0].clipped_at_window_end


def test_a_window_ending_inside_the_band_clips_the_last_segment_only() -> None:
    segments, episodes = build(3, [ing(10, 3, 4), ing(20, 4, 5)])
    assert segments[-1].end_utc is None and segments[-1].clipped_at_window_end
    assert episodes[-1].clipped_at_window_end and not episodes[-1].clipped_at_window_start


def test_retrograde_exit_and_forward_reentry_is_a_second_flagged_episode() -> None:
    # 3 -> 4 (in) -> 3 (out, retrograde) -> 4 (in again, forward) -> 5
    segments, episodes = build(
        3, [ing(10, 3, 4), ing(20, 4, 3, retro=True), ing(30, 3, 4), ing(40, 4, 5)]
    )
    assert len(episodes) == 2
    assert episodes[0].ended_by_backward_motion is True
    assert episodes[0].retrograde_reentry_of_previous_episode is False
    assert episodes[1].retrograde_reentry_of_previous_episode is True
    # Never merged across the gap, even though both segments are the same sign.
    assert [s.sign for s in segments[:2]] == [Rashi.LEO, Rashi.LEO]
    assert segments[0].segment_id != segments[1].segment_id


def test_forward_exit_and_retrograde_reentry_is_flagged_by_the_entry() -> None:
    # 5 -> 6 -> 7 (out, forward) -> 6 (in again, retrograde) -> 7
    _, episodes = build(5, [ing(10, 5, 6), ing(20, 6, 7), ing(30, 7, 6, retro=True), ing(40, 6, 7)])
    assert len(episodes) == 2
    assert episodes[0].ended_by_backward_motion is False
    assert episodes[1].entered_by_backward_motion is True
    assert episodes[1].retrograde_reentry_of_previous_episode is True


def test_a_plain_second_pass_after_a_forward_exit_is_not_a_retrograde_reentry() -> None:
    _, episodes = build(5, [ing(10, 5, 6), ing(20, 6, 7), ing(30, 7, 8)], moon=5)
    assert len(episodes) == 1 and episodes[0].retrograde_reentry_of_previous_episode is False


def test_backward_motion_inside_the_band_does_not_split_an_episode() -> None:
    segments, episodes = build(4, [ing(10, 4, 5), ing(20, 5, 4, retro=True), ing(30, 4, 5)])
    assert len(episodes) == 1
    assert [s.sign for s in segments] == [Rashi.LEO, Rashi.VIRGO, Rashi.LEO, Rashi.VIRGO]
    assert segments[2].entered_by_backward_motion is True
    assert segments[1].ended_by_backward_motion is True


def test_ids_are_unique_and_deterministic() -> None:
    args = (3, [ing(10, 3, 4), ing(20, 4, 3, retro=True), ing(30, 3, 4), ing(40, 4, 5)])
    first = build(*args)
    assert first == build(*args)
    ids = [s.segment_id for s in first[0]] + [e.episode_id for e in first[1]]
    assert len(ids) == len(set(ids))


def test_an_inconsistent_ingress_chain_is_rejected() -> None:
    with pytest.raises(InconsistentTimelineError):
        build(3, [ing(10, 4, 5)])
    with pytest.raises(InconsistentTimelineError):
        build(3, [ing(10, 3, 4), ing(20, 6, 7)])


def test_the_wrapping_band_has_the_expected_phases() -> None:
    segments, _ = build(10, [ing(10, 10, 11), ing(20, 11, 0), ing(30, 0, 1)], moon=11)
    assert [(s.sign, s.phase) for s in segments] == [
        (Rashi.AQUARIUS, 1),
        (Rashi.PISCES, 2),
        (Rashi.ARIES, 3),
    ]
