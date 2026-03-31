"""
Jaimini → Lal Kitab Bridge + Nakshatra Precision Layer
=======================================================
Antar Platform · March 31, 2026

Architecture:
  Jaimini says WHAT will manifest (career peak, marriage, health issue).
  Lal Kitab says WHY it might be obstructed and WHAT TO DO about it.
  Nakshatra says HOW the event will feel and whether timing is smooth or rough.

This module:
  1. Takes Jaimini event predictions from jaimini_data JSONB
  2. Maps each event's karaka planet to its LK house (Fixed Aries = House 1)
  3. Checks Pakka Ghar, sleeping, enemy, Rin status from lal_kitab_data
  4. Generates a specific correction remedy per event
  5. Adds Nakshatra quality overlay (sub-lord check, soul flavor)
  6. Outputs a JAIMINI→LK CORRECTION block for the Claude prompt

Integration:
  Called from /predict after the Jaimini block and LK block.
  In build_complete_context():
    context += jaimini_block          # Layer 2.5
    context += lk_block               # Layer 3
    context += bridge_block           # Layer 3.5 (this module)

File: antar_engine/jaimini_lk_bridge.py
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import date

logger = logging.getLogger("antar.bridge")

# =============================================================================
# CONSTANTS — Lal Kitab Fixed Aries Chart
# =============================================================================

# In LK, House 1 = always Aries, regardless of lagna
# To convert: LK house of a planet = (planet_sign_index) + 1
# Since Aries=0 in our 0-indexed system, LK house = sign_index + 1

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Pakka Ghar — each planet's permanent house in LK
PAKKA_GHAR = {
    "Sun": 1,       # House 1 (Aries)
    "Moon": 4,      # House 4 (Cancer)
    "Mars": 3,      # House 3 (Gemini) — also 8
    "Mercury": 7,   # House 7 (Libra)
    "Jupiter": 2,   # House 2 (Taurus) — also 5, 9
    "Venus": 7,     # House 7 (Libra)
    "Saturn": 8,    # House 8 (Scorpio) — also 10, 11
    "Rahu": 12,     # House 12 (Pisces)
    "Ketu": 6,      # House 6 (Virgo)
}

# Planetary friendships in LK (simplified)
LK_FRIENDS = {
    "Sun": ["Moon", "Mars", "Jupiter"],
    "Moon": ["Sun", "Mercury"],
    "Mars": ["Sun", "Moon", "Jupiter"],
    "Mercury": ["Sun", "Venus", "Rahu"],
    "Jupiter": ["Sun", "Moon", "Mars"],
    "Venus": ["Mercury", "Saturn", "Rahu"],
    "Saturn": ["Mercury", "Venus", "Rahu"],
    "Rahu": ["Mercury", "Venus", "Saturn"],
    "Ketu": ["Mars", "Jupiter"],
}

LK_ENEMIES = {
    "Sun": ["Saturn", "Rahu", "Ketu"],
    "Moon": ["Rahu", "Ketu"],
    "Mars": ["Mercury", "Rahu"],
    "Mercury": ["Moon", "Ketu"],
    "Jupiter": ["Mercury", "Venus", "Rahu"],
    "Venus": ["Sun", "Moon"],
    "Saturn": ["Sun", "Moon", "Mars"],
    "Rahu": ["Sun", "Moon", "Mars"],
    "Ketu": ["Moon", "Venus"],
}

# Planet → donation/remedy items (LK specific)
LK_REMEDIES = {
    "Sun": {"item": "wheat or jaggery", "day": "Sunday", "action": "Offer water to the rising sun", "metal": "copper"},
    "Moon": {"item": "rice or milk", "day": "Monday", "action": "Donate white cloth or silver to a woman", "metal": "silver"},
    "Mars": {"item": "red lentils (masoor dal)", "day": "Tuesday", "action": "Donate red lentils or feed sweet bread to dogs", "metal": "copper"},
    "Mercury": {"item": "green moong dal", "day": "Wednesday", "action": "Donate green items or feed green grass to cows", "metal": "bronze"},
    "Jupiter": {"item": "yellow sweets or turmeric", "day": "Thursday", "action": "Donate yellow sweets on Thursday. Respect teachers.", "metal": "gold"},
    "Venus": {"item": "white foods or camphor", "day": "Friday", "action": "Donate white items or perfume. Respect women.", "metal": "silver"},
    "Saturn": {"item": "mustard oil or black sesame", "day": "Saturday", "action": "Serve workers with respect. Donate oil on Saturdays.", "metal": "iron"},
    "Rahu": {"item": "coal or black blanket", "day": "Saturday", "action": "Donate coal to a sweeper or immerse coal in running water", "metal": "lead"},
    "Ketu": {"item": "sesame seeds or a two-toned blanket", "day": "Tuesday", "action": "Feed a stray dog. Donate blankets to the needy.", "metal": "iron"},
}

# Remedy placement based on Moving Lagna house position
REMEDY_PLACEMENT = {
    1: "Wear the remedy (ring, thread, or metal on the body)",
    2: "Keep the remedy item at home near the entrance",
    3: "Carry the item while traveling or commuting",
    4: "Immerse the remedy in running water (river, stream)",
    5: "Place at a temple, school, or place of learning",
    6: "Bury the item in the ground or donate to someone in need",
    7: "Gift the item to your spouse or business partner",
    8: "Immerse in still water or donate at a cremation ground",
    9: "Donate at a religious place or to a teacher/mentor",
    10: "Place at your workplace or donate to government workers",
    11: "Share with elder siblings or donate to a community center",
    12: "Immerse in flowing water at night or donate to a hospital",
}

# =============================================================================
# NAKSHATRA PRECISION LAYER
# =============================================================================

# 27 Nakshatras with their lords, quality, and soul flavor
NAKSHATRAS = {
    "Ashwini": {"lord": "Ketu", "quality": "swift", "flavor": "Healing and rapid transformation"},
    "Bharani": {"lord": "Venus", "quality": "fierce", "flavor": "Creation through destruction — birth pains"},
    "Krittika": {"lord": "Sun", "quality": "mixed", "flavor": "Purification through fire — cutting truth"},
    "Rohini": {"lord": "Moon", "quality": "soft", "flavor": "Growth, beauty, and material abundance"},
    "Mrigashira": {"lord": "Mars", "quality": "soft", "flavor": "Seeking and searching — the eternal quest"},
    "Ardra": {"lord": "Rahu", "quality": "fierce", "flavor": "Storms that clear the path forward"},
    "Punarvasu": {"lord": "Jupiter", "quality": "movable", "flavor": "Return to wisdom — recovery and renewal"},
    "Pushya": {"lord": "Saturn", "quality": "light", "flavor": "Nourishment and unconditional support"},
    "Ashlesha": {"lord": "Mercury", "quality": "sharp", "flavor": "Kundalini energy — deep psychological insight"},
    "Magha": {"lord": "Ketu", "quality": "fierce", "flavor": "Royal lineage and ancestral power"},
    "Purva Phalguni": {"lord": "Venus", "quality": "fierce", "flavor": "Pleasure, creativity, and relaxation"},
    "Uttara Phalguni": {"lord": "Sun", "quality": "fixed", "flavor": "Patronage, contracts, and agreements"},
    "Hasta": {"lord": "Moon", "quality": "light", "flavor": "Skill, craftsmanship, and clever hands"},
    "Chitra": {"lord": "Mars", "quality": "soft", "flavor": "Architecture and brilliant design"},
    "Swati": {"lord": "Rahu", "quality": "movable", "flavor": "Independence and self-driven movement"},
    "Vishakha": {"lord": "Jupiter", "quality": "mixed", "flavor": "Single-pointed determination — the goal-setter"},
    "Anuradha": {"lord": "Saturn", "quality": "soft", "flavor": "Devotion, loyalty, and deep friendship"},
    "Jyeshtha": {"lord": "Mercury", "quality": "sharp", "flavor": "Seniority, authority, and protective power"},
    "Mula": {"lord": "Ketu", "quality": "fierce", "flavor": "Root destruction to rebuild from truth"},
    "Purva Ashadha": {"lord": "Venus", "quality": "fierce", "flavor": "Invincibility and undefeatable will"},
    "Uttara Ashadha": {"lord": "Sun", "quality": "fixed", "flavor": "Final victory through sustained effort"},
    "Shravana": {"lord": "Moon", "quality": "movable", "flavor": "Listening, learning, and connection through knowledge"},
    "Dhanishta": {"lord": "Mars", "quality": "movable", "flavor": "Wealth through rhythm and group dynamics"},
    "Shatabhisha": {"lord": "Rahu", "quality": "movable", "flavor": "Healing through solitude and cosmic insight"},
    "Purva Bhadrapada": {"lord": "Jupiter", "quality": "fierce", "flavor": "Scorching intensity that transforms"},
    "Uttara Bhadrapada": {"lord": "Saturn", "quality": "fixed", "flavor": "Deep wisdom earned through patience"},
    "Revati": {"lord": "Mercury", "quality": "soft", "flavor": "Journey completion — liberation and healing"},
}

# Quality → timing modifier
NAKSHATRA_TIMING_QUALITY = {
    "swift": "Events arrive suddenly with little warning. Act fast.",
    "soft": "Events unfold gently. Natural flow — do not force.",
    "fierce": "Events arrive through disruption or intensity. Stay grounded.",
    "mixed": "Mixed results — some doors open, others close simultaneously.",
    "sharp": "Precise, surgical events. Details matter more than usual.",
    "movable": "Fluid period. Relocations, travel, and changes are favored.",
    "light": "Light, easy period. Opportunities arrive without effort.",
    "fixed": "Slow, permanent results. What you build now stays.",
}


def get_nakshatra_quality(nakshatra_name: str) -> Dict[str, str]:
    """Get the nakshatra's lord, quality, and soul flavor."""
    nak = NAKSHATRAS.get(nakshatra_name, {})
    if not nak:
        # Try partial match
        for name, data in NAKSHATRAS.items():
            if name.lower() in nakshatra_name.lower() or nakshatra_name.lower() in name.lower():
                return data
    return nak or {"lord": "unknown", "quality": "mixed", "flavor": ""}


