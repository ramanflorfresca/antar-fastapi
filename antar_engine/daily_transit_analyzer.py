"""
antar_engine/daily_transit_analyzer.py
======================================
Phase 1 Transit Analyzer — computes slow-planet transit positions,
house placements from natal Moon/Lagna, classical interpretations,
dasha spotlight, and synthesis hints.

Called by: daily_prediction_engine.py (inside the 7-day loop)
Depends on: classical_transit_library.py, swisseph
"""
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import swisseph as swe

from antar_engine.classical_transit_library import lookup_classical_transit

logger = logging.getLogger("antar_engine.daily_transit_analyzer")

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

swe.set_sid_mode(swe.SIDM_LAHIRI)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGN_TO_INDEX = {s: i for i, s in enumerate(SIGNS)}

# Slow planets we track for daily transit analysis
SLOW_PLANETS = {
    "Saturn": swe.SATURN,
    "Jupiter": swe.JUPITER,
    "Rahu": swe.MEAN_NODE,  # Ketu derived from Rahu
}

SWE_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

# House quality classification
GOOD_HOUSES = {1, 2, 3, 5, 7, 9, 10, 11}
DUSTHANA_HOUSES = {6, 8, 12}
NEUTRAL_HOUSES = {4}

# Domain mapping by house
HOUSE_DOMAINS = {
    1: ["health", "identity"],
    2: ["finance", "family"],
    3: ["communication", "courage"],
    4: ["home", "emotional wellbeing"],
    5: ["relationships", "creativity"],
    6: ["health", "career"],
    7: ["relationships", "partnerships"],
    8: ["health", "transformation"],
    9: ["learning", "travel"],
    10: ["career", "public life"],
    11: ["finance", "social network"],
    12: ["spiritual", "isolation"],
}


# ─────────────────────────────────────────────────────────────────
# SWISS EPHEMERIS HELPERS
# ─────────────────────────────────────────────────────────────────

def _get_julian_day(target_date) -> float:
    """Convert a date to Julian Day number (noon UT)."""
    if isinstance(target_date, datetime):
        d = target_date
        return swe.julday(d.year, d.month, d.day,
                          d.hour + d.minute / 60.0)
    elif isinstance(target_date, date):
        return swe.julday(target_date.year, target_date.month,
                          target_date.day, 12.0)  # noon UT
    else:
        raise ValueError(f"target_date must be date or datetime, got {type(target_date)}")


def get_planet_full_position(target_date, planet_id: int) -> dict:
    """
    Compute sidereal position of a planet for a given date.
    Returns: { longitude, sign, sign_index, degree_in_sign, speed, retrograde }
    """
    jd = _get_julian_day(target_date)
    result = swe.calc_ut(jd, planet_id, SWE_FLAGS)
    lon = result[0][0]
    speed = result[0][3]
    sign_idx = int(lon / 30)
    deg_in_sign = lon % 30

    return {
        "longitude": round(lon, 4),
        "sign": SIGNS[sign_idx],
        "sign_index": sign_idx,
        "degree_in_sign": round(deg_in_sign, 2),
        "speed": round(speed, 4),
        "retrograde": speed < 0,
    }


def house_from_reference(transit_sign_index: int, reference_sign_index: int) -> int:
    """
    Compute house number of transit planet from a reference sign (Moon or Lagna).
    House 1 = same sign as reference.
    """
    return ((transit_sign_index - reference_sign_index) % 12) + 1


# ─────────────────────────────────────────────────────────────────
# NATAL CHART DATA EXTRACTORS
# ─────────────────────────────────────────────────────────────────

def _get_natal_sign_index(chart_data: dict, target: str = "Moon") -> int:
    """
    Extract the sign index of a natal body (Moon or Lagna/Ascendant).
    Returns sign index (0-11) or -1 if not found.
    """
    if target.lower() == "lagna":
        # Try ascendant / lagna from chart_data
        lagna = chart_data.get("lagna") or chart_data.get("ascendant", {})
        if isinstance(lagna, dict):
            sign = lagna.get("sign") or lagna.get("rashi") or ""
        elif isinstance(lagna, str):
            sign = lagna
        else:
            sign = ""
        return SIGN_TO_INDEX.get(sign, -1)

    # Planet lookup
    planets = chart_data.get("planets") or chart_data.get("planet_positions", [])

    if isinstance(planets, list):
        for p in planets:
            if isinstance(p, dict):
                name = (p.get("name") or p.get("planet") or "").strip()
                if name.lower() == target.lower():
                    sign = p.get("sign") or p.get("rashi") or ""
                    return SIGN_TO_INDEX.get(sign, -1)
    elif isinstance(planets, dict):
        body = planets.get(target) or planets.get(target.lower(), {})
        if body:
            sign = body.get("sign") or body.get("rashi") or ""
            return SIGN_TO_INDEX.get(sign, -1)

    return -1


