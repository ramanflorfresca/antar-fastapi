"""
antar_engine/aspects_engine.py
===============================
Graha Drishti (planetary aspects) engine for transit analysis.

Computes which natal planets receive aspects from current transit planets.
This explains interior experience: "Saturn's 3rd aspect on your Moon is
why motivation feels heavy."

Phase 2 of daily prediction engine.
Called by: daily_transit_analyzer.py
"""

from __future__ import annotations
from typing import Dict, List, Optional

# ── Constants ─────────────────────────────────────────────────────────────────

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_TO_INDEX = {s: i for i, s in enumerate(SIGNS)}

# Every planet has a 7th house aspect by default.
# Special aspects override the default list entirely.
ASPECT_RULES = {
    "Sun":     [7],
    "Moon":    [7],
    "Mars":    [4, 7, 8],
    "Mercury": [7],
    "Jupiter": [5, 7, 9],
    "Venus":   [7],
    "Saturn":  [3, 7, 10],
    "Rahu":    [5, 7, 9],
    "Ketu":    [5, 7, 9],
}

# Malefic/benefic classification for aspect interpretation
MALEFICS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}
BENEFICS = {"Jupiter", "Venus", "Moon", "Mercury"}

# Natal planet significance for interpretation
NATAL_SIGNIFICANCE = {
    "Sun":     "ego, vitality, authority, father",
    "Moon":    "mind, emotions, mother, intuition",
    "Mars":    "energy, courage, aggression, siblings",
    "Mercury": "intellect, communication, business, learning",
    "Jupiter": "wisdom, expansion, fortune, teachers",
    "Venus":   "love, beauty, wealth, creativity",
    "Saturn":  "discipline, structure, delays, karma",
    "Rahu":    "desires, obsession, unconventional paths",
    "Ketu":    "detachment, spirituality, past karma",
}


def _get_natal_planet_positions(chart_data: dict) -> Dict[str, int]:
    """
    Extract sign indices for all natal planets from chart_data.
    Returns: {planet_name: sign_index (0-11)}
    """
    positions = {}
    planets = chart_data.get("planets") or chart_data.get("planet_positions", [])

    if isinstance(planets, list):
        for p in planets:
            if isinstance(p, dict):
                name = (p.get("name") or p.get("planet") or "").strip()
                sign = p.get("sign") or p.get("rashi") or ""
                if name and sign in SIGN_TO_INDEX:
                    positions[name] = SIGN_TO_INDEX[sign]
    elif isinstance(planets, dict):
        for name, data in planets.items():
            if isinstance(data, dict):
                sign = data.get("sign") or data.get("rashi") or ""
                if sign in SIGN_TO_INDEX:
                    positions[name] = SIGN_TO_INDEX[sign]

    # Also get Lagna
    lagna = chart_data.get("lagna") or chart_data.get("ascendant", {})
    if isinstance(lagna, dict):
        sign = lagna.get("sign") or lagna.get("rashi") or ""
        if sign in SIGN_TO_INDEX:
            positions["Lagna"] = SIGN_TO_INDEX[sign]
    elif isinstance(lagna, str) and lagna in SIGN_TO_INDEX:
        positions["Lagna"] = SIGN_TO_INDEX[lagna]

    return positions