def get_sublord_check(dasha_planet: str, nakshatra_name: str) -> Dict[str, Any]:
    """
    Check if the dasha planet's nakshatra lord supports or obstructs.
    The nakshatra lord is the "sub-lord" that modifies the dasha planet's effects.

    If sub-lord is a friend of the dasha planet → smooth manifestation
    If sub-lord is an enemy → obstructed, needs remedy
    """
    nak = get_nakshatra_quality(nakshatra_name)
    sub_lord = nak.get("lord", "")

    if not sub_lord or sub_lord == "unknown":
        return {"status": "unknown", "sub_lord": "", "detail": ""}

    friends = LK_FRIENDS.get(dasha_planet, [])
    enemies = LK_ENEMIES.get(dasha_planet, [])

    # A planet is always friendly with itself
    if sub_lord == dasha_planet:
        return {
            "status": "supportive",
            "sub_lord": sub_lord,
            "detail": f"{sub_lord} (nakshatra lord) is the same as {dasha_planet} — self-reinforcing, strong period"
        }

    if sub_lord in friends:
        return {
            "status": "supportive",
            "sub_lord": sub_lord,
            "detail": f"{sub_lord} (nakshatra lord) is a friend of {dasha_planet} — smooth manifestation expected"
        }
    elif sub_lord in enemies:
        return {
            "status": "obstructed",
            "sub_lord": sub_lord,
            "detail": f"{sub_lord} (nakshatra lord) is an enemy of {dasha_planet} — requires correction"
        }
    else:
        return {
            "status": "neutral",
            "sub_lord": sub_lord,
            "detail": f"{sub_lord} (nakshatra lord) is neutral to {dasha_planet}"
        }


