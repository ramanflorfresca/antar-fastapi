"""
Venture Timing Signature v1.0 — Surface B: Life Arc
=====================================================
Given a chart running a venture in a fit business category,
identifies optimal launch, scale, caution, and exit windows
within the dasha calendar.

Uses Vimsottari MD/AD periods, Sade Sati status, and transit
overlay to classify timing windows.

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any


# ─── METADATA ────────────────────────────────────────────────────────────────

SIGNATURE_METADATA = {
    "name": "venture_timing",
    "version": "1.0",
    "event_label": "Venture launch/scale/exit timing",
    "confidence": "MEDIUM",
    "positive_sample_size": 2,
    "positive_rate": None,
    "false_positive_rate": None,
    "last_validated": "2026-04-19",
    "enabled_in_library": False,
    "sources": [
        "Retrodiction: Raman (Capricorn rising), Andres (Cancer rising)",
        "Classical Vimsottari dasha + transit timing principles",
    ],
    "notes": "Identifies venture timing windows based on dasha calendar. "
             "Outputs launch, scale, caution, and exit windows. "
             "NOT probability predictions — structural timing alignment.",
}


# ─── DIGNITY TABLES ──────────────────────────────────────────────────────────

SIGN_LORDS = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon",
    4: "Sun", 5: "Mercury", 6: "Venus", 7: "Mars",
    8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter",
}

EXALTATION = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7,
}

OWN_SIGNS = {
    "Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
    "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
    "Rahu": [10], "Ketu": [7],
}

# Dasha period lengths (years) for each planet
DASHA_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10,
    "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}

# Dasha sequence (Vimsottari)
DASHA_SEQUENCE = [
    "Ketu", "Venus", "Sun", "Moon", "Mars",
    "Rahu", "Jupiter", "Saturn", "Mercury",
]


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _get_house_lord(house_num: int, lagna_sign_idx: int) -> str:
    sign_idx = (lagna_sign_idx + house_num - 1) % 12
    return SIGN_LORDS[sign_idx]


def _is_dignified(planet_name: str, sign_idx: int) -> bool:
    if sign_idx == EXALTATION.get(planet_name, -99):
        return True
    if sign_idx in OWN_SIGNS.get(planet_name, []):
        return True
    return False


def _get_planet_house(planet_name: str, planets: dict, lagna_idx: int) -> Optional[int]:
    pdata = planets.get(planet_name, {})
    if not pdata:
        return None
    h = pdata.get("house")
    if h is not None:
        try:
            return int(h)
        except (TypeError, ValueError):
            pass
    sign_idx = pdata.get("sign_index", -1)
    if sign_idx < 0:
        return None
    return (sign_idx - lagna_idx + 12) % 12 + 1


# ─── DASHA LORD CLASSIFICATION ───────────────────────────────────────────────

def classify_dasha_lord(lord_name: str, chart_data: dict) -> dict:
    """
    Classify a dasha lord's venture-timing quality.

    Returns:
        {
            "quality": "launch" | "scale" | "caution" | "exit" | "neutral",
            "score": float,
            "reason": str,
        }
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # Which houses does this lord rule?
    ruled_houses = []
    for h in range(1, 13):
        if _get_house_lord(h, lagna_idx) == lord_name:
            ruled_houses.append(h)

    # Where is this planet placed?
    planet_house = _get_planet_house(lord_name, planets, lagna_idx)
    planet_sign = None
    pdata = planets.get(lord_name, {})
    if pdata:
        planet_sign = pdata.get("sign_index", -1)
        if planet_sign < 0:
            planet_sign = None

    dignified = planet_sign is not None and _is_dignified(lord_name, planet_sign)

    # ── LAUNCH LORDS ──
    # Mercury, Jupiter, Venus — natural significators of new ventures
    # Also: lords of 1H (self), 5H (creative initiative), 9H (fortune/dharma)
    launch_houses = {1, 5, 9}
    is_launch_lord = lord_name in ("Mercury", "Jupiter", "Venus")
    rules_launch = bool(set(ruled_houses) & launch_houses)

    if is_launch_lord or rules_launch:
        quality = "launch"
        score = 3.0 if (is_launch_lord and rules_launch) else 2.0
        if dignified:
            score += 1.0
        reason_parts = []
        if is_launch_lord:
            reason_parts.append(f"{lord_name} is a natural venture-launch significator")
        if rules_launch:
            reason_parts.append(f"rules {[h for h in ruled_houses if h in launch_houses]}")
        if dignified:
            reason_parts.append("dignified — strong execution")
        return {
            "quality": quality,
            "score": round(score, 1),
            "reason": "; ".join(reason_parts),
        }

    # ── SCALE LORDS ──
    # Rahu (unconventional ambition), Saturn (structure/discipline)
    # Also: lords of 10H (career), 11H (gains)
    scale_houses = {10, 11}
    is_scale_lord = lord_name in ("Rahu", "Saturn")
    rules_scale = bool(set(ruled_houses) & scale_houses)

    if is_scale_lord or rules_scale:
        quality = "scale"
        score = 2.5 if (is_scale_lord and rules_scale) else 2.0
        if dignified:
            score += 1.0
        reason_parts = []
        if is_scale_lord:
            reason_parts.append(f"{lord_name} MD/AD = expansion/structure arc")
        if rules_scale:
            reason_parts.append(f"rules {[h for h in ruled_houses if h in scale_houses]}")
        if dignified:
            reason_parts.append("dignified — disciplined expansion")
        return {
            "quality": quality,
            "score": round(score, 1),
            "reason": "; ".join(reason_parts),
        }

    # ── CAUTION LORDS ──
    # Lords of 6H (enemies/debt), 8H (sudden losses), 12H (dissolution)
    caution_houses = {6, 8, 12}
    rules_caution = bool(set(ruled_houses) & caution_houses)
    in_caution_house = planet_house in (6, 8, 12) if planet_house else False

    if rules_caution and not dignified:
        quality = "caution"
        score = -2.0
        if in_caution_house:
            score -= 1.0
        reason_parts = [f"rules dushthana houses {[h for h in ruled_houses if h in caution_houses]}"]
        if in_caution_house:
            reason_parts.append(f"also placed in H{planet_house}")
        if not dignified:
            reason_parts.append("not dignified — no protective strength")
        return {
            "quality": quality,
            "score": round(score, 1),
            "reason": "; ".join(reason_parts),
        }

    # ── EXIT / TRANSITION LORDS ──
    # Ketu (detachment, endings), also 12H lord
    if lord_name == "Ketu":
        quality = "exit"
        score = -1.0
        return {
            "quality": quality,
            "score": score,
            "reason": "Ketu MD/AD = detachment phase; natural exit/transition window",
        }

    # ── NEUTRAL ──
    # Sun, Moon, Mars in non-critical houses
    return {
        "quality": "neutral",
        "score": 0.0,
        "reason": f"{lord_name} in neutral configuration for venture timing",
    }


