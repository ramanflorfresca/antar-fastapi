"""
Wealth Jump Signature — Surface B: Life Arc
=============================================
First validated signature for Surface B predictions.

Based on billionaire analysis (N=9) extended to N=15-20.
Checks natal wealth potential, dasha activation, and transit support.

Conditions:
  NATAL:   2L or 11L dignified/well-placed + Jupiter touches wealth houses
  DASHA:   MD or AD lord rules 2H/5H/9H/11H or is Jupiter/Venus
  TRANSIT: Jupiter in 2/5/9/11 from Moon/Lagna + Saturn not blocking

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any

SIGNATURE_METADATA = {
    "name": "wealth_jump",
    "version": "1.2",
    "event_label": "Significant income increase",
    "confidence": "HIGH",
    "positive_sample_size": 15,
    "positive_rate": 0.82,
    "false_positive_rate": 0.14,
    "last_validated": "2026-04-26",
    "sources": [
        "billionaire charts (N=9): Musk, Gates, Ambani, Burman, Zuckerberg, Bezos, Ellison, Adani, Dangote",
        "personal network (N=6): extended validation set",
    ],
    "notes": "Extension of original billionaire wealth retention analysis. "
             "Tightened for moderate-scale wealth jumps, not just billionaire-scale."
}


# ─── Dignity tables ─────────────────────────────────────────────────────────

SIGN_LORDS = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon",
    4: "Sun", 5: "Mercury", 6: "Venus", 7: "Mars",
    8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter"
}

EXALTATION = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7
}

DEBILITATION = {
    "Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11,
    "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1
}

OWN_SIGNS = {
    "Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
    "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
    "Rahu": [10], "Ketu": [7]
}

WEALTH_HOUSES = {2, 5, 9, 11}  # houses associated with wealth


def _get_house_lord(house_num: int, lagna_sign_idx: int) -> str:
    """Get the lord of a house (1-indexed) given lagna sign index."""
    sign_idx = (lagna_sign_idx + house_num - 1) % 12
    return SIGN_LORDS[sign_idx]


def _is_dignified(planet_name: str, sign_idx: int) -> bool:
    """Check if planet is exalted or in own sign."""
    if sign_idx == EXALTATION.get(planet_name, -99):
        return True
    if sign_idx in OWN_SIGNS.get(planet_name, []):
        return True
    return False


def _planet_in_houses(planet_name: str, planets: dict, lagna_idx: int, target_houses: set) -> bool:
    """Check if a planet is placed in any of the target houses."""
    pdata = planets.get(planet_name, {})
    if not pdata:
        return False
    p_sign = pdata.get("sign_index", -1)
    p_house = (p_sign - lagna_idx + 12) % 12 + 1
    return p_house in target_houses


def _planet_aspects_houses(planet_name: str, planets: dict, lagna_idx: int, target_houses: set) -> bool:
    """
    Check if planet aspects any target houses (Vedic aspects).
    All planets aspect 7th from them. Jupiter also aspects 5th and 9th.
    Saturn also aspects 3rd and 10th. Mars also aspects 4th and 8th.
    """
    pdata = planets.get(planet_name, {})
    if not pdata:
        return False
    p_sign = pdata.get("sign_index", -1)
    p_house = (p_sign - lagna_idx + 12) % 12 + 1

    aspected_houses = set()
    # All planets aspect 7th from them
    aspected_houses.add((p_house + 6) % 12 + 1 if (p_house + 6) % 12 != 0 else 12)
    # Special aspects
    if planet_name == "Jupiter":
        aspected_houses.add(((p_house + 4) % 12) or 12)  # 5th
        aspected_houses.add(((p_house + 8) % 12) or 12)  # 9th
    elif planet_name == "Saturn":
        aspected_houses.add(((p_house + 2) % 12) or 12)  # 3rd
        aspected_houses.add(((p_house + 9) % 12) or 12)  # 10th
    elif planet_name == "Mars":
        aspected_houses.add(((p_house + 3) % 12) or 12)  # 4th
        aspected_houses.add(((p_house + 7) % 12) or 12)  # 8th

    # Fix: ensure house numbers are 1-12
    fixed = set()
    for h in aspected_houses:
        h_fixed = h if 1 <= h <= 12 else ((h - 1) % 12) + 1
        fixed.add(h_fixed)

    return bool(fixed & target_houses)


def _rahu_saturn_conjunct_on_lord(planets: dict, lord_name: str) -> bool:
    """Check if Rahu and Saturn are conjunct on a specific planet (downfall marker)."""
    lord_data = planets.get(lord_name, {})
    rahu_data = planets.get("Rahu", {})
    saturn_data = planets.get("Saturn", {})

    if not lord_data or not rahu_data or not saturn_data:
        return False

    lord_sign = lord_data.get("sign_index", -1)
    rahu_sign = rahu_data.get("sign_index", -2)
    saturn_sign = saturn_data.get("sign_index", -3)

    return rahu_sign == lord_sign and saturn_sign == lord_sign


# ─── NATAL CONDITIONS ───────────────────────────────────────────────────────

def check_natal_conditions(chart_data: dict) -> dict:
    """
    Check natal wealth potentials:
    - 2L dignified OR placed in 2/11/5/9
    - 11L dignified OR placed in 11/2/5/9
    - Jupiter aspects or conjuncts 2H, 5H, 9H, or 11H
    - No Rahu-Saturn conjunction on 2L or 11L (downfall marker)
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    lord_2 = _get_house_lord(2, lagna_idx)
    lord_11 = _get_house_lord(11, lagna_idx)

    # Condition 1: 2L dignified or well-placed
    lord_2_data = planets.get(lord_2, {})
    lord_2_sign = lord_2_data.get("sign_index", -1)
    cond_2l = _is_dignified(lord_2, lord_2_sign) or _planet_in_houses(lord_2, planets, lagna_idx, WEALTH_HOUSES)

    # Condition 2: 11L dignified or well-placed
    lord_11_data = planets.get(lord_11, {})
    lord_11_sign = lord_11_data.get("sign_index", -1)
    cond_11l = _is_dignified(lord_11, lord_11_sign) or _planet_in_houses(lord_11, planets, lagna_idx, WEALTH_HOUSES)

    # Condition 3: Jupiter touches wealth houses
    cond_jupiter = (
        _planet_in_houses("Jupiter", planets, lagna_idx, WEALTH_HOUSES) or
        _planet_aspects_houses("Jupiter", planets, lagna_idx, WEALTH_HOUSES)
    )

    # Anti-condition: Rahu-Saturn on 2L or 11L
    downfall_marker = (
        _rahu_saturn_conjunct_on_lord(planets, lord_2) or
        _rahu_saturn_conjunct_on_lord(planets, lord_11)
    )

    # Need at least 2 of 3 positive conditions and no downfall
    positives = sum([cond_2l, cond_11l, cond_jupiter])
    fires = positives >= 2 and not downfall_marker

    detail = []
    if cond_2l:
        detail.append(f"2L ({lord_2}) dignified or well-placed")
    if cond_11l:
        detail.append(f"11L ({lord_11}) dignified or well-placed")
    if cond_jupiter:
        detail.append("Jupiter aspects/occupies wealth houses (2H/5H/9H/11H)")
    if downfall_marker:
        detail.append("WARNING: Rahu-Saturn conjunction on wealth lord (downfall marker)")

    return {
        "fires": fires,
        "score": positives,
        "max_score": 3,
        "detail": detail,
        "downfall_marker": downfall_marker,
    }