# ─────────────────────────────────────────────────────────────────
# CORE TRANSIT ANALYSIS
# ─────────────────────────────────────────────────────────────────

def _compute_slow_transits(target_date, natal_moon_idx: int, natal_lagna_idx: int) -> list:
    """
    Compute positions and house placements for Saturn, Jupiter, Rahu, Ketu.
    Returns list of transit dicts.
    """
    transits = []

    for planet_name, planet_id in SLOW_PLANETS.items():
        pos = get_planet_full_position(target_date, planet_id)

        house_from_moon = house_from_reference(pos["sign_index"], natal_moon_idx) if natal_moon_idx >= 0 else None
        house_from_lagna = house_from_reference(pos["sign_index"], natal_lagna_idx) if natal_lagna_idx >= 0 else None

        # Classical interpretation (from Moon)
        classical = lookup_classical_transit(planet_name, house_from_moon) if house_from_moon else None

        transit = {
            "planet": planet_name,
            "sign": pos["sign"],
            "sign_index": pos["sign_index"],
            "degree": pos["degree_in_sign"],
            "retrograde": pos["retrograde"],
            "house_from_moon": house_from_moon,
            "house_from_lagna": house_from_lagna,
            "classical": classical,
        }
        transits.append(transit)

        # Ketu = Rahu + 180°
        if planet_name == "Rahu":
            ketu_lon = (pos["longitude"] + 180) % 360
            ketu_sign_idx = int(ketu_lon / 30)
            ketu_deg = ketu_lon % 30

            ketu_house_moon = house_from_reference(ketu_sign_idx, natal_moon_idx) if natal_moon_idx >= 0 else None
            ketu_house_lagna = house_from_reference(ketu_sign_idx, natal_lagna_idx) if natal_lagna_idx >= 0 else None
            ketu_classical = lookup_classical_transit("Ketu", ketu_house_moon) if ketu_house_moon else None

            transits.append({
                "planet": "Ketu",
                "sign": SIGNS[ketu_sign_idx],
                "sign_index": ketu_sign_idx,
                "degree": round(ketu_deg, 2),
                "retrograde": True,  # Ketu always retrograde
                "house_from_moon": ketu_house_moon,
                "house_from_lagna": ketu_house_lagna,
                "classical": ketu_classical,
            })

    return transits


def _build_dasha_spotlight(slow_transits: list, current_md_lord: str) -> Optional[dict]:
    """
    If the MD lord is one of the slow planets being tracked,
    that transit gets elevated to 'spotlight' status — it dominates the day.
    """
    if not current_md_lord:
        return None

    md_lord_clean = current_md_lord.strip()
    for t in slow_transits:
        if t["planet"].lower() == md_lord_clean.lower():
            house = t["house_from_moon"]
            house_quality = (
                "favorable" if house in GOOD_HOUSES
                else "challenging" if house in DUSTHANA_HOUSES
                else "neutral"
            )
            return {
                "planet": t["planet"],
                "sign": t["sign"],
                "house_from_moon": house,
                "house_from_lagna": t["house_from_lagna"],
                "retrograde": t["retrograde"],
                "house_quality": house_quality,
                "classical": t["classical"],
                "reason": f"{t['planet']} is your current Mahadasha lord — its transit position colors everything today.",
            }

    return None


def compute_synthesis_hints(slow_transits: list, dasha_spotlight: Optional[dict], natal_moon_sign: str) -> list:
    """
    Rule-based domain mapping: which life areas are activated, pressured, or supported.
    Returns a list of hint strings for prompt injection.
    """
    hints = []

    # Collect activated domains with polarity
    domain_signals = {}  # domain -> list of (planet, polarity)

    for t in slow_transits:
        house = t["house_from_moon"]
        if house is None:
            continue

        polarity = "support" if house in GOOD_HOUSES else "pressure" if house in DUSTHANA_HOUSES else "neutral"
        domains = HOUSE_DOMAINS.get(house, [])

        for d in domains:
            if d not in domain_signals:
                domain_signals[d] = []
            domain_signals[d].append((t["planet"], polarity))

    # Build hints from domain signals
    for domain, signals in domain_signals.items():
        support_planets = [p for p, pol in signals if pol == "support"]
        pressure_planets = [p for p, pol in signals if pol == "pressure"]

        if support_planets and pressure_planets:
            hints.append(
                f"{domain.upper()}: mixed — {', '.join(support_planets)} support "
                f"but {', '.join(pressure_planets)} pressure"
            )
        elif pressure_planets:
            hints.append(
                f"{domain.upper()}: under pressure from {', '.join(pressure_planets)}"
            )
        elif support_planets:
            hints.append(
                f"{domain.upper()}: supported by {', '.join(support_planets)}"
            )

    # Dasha lord emphasis
    if dasha_spotlight:
        planet = dasha_spotlight["planet"]
        quality = dasha_spotlight["house_quality"]
        hints.append(
            f"DASHA LORD ({planet}): transit is {quality} — weight this planet's themes most heavily"
        )

    # Retrograde note
    retro_planets = [t["planet"] for t in slow_transits if t["retrograde"]]
    if retro_planets:
        hints.append(
            f"RETROGRADE: {', '.join(retro_planets)} — internalize, review, don't force outcomes"
        )

    return hints


