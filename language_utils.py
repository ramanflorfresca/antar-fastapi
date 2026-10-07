"""
Antar Language Utilities
"""

# [hi 2026-10-07] single registry — antar_engine/lang_registry.py
from antar_engine.lang_registry import SUPPORTED_LANGUAGES as _REGISTRY
VALID_LANGUAGES = set(_REGISTRY)
VALID_REMEDY_STYLES = {"traditional", "secular"}

_LANGUAGE_BLOCKS = {
    "hi": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in Hindi using Devanagari script (हिन्दी).\n"
        "NEVER write Hindi in Roman letters (that is Hinglish, a different language setting) and never an English sentence.\n"
        "Address the reader respectfully as 'आप' (आपका, आपकी, आपको) — never 'तू' or 'तुम'.\n"
        "Use plain, warm Hindi. Do not mix in English words except proper nouns.\n"
        "All numbers, dates, percentages in standard numerals (87%, 15 अप्रैल).\n"
        "Never translate: Antar. No Sanskrit astrological jargon — use plain Hindi.\n\n"
    ),
    "hinglish": (
        "LANGUAGE INSTRUCTION: Respond in Hinglish — casual Hindi-English mix in Roman script.\n"
        "Example: 'Aapka career energy abhi peak pe hai. Next 3 weeks mein bold move karo.'\n"
        "Mix naturally. Numbers/dates in standard format.\n"
        "Never translate: Antar, Seeker, Navigator.\n\n"
    ),
    "es": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in Latin American Spanish.\n"
        "Professional, clear. No European Spanish (no vosotros).\n"
        "Compose natively in Spanish — never translate English phrasing word-for-word.\n"
        "Never revert to English mid-sentence.\n"
        "Numbers/dates in standard format. Never translate: Antar, Seeker, Navigator.\n\n"
    ),
    "pt": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in Brazilian Portuguese.\n"
        "Professional, clear. Not European Portuguese.\n"
        "Compose natively in Portuguese — never translate English phrasing word-for-word.\n"
        "Never revert to English mid-sentence.\n"
        "Numbers/dates in standard format. Never translate: Antar, Seeker, Navigator.\n\n"
    ),
    "fr": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in French (France).\n"
        "Warm, clear, modern French — no anglicisms, no literal calques.\n"
        "Compose natively in French — never translate English phrasing word-for-word.\n"
        "Never revert to English mid-sentence.\n"
        "Numbers/dates in standard format. Never translate: Antar, Seeker, Navigator.\n\n"
    ),
}

def build_language_instruction(language="en"):
    if not language or language == "en":
        return ""
    return _LANGUAGE_BLOCKS.get(language, "")

def resolve_language(request_body=None, chart_data=None):
    if request_body:
        lang = request_body.get("language")
        if lang and lang in VALID_LANGUAGES:
            return lang
    if chart_data:
        stored = chart_data.get("language")
        if stored and stored in VALID_LANGUAGES:
            return stored
    return "en"

def resolve_language_from_query(query_params, chart_data=None):
    lang = None
    if query_params:
        lang = query_params.get("language") if hasattr(query_params, 'get') else None
    if lang and lang in VALID_LANGUAGES:
        return lang
    if chart_data:
        stored = chart_data.get("language")
        if stored and stored in VALID_LANGUAGES:
            return stored
    return "en"
