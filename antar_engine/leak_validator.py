"""
antar_engine/leak_validator.py — Class B post-generation safety net.

Scans user-facing prose for jargon tokens (planet, sign, house, Sanskrit deity
term, engine name, CAPS strategy codename). If found, returns a localized
fallback — NEVER word-strips, which would leave broken sentences (the bug the
QA caught on /ask: "However, the is missing —").

Use via `validate_field(text, field_key, language, fallback=None)` at the
response boundary. Safe to call repeatedly; passes clean text through.
"""
import re
from typing import Optional

# Planet names (EN + ES). ES is the same lexeme except for "Sol" / "Luna".
_PLANETS_RE = re.compile(
    r"\b(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu|"
    r"Sol|Luna|Marte|Mercurio|J[uú]piter|Venus|Saturno)\b"
)

# Sign names — only flag when used as astrological label (capitalized standalone).
# Avoid false positives on the English word "may" by limiting to capitalized.
_SIGN_NAMES = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    "Tauro", "G\u00e9minis", "C\u00e1ncer", "Virgo", "Libra",
    "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis",
)
_SIGNS_RE = re.compile(r"\b(?:" + "|".join(_SIGN_NAMES) + r")\b")

# House refs — "Nth house", "house N", "(house N)", "in N house".
_HOUSE_RE = re.compile(
    r"\b\d+(?:st|nd|rd|th)?\s+house\b|\(?house\s+\d+\)?|\b\d+H\b",
    re.IGNORECASE,
)

# Sanskrit deity / system terms (the brief's explicit ban; bija mantras are NOT
# scanned here — those are mantra text, not prose).
_SANSKRIT_RE = re.compile(
    r"\b(?:Atma|Manas|Buddhi|Vak|Shakti|Dharma|Guru|Karma|Tapas|Kama|Maya|"
    r"Moksha|Ahamkara|dasha|mahadasha|antardasha|pratyantar|sookshma|vimsottari|"
    r"vimshottari|ashtottari|jaimini|lal\s*kitab|nakshatra|lagna|rashi|tithi|"
    r"karana|panchanga|panchang|varshphal|graha|bhava|karaka|atmakaraka|"
    r"amatyakaraka|darakaraka|gochar|sade\s*sati|ithasala|muhurta|muhurat|"
    r"navamsa|karakamsa|upapada|paada)\b",
    re.IGNORECASE,
)

# Engine / system name in CAPS or mixed case
_ENGINE_RE = re.compile(
    r"\b(?:VIMSOTTARI|VIMSHOTTARI|JAIMINI|LAL\s*KITAB|ASHTOTTARI|TRANSIT\s+ENGINE)\b",
    re.IGNORECASE,
)

# CAPS strategy codename — "THE TURNAROUND ARCHITECT", "STRATEGY: X", "STAR: X"
_CODENAME_RE = re.compile(
    r"\b(?:THE\s+[A-Z]{3,}(?:\s+[A-Z]{3,}){0,3}|STRATEGY\s*:\s*[A-Z]+|STAR\s*:\s*[A-Z]+|AUTHORITY\s+ENGINE|CAPITAL\s+RUNWAY|ALLIANCE\s+SYNC)\b"
)


def has_leak(text: str) -> Optional[str]:
    """Return rule name of first banned token found, or None if clean."""
    if not isinstance(text, str) or not text.strip():
        return None
    for name, rx in (
        ("planet",   _PLANETS_RE),
        ("sign",     _SIGNS_RE),
        ("house",    _HOUSE_RE),
        ("sanskrit", _SANSKRIT_RE),
        ("engine",   _ENGINE_RE),
        ("codename", _CODENAME_RE),
    ):
        if rx.search(text):
            return name
    return None


# Localized safe fallbacks keyed by field kind. Sentences are complete on their
# own and never reference a planet/sign/house.
_FALLBACKS = {
    "en": {
        "diagnosis":       "Your current life chapter is active and asks for steady support right now.",
        "remedy_why":      "This pattern asks for steady attention this week.",
        "practice_why":    "This energy is the focus right now. A small, focused action can amplify it.",
        "mantra_why":      "This practice re-attunes your energy field to a steadier rhythm.",
        "duration_reason": "This cycle length is enough to shift the pattern through sustained, consistent practice.",
        "supporting_why":  "This energy supports the primary practice this week.",
        "primary_action":  "Spend a few minutes in stillness this morning. Take one small, deliberate action this week.",
        "generic":         "This pattern asks for steady attention right now.",
    },
    "es": {
        "diagnosis":       "Tu capítulo de vida actual está activo y pide apoyo constante ahora mismo.",
        "remedy_why":      "Este patrón pide atención constante esta semana.",
        "practice_why":    "Esta energía es el foco ahora. Una pequeña acción enfocada puede amplificarla.",
        "mantra_why":      "Esta práctica re-sincroniza tu campo de energía con un ritmo más firme.",
        "duration_reason": "La duración del ciclo basta para mover el patrón con práctica constante.",
        "supporting_why":  "Esta energía apoya la práctica principal esta semana.",
        "primary_action":  "Pasa unos minutos en silencio esta mañana. Da un paso pequeño y deliberado esta semana.",
        "generic":         "Este patrón pide atención constante ahora.",
    },
}


def _fallback(field_kind: str, language: str) -> str:
    lang = (language or "en").lower()[:2]
    bank = _FALLBACKS.get(lang) or _FALLBACKS["en"]
    return bank.get(field_kind) or bank.get("generic") or ""


def validate_field(text: str, field_kind: str = "generic",
                   language: str = "en", fallback: Optional[str] = None) -> str:
    """If `text` carries a banned token, return safe fallback. Else return text.

    NEVER word-strips. The fallback is a complete sentence so the reader sees a
    coherent, if generic, statement instead of garble.

    Args:
        text: prose to validate.
        field_kind: e.g. 'diagnosis', 'remedy_why', 'practice_why',
            'mantra_why', 'duration_reason', 'supporting_why', 'primary_action'.
        language: 'en' or 'es' (other langs fall back to 'en').
        fallback: explicit override; takes precedence over the kind-keyed default.
    """
    leak = has_leak(text)
    if leak is None:
        return text
    if fallback:
        return fallback
    return _fallback(field_kind, language)


def validate_in_place(payload: dict, paths: list, language: str = "en") -> int:
    """Walk specific JSON paths in `payload` and replace leaked fields.

    Each entry in `paths` is a tuple (json_path_segments, field_kind).
    json_path_segments is a list of either string keys or "[*]" for list walk.

    Returns number of fields replaced (for logging).
    """
    fixed = 0

    def _walk(node, segs, kind):
        nonlocal fixed
        if not segs:
            return node
        head, rest = segs[0], segs[1:]
        if head == "[*]" and isinstance(node, list):
            for i, v in enumerate(node):
                node[i] = _walk(v, rest, kind)
            return node
        if isinstance(node, dict):
            if head in node:
                if not rest and isinstance(node[head], str):
                    new = validate_field(node[head], kind, language)
                    if new != node[head]:
                        fixed += 1
                        node[head] = new
                else:
                    node[head] = _walk(node[head], rest, kind)
        return node

    for segs, kind in paths:
        _walk(payload, list(segs), kind)
    return fixed
