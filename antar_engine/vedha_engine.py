"""
antar_engine/vedha_engine.py
=============================
Phase 3 — Vedha (obstruction) analysis for transit benefits.

Classical Chandra-gochara vedha: when a planet transits a favorable
house from Moon, its benefit gets CANCELLED if another planet
simultaneously occupies the corresponding vedha point.

Standard vedha tables from Brihat Samhita / Phala Deepika.

Called by: daily_transit_analyzer.py (Phase 3 integration)
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("antar_engine.vedha_engine")

# ─────────────────────────────────────────────────────────────────
# VEDHA TABLES
# ─────────────────────────────────────────────────────────────────
# Format: { favorable_house_from_moon: vedha_point_house_from_moon }
# If a malefic/any planet is in the vedha point, the favorable transit
# benefit is cancelled.

# Sun: favorable in 3, 6, 10, 11
SUN_VEDHAS = {
    3: 9,
    6: 12,
    10: 4,
    11: 5,
}

# Moon: favorable in 1, 3, 6, 7, 10, 11
MOON_VEDHAS = {
    1: 5,
    3: 9,
    6: 12,
    7: 2,
    10: 4,
    11: 8,
}

# Mars: favorable in 3, 6, 11
MARS_VEDHAS = {
    3: 12,
    6: 9,
    11: 5,
}

# Mercury: favorable in 2, 4, 6, 8, 10, 11
MERCURY_VEDHAS = {
    2: 5,
    4: 3,
    6: 9,
    8: 1,
    10: 7,
    11: 12,
}

# Jupiter: favorable in 2, 5, 7, 9, 11
JUPITER_VEDHAS = {
    2: 12,
    5: 4,
    7: 3,
    9: 10,
    11: 8,
}

# Venus: favorable in 1, 2, 3, 4, 5, 8, 9, 11, 12
VENUS_VEDHAS = {
    1: 8,
    2: 7,
    3: 1,
    4: 10,
    5: 9,
    8: 5,
    9: 11,
    11: 6,
    12: 3,
}

# Saturn: favorable in 3, 6, 11
SATURN_VEDHAS = {
    3: 12,
    6: 9,
    11: 5,
}

# Rahu/Ketu: use Saturn's vedha table (traditional practice)
RAHU_VEDHAS = SATURN_VEDHAS
KETU_VEDHAS = SATURN_VEDHAS

VEDHA_TABLES = {
    "Sun": SUN_VEDHAS,
    "Moon": MOON_VEDHAS,
    "Mars": MARS_VEDHAS,
    "Mercury": MERCURY_VEDHAS,
    "Jupiter": JUPITER_VEDHAS,
    "Venus": VENUS_VEDHAS,
    "Saturn": SATURN_VEDHAS,
    "Rahu": RAHU_VEDHAS,
    "Ketu": KETU_VEDHAS,
}

# Houses that are favorable for each planet (from Moon)
FAVORABLE_HOUSES = {
    "Sun": {3, 6, 10, 11},
    "Moon": {1, 3, 6, 7, 10, 11},
    "Mars": {3, 6, 11},
    "Mercury": {2, 4, 6, 8, 10, 11},
    "Jupiter": {2, 5, 7, 9, 11},
    "Venus": {1, 2, 3, 4, 5, 8, 9, 11, 12},
    "Saturn": {3, 6, 11},
    "Rahu": {3, 6, 11},
    "Ketu": {3, 6, 11},
}


# ─────────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────────

def check_vedha(
    planet: str,
    transit_house_from_moon: int,
    all_transit_houses: Dict[str, int],
) -> dict:
    """
    Determine if a transit planet's benefit is canceled by vedha.

    Args:
        planet: name of the transiting planet (e.g., "Saturn")
        transit_house_from_moon: house # (1-12) of this planet from Moon
        all_transit_houses: {planet_name: house_from_moon} for ALL transiting planets

    Returns:
        {
            "has_vedha": bool,
            "vedha_point": int or None,
            "cancelling_planet": str or None,
            "is_favorable_house": bool,
            "note": str,
        }
    """
    result = {
        "has_vedha": False,
        "vedha_point": None,
        "cancelling_planet": None,
        "is_favorable_house": False,
        "note": "",
    }

    if not transit_house_from_moon or not all_transit_houses:
        return result

    # Check if this planet is in a favorable house
    favorable = FAVORABLE_HOUSES.get(planet, set())
    is_favorable = transit_house_from_moon in favorable
    result["is_favorable_house"] = is_favorable

    if not is_favorable:
        # Vedha only matters for favorable transits — unfavorable transits
        # don't need cancellation (they're already unfavorable)
        return result

    # Look up vedha point
    vedha_table = VEDHA_TABLES.get(planet, {})
    vedha_point = vedha_table.get(transit_house_from_moon)

    if not vedha_point:
        return result

    result["vedha_point"] = vedha_point

    # Check if ANY planet is in the vedha point
    for other_planet, other_house in all_transit_houses.items():
        if other_planet == planet:
            continue
        if other_house == vedha_point:
            result["has_vedha"] = True
            result["cancelling_planet"] = other_planet
            result["note"] = (
                f"{planet}'s benefit in H{transit_house_from_moon} from Moon is "
                f"canceled because {other_planet} is in H{vedha_point} from Moon (vedha point)."
            )
            return result

    return result


def check_all_vedhas(
    all_transits: List[dict],
    natal_moon_sign_index: int,
) -> Dict[str, dict]:
    """
    Check vedha for all transiting planets at once.

    Args:
        all_transits: list of transit dicts (each must have 'planet' and 'house_from_moon')
        natal_moon_sign_index: sign index (0-11) of natal Moon

    Returns:
        {planet_name: vedha_result_dict} for each planet that has a favorable transit
    """
    # Build house lookup
    all_houses = {}
    for t in all_transits:
        planet = t.get("planet", "")
        house = t.get("house_from_moon")
        if planet and house:
            all_houses[planet] = house

    # Check each planet
    vedha_results = {}
    for t in all_transits:
        planet = t.get("planet", "")
        house = t.get("house_from_moon")
        if not planet or not house:
            continue

        vedha = check_vedha(planet, house, all_houses)
        if vedha.get("is_favorable_house"):
            vedha_results[planet] = vedha

    return vedha_results


def format_vedha_for_prompt(vedha_results: Dict[str, dict]) -> str:
    """
    Format vedha analysis into a text block for LLM prompt injection.
    """
    if not vedha_results:
        return ""

    active_vedhas = {p: v for p, v in vedha_results.items() if v.get("has_vedha")}
    clear_benefits = {p: v for p, v in vedha_results.items() if not v.get("has_vedha")}

    if not active_vedhas and not clear_benefits:
        return ""

    lines = ["VEDHA ANALYSIS (transit benefit obstructions):"]

    if active_vedhas:
        for planet, v in active_vedhas.items():
            lines.append(f"  {planet} [VEDHA ACTIVE]: {v.get('note', '')}")

    if clear_benefits:
        clear_names = ", ".join(clear_benefits.keys())
        lines.append(f"  Clear benefits (no vedha): {clear_names}")

    return "\n".join(lines)
