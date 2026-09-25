"""Panchang vocabularies (Phase 10; `docs/ASTROLOGY_STANDARDS.md` v1.23.0,
PC-01 to PC-30). Stable, language-neutral identifiers; display names belong
to the presentation layer.
"""

from __future__ import annotations

from enum import Enum

from pandit_astro_engine.models import CelestialBody

TITHI_SPAN_DEGREES = 12.0
KARANA_SPAN_DEGREES = 6.0
YOGA_SPAN_DEGREES = 360.0 / 27.0
NAKSHATRA_SPAN_DEGREES = 360.0 / 27.0
SIGN_SPAN_DEGREES = 30.0

#: Ghati of 24 minutes of civil time (60 to a 24-hour day) and pala
#: (vighati) of 24 seconds: PC-24, an engineering convention.
GHATI_MINUTES = 24.0
PALA_SECONDS = 24.0


class Paksha(str, Enum):
    SHUKLA = "shukla"
    KRISHNA = "krishna"


class TithiName(str, Enum):
    PRATIPADA = "pratipada"
    DVITIYA = "dvitiya"
    TRITIYA = "tritiya"
    CHATURTHI = "chaturthi"
    PANCHAMI = "panchami"
    SHASHTHI = "shashthi"
    SAPTAMI = "saptami"
    ASHTAMI = "ashtami"
    NAVAMI = "navami"
    DASHAMI = "dashami"
    EKADASHI = "ekadashi"
    DVADASHI = "dvadashi"
    TRAYODASHI = "trayodashi"
    CHATURDASHI = "chaturdashi"
    PURNIMA = "purnima"
    AMAVASYA = "amavasya"


_TITHI_BASE = tuple(TithiName)[:14]


def tithi_name(index: int) -> TithiName:
    """`index` 1-30: Shukla 1-15, Krishna 1-14 as 16-29, Amavasya 30."""
    if index == 15:
        return TithiName.PURNIMA
    if index == 30:
        return TithiName.AMAVASYA
    return _TITHI_BASE[(index - 1) % 15]


def tithi_paksha(index: int) -> Paksha:
    return Paksha.SHUKLA if index <= 15 else Paksha.KRISHNA


def tithi_number_in_paksha(index: int) -> int:
    """1-15 in the Shukla half; 1-14 and 30 (new moon) in the Krishna half,
    the numbering of the Calendar Reform Committee's calendar."""
    if index <= 15:
        return index
    return 30 if index == 30 else index - 15


class YogaName(str, Enum):
    VISHKAMBHA = "vishkambha"
    PRITI = "priti"
    AYUSHMAN = "ayushman"
    SAUBHAGYA = "saubhagya"
    SHOBHANA = "shobhana"
    ATIGANDA = "atiganda"
    SUKARMA = "sukarma"
    DHRITI = "dhriti"
    SHULA = "shula"
    GANDA = "ganda"
    VRIDDHI = "vriddhi"
    DHRUVA = "dhruva"
    VYAGHATA = "vyaghata"
    HARSHANA = "harshana"
    VAJRA = "vajra"
    SIDDHI = "siddhi"
    VYATIPATA = "vyatipata"
    VARIYAN = "variyan"
    PARIGHA = "parigha"
    SHIVA = "shiva"
    SIDDHA = "siddha"
    SADHYA = "sadhya"
    SHUBHA = "shubha"
    SHUKLA = "shukla"
    BRAHMA = "brahma"
    INDRA = "indra"
    VAIDHRITI = "vaidhriti"


class KaranaName(str, Enum):
    BAVA = "bava"
    BALAVA = "balava"
    KAULAVA = "kaulava"
    TAITILA = "taitila"
    GARA = "gara"
    VANIJA = "vanija"
    VISHTI = "vishti"
    SHAKUNI = "shakuni"
    CHATUSHPADA = "chatushpada"
    NAGA = "naga"
    KIMSTUGHNA = "kimstughna"


_MOVABLE_KARANAS = tuple(KaranaName)[:7]


