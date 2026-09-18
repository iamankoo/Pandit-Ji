# Pandit Ji — Locked Feature Specification

Project: Pandit Ji
Product: Self-hosted AI Astrology Platform / AI Astrologer
Status: LOCKED BASELINE
Version: 1.0

## 1. Product Vision

Pandit Ji is a self-hosted AI astrology platform designed to combine a deterministic astrology calculation engine, a comprehensive Vedic/Western astrology knowledge and rule system, and an AI agent capable of understanding natural-language questions and producing personalized astrological interpretations.

The locked baseline feature set combines the major capabilities identified for AstroSage and KundliGPT. Pandit Ji is intended to go beyond a generic AI horoscope chatbot by separating:

- Astronomical/astrological calculations
- Astrology rules and knowledge
- AI reasoning and conversation
- Evidence/consistency verification
- Personalization and memory

### Accuracy principle

- Mathematical/chart calculations must be deterministic, reproducible, and extensively tested.
- The AI must never invent planetary positions, dashas, houses, yogas, or other chart facts.
- Interpretations and future-oriented readings must be presented as astrological interpretations, not scientifically guaranteed outcomes.
- The system should record the astrological factors supporting an interpretation and, where applicable, conflicting factors.

## 2. Core AI Features

### AI Astrologer

- Natural-language astrology chat
- Personalized chart-aware answers
- Follow-up questions
- Conversation context
- Personalized interpretations
- Multi-turn conversations
- Domain-specific astrology analysis
- Timing-oriented questions
- Explainable astrological reasoning
- Remedies and guidance
- Chart-based responses instead of generic horoscope responses

### Specialist AI Agents / Modes

- General astrology
- Love & relationships
- Marriage
- Career
- Wealth/finance
- Business
- Daily guidance
- Education
- Travel/foreign opportunities
- Life analysis
- Compatibility
- Transit analysis
- Dasha analysis

### AI Voice

- Voice astrology conversations
- Speech-to-text
- Text-to-speech
- Multilingual voice interaction
- Voice follow-up conversations

## 3. Birth Profile

- Date of birth
- Exact time of birth
- Birthplace
- Latitude
- Longitude
- Time zone
- Historical timezone handling
- DST handling where applicable
- Multiple saved birth profiles
- User profile management
- Family/partner profiles
- Chart profile selection

## 4. Birth Chart / Kundli

### Core Charts

- Janam Kundli
- Lagna / D1 chart
- Chandra/Moon chart
- Navamsa / D9
- Divisional charts
- North Indian chart style
- South Indian chart style
- Planetary chart
- Chalit chart
- Shodashvarga
- Ashtakvarga

### Planetary Information

- Planetary positions
- Exact planetary degrees
- Rashi/sign
- Nakshatra
- Pada
- House placement
- House lordship
- Planetary dignity
- Exaltation
- Debilitation
- Retrograde status
- Combustion
- Planetary speed
- Relevant planetary relationships/aspects

### Calculation Configuration

- Sidereal/Vedic zodiac
- Lahiri ayanamsa
- Ayanamsa configuration
- Tropical/Western zodiac
- House-system configuration
- Placidus houses for Western mode
- Degree-level calculations
- Swiss Ephemeris integration
- Reproducible calculation settings

## 5. Vedic Astrology

- Rashis
- Bhavas/Houses
- Grahas
- Nakshatras
- Nakshatra Padas
- Planetary aspects
- Planetary relationships
- Yogas
- Doshas
- Planetary dignity
- House lord analysis
- Functional benefic/malefic analysis
- Strength analysis
- Shodashvarga
- Ashtakvarga
- Vedic timing systems
- Vedic predictive analysis

## 6. Dasha System

- Vimshottari Dasha
- Mahadasha
- Antardasha
- Pratyantar Dasha
- Full Dasha timeline
- Current running Dasha
- Future Dasha periods
- Dasha transition dates
- Dasha-based interpretation
- Dasha timing analysis
- Long-term life timeline

## 7. Transits / Gochar

- Current planetary transits
- Historical transits
- Future transits
- Transit-to-natal analysis
- Jupiter transit
- Saturn transit
- Rahu transit
- Ketu transit
- Other planetary transits
- Transit timing
- Sade Sati analysis
- Transit-based predictions
- Transit alerts/readings

## 8. Yogas and Doshas

- Yoga detection
- Yoga interpretation
- Relevant combinations
- Mangal Dosha
- Nadi Dosha
- Bhakoot Dosha
- Kaal Sarp Dosha
- Saturn-related influences
- Other supported doshas
- Dosha severity/context analysis
- Supporting chart evidence
- Remedial guidance

## 9. Western Astrology

- Tropical zodiac
- Western natal chart
- Placidus houses
- Western planetary aspects
- Western chart interpretation
- Vedic vs Western comparison
- Dual-system analysis

## 10. KP / Lal Kitab / Nadi / Other Systems

