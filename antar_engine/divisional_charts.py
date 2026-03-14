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




def _get_d60_sign(longitude: float) -> str:
    """
    D60 Shashtiamsa — most sensitive divisional chart.
    Each sign is divided into 60 parts (0.5° each).
    Reveals past life karma for each planet.
    
    Calculation:
    - Each sign = 30°, divided into 60 parts = 0.5° each
    - Part number = floor(degree_in_sign / 0.5) + 1
    - For odd signs: parts 1-60 go Aries → Pisces
    - For even signs: parts 1-60 go Libra → Virgo (reversed)
    """
    sign_num = int(longitude / 30)
    degree_in_sign = longitude % 30
    part = int(degree_in_sign / 0.5)  # 0-59

    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

    ODD_SIGNS  = [0, 2, 4, 6, 8, 10]   # Aries, Gemini, Leo, Libra, Sag, Aquarius
    EVEN_SIGNS = [1, 3, 5, 7, 9, 11]   # Taurus, Cancer, Virgo, Scorpio, Cap, Pisces

    if sign_num in ODD_SIGNS:
        # Goes forward from Aries
        d60_sign_idx = part % 12
    else:
        # Goes forward from Libra (reversed direction)
        d60_sign_idx = (6 + part) % 12

    return SIGNS[d60_sign_idx]


def _get_d24_sign(longitude: float) -> str:
    """D24 Chaturvimsamsa — education, learning, spiritual knowledge."""
    sign_num = int(longitude / 30)
    degree_in_sign = longitude % 30
    part = int(degree_in_sign / (30/24))  # 0-23

    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

    ODD_SIGNS = [0, 2, 4, 6, 8, 10]
    if sign_num in ODD_SIGNS:
        start = 3  # Leo (index 4) for odd signs
        d24_idx = (4 + part) % 12
    else:
        start = 9  # Cancer (index 3) for even signs
        d24_idx = (3 + part) % 12

    return SIGNS[d24_idx]


def _get_d30_sign(longitude: float) -> str:
    """
    D30 Trimsamsa — misfortune, illness, evil, problems.
    Special rules: Sun and Moon don't have D30.
    Mars, Saturn, Jupiter, Mercury, Venus each own degrees.
    Odd signs: Mars 0-5, Saturn 5-10, Jupiter 10-18, Mercury 18-25, Venus 25-30
    Even signs: Venus 0-5, Mercury 5-12, Jupiter 12-20, Saturn 20-25, Mars 25-30
    """
    sign_num = int(longitude / 30)
    degree_in_sign = longitude % 30

    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

    ODD_SIGNS = [0, 2, 4, 6, 8, 10]

    if sign_num in ODD_SIGNS:
        # Mars=Aries, Saturn=Aquarius, Jupiter=Sagittarius, Mercury=Gemini, Venus=Libra
        if degree_in_sign < 5:    return "Aries"
        elif degree_in_sign < 10: return "Aquarius"
        elif degree_in_sign < 18: return "Sagittarius"
        elif degree_in_sign < 25: return "Gemini"
        else:                     return "Libra"
    else:
        # Venus=Taurus, Mercury=Virgo, Jupiter=Pisces, Saturn=Capricorn, Mars=Scorpio
        if degree_in_sign < 5:    return "Taurus"
        elif degree_in_sign < 12: return "Virgo"
        elif degree_in_sign < 20: return "Pisces"
        elif degree_in_sign < 25: return "Capricorn"
        else:                     return "Scorpio"


def _get_d16_sign(longitude: float) -> str:
    """D16 Shodashamsa — vehicles, happiness, comforts."""
    sign_num = int(longitude / 30)
    degree_in_sign = longitude % 30
    part = int(degree_in_sign / (30/16))  # 0-15

    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

    ODD_SIGNS = [0, 2, 4, 6, 8, 10]
    if sign_num in ODD_SIGNS:
        d16_idx = (0 + part) % 12  # starts from Aries
    else:
        d16_idx = (6 + part) % 12  # starts from Libra

    return SIGNS[d16_idx]


def _get_d20_sign(longitude: float) -> str:
    """D20 Vimshamsa — spiritual progress, mantra siddhi."""
    sign_num = int(longitude / 30)
    degree_in_sign = longitude % 30
    part = int(degree_in_sign / (30/20))  # 0-19

    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

    ODD_SIGNS = [0, 2, 4, 6, 8, 10]
    if sign_num in ODD_SIGNS:
        d20_idx = (0 + part) % 12  # starts Aries
    else:
        d20_idx = (6 + part) % 12  # starts Libra

    return SIGNS[d20_idx]


