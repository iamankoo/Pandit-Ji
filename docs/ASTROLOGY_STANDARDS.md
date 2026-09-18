# Pandit Ji Astrology Standards

Status: **LOCKED canonical location** — `docs/ASTROLOGY_STANDARDS.md` is the single, authoritative document for calculation standards, Vedic defaults, ayanamsa, zodiac, house systems, ephemeris configuration, astronomical calculation requirements, astrology methodology separation, interpretation standards, reproducibility, uncertainty, and versioning. There is no separate `docs/calculation-standards.md` — any earlier reference to that filename referred to this document and should be treated as resolved in favor of this one.

## Core rule
**Facts flow one direction; AI only narrates.**

The AI must never independently calculate planetary positions, houses, ascendant, nakshatra/pada, divisional charts, dashas, transits, yogas/doshas, Panchang timings, or compatibility scores.

## Default Vedic profile
- Zodiac: Sidereal
- Ayanamsa: Lahiri
- House baseline: Vedic whole-sign
- Degree-level planetary positions
- Historical timezone/DST handling
- Explicit versioned calculation configuration

Alternate systems must be selected explicitly.

## Supported systems
Vedic/Jyotish, Western/Tropical, KP, Lal Kitab, Nadi, Horary, Numerology, Chinese astrology, Tarot, Vastu/Feng Shui, Palmistry.

Each system has its own methodology. Systems must not be silently mixed.

## Interpretation
Every major conclusion should be traceable to:
1. calculation facts
2. applicable rule/source
3. relevant period
4. supporting factors
5. conflicting factors
6. evidence/confidence state

Clearly separate calculated fact, traditional interpretation, AI explanation, and user-provided information.

## Uncertainty
Approximate birth time must remain approximate. Do not silently treat it as exact.

No scientifically unsupported guarantee of future prediction.

## Reproducibility
Store engine version, ephemeris/version, ayanamsa, house system, timezone database, coordinates and birth inputs with calculation results.

## Health
Astrological health content is traditional/educational only, never diagnosis, prognosis, treatment or emergency advice.

## Remedies
Gemstones, mantras, puja, fasting, donations and rituals are traditional/spiritual practices, not scientifically established treatments.

## Palmistry
Image quality, hand side, visible structures and uncertainty must be separated from interpretation. No medical diagnosis from palm images.

## Versioning
Changes to calculation standards require versioning, changelog, regression tests and explicit approval.