# =============================================================================
# THE BRIDGE: Jaimini Event → LK Correction
# =============================================================================

def _planet_to_lk_house(sign_index: int) -> int:
    """Convert planet's sign index (0-11) to LK house (1-12). Fixed Aries = House 1."""
    return sign_index + 1


def _is_in_pakka_ghar(planet: str, lk_house: int) -> bool:
    """Check if planet is in its Pakka Ghar (permanent house)."""
    return PAKKA_GHAR.get(planet, 0) == lk_house


def _check_sleeping(planet: str, lk_house: int) -> bool:
    """
    LK Sleeping Planet rule: planet in houses 6, 8, or 12 with no
    benefic support is considered 'sleeping' (blocked).
    Simplified check: dusthana houses = sleeping risk.
    """
    return lk_house in [6, 8, 12]


def _check_enemy_house(planet: str, lk_house: int) -> bool:
    """Check if the planet is in a house ruled by its enemy."""
    # House lord in LK (Fixed Aries chart) = sign lord of that house index
    HOUSE_LORDS = {
        1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon",
        5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars",
        9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"
    }
    house_lord = HOUSE_LORDS.get(lk_house, "")
    enemies = LK_ENEMIES.get(planet, [])
    return house_lord in enemies


def generate_bridge_correction(
    jaimini_predictions: List[Dict],
    karakas: List[Dict],
    lal_kitab_data: Dict,
    moon_nakshatra: str = "",
    current_dasha_planet: str = "",
    lagna_sign: str = "",
) -> str:
    """
    Main bridge function. Takes Jaimini predictions + LK data,
    generates the CORRECTION block for the Claude prompt.

    Args:
        jaimini_predictions: list of event dicts from jaimini_data["predictions"]
        karakas: list of karaka dicts from jaimini_data["karakas"]
        lal_kitab_data: stored lal_kitab_data JSONB from charts table
        moon_nakshatra: user's birth nakshatra (for quality overlay)
        current_dasha_planet: current Vimsottari MD planet name
        lagna_sign: birth lagna sign name

    Returns:
        Formatted string block for the /predict system prompt
    """
    if not jaimini_predictions and not karakas:
        return ""

    lines = []
    lines.append("")
    lines.append("═══ JAIMINI → LAL KITAB CORRECTION ═══")
    lines.append("")

    # Build karaka map: code → {planet, sign, sign_name}
    karaka_map = {}
    for k in karakas:
        karaka_map[k.get("karaka", "")] = k

    # ── Process each Jaimini event prediction ──
    corrections_found = 0

    for pred in jaimini_predictions:
        event_type = pred.get("event_type", "")
        confidence = pred.get("confidence", "medium")
        description = pred.get("description", "")
        karaka_code = pred.get("karaka", "")

        # Find the karaka planet for this event
        karaka = karaka_map.get(karaka_code, {})
        planet = karaka.get("planet", "")
        sign_idx = karaka.get("sign")

        if not planet or sign_idx is None:
            continue

        lk_house = _planet_to_lk_house(sign_idx)
        in_pakka = _is_in_pakka_ghar(planet, lk_house)
        is_sleeping = _check_sleeping(planet, lk_house)
        is_enemy = _check_enemy_house(planet, lk_house)

        # Get remedy
        remedy = LK_REMEDIES.get(planet, {})

        # Build the correction entry
        lines.append(f"EVENT: {event_type.upper()} [{confidence.upper()}]")
        lines.append(f"  Trigger: {description}")
        lines.append(f"  Karaka: {karaka_code} = {planet} in LK House {lk_house}")

        if in_pakka:
            lines.append(f"  Pakka Ghar: YES — {planet} is in its permanent house. Maximum strength. No correction needed.")
        elif is_sleeping:
            lines.append(f"  STATUS: SLEEPING — {planet} is in house {lk_house} (dusthana). Wisdom/energy blocked.")
            lines.append(f"  AWAKENING: {remedy.get('action', 'Perform the appropriate remedy.')}")
            lines.append(f"  Practice: {remedy.get('item', '')} on {remedy.get('day', '')}.")
            corrections_found += 1
        elif is_enemy:
            lines.append(f"  STATUS: ENEMY HOUSE — {planet} is weakened in house {lk_house}.")
            lines.append(f"  CORRECTION: {remedy.get('action', 'Perform the appropriate remedy.')}")
            lines.append(f"  Practice: Donate {remedy.get('item', '')} on {remedy.get('day', '')}.")
            corrections_found += 1
        else:
            lines.append(f"  STATUS: NEUTRAL — {planet} in house {lk_house}. No major obstruction.")
            lines.append(f"  BOOSTER: To strengthen, {remedy.get('action', '')}")

        lines.append("")

    # ── Nakshatra Quality Overlay ──
    if moon_nakshatra:
        nak_data = get_nakshatra_quality(moon_nakshatra)
        if nak_data:
            lines.append("NAKSHATRA PRECISION:")
            quality = nak_data.get("quality", "mixed")
            flavor = nak_data.get("flavor", "")
            timing_note = NAKSHATRA_TIMING_QUALITY.get(quality, "")

            lines.append(f"  Birth Nakshatra: {moon_nakshatra}")
            lines.append(f"  Quality: {quality.upper()}")
            lines.append(f"  Soul Flavor: {flavor}")
            if timing_note:
                lines.append(f"  Timing: {timing_note}")

    # ── Sub-Lord Check on current dasha planet ──
    if current_dasha_planet and moon_nakshatra:
        sublord = get_sublord_check(current_dasha_planet, moon_nakshatra)
        if sublord.get("status") != "unknown":
            lines.append(f"  Sub-Lord Check: {sublord['detail']}")
            if sublord["status"] == "obstructed":
                enemy_remedy = LK_REMEDIES.get(sublord["sub_lord"], {})
                if enemy_remedy:
                    lines.append(f"  Sub-Lord Correction: {enemy_remedy.get('action', '')}")

    # ── AK Nakshatra Soul Purpose ──
    ak = karaka_map.get("AK", {})
    if ak:
        # If we had the AK's nakshatra in D9, we'd use it here
        # For now, use the AK planet's general soul purpose from Karakamsa
        ak_planet = ak.get("planet", "")
        if ak_planet:
            lines.append("")
            lines.append("SOUL PURPOSE OVERLAY:")
            lines.append(f"  Atmakaraka: {ak_planet}")
            # The AK planet's karmic lesson
            ak_lessons = {
                "Sun": "Learning humility. The soul must serve, not just lead.",
                "Moon": "Learning emotional detachment. The soul must observe without absorbing.",
                "Mars": "Learning patience. The soul must wait before acting.",
                "Mercury": "Learning truth over cleverness. The soul must simplify.",
                "Jupiter": "Learning to receive, not just teach. The soul must be a student.",
                "Venus": "Learning renunciation. The soul must let go of attachment to beauty.",
                "Saturn": "Learning to accept help. The soul must stop carrying everything alone.",
            }
            lesson = ak_lessons.get(ak_planet, "")
            if lesson:
                lines.append(f"  Karmic Lesson: {lesson}")

    # ── 35-Year LK Cycle Check ──
    # Compare LK cycle planet with Jaimini sign lord
    # If friends → prediction manifests 2x faster
    if lal_kitab_data:
        year_lord = ""
        if isinstance(lal_kitab_data, str):
            try:
                lal_kitab_data = json.loads(lal_kitab_data)
            except (json.JSONDecodeError, TypeError):
                lal_kitab_data = {}
        year_lord = lal_kitab_data.get("year_lord", "")

        if year_lord and jaimini_predictions:
            first_pred = jaimini_predictions[0]
            # Get the Jaimini dasha lord from the event
            # The karaka planet is the event trigger, but the sign lord matters for LK friendship
            karaka_planet = karaka_map.get(first_pred.get("karaka", ""), {}).get("planet", "")
            if karaka_planet and year_lord:
                friends = LK_FRIENDS.get(year_lord, [])
                if karaka_planet in friends:
                    lines.append("")
                    lines.append(f"LK CYCLE ACCELERATION: Year lord {year_lord} is friends with {karaka_planet}.")
                    lines.append(f"  This means Jaimini-predicted events manifest FASTER this year.")
                elif karaka_planet in LK_ENEMIES.get(year_lord, []):
                    lines.append("")
                    lines.append(f"LK CYCLE FRICTION: Year lord {year_lord} conflicts with {karaka_planet}.")
                    lines.append(f"  Predicted events may face delays. Apply the correction remedy above.")

    # ── Summary ──
    if corrections_found > 0:
        lines.append("")
        lines.append(f"TOTAL CORRECTIONS NEEDED: {corrections_found}")
        lines.append("Apply the most urgent correction first. One remedy at a time.")
    else:
        lines.append("")
        lines.append("NO CORRECTIONS NEEDED: All event karakas are well-placed in the LK chart.")

    lines.append("")
    lines.append("═══ END JAIMINI → LK CORRECTION ═══")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# HOT PATH — Called from /predict after Jaimini + LK blocks