def _get_d27_sign(longitude: float) -> str:
    """D27 Bhamsa/Nakshatramsa — strength, weakness, physical capacity."""
    sign_num = int(longitude / 30)
    degree_in_sign = longitude % 30
    part = int(degree_in_sign / (30/27))  # 0-26

    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

    # Fire signs start from Aries, Earth from Cancer, Air from Libra, Water from Capricorn
    FIRE  = [0, 4, 8]   # Aries, Leo, Sag
    EARTH = [1, 5, 9]   # Taurus, Virgo, Cap
    AIR   = [2, 6, 10]  # Gemini, Libra, Aquarius
    WATER = [3, 7, 11]  # Cancer, Scorpio, Pisces

    if sign_num in FIRE:    start = 0   # Aries
    elif sign_num in EARTH: start = 3   # Cancer
    elif sign_num in AIR:   start = 6   # Libra
    else:                   start = 9   # Capricorn

    d27_idx = (start + part) % 12
    return SIGNS[d27_idx]


def calculate_d60_analysis(planets: dict, lagna_longitude: float) -> dict:
    """
    Full D60 Shashtiamsa analysis.
    Returns karmic analysis for each planet.
    This is the most important chart for understanding WHY
    certain patterns repeat in a person's life.
    """
    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    SIGN_LORDS = {
        "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
        "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
        "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
    }

    D60_KARMA_SIGNS = {
        "Aries":       ("Ghora", "fierce/karmic intensity"),
        "Taurus":      ("Rakshasa", "demonic karma from past — needs purification"),
        "Gemini":      ("Deva", "divine karma — spiritual merit"),
        "Cancer":      ("Kubera", "wealth karma — past life generosity"),
        "Leo":         ("Yaksha", "semi-divine — mixed karma"),
        "Virgo":       ("Kinara", "celestial musician karma — arts and beauty"),
        "Libra":       ("Bhrashta", "fallen karma — past life dharma violation"),
        "Scorpio":     ("Kalinasha", "time-destroyer karma — transformation"),
        "Sagittarius": ("Saumya", "gentle divine karma — dharmic past life"),
        "Capricorn":   ("Cruura", "cruel karma — aggression in past life"),
        "Aquarius":    ("Atisheetala", "very cold karma — emotional detachment"),
        "Pisces":      ("Kaala", "time karma — karmic completion"),
    }

    lagna_sign = _get_d60_sign(lagna_longitude)
    lagna_idx  = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0

    planet_analysis = {}
    overall_karma   = []
    positive_karma  = []
    challenging_karma = []

    POSITIVE_D60 = ["Gemini", "Cancer", "Leo", "Sagittarius", "Pisces"]
    CHALLENGING_D60 = ["Taurus", "Libra", "Scorpio", "Capricorn"]

    for planet, data in planets.items():
        longitude = data.get("longitude", 0)
        d60_sign  = _get_d60_sign(longitude)
        d60_idx   = SIGNS.index(d60_sign) if d60_sign in SIGNS else 0
        house_from_lagna = ((d60_idx - lagna_idx) % 12) + 1
        karma_name, karma_desc = D60_KARMA_SIGNS.get(d60_sign, ("Misra", "mixed karma"))

        is_positive    = d60_sign in POSITIVE_D60
        is_challenging = d60_sign in CHALLENGING_D60

        if is_positive:
            positive_karma.append(f"{planet} has {karma_name} karma ({karma_desc})")
        elif is_challenging:
            challenging_karma.append(f"{planet} has {karma_name} karma ({karma_desc}) — needs conscious attention")

        planet_analysis[planet] = {
            "d60_sign":        d60_sign,
            "d60_lord":        SIGN_LORDS.get(d60_sign, ""),
            "house":           house_from_lagna,
            "karma_name":      karma_name,
            "karma_desc":      karma_desc,
            "is_positive":     is_positive,
            "is_challenging":  is_challenging,
        }

    # D60 Lagna analysis
    lagna_karma = D60_KARMA_SIGNS.get(lagna_sign, ("Misra", "mixed"))

    return {
        "lagna":              lagna_sign,
        "lagna_karma":        lagna_karma,
        "planet_analysis":    planet_analysis,
        "positive_karma":     positive_karma,
        "challenging_karma":  challenging_karma,
        "meaning":            "D60 Shashtiamsa — past life karma chart. Most important for understanding recurring life patterns.",
        "instruction":        "Use D60 to explain WHY certain themes keep repeating. Planets with challenging D60 karma = karmic debts being repaid. Positive D60 = karmic rewards.",
    }