# ─────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────

async def analyze_day_transits(
    chart_data: dict,
    target_date,
    current_md_lord: str = "",
) -> dict:
    """
    Main function: compute slow-planet transit analysis for one day.

    Args:
        chart_data: natal chart dict from Supabase (parsed JSONB)
        target_date: date or datetime for the day to analyze
        current_md_lord: current Mahadasha lord name (e.g., "Saturn")

    Returns:
        dict with keys: slow_transits, dasha_spotlight, synthesis_hints,
        plus pre-formatted prompt blocks.
    """
    try:
        natal_moon_idx = _get_natal_sign_index(chart_data, "Moon")
        natal_lagna_idx = _get_natal_sign_index(chart_data, "lagna")

        if natal_moon_idx < 0:
            logger.warning("[transit-analyzer] Could not find natal Moon sign in chart_data")

        # Compute slow planet positions + house placements
        slow_transits = _compute_slow_transits(target_date, natal_moon_idx, natal_lagna_idx)

        # Build dasha spotlight
        dasha_spotlight = _build_dasha_spotlight(slow_transits, current_md_lord)

        # Compute synthesis hints
        natal_moon_sign = SIGNS[natal_moon_idx] if natal_moon_idx >= 0 else "unknown"
        synthesis_hints = compute_synthesis_hints(slow_transits, dasha_spotlight, natal_moon_sign)

        return {
            "slow_transits": slow_transits,
            "dasha_spotlight": dasha_spotlight,
            "synthesis_hints": synthesis_hints,
            # Pre-formatted prompt blocks
            "transit_analysis_block": format_for_prompt(slow_transits),
            "dasha_spotlight_block": format_dasha_spotlight(dasha_spotlight),
            "synthesis_hints_block": format_synthesis_hints(synthesis_hints),
        }

    except Exception as e:
        logger.error(f"[transit-analyzer] analyze_day_transits failed: {e}")
        return {
            "slow_transits": [],
            "dasha_spotlight": None,
            "synthesis_hints": [],
            "transit_analysis_block": "Transit data unavailable.",
            "dasha_spotlight_block": "No dasha spotlight available.",
            "synthesis_hints_block": "No synthesis hints available.",
        }


# ─────────────────────────────────────────────────────────────────
# PROMPT FORMATTERS
# ─────────────────────────────────────────────────────────────────

def format_for_prompt(slow_transits: list) -> str:
    """
    Format slow planet transit data into a text block for LLM prompt injection.
    """
    if not slow_transits:
        return "Transit data unavailable."

    lines = ["SLOW-PLANET TRANSITS (today):"]
    for t in slow_transits:
        retro_tag = " [R]" if t["retrograde"] else ""
        house_moon = f"H{t['house_from_moon']} from Moon" if t["house_from_moon"] else "house unknown"
        house_lagna = f"H{t['house_from_lagna']} from Lagna" if t["house_from_lagna"] else ""

        placement = house_moon
        if house_lagna:
            placement += f", {house_lagna}"

        lines.append(f"  {t['planet']} in {t['sign']} {t['degree']:.1f}°{retro_tag} → {placement}")

        # Add classical interpretation
        classical = t.get("classical")
        if classical:
            lines.append(f"    Classical: {classical['essence']}")
            lines.append(f"    Themes: {', '.join(classical['themes'])}")
            lines.append(f"    Advice: {classical['advice']}")

    return "\n".join(lines)


def format_dasha_spotlight(dasha_spotlight: Optional[dict]) -> str:
    """
    Format dasha spotlight into a text block for LLM prompt injection.
    """
    if not dasha_spotlight:
        return "No dasha lord among slow transiting planets."

    ds = dasha_spotlight
    retro_note = " (retrograde — internalized energy)" if ds["retrograde"] else ""
    lines = [
        f"DASHA LORD SPOTLIGHT: {ds['planet']}",
        f"  Position: {ds['sign']}, H{ds['house_from_moon']} from Moon{retro_note}",
        f"  Transit quality: {ds['house_quality']}",
        f"  {ds['reason']}",
    ]
    if ds["classical"]:
        lines.append(f"  Classical: {ds['classical']['essence']}")
        lines.append(f"  Advice: {ds['classical']['advice']}")

    return "\n".join(lines)


def format_synthesis_hints(synthesis_hints: list) -> str:
    """
    Format synthesis hints into a text block for LLM prompt injection.
    """
    if not synthesis_hints:
        return "No synthesis hints available."

    lines = ["SYNTHESIS HINTS (life-area activations):"]
    for hint in synthesis_hints:
        lines.append(f"  • {hint}")

    return "\n".join(lines)
