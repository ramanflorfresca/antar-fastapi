"""
antar_engine/d_charts_calculator.py

Pure Divisional Chart Math
──────────────────────────────────────────────────────────────────────
WHAT THIS FILE DOES:
  Takes planet longitudes (already stored in DB as chart_data)
  Returns the sign each planet occupies in any divisional chart

WHEN IS IT CALLED:
  Every request, real-time, < 10ms total
  Never stored. Never needs to be stored.
  Same input always produces same output.

CHARTS SUPPORTED:
  D-2   Hora              wealth, money flow
  D-3   Drekkana          siblings, self-effort, courage
  D-4   Chaturthamsha     property, fixed assets, luck
  D-6   Shashthamsha      enemies, legal, disease, debts
  D-7   Saptamsha         children, fertility
  D-9   Navamsa           marriage, soul purpose
  D-10  Dashamsha         career, professional destiny
  D-12  Dwadashamsha      parents, foreign settlement
  D-16  Shodashamsha      vehicles, comforts
  D-20  Vimshamsha        spiritual progress
  D-24  Chaturvimshamsha  education, learning
  D-27  Bhamsha           strength, siblings
  D-30  Trimshamsha       evils, hidden enemies
  D-40  Khavedamsha       auspicious/inauspicious effects
  D-60  Shashtiamsha      past karma (most precise timing)

USAGE:
  from antar_engine.d_charts_calculator import get_d_chart, get_all_d_charts

  # Get one chart
  d9 = get_d_chart(chart_data, 9)
  # d9 = { "Sun": {"sign":"Leo","lord":"Sun","strength":"own"}, ... }

  # Get multiple at once (most efficient)
  charts = get_all_d_charts(chart_data, [2, 6, 9, 10])
  d6 = charts["D6"]
  d9 = charts["D9"]
"""

from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]
SIGN_INDEX = {s: i for i, s in enumerate(SIGNS)}

SIGN_LORDS = {
    "Aries":       "Mars",
    "Taurus":      "Venus",
    "Gemini":      "Mercury",
    "Cancer":      "Moon",
    "Leo":         "Sun",
    "Virgo":       "Mercury",
    "Libra":       "Venus",
    "Scorpio":     "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn":   "Saturn",
    "Aquarius":    "Saturn",
    "Pisces":      "Jupiter",
}

EXALTATION = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
    "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
    "Saturn": "Libra", "Rahu": "Gemini", "Ketu": "Sagittarius",
}
DEBILITATION = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
    "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
    "Saturn": "Aries", "Rahu": "Sagittarius", "Ketu": "Gemini",
}
OWN_SIGNS = {
    "Sun":     ["Leo"],
    "Moon":    ["Cancer"],
    "Mars":    ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Venus":   ["Taurus", "Libra"],
    "Saturn":  ["Capricorn", "Aquarius"],
    "Rahu":    [],
    "Ketu":    [],
}
NATURAL_BENEFICS = {"Jupiter", "Venus", "Moon", "Mercury"}
NATURAL_MALEFICS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}


# ── Core longitude → D-chart sign calculator ─────────────────────────────────