# ─── SADE SATI ANALYSIS ─────────────────────────────────────────────────────

def _check_sade_sati_phase(chart_data: dict, transit_saturn_sign: Optional[int] = None) -> dict:
    """
    Determine Sade Sati phase relative to natal Moon.

    Returns:
        {
            "active": bool,
            "phase": "rising" | "peak" | "setting" | None,
            "caution_level": "HIGH" | "MEDIUM" | "LOW" | None,
            "detail": str,
        }
    """
    planets = chart_data.get("planets", {})
    moon_sign = planets.get("Moon", {}).get("sign_index")
    if moon_sign is None:
        return {"active": False, "phase": None, "caution_level": None, "detail": "Moon sign not available"}

    if transit_saturn_sign is None:
        return {"active": False, "phase": None, "caution_level": None, "detail": "Transit Saturn not provided"}

    # Sade Sati: Saturn in 12th, 1st, or 2nd from natal Moon sign
    offset = (transit_saturn_sign - moon_sign + 12) % 12

    if offset == 11:  # 12th from Moon
        return {
            "active": True,
            "phase": "rising",
            "caution_level": "MEDIUM",
            "detail": "Sade Sati rising phase — Saturn approaching Moon. Foundation-testing period.",
        }
    elif offset == 0:  # same sign as Moon
        return {
            "active": True,
            "phase": "peak",
            "caution_level": "HIGH",
            "detail": "Sade Sati peak — Saturn on natal Moon. Maximum pressure. Don't overcommit.",
        }
    elif offset == 1:  # 2nd from Moon
        return {
            "active": True,
            "phase": "setting",
            "caution_level": "MEDIUM",
            "detail": "Sade Sati setting phase — lessons integrating. Caution on equity dilution and timelines.",
        }
    else:
        return {"active": False, "phase": None, "caution_level": None, "detail": "Not in Sade Sati"}


