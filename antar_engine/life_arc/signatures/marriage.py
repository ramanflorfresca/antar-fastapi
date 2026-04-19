"""
Marriage Signature v0.1 — Surface B: Life Arc
===============================================
STUB: conditions are classical defaults, not validated.
Will be rewritten once dataset (N=15 first-marriage charts) is available.

Event definition: first marriage / formal committed partnership.

Stub natal conditions:
  - 7L (partnership) dignified or well-placed
  - Venus not debilitated (love/partnership karaka)
  - No severe 7H affliction (Mars/Saturn/Rahu stacked)

Stub dasha conditions:
  - MD or AD lord rules 7H, 2H, or 11H
  - OR Venus/Jupiter MD/AD (classical marriage signifiers)

Stub transit conditions:
  - Jupiter transits 7H from natal Lagna or Moon
  - OR Jupiter aspects 7H

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any

SIGNATURE_METADATA = {
    "name": "marriage",
    "version": "0.1",
    "event_label": "Marriage or committed partnership",
    "confidence": "INDICATIVE",  # Not yet validated
    "positive_sample_size": 0,
    "positive_rate": None,
    "false_positive_rate": None,
    "last_validated": None,
    "enabled_in_library": False,  # DISABLED until validated
    "sources": ["Stub — awaiting dataset"],
    "notes": "STUB: conditions are classical defaults, not validated. "
             "Will be rewritten once Raman supplies N=15 first-marriage chart dataset.",
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


def _get_house_lord(house_num: int, lagna_sign_idx: int) -> str:
    sign_idx = (lagna_sign_idx + house_num - 1) % 12
    return SIGN_LORDS[sign_idx]


def _is_dignified(planet_name: str, sign_idx: int) -> bool:
    if sign_idx == EXALTATION.get(planet_name, -99):
        return True
    if sign_idx in OWN_SIGNS.get(planet_name, []):
        return True
    return False


def _is_debilitated(planet_name: str, sign_idx: int) -> bool:
    return sign_idx == DEBILITATION.get(planet_name, -99)


# ─── NATAL CONDITIONS ───────────────────────────────────────────────────────

def check_natal_conditions(chart_data: dict) -> dict:
    """
    Stub natal check for marriage potential:
    - 7L dignified or well-placed (kendra/trikona)
    - Venus not debilitated
    - No severe 7H affliction (Mars + Saturn + Rahu all in 7H)
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # 7L check
    lord_7 = _get_house_lord(7, lagna_idx)
    lord_7_data = planets.get(lord_7, {})
    lord_7_sign = lord_7_data.get("sign_index", -1) if lord_7_data else -1
    lord_7_house = (lord_7_sign - lagna_idx + 12) % 12 + 1 if lord_7_sign >= 0 else 0
    lord_7_good = (
        _is_dignified(lord_7, lord_7_sign) or
        lord_7_house in {1, 4, 5, 7, 9, 10}
    )

    # Venus not debilitated
    venus_data = planets.get("Venus", {})
    venus_sign = venus_data.get("sign_index", -1) if venus_data else -1
    venus_ok = not _is_debilitated("Venus", venus_sign)

    # 7H affliction check — Mars/Saturn/Rahu all in 7H is severe
    affliction_count = 0
    for malefic in ["Mars", "Saturn", "Rahu"]:
        pdata = planets.get(malefic, {})
        if not pdata:
            continue
        p_sign = pdata.get("sign_index", -1)
        if p_sign < 0:
            continue
        p_house = (p_sign - lagna_idx + 12) % 12 + 1
        if p_house == 7:
            affliction_count += 1
    severe_affliction = affliction_count >= 2  # 2+ malefics in 7H = severe

    fires = lord_7_good and venus_ok and not severe_affliction

    detail = []
    if lord_7_good:
        detail.append(f"7L ({lord_7}) dignified or well-placed in H{lord_7_house}")
    else:
        detail.append(f"7L ({lord_7}) not well-placed")
    if not venus_ok:
        detail.append("Venus debilitated (partnership karaka weakened)")
    if severe_affliction:
        detail.append(f"Severe 7H affliction ({affliction_count} malefics in 7H)")

    return {
        "fires": fires,
        "score": sum([lord_7_good, venus_ok, not severe_affliction]),
        "max_score": 3,
        "detail": detail,
        "downfall_marker": severe_affliction,
    }


