"""Localized, deterministic user-facing texts: disclaimers, refusals, limitations.

These strings are application text, not model output. Machine-readable fields (evidence ids, rule
ids, source profiles, error codes, disclaimer codes) are never translated. The Hindi and Hinglish
texts were written for this module and have not been reviewed by a native-speaker editor
(`CALIBRATION_REQUIRED`: language quality is not evaluated).
"""

from __future__ import annotations

from enum import Enum

from pandit_contracts.agent import AgentErrorCode, DisclaimerCode
from pandit_contracts.llm import LLMLanguage

EN, HI, HG = LLMLanguage.EN, LLMLanguage.HI, LLMLanguage.HINGLISH

DISCLAIMERS: dict[DisclaimerCode, dict[LLMLanguage, str]] = {
    DisclaimerCode.TRADITIONAL_INTERPRETIVE: {
        EN: "Palmistry readings are traditional and interpretive; they are not scientifically "
        "established fact.",
        HI: "हस्तरेखा-पठन पारंपरिक और व्याख्यात्मक है; यह वैज्ञानिक रूप से स्थापित तथ्य नहीं है।",
        HG: "Palmistry ki readings traditional aur interpretive hoti hain; yeh scientifically "
        "proven fact nahi hain.",
    },
    DisclaimerCode.NO_GUARANTEED_OUTCOME: {
        EN: "Astrology describes traditional tendencies and periods; no outcome is guaranteed.",
        HI: "ज्योतिष पारंपरिक प्रवृत्तियों और समय-खंडों का वर्णन करता है; किसी भी परिणाम की गारंटी नहीं है।",
        HG: "Astrology traditional tendencies aur periods batati hai; kisi bhi result ki "
        "guarantee nahi hai.",
    },
    DisclaimerCode.NOT_PROFESSIONAL_ADVICE: {
        EN: "This is not a substitute for professional medical, legal or financial advice.",
        HI: "यह पेशेवर चिकित्सीय, कानूनी या वित्तीय सलाह का विकल्प नहीं है।",
        HG: "Yeh professional medical, legal ya financial advice ka substitute nahi hai.",
    },
    DisclaimerCode.EVIDENCE_NOT_PRODUCTION_READY: {
        EN: "The underlying evidence is not production-ready; treat this as a technical preview.",
        HI: "आधारभूत साक्ष्य अभी उत्पादन-योग्य नहीं है; इसे तकनीकी पूर्वावलोकन मानें।",
        HG: "Neeche ka evidence abhi production-ready nahi hai; ise technical preview samjhein.",
    },
    DisclaimerCode.PENDING_VERIFICATION: {
        EN: "This narration has not yet been independently verified against the evidence.",
        HI: "इस विवरण का साक्ष्य के विरुद्ध स्वतंत्र सत्यापन अभी नहीं हुआ है।",
        HG: "Is narration ka evidence ke against independent verification abhi nahi hua hai.",
    },
}


class Message(str, Enum):
    REFUSAL_UNSAFE = "REFUSAL_UNSAFE"
    REFUSAL_INJECTION = "REFUSAL_INJECTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    GENERIC_FAILURE = "GENERIC_FAILURE"
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    LIMITATIONS_HEADING = "LIMITATIONS_HEADING"
    LIMITATION_MISSING = "LIMITATION_MISSING"
    LIMITATION_TRIMMED = "LIMITATION_TRIMMED"


