"""
antar_engine/places_what_changes.py

The "WHAT will this move DO" read — the classical relocation-chart answer.

`places_lk_relocation.lk_relocation_findings` reads the Lal-Kitab layer
(debt/home shifts). This module reads the STANDARD Vedic relocation: keeping the
birth planets fixed, the ascendant + houses re-compute for the new place, so
each planet LANDS in a different house — "in this place, Saturn moves into your
10th of career." It names the most significant of those shifts in plain
language, honestly (the gift AND the cost), so a user sees what their chart
BECOMES at a location, not just a score.

Reads `relocation["relocated_planet_houses"]` = {planet: {natal_house,
relocated_house}} (same source lk_relocation_findings uses). Localized en/es/pt.
Never raises; returns [] when the relocation chart is unavailable.

Owner rule honored: malefics/nodes in the upachaya 3/6/11 THRIVE (Rahu-in-6th is
Harsha, not a dusthana weakness) — so a malefic relocating into the 6th is a
GIFT (fighting-spirit), not a strain. Only 8/12 (and 6 for benefics) read as a
cost. Descriptive only — no score, no verdict on whether to move.
"""
from __future__ import annotations

_BENEFIC = {"Jupiter", "Venus", "Moon", "Mercury"}
# everything else (Sun, Mars, Saturn, Rahu, Ketu) is treated as a malefic/harsh
# actor for the upachaya rule.

# jargon-free life-area per house
_AREA = {
    1:  {"en": "self and vitality",              "es": "identidad y vitalidad",           "pt": "identidade e vitalidade"},
    2:  {"en": "money and family",               "es": "el dinero y la familia",          "pt": "o dinheiro e a família"},
    3:  {"en": "drive and communication",        "es": "el empuje y la comunicación",     "pt": "o impulso e a comunicação"},
    4:  {"en": "home, roots and inner peace",    "es": "el hogar, las raíces y la paz interior", "pt": "o lar, as raízes e a paz interior"},
    5:  {"en": "creativity, children and mind",  "es": "la creatividad, los hijos y la mente", "pt": "a criatividade, os filhos e a mente"},
    6:  {"en": "work, service and health",       "es": "el trabajo, el servicio y la salud", "pt": "o trabalho, o serviço e a saúde"},
    7:  {"en": "partnership and close bonds",    "es": "la pareja y los vínculos cercanos", "pt": "a parceria e os vínculos próximos"},
    8:  {"en": "upheaval and shared matters",    "es": "la agitación y los asuntos compartidos", "pt": "a reviravolta e os assuntos compartilhados"},
    9:  {"en": "fortune, belief and the long journey", "es": "la fortuna, la fe y el gran viaje", "pt": "a fortuna, a fé e a longa jornada"},
    10: {"en": "career, standing and public life", "es": "la carrera, el estatus y la vida pública", "pt": "a carreira, o status e a vida pública"},
    11: {"en": "gains, income and network",      "es": "las ganancias, los ingresos y la red", "pt": "os ganhos, a renda e a rede"},
    12: {"en": "letting go, foreign lands and the inner world", "es": "el soltar, las tierras lejanas y el mundo interior", "pt": "o soltar, as terras distantes e o mundo interior"},
}

# what each graha BRINGS to the house it lands in
_QUALITY = {
    "Sun":     {"en": "authority and visibility",       "es": "autoridad y visibilidad",        "pt": "autoridade e visibilidade"},
    "Moon":    {"en": "feeling and belonging",          "es": "emoción y pertenencia",          "pt": "emoção e pertencimento"},
    "Mars":    {"en": "drive and courage",              "es": "empuje y coraje",                "pt": "impulso e coragem"},
    "Mercury": {"en": "sharp thinking and dealmaking",  "es": "pensamiento ágil y negociación", "pt": "raciocínio ágil e negociação"},
    "Jupiter": {"en": "growth, luck and wisdom",        "es": "crecimiento, suerte y sabiduría", "pt": "crescimento, sorte e sabedoria"},
    "Venus":   {"en": "ease, pleasure and relationship", "es": "soltura, placer y relación",     "pt": "leveza, prazer e relação"},
    "Saturn":  {"en": "structure and slow-built authority", "es": "estructura y autoridad de construcción lenta", "pt": "estrutura e autoridade construída aos poucos"},
    "Rahu":    {"en": "hunger, ambition and reinvention", "es": "hambre, ambición y reinvención", "pt": "fome, ambição e reinvenção"},
    "Ketu":    {"en": "detachment and depth",           "es": "desapego y profundidad",         "pt": "desapego e profundidade"},
}

