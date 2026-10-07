"""
antar_engine/lang_registry.py — the single registry of languages Antar serves.

Codes (what the FE sends / reads from GET /api/v1/me/language -> `available`):

    en        English
    es        Español   (Latin American)
    pt        Português (Brazilian)
    fr        Français
    hi        हिन्दी     — Hindi in DEVANAGARI script
    hinglish  Hinglish  — Hindi in ROMAN script, code-mixed with English

`hi` and `hinglish` are different products. `hi` is Devanagari only; a reply to a
`hi` reader that is English or Roman-script is a defect, never a graceful fallback.
(Before this module a few places treated "hi" as an alias of Hinglish — the WhatsApp
saved-language reader, the follow-up chip tables, the Meta-template picker. Those
now go through here.)

Unknown / unsupported codes resolve to English EXPLICITLY (and are logged) — never
to Hinglish or to another language that merely shares a prefix ("hindi" and "his"
do not start-with-match "hi").
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Order is the order the FE shows them in the picker.
SUPPORTED_LANGUAGES = ("en", "hi", "hinglish", "es", "pt", "fr")

# Native names for the picker (additive field on GET /me/language).
LANGUAGE_LABELS = {
    "en": "English",
    "hi": "हिन्दी",
    "hinglish": "Hinglish",
    "es": "Español",
    "pt": "Português",
    "fr": "Français",
}

# Languages whose surface text is produced by the response-time translator
# (antar_engine.translation_middleware). hinglish is NOT here: it is written
# directly by the model on the surfaces that support it (Ask) and is not translated.
TRANSLATED_LANGUAGES = ("es", "pt", "fr", "hi")

# Languages the WhatsApp conversation has strings for.
WA_LANGUAGES = ("en", "es", "pt", "hinglish", "hi")

# Accepted spellings -> canonical code. Script subtags disambiguate Hindi:
# "hi-Latn" is Roman-script Hindi (Hinglish), "hi-Deva"/"hi-IN" is Devanagari.
_ALIASES = {
    "hindi": "hi", "hin": "hi", "hi-in": "hi", "hi_in": "hi", "hi-deva": "hi",
    "hi-latn": "hinglish", "hi_latn": "hinglish", "hin-latn": "hinglish",
    "hinglish": "hinglish", "hing": "hinglish",
    "english": "en", "spanish": "es", "portuguese": "pt", "french": "fr",
}


def normalize_language(raw, default: str = "en", log: bool = True) -> str:
    """Canonical language code for any client-supplied value.

    * "pt-BR" -> "pt", "es_CO" -> "es", "HI" -> "hi", "hi-Latn" -> "hinglish".
    * Empty/None -> `default`.
    * Unknown ("xx", "klingon", "his") -> "en", logged. NEVER a guess.
    """
    s = str(raw or "").strip().lower().replace("_", "-")
    if not s:
        return default
    if s in _ALIASES:
        return _ALIASES[s]
    if s in SUPPORTED_LANGUAGES:
        return s
    base = s.split("-")[0]
    if base in SUPPORTED_LANGUAGES:
        return base
    if log:
        logger.warning("[lang] unsupported language %r -> falling back to en", raw)
    return "en"


def is_supported(raw) -> bool:
    s = str(raw or "").strip().lower().replace("_", "-")
    return s in SUPPORTED_LANGUAGES or s in _ALIASES or s.split("-")[0] in SUPPORTED_LANGUAGES


# ── Devanagari script measurement ────────────────────────────────────────────

# Letters (not combining marks, digits or the danda): independent vowels, consonants,
# the nukta consonants (U+0958-095F), the extra vowels / letters (U+0960-0961,
# U+0972-097F).
_DEV_LETTER = re.compile(r"[ऄ-हक़-ॡॲ-ॿ]")
_LATIN_LETTER = re.compile(r"[A-Za-zÀ-ɏ]")


def script_counts(text: str) -> tuple:
    """(devanagari_letters, latin_letters) in `text`."""
    t = text or ""
    return len(_DEV_LETTER.findall(t)), len(_LATIN_LETTER.findall(t))


def devanagari_ratio(text: str) -> float:
    """Devanagari letters / (Devanagari + Latin letters). 1.0 for a string with no
    letters at all (digits, dates, punctuation carry no language)."""
    dev, lat = script_counts(text)
    total = dev + lat
    return 1.0 if total == 0 else dev / total


def is_mostly_devanagari(text: str, min_ratio: float = 0.7) -> bool:
    """True when `text` is acceptable Hindi output.

    Proper nouns and loanwords stay Latin on purpose ("Antar", "Rahu"…), so the
    bar is a RATIO, not "zero Latin". 0.7 passes a Hindi sentence carrying a couple
    of Latin names and fails English, Roman-script Hinglish, and half-translated text.
    """
    return devanagari_ratio(text) >= min_ratio


def has_devanagari(text: str) -> bool:
    return bool(_DEV_LETTER.search(text or ""))


# A string is "prose" (worth language-checking) when it has real words — not an
# enum ("explore"), an id, a number or a date.
def is_prose(text: str, min_latin_letters: int = 6) -> bool:
    if not isinstance(text, str):
        return False
    dev, lat = script_counts(text)
    if dev:
        return True
    return lat >= min_latin_letters and len(text.split()) >= 2


def detect_devanagari_language(text: str, min_letters: int = 1,
                               min_share: float = 0.4) -> Optional[str]:
    """'hi' when `text` is written in Devanagari, else None.

    The script itself is unmistakable, so unlike the Roman-script detectors this
    needs no word list. Guards against false positives:
      * a lone Devanagari name inside an English sentence ("my friend राम asked")
        has a Devanagari share well under `min_share` -> None;
      * needs at least `min_letters` Devanagari letters, so a stray combining mark -> None.
    A short Devanagari-only message ("हाँ", "राम", "मदद") IS Hindi.
    Marathi/Nepali/Sanskrit are Devanagari too; Antar has no such products, so they
    are answered in Hindi rather than in English.
    """
    dev, lat = script_counts(text)
    if dev < min_letters:
        return None
    return "hi" if dev / (dev + lat) >= min_share else None


# ── Per-language fallbacks ───────────────────────────────────────────────────
# Used ONLY when generated text is rejected by the language guard and could not be
# repaired. They are deliberately generic and honest — no astrology claims — so a
# fallback can never contradict the chart.

FALLBACKS = {
    "hi": {
        "read": "अभी आपके प्रश्न का पूरा उत्तर तैयार नहीं हो पाया। कृपया थोड़ी देर बाद दोबारा पूछिए।",
        "next": "थोड़ी देर बाद अपना प्रश्न फिर से भेजिए।",
        "why": "अभी इसका कारण तैयार नहीं हो पाया। कृपया दोबारा पूछिए।",
        "generic": "यह जानकारी अभी हिन्दी में उपलब्ध नहीं है। कृपया थोड़ी देर बाद देखिए।",
    },
}


def fallback_text(key: str, language: str) -> str:
    """Per-language fallback line. Languages without an entry get the English one,
    explicitly (the table below), never another language's."""
    lang = normalize_language(language, log=False)
    table = FALLBACKS.get(lang) or _EN_FALLBACKS
    return table.get(key) or table["generic"]


_EN_FALLBACKS = {
    "read": "I couldn't finish this answer just now. Please ask again in a moment.",
    "next": "Please send your question again in a moment.",
    "why": "I couldn't put the reason together just now. Please ask again.",
    "generic": "This isn't available right now. Please check back in a moment.",
}