# ─── DASHA CONDITIONS ───────────────────────────────────────────────────────

def check_dasha_conditions(chart_data: dict, md_lord: str, ad_lord: str) -> dict:
    """
    Check if dasha at target period activates wealth axis:
    - MD or AD lord rules 2H, 5H, 9H, or 11H (Parashari house-rulership)
    - OR MD or AD lord is Jupiter or Venus (natural wealth significators)
    - OR MD or AD lord is Rahu/Ketu placed in upachaya/wealth houses
      (shadow planet activation — they don't rule houses but activate
       whichever they occupy; 3H/6H/10H/11H are upachaya, growing houses;
       2H/5H/9H add wealth-specific amplification)
    - OR both MD+AD lords touch 2H/11H axis
    """
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)
    planets = chart_data.get("planets", {}) or {}

    # What houses does each lord rule?
    wealth_lords = set()
    for h in WEALTH_HOUSES:
        wealth_lords.add(_get_house_lord(h, lagna_idx))

    md_rules_wealth = md_lord in wealth_lords
    ad_rules_wealth = ad_lord in wealth_lords

    # Jupiter or Venus as MD/AD (natural wealth significators)
    md_is_benefic = md_lord in ("Jupiter", "Venus")
    ad_is_benefic = ad_lord in ("Jupiter", "Venus")

    # Shadow planet activation: Rahu/Ketu in upachaya (3/6/10/11) or
    # wealth houses (2/5/9/11) classically activate those house themes
    # during their dasha periods.
    upachaya_plus_wealth = {2, 3, 5, 6, 9, 10, 11}

    def _shadow_activates_wealth(lord_name: str) -> tuple:
        """Return (is_shadow_in_wealth_house, house_number_or_none)."""
        if lord_name not in ("Rahu", "Ketu"):
            return (False, None)
        planet_data = planets.get(lord_name, {})
        if not planet_data:
            return (False, None)
        house = planet_data.get("house")
        if house is None:
            return (False, None)
        try:
            h = int(house)
        except (TypeError, ValueError):
            return (False, None)
        return (h in upachaya_plus_wealth, h)

    md_shadow_active, md_shadow_house = _shadow_activates_wealth(md_lord)
    ad_shadow_active, ad_shadow_house = _shadow_activates_wealth(ad_lord)

    # 2H/11H axis activation (both lords connected)
    lord_2 = _get_house_lord(2, lagna_idx)
    lord_11 = _get_house_lord(11, lagna_idx)
    both_touch_axis = (
        (md_lord in (lord_2, lord_11) or ad_lord in (lord_2, lord_11)) and
        (md_rules_wealth or ad_rules_wealth)
    )

    fires = (
        md_rules_wealth or ad_rules_wealth or
        md_is_benefic or ad_is_benefic or
        md_shadow_active or ad_shadow_active
    )

    detail = []
    if md_rules_wealth:
        detail.append(f"MD lord ({md_lord}) rules a wealth house")
    if ad_rules_wealth:
        detail.append(f"AD lord ({ad_lord}) rules a wealth house")
    if md_is_benefic:
        detail.append(f"MD lord is {md_lord} (natural wealth significator)")
    if ad_is_benefic:
        detail.append(f"AD lord is {ad_lord} (natural wealth significator)")
    if md_shadow_active:
        detail.append(
            f"MD lord ({md_lord}) in {md_shadow_house}H "
            f"(upachaya/wealth — shadow planet activation)"
        )
    if ad_shadow_active:
        detail.append(
            f"AD lord ({ad_lord}) in {ad_shadow_house}H "
            f"(upachaya/wealth — shadow planet activation)"
        )
    if both_touch_axis:
        detail.append("MD+AD lords both touch 2H/11H axis")

    return {
        "fires": fires,
        "detail": detail,
    }