def karana_name(index: int) -> KaranaName:
    """`index` 1-60, the half-tithis from the new moon: 1 Kimstughna; 2-57
    the seven movable karanas eight times; 58 Shakuni; 59 Chatushpada;
    60 Naga (PC-11)."""
    if index == 1:
        return KaranaName.KIMSTUGHNA
    if index == 58:
        return KaranaName.SHAKUNI
    if index == 59:
        return KaranaName.CHATUSHPADA
    if index == 60:
        return KaranaName.NAGA
    return _MOVABLE_KARANAS[(index - 2) % 7]


class MonthName(str, Enum):
    CHAITRA = "chaitra"
    VAISHAKHA = "vaishakha"
    JYESHTHA = "jyeshtha"
    ASHADHA = "ashadha"
    SHRAVANA = "shravana"
    BHADRAPADA = "bhadrapada"
    ASHVINA = "ashvina"
    KARTIKA = "kartika"
    MARGASHIRSHA = "margashirsha"
    PAUSHA = "pausha"
    MAGHA = "magha"
    PHALGUNA = "phalguna"


MONTH_ORDER: tuple[MonthName, ...] = tuple(MonthName)


def saura_month_of_sign(sign_index: int) -> MonthName:
    """The saura month that begins when the Sun enters sign `sign_index`
    (0 = Mesha begins saura Vaishakha; 11 = Meena begins saura Chaitra;
    CRC 1955 recommendation (5))."""
    return MONTH_ORDER[(sign_index + 1) % 12]


#: Weekday lords, Sunday = 0 (Sewell and Dikshit Art. 5).
WEEKDAY_LORD: tuple[CelestialBody, ...] = (
    CelestialBody.SUN,
    CelestialBody.MOON,
    CelestialBody.MARS,
    CelestialBody.MERCURY,
    CelestialBody.JUPITER,
    CelestialBody.VENUS,
    CelestialBody.SATURN,
)


class Weekday(str, Enum):
    SUNDAY = "sunday"
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"


WEEKDAY_ORDER: tuple[Weekday, ...] = tuple(Weekday)


def hora_sequence(first_lord: CelestialBody, count: int) -> tuple[CelestialBody, ...]:
    """Each hora lord is the sixth, in weekday order, from the previous one
    (Kalaprakasika Ch. XXXIII, p. 176), the first being the weekday lord."""
    index = WEEKDAY_LORD.index(first_lord)
    out = []
    for _ in range(count):
        out.append(WEEKDAY_LORD[index])
        index = (index + 5) % 7
    return tuple(out)


class Tara(str, Enum):
    JANMA = "janma"
    SAMPAT = "sampat"
    VIPAT = "vipat"
    KSHEMA = "kshema"
    PRATYAK = "pratyak"
    SADHANA = "sadhana"
    NAIDHANA = "naidhana"
    MITRA = "mitra"
    PARAMA_MITRA = "parama_mitra"


TARA_ORDER: tuple[Tara, ...] = tuple(Tara)


class PanchakaRemainder(str, Enum):
    """Remainders of (tithi + weekday + nakshatra + lagna) / 9 (Raman,
    Muhurtha pp. 19-20; equivalent to Kalaprakasika Ch. XXIX p. 161)."""

    MRITYU = "mrityu"  # 1
    AGNI = "agni"  # 2
    RAJA = "raja"  # 4
    CHORA = "chora"  # 6
    ROGA = "roga"  # 8
    NONE = "none"  # 3, 5, 7, 0


PANCHAKA_BY_REMAINDER: dict[int, PanchakaRemainder] = {
    1: PanchakaRemainder.MRITYU,
    2: PanchakaRemainder.AGNI,
    4: PanchakaRemainder.RAJA,
    6: PanchakaRemainder.CHORA,
    8: PanchakaRemainder.ROGA,
    3: PanchakaRemainder.NONE,
    5: PanchakaRemainder.NONE,
    7: PanchakaRemainder.NONE,
    0: PanchakaRemainder.NONE,
}

#: Eighth parts of the day (1-8) by weekday, Sunday = 0.
#: Rahu Kalam: Kalaprakasika p. 176, translator's footnote (daytime only).
RAHU_KALAM_DAY_PART: tuple[int, ...] = (8, 2, 7, 5, 6, 4, 3)
#: Yamaganda: Kalaprakasika Ch. XXXIII p. 175 (text).
YAMAGANDA_DAY_PART: tuple[int, ...] = (5, 4, 3, 2, 1, 7, 6)
