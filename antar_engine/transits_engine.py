"""
antar_engine/transits_engine.py
Calculate current planetary transits and their effect on natal chart.
Transit = current sky position vs natal planet position.
"""

from datetime import datetime, timedelta
import os

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

# Orb for considering a transit active (in degrees)
TRANSIT_ORBS = {
    "Sun":     3.0,
    "Moon":    2.0,
    "Mars":    5.0,
    "Mercury": 3.0,
    "Jupiter": 7.0,
    "Venus":   3.0,
    "Saturn":  7.0,
    "Rahu":    5.0,
    "Ketu":    5.0,
}

# How long each planet stays in a sign
SIGN_DURATION_DAYS = {
    "Sun": 30, "Moon": 2.5, "Mars": 45, "Mercury": 25,
    "Jupiter": 365, "Venus": 25, "Saturn": 912,
    "Rahu": 548, "Ketu": 548,
}

# Transit effects on natal houses
TRANSIT_HOUSE_EFFECTS = {
    "Jupiter": {
        1:  "Direct blessing on self — health, optimism, new opportunities open",
        2:  "Wealth expansion — income increases, family harmony improves",
        4:  "Home improvement, property gains, mother's health improves",
        5:  "Creative projects flourish, children bring joy, good for speculation",
        7:  "Partnership opportunities, marriage prospects improve, business grows",
        9:  "Fortune peaks, travel, higher education, dharmic clarity",
        10: "Career peak — promotions, recognition, authority increases",
        11: "Maximum gains — income surge, goals achieved, social expansion",
    },
    "Saturn": {
        1:  "Sade Sati period if natal Moon is Sagittarius, Capricorn, or Aquarius — discipline required",
        4:  "Home and family under pressure — requires patience",
        7:  "Relationship and partnership challenges — demands commitment",
        10: "Career restructuring — hard work required but lasting results",
        12: "Spiritual reflection period — preparation for major life shift",
    },
    "Rahu": {
        1:  "Unusual opportunities — ambition peaks, foreign connections activate",
        7:  "Unconventional relationships or partnerships emerge",
        10: "Career disruption and unexpected rise possible simultaneously",
    },
}


def calculate_current_transits(natal_chart: dict) -> dict:
    """
    Calculate current planetary positions and their transit effects.
    Uses Swiss Ephemeris for current sky positions.
    Returns transit analysis for next 12 months.
    """
    try:
        import pyswisseph as swe
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ephe_path  = os.path.join(script_dir, 'ephe')
        swe.set_ephe_path(ephe_path)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
    except Exception as e:
        return {"error": f"Swiss Ephemeris not available: {e}", "transits": []}

    PLANET_IDS = {
        'Sun': swe.SUN, 'Moon': swe.MOON, 'Mars': swe.MARS,
        'Mercury': swe.MERCURY, 'Jupiter': swe.JUPITER,
        'Venus': swe.VENUS, 'Saturn': swe.SATURN,
    }

    now    = datetime.utcnow()
    jd_now = swe.julday(now.year, now.month, now.day,
                         now.hour + now.minute/60.0)

    natal_lagna     = natal_chart.get("lagna", {})
    natal_lagna_sign = natal_lagna.get("sign", "Aries") if isinstance(natal_lagna, dict) else "Aries"
    lagna_idx        = SIGNS.index(natal_lagna_sign) if natal_lagna_sign in SIGNS else 0
    natal_planets    = natal_chart.get("planets", {})

    current_transits = []
    ayanamsa = swe.get_ayanamsa(jd_now)

    for planet, planet_id in PLANET_IDS.items():
        try:
            pos, _ = swe.calc_ut(jd_now, planet_id)
            tropical_long = pos[0]
            sidereal_long = (tropical_long - ayanamsa) % 360

            sign_idx   = int(sidereal_long / 30)
            sign       = SIGNS[sign_idx]
            degree     = sidereal_long % 30
            house      = ((sign_idx - lagna_idx) % 12) + 1

            # Compare with natal position
            natal_data  = natal_planets.get(planet, {})
            natal_sign  = natal_data.get("sign", "")
            natal_house = natal_data.get("house", 0)

            # Is this transit activating natal position?
            transit_over_natal = (sign == natal_sign)

            # Effect of current transit
            effect_key  = planet
            house_effect = TRANSIT_HOUSE_EFFECTS.get(planet, {}).get(house, "")

            current_transits.append({
                "planet":               planet,
                "current_sign":         sign,
                "current_house":        house,
                "current_degree":       round(degree, 2),
                "natal_sign":           natal_sign,
                "natal_house":          natal_house,
                "transit_over_natal":   transit_over_natal,
                "house_effect":         house_effect,
                "sign_changed":         sign != natal_sign,
            })

        except Exception as e:
            current_transits.append({
                "planet": planet,
                "error": str(e),
            })

    # Calculate Jupiter's current house — most important for timing
    jup_transit = next((t for t in current_transits if t["planet"] == "Jupiter"), {})
    sat_transit = next((t for t in current_transits if t["planet"] == "Saturn"), {})

    # Key timing insights
    timing_insights = []

    if jup_transit.get("current_house") in [1, 5, 9, 10, 11]:
        timing_insights.append({
            "type":    "favorable",
            "planet":  "Jupiter",
            "message": f"Jupiter transiting house {jup_transit['current_house']} — {TRANSIT_HOUSE_EFFECTS.get('Jupiter', {}).get(jup_transit['current_house'], 'favorable period')}",
            "duration": f"Until Jupiter moves to next sign (~{SIGN_DURATION_DAYS['Jupiter']} days)",
        })

    if sat_transit.get("current_house") in [10, 1, 7]:
        timing_insights.append({
            "type":    "challenging",
            "planet":  "Saturn",
            "message": f"Saturn transiting house {sat_transit['current_house']} — {TRANSIT_HOUSE_EFFECTS.get('Saturn', {}).get(sat_transit['current_house'], 'requires patience')}",
            "duration": "Saturn moves slowly — 2.5 years in each sign",
        })

    return {
        "current_transits": current_transits,
        "timing_insights":  timing_insights,
        "calculated_at":    now.isoformat(),
        "jupiter_house":    jup_transit.get("current_house"),
        "saturn_house":     sat_transit.get("current_house"),
    }


def transits_prompt_block(transit_data: dict) -> str:
    """Format transit data for LLM prompt."""
    if not transit_data or "error" in transit_data:
        return ""

    lines = ["=== CURRENT PLANETARY TRANSITS ==="]
    lines.append(f"As of {transit_data.get('calculated_at','today')[:10]}:\n")

    for t in transit_data.get("current_transits", []):
        if "error" in t:
            continue
        planet = t["planet"]
        cur_house = t.get("current_house", "?")
        cur_sign  = t.get("current_sign", "?")
        effect    = t.get("house_effect", "")
        over_natal = "← TRANSITING NATAL POSITION" if t.get("transit_over_natal") else ""
        lines.append(f"  {planet:<10} in {cur_sign:<14} house {cur_house:<3} {over_natal}")
        if effect:
            lines.append(f"             Effect: {effect}")

    if transit_data.get("timing_insights"):
        lines.append("\nKEY TIMING WINDOWS:")
        for ins in transit_data["timing_insights"]:
            lines.append(f"  [{ins['type'].upper()}] {ins['message']}")

    lines.append("=== END TRANSITS ===")
    return "\n".join(lines)
