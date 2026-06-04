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

# ── Quantitative scoring (score_pct) ─────────────────────────────────────────
SIGNS_12 = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
            "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
_BENEFIC_ASPECTS = {"Jupiter": (5, 7, 9), "Venus": (7,), "Mercury": (7,), "Moon": (7,)}
_KENDRA_TRIKONA = {1, 4, 5, 7, 9, 10}

PLANET_STRENGTH_PCT = {
    "exalted": 95, "own_sign": 85, "moolatrikona": 80, "friend": 70,
    "neutral": 55, "enemy": 38, "debilitated": 18, "combust": 22, "sleeping": 25,
}


def _planet_house(chart, planet):
    """House (1-12) of a planet; uses chart's house field, else whole-sign fallback."""
    pdata = ((chart or {}).get("planets") or {}).get(planet) or {}
    h = pdata.get("house")
    if isinstance(h, int) and 1 <= h <= 12:
        return h
    sign = pdata.get("sign")
    lagna = (chart or {}).get("lagna") or {}
    lsign = lagna.get("sign") if isinstance(lagna, dict) else None
    if sign in SIGNS_12 and lsign in SIGNS_12:
        return ((SIGNS_12.index(sign) - SIGNS_12.index(lsign)) % 12) + 1
    return None


def _benefic_aspect_info(chart, target_house):
    """(aspected_by_benefic, benefic_in_kendra_or_trikona) for `target_house`."""
    if not target_house:
        return (False, False)
    planets = (chart or {}).get("planets") or {}
    aspected = from_kt = False
    for b in _BENEFICS:
        if b not in planets:
            continue
        hb = _planet_house(chart, b)
        if not hb:
            continue
        offset = ((target_house - hb) % 12) + 1
        if offset in _BENEFIC_ASPECTS[b]:
            aspected = True
            if hb in _KENDRA_TRIKONA:
                from_kt = True
    return (aspected, from_kt)


def _ruler_strength(planet, condition, chart):
    """0-100 strength of one ruling planet, with house + benefic-aspect modifiers."""
    s = PLANET_STRENGTH_PCT.get(condition, 55)
    h = _planet_house(chart, planet)
    if h is not None:
        aspected, from_kt = _benefic_aspect_info(chart, h)
        if h in (6, 8, 12) and not aspected:
            s -= 10
        if aspected and from_kt:
            s += 5
    return max(0, min(100, s))


def _chakra_score_pct(states, chart):
    """Average of the chakra's ruling planets' strengths, 0-100 int."""
    vals = [_ruler_strength(p, c, chart) for p, c in states]
    if not vals:
        return 55
    return int(round(max(0, min(100, sum(vals) / len(vals)))))


def _state_from_score(score_pct):
    if score_pct >= 80:
        return "strong"
    if score_pct >= 60:
        return "balanced"
    if score_pct >= 35:
        return "weak"
    return "blocked"

# Plain-language condition word for the reason string.
_COND_WORD = {
    "en": {"exalted": "exalted", "own_sign": "in its own sign", "friend": "well-placed",
           "neutral": "neutral", "enemy": "strained", "debilitated": "weak",
           "combust": "overshadowed", "sleeping": "dormant"},
    "es": {"exalted": "exaltada", "own_sign": "en su propio signo", "friend": "bien sostenida",
           "neutral": "neutral", "enemy": "tensionada", "debilitated": "débil",
           "combust": "eclipsada", "sleeping": "dormida"},
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
    from antar_engine.practice_scopes import _energy as _nrg
    _conn = "se lee" if lang == "es" else "reads"
    parts = [f"{_nrg(p, lang)} {_conn} {_COND_WORD[lang].get(c, c)}" for p, c in rulers_states]
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
            out[chakra] = {"state": "balanced", "score_pct": 55, "reason": "", "priority": "none"}
            continue

        score_pct = _chakra_score_pct(states, chart)
        state = _state_from_score(score_pct)

        if priority_planet and priority_planet in rulers:
            priority = "primary"
        elif state in ("weak", "blocked"):
            priority = "secondary"
        else:
            priority = "none"

        out[chakra] = {"state": state, "score_pct": score_pct,
                       "reason": _reason(states, state, lang), "priority": priority}
    return out