# [de-jargon 2026-09-21] Lead with the plain QUALITY the planet stands for, not
# the planet NAME — "here structure and slow-built authority moves into career",
# not "here your Saturn moves into career". Same meaning, no jargon.
_LIFT = {
    "en": "Here {q} moves into {area} — this ground lifts it in that part of your life.",
    "es": "Aquí {q} entra en {area} — este lugar lo realza en esa parte de tu vida.",
    "pt": "Aqui {q} entra em {area} — este lugar o realça nessa parte da sua vida.",
}
_TEST = {
    "en": "Here {q} moves into {area} — this ground asks more of that area, and can stir it into strain.",
    "es": "Aquí {q} entra en {area} — este lugar exige más de esa área y puede tensarlo.",
    "pt": "Aqui {q} entra em {area} — este lugar exige mais dessa área e pode tensioná-lo.",
}

# render order: the angles astrocartography lights up first, then trines, gains,
# then the tested houses.
_HOUSE_RANK = {10: 0, 1: 1, 7: 2, 4: 3, 9: 4, 5: 5, 11: 6, 6: 7, 3: 8, 2: 9, 8: 10, 12: 11}
_NOTABLE = {1, 4, 5, 6, 7, 8, 9, 10, 11, 12}   # 2/3 are quieter; skipped as headlines


def _lang(language) -> str:
    base = str(language or "en").split("_")[0].split("-")[0].lower()
    return base if base in ("en", "es", "pt") else "en"


def _polarity(planet: str, house: int) -> str:
    """gift | cost for a planet landing in `house` (relocated). Honors the
    upachaya rule: malefics/nodes in 3/6/11 thrive."""
    if house in (1, 4, 5, 7, 9, 10, 11):
        return "gift"
    if house == 6:
        return "gift" if planet not in _BENEFIC else "cost"   # Harsha for a malefic
    if house in (8, 12):
        return "cost"
    return "gift"


def relocation_what_changes(relocation: dict, language: str = "en",
                            limit: int = 3) -> list[dict]:
    """The classical 'what your chart becomes here' read.

    Returns (never raises) a list of:
        {"planet": str, "house": int, "polarity": "gift"|"cost", "text": str}
    ordered angles-first, with at least one cost surfaced when one exists (so the
    read is honest, not only flattering). Empty when unavailable.
    """
    try:
        if not relocation or not relocation.get("_available"):
            return []
        moved = relocation.get("relocated_planet_houses") or {}
        if not moved:
            return []
        L = _lang(language)

        items = []
        for planet, mv in moved.items():
            if planet not in _QUALITY:
                continue
            try:
                nat_h = int(mv.get("natal_house"))
                rel_h = int(mv.get("relocated_house"))
            except (TypeError, ValueError):
                continue
            if rel_h == nat_h or rel_h not in _NOTABLE:
                continue   # only a real, headline-worthy relocation
            pol = _polarity(planet, rel_h)
            tmpl = _LIFT[L] if pol == "gift" else _TEST[L]
            text = tmpl.format(p=planet, area=_AREA[rel_h][L], q=_QUALITY[planet][L])
            items.append({"planet": planet, "house": rel_h, "polarity": pol, "text": text})

        if not items:
            return []
        items.sort(key=lambda it: (_HOUSE_RANK.get(it["house"], 99), it["planet"]))

        # keep it honest: if a cost exists but wouldn't make the top `limit`,
        # swap the weakest gift for the top-ranked cost.
        top = items[:limit]
        costs = [it for it in items if it["polarity"] == "cost"]
        if costs and not any(it["polarity"] == "cost" for it in top) and limit >= 2:
            top = top[:limit - 1] + [costs[0]]
        return top
    except Exception:
        return []
