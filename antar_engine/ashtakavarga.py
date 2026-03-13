"""
antar_engine/ashtakavarga.py  — REAL IMPLEMENTATION
=====================================================
Ashtakavarga = "Eight Sources" transit strength system.

WHAT IT DOES:
  Every planet casts "bindus" (benefic points) into signs based on
  its position relative to each of the 7 planets + lagna.
  
  For each transiting planet, we count how many bindus it receives
  in the sign it's transiting. 
  
  0-2 bindus → transit is WEAK (planet struggles, bad outcomes)
  3-4 bindus → NEUTRAL (average effects)
  5-6 bindus → STRONG (planet is powerful, good outcomes)
  7-8 bindus → VERY STRONG (rare, exceptional results)

WHY THIS MATTERS FOR ANTAR:
  Without Ashtakavarga: "Jupiter transiting your 10th house = good for career"
  With Ashtakavarga:    "Jupiter transiting your 10th house with 6 bindus = 
                         EXCEPTIONALLY powerful career window — act now"
                        OR
                        "Jupiter transiting your 10th house with 2 bindus =
                         Jupiter's transit is weak here — don't over-rely on 
                         this window, timing is important"

  This is what separates general horoscope from personalized prediction.

COMPUTATION:
  For each planet P, its Ashtakavarga shows which signs receive bindus
  from P's position relative to every other planet and lagna.
  
  The "contribution tables" below define exactly which relative positions
  (houses from P's natal position) cast a bindu.

  These tables are from Parashari tradition (BPHS).

USAGE:
  from antar_engine.ashtakavarga import (
      compute_bhinnashtakavarga,   # one planet's bindus in all 12 signs
      compute_sarvashtakavarga,    # total bindus (all planets combined)
      get_transit_bindus,          # bindus for a specific transit
      get_transit_strength,        # "strong"/"neutral"/"weak" label
      ashtakavarga_transit_boost,  # confidence multiplier for rules engine
  )
"""

from __future__ import annotations
from typing import Dict, List

# ── Constants ──────────────────────────────────────────────────────────────────

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
PLANET_INDEX = {p: i for i, p in enumerate(PLANETS)}

# ── Contribution Tables (Parashari / BPHS) ────────────────────────────────────
#
# For each planet (rows), these are the HOUSE POSITIONS from which
# that planet receives a bindu FROM each contributor.
#
# Format: CONTRIBUTIONS[contributor][planet] = [list of positions 1-12]
# where position = house number counted from contributor's natal sign
#
# Example: CONTRIBUTIONS["Sun"]["Sun"] = [1,2,4,7,8,9,10,11]
# means: Sun casts a bindu into signs that are 1,2,4,7,8,9,10,11 houses
# from Sun's own natal position (for Sun's Ashtakavarga)