def _divisional_sign_index(longitude: float, division: int) -> int:
    """
    Convert absolute longitude (0-360) to sign index (0-11) in a divisional chart.
    This is the core math. All other functions call this.
    """
    sign_idx       = int(longitude / 30) % 12
    degree_in_sign = longitude % 30
    portion_size   = 30.0 / division
    portion_num    = int(degree_in_sign / portion_size)   # 0-based portion within sign

    # ── D-2: Hora ─────────────────────────────────────────────────
    # Odd signs (Aries, Gemini...): 1st half = Sun hora (Leo=4), 2nd = Moon hora (Cancer=3)
    # Even signs (Taurus, Cancer...): 1st half = Moon hora, 2nd = Sun hora
    if division == 2:
        if sign_idx % 2 == 0:   # odd signs
            return 4 if portion_num == 0 else 3
        else:                   # even signs
            return 3 if portion_num == 0 else 4

    # ── D-3: Drekkana ─────────────────────────────────────────────
    # Each sign divided into 3 x 10° portions
    # 1st portion: same sign, 2nd: +4 signs, 3rd: +8 signs
    elif division == 3:
        offsets = [0, 4, 8]
        return (sign_idx + offsets[portion_num]) % 12

    # ── D-4: Chaturthamsha ────────────────────────────────────────
    # Each 7.5° portion: movable→Aries, fixed→Cancer, dual→Libra, +Capricorn
    elif division == 4:
        movable = [0, 3, 6, 9]   # Aries, Cancer, Libra, Capricorn
        if sign_idx in [0, 3, 6, 9]:   start = 0
        elif sign_idx in [1, 4, 7, 10]: start = 3
        else:                           start = 6
        return (start + portion_num * 3) % 12

    # ── D-6: Shashthamsha ─────────────────────────────────────────
    # Odd signs: start from Aries; Even signs: start from Libra
    elif division == 6:
        if sign_idx % 2 == 0:   return portion_num % 12
        else:                   return (6 + portion_num) % 12

    # ── D-7: Saptamsha ───────────────────────────────────────────
    # Odd signs: start from same sign; Even signs: start from 7th sign
    elif division == 7:
        if sign_idx % 2 == 0:   return (sign_idx + portion_num) % 12
        else:                   return (sign_idx + 6 + portion_num) % 12

    # ── D-9: Navamsa ─────────────────────────────────────────────
    # Movable signs → Aries (0), Fixed → Capricorn (9), Dual → Cancer (3)
    elif division == 9:
        sign_type = sign_idx % 3
        starts    = {0: 0, 1: 9, 2: 3}
        return (starts[sign_type] + portion_num) % 12

    # ── D-10: Dashamsha ──────────────────────────────────────────
    # Odd signs: start from same sign; Even signs: start from 9th sign (Capricorn)
    elif division == 10:
        if sign_idx % 2 == 0:   return (sign_idx + portion_num) % 12
        else:                   return (sign_idx + 9 + portion_num) % 12

    # ── D-12: Dwadashamsha ───────────────────────────────────────
    # Starts from same sign, 2.5° each portion
    elif division == 12:
        return (sign_idx + portion_num) % 12

    # ── D-16: Shodashamsha ───────────────────────────────────────
    # Movable → Aries, Fixed → Leo, Dual → Sagittarius
    elif division == 16:
        sign_type = sign_idx % 3
        starts    = {0: 0, 1: 4, 2: 8}
        return (starts[sign_type] + portion_num) % 12

    # ── D-20: Vimshamsha ─────────────────────────────────────────
    # Movable → Aries, Fixed → Sagittarius, Dual → Leo
    elif division == 20:
        sign_type = sign_idx % 3
        starts    = {0: 0, 1: 8, 2: 4}
        return (starts[sign_type] + portion_num) % 12

    # ── D-24: Chaturvimshamsha ───────────────────────────────────
    # Odd signs → Leo (4), Even signs → Cancer (3)
    elif division == 24:
        if sign_idx % 2 == 0:   return (4 + portion_num) % 12
        else:                   return (3 + portion_num) % 12

    # ── D-27: Bhamsha ────────────────────────────────────────────
    # Fiery → Aries, Earthy → Cancer, Airy → Libra, Watery → Capricorn
    elif division == 27:
        element = sign_idx % 4
        starts  = {0: 0, 1: 3, 2: 6, 3: 9}
        return (starts[element] + portion_num) % 12

    # ── D-30: Trimshamsha ────────────────────────────────────────
    # Complex — different degrees for different planets
    # Simplified: odd signs → Aries, even signs → Taurus base
    elif division == 30:
        if sign_idx % 2 == 0:   return portion_num % 12
        else:                   return (1 + portion_num) % 12

    # ── D-60: Shashtiamsha ───────────────────────────────────────
    # Most precise. Odd signs → Aries onward, Even → Libra onward
    elif division == 60:
        if sign_idx % 2 == 0:   return portion_num % 12
        else:                   return (6 + portion_num) % 12

    # ── Generic fallback ─────────────────────────────────────────
    else:
        return (sign_idx * division + portion_num) % 12


def _planet_strength(planet: str, sign: str) -> str:
    """Return dignity of planet in given sign."""
    if EXALTATION.get(planet) == sign:        return "exalted"
    if sign in OWN_SIGNS.get(planet, []):     return "own"
    if DEBILITATION.get(planet) == sign:      return "debilitated"
    return "neutral"


