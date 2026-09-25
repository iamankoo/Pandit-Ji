"""KP star/sub/sub-sub division and the 249-entry table (Phase 9 WP-E,
KP-05 to KP-07). Reference values come from KP Reader III and VI (OCR,
fixture `kp_reader3_sub_table.json`), never from the implementation."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from pandit_astro_engine.dashas.constants import VIMSHOTTARI_YEARS
from pandit_astro_engine.kp.subdivision import kp_lords, kp_table, kp_table_entry
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import nakshatra_position
from pandit_astro_engine.rashi import Rashi

FIXTURE = Path(__file__).parent / "fixtures" / "kp_reader3_sub_table.json"


def _dms(text: str) -> Fraction:
    d, m, s = (int(x) for x in text.split("-"))
    return Fraction(d) + Fraction(m, 60) + Fraction(s, 3600)


def _deg(d: int, m: int = 0, s: int = 0) -> float:
    return d + m / 60 + s / 3600


def test_table_has_249_entries_tiling_the_zodiac() -> None:
    table = kp_table()
    assert len(table) == 249
    assert table[0].start == 0
    assert table[-1].end == 360
    for previous, current in zip(table, table[1:], strict=False):
        assert previous.end == current.start
        assert current.number == previous.number + 1


def test_exactly_six_subs_are_split_by_a_sign_boundary() -> None:
    table = kp_table()
    split = [
        e
        for i, e in enumerate(table)
        if i and table[i - 1].nakshatra == e.nakshatra and table[i - 1].sub_lord == e.sub_lord
    ]
    assert len(split) == 6
    assert all(e.start % 30 == 0 for e in split)


def test_every_entry_lies_in_one_sign() -> None:
    for e in kp_table():
        assert e.start // 30 == (e.end - Fraction(1, 10**9)) // 30


def test_sub_spans_are_years_times_400_arcseconds() -> None:
    for e in kp_table():
        if e.start % 30 == 0 or e.end % 30 == 0:
            continue  # a split piece or a piece ending on a sign boundary
        width_arcsec = (e.end - e.start) * 3600
        assert width_arcsec == VIMSHOTTARI_YEARS[e.sub_lord] * 400


def test_first_sub_of_every_star_is_the_star_lord() -> None:
    seen: set[str] = set()
    for e in kp_table():
        if e.nakshatra.value not in seen:
            seen.add(e.nakshatra.value)
            assert e.sub_lord == e.star_lord
    assert len(seen) == 27


def test_reader3_printed_rows_match_the_derived_table() -> None:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = doc["rows"]
    assert len(rows) == 202
    index = {
        (
            e.sign_lord.value,
            e.star_lord.value,
            e.sub_lord.value,
            e.start % 30,
            (e.end % 30) or Fraction(30),
        ): e.number
        for e in kp_table()
    }
    numbered = 0
    for row in rows:
        key = (
            row["sign_lord"],
            row["star_lord"],
            row["sub_lord"],
            _dms(row["start_in_sign"]),
            _dms(row["end_in_sign"]),
        )
        assert key in index, row
        if row["printed_number"] is not None:
            numbered += 1
            assert index[key] == row["printed_number"], row
    assert numbered == 128


@pytest.mark.parametrize(
    ("number", "sign", "star_lord", "sub_lord", "start"),
    [
        # KP Reader VI: "number 48 refers to Mercury sign, Rahu star, Jupiter sub, which
        # commences at 8 deg 40 min in Gemini".
        (48, Rashi.GEMINI, CelestialBody.RAHU, CelestialBody.JUPITER, _deg(68, 40)),
        # KP Reader VI: 74 is Cancer, Saturn star Pushya, Jupiter sub from 14 deg 53' 20".
        (74, Rashi.CANCER, CelestialBody.SATURN, CelestialBody.JUPITER, _deg(104, 53, 20)),
        # KP Reader VI horary example: 29 puts the Ascendant at Taurus 10 deg 00'.
        (29, Rashi.TAURUS, CelestialBody.MOON, CelestialBody.MOON, _deg(40)),
        (1, Rashi.ARIES, CelestialBody.KETU, CelestialBody.KETU, 0.0),
        # KP Reader III: "249. Jupiter, Mercury, Saturn : (27-53-20)-(30-00-00)".
        (249, Rashi.PISCES, CelestialBody.MERCURY, CelestialBody.SATURN, _deg(357, 53, 20)),
    ],
)
def test_reader_worked_numbers(
    number: int, sign: Rashi, star_lord: CelestialBody, sub_lord: CelestialBody, start: float
) -> None:
    e = kp_table_entry(number)
    assert (e.sign, e.star_lord, e.sub_lord) == (sign, star_lord, sub_lord)
    assert float(e.start) == pytest.approx(start, abs=1e-9)


@pytest.mark.parametrize("number", [0, 250, -1])
def test_table_number_out_of_range(number: int) -> None:
    with pytest.raises(ValueError):
        kp_table_entry(number)


def test_lords_agree_with_the_table_and_the_phase5_nakshatra() -> None:
    for e in kp_table():
        mid = float((e.start + e.end) / 2)
        lords = kp_lords(mid)
        assert (lords.sign, lords.star_lord, lords.sub_lord) == (e.sign, e.star_lord, e.sub_lord)
        assert lords.nakshatra == nakshatra_position(mid).nakshatra


def test_boundary_belongs_to_the_later_sub() -> None:
    e = kp_table_entry(48)
    at = kp_lords(float(e.start))
    below = kp_lords(float(e.start) - 1e-9)
    assert at.sub_lord == CelestialBody.JUPITER
    assert below.sub_lord == CelestialBody.RAHU
    assert at.near_boundary and below.near_boundary


def test_sub_sub_division_tiles_the_sub() -> None:
    e = kp_table_entry(74)
    step = (e.end - e.start) / 5000
    lords = []
    for k in range(5000):
        lon = float(e.start + step * k + step / 2)
        info = kp_lords(lon)
        assert info.sub_start <= Fraction(lon) < info.sub_end
        assert info.sub_sub_start <= Fraction(lon) < info.sub_sub_end
        if not lords or lords[-1] != info.sub_sub_lord:
            lords.append(info.sub_sub_lord)
    # Nine sub-subs, starting with the sub lord, in Vimshottari order.
    assert lords == [
        CelestialBody.JUPITER,
        CelestialBody.SATURN,
        CelestialBody.MERCURY,
        CelestialBody.KETU,
        CelestialBody.VENUS,
        CelestialBody.SUN,
        CelestialBody.MOON,
        CelestialBody.MARS,
        CelestialBody.RAHU,
    ]


def test_sub_sub_widths_are_proportional() -> None:
    info = kp_lords(_deg(104, 53, 21))
    width = info.sub_sub_end - info.sub_sub_start
    sub_width = info.sub_end - info.sub_start
    assert width == sub_width * VIMSHOTTARI_YEARS[info.sub_sub_lord] / 120


@pytest.mark.parametrize("longitude", [-0.1, 360.0, 400.0])
def test_invalid_longitude_rejected(longitude: float) -> None:
    with pytest.raises(ValueError):
        kp_lords(longitude)


def test_deterministic() -> None:
    assert kp_lords(123.456789) == kp_lords(123.456789)
    assert kp_table() is kp_table()