# ─── MAIN ANALYSIS ───────────────────────────────────────────────────────────

def analyze_venture_timing(
    chart_data: dict,
    dasha_periods: Optional[List[dict]] = None,
    transit_saturn_sign: Optional[int] = None,
    horizon_months: int = 60,
) -> dict:
    """
    Analyze venture timing windows from dasha calendar.

    Args:
        chart_data: Full chart data dict.
        dasha_periods: List of dasha period dicts with:
            {"md_lord": str, "ad_lord": str, "start": str, "end": str}
            If None, uses chart_data's current_phase only.
        transit_saturn_sign: Current Saturn transit sign (0-11).
        horizon_months: How far ahead to look (default 60 = 5 years).

    Returns:
        {
            "current_phase": {...},
            "launch_windows": [...],
            "scale_windows": [...],
            "caution_windows": [...],
            "exit_windows": [...],
            "sade_sati": {...},
        }
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # ── Classify each dasha period ──
    launch_windows = []
    scale_windows = []
    caution_windows = []
    exit_windows = []
    current_phase_info = None

    if dasha_periods:
        for period in dasha_periods:
            md_lord = period.get("md_lord", "")
            ad_lord = period.get("ad_lord", "")
            start = period.get("start", "")
            end = period.get("end", "")

            md_class = classify_dasha_lord(md_lord, chart_data)
            ad_class = classify_dasha_lord(ad_lord, chart_data)

            # Combined quality assessment
            combined_score = md_class["score"] + ad_class["score"] * 0.6
            combined_quality = _combine_qualities(md_class["quality"], ad_class["quality"])

            window = {
                "window": f"{start} — {end}",
                "md_lord": md_lord,
                "ad_lord": ad_lord,
                "quality": combined_quality.upper(),
                "score": round(combined_score, 1),
                "reason": f"MD {md_lord}: {md_class['reason']}. AD {ad_lord}: {ad_class['reason']}",
            }

            if combined_quality == "launch":
                launch_windows.append(window)
            elif combined_quality == "scale":
                scale_windows.append(window)
            elif combined_quality == "caution":
                caution_windows.append(window)
            elif combined_quality == "exit":
                exit_windows.append(window)

            # First period = current phase
            if current_phase_info is None:
                current_phase_info = {
                    "md_lord": md_lord,
                    "ad_lord": ad_lord,
                    "quality": combined_quality.upper(),
                    "reason": window["reason"],
                    "window": f"{start} — {end}",
                }
    else:
        # Fallback: classify current MD/AD from chart_data if available
        current_phase = chart_data.get("current_phase", {})
        vimsottari = current_phase.get("vimsottari", {}) if isinstance(current_phase, dict) else {}
        md_lord = vimsottari.get("md", "")
        ad_lord = vimsottari.get("ad", "")
        if md_lord:
            md_class = classify_dasha_lord(md_lord, chart_data)
            ad_class = classify_dasha_lord(ad_lord, chart_data) if ad_lord else {"quality": "neutral", "score": 0, "reason": ""}
            combined_quality = _combine_qualities(md_class["quality"], ad_class.get("quality", "neutral"))
            current_phase_info = {
                "md_lord": md_lord,
                "ad_lord": ad_lord,
                "quality": combined_quality.upper(),
                "reason": f"MD {md_lord}: {md_class['reason']}",
                "window": f"{vimsottari.get('md_start', '?')} — {vimsottari.get('md_end', '?')}",
            }

    # ── Sade Sati check ──
    sade_sati = _check_sade_sati_phase(chart_data, transit_saturn_sign)

    # If Sade Sati is active, add a caution overlay
    if sade_sati.get("active"):
        caution_windows.append({
            "window": "Current (Sade Sati active)",
            "quality": sade_sati["caution_level"],
            "reason": sade_sati["detail"],
            "type": "sade_sati",
        })

    return {
        "current_phase": current_phase_info or {"quality": "UNKNOWN", "reason": "Dasha data not available"},
        "launch_windows": launch_windows,
        "scale_windows": scale_windows,
        "caution_windows": caution_windows,
        "exit_windows": exit_windows,
        "sade_sati": sade_sati,
        "signature_version": SIGNATURE_METADATA["version"],
        "honesty_note": (
            "Timing windows describe structural alignment of planetary periods, "
            "not guaranteed outcomes. Good timing + wrong business type still fails. "
            "Use alongside business_fit signature."
        ),
    }


def _combine_qualities(md_quality: str, ad_quality: str) -> str:
    """
    Combine MD and AD qualities into a single window classification.
    MD has more weight (longer period), but AD modifies it.
    """
    # Priority: caution > exit > scale > launch > neutral
    if md_quality == "caution" or ad_quality == "caution":
        # If both are caution, definitely caution
        # If one is caution and other is positive, still caution (conservative)
        if md_quality == "caution" and ad_quality == "caution":
            return "caution"
        elif md_quality == "caution":
            return "caution"
        else:
            # AD is caution but MD is positive — moderate caution
            return "caution" if ad_quality == "caution" else md_quality

    if md_quality == "exit" or ad_quality == "exit":
        return "exit"

    if md_quality == "launch" and ad_quality in ("launch", "neutral"):
        return "launch"
    if md_quality == "scale" and ad_quality in ("scale", "neutral", "launch"):
        return "scale"
    if md_quality == "launch" and ad_quality == "scale":
        return "launch"  # launch within scaling energy
    if md_quality == "scale" and ad_quality == "launch":
        return "scale"

    if md_quality == "neutral" and ad_quality == "neutral":
        return "neutral"

    # Default: use MD quality
    return md_quality


# ─── CONFORMANCE LAYER: check_signature INTERFACE ────────────────────────────
# venture_timing is a timing-aware signature. It uses dasha/transit
# to identify windows. Implements standard interface for registry.

def check_natal_conditions(chart_data: dict) -> dict:
    """
    Natal check for venture timing — checks if chart has
    any strong dasha lords for venture activity.
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # Check if any of the natural venture lords are strong
    venture_lords = ["Mercury", "Jupiter", "Venus", "Rahu"]
    strong_count = 0
    detail = []

    for lord in venture_lords:
        pdata = planets.get(lord, {})
        sign_idx = pdata.get("sign_index", -1)
        if sign_idx >= 0 and _is_dignified(lord, sign_idx):
            strong_count += 1
            detail.append(f"{lord} dignified — strong when its dasha activates")

    fires = strong_count >= 1  # At least one venture lord is strong

    return {
        "fires": fires,
        "score": strong_count,
        "max_score": 4,
        "detail": detail,
        "downfall_marker": False,
    }


