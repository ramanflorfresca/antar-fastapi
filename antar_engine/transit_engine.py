"""
transit_engine.py — Real-time transit computation using Swiss Ephemeris.

Computes where planets are in the sky RIGHT NOW and how they relate
to a user's natal chart positions. This is the "delivery boy" layer —
dashas open the window, transits deliver the event.
"""
import swisseph as swe
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Ayanamsa — must match what natal chart used (Lahiri)
swe.set_sid_mode(swe.SIDM_LAHIRI)

# Planet IDs in Swiss Ephemeris
SWE_PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
}

# Rahu = mean north node, Ketu = 180° opposite
SWE_RAHU = swe.MEAN_NODE

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Aspect orbs (degrees of tolerance)
ASPECT_ORBS = {
    "Sun": 15, "Moon": 12, "Mars": 8, "Mercury": 7,
    "Jupiter": 9, "Venus": 7, "Saturn": 9, "Rahu": 8, "Ketu": 8,
}

# Major aspect angles
ASPECTS = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    180: "opposition",
}


def get_current_transit_positions(date: datetime = None) -> Dict:
    """
    Compute sidereal positions of all planets for a given date/time.
    Returns dict: { "Sun": { "longitude": 45.23, "sign": "Taurus",
                              "sign_index": 1, "degree_in_sign": 15.23 }, ... }
    """
    if not date:
        date = datetime.utcnow()

    jd = swe.julday(date.year, date.month, date.day,
                     date.hour + date.minute / 60.0)

    positions = {}
    for name, pid in SWE_PLANETS.items():
        result = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)
        lon = result[0][0]  # sidereal longitude
        sign_idx = int(lon / 30)
        deg_in_sign = lon % 30
        positions[name] = {
            "longitude": round(lon, 4),
            "sign": SIGNS[sign_idx],
            "sign_index": sign_idx,
            "degree_in_sign": round(deg_in_sign, 2),
            "speed": round(result[0][3], 4),  # daily speed
            "retrograde": result[0][3] < 0,
        }

    # Rahu (mean node)
    rahu_result = swe.calc_ut(jd, SWE_RAHU, swe.FLG_SIDEREAL)
    rahu_lon = rahu_result[0][0]
    rahu_sign_idx = int(rahu_lon / 30)
    positions["Rahu"] = {
        "longitude": round(rahu_lon, 4),
        "sign": SIGNS[rahu_sign_idx],
        "sign_index": rahu_sign_idx,
        "degree_in_sign": round(rahu_lon % 30, 2),
        "speed": round(rahu_result[0][3], 4),
        "retrograde": True,  # Rahu is always retrograde
    }

    # Ketu = 180° from Rahu
    ketu_lon = (rahu_lon + 180) % 360
    ketu_sign_idx = int(ketu_lon / 30)
    positions["Ketu"] = {
        "longitude": round(ketu_lon, 4),
        "sign": SIGNS[ketu_sign_idx],
        "sign_index": ketu_sign_idx,
        "degree_in_sign": round(ketu_lon % 30, 2),
        "speed": round(-rahu_result[0][3], 4),
        "retrograde": True,
    }

    return positions


def compute_transit_aspects(transit_positions: Dict, natal_positions: Dict) -> List[Dict]:
    """
    Find all aspects between current transiting planets and natal positions.
    Returns list of active aspects with orb and significance.
    """
    aspects = []

    for t_name, t_data in transit_positions.items():
        t_lon = t_data["longitude"]

        for n_name, n_data in natal_positions.items():
            if not isinstance(n_data, dict) or "longitude" not in n_data:
                continue

            n_lon = n_data["longitude"]

            # Calculate angular distance
            diff = abs(t_lon - n_lon)
            if diff > 180:
                diff = 360 - diff

            # Check each aspect angle
            for angle, aspect_name in ASPECTS.items():
                orb = ASPECT_ORBS.get(t_name, 8)
                if abs(diff - angle) <= orb:
                    strength = 1.0 - (abs(diff - angle) / orb)
                    aspects.append({
                        "transit_planet": t_name,
                        "natal_planet": n_name,
                        "aspect": aspect_name,
                        "exact_angle": round(diff, 2),
                        "orb": round(abs(diff - angle), 2),
                        "strength": round(strength, 2),
                        "transit_sign": t_data["sign"],
                        "natal_sign": n_data.get("sign", ""),
                        "natal_house": n_data.get("house", 0),
                        "transit_retrograde": t_data.get("retrograde", False),
                    })

    # Sort by strength (strongest first)
    aspects.sort(key=lambda x: -x["strength"])
    return aspects


