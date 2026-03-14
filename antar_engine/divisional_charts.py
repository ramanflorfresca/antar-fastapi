"""
antar_engine/divisional_charts.py
Calculate D1 through D12 divisional charts from planetary longitudes.
Each divisional chart shows a specific life dimension.
"""

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

DIVISIONAL_MEANINGS = {
    "d1":  "Natal chart — overall life",
    "d2":  "Hora — wealth and finances",
    "d3":  "Drekkana — siblings, courage, initiative",
    "d4":  "Chaturthamsa — property, fixed assets, fortune",
    "d5":  "Panchamsa — creativity, children, intelligence",
    "d7":  "Saptamsa — children, progeny, creativity",
    "d9":  "Navamsa — soul, dharma, marriage, deeper nature",
    "d10": "Dashamsa — career, profession, public life",
    "d12": "Dwadashamsa — parents, ancestry",
}

def _get_divisional_sign(longitude: float, division: int) -> str:
    """Calculate divisional sign for any division D1-D12."""
    sign_num = int(longitude / 30)
    degree_in_sign = longitude % 30
    division_size = 30.0 / division
    division_num = int(degree_in_sign / division_size)

    # D9 uses the Navamsa calculation
    if division == 9:
        fire_signs  = [0, 4, 8]
        earth_signs = [1, 5, 9]
        air_signs   = [2, 6, 10]
        water_signs = [3, 7, 11]
        if sign_num in fire_signs:   start = 0
        elif sign_num in earth_signs: start = 9
        elif sign_num in air_signs:   start = 6
        else:                         start = 3
        return SIGNS[(start + division_num) % 12]

    # D10: 1-15 degrees → sign itself, 16-30 → 9th from sign
    if division == 10:
        if degree_in_sign < 15:
            return SIGNS[sign_num]
        else:
            return SIGNS[(sign_num + 8) % 12]

    # Standard calculation for other divisions
    result_sign = (sign_num * division + division_num) % 12
    return SIGNS[result_sign]



