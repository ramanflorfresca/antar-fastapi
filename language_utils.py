"""
Antar Language Utilities
"""

VALID_LANGUAGES = {"en", "hi", "hinglish", "es", "pt"}
VALID_REMEDY_STYLES = {"traditional", "secular"}

_LANGUAGE_BLOCKS = {
    "hi": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in Hindi using Devanagari script.\n"
        "Use formal, respectful Hindi. Do not mix in English words.\n"
        "All numbers, dates, percentages in standard numerals (87%, April 15).\n"
        "Never translate: Antar, Seeker, Navigator.\n"
        "No Sanskrit astrological terms — use plain Hindi.\n\n"
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
        "Never revert to English mid-sentence.\n"
        "Numbers/dates in standard format. Never translate: Antar, Seeker, Navigator.\n\n"
    ),
    "pt": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in Brazilian Portuguese.\n"
        "Professional, clear. Not European Portuguese.\n"
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
