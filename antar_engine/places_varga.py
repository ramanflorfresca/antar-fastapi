"""Relocated varga confirmation (descriptive annotation, never scored).

Relocation keeps the birth moment, so every planet's divisional (varga) sign is
the same in every city; only the varga LAGNA moves, and it is a pure function of
the relocated ascendant's degree. For each city we count houses from the
relocated varga lagna to the key planet's varga sign:

    love              -> navamsa (D-9): Venus and the natal 7th lord
    career / business -> dashamsa (D-10): the natal 10th lord

Supportive placement (kendra / trikona / 11th) or friction (6 / 8 / 12) becomes
one plain-language line on the place card. Neutral placements are omitted. No
score, no verdict: it confirms or qualifies what the line and houses already say.
"""
from __future__ import annotations

from typing import Optional

_SUPPORTIVE = {1, 4, 5, 7, 9, 10, 11}
_FRICTION = {6, 8, 12}

# concern -> (varga number, label key, extra planets besides the natal lord)
_SPEC = {
    "love":     (9,  "marriage", ["Venus"]),
    "career":   (10, "work",     []),
    "business": (10, "work",     []),
}
_LORD_CONCERN = {"love": "love", "career": "career", "business": "career"}

_TEXT = {
    "en": {
        ("marriage", "supportive"): "Seen through the deeper partnership chart for this place, your {q} lands on supportive ground — a relationship here reads as able to deliver what the line suggests.",
        ("marriage", "friction"):   "Seen through the deeper partnership chart for this place, your {q} lands on harder ground — closeness here asks for more work than the line alone suggests.",
        ("work", "supportive"):     "Seen through the deeper working-life chart for this place, your {q} lands on supportive ground — work here reads as able to carry the promise of the line.",
        ("work", "friction"):       "Seen through the deeper working-life chart for this place, your {q} lands on harder ground — the working life here asks for more effort than the line alone suggests.",
    },
    "es": {
        ("marriage", "supportive"): "Vista desde la carta profunda de pareja de este lugar, tu {q} queda en terreno favorable — una relación aquí parece capaz de dar lo que sugiere la línea.",
        ("marriage", "friction"):   "Vista desde la carta profunda de pareja de este lugar, tu {q} queda en terreno más duro — la cercanía aquí pide más trabajo del que sugiere la línea sola.",
        ("work", "supportive"):     "Vista desde la carta profunda de vida laboral de este lugar, tu {q} queda en terreno favorable — el trabajo aquí parece capaz de sostener la promesa de la línea.",
        ("work", "friction"):       "Vista desde la carta profunda de vida laboral de este lugar, tu {q} queda en terreno más duro — la vida laboral aquí pide más esfuerzo del que sugiere la línea sola.",
    },
}


def _key_planets(chart: dict, concern: str, extra: list) -> list:
    from antar_engine.places_concern import chart_lords_for_concern
    lords = chart_lords_for_concern(chart, _LORD_CONCERN[concern])
    out = []
    for p in lords + extra:
        if p not in out:
            out.append(p)
    return out


def relocation_varga_notes(chart: dict, relocation: dict, concern: str,
                           language: str = "en", limit: int = 2) -> list:
    """[{varga, planet, house, polarity, text}] for this city, or [] when the
    concern has no varga lens, the relocated ascendant degree is unavailable,
    or every placement is neutral."""
    spec = _SPEC.get(concern)
    reloc_lon: Optional[float] = (relocation or {}).get("relocated_lagna_longitude")
    if not spec or reloc_lon is None:
        return []
    n, label, extra = spec
    try:
        from antar_engine.antar_ephemeris import _divisional_sign_index
        from antar_engine.places_composer import _lang, _planet
        lang = _lang(language)
        frames = _TEXT.get(lang) or _TEXT["en"]
        lagna_v = _divisional_sign_index(reloc_lon, n) % 12
        out = []
        for planet in _key_planets(chart, concern, extra):
            rec = (chart.get("planets") or {}).get(planet) or {}
            lon = rec.get("longitude")
            if lon is None:
                continue
            house = ((_divisional_sign_index(float(lon), n) % 12) - lagna_v) % 12 + 1
            if house in _FRICTION:
                pol = "friction"
            elif house in _SUPPORTIVE:
                pol = "supportive"
            else:
                continue
            out.append({"varga": f"D{n}", "planet": planet, "house": house, "polarity": pol,
                        "text": frames[(label, pol)].format(q=_planet(planet, lang))})
        # friction first so a caution is never buried, then supportive
        out.sort(key=lambda r: 0 if r["polarity"] == "friction" else 1)
        return out[:limit]
    except Exception:
        return []