def calculate_d2_hora(planets: dict, lagna_longitude: float) -> dict:
    """
    D2 Hora chart — special rules, NOT like other divisional charts.
    
    Rules:
    - Only 2 possible positions: Sun hora (Leo) or Moon hora (Cancer)
    - Odd signs (Aries/Gemini/Leo/Libra/Sag/Aquarius):
        first 15° = Sun hora (Leo)
        last 15°  = Moon hora (Cancer)
    - Even signs (Taurus/Cancer/Virgo/Scorpio/Cap/Pisces):
        first 15° = Moon hora (Cancer)
        last 15°  = Sun hora (Leo)
    - Lagna: whichever hora the lagna degree falls in
    - Only 2 houses: house 1 (same as lagna hora) or house 2 (other hora)
    
    Interpretation:
    - Sun hora (Leo): wealth through self-effort, authority, father
    - Moon hora (Cancer): wealth through public, mother, inherited, business
    - Planets in house 1: directly supports the lagna hora wealth type
    - Planets in house 2: supports the other wealth channel
    - More planets in house 1 = stronger that wealth channel
    """
    ODD_SIGNS  = [0, 2, 4, 6, 8, 10]  # Aries, Gemini, Leo, Libra, Sag, Aquarius
    EVEN_SIGNS = [1, 3, 5, 7, 9, 11]  # Taurus, Cancer, Virgo, Scorpio, Cap, Pisces

    def get_hora(longitude: float) -> str:
        sign_num = int(longitude / 30)
        degree   = longitude % 30
        if sign_num in ODD_SIGNS:
            return "Leo" if degree < 15 else "Cancer"
        else:
            return "Cancer" if degree < 15 else "Leo"

    lagna_hora = get_hora(lagna_longitude)
    other_hora = "Cancer" if lagna_hora == "Leo" else "Leo"

    planet_positions = {}
    for planet, data in planets.items():
        longitude = data.get("longitude", 0)
        if planet == "Ketu":
            rahu_long = planets.get("Rahu", {}).get("longitude", 0)
            longitude = (rahu_long + 180) % 360
        hora = get_hora(longitude)
        house = 1 if hora == lagna_hora else 2
        planet_positions[planet] = {
            "sign":      hora,
            "house":     house,
            "hora_type": "Sun hora" if hora == "Leo" else "Moon hora",
        }

    # Analysis
    sun_hora_planets  = [p for p, d in planet_positions.items() if d["sign"] == "Leo"]
    moon_hora_planets = [p for p, d in planet_positions.items() if d["sign"] == "Cancer"]

    # Wealth indicators from D2
    wealth_signals = []
    if "Jupiter" in sun_hora_planets:
        wealth_signals.append("Jupiter in Sun hora — wealth through authority, expertise, teaching")
    if "Jupiter" in moon_hora_planets:
        wealth_signals.append("Jupiter in Moon hora — wealth through public, business, real estate")
    if "Venus" in sun_hora_planets:
        wealth_signals.append("Venus in Sun hora — wealth through luxury, arts, authority")
    if "Venus" in moon_hora_planets:
        wealth_signals.append("Venus in Moon hora — wealth through public-facing beauty, relationships")
    if len(sun_hora_planets) >= 4:
        wealth_signals.append(f"Strong Sun hora ({len(sun_hora_planets)} planets) — self-made wealth dominant")
    if len(moon_hora_planets) >= 4:
        wealth_signals.append(f"Strong Moon hora ({len(moon_hora_planets)} planets) — inherited/public wealth dominant")

    return {
        "lagna":             lagna_hora,
        "lagna_lord":        "Sun" if lagna_hora == "Leo" else "Moon",
        "other_hora":        other_hora,
        "planets":           planet_positions,
        "sun_hora_planets":  sun_hora_planets,
        "moon_hora_planets": moon_hora_planets,
        "wealth_signals":    wealth_signals,
        "meaning":           "D2 Hora — wealth chart. Sun hora=Leo=self-effort wealth. Moon hora=Cancer=public/inherited wealth.",
        "d2_rule":           "Planets in house 1 strengthen lagna hora wealth. Planets in house 2 strengthen alternate wealth channel.",
    }


def calculate_all_divisional_charts(planets: dict, lagna_longitude: float) -> dict:
    """
    Calculate D1 through D12 for all planets + lagna.
    Returns dict of divisional charts, each with planet sign placements.
    """
    divisions = {
        "d1": 1, "d2": "hora",  # special calculation — handled separately "d3": 3, "d4": 4, "d5": 5,
        "d7": 7, "d9": 9, "d10": 10, "d12": 12
    }

    results = {}

    for div_name, div_num in divisions.items():
        # D2 Hora has special rules — skip in main loop
        if div_name == "d2" or div_num == "hora":
            continue

        chart = {}

        # Lagna in divisional chart
        lagna_sign = _get_divisional_sign(lagna_longitude, div_num)
        chart["lagna"] = lagna_sign
        chart["lagna_lord"] = SIGN_LORDS.get(lagna_sign, "")

        # Calculate lagna index for house placement
        lagna_idx = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0

        # Planets in divisional chart
        planet_positions = {}
        for planet, data in planets.items():
            longitude = data.get("longitude", 0)
            if planet in ("Rahu", "Ketu"):
                # Rahu/Ketu are always opposite in navamsa
                if planet == "Rahu":
                    sign = _get_divisional_sign(longitude, div_num)
                else:
                    # Ketu is 180 degrees from Rahu
                    ketu_long = (longitude + 180) % 360
                    sign = _get_divisional_sign(ketu_long, div_num)
            else:
                sign = _get_divisional_sign(longitude, div_num)

            sign_idx = SIGNS.index(sign) if sign in SIGNS else 0
            house = ((sign_idx - lagna_idx) % 12) + 1
            sign_lord = SIGN_LORDS.get(sign, "")

            planet_positions[planet] = {
                "sign":       sign,
                "house":      house,
                "sign_lord":  sign_lord,
            }

        chart["planets"]  = planet_positions
        chart["meaning"]  = DIVISIONAL_MEANINGS.get(div_name, "")
        results[div_name] = chart

    # Calculate D2 Hora separately with correct rules
    results["d2"] = calculate_d2_hora(planets, lagna_longitude)

    return results


