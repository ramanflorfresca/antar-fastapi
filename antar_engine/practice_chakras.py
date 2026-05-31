"""
antar_engine/practice_chakras.py
─────────────────────────────────────────────────────────────────────────────
Chakra ↔ planet diagnostic.  Phase 1 (practice redesign).

Derives each of the 7 chakra states from its ruling planets' natal conditions
(reusing places_conditions).  Planet names are allowed as actors (Path B);
no house numbers appear.
"""

from __future__ import annotations

from typing import Optional

CHAKRA_RULERS = {
    "crown":        ["Ketu", "Jupiter"],
    "third_eye":    ["Jupiter", "Moon", "Saturn"],
    "throat":       ["Mercury", "Saturn"],
    "heart":        ["Venus", "Sun"],
    "solar_plexus": ["Sun", "Mars"],
    "sacral":       ["Moon", "Venus", "Jupiter"],
    "root":         ["Mars", "Saturn"],
}

CHAKRA_ORDER = ["crown", "third_eye", "throat", "heart", "solar_plexus", "sacral", "root"]

_STRONG = {"exalted", "own_sign", "friend"}
_WEAK = {"debilitated", "combust", "sleeping"}
_AFFLICTED = {"debilitated", "combust", "sleeping", "enemy"}

# Plain-language condition word for the reason string.
_COND_WORD = {
    "en": {"exalted": "exalted", "own_sign": "in its own sign", "friend": "well-placed",
           "neutral": "neutral", "enemy": "strained", "debilitated": "weak",
           "combust": "overshadowed", "sleeping": "dormant"},
    "es": {"exalted": "exaltado", "own_sign": "en su propio signo", "friend": "bien ubicado",
           "neutral": "neutral", "enemy": "tensionado", "debilitated": "débil",
           "combust": "eclipsado", "sleeping": "dormido"},
}


# ── Chakra balancing mantras (bija) + Solfeggio tone for the chakra sheet ────
CHAKRA_MANTRAS = {
    "root":         {"name": "Om Lam",  "sanskrit": "ॐ लं",  "translit": "OM LAM",  "tone_hz": 396},
    "sacral":       {"name": "Om Vam",  "sanskrit": "ॐ वं",  "translit": "OM VAM",  "tone_hz": 417},
    "solar_plexus": {"name": "Om Ram",  "sanskrit": "ॐ रं",  "translit": "OM RAM",  "tone_hz": 528},
    "heart":        {"name": "Om Yam",  "sanskrit": "ॐ यं",  "translit": "OM YAM",  "tone_hz": 639},
    "throat":       {"name": "Om Aim",  "sanskrit": "ॐ ऐं",  "translit": "OM AIM",  "tone_hz": 741},
    "third_eye":    {"name": "Om Ksham","sanskrit": "ॐ क्षं", "translit": "OM KSHAM","tone_hz": 852},
    "crown":        {"name": "Om",      "sanskrit": "ॐ",     "translit": "OM",      "tone_hz": 963},
}


def build_chakra_mantra_response(chakra_key: str, language: str = "en") -> dict:
    """Chakra-specific balancing mantra with audio_url + tone_hz, or {}."""
    from antar_engine.practice_library import AUDIO_BASE, _audio_lang
    m = CHAKRA_MANTRAS.get(chakra_key)
    if not m:
        return {}
    lang = _audio_lang(language)
    return {
        "name": m["name"],
        "sanskrit": m["sanskrit"],
        "transliteration": m["translit"],
        "count": 108,
        "duration_minutes": 12,
        "audio_url": f"{AUDIO_BASE}/chakra-{chakra_key}-{lang}.mp3",
        "tone_hz": m["tone_hz"],
    }


def _lang(language: str) -> str:
    return "es" if str(language).lower().startswith("es") else "en"


def _reason(rulers_states: list[tuple], state: str, lang: str) -> str:
    parts = [f"{p} {_COND_WORD[lang].get(c, c)}" for p, c in rulers_states]
    joined = (" y " if lang == "es" else " and ").join(parts) if len(parts) <= 2 else \
        ((", ".join(parts[:-1])) + (" y " if lang == "es" else " and ") + parts[-1])
    if lang == "es":
        tail = {"strong": "— este centro tiene buen sostén.",
                "balanced": "— este centro está equilibrado.",
                "weak": "— este centro pide atención.",
                "blocked": "— este centro está bloqueado y necesita trabajo."}[state]
        return f"{joined.capitalize()} {tail}"
    tail = {"strong": "— this center is well supported.",
            "balanced": "— this center is balanced.",
            "weak": "— this center needs attention.",
            "blocked": "— this center is blocked and needs work."}[state]
    return f"{joined.capitalize()} {tail}"


def compute_chakra_states(
    chart: dict,
    conditions: Optional[dict] = None,
    priority_planet: Optional[str] = None,
    language: str = "en",
) -> dict:
    """
    Return {chakra: {state, reason, priority}} for all 7 chakras.
      state    : strong | balanced | weak | blocked
      priority : primary (ruled by today's priority planet)
                 | secondary (weak/blocked, not the priority planet)
                 | none
    """
    lang = _lang(language)
    if conditions is None:
        from antar_engine.places_conditions import compute_all_conditions
        conditions = compute_all_conditions(chart)

    out = {}
    for chakra in CHAKRA_ORDER:
        rulers = CHAKRA_RULERS[chakra]
        states = []
        for p in rulers:
            c = conditions.get(p, {}).get("condition")
            if c:
                states.append((p, c))
        if not states:
            out[chakra] = {"state": "balanced", "reason": "", "priority": "none"}
            continue

        conds = [c for _p, c in states]
        afflicted = [c for c in conds if c in _AFFLICTED]
        if len(afflicted) >= 2 or (afflicted and len(afflicted) == len(conds)):
            state = "blocked"
        elif any(c in _WEAK for c in conds):
            state = "weak"
        elif all(c in _STRONG for c in conds):
            state = "strong"
        elif all(c == "neutral" for c in conds):
            state = "balanced"
        else:
            state = "balanced"

        if priority_planet and priority_planet in rulers:
            priority = "primary"
        elif state in ("weak", "blocked"):
            priority = "secondary"
        else:
            priority = "none"

        out[chakra] = {"state": state, "reason": _reason(states, state, lang), "priority": priority}
    return out