def calculate_extended_divisional_charts(planets: dict, lagna_longitude: float) -> dict:
    """
    Calculate D16, D20, D24, D27, D30, D60.
    Returns dict ready to merge into divisional_charts.
    """
    SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
             "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    SIGN_LORDS = {
        "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
        "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
        "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
    }

    lagna_sign = _get_d60_sign(lagna_longitude)  # placeholder, calculated per div
    results    = {}

    DIV_FUNCS = {
        "d16": (_get_d16_sign, "D16 Shodashamsa — vehicles, happiness, comforts, pleasures"),
        "d20": (_get_d20_sign, "D20 Vimshamsa — spiritual progress, mantra siddhi, worship"),
        "d24": (_get_d24_sign, "D24 Chaturvimsamsa — education, learning, academic achievement"),
        "d27": (_get_d27_sign, "D27 Bhamsa — physical strength, weakness, stamina"),
        "d30": (_get_d30_sign, "D30 Trimsamsa — misfortune, illness, moral failings, problems"),
    }

    for div_name, (func, meaning) in DIV_FUNCS.items():
        lagna_d_sign = func(lagna_longitude)
        lagna_d_idx  = SIGNS.index(lagna_d_sign) if lagna_d_sign in SIGNS else 0

        chart = {
            "lagna":       lagna_d_sign,
            "lagna_lord":  SIGN_LORDS.get(lagna_d_sign, ""),
            "meaning":     meaning,
            "planets":     {},
        }

        for planet, data in planets.items():
            longitude = data.get("longitude", 0)
            if planet == "Ketu":
                rahu_long = planets.get("Rahu", {}).get("longitude", 0)
                longitude = (rahu_long + 180) % 360

            p_sign   = func(longitude)
            p_idx    = SIGNS.index(p_sign) if p_sign in SIGNS else 0
            p_house  = ((p_idx - lagna_d_idx) % 12) + 1
            p_lord   = SIGN_LORDS.get(p_sign, "")

            chart["planets"][planet] = {
                "sign":       p_sign,
                "house":      p_house,
                "sign_lord":  p_lord,
            }

        results[div_name] = chart

    # D60 gets special treatment
    results["d60"] = calculate_d60_analysis(planets, lagna_longitude)

    return results


def get_d60_context_block(d60_analysis: dict) -> str:
    """Format D60 for LLM context — past life karma summary."""
    if not d60_analysis:
        return ""

    lines = [
        "D60 SHASHTIAMSA (Past Life Karma Chart — MOST IMPORTANT for recurring patterns):",
        f"  D60 Lagna: {d60_analysis.get('lagna','')} — {d60_analysis.get('lagna_karma',('',''))[1]}",
        "",
        "  POSITIVE KARMA (past life merit flowing into this life):",
    ]
    for pk in d60_analysis.get("positive_karma", []):
        lines.append(f"    ✓ {pk}")

    lines.append("  CHALLENGING KARMA (past life debts being resolved):")
    for ck in d60_analysis.get("challenging_karma", []):
        lines.append(f"    ⚠ {ck}")

    lines += [
        "",
        "  INSTRUCTION: When user asks WHY something keeps happening,",
        "  reference D60. Challenging karma = karmic pattern being resolved.",
        "  Positive karma = natural gifts from previous lives.",
        "  Remedy: Acknowledge the karma, apply planet-specific remedy, serve.",
    ]
    return "\n".join(lines)


def get_d30_warnings(d30_chart: dict, current_md_lord: str = "") -> list:
    """
    D30 Trimsamsa — warning system for misfortune.
    Planets in malefic D30 signs = trouble during their dasha.
    """
    MALEFIC_D30 = ["Aries", "Scorpio", "Capricorn", "Aquarius"]
    warnings = []
    planets = d30_chart.get("planets", {})
    for planet, data in planets.items():
        sign = data.get("sign", "")
        if sign in MALEFIC_D30:
            warnings.append({
                "planet":  planet,
                "d30_sign": sign,
                "warning": f"{planet} in malefic D30 sign ({sign}) — misfortune possible during {planet} dasha/antardasha",
                "remedy":  f"Strengthen {planet} through its natural remedy to reduce D30 malefic effects",
            })
    return warnings


def get_d24_education_analysis(d24_chart: dict) -> dict:
    """D24 education and academic potential."""
    planets  = d24_chart.get("planets", {})
    lagna    = d24_chart.get("lagna", "")

    merc_house = planets.get("Mercury", {}).get("house", 0)
    jup_house  = planets.get("Jupiter", {}).get("house", 0)
    sun_house  = planets.get("Sun", {}).get("house", 0)

    indicators = []
    if merc_house in [1, 4, 5, 9, 10]:
        indicators.append(f"Mercury in D24 house {merc_house} — sharp academic mind, educational excellence")
    if jup_house in [1, 4, 5, 9]:
        indicators.append(f"Jupiter in D24 house {jup_house} — higher education blessed, wisdom learning")
    if sun_house in [1, 9, 10]:
        indicators.append(f"Sun in D24 house {sun_house} — academic authority, government education")

    score = min(90, len(indicators) * 28 + 20)
    return {
        "lagna": lagna, "score": score,
        "indicators": indicators,
        "verdict": ("Exceptional academic potential" if score >= 75
                    else "Good education" if score >= 50
                    else "Education through non-traditional paths"),
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

    # Add extended divisional charts (D16, D20, D24, D27, D30, D60)
    try:
        extended = calculate_extended_divisional_charts(planets, lagna_longitude)
        results.update(extended)
    except Exception as _ext_e:
        print(f"[divisional] Extended charts error (non-fatal): {_ext_e}")

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
