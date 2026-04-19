"""
Wealth Loss Signature v0.1 — Surface B: Life Arc
==================================================
STUB: conditions are classical defaults, not validated.
Will be rewritten once dataset (N=15 financial-crisis charts) is available.

Event definition: sudden financial crisis, bankruptcy, or >50% wealth loss
within 12 months.

Stub natal conditions:
  - Rahu-Saturn conjunction on 2L or 11L (downfall marker)
  - 8L afflicting 2L/11L (8H = sudden transformation)

Stub dasha conditions:
  - MD or AD lord is 8L or 12L
  - OR MD/AD lord afflicts 2H or 11H

Stub transit conditions:
  - Saturn transits 2H or 2L
  - OR Jupiter absent from wealth houses
  - OR eclipse on 2H/11H axis within 30 days

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any

SIGNATURE_METADATA = {
    "name": "wealth_loss",
    "version": "0.1",
    "event_label": "Financial stress window",
    "confidence": "INDICATIVE",  # Not yet validated
    "positive_sample_size": 0,
    "positive_rate": None,
    "false_positive_rate": None,
    "last_validated": None,
    "enabled_in_library": False,  # DISABLED until validated
    "sources": ["Stub — awaiting dataset"],
    "notes": "STUB: conditions are classical defaults, not validated. "
             "Will be rewritten once Raman supplies N=15 financial-crisis chart dataset.",
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

WEALTH_HOUSES = {2, 5, 9, 11}


def _get_house_lord(house_num: int, lagna_sign_idx: int) -> str:
    sign_idx = (lagna_sign_idx + house_num - 1) % 12
    return SIGN_LORDS[sign_idx]


def _is_dignified(planet_name: str, sign_idx: int) -> bool:
    if sign_idx == EXALTATION.get(planet_name, -99):
        return True
    if sign_idx in OWN_SIGNS.get(planet_name, []):
        return True
    return False


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
    Stub natal check for wealth loss vulnerability:
    - Rahu-Saturn conjunction on 2L or 11L (downfall marker)
    - 8L in same sign as 2L or 11L (sudden transformation of wealth)
    - 12L in same sign as 2L or 11L (dissipation of wealth)
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    lord_2 = _get_house_lord(2, lagna_idx)
    lord_11 = _get_house_lord(11, lagna_idx)
    lord_8 = _get_house_lord(8, lagna_idx)
    lord_12 = _get_house_lord(12, lagna_idx)

    # Rahu-Saturn downfall marker
    downfall_2l = _rahu_saturn_conjunct_on_lord(planets, lord_2)
    downfall_11l = _rahu_saturn_conjunct_on_lord(planets, lord_11)
    has_downfall = downfall_2l or downfall_11l

    # 8L conjunct 2L or 11L (same sign)
    lord_8_sign = planets.get(lord_8, {}).get("sign_index", -1)
    lord_2_sign = planets.get(lord_2, {}).get("sign_index", -2)
    lord_11_sign = planets.get(lord_11, {}).get("sign_index", -3)
    affliction_8l = (
        (lord_8_sign >= 0 and lord_8_sign == lord_2_sign) or
        (lord_8_sign >= 0 and lord_8_sign == lord_11_sign)
    )

    # 12L conjunct 2L or 11L (same sign)
    lord_12_sign = planets.get(lord_12, {}).get("sign_index", -4)
    affliction_12l = (
        (lord_12_sign >= 0 and lord_12_sign == lord_2_sign) or
        (lord_12_sign >= 0 and lord_12_sign == lord_11_sign)
    )

    score = sum([has_downfall, affliction_8l, affliction_12l])
    fires = score >= 2  # need at least 2 vulnerability markers

    detail = []
    if has_downfall:
        detail.append(f"Rahu-Saturn conjunction on wealth lord ({'2L' if downfall_2l else '11L'})")
    if affliction_8l:
        detail.append(f"8L ({lord_8}) conjunct wealth lord (sudden transformation)")
    if affliction_12l:
        detail.append(f"12L ({lord_12}) conjunct wealth lord (dissipation)")
    if not detail:
        detail.append("No significant wealth-loss natal markers")

    return {
        "fires": fires,
        "score": score,
        "max_score": 3,
        "detail": detail,
        "downfall_marker": has_downfall,
    }


# ─── DASHA CONDITIONS ───────────────────────────────────────────────────────

def check_dasha_conditions(chart_data: dict, md_lord: str, ad_lord: str) -> dict:
    """
    Stub dasha check for wealth loss:
    - MD or AD lord is 8L or 12L (crisis/loss dasha lords)
    - OR MD or AD lord rules 2H/11H AND is debilitated (weak wealth activation)
    """
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)
    planets = chart_data.get("planets", {}) or {}

    lord_8 = _get_house_lord(8, lagna_idx)
    lord_12 = _get_house_lord(12, lagna_idx)
    lord_2 = _get_house_lord(2, lagna_idx)
    lord_11 = _get_house_lord(11, lagna_idx)

    # 8L or 12L dasha
    md_is_crisis = md_lord in (lord_8, lord_12)
    ad_is_crisis = ad_lord in (lord_8, lord_12)

    # Wealth lord in own dasha but debilitated
    md_data = planets.get(md_lord, {})
    md_sign = md_data.get("sign_index", -1) if md_data else -1
    ad_data = planets.get(ad_lord, {})
    ad_sign = ad_data.get("sign_index", -1) if ad_data else -1

    md_weak_wealth = (
        md_lord in (lord_2, lord_11) and
        md_sign == DEBILITATION.get(md_lord, -99)
    )
    ad_weak_wealth = (
        ad_lord in (lord_2, lord_11) and
        ad_sign == DEBILITATION.get(ad_lord, -99)
    )

    fires = md_is_crisis or ad_is_crisis or md_weak_wealth or ad_weak_wealth

    detail = []
    if md_is_crisis:
        detail.append(f"MD lord ({md_lord}) is {'8L' if md_lord == lord_8 else '12L'} (crisis lord)")
    if ad_is_crisis:
        detail.append(f"AD lord ({ad_lord}) is {'8L' if ad_lord == lord_8 else '12L'} (crisis lord)")
    if md_weak_wealth:
        detail.append(f"MD lord ({md_lord}) rules wealth but debilitated")
    if ad_weak_wealth:
        detail.append(f"AD lord ({ad_lord}) rules wealth but debilitated")
    if not fires:
        detail.append("Dasha lords do not activate crisis axis")

    return {
        "fires": fires,
        "detail": detail,
    }


# ─── TRANSIT CONDITIONS ─────────────────────────────────────────────────────

def check_transit_conditions(chart_data: dict, transit_positions: dict) -> dict:
    """
    Stub transit check for wealth loss:
    - Saturn transits 2H from natal Lagna (pressure on income)
    - OR Jupiter NOT in any wealth house from Lagna or Moon (no protection)
    """
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)
    moon_idx = chart_data.get("planets", {}).get("Moon", {}).get("sign_index", 0)

    saturn_sign = transit_positions.get("Saturn", {}).get("sign_index", -1)
    jupiter_sign = transit_positions.get("Jupiter", {}).get("sign_index", -1)

    # Saturn on 2H from Lagna
    sat_house_lagna = (saturn_sign - lagna_idx + 12) % 12 + 1 if saturn_sign >= 0 else 0
    saturn_pressure = sat_house_lagna == 2

    # Jupiter NOT protecting wealth houses
    jup_house_lagna = (jupiter_sign - lagna_idx + 12) % 12 + 1 if jupiter_sign >= 0 else 0
    jup_house_moon = (jupiter_sign - moon_idx + 12) % 12 + 1 if jupiter_sign >= 0 else 0
    jupiter_absent = (
        jup_house_lagna not in WEALTH_HOUSES and
        jup_house_moon not in WEALTH_HOUSES
    )

    fires = saturn_pressure or jupiter_absent

    detail = []
    if saturn_pressure:
        detail.append("Saturn transits 2H from Lagna (income pressure)")
    if jupiter_absent:
        detail.append(f"Jupiter in H{jup_house_lagna}/H{jup_house_moon} (not protecting wealth houses)")
    if not fires:
        detail.append("No significant wealth-stress transits active")

    return {
        "fires": fires,
        "detail": detail,
    }


# ─── MAIN SIGNATURE CHECK ─────────────────────────────────────────────────

def check_signature(
    chart_data: dict,
    md_lord: str,
    ad_lord: str,
    transit_positions: dict,
) -> dict:
    """Full wealth_loss signature check."""
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
    missing = []
    if not natal["fires"]:
        missing.append("Natal wealth-loss vulnerability not detected")
    if not dasha["fires"]:
        missing.append("Dasha lords do not activate crisis axis")
    if not transit["fires"]:
        missing.append("No significant wealth-stress transits active")
    return missing
