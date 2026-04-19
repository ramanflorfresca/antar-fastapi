"""
Job Change Signature v0.1 — Surface B: Life Arc
=================================================
STUB: conditions are classical defaults, not validated.
Will be rewritten once dataset (N=15 job-change charts) is available.

Event definition: voluntary lateral or upward job change,
same country, same industry.

Stub natal conditions:
  - 10L (career lord) dignified or in kendra/trikona
  - 6L (service/employment) not debilitated

Stub dasha conditions:
  - MD or AD lord activates 10H, 6H, or 11H
  - OR dasha shift (new MD/AD starting) within window

Stub transit conditions:
  - Saturn transits 10H or 10L from natal Lagna
  - OR Jupiter aspects 10H

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any

SIGNATURE_METADATA = {
    "name": "job_change",
    "version": "0.1",
    "event_label": "Job or career transition",
    "confidence": "INDICATIVE",  # Not yet validated
    "positive_sample_size": 0,
    "positive_rate": None,
    "false_positive_rate": None,
    "last_validated": None,
    "enabled_in_library": False,  # DISABLED until validated
    "sources": ["Stub — awaiting dataset"],
    "notes": "STUB: conditions are classical defaults, not validated. "
             "Will be rewritten once Raman supplies N=15 job-change chart dataset.",
}


# ─── Dignity tables (shared with wealth_jump) ──────────────────────────────

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
    Stub natal check for job change potential:
    - 10L (career lord) dignified or well-placed (kendra/trikona)
    - 6L (service/employment lord) not debilitated
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # 10L check
    lord_10 = _get_house_lord(10, lagna_idx)
    lord_10_data = planets.get(lord_10, {})
    lord_10_sign = lord_10_data.get("sign_index", -1) if lord_10_data else -1
    lord_10_house = (lord_10_sign - lagna_idx + 12) % 12 + 1 if lord_10_sign >= 0 else 0
    lord_10_good = (
        _is_dignified(lord_10, lord_10_sign) or
        lord_10_house in {1, 4, 5, 7, 9, 10}
    )

    # 6L not debilitated
    lord_6 = _get_house_lord(6, lagna_idx)
    lord_6_data = planets.get(lord_6, {})
    lord_6_sign = lord_6_data.get("sign_index", -1) if lord_6_data else -1
    lord_6_ok = not _is_debilitated(lord_6, lord_6_sign)

    fires = lord_10_good and lord_6_ok

    detail = []
    if lord_10_good:
        detail.append(f"10L ({lord_10}) dignified or well-placed in H{lord_10_house}")
    else:
        detail.append(f"10L ({lord_10}) not well-placed")
    if not lord_6_ok:
        detail.append(f"6L ({lord_6}) debilitated — employment instability")

    return {
        "fires": fires,
        "score": sum([lord_10_good, lord_6_ok]),
        "max_score": 2,
        "detail": detail,
        "downfall_marker": False,
    }


# ─── DASHA CONDITIONS ───────────────────────────────────────────────────────

def check_dasha_conditions(chart_data: dict, md_lord: str, ad_lord: str) -> dict:
    """
    Stub dasha check for job change:
    - MD or AD lord rules 10H, 6H, or 11H
    - OR dasha shift occurs within window (new MD/AD starting)
    """
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    career_houses = {6, 10, 11}
    career_lords = set()
    for h in career_houses:
        career_lords.add(_get_house_lord(h, lagna_idx))

    md_rules_career = md_lord in career_lords
    ad_rules_career = ad_lord in career_lords

    fires = md_rules_career or ad_rules_career

    detail = []
    if md_rules_career:
        detail.append(f"MD lord ({md_lord}) rules a career house (6/10/11)")
    if ad_rules_career:
        detail.append(f"AD lord ({ad_lord}) rules a career house (6/10/11)")
    if not fires:
        detail.append("Dasha lords do not activate career axis")

    return {
        "fires": fires,
        "detail": detail,
    }


# ─── TRANSIT CONDITIONS ─────────────────────────────────────────────────────

def check_transit_conditions(chart_data: dict, transit_positions: dict) -> dict:
    """
    Stub transit check for job change:
    - Saturn transits 10H from natal Lagna (restructuring career)
    - OR Jupiter aspects or occupies 10H from natal Lagna
    """
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    saturn_sign = transit_positions.get("Saturn", {}).get("sign_index", -1)
    jupiter_sign = transit_positions.get("Jupiter", {}).get("sign_index", -1)

    sat_house_lagna = (saturn_sign - lagna_idx + 12) % 12 + 1 if saturn_sign >= 0 else 0
    jup_house_lagna = (jupiter_sign - lagna_idx + 12) % 12 + 1 if jupiter_sign >= 0 else 0

    saturn_on_10 = sat_house_lagna == 10
    jupiter_on_10 = jup_house_lagna == 10

    # Jupiter aspects 10H (from 4H via 7th aspect, or from 2H/6H via special)
    jup_aspects_10 = jup_house_lagna in {4, 2, 6}  # 7th, 5th, 9th aspect to H10

    fires = saturn_on_10 or jupiter_on_10 or jup_aspects_10

    detail = []
    if saturn_on_10:
        detail.append("Saturn transits 10H from Lagna (career restructuring)")
    if jupiter_on_10:
        detail.append("Jupiter transits 10H from Lagna (career expansion)")
    if jup_aspects_10:
        detail.append(f"Jupiter in H{jup_house_lagna} aspects 10H (career support)")
    if not fires:
        detail.append("No significant career transits active")

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
    """Full job_change signature check."""
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
        missing.append("Natal career potential not strong enough")
    if not dasha["fires"]:
        missing.append("Dasha lords do not activate career axis")
    if not transit["fires"]:
        missing.append("No supportive career transits active")
    return missing