The product baseline includes support for the broader astrology ecosystem represented by AstroSage, subject to implementation and validation of each system:

- KP Astrology
- KP Horary
- Lal Kitab
- Nadi Astrology
- Horary Astrology
- Chinese Astrology
- Feng Shui-related guidance
- Vastu-related guidance
- Tarot
- Numerology

## 11. Life Analysis

Pandit Ji must support chart-based analysis across broad life domains, including:

- Birth / early life
- Childhood
- Personality
- Personal life
- Family
- Parents
- Siblings
- Education
- School
- College
- Subjects
- Higher education
- Career
- Job
- Corporate life
- Business
- Startup
- Entrepreneurship
- Wealth
- Finance
- Income
- Investments-related astrological interpretation
- Love
- Girlfriend/boyfriend/relationships
- Marriage
- Spouse
- Family life
- Children
- Foreign travel
- Foreign education
- Foreign settlement
- Journeys/travel
- Major life transitions
- Spirituality
- General life patterns

Health-related astrology may be supported as an astrological interpretation, but must not be represented as medical diagnosis or medical advice.

## 12. Career and Education

### Career

- Career analysis
- Job analysis
- Job-change timing
- Career direction
- Corporate-life analysis
- Business vs job
- Entrepreneurship
- Startup/business analysis
- Professional strengths
- Career periods
- Dasha-based career timing
- Transit-based career timing

### Education

- School education
- College education
- Higher education
- Subject suitability
- Academic patterns
- Competitive examinations
- Higher studies
- Foreign education
- Education timing

## 13. Love, Relationship and Marriage

- Love analysis
- Relationship analysis
- Relationship timing
- Marriage analysis
- Marriage timing
- Spouse-related analysis
- Compatibility
- Relationship strengths/challenges
- Kundli matching
- Guna Milan / Ashtakoot
- 36-point compatibility system
- Varna
- Vashya
- Tara
- Yoni
- Graha Maitri
- Gana
- Bhakoot
- Nadi
- Dosha detection
- AI relationship interpretation
- AI conversation about compatibility

## 14. Kundli Matching

- Two-person matching
- Multiple saved profiles
- Ashtakoot/Guna Milan
- 36-point score
- Individual category scores
- Compatibility visualization
- Nadi analysis
- Bhakoot analysis
- Other compatibility factors
- Dosha analysis
- AI-generated relationship interpretation
- Follow-up questions about the match

## 15. Panchang

- Daily Panchang
- Tithi
- Vara
- Nakshatra
- Yoga
- Karana
- Hora
- Choghadiya
- Rahu Kaal
- Gowri Panchang
- Panchak
- Bhadra
- Tara Balam
- Chandra Balam
- Sunrise/sunset-related calculations
- Moon-related calculations
- Location-specific Panchang
- Date-specific Panchang

## 16. Muhurta

- Marriage/Vivah Muhurat
- Griha Pravesh
- Housewarming
- Mundan Muhurat
- Other Shubh Muhurat
- Auspicious timings
- Inauspicious timings
- Date/time selection
- Location-specific Muhurta

## 17. Horoscope

- Daily horoscope
- Weekly horoscope
- Monthly horoscope
- Yearly horoscope
- Love horoscope
- Education horoscope
- Transit-based horoscope
- Zodiac-wise horoscope
- Lucky numbers
- Lucky colours
- Remedies
- Auspicious timings
- Inauspicious timings

## 18. Numerology

- Numerology calculator
- Root/Moolank
- Fortune/Bhagyank
- Lucky numbers
- Name-related numerology
- Numerology reports
- AI numerology interpretation
- Multilingual numerology

## 19. Remedies and Guidance

- Astrological remedies
- Dosha remedies
- Planetary remedies
- Gemstone recommendations
- Mantra-related guidance
- Puja-related guidance
- Traditional remedial suggestions
- Lal Kitab remedies where applicable
- Personalized remedies based on chart factors

Remedies must be presented as traditional astrological practices, not as guaranteed medical, financial, or other real-world outcomes.

## 20. Specialized Reports

The product baseline includes report-generation capabilities for:

- Life Insights
- Complete birth-chart report
- Dasha report
- Love & Marriage report
- Career report
- Wealth/finance report
- Education report
- Mangal Dosha report
- Saturn/Sade Sati report
- Videsh Yoga / foreign opportunities report
- Foreign education report
- Foreign settlement report
- Gemstone report
- Transit report
- Yoga report
- Planetary influence reports
- Annual/Varshphal report
- Compatibility report
- Numerology report
- Targeted question reports
- Long-term life timeline

## 21. Annual / Varshphal Analysis

- Annual horoscope
- Varshphal
- Year-specific analysis
- Yearly planetary influences
- Yearly career analysis
- Yearly relationship analysis
- Yearly finance analysis
- Yearly education analysis
- Yearly travel analysis
- Important periods of the year

## 22. Human Astrology Ecosystem

The combined AstroSage feature baseline includes support for:

- Live astrologer chat
- Live astrologer calls
- Vedic astrologers
- KP astrologers
- Lal Kitab astrologers
- Nadi astrologers
- Numerologists
- Tarot readers
- Vastu experts
- Marriage/compatibility experts
- Horary experts
- Multilingual consultations

These can be implemented as a future marketplace/consultation module if required.

## 23. Astrology Content Ecosystem

- Astrology articles
- Educational astrology content
- Festivals
- Hindu calendar
- Astrology learning resources
- Zodiac content
- Transit content
- Remedial content
- Astrology guides
- Expert content

## 24. AI Reasoning Architecture

The AI must operate on structured astrology data rather than hallucinating calculations.

Required pipeline:

```
User Question
    ↓
Intent Detection
    ↓
Relevant Astrology Domain Selection
    ↓
Birth Profile Retrieval
    ↓
Deterministic Calculation Engine
    ↓
Chart / Dasha / Transit Data
    ↓
Astrology Rule Engine
    ↓
Evidence Collection
    ↓
Contradiction / Conflict Analysis
    ↓
AI Reasoning
    ↓
Verification Layer
    ↓
Personalized Response
```

## 25. Explainable Astrology

Every substantial interpretation should be able to expose:

- What chart factors were considered
- Which houses were considered
- Which planets were considered
- Which dashas were considered
- Which transits were considered
- Which yogas/doshas were detected
- Which astrology rules were triggered
- Supporting factors
- Contradicting factors
- Relevant time periods
- Calculation configuration

## 26. Verification and Evaluation

- Deterministic calculation tests
- Cross-check against trusted ephemeris outputs
- Chart reproducibility tests
- Rule-engine unit tests
- Regression tests
- Dasha calculation tests
- Transit calculation tests
- Compatibility calculation tests
- Panchang calculation tests
- AI hallucination detection
- Unsupported-claim detection
- Contradiction detection
- Historical backtesting framework
- Prediction/outcome data collection
- Accuracy benchmarking
- Human-expert evaluation

Important: The system must not claim 100% real-world future prediction accuracy unless such performance is independently demonstrated by appropriate empirical testing. Mathematical calculation accuracy and predictive/interpretive accuracy are separate metrics.

## 27. Memory and Personalization

- User profile memory
- Birth-profile memory
- Saved family/partner charts
- Conversation memory
- User preferences
- Previously discussed topics
- Saved reports
- Personalized explanations
- User feedback
- Correction history
- Optional long-term astrology journal

## 28. Multilingual Support

Baseline should support:

- English
- Hindi
- Hinglish

The architecture should be extensible to additional Indian and international languages.

Target conversational experience:

- Natural Hindi
- Natural Hinglish
- Natural English
- Language-aware terminology
- Astrology terms preserved appropriately across languages

## 29. User Experience

- Modern professional UI
- Interactive birth chart
- Interactive planetary details
- AI chat
- Voice chat
- Dashboard
- Saved profiles
- Saved reports
- Timeline views
- Dasha timeline visualization
- Transit timeline
- Compatibility dashboard
- Panchang dashboard
- Personalized home screen
- Fast responsive experience
- Mobile-first design
- Web support

## 30. Backend / Platform Requirements

Suggested foundation:

- Python
- FastAPI
- PostgreSQL
- pgvector
- Redis
- SQLAlchemy
- Docker
- Docker Compose
- Flutter for mobile
- React/Next.js for web where appropriate

The exact implementation stack can evolve, but the architecture must preserve the separation between calculation, rules, AI, memory, and presentation.

## 31. Privacy and Security

- Secure authentication
- Encrypted sensitive user data
- Secure birth-data storage
- Data deletion
- Privacy controls
- Minimal data collection
- Secure API design
- Access control
- Audit logging
- No unnecessary third-party sharing
- Self-hosted AI option
- Clear disclosure of external services when used

## 32. Product Principles — LOCKED

- Pandit Ji is an AI astrology platform, not merely an AI horoscope chatbot.
- Astrology calculations must be deterministic.
- AI must not invent chart facts.
- The combined AstroSage + KundliGPT feature set is the locked baseline.
- The system should support comprehensive life-domain analysis.
- Vedic astrology is the primary foundation.
- Western astrology and additional systems are supported as modules.
- AI should explain which astrological factors support an interpretation.
- Predictions must not be presented as scientifically guaranteed facts.
- The architecture should support self-hosted AI and minimize dependency on external AI APIs.
- Every major subsystem must be testable independently.
- New features can be added, but the locked baseline must not be removed without an explicit product decision.

## 33. Future Expansion

Potential future modules, not required for the initial baseline:

- Palm reading
- Face reading
- Image-based palm analysis
- AI document/report generation
- Personalized daily notifications
- Event/period alerts
- Advanced predictive timeline
- Astrological journaling
- Expert marketplace
- Community
- Astrology education/courses
- Research/backtesting laboratory
- Personal astrology API
- Developer SDK