MESSAGES: dict[Message, dict[LLMLanguage, str]] = {
    Message.REFUSAL_UNSAFE: {
        EN: "I can't offer that kind of reading. I can describe what the evidence shows in "
        "traditional terms, without medical, lifespan, character or similar judgments.",
        HI: "मैं इस प्रकार का पठन नहीं दे सकता। मैं साक्ष्य जो दिखाता है उसे पारंपरिक रूप में बता "
        "सकता हूँ, बिना चिकित्सीय, आयु, चरित्र या ऐसे निर्णयों के।",
        HG: "Main is tarah ki reading nahi de sakta. Main evidence jo dikhata hai use traditional "
        "roop mein bata sakta hoon, bina medical, lifespan, character jaise judgments ke.",
    },
    Message.REFUSAL_INJECTION: {
        EN: "I can't follow instructions that change how I use the evidence or my rules. "
        "Please ask your question directly.",
        HI: "मैं ऐसे निर्देशों का पालन नहीं कर सकता जो साक्ष्य या मेरे नियमों के उपयोग को बदलते हों। "
        "कृपया अपना प्रश्न सीधे पूछें।",
        HG: "Main aise instructions follow nahi kar sakta jo evidence ya mere rules ka use "
        "badlein. "
        "Kripya apna sawal seedha poochhein.",
    },
    Message.INSUFFICIENT_EVIDENCE: {
        EN: "There isn't enough evidence available to answer this reliably.",
        HI: "इसका विश्वसनीय उत्तर देने के लिए पर्याप्त साक्ष्य उपलब्ध नहीं है।",
        HG: "Is sawal ka reliable jawab dene ke liye abhi enough evidence available nahi hai.",
    },
    Message.LLM_UNAVAILABLE: {
        EN: "The assistant is temporarily unavailable. Please try again later.",
        HI: "सहायक अभी अस्थायी रूप से उपलब्ध नहीं है। कृपया बाद में पुनः प्रयास करें।",
        HG: "Assistant abhi temporarily available nahi hai. Kripya baad mein dobara try karein.",
    },
    Message.GENERIC_FAILURE: {
        EN: "I could not produce a reliable answer this time.",
        HI: "इस बार मैं विश्वसनीय उत्तर तैयार नहीं कर सका।",
        HG: "Is baar main reliable jawab taiyar nahi kar saka.",
    },
    Message.UNSUPPORTED_LANGUAGE: {
        EN: "This language is not supported for this request.",
        HI: "इस अनुरोध के लिए यह भाषा समर्थित नहीं है।",
        HG: "Is request ke liye yeh language supported nahi hai.",
    },
    Message.LIMITATIONS_HEADING: {EN: "Limitations", HI: "सीमाएँ", HG: "Seemayein (limitations)"},
    Message.LIMITATION_MISSING: {
        EN: "Evidence of type {capability} is not available, so this answer does not cover it.",
        HI: "{capability} प्रकार का साक्ष्य उपलब्ध नहीं है, इसलिए यह उत्तर उसे शामिल नहीं करता।",
        HG: "{capability} type ka evidence available nahi hai, isliye yeh jawab use cover "
        "nahi karta.",
    },
    Message.LIMITATION_TRIMMED: {
        EN: "{count} lower-priority evidence items were left out to fit the size limit.",
        HI: "आकार सीमा के कारण {count} कम-प्राथमिकता वाले साक्ष्य छोड़ दिए गए।",
        HG: "Size limit ki wajah se {count} kam-priority evidence items chhod diye gaye.",
    },
}

_ERROR_MESSAGE: dict[AgentErrorCode, Message] = {
    AgentErrorCode.UNSAFE_REQUEST: Message.REFUSAL_UNSAFE,
    AgentErrorCode.PROMPT_INJECTION: Message.REFUSAL_INJECTION,
    AgentErrorCode.INSUFFICIENT_EVIDENCE: Message.INSUFFICIENT_EVIDENCE,
    AgentErrorCode.MISSING_EVIDENCE: Message.INSUFFICIENT_EVIDENCE,
    AgentErrorCode.LLM_UNAVAILABLE: Message.LLM_UNAVAILABLE,
    AgentErrorCode.LLM_TIMEOUT: Message.LLM_UNAVAILABLE,
    AgentErrorCode.UNSUPPORTED_LANGUAGE: Message.UNSUPPORTED_LANGUAGE,
}


def text(message: Message, language: LLMLanguage, **fields: object) -> str:
    return MESSAGES[message][language].format(**fields)


def user_message_for(code: AgentErrorCode, language: LLMLanguage) -> str:
    return text(_ERROR_MESSAGE.get(code, Message.GENERIC_FAILURE), language)


def disclaimer_text(code: DisclaimerCode, language: LLMLanguage) -> str:
    return DISCLAIMERS[code][language]