CONTRIBUTIONS: Dict[str, Dict[str, List[int]]] = {
    "Sun": {
        "Sun":     [1, 2, 4, 7, 8, 9, 10, 11],
        "Moon":    [3, 6, 10, 11],
        "Mars":    [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11],
        "Venus":   [6, 7, 12],
        "Saturn":  [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna":   [3, 4, 6, 10, 11, 12],
    },
    "Moon": {
        "Sun":     [3, 6, 7, 8, 10, 11],
        "Moon":    [1, 3, 6, 7, 10, 11],
        "Mars":    [2, 3, 5, 6, 9, 10, 11],
        "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 4, 7, 8, 10, 11, 12],
        "Venus":   [3, 4, 5, 7, 9, 10, 11],
        "Saturn":  [3, 5, 6, 11],
        "Lagna":   [3, 6, 10, 11],
    },
    "Mars": {
        "Sun":     [3, 5, 6, 10, 11],
        "Moon":    [3, 6, 11],
        "Mars":    [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12],
        "Venus":   [6, 8, 11, 12],
        "Saturn":  [1, 4, 7, 8, 9, 10, 11],
        "Lagna":   [1, 3, 6, 10, 11],
    },
    "Mercury": {
        "Sun":     [5, 6, 9, 11, 12],
        "Moon":    [2, 4, 6, 8, 10, 11],
        "Mars":    [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12],
        "Venus":   [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn":  [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna":   [1, 2, 4, 6, 8, 10, 11],
    },
    "Jupiter": {
        "Sun":     [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "Moon":    [2, 5, 7, 9, 11],
        "Mars":    [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
        "Venus":   [2, 5, 6, 9, 10, 11],
        "Saturn":  [3, 5, 6, 12],
        "Lagna":   [1, 2, 4, 5, 6, 7, 9, 10, 11],
    },
    "Venus": {
        "Sun":     [8, 11, 12],
        "Moon":    [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars":    [3, 4, 6, 9, 11, 12],
        "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11],
        "Venus":   [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn":  [3, 4, 5, 8, 9, 10, 11],
        "Lagna":   [1, 2, 3, 4, 5, 8, 9, 11],
    },
    "Saturn": {
        "Sun":     [1, 2, 4, 7, 8, 10, 11],
        "Moon":    [3, 6, 11],
        "Mars":    [3, 5, 6, 10, 11, 12],
        "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12],
        "Venus":   [6, 11, 12],
        "Saturn":  [3, 5, 6, 11],
        "Lagna":   [1, 3, 4, 6, 10, 11],
    },
}

# Bindu thresholds for strength labels
BINDU_THRESHOLDS = {
    "Sun":     {"weak": 3, "strong": 5},   # max 8
    "Moon":    {"weak": 5, "strong": 7},   # max 8 (Moon needs more)
    "Mars":    {"weak": 3, "strong": 5},
    "Mercury": {"weak": 4, "strong": 6},
    "Jupiter": {"weak": 4, "strong": 6},
    "Venus":   {"weak": 4, "strong": 6},
    "Saturn":  {"weak": 3, "strong": 5},
}

# Confidence multipliers for rules engine
BINDU_MULTIPLIER = {
    "very_strong": 1.25,  # 7-8 bindus
    "strong":      1.15,  # 5-6 bindus
    "neutral":     1.00,  # 3-4 bindus
    "weak":        0.80,  # 1-2 bindus
    "very_weak":   0.65,  # 0 bindus
}


# ── Core Computation ──────────────────────────────────────────────────────────

def _sign_index_of(planet: str, chart_data: dict) -> int:
    """Get natal sign index (0-11) of a planet or lagna."""
    if planet == "Lagna":
        return chart_data.get("lagna", {}).get("sign_index", 0)
    return chart_data.get("planets", {}).get(planet, {}).get("sign_index", 0)


def compute_bhinnashtakavarga(planet: str, chart_data: dict) -> List[int]:
    """
    Compute Bhinnashtakavarga for one planet.
    Returns list of 12 integers — bindus in each sign (index 0=Aries, 11=Pisces).
    
    Algorithm:
      For each contributor (7 planets + Lagna):
        Get contributor's natal sign index
        The contribution table says which house positions FROM contributor cast a bindu
        Convert house positions to sign indices
        Add 1 to those sign indices in the result
    """
    if planet not in CONTRIBUTIONS:
        return [0] * 12

    bindus = [0] * 12
    contrib_table = CONTRIBUTIONS[planet]  # {contributor: [positions]}

    contributors = PLANETS + ["Lagna"]
    for contributor in contributors:
        if contributor not in contrib_table:
            continue
        positions = contrib_table[contributor]       # e.g. [1, 2, 4, 7, 8, 9, 10, 11]
        contrib_sign = _sign_index_of(contributor, chart_data)  # natal sign of contributor

        for pos in positions:
            # pos is house number (1-12), counted from contributor's sign
            # sign index = (contributor_sign + pos - 1) % 12
            target_sign = (contrib_sign + pos - 1) % 12
            bindus[target_sign] += 1

    return bindus


def compute_sarvashtakavarga(chart_data: dict) -> List[int]:
    """
    Sarvashtakavarga = sum of all 7 planets' Bhinnashtakavarga.
    Returns list of 12 integers — total bindus per sign.
    Maximum possible = 56 per sign (7 planets × 8 contributors each).
    Average = ~28 per sign.
    """
    total = [0] * 12
    for planet in PLANETS:
        bhinna = compute_bhinnashtakavarga(planet, chart_data)
        for i in range(12):
            total[i] += bhinna[i]
    return total


def get_transit_bindus(transit_planet: str, transit_sign_index: int,
                       chart_data: dict) -> int:
    """
    Get the number of bindus for a specific planet transiting a specific sign.
    This is the KEY function for transit strength assessment.
    """
    bhinna = compute_bhinnashtakavarga(transit_planet, chart_data)
    return bhinna[transit_sign_index % 12]


def get_transit_strength(transit_planet: str, transit_sign_index: int,
                         chart_data: dict) -> dict:
    """
    Full transit strength assessment.
    Returns: {bindus, strength, label, multiplier, interpretation}
    """
    bindus = get_transit_bindus(transit_planet, transit_sign_index, chart_data)
    thresholds = BINDU_THRESHOLDS.get(transit_planet, {"weak": 3, "strong": 5})

    if bindus >= 7:
        strength = "very_strong"
        label    = "EXCEPTIONAL"
        interp   = f"{transit_planet} is operating at peak power in this transit ({bindus}/8 bindus). Rare and highly auspicious."
    elif bindus >= thresholds["strong"]:
        strength = "strong"
        label    = "STRONG"
        interp   = f"{transit_planet} transit is strong ({bindus}/8 bindus). Effects are clear and beneficial."
    elif bindus >= thresholds["weak"]:
        strength = "neutral"
        label    = "MODERATE"
        interp   = f"{transit_planet} transit is average strength ({bindus}/8 bindus). Mixed results — timing matters."
    elif bindus >= 1:
        strength = "weak"
        label    = "WEAK"
        interp   = f"{transit_planet} transit has low bindus ({bindus}/8). Effects are muted or delayed. Don't over-rely on this window."
    else:
        strength = "very_weak"
        label    = "VERY WEAK"
        interp   = f"{transit_planet} transit has 0 bindus. This transit is largely ineffective for you. Wait for a stronger window."

    return {
        "bindus":       bindus,
        "strength":     strength,
        "label":        label,
        "multiplier":   BINDU_MULTIPLIER[strength],
        "interpretation": interp,
    }


def get_sarva_strength(sign_index: int, chart_data: dict) -> dict:
    """
    Get Sarvashtakavarga strength for a specific sign.
    Used to assess overall life area strength (not just one planet).
    """
    sarva = compute_sarvashtakavarga(chart_data)
    bindus = sarva[sign_index % 12]

    # Sarva thresholds: average ~28, strong >30, weak <25
    if bindus >= 35:
        strength = "very_strong"
        label    = "HIGHLY FAVORABLE ZONE"
    elif bindus >= 28:
        strength = "strong"
        label    = "FAVORABLE ZONE"
    elif bindus >= 22:
        strength = "neutral"
        label    = "MODERATE ZONE"
    elif bindus >= 15:
        strength = "weak"
        label    = "CHALLENGING ZONE"
    else:
        strength = "very_weak"
        label    = "VERY CHALLENGING ZONE"

    return {
        "bindus":   bindus,
        "strength": strength,
        "label":    label,
    }


# ── Ashtakavarga Transit Boost for Rules Engine ───────────────────────────────

def ashtakavarga_transit_boost(transit_signals: list, chart_data: dict) -> list:
    """
    Boost or reduce transit signal confidence based on actual Ashtakavarga bindus.
    
    This is the KEY integration function for astrological_rules.py:
    - Strong transit (5+ bindus) → confidence boosted → appears in top signals
    - Weak transit (0-2 bindus)  → confidence reduced → may drop out of top signals
    
    This transforms "Jupiter in 10H is good" into 
    "Jupiter in 10H with 6 bindus = act NOW" vs 
    "Jupiter in 10H with 2 bindus = weak window, don't over-commit"
    """
    boosted = []
    for signal in transit_signals:
        planet   = signal.get("transit_planet", signal.get("planet", ""))
        house    = signal.get("house", 0)

        if not planet or not house:
            boosted.append(signal)
            continue

        # Convert house to sign index (lagna sign + house - 1)
        lagna_si  = chart_data.get("lagna", {}).get("sign_index", 0)
        sign_idx  = (lagna_si + house - 1) % 12

        if planet not in PLANETS:
            boosted.append(signal)
            continue

        strength_data = get_transit_strength(planet, sign_idx, chart_data)
        bindus        = strength_data["bindus"]
        multiplier    = strength_data["multiplier"]
        label         = strength_data["label"]

        # Clone signal and apply boost
        s = dict(signal)
        s["confidence"]         = min(s["confidence"] * multiplier, 0.97)
        s["ashtakavarga_bindus"]= bindus
        s["ashtakavarga_label"] = label
        s["ashtakavarga_note"]  = strength_data["interpretation"]

        # Append bindu info to prediction text
        if bindus >= 5:
            s["prediction"] = s["prediction"] + (
                f" [Ashtakavarga: {bindus}/8 bindus — this transit is STRONG for you specifically. "
                f"Act decisively in this window.]"
            )
        elif bindus <= 2:
            s["prediction"] = s["prediction"] + (
                f" [Ashtakavarga: {bindus}/8 bindus — this transit is weak for your chart. "
                f"Effects will be muted. Don't over-rely on this timing.]"
            )

        boosted.append(s)

    return boosted


def get_best_transit_windows(chart_data: dict, planet: str) -> list:
    """
    Find which signs give the strongest transit for a planet.
    Useful for telling users: 'Jupiter is strongest for you in Gemini and Scorpio'
    Returns list of {sign, bindus, strength} sorted by bindus descending.
    """
    bhinna = compute_bhinnashtakavarga(planet, chart_data)
    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    windows = [
        {"sign": SIGNS[i], "sign_index": i, "bindus": bhinna[i]}
        for i in range(12)
    ]
    windows.sort(key=lambda x: x["bindus"], reverse=True)

    thresholds = BINDU_THRESHOLDS.get(planet, {"weak": 3, "strong": 5})
    for w in windows:
        b = w["bindus"]
        if b >= 7:             w["strength"] = "very_strong"
        elif b >= thresholds["strong"]: w["strength"] = "strong"
        elif b >= thresholds["weak"]:   w["strength"] = "neutral"
        elif b >= 1:           w["strength"] = "weak"
        else:                  w["strength"] = "very_weak"

    return windows


def get_ashtakavarga_summary(chart_data: dict) -> dict:
    """
    Full Ashtakavarga summary for a chart.
    Returns per-planet bindus per sign + Sarva totals.
    Useful for storing in DB or sending to frontend.
    """
    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    summary = {}
    for planet in PLANETS:
        bhinna = compute_bhinnashtakavarga(planet, chart_data)
        summary[planet] = {SIGNS[i]: bhinna[i] for i in range(12)}

    sarva = compute_sarvashtakavarga(chart_data)
    summary["Sarva"] = {SIGNS[i]: sarva[i] for i in range(12)}

    return summary


# ── Signal Generator for Rules Engine ────────────────────────────────────────

def apply_ashtakavarga_signals(chart_data: dict, current_transits: list,
                                concern: str) -> list:
    """
    Generate Ashtakavarga-specific signals for the rules pipeline.
    Fires when a slow planet (Jupiter/Saturn/Rahu) has exceptional OR very weak bindus.
    These are rare enough to always surface in top signals.
    """
    signals = []
    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    key_planets = {"Jupiter", "Saturn", "Rahu", "Ketu"}
    lagna_si = chart_data.get("lagna", {}).get("sign_index", 0)

    for t in current_transits:
        planet = t.get("planet", "")
        if planet not in key_planets:
            continue
        house    = t.get("transit_house", 0)
        sign_idx = (lagna_si + house - 1) % 12
        sign     = SIGNS[sign_idx]

        if planet == "Ketu":
            # Ketu uses Mars table (standard practice)
            check_planet = "Mars"
        else:
            check_planet = planet

        if check_planet not in PLANETS:
            continue

        sd = get_transit_strength(check_planet, sign_idx, chart_data)
        bindus     = sd["bindus"]
        strength   = sd["strength"]
        multiplier = sd["multiplier"]

        domain_map = {
            "Jupiter": "career" if house in (1,2,3,4,5,10,11) else "spiritual",
            "Saturn":  "career" if house in (10,) else "health",
            "Rahu":    "career",
            "Ketu":    "spiritual",
        }
        domain = domain_map.get(planet, "general")

        if strength == "very_strong":
            signals.append({
                "system":           "ashtakavarga",
                "planet":           planet,
                "rule_id":          f"AVG_{planet}_H{house}_PEAK",
                "domain":           domain,
                "confidence":       0.90,
                "prediction":       (
                    f"Ashtakavarga PEAK WINDOW: {planet} in House {house} ({sign}) "
                    f"has {bindus}/8 bindus — the highest personal strength score possible. "
                    f"This is not a generic transit — for YOUR chart specifically, "
                    f"this is a rare, high-powered window. "
                    f"{'Career breakthroughs' if domain == 'career' else 'Spiritual breakthroughs'} "
                    f"initiated now carry unusual staying power."
                ),
                "warning":          "",
                "remedy_planet":    planet,
                "concern_relevance":0.92,
                "ashtakavarga_bindus": bindus,
                "ashtakavarga_label": "PEAK",
                "timeframe":        t.get("timeframe", "current transit"),
            })

        elif strength == "strong":
            signals.append({
                "system":           "ashtakavarga",
                "planet":           planet,
                "rule_id":          f"AVG_{planet}_H{house}_STRONG",
                "domain":           domain,
                "confidence":       0.82,
                "prediction":       (
                    f"Ashtakavarga confirms: {planet} in House {house} has {bindus}/8 bindus — "
                    f"strong personal resonance with this transit. "
                    f"Generic predictions for this transit are amplified for you. "
                    f"This window is worth acting on specifically."
                ),
                "warning":          "",
                "remedy_planet":    planet,
                "concern_relevance":0.85,
                "ashtakavarga_bindus": bindus,
                "ashtakavarga_label": "STRONG",
            })

        elif strength in ("weak", "very_weak"):
            signals.append({
                "system":           "ashtakavarga",
                "planet":           planet,
                "rule_id":          f"AVG_{planet}_H{house}_WEAK",
                "domain":           domain,
                "confidence":       0.78,
                "prediction":       (
                    f"Ashtakavarga CAUTION: {planet} in House {house} has only {bindus}/8 bindus. "
                    f"Despite what general astrology says about this transit, "
                    f"for YOUR chart this is a low-power window. "
                    f"{'Avoid major career commitments' if domain == 'career' else 'Wait for a stronger window'} "
                    f"— the next {planet} transit will be more powerful for you."
                ),
                "warning":          f"{planet} transit is weak for your specific chart ({bindus}/8 bindus). Don't over-invest in this timing.",
                "remedy_planet":    planet,
                "concern_relevance":0.85,
                "ashtakavarga_bindus": bindus,
                "ashtakavarga_label": "WEAK",
                "is_pain_signal":   True,
            })

    return signals