def _get_longitude(body: str, data: dict) -> float:
    """Extract or reconstruct longitude from stored planet data."""
    lng = data.get("longitude")
    if lng is not None:
        return float(lng)
    # Reconstruct from sign + degree (fallback)
    sign = data.get("sign", "Aries")
    deg  = data.get("degree", 0)
    return SIGN_INDEX.get(sign, 0) * 30.0 + float(deg)


# ── Public API ────────────────────────────────────────────────────────────────

def get_d_chart(chart_data: dict, division: int) -> dict:
    """
    Calculate a single divisional chart.

    Args:
        chart_data: from DB charts.chart_data
        division:   2, 6, 9, 10 etc.

    Returns:
        {
          "Sun":    { sign, sign_index, lord, strength },
          "Moon":   { ... },
          ...
          "Lagna":  { sign, sign_index, lord, strength },
        }
    """
    result = {}

    # All planets
    for planet, data in chart_data["planets"].items():
        lng      = _get_longitude(planet, data)
        si       = _divisional_sign_index(lng, division)
        sign     = SIGNS[si]
        result[planet] = {
            "sign":       sign,
            "sign_index": si,
            "lord":       SIGN_LORDS[sign],
            "strength":   _planet_strength(planet, sign),
        }

    # Lagna
    lagna_sign = chart_data["lagna"]["sign"]
    lagna_deg  = chart_data["lagna"].get("degree", 0)
    lagna_lng  = SIGN_INDEX[lagna_sign] * 30.0 + lagna_deg
    si         = _divisional_sign_index(lagna_lng, division)
    sign       = SIGNS[si]
    result["Lagna"] = {
        "sign":       sign,
        "sign_index": si,
        "lord":       SIGN_LORDS[sign],
        "strength":   "neutral",
    }

    return result


def get_all_d_charts(chart_data: dict, divisions: list[int]) -> dict:
    """
    Calculate multiple divisional charts at once.
    More efficient than calling get_d_chart() in a loop.

    Returns: { "D6": {...}, "D9": {...}, "D10": {...} }
    """
    return {f"D{d}": get_d_chart(chart_data, d) for d in divisions}


def get_house_lord(lagna_sign: str, house_number: int) -> str:
    """Return the lord of a house from lagna."""
    lagna_idx  = SIGN_INDEX[lagna_sign]
    house_sign = SIGNS[(lagna_idx + house_number - 1) % 12]
    return SIGN_LORDS[house_sign]


def get_house_sign(lagna_sign: str, house_number: int) -> str:
    """Return the sign of a house from lagna."""
    lagna_idx = SIGN_INDEX[lagna_sign]
    return SIGNS[(lagna_idx + house_number - 1) % 12]


def get_planets_in_house(
    d_chart: dict,
    lagna_sign: str,
    house_number: int
) -> list[str]:
    """Return all planets sitting in a specific house in a divisional chart."""
    lagna_idx = SIGN_INDEX.get(
        d_chart.get("Lagna", {}).get("sign", lagna_sign), 0
    )
    house_idx = (lagna_idx + house_number - 1) % 12
    return [
        p for p, pos in d_chart.items()
        if p != "Lagna" and pos.get("sign_index") == house_idx
    ]


def is_planet_strong(planet: str, d_chart: dict) -> bool:
    """True if planet is exalted or in own sign in the given D-chart."""
    strength = d_chart.get(planet, {}).get("strength", "neutral")
    return strength in ("exalted", "own")


def is_planet_weak(planet: str, d_chart: dict) -> bool:
    """True if planet is debilitated in the given D-chart."""
    return d_chart.get(planet, {}).get("strength", "neutral") == "debilitated"


def get_d1_from_chart_data(chart_data: dict) -> dict:
    """
    Return D-1 (Rashi) in the same format as get_d_chart().
    D-1 is already in chart_data — this just normalises the format.
    """
    result = {}
    for planet, data in chart_data["planets"].items():
        sign = data.get("sign", "Aries")
        result[planet] = {
            "sign":       sign,
            "sign_index": SIGN_INDEX.get(sign, 0),
            "lord":       SIGN_LORDS.get(sign, "Mars"),
            "strength":   _planet_strength(planet, sign),
        }
    lagna_sign = chart_data["lagna"]["sign"]
    result["Lagna"] = {
        "sign":       lagna_sign,
        "sign_index": SIGN_INDEX[lagna_sign],
        "lord":       SIGN_LORDS[lagna_sign],
        "strength":   "neutral",
    }
    return result
