"""Relocated 'feel' (nakshatra flavour) and drishti reads. Descriptive only.

* feel    - the nakshatra the relocated ascendant falls in. Its Vimshottari ruler
            gives the everyday flavour of life in that place. Rendered as one
            plain sentence (no Sanskrit, no planet names).
* drishti - which supportive / testing planets look onto the relocated 1st, 7th
            or 10th house (the one that matches the concern). Planet-to-planet
            aspects never move with location; which HOUSE they land on does.

No score, no verdict. Nodes are not given aspects here (schools differ).
"""
from __future__ import annotations

from typing import Optional

_NAK_SPAN = 360.0 / 27.0
_VIM_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

_FEEL = {
    "en": {
        "Sun": "visible, status-aware and self-directed",
        "Moon": "emotional, nurturing and tuned to the people around you",
        "Mars": "driven, direct and competitive",
        "Mercury": "talkative, quick and full of exchange",
        "Jupiter": "expansive, hopeful and teaching-minded",
        "Venus": "warm, social and pleasure-seeking",
        "Saturn": "serious, structured and slow-building",
        "Rahu": "restless, ambitious and unconventional",
        "Ketu": "withdrawn, inward and detached",
    },
    "es": {
        "Sun": "visible, consciente del estatus y con rumbo propio",
        "Moon": "emocional, cuidadora y sintonizada con quienes te rodean",
        "Mars": "impulsada, directa y competitiva",
        "Mercury": "conversadora, ágil y llena de intercambio",
        "Jupiter": "expansiva, esperanzada y con vocación de enseñar",
        "Venus": "cálida, social y amante del placer",
        "Saturn": "seria, estructurada y de construcción lenta",
        "Rahu": "inquieta, ambiciosa y poco convencional",
        "Ketu": "retraída, interior y desapegada",
    },
}
_FEEL_FRAME = {
    "en": "Day to day, life in this place is likely to feel {flavor}.",
    "es": "En el día a día, la vida en este lugar probablemente se sienta {flavor}.",
}


def relocated_feel(relocation: dict, language: str = "en") -> Optional[dict]:
    """{'text': ...} from the nakshatra ruler of the relocated ascendant, or None."""
    lon = (relocation or {}).get("relocated_lagna_longitude")
    if lon is None:
        return None
    try:
        from antar_engine.places_composer import _lang
        lang = _lang(language)
        lord = _VIM_ORDER[int((float(lon) % 360.0) // _NAK_SPAN) % 9]
        bank = _FEEL.get(lang) or _FEEL["en"]
        frame = _FEEL_FRAME.get(lang) or _FEEL_FRAME["en"]
        return {"text": frame.format(flavor=bank[lord])}
    except Exception:
        return None


# ── drishti ─────────────────────────────────────────────────────────────────
_SPECIAL = {"Mars": (4, 8), "Jupiter": (5, 9), "Saturn": (3, 10)}   # plus the 7th for all
_ASPECTORS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
_SUPPORTIVE = {"Jupiter", "Venus", "Mercury", "Moon"}
_TESTING = {"Saturn", "Mars", "Sun"}
_CONCERN_HOUSE = {"love": (7, "partnership"), "career": (10, "working life"),
                  "business": (10, "working life"), "health": (1, "health and vitality")}
_THEME_ES = {"partnership": "pareja", "working life": "vida laboral",
             "health and vitality": "salud y vitalidad"}
_TEXT = {
    "en": {
        "supportive": "Supportive influences (your {q}) look onto the {theme} side of this place, easing it.",
        "testing": "Testing influences (your {q}) look onto the {theme} side of this place — expect it to ask more of you.",
    },
    "es": {
        "supportive": "Influencias favorables (tu {q}) miran hacia el lado de {theme} de este lugar y lo suavizan.",
        "testing": "Influencias exigentes (tu {q}) miran hacia el lado de {theme} de este lugar — espera que te pida más.",
    },
}


def _aspected_signs(sign_idx: int, planet: str) -> set:
    return {(sign_idx + n - 1) % 12 for n in (7,) + _SPECIAL.get(planet, ())}


def relocation_drishti(chart: dict, relocation: dict, concern: str,
                       language: str = "en") -> Optional[dict]:
    """{'polarity','text'} for the relocated house that matches the concern, when
    supportive and testing aspects are not balanced; else None."""
    spec = _CONCERN_HOUSE.get(concern)
    reloc_idx = (relocation or {}).get("relocated_lagna_index")
    if not spec or reloc_idx is None:
        return None
    house, theme = spec
    target = (int(reloc_idx) + house - 1) % 12
    sup, tes = [], []
    planets = (chart or {}).get("planets") or {}
    for p in _ASPECTORS:
        rec = planets.get(p) or {}
        si = rec.get("sign_index")
        if si is None and rec.get("longitude") is not None:
            si = int((float(rec["longitude"]) % 360.0) // 30.0)
        if si is None or int(si) == target:      # occupying = conjunction, not aspect
            continue
        if target in _aspected_signs(int(si), p):
            if p in _SUPPORTIVE:
                sup.append(p)
            elif p in _TESTING:
                tes.append(p)
    if len(sup) == len(tes):
        return None
    pol = "supportive" if len(sup) > len(tes) else "testing"
    try:
        from antar_engine.places_composer import _lang, _planet
        lang = _lang(language)
        names = [_planet(p, lang) for p in (sup if pol == "supportive" else tes)[:2]]
        q = " / ".join(names)
        th = _THEME_ES.get(theme, theme) if lang == "es" else theme
        frame = (_TEXT.get(lang) or _TEXT["en"])[pol]
        return {"polarity": pol, "text": frame.format(q=q, theme=th)}
    except Exception:
        return None
