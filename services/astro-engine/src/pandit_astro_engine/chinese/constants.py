"""Stable identifiers and tables for the Chinese Four Pillars (BaZi)
calendar module (Phase 9 WP-H; `docs/ASTROLOGY_STANDARDS.md` v1.18.0,
CN-01 to CN-14; sources in `research/ASTROLOGY_SOURCES.md` Group 19).

Identifiers are Hanyu Pinyin without tones; the Chinese characters are
presentation data only. The element, polarity and animal tables follow
《三命通會》 (Sanming Tonghui) 卷二 論十干合 and 論地支屬相, and 卷三 論十干祿.
"""

from __future__ import annotations

from enum import Enum

#: Standards version recorded on every Chinese result (CN-13).
CHINESE_STANDARDS_VERSION = "1.18.0"

#: System tag. Never "vedic", "western" or "kp".
CHINESE_SYSTEM_ID = "chinese_bazi"


class Stem(str, Enum):
    JIA = "jia"
    YI = "yi"
    BING = "bing"
    DING = "ding"
    WU = "wu"
    JI = "ji"
    GENG = "geng"
    XIN = "xin"
    REN = "ren"
    GUI = "gui"


class Branch(str, Enum):
    ZI = "zi"
    CHOU = "chou"
    YIN = "yin"
    MAO = "mao"
    CHEN = "chen"
    SI = "si"
    WU = "wu"
    WEI = "wei"
    SHEN = "shen"
    YOU = "you"
    XU = "xu"
    HAI = "hai"


class Element(str, Enum):
    WOOD = "wood"
    FIRE = "fire"
    EARTH = "earth"
    METAL = "metal"
    WATER = "water"


class Polarity(str, Enum):
    YANG = "yang"
    YIN = "yin"


STEMS: tuple[Stem, ...] = tuple(Stem)
BRANCHES: tuple[Branch, ...] = tuple(Branch)

STEM_CHARACTER = dict(zip(STEMS, "甲乙丙丁戊己庚辛壬癸", strict=True))
BRANCH_CHARACTER = dict(zip(BRANCHES, "子丑寅卯辰巳午未申酉戌亥", strict=True))

#: 甲乙 wood, 丙丁 fire, 戊己 earth, 庚辛 metal, 壬癸 water; the first of each
#: pair is yang (卷二 論十干合: "甲屬陽為兄，乙屬陰為妹" ...).
STEM_ELEMENT: dict[Stem, Element] = {
    s: (Element.WOOD, Element.FIRE, Element.EARTH, Element.METAL, Element.WATER)[i // 2]
    for i, s in enumerate(STEMS)
}
STEM_POLARITY: dict[Stem, Polarity] = {
    s: Polarity.YANG if i % 2 == 0 else Polarity.YIN for i, s in enumerate(STEMS)
}

#: 卷三 論十干祿: 寅卯 with 甲乙 (wood), 巳午 with 丙丁 (fire), 申酉 with 庚辛
#: (metal), 亥子 with 壬癸 (water); 辰戌丑未 are the earth positions.
BRANCH_ELEMENT: dict[Branch, Element] = {
    Branch.ZI: Element.WATER,
    Branch.CHOU: Element.EARTH,
    Branch.YIN: Element.WOOD,
    Branch.MAO: Element.WOOD,
    Branch.CHEN: Element.EARTH,
    Branch.SI: Element.FIRE,
    Branch.WU: Element.FIRE,
    Branch.WEI: Element.EARTH,
    Branch.SHEN: Element.METAL,
    Branch.YOU: Element.METAL,
    Branch.XU: Element.EARTH,
    Branch.HAI: Element.WATER,
}

#: 卷二 論地支屬相: 子鼠 丑牛 寅虎 卯兔 辰龍 巳蛇 午馬 未羊 申猴 酉雞 戌犬 亥豬;
#: 鼠 虎 龍 馬 猴 犬 (odd positions) yang, the others yin.
BRANCH_ANIMAL: dict[Branch, str] = dict(
    zip(
        BRANCHES,
        (
            "rat",
            "ox",
            "tiger",
            "rabbit",
            "dragon",
            "snake",
            "horse",
            "goat",
            "monkey",
            "rooster",
            "dog",
            "pig",
        ),
        strict=True,
    )
)
BRANCH_POLARITY: dict[Branch, Polarity] = {
    b: Polarity.YANG if i % 2 == 0 else Polarity.YIN for i, b in enumerate(BRANCHES)
}

#: Sun apparent longitudes of the twelve "jie" terms that open the months,
#: starting with 立春 (Lichun, 315 degrees) which opens the 寅 month.
FIRST_JIE_LONGITUDE = 315.0

#: Offset added to the Julian Day Number so that index 0 is 甲子 (CN-06).
JDN_SEXAGENARY_OFFSET = 49

#: A Sun longitude within this many degrees of a jie term (about 9 seconds
#: of time) is flagged `near_solar_term`.
SOLAR_TERM_EPSILON_DEGREES = 1e-4


class TimeBasis(str, Enum):
    """The clock that fixes the day and hour pillars (CN-08); no default."""

    CLOCK_TIME = "clock_time"
    LOCAL_MEAN_SOLAR_TIME = "local_mean_solar_time"
    LOCAL_APPARENT_SOLAR_TIME = "local_apparent_solar_time"


class DayBoundary(str, Enum):
    """Where the day pillar changes (CN-09); no default."""

    ZI_HOUR_2300 = "zi_hour_2300"
    MIDNIGHT = "midnight"


class ChineseTimePrecision(str, Enum):
    EXACT = "exact"
    UNKNOWN = "unknown"


class PillarStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class PillarReason(str, Enum):
    BIRTH_TIME_UNKNOWN = "birth_time_unknown"
    SOLAR_TERM_ON_BIRTH_DATE = "solar_term_on_birth_date"
    LATE_ZI_HOUR_STEM_UNRESOLVED = "late_zi_hour_stem_unresolved"