def compute_aspects_to_natal(
    transit_positions: Dict[str, int],
    chart_data: dict,
) -> List[dict]:
    """
    For each transit planet, compute which natal planets it aspects today.

    Args:
        transit_positions: {planet_name: sign_index (0-11)} for today's transits
        chart_data: natal chart dict from Supabase

    Returns:
        List of aspect dicts:
        {
            "transit_planet": "Saturn",
            "transit_sign": "Pisces",
            "aspects_natal": "Moon",
            "natal_sign": "Sagittarius",
            "aspect_type": "3rd",
            "is_malefic": True,
            "note": "Saturn's 3rd aspect on natal Moon heavies mood and emotions",
        }
    """
    natal_positions = _get_natal_planet_positions(chart_data)
    if not natal_positions:
        return []

    aspects = []

    for transit_planet, transit_sign_idx in transit_positions.items():
        aspect_houses = ASPECT_RULES.get(transit_planet, [7])

        for aspect_house in aspect_houses:
            # Sign being aspected = (transit_sign + aspect_house - 1) % 12
            aspected_sign_idx = (transit_sign_idx + aspect_house - 1) % 12

            # Check which natal planets sit in the aspected sign
            for natal_planet, natal_sign_idx in natal_positions.items():
                if natal_sign_idx == aspected_sign_idx:
                    # Skip self-aspects (transit planet aspecting its own natal position
                    # is a conjunction or return, handled elsewhere)
                    if transit_planet == natal_planet and aspect_house == 1:
                        continue

                    is_malefic = transit_planet in MALEFICS
                    significance = NATAL_SIGNIFICANCE.get(natal_planet, "")

                    # Build interpretation note
                    if is_malefic:
                        if natal_planet == "Moon":
                            note = f"{transit_planet}'s {_ordinal(aspect_house)} aspect on natal Moon heavies mood and emotions"
                        elif natal_planet == "Sun":
                            note = f"{transit_planet}'s {_ordinal(aspect_house)} aspect on natal Sun challenges vitality and confidence"
                        elif natal_planet == "Mercury":
                            note = f"{transit_planet}'s {_ordinal(aspect_house)} aspect on natal Mercury creates mental tension and communication friction"
                        elif natal_planet == "Venus":
                            note = f"{transit_planet}'s {_ordinal(aspect_house)} aspect on natal Venus strains relationships and creativity"
                        elif natal_planet == "Jupiter":
                            note = f"{transit_planet}'s {_ordinal(aspect_house)} aspect on natal Jupiter dampens optimism and growth"
                        elif natal_planet == "Lagna":
                            note = f"{transit_planet}'s {_ordinal(aspect_house)} aspect on Lagna pressures health and self-presentation"
                        else:
                            note = f"{transit_planet}'s {_ordinal(aspect_house)} aspect on natal {natal_planet} creates friction in {significance}"
                    else:
                        if natal_planet == "Moon":
                            note = f"{transit_planet}'s {_ordinal(aspect_house)} aspect on natal Moon lifts emotional clarity"
                        elif natal_planet == "Sun":
                            note = f"{transit_planet}'s {_ordinal(aspect_house)} aspect on natal Sun boosts confidence and authority"
                        elif natal_planet == "Lagna":
                            note = f"{transit_planet}'s {_ordinal(aspect_house)} aspect on Lagna supports health and presence"
                        else:
                            note = f"{transit_planet}'s {_ordinal(aspect_house)} aspect on natal {natal_planet} supports {significance}"

                    aspects.append({
                        "transit_planet": transit_planet,
                        "transit_sign": SIGNS[transit_sign_idx],
                        "aspects_natal": natal_planet,
                        "natal_sign": SIGNS[natal_sign_idx],
                        "aspect_type": f"{_ordinal(aspect_house)}",
                        "is_malefic": is_malefic,
                        "note": note,
                    })

    # Sort: malefic aspects on Moon/Sun/Lagna first (most impactful)
    priority_natals = {"Moon": 0, "Sun": 1, "Lagna": 2}
    aspects.sort(key=lambda a: (
        0 if a["is_malefic"] else 1,
        priority_natals.get(a["aspects_natal"], 5),
    ))

    return aspects


def get_significant_aspects(aspects: List[dict], max_count: int = 5) -> List[dict]:
    """
    Filter to most significant aspects for prompt injection.
    Prioritizes malefic aspects on sensitive natal points (Moon, Sun, Lagna).
    """
    # Already sorted by significance from compute_aspects_to_natal
    return aspects[:max_count]


def _ordinal(n: int) -> str:
    """Convert house number to ordinal string."""
    if n == 1:
        return "1st"
    elif n == 2:
        return "2nd"
    elif n == 3:
        return "3rd"
    else:
        return f"{n}th"