# =============================================================================

def format_bridge_from_stored(chart_data: Dict[str, Any]) -> str:
    """
    HOT PATH: Read stored jaimini_data + lal_kitab_data from chart row,
    generate the bridge correction block.

    Args:
        chart_data: Full chart row from Supabase

    Returns:
        Formatted string block for the /predict system prompt.
        Empty string if data is missing (graceful degradation).
    """
    jaimini_data = chart_data.get("jaimini_data", {})
    lal_kitab_data = chart_data.get("lal_kitab_data", {})

    if isinstance(jaimini_data, str):
        try:
            jaimini_data = json.loads(jaimini_data)
        except (json.JSONDecodeError, TypeError):
            return ""

    if isinstance(lal_kitab_data, str):
        try:
            lal_kitab_data = json.loads(lal_kitab_data)
        except (json.JSONDecodeError, TypeError):
            lal_kitab_data = {}

    predictions = jaimini_data.get("predictions", [])
    karakas = jaimini_data.get("karakas", [])

    if not predictions and not karakas:
        return ""

    moon_nakshatra = chart_data.get("moon_nakshatra", "")
    current_dasha = chart_data.get("current_dasha", "")
    lagna_sign = chart_data.get("lagna_sign", "")

    # Extract dasha planet from "Mars-Moon" format
    dasha_planet = current_dasha.split("-")[0].strip() if current_dasha else ""

    try:
        return generate_bridge_correction(
            jaimini_predictions=predictions,
            karakas=karakas,
            lal_kitab_data=lal_kitab_data,
            moon_nakshatra=moon_nakshatra,
            current_dasha_planet=dasha_planet,
            lagna_sign=lagna_sign,
        )
    except Exception as e:
        logger.error(f"Bridge generation failed: {e}")
        return ""


# =============================================================================
# MAIN.PY WIRING
# =============================================================================

"""
In build_complete_context() or the /predict endpoint, after the Jaimini block
and the LK block, add:

    # --- LAYER 3.5: JAIMINI → LK BRIDGE ---
    from antar_engine.jaimini_lk_bridge import format_bridge_from_stored
    bridge_block = format_bridge_from_stored(chart_data)
    if bridge_block:
        context += bridge_block
"""
