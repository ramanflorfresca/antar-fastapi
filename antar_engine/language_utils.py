"""
Antar Language Utilities
========================
Single source of truth for language instruction injection.
Drop this file alongside main.py (or in antar_engine/).

Import:
    from language_utils import build_language_instruction, resolve_language

Author: Antar Engine Team
Date: April 2026
"""


# ═══════════════════════════════════════════════════════════════════
# VALID LANGUAGES
# ═══════════════════════════════════════════════════════════════════

VALID_LANGUAGES = {"en", "hi", "hinglish", "es", "pt"}
VALID_REMEDY_STYLES = {"traditional", "secular"}


# ═══════════════════════════════════════════════════════════════════
# LANGUAGE INSTRUCTION BLOCK
# ═══════════════════════════════════════════════════════════════════

_LANGUAGE_BLOCKS = {
    "hi": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in Hindi using Devanagari script (हिन्दी).\n"
        "Use formal, respectful Hindi. Do not mix in English words or phrases.\n"
        "All numbers, dates, and percentages must remain in standard numerals (e.g., 87%, April 15).\n"
        "Never translate proper nouns: Antar, Seeker, Navigator stay in English.\n"
        "Do not use Sanskrit astrological terms — use plain Hindi equivalents.\n\n"
    ),
    "hinglish": (
        "LANGUAGE INSTRUCTION: Respond in Hinglish — a casual mix of Hindi and English, written in Roman script.\n"
        "This is how urban Indians text. Example tone: 'Aapka career energy abhi peak pe hai. "
        "Next 3 weeks mein ek bold move karo — regret nahi hoga.'\n"
        "Mix naturally. Don't force Hindi where English flows better, and vice versa.\n"
        "All numbers, dates, and percentages in standard numerals.\n"
        "Never translate proper nouns: Antar, Seeker, Navigator stay as-is.\n\n"
    ),
    "es": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in Latin American Spanish (español latinoamericano).\n"
        "Use professional, clear Spanish — not European Spanish (no 'vosotros').\n"
        "If a concept has no direct Spanish translation, use the most common professional "
        "equivalent in Latin American business Spanish. Never revert to English mid-sentence.\n"
        "All numbers, dates, and percentages in standard numerals.\n"
        "Never translate proper nouns: Antar, Seeker, Navigator stay in English.\n\n"
    ),
    "pt": (
        "LANGUAGE INSTRUCTION: Respond ENTIRELY in Brazilian Portuguese (português brasileiro).\n"
        "Use professional, clear Brazilian Portuguese — not European Portuguese.\n"
        "If a concept has no direct Portuguese translation, use the most common professional "
        "equivalent in Brazilian business Portuguese. Never revert to English mid-sentence.\n"
        "All numbers, dates, and percentages in standard numerals.\n"
        "Never translate proper nouns: Antar, Seeker, Navigator stay in English.\n\n"
    ),
}


def build_language_instruction(language: str = "en") -> str:
    """
    Returns the language instruction block to prepend to any Claude system prompt.

    For 'en', returns empty string (no instruction needed — English is default).
    For all others, returns a multi-line instruction block that goes BEFORE
    the main system prompt. Claude reads top-down.

    Usage:
        lang_block = build_language_instruction("hi")
        final_prompt = lang_block + existing_system_prompt
    """
    if not language or language == "en":
        return ""
    return _LANGUAGE_BLOCKS.get(language, "")


def resolve_language(request_body: dict = None, chart_data: dict = None) -> str:
    """
    Resolve language with strict priority:
      1. Explicit 'language' in request body (frontend sends this per-call)
      2. Stored 'language' in chart row from Supabase (persisted preference)
      3. Default: 'en'

    Args:
        request_body: The parsed request JSON (may contain 'language' key)
        chart_data:   The chart row dict from Supabase (may contain 'language' key)

    Returns:
        One of: 'en', 'hi', 'hinglish', 'es', 'pt'
    """
    # Priority 1: Request body
    if request_body:
        lang = request_body.get("language")
        if lang and lang in VALID_LANGUAGES:
            return lang

    # Priority 2: Stored preference
    if chart_data:
        stored = chart_data.get("language")
        if stored and stored in VALID_LANGUAGES:
            return stored

    # Priority 3: Default
    return "en"


def resolve_language_from_query(query_params, chart_data: dict = None) -> str:
    """
    Same as resolve_language but reads from query params (for GET endpoints).

    Usage:
        language = resolve_language_from_query(request.query_params, chart_row)
    """
    lang = None
    if query_params:
        lang = query_params.get("language")
    if lang and lang in VALID_LANGUAGES:
        return lang

    if chart_data:
        stored = chart_data.get("language")
        if stored and stored in VALID_LANGUAGES:
            return stored

    return "en"