def compute_transit_house_activation(transit_positions: Dict, natal_lagna_degree: float) -> Dict:
    """
    Determine which natal houses are activated by transiting planets.
    Returns dict: { 1: ["Jupiter"], 7: ["Saturn", "Rahu"], 10: ["Sun"] }
    """
    lagna_sign_idx = int(natal_lagna_degree / 30)
    house_activation = {i: [] for i in range(1, 13)}

    for name, data in transit_positions.items():
        t_sign_idx = data["sign_index"]
        # House = distance from lagna sign + 1
        house = ((t_sign_idx - lagna_sign_idx) % 12) + 1
        house_activation[house].append(name)

    # Remove empty houses
    return {h: planets for h, planets in house_activation.items() if planets}


def detect_major_transits(transit_positions: Dict, natal_positions: Dict,
                          natal_lagna_degree: float) -> List[Dict]:
    """
    Detect major life-affecting transits:
    - Saturn over natal Moon (Sade Sati)
    - Jupiter over natal lagna or 7th
    - Rahu/Ketu axis over natal Sun/Moon
    - Saturn return (Saturn over natal Saturn)
    """
    major = []
    lagna_sign_idx = int(natal_lagna_degree / 30)

    # Sade Sati check (Saturn within 1 sign of natal Moon)
    natal_moon = natal_positions.get("Moon", {})
    if natal_moon and isinstance(natal_moon, dict):
        moon_sign_idx = natal_moon.get("sign_index",
            SIGNS.index(natal_moon["sign"]) if natal_moon.get("sign") in SIGNS else -1)
        saturn_sign_idx = transit_positions.get("Saturn", {}).get("sign_index", -1)

        if moon_sign_idx >= 0 and saturn_sign_idx >= 0:
            dist = (saturn_sign_idx - moon_sign_idx) % 12
            if dist in (11, 0, 1):  # 12th, 1st, 2nd from Moon
                phase = {11: "rising", 0: "peak", 1: "setting"}[dist]
                major.append({
                    "type": "sade_sati",
                    "phase": phase,
                    "severity": "high" if dist == 0 else "moderate",
                    "description": f"Saturn transiting {'over' if dist == 0 else 'near'} your natal Moon — "
                                   f"emotional pressure and restructuring {'at peak' if dist == 0 else 'phase'}",
                    "affected_chakra": "Sacral",
                    "planet": "Saturn",
                })

    # Saturn return (Saturn over natal Saturn)
    natal_saturn = natal_positions.get("Saturn", {})
    if natal_saturn and isinstance(natal_saturn, dict):
        sat_natal_sign = natal_saturn.get("sign_index",
            SIGNS.index(natal_saturn["sign"]) if natal_saturn.get("sign") in SIGNS else -1)
        sat_transit_sign = transit_positions.get("Saturn", {}).get("sign_index", -1)
        if sat_natal_sign >= 0 and sat_natal_sign == sat_transit_sign:
            major.append({
                "type": "saturn_return",
                "severity": "high",
                "description": "Saturn returning to its natal position — major life restructuring cycle",
                "affected_chakra": "Third Eye",
                "planet": "Saturn",
            })

    # Jupiter over lagna (growth year)
    jup_sign = transit_positions.get("Jupiter", {}).get("sign_index", -1)
    if jup_sign == lagna_sign_idx:
        major.append({
            "type": "jupiter_lagna",
            "severity": "positive",
            "description": "Jupiter transiting your identity area — expansion, growth, new opportunities",
            "affected_chakra": "Crown",
            "planet": "Jupiter",
        })

    # Rahu/Ketu over natal Sun or Moon
    rahu_sign = transit_positions.get("Rahu", {}).get("sign_index", -1)
    ketu_sign = transit_positions.get("Ketu", {}).get("sign_index", -1)

    natal_sun = natal_positions.get("Sun", {})
    if natal_sun and isinstance(natal_sun, dict):
        sun_sign_idx = natal_sun.get("sign_index",
            SIGNS.index(natal_sun["sign"]) if natal_sun.get("sign") in SIGNS else -1)
        if rahu_sign == sun_sign_idx:
            major.append({
                "type": "rahu_sun",
                "severity": "high",
                "description": "Rahu transiting over natal Sun — identity crisis or breakthrough, ambition surge",
                "affected_chakra": "Solar Plexus",
                "planet": "Rahu",
            })
        if ketu_sign == sun_sign_idx:
            major.append({
                "type": "ketu_sun",
                "severity": "moderate",
                "description": "Ketu transiting over natal Sun — detachment from ego, spiritual growth",
                "affected_chakra": "Crown",
                "planet": "Ketu",
            })

    return major