def check_dasha_conditions(chart_data: dict, md_lord: str, ad_lord: str) -> dict:
    """Check if current dasha supports venture activity."""
    md_class = classify_dasha_lord(md_lord, chart_data)
    ad_class = classify_dasha_lord(ad_lord, chart_data)

    fires = md_class["quality"] in ("launch", "scale")
    detail = [
        f"MD {md_lord}: {md_class['quality']} ({md_class['reason']})",
        f"AD {ad_lord}: {ad_class['quality']} ({ad_class['reason']})",
    ]

    return {
        "fires": fires,
        "detail": detail,
    }


def check_transit_conditions(chart_data: dict, transit_positions: dict) -> dict:
    """Check if transits support venture activity (no Sade Sati peak)."""
    saturn_sign = transit_positions.get("Saturn", {}).get("sign_index")
    sade_sati = _check_sade_sati_phase(chart_data, saturn_sign)

    # Fires if NOT in Sade Sati peak
    fires = not (sade_sati.get("active") and sade_sati.get("phase") == "peak")

    detail = [sade_sati.get("detail", "Transit analysis incomplete")]

    return {
        "fires": fires,
        "detail": detail,
    }


def check_signature(
    chart_data: dict,
    md_lord: str,
    ad_lord: str,
    transit_positions: dict,
) -> dict:
    """Full venture_timing signature check."""
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
        "downfall_marker": False,
    }


def _build_missing(natal: dict, dasha: dict, transit: dict) -> list:
    missing = []
    if not natal["fires"]:
        missing.append("No strong venture lords dignified in natal chart")
    if not dasha["fires"]:
        missing.append("Current dasha period not in launch/scale mode")
    if not transit["fires"]:
        missing.append("Sade Sati peak active — major caution window")
    return missing