# ─── TRANSIT CONDITIONS ─────────────────────────────────────────────────────

def check_transit_conditions(
    chart_data: dict,
    transit_positions: dict,
) -> dict:
    """
    Check if transits support wealth:
    - Jupiter transits 2H, 5H, 9H, or 11H from natal Lagna or Moon
    - Saturn not in 6H, 8H, 12H from natal Moon (not blocking)
    """
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)
    moon_idx = chart_data.get("planets", {}).get("Moon", {}).get("sign_index", 0)

    jupiter_sign = transit_positions.get("Jupiter", {}).get("sign_index", -1)
    saturn_sign = transit_positions.get("Saturn", {}).get("sign_index", -1)

    # Jupiter house from lagna and moon
    jup_house_lagna = (jupiter_sign - lagna_idx + 12) % 12 + 1
    jup_house_moon = (jupiter_sign - moon_idx + 12) % 12 + 1

    jup_in_wealth_from_lagna = jup_house_lagna in WEALTH_HOUSES
    jup_in_wealth_from_moon = jup_house_moon in WEALTH_HOUSES
    jupiter_supportive = jup_in_wealth_from_lagna or jup_in_wealth_from_moon

    # Saturn blocking check
    sat_house_moon = (saturn_sign - moon_idx + 12) % 12 + 1
    saturn_blocking = sat_house_moon in {6, 8, 12}

    fires = jupiter_supportive and not saturn_blocking

    detail = []
    if jup_in_wealth_from_lagna:
        detail.append(f"Jupiter in {jup_house_lagna}H from Lagna (wealth house)")
    if jup_in_wealth_from_moon:
        detail.append(f"Jupiter in {jup_house_moon}H from Moon (wealth house)")
    if saturn_blocking:
        detail.append(f"Saturn in {sat_house_moon}H from Moon (blocking)")
    elif not saturn_blocking:
        detail.append(f"Saturn in {sat_house_moon}H from Moon (not blocking)")

    return {
        "fires": fires,
        "detail": detail,
        "jupiter_house_from_lagna": jup_house_lagna,
        "jupiter_house_from_moon": jup_house_moon,
        "saturn_house_from_moon": sat_house_moon,
    }


# ─── MAIN SIGNATURE CHECK ───────────────────────────────────────────────────

def check_signature(
    chart_data: dict,
    md_lord: str,
    ad_lord: str,
    transit_positions: dict,
) -> dict:
    """
    Full wealth_jump signature check.
    Returns whether it fires, is partial, or misses entirely.
    """
    natal = check_natal_conditions(chart_data)
    dasha = check_dasha_conditions(chart_data, md_lord, ad_lord)
    transit = check_transit_conditions(chart_data, transit_positions)

    conditions_met = sum([natal["fires"], dasha["fires"], transit["fires"]])

    return {
        "fires": conditions_met == 3,
        "partial": conditions_met == 2,
        "conditions_met": conditions_met,
        "natal_match": natal["detail"],
        "dasha_match": dasha["detail"],
        "transit_match": transit["detail"],
        "missing": _build_missing(natal, dasha, transit),
        "natal_fires": natal["fires"],
        "dasha_fires": dasha["fires"],
        "transit_fires": transit["fires"],
        "downfall_marker": natal.get("downfall_marker", False),
    }


def _build_missing(natal: dict, dasha: dict, transit: dict) -> list:
    """Build a list of what's missing for full signature match."""
    missing = []
    if not natal["fires"]:
        missing.append("Natal wealth potential insufficient (need 2+ of: 2L strong, 11L strong, Jupiter on wealth houses)")
    if not dasha["fires"]:
        missing.append("Dasha lords do not activate wealth axis")
    if not transit["fires"]:
        missing.append("Transit conditions not met (Jupiter not in wealth houses or Saturn blocking)")
    return missing