def get_full_transit_report(chart_data: Dict, date: datetime = None) -> Dict:
    """
    Complete transit analysis for a chart.
    Returns aspects, house activation, and major transit events.
    """
    natal_planets = chart_data.get("planets", {})
    lagna = chart_data.get("lagna", {})
    lagna_degree = lagna.get("degree", 0) if isinstance(lagna, dict) else 0

    transit_pos = get_current_transit_positions(date)
    aspects = compute_transit_aspects(transit_pos, natal_planets)
    houses = compute_transit_house_activation(transit_pos, lagna_degree)
    major = detect_major_transits(transit_pos, natal_planets, lagna_degree)

    # Top 5 strongest aspects
    top_aspects = aspects[:5]

    # Summary: which life areas are most activated
    HOUSE_LABELS = {
        1: "identity", 2: "wealth", 3: "courage", 4: "home",
        5: "creativity", 6: "work", 7: "partnerships", 8: "transformation",
        9: "luck", 10: "career", 11: "gains", 12: "foreign",
    }

    activated_areas = []
    for h, planets in houses.items():
        if any(p in ("Jupiter", "Saturn", "Rahu", "Ketu") for p in planets):
            activated_areas.append({
                "house": h,
                "area": HOUSE_LABELS.get(h, f"house {h}"),
                "planets": planets,
            })

    return {
        "date": (date or datetime.utcnow()).strftime("%Y-%m-%d"),
        "transit_positions": transit_pos,
        "top_aspects": top_aspects,
        "house_activation": houses,
        "major_transits": major,
        "activated_areas": activated_areas,
    }


def format_transit_for_prompt(transit_report: Dict) -> str:
    """
    Format transit data as a context block for Claude/DeepSeek prompts.
    """
    lines = ["CURRENT TRANSITS (live sky positions vs your natal chart):"]

    for aspect in transit_report.get("top_aspects", [])[:5]:
        tp = aspect["transit_planet"]
        np = aspect["natal_planet"]
        asp = aspect["aspect"]
        strength = aspect["strength"]
        lines.append(f"  {tp} in sky is in {asp} with your natal {np} "
                     f"(strength: {strength:.0%}, house {aspect.get('natal_house', '?')})")

    for mt in transit_report.get("major_transits", []):
        lines.append(f"  ** MAJOR: {mt['description']}")

    areas = transit_report.get("activated_areas", [])
    if areas:
        area_str = ", ".join(f"{a['area']} ({'+'.join(a['planets'])})" for a in areas[:4])
        lines.append(f"  Active life areas today: {area_str}")

    return "\n".join(lines)