# ─── DASHA CONDITIONS ───────────────────────────────────────────────────────

def check_dasha_conditions(chart_data: dict, md_lord: str, ad_lord: str) -> dict:
    """
    Stub dasha check for marriage:
    - MD or AD lord rules 7H, 2H, or 11H
    - OR Venus or Jupiter MD/AD (classical marriage signifiers)
    """
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    marriage_houses = {2, 7, 11}
    marriage_lords = set()
    for h in marriage_houses:
        marriage_lords.add(_get_house_lord(h, lagna_idx))

    md_rules_marriage = md_lord in marriage_lords
    ad_rules_marriage = ad_lord in marriage_lords

    # Venus/Jupiter as natural marriage significators
    md_is_signifier = md_lord in ("Venus", "Jupiter")
    ad_is_signifier = ad_lord in ("Venus", "Jupiter")

    fires = md_rules_marriage or ad_rules_marriage or md_is_signifier or ad_is_signifier

    detail = []
    if md_rules_marriage:
        detail.append(f"MD lord ({md_lord}) rules marriage house (2/7/11)")
    if ad_rules_marriage:
        detail.append(f"AD lord ({ad_lord}) rules marriage house (2/7/11)")
    if md_is_signifier:
        detail.append(f"MD lord is {md_lord} (natural marriage significator)")
    if ad_is_signifier:
        detail.append(f"AD lord is {ad_lord} (natural marriage significator)")
    if not fires:
        detail.append("Dasha lords do not activate marriage axis")

    return {
        "fires": fires,
        "detail": detail,
    }


# ─── TRANSIT CONDITIONS ─────────────────────────────────────────────────────

def check_transit_conditions(chart_data: dict, transit_positions: dict) -> dict:
    """
    Stub transit check for marriage:
    - Jupiter transits 7H from natal Lagna or Moon
    - OR Jupiter aspects 7H (from 1H via 7th aspect, or from 3H/11H via special)
    """
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)
    moon_idx = chart_data.get("planets", {}).get("Moon", {}).get("sign_index", 0)

    jupiter_sign = transit_positions.get("Jupiter", {}).get("sign_index", -1)

    jup_house_lagna = (jupiter_sign - lagna_idx + 12) % 12 + 1 if jupiter_sign >= 0 else 0
    jup_house_moon = (jupiter_sign - moon_idx + 12) % 12 + 1 if jupiter_sign >= 0 else 0

    jup_in_7_lagna = jup_house_lagna == 7
    jup_in_7_moon = jup_house_moon == 7

    # Jupiter aspects 7H from: 1H (7th aspect), 3H (5th aspect), 11H (9th aspect)
    jup_aspects_7 = jup_house_lagna in {1, 3, 11}

    fires = jup_in_7_lagna or jup_in_7_moon or jup_aspects_7

    detail = []
    if jup_in_7_lagna:
        detail.append("Jupiter transits 7H from Lagna (partnership expansion)")
    if jup_in_7_moon:
        detail.append("Jupiter transits 7H from Moon (emotional partnership readiness)")
    if jup_aspects_7:
        detail.append(f"Jupiter in H{jup_house_lagna} aspects 7H (partnership support)")
    if not fires:
        detail.append("No supportive partnership transits active")

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
    """Full marriage signature check."""
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
        missing.append("Natal partnership potential not strong enough")
    if not dasha["fires"]:
        missing.append("Dasha lords do not activate marriage axis")
    if not transit["fires"]:
        missing.append("No supportive partnership transits active")
    return missing
