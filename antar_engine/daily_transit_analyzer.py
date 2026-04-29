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
from antar_engine.tara_bala import compute_tara_bala, find_next_favorable_tara
from antar_engine.aspects_engine import compute_aspects_to_natal, get_significant_aspects
from antar_engine.ashtakavarga import get_day_ashtakavarga_analysis

# Phase 3 imports
from antar_engine.day_chart_engine import cast_day_chart, get_country_coords, format_day_chart_for_prompt
from antar_engine.yoga_detector import detect_day_yogas, format_day_yogas_for_prompt
from antar_engine.muhurta_engine import compute_muhurtas, format_muhurtas_for_prompt
from antar_engine.vedha_engine import check_all_vedhas, format_vedha_for_prompt

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

# Fast planets added in Phase 2
FAST_PLANETS = {
    "Sun": swe.SUN,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
}

# All planets for ashtakavarga aggregate (7 classical)
ALL_SEVEN_PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
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


def _compute_fast_transits(target_date, natal_moon_idx: int, natal_lagna_idx: int) -> list:
    """
    Compute positions and house placements for Sun, Mars, Mercury, Venus.
    Returns list of transit dicts (same shape as slow_transits).
    """
    transits = []

    for planet_name, planet_id in FAST_PLANETS.items():
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

    return transits


def _compute_all_transit_sign_indices(target_date) -> dict:
    """
    Compute current sign index for all 7 classical planets.
    Used for ashtakavarga day aggregate.
    Returns: {planet_name: sign_index}
    """
    positions = {}
    for planet_name, planet_id in ALL_SEVEN_PLANETS.items():
        pos = get_planet_full_position(target_date, planet_id)
        positions[planet_name] = pos["sign_index"]
    return positions


def _get_natal_moon_nakshatra(chart_data: dict) -> str:
    """Extract natal Moon nakshatra from chart_data."""
    planets = chart_data.get("planets") or chart_data.get("planet_positions", [])

    if isinstance(planets, list):
        for p in planets:
            if isinstance(p, dict):
                name = (p.get("name") or p.get("planet") or "").strip()
                if name.lower() == "moon":
                    return p.get("nakshatra") or ""
    elif isinstance(planets, dict):
        moon = planets.get("Moon") or planets.get("moon", {})
        if isinstance(moon, dict):
            return moon.get("nakshatra") or ""

    return ""