def get_d10_career_picture(d10: dict) -> str:
    """Generate a career analysis from D10 chart."""
    if not d10:
        return ""

    lagna = d10.get("lagna", "")
    lagna_lord = d10.get("lagna_lord", "")
    planets = d10.get("planets", {})

    lines = [f"D10 Lagna: {lagna} (lord: {lagna_lord})"]

    # 10th house from D10 lagna = career peak
    lagna_idx = SIGNS.index(lagna) if lagna in SIGNS else 0
    tenth_sign_idx = (lagna_idx + 9) % 12
    tenth_sign = SIGNS[tenth_sign_idx]
    tenth_lord = SIGN_LORDS.get(tenth_sign, "")
    lines.append(f"D10 10th house: {tenth_sign} (lord: {tenth_lord})")

    # Planets in houses 1, 10, 11 of D10 (career indicators)
    key_houses = {1: "identity in career", 10: "peak career", 11: "career gains"}
    for planet, data in planets.items():
        if data.get("house") in key_houses:
            lines.append(f"  {planet} in D10 house {data['house']} ({key_houses[data['house']]})")

    return " | ".join(lines)


def get_d9_soul_picture(d9: dict) -> str:
    """Generate a soul/dharma analysis from D9 chart."""
    if not d9:
        return ""

    lagna = d9.get("lagna", "")
    planets = d9.get("planets", {})

    lines = [f"D9 Lagna: {lagna}"]

    # Venus in D9 = marriage/relationship quality
    venus = planets.get("Venus", {})
    if venus:
        lines.append(f"Venus in D9: {venus.get('sign','')} house {venus.get('house','')}")

    # 7th house in D9 = spouse nature
    lagna_idx = SIGNS.index(lagna) if lagna in SIGNS else 0
    seventh_idx = (lagna_idx + 6) % 12
    seventh_sign = SIGNS[seventh_idx]
    lines.append(f"D9 7th (spouse): {seventh_sign} (lord: {SIGN_LORDS.get(seventh_sign,'')})")

    # Atmakaraka in D9 (planet with highest degree = soul significator)
    return " | ".join(lines)


def get_house_analysis(planets: dict, lagna_sign: str) -> dict:
    """
    Full house analysis from D1 chart.
    Returns which planets are in which houses, house lords, etc.
    """
    lagna_idx = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0

    houses = {}
    for h in range(1, 13):
        sign_idx = (lagna_idx + h - 1) % 12
        sign = SIGNS[sign_idx]
        lord = SIGN_LORDS.get(sign, "")
        houses[h] = {
            "sign": sign,
            "lord": lord,
            "planets": [],
        }

    for planet, data in planets.items():
        house = data.get("house", 1)
        if 1 <= house <= 12:
            houses[house]["planets"].append(planet)

    # Key house analysis
    key_houses = {
        1:  "Self, body, personality",
        2:  "Wealth, family, speech",
        4:  "Home, mother, property, happiness",
        5:  "Children, intelligence, past karma, creativity",
        7:  "Marriage, partnerships, business",
        8:  "Transformation, longevity, hidden matters",
        9:  "Dharma, father, fortune, higher wisdom",
        10: "Career, public life, authority, karma",
        11: "Gains, income, elder siblings, aspirations",
        12: "Loss, spirituality, foreign lands, moksha",
    }

    analysis = {}
    for h, meaning in key_houses.items():
        house_data = houses.get(h, {})
        analysis[h] = {
            "sign":    house_data.get("sign", ""),
            "lord":    house_data.get("lord", ""),
            "planets": house_data.get("planets", []),
            "meaning": meaning,
        }

    return {"all": houses, "key": analysis}