def _get_today_moon_nakshatra(target_date) -> str:
    """Compute today's Moon nakshatra from Swiss Ephemeris."""
    NAKSHATRAS = [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
        "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
        "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
        "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
        "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
        "Revati",
    ]
    try:
        moon_pos = get_planet_full_position(target_date, swe.MOON)
        nak_idx = int(moon_pos["longitude"] / (360 / 27))
        return NAKSHATRAS[nak_idx % 27]
    except Exception:
        return ""


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
    current_country: str = "",
    tz_offset: float = 0,
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

        # ── Phase 1: Slow planet positions + house placements ──
        slow_transits = _compute_slow_transits(target_date, natal_moon_idx, natal_lagna_idx)

        # ── Phase 2: Fast planet positions + house placements ──
        fast_transits = _compute_fast_transits(target_date, natal_moon_idx, natal_lagna_idx)

        # Combined for synthesis
        all_transits = slow_transits + fast_transits

        # Build dasha spotlight (checks all transits now)
        dasha_spotlight = _build_dasha_spotlight(all_transits, current_md_lord)

        # Compute synthesis hints (uses all transits)
        natal_moon_sign = SIGNS[natal_moon_idx] if natal_moon_idx >= 0 else "unknown"
        synthesis_hints = compute_synthesis_hints(all_transits, dasha_spotlight, natal_moon_sign)

        # ── Phase 2: Ashtakavarga day aggregate ──
        ashtakavarga_data = None
        try:
            all_sign_indices = _compute_all_transit_sign_indices(target_date)
            ashtakavarga_data = get_day_ashtakavarga_analysis(chart_data, all_sign_indices)
        except Exception as av_err:
            logger.warning(f"[transit-analyzer] Ashtakavarga failed (non-fatal): {av_err}")

        # ── Phase 2: Tara Bala ──
        tara_bala_data = None
        next_favorable = None
        try:
            natal_moon_nak = _get_natal_moon_nakshatra(chart_data)
            today_moon_nak = _get_today_moon_nakshatra(target_date)
            if natal_moon_nak and today_moon_nak:
                tara_bala_data = compute_tara_bala(natal_moon_nak, today_moon_nak)
                # If unfavorable, find next favorable tara
                if tara_bala_data and tara_bala_data["quality"] in ("unfavorable", "caution", "cautious"):
                    next_favorable = find_next_favorable_tara(natal_moon_nak, today_moon_nak)
        except Exception as tb_err:
            logger.warning(f"[transit-analyzer] Tara Bala failed (non-fatal): {tb_err}")

        # ── Phase 2: Aspects to natal ──
        aspects_to_natal = []
        try:
            transit_positions = {}
            for t in all_transits:
                transit_positions[t["planet"]] = t["sign_index"]
            raw_aspects = compute_aspects_to_natal(transit_positions, chart_data)
            aspects_to_natal = get_significant_aspects(raw_aspects, max_count=6)
        except Exception as asp_err:
            logger.warning(f"[transit-analyzer] Aspects failed (non-fatal): {asp_err}")

        # ── Phase 3: Day chart, yogas, muhurta, vedha ──
        day_chart_data = {}
        day_yogas_data = []
        muhurtas_data = {}
        vedha_data = {}

        try:
            coords = get_country_coords(current_country) if current_country else None
            if coords:
                p3_lat, p3_lon = coords

                # Day chart at dawn
                day_chart_data = await cast_day_chart(target_date, p3_lat, p3_lon)

                # Day yogas
                if day_chart_data:
                    day_yogas_data = detect_day_yogas(day_chart_data)

                # Muhurta windows
                muhurtas_data = compute_muhurtas(target_date, p3_lat, p3_lon, tz_offset=tz_offset)

                # Vedha analysis on all transits
                if natal_moon_idx >= 0:
                    vedha_data = check_all_vedhas(all_transits, natal_moon_idx)
                    # Annotate transits with vedha info
                    for tx in all_transits:
                        planet = tx.get("planet", "")
                        if planet in vedha_data:
                            vedha = vedha_data[planet]
                            tx["vedha"] = vedha
                            if vedha.get("has_vedha") and tx.get("classical"):
                                tx["classical"]["essence"] += f" [VEDHA: {vedha['note']}]"
            else:
                logger.info(f"[transit-analyzer] No coords for country '{current_country}' — skipping Phase 3")
        except Exception as p3_err:
            logger.warning(f"[transit-analyzer] Phase 3 failed (non-fatal): {p3_err}")

        # ── Build enhanced synthesis hints ──
        enhanced_synthesis = _build_enhanced_synthesis(
            synthesis_hints, ashtakavarga_data, tara_bala_data,
            next_favorable, aspects_to_natal
        )

        return {
            # Phase 1 (kept)
            "slow_transits": slow_transits,
            "dasha_spotlight": dasha_spotlight,
            "synthesis_hints": synthesis_hints,
            # Phase 2 additions
            "fast_transits": fast_transits,
            "all_planet_transits": all_transits,
            "ashtakavarga": ashtakavarga_data,
            "tara_bala": tara_bala_data,
            "next_favorable_tara": next_favorable,
            "aspects_to_natal": aspects_to_natal,
            "enhanced_synthesis": enhanced_synthesis,
            # Pre-formatted prompt blocks
            "transit_analysis_block": format_all_transits_for_prompt(all_transits),
            "dasha_spotlight_block": format_dasha_spotlight(dasha_spotlight),
            "synthesis_hints_block": format_synthesis_hints(synthesis_hints),
            "ashtakavarga_block": format_ashtakavarga(ashtakavarga_data),
            "tara_bala_block": format_tara_bala(tara_bala_data, next_favorable),
            "aspects_block": format_aspects(aspects_to_natal),
            "enhanced_synthesis_block": format_enhanced_synthesis(enhanced_synthesis),
            # Phase 3 additions
            "day_chart": day_chart_data,
            "day_yogas": day_yogas_data,
            "muhurtas": muhurtas_data,
            "vedha": vedha_data,
            "day_chart_block": format_day_chart_for_prompt(day_chart_data),
            "day_yogas_block": format_day_yogas_for_prompt(day_yogas_data),
            "muhurtas_block": format_muhurtas_for_prompt(muhurtas_data),
            "vedha_block": format_vedha_for_prompt(vedha_data),
        }

    except Exception as e:
        logger.error(f"[transit-analyzer] analyze_day_transits failed: {e}")
        return {
            "slow_transits": [],
            "fast_transits": [],
            "all_planet_transits": [],
            "dasha_spotlight": None,
            "synthesis_hints": [],
            "ashtakavarga": None,
            "tara_bala": None,
            "next_favorable_tara": None,
            "aspects_to_natal": [],
            "enhanced_synthesis": None,
            "transit_analysis_block": "Transit data unavailable.",
            "dasha_spotlight_block": "No dasha spotlight available.",
            "synthesis_hints_block": "No synthesis hints available.",
            "ashtakavarga_block": "",
            "tara_bala_block": "",
            "aspects_block": "",
            "enhanced_synthesis_block": "",
            # Phase 3 fallbacks
            "day_chart": {},
            "day_yogas": [],
            "muhurtas": {},
            "vedha": {},
            "day_chart_block": "",
            "day_yogas_block": "",
            "muhurtas_block": "",
            "vedha_block": "",
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


# ─────────────────────────────────────────────────────────────────
# PHASE 2 PROMPT FORMATTERS
# ─────────────────────────────────────────────────────────────────

def format_all_transits_for_prompt(all_transits: list) -> str:
    """
    Format ALL planet transit data (slow + fast) into a text block for LLM prompt.
    """
    if not all_transits:
        return "Transit data unavailable."

    # Separate slow and fast for clarity
    slow = [t for t in all_transits if t["planet"] in ("Saturn", "Jupiter", "Rahu", "Ketu")]
    fast = [t for t in all_transits if t["planet"] not in ("Saturn", "Jupiter", "Rahu", "Ketu")]

    lines = ["ALL PLANET TRANSITS (today):"]
    lines.append("")
    lines.append("  SLOW PLANETS (long-term backdrop):")
    for t in slow:
        retro_tag = " [R]" if t["retrograde"] else ""
        house_moon = f"H{t['house_from_moon']} from Moon" if t["house_from_moon"] else "house unknown"
        house_lagna = f"H{t['house_from_lagna']} from Lagna" if t["house_from_lagna"] else ""
        placement = house_moon + (f", {house_lagna}" if house_lagna else "")
        lines.append(f"    {t['planet']} in {t['sign']} {t['degree']:.1f}°{retro_tag} → {placement}")
        classical = t.get("classical")
        if classical:
            lines.append(f"      Classical: {classical['essence']}")
            lines.append(f"      Advice: {classical['advice']}")

    lines.append("")
    lines.append("  FAST PLANETS (today's flavor):")
    for t in fast:
        retro_tag = " [R]" if t["retrograde"] else ""
        house_moon = f"H{t['house_from_moon']} from Moon" if t["house_from_moon"] else "house unknown"
        house_lagna = f"H{t['house_from_lagna']} from Lagna" if t["house_from_lagna"] else ""
        placement = house_moon + (f", {house_lagna}" if house_lagna else "")
        lines.append(f"    {t['planet']} in {t['sign']} {t['degree']:.1f}°{retro_tag} → {placement}")
        classical = t.get("classical")
        if classical:
            lines.append(f"      Classical: {classical['essence']}")
            lines.append(f"      Advice: {classical['advice']}")

    return "\n".join(lines)


def format_ashtakavarga(av_data: Optional[dict]) -> str:
    """Format ashtakavarga day analysis for prompt injection."""
    if not av_data:
        return ""

    aggregate = av_data["aggregate_today"]
    classification = av_data["classification"]

    lines = [f"ASHTAKAVARGA QUANTIFICATION:"]
    lines.append(f"  Today's aggregate: {aggregate}/56 ({classification})")

    for planet, scores in av_data.get("planet_scores", {}).items():
        lines.append(f"    {planet} in {scores['sign']}: {scores['bindu']}/8 bindus ({scores['interpretation']})")

    return "\n".join(lines)


def format_tara_bala(tara_data: Optional[dict], next_favorable: Optional[dict] = None) -> str:
    """Format tara bala for prompt injection."""
    if not tara_data:
        return ""

    lines = ["TARA BALA (nakshatra day timing):"]
    lines.append(f"  Today's tara: {tara_data['tara_name']} ({tara_data['quality']})")
    lines.append(f"  Classical advice: {tara_data['advice']}")
    lines.append(f"  Nakshatra count from natal Moon: {tara_data['count']}")

    if next_favorable:
        lines.append(f"  Next favorable tara: {next_favorable['tara_name']} in ~{next_favorable.get('approx_days', '?')} days ({next_favorable.get('nakshatra', '')})")

    return "\n".join(lines)


def format_aspects(aspects: list) -> str:
    """Format significant transit aspects to natal planets for prompt injection."""
    if not aspects:
        return ""

    lines = ["TRANSIT ASPECTS TO NATAL PLANETS:"]
    for a in aspects:
        malefic_tag = "[MALEFIC]" if a["is_malefic"] else "[BENEFIC]"
        lines.append(f"  {a['transit_planet']} ({a['transit_sign']}) → {a['aspect_type']} aspect → natal {a['aspects_natal']} ({a['natal_sign']}) {malefic_tag}")
        lines.append(f"    {a['note']}")

    return "\n".join(lines)


def format_enhanced_synthesis(synthesis: Optional[dict]) -> str:
    """Format enhanced synthesis for prompt injection."""
    if not synthesis:
        return ""

    lines = ["ENHANCED DAY SYNTHESIS:"]

    if synthesis.get("overall_score") is not None:
        lines.append(f"  Ashtakavarga day score: {synthesis['overall_score']}/56 ({synthesis.get('quality_label', '')})")

    if synthesis.get("tara_quality"):
        lines.append(f"  Tara bala: {synthesis['tara_name']} ({synthesis['tara_quality']})")

    if synthesis.get("dominant_theme"):
        lines.append(f"  Dominant theme: {synthesis['dominant_theme']}")

    if synthesis.get("why_stuck"):
        lines.append(f"  Why dynamics feel the way they do: {synthesis['why_stuck']}")

    if synthesis.get("action_timing"):
        lines.append(f"  Action timing: {synthesis['action_timing']}")

    return "\n".join(lines)


def _build_enhanced_synthesis(
    base_hints: list,
    av_data: Optional[dict],
    tara_data: Optional[dict],
    next_favorable: Optional[dict],
    aspects: list,
) -> dict:
    """
    Build enhanced synthesis combining all Phase 2 signals.
    This gives Claude the "why dynamics feel the way they do" answer.
    """
    synthesis = {
        "overall_score": None,
        "quality_label": "",
        "tara_name": "",
        "tara_quality": "",
        "dominant_theme": "",
        "why_stuck": "",
        "action_timing": "",
    }

    # Ashtakavarga quantification
    if av_data:
        synthesis["overall_score"] = av_data["aggregate_today"]
        synthesis["quality_label"] = av_data["classification"]

    # Tara bala
    if tara_data:
        synthesis["tara_name"] = tara_data["tara_name"]
        synthesis["tara_quality"] = tara_data["quality"]

    # Build "why stuck" narrative from combined signals
    friction_layers = []

    if av_data and av_data["aggregate_today"] < 28:
        friction_layers.append(
            f"ashtakavarga aggregate is {av_data['aggregate_today']}/56 (below average)"
        )

    if tara_data and tara_data["quality"] in ("unfavorable", "caution", "cautious"):
        friction_layers.append(
            f"tara bala is {tara_data['tara_name']} ({tara_data['quality']})"
        )

    # Malefic aspects on Moon/Sun
    malefic_on_sensitive = [
        a for a in aspects
        if a["is_malefic"] and a["aspects_natal"] in ("Moon", "Sun", "Lagna")
    ]
    for a in malefic_on_sensitive[:2]:
        friction_layers.append(
            f"{a['transit_planet']}'s {a['aspect_type']} aspect on natal {a['aspects_natal']}"
        )

    if friction_layers:
        synthesis["why_stuck"] = " + ".join(friction_layers)
    else:
        # Check for positive signals
        support_layers = []
        if av_data and av_data["aggregate_today"] >= 35:
            support_layers.append(f"ashtakavarga {av_data['aggregate_today']}/56 is strong")
        if tara_data and tara_data["quality"] in ("favorable", "very_favorable"):
            support_layers.append(f"{tara_data['tara_name']} tara supports action")
        benefic_aspects = [a for a in aspects if not a["is_malefic"] and a["aspects_natal"] in ("Moon", "Sun", "Lagna")]
        for a in benefic_aspects[:1]:
            support_layers.append(f"{a['transit_planet']} supports natal {a['aspects_natal']}")
        if support_layers:
            synthesis["dominant_theme"] = "Supportive day: " + " + ".join(support_layers)

    # Action timing
    if tara_data and tara_data["quality"] in ("unfavorable", "caution", "cautious") and next_favorable:
        synthesis["action_timing"] = (
            f"Wait for {next_favorable['tara_name']} tara (~{next_favorable.get('approx_days', '?')} days)"
        )
    elif tara_data and tara_data["quality"] in ("favorable", "very_favorable"):
        synthesis["action_timing"] = f"Act today — {tara_data['tara_name']} tara favors initiative"

    return synthesis
