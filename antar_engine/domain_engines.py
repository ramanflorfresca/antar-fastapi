"""
antar_engine/domain_engines.py

5 deterministic domain engines. Python calculates verdicts.
LLM only narrates — never decides.

Usage:
    from antar_engine.domain_engines import run_all_domain_engines
    verdicts = run_all_domain_engines(chart_data, dashas, birth_date)
    # Pass verdicts to LLM as facts
"""

from datetime import datetime, date
from typing import Optional

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]
SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}
EXALTATION = {
    "Sun":"Aries","Moon":"Taurus","Mars":"Capricorn","Mercury":"Virgo",
    "Jupiter":"Cancer","Venus":"Pisces","Saturn":"Libra"
}
DEBILITATION = {
    "Sun":"Libra","Moon":"Scorpio","Mars":"Cancer","Mercury":"Pisces",
    "Jupiter":"Capricorn","Venus":"Virgo","Saturn":"Aries"
}


# ═══════════════════════════════════════════════════════════════
# ENGINE 1 — WEALTH (billionaire potential)
# ═══════════════════════════════════════════════════════════════

WEALTH_COMBINATIONS = [
    # (name, weight, description)
    ("rahu_11th",       0.90, "Rahu in 11th — unconventional massive gains, tech/foreign wealth"),
    ("jupiter_2nd",     0.85, "Jupiter in 2nd — classical Dhana Yoga, accumulated wealth"),
    ("jupiter_11th",    0.85, "Jupiter in 11th — gains through wisdom and expansion"),
    ("exalted_jupiter", 0.90, "Jupiter exalted (Cancer) — strongest Dhana, exceptional fortune"),
    ("lord2_in_11th",   0.80, "2nd lord in 11th — wealth accumulation yoga"),
    ("lord11_in_2nd",   0.80, "11th lord in 2nd — income converts directly to assets"),
    ("dhana_yoga",      0.85, "2nd and 11th lords conjunct — direct Dhana Yoga"),
    ("stellium_11th",   0.75, "3+ planets in 11th — exceptional gains cluster"),
    ("raj_yoga",        0.70, "Raj Yoga present — wealth through authority and power"),
    ("venus_11th",      0.65, "Venus in 11th — gains through luxury, beauty, networks"),
    ("sun_11th",        0.65, "Sun in 11th — gains from authority, government"),
    ("jupiter_exch_9th",0.80, "Jupiter-9th lord exchange — Lakshmi Yoga"),
    ("lord5_lord9_conj",0.75, "5th and 9th lords conjunct — Lakshmi Yoga variant"),
    ("moon_11th",       0.60, "Moon in 11th — public gains, emotional abundance"),
    ("mercury_11th",    0.65, "Mercury in 11th — business and communication gains"),
    ("rahu_2nd",        0.75, "Rahu in 2nd — sudden unconventional wealth accumulation"),
    ("saturn_11th",     0.65, "Saturn in 11th — slow but massive sustained gains"),
    ("d2_sun_hora",     0.60, "Strong Sun hora in D2 — self-made wealth"),
    ("d2_moon_hora",    0.60, "Strong Moon hora in D2 — public/inherited wealth"),
]

def run_wealth_engine(
    planets: dict,
    lagna_sign: str,
    house_lords: dict,
    yogas: list,
    dashas: dict,
    d2_chart: dict,
) -> dict:
    """
    Score wealth/billionaire potential deterministically.
    Returns score, verdict, peak_window, wealth_type.
    """
    found = []
    total_weight = 0.0

    lagna_idx  = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0
    lord_2_planet  = house_lords.get(2, {}).get("lord", "") if isinstance(house_lords, dict) else ""
    lord_11_planet = house_lords.get(11, {}).get("lord", "") if isinstance(house_lords, dict) else ""
    lord_5_planet  = house_lords.get(5, {}).get("lord", "") if isinstance(house_lords, dict) else ""
    lord_9_planet  = house_lords.get(9, {}).get("lord", "") if isinstance(house_lords, dict) else ""

    def house(planet): return planets.get(planet, {}).get("house", 0)
    def sign(planet):  return planets.get(planet, {}).get("sign", "")

    # Check each combination
    checks = {
        "rahu_11th":       house("Rahu") == 11,
        "jupiter_2nd":     house("Jupiter") == 2,
        "jupiter_11th":    house("Jupiter") == 11,
        "exalted_jupiter": sign("Jupiter") == EXALTATION.get("Jupiter",""),
        "lord2_in_11th":   lord_2_planet and house(lord_2_planet) == 11,
        "lord11_in_2nd":   lord_11_planet and house(lord_11_planet) == 2,
        "dhana_yoga":      (lord_2_planet and lord_11_planet and
                           house(lord_2_planet) == house(lord_11_planet) and
                           lord_2_planet != lord_11_planet),
        "stellium_11th":   len([p for p,d in planets.items() if d.get("house")==11]) >= 3,
        "raj_yoga":        any("Raj" in y.get("name","") and y.get("strength")=="strong" for y in yogas),
        "venus_11th":      house("Venus") == 11,
        "sun_11th":        house("Sun") == 11,
        "jupiter_exch_9th": (lord_9_planet == "Jupiter" and
                              sign("Jupiter") == house_lords.get(9,{}).get("sign","") if isinstance(house_lords,dict) else False),
        "lord5_lord9_conj": (lord_5_planet and lord_9_planet and
                             house(lord_5_planet) == house(lord_9_planet) and
                             lord_5_planet != lord_9_planet),
        "moon_11th":       house("Moon") == 11,
        "mercury_11th":    house("Mercury") == 11,
        "rahu_2nd":        house("Rahu") == 2,
        "saturn_11th":     house("Saturn") == 11,
        "d2_sun_hora":     len(d2_chart.get("sun_hora_planets",[])) >= 4 if d2_chart else False,
        "d2_moon_hora":    len(d2_chart.get("moon_hora_planets",[])) >= 4 if d2_chart else False,
    }

    for name, weight, desc in WEALTH_COMBINATIONS:
        if checks.get(name):
            found.append({"name": name, "weight": weight, "desc": desc})
            total_weight += weight

    # Score: max possible ≈ 3.0 for exceptional chart → normalize to 100
    max_realistic = 3.0
    score = min(round((total_weight / max_realistic) * 100), 99)

    # Verdict
    if score >= 75:
        verdict = "Strong billionaire potential — multiple wealth yogas confirmed"
        wealth_class = "exceptional"
    elif score >= 55:
        verdict = "Significant wealth potential — above-average combinations present"
        wealth_class = "strong"
    elif score >= 35:
        verdict = "Moderate wealth — steady prosperity through effort"
        wealth_class = "moderate"
    else:
        verdict = "Wealth comes through sustained work — no exceptional shortcuts"
        wealth_class = "steady"

    # Wealth type
    wealth_type = []
    if checks.get("rahu_11th") or checks.get("rahu_2nd"):
        wealth_type.append("unconventional/foreign/tech")
    if checks.get("jupiter_2nd") or checks.get("jupiter_11th") or checks.get("exalted_jupiter"):
        wealth_type.append("wisdom/expansion/advisory")
    if checks.get("sun_11th"):
        wealth_type.append("authority/government")
    if checks.get("venus_11th"):
        wealth_type.append("luxury/networks/beauty")
    if checks.get("raj_yoga"):
        wealth_type.append("leadership/institution")

    # Peak window from dashas
    peak_window = _find_wealth_peak_window(planets, dashas)

    return {
        "score":       score,
        "verdict":     verdict,
        "wealth_class": wealth_class,
        "combinations_found": len(found),
        "combinations": found,
        "wealth_type": " + ".join(wealth_type) if wealth_type else "earned through effort",
        "peak_window": peak_window,
        "billionaire_possible": score >= 65,
    }


def _find_wealth_peak_window(planets: dict, dashas: dict) -> str:
    """Find the peak wealth-building window from dashas."""
    now = datetime.utcnow()
    WEALTH_LORDS = {"Jupiter","Venus","Rahu","Sun","Moon"}
    windows = []

    for row in dashas.get("vimsottari", []):
        lord  = row.get("lord_or_sign") or row.get("planet_or_sign","")
        level = row.get("level") or row.get("type","")
        if level != "mahadasha" or lord not in WEALTH_LORDS:
            continue
        try:
            sd = datetime.strptime(str(row.get("start_date",""))[:10], "%Y-%m-%d")
            ed = datetime.strptime(str(row.get("end_date",""))[:10], "%Y-%m-%d")
            if ed > now:
                windows.append((lord, sd.year, ed.year, (sd-now).days))
        except Exception:
            continue

    if not windows:
        return "Requires dasha data"

    windows.sort(key=lambda x: abs(x[3]))  # closest to now
    w = windows[0]
    return f"{w[1]}–{w[2]} ({w[0]} Mahadasha)"


# ═══════════════════════════════════════════════════════════════
# ENGINE 2 — CAREER
# ═══════════════════════════════════════════════════════════════

CAREER_PLANET_DOMAINS = {
    "Sun":     {"professions": ["government","politics","medicine","CEO","leadership","authority"], "score": 0.80},
    "Moon":    {"professions": ["hospitality","public service","nursing","real estate","food","import-export"], "score": 0.70},
    "Mars":    {"professions": ["engineering","military","surgery","sports","real estate","police"], "score": 0.80},
    "Mercury": {"professions": ["technology","writing","business","accounting","teaching","media","IT"], "score": 0.85},
    "Jupiter": {"professions": ["law","finance","education","consulting","advisory","banking","philosophy"], "score": 0.80},
    "Venus":   {"professions": ["arts","fashion","beauty","entertainment","luxury","design","film"], "score": 0.75},
    "Saturn":  {"professions": ["construction","mining","labor","administration","service industry","research"], "score": 0.70},
    "Rahu":    {"professions": ["technology","foreign trade","politics","media","research","startup","disruptive fields"], "score": 0.85},
    "Ketu":    {"professions": ["spirituality","research","medicine","occult","technical specialist","behind-the-scenes"], "score": 0.65},
}

D10_LAGNA_CAREER = {
    "Aries":      "Leadership, military, engineering, entrepreneurship",
    "Taurus":     "Finance, luxury goods, agriculture, arts",
    "Gemini":     "Communication, media, technology, business",
    "Cancer":     "Hospitality, real estate, food, public service",
    "Leo":        "Government, authority, entertainment, management",
    "Virgo":      "Healthcare, accounting, analysis, service industry",
    "Libra":      "Law, diplomacy, arts, partnerships, fashion",
    "Scorpio":    "Research, medicine, finance, intelligence, occult",
    "Sagittarius":"Education, law, religion, philosophy, international",
    "Capricorn":  "Administration, construction, discipline-based fields",
    "Aquarius":   "Technology, innovation, social work, research",
    "Pisces":     "Medicine, spirituality, arts, foreign trade, mystical",
}

def run_career_engine(
    planets: dict,
    lagna_sign: str,
    house_lords: dict,
    yogas: list,
    atmakaraka: str,
    divisional_charts: dict,
) -> dict:
    """Score career domains deterministically from D1 + D10."""

    d10  = divisional_charts.get("d10", {})
    d10_lagna = d10.get("lagna","")
    d10_planets = d10.get("planets", {})

    def house(planet, chart=None):
        if chart:
            return chart.get(planet, {}).get("house", 0)
        return planets.get(planet, {}).get("house", 0)

    # Planets in 10th house D1
    planets_in_10th = [p for p,d in planets.items() if d.get("house")==10]

    # 10th lord
    lord_10 = house_lords.get(10, {}).get("lord","") if isinstance(house_lords, dict) else ""
    lord_10_house = planets.get(lord_10, {}).get("house", 0) if lord_10 else 0

    # Career scores by domain
    career_scores = {}
    reasons = {}

    for planet in planets_in_10th:
        dom = CAREER_PLANET_DOMAINS.get(planet, {})
        for prof in dom.get("professions", []):
            career_scores[prof] = career_scores.get(prof, 0) + dom.get("score", 0.5)
            reasons[prof] = reasons.get(prof, []) + [f"{planet} in 10th D1"]

    # D10 lagna adds context
    d10_career = D10_LAGNA_CAREER.get(d10_lagna, "")

    # Atmakaraka domain
    ak_dom = CAREER_PLANET_DOMAINS.get(atmakaraka, {})
    for prof in ak_dom.get("professions", []):
        career_scores[prof] = career_scores.get(prof, 0) + 0.4
        reasons[prof] = reasons.get(prof, []) + [f"Atmakaraka {atmakaraka}"]

    # 10th lord strength
    if lord_10 and lord_10_house in [1, 4, 7, 10, 5, 9, 11]:
        dom = CAREER_PLANET_DOMAINS.get(lord_10, {})
        for prof in dom.get("professions", []):
            career_scores[prof] = career_scores.get(prof, 0) + 0.5
            reasons[prof] = reasons.get(prof, []) + [f"10th lord {lord_10} in house {lord_10_house}"]

    # Sort by score
    sorted_careers = sorted(career_scores.items(), key=lambda x: x[1], reverse=True)
    top_3 = sorted_careers[:3]

    # Overall career score
    career_score = min(round(sum(v for _,v in top_3) * 15), 99)

    # Peak timing from 10th lord dasha
    peak_timing = _career_peak_timing(lord_10, planets)

    return {
        "score":           career_score,
        "top_career":      top_3[0][0].title() if top_3 else "Multiple domains",
        "top_3_careers":   [c.title() for c,_ in top_3],
        "d10_lagna":       d10_lagna,
        "d10_career_type": d10_career,
        "planets_in_10th": planets_in_10th,
        "10th_lord":       lord_10,
        "10th_lord_house": lord_10_house,
        "atmakaraka":      atmakaraka,
        "peak_timing":     peak_timing,
        "reasons":         {c: reasons.get(c,[]) for c,_ in top_3},
    }


def _career_peak_timing(lord_10: str, planets: dict) -> str:
    if not lord_10:
        return "Unknown"
    lord_house = planets.get(lord_10, {}).get("house", 0)
    if lord_house in [1, 4, 7, 10]:
        return "Angular house placement — sustained career throughout life"
    elif lord_house in [5, 9]:
        return "Trikona placement — career through dharma and fortune"
    elif lord_house == 11:
        return "11th house — career success through gains and networks"
    else:
        return "Career requires sustained effort to peak"


# ═══════════════════════════════════════════════════════════════
# ENGINE 3 — RELATIONSHIP
# ═══════════════════════════════════════════════════════════════

def run_relationship_engine(
    planets: dict,
    lagna_sign: str,
    house_lords: dict,
    divisional_charts: dict,
    birth_date: str,
) -> dict:
    """Score relationship potential and timing deterministically."""

    d9 = divisional_charts.get("d9", {})
    d7 = divisional_charts.get("d7", {})
    d9_lagna  = d9.get("lagna","")
    d9_venus  = d9.get("planets",{}).get("Venus",{})
    d9_moon   = d9.get("planets",{}).get("Moon",{})
    d9_jupiter = d9.get("planets",{}).get("Jupiter",{})

    def house(planet): return planets.get(planet, {}).get("house", 0)
    def sign(planet):  return planets.get(planet, {}).get("sign","")

    lord_7  = house_lords.get(7, {}).get("lord","") if isinstance(house_lords,dict) else ""
    lord_7_house = planets.get(lord_7, {}).get("house",0) if lord_7 else 0

    planets_in_7th = [p for p,d in planets.items() if d.get("house")==7]

    # Score components
    score_factors = []
    warnings = []
    strengths = []

    # Venus placement
    venus_house = house("Venus")
    if venus_house in [1, 2, 4, 5, 7, 9, 11]:
        score_factors.append(0.80)
        strengths.append(f"Venus in house {venus_house} — relationship harmony")
    elif venus_house in [6, 8, 12]:
        score_factors.append(0.30)
        warnings.append(f"Venus in house {venus_house} — relationship challenges, karmic lessons")

    # 7th house condition
    if lord_7 and lord_7_house in [1, 4, 5, 7, 9, 11]:
        score_factors.append(0.75)
        strengths.append(f"7th lord {lord_7} in house {lord_7_house} — favorable marriage")
    elif lord_7 and lord_7_house in [6, 8, 12]:
        score_factors.append(0.25)
        warnings.append(f"7th lord {lord_7} in house {lord_7_house} — delayed or difficult marriage")

    # Jupiter aspect to 7th
    jupiter_house = house("Jupiter")
    houses_jupiter_aspects = [jupiter_house, (jupiter_house+4)%12 or 12,
                               (jupiter_house+6)%12 or 12, (jupiter_house+8)%12 or 12]
    if 7 in houses_jupiter_aspects:
        score_factors.append(0.75)
        strengths.append("Jupiter aspects 7th house — marriage blessings")

    # Saturn aspect to 7th
    saturn_house = house("Saturn")
    if 7 in [saturn_house, (saturn_house+2)%12 or 12,
              (saturn_house+6)%12 or 12, (saturn_house+9)%12 or 12]:
        score_factors.append(0.30)
        warnings.append("Saturn aspects 7th house — delays or karmic marriage partner")

    # D9 Venus placement
    d9_venus_house = d9_venus.get("house",0)
    if d9_venus_house in [1, 5, 7, 9, 11]:
        score_factors.append(0.80)
        strengths.append(f"Venus in D9 house {d9_venus_house} — soul-level relationship fulfillment")
    elif d9_venus_house in [6, 8, 12]:
        score_factors.append(0.30)
        warnings.append(f"Venus in D9 house {d9_venus_house} — karmic relationship patterns")

    score = round(sum(score_factors) / max(len(score_factors),1) * 100) if score_factors else 50

    # Partner nature from 7th house sign
    lord_7_sign = house_lords.get(7, {}).get("sign","") if isinstance(house_lords,dict) else ""
    partner_nature = _partner_nature(lord_7_sign, lord_7, d9_lagna)

    # Marriage timing
    try:
        born = date.fromisoformat(birth_date[:10])
        age  = (date.today() - born).days // 365
    except Exception:
        age = 35

    marriage_timing = _marriage_timing(lord_7_house, venus_house, age, warnings)

    return {
        "score":           score,
        "partner_nature":  partner_nature,
        "marriage_timing": marriage_timing,
        "strengths":       strengths,
        "warnings":        warnings,
        "7th_lord":        lord_7,
        "7th_lord_house":  lord_7_house,
        "venus_house":     venus_house,
        "d9_lagna":        d9_lagna,
        "d9_venus_house":  d9_venus_house,
        "planets_in_7th":  planets_in_7th,
    }


def _partner_nature(sign_7th: str, lord_7: str, d9_lagna: str) -> str:
    nature = {
        "Aries":"energetic, independent, action-oriented",
        "Taurus":"stable, sensual, financially focused",
        "Gemini":"intellectual, communicative, dual nature",
        "Cancer":"nurturing, emotional, family-oriented",
        "Leo":"charismatic, proud, creative",
        "Virgo":"analytical, service-oriented, health-conscious",
        "Libra":"balanced, artistic, partnership-focused",
        "Scorpio":"intense, transformative, secretive",
        "Sagittarius":"philosophical, adventurous, foreign connections",
        "Capricorn":"disciplined, career-focused, older/mature",
        "Aquarius":"unconventional, intellectual, technology-oriented",
        "Pisces":"spiritual, artistic, empathetic",
    }
    base = nature.get(sign_7th, "diverse and multifaceted")
    if lord_7 in ["Rahu"]:
        return f"{base} — possible foreign or unconventional partner"
    if lord_7 == "Saturn":
        return f"{base} — older, more serious, or delayed meeting"
    return base


def _marriage_timing(lord_7_house: int, venus_house: int, age: int, warnings: list) -> str:
    if warnings and len(warnings) >= 2:
        return "Marriage requires patience — multiple caution indicators present"
    if lord_7_house in [1, 7]:
        return "Marriage prominent throughout life — early or on-time marriage likely"
    if lord_7_house in [5, 9, 11]:
        return "Marriage through fortune or social networks — timing 25-35 typically"
    if lord_7_house in [6, 8, 12]:
        return "Delayed or unconventional marriage — after 30 more likely"
    return "Standard marriage timing — depends on current dasha activation"


# ═══════════════════════════════════════════════════════════════
# ENGINE 4 — HEALTH
# ═══════════════════════════════════════════════════════════════

PLANET_BODY_PARTS = {
    "Sun":     ["heart","spine","right eye","vitality","bones"],
    "Moon":    ["mind","lungs","blood","left eye","breast","stomach","fluids"],
    "Mars":    ["muscles","blood pressure","accidents","surgery","inflammation","head"],
    "Mercury": ["nervous system","skin","hands","lungs","intestines","speech"],
    "Jupiter": ["liver","fat","hips","thighs","arteries"],
    "Venus":   ["kidneys","reproductive","throat","face","diabetes risk"],
    "Saturn":  ["bones","teeth","joints","chronic illness","knees","feet"],
    "Rahu":    ["unusual diseases","foreign infections","neurological","skin"],
    "Ketu":    ["mysterious illness","past-life diseases","fevers","spiritual health"],
}

DASHA_HEALTH_THEMES = {
    "Sun":     "vitality and heart — avoid overexertion, eye care important",
    "Moon":    "mental health and digestion — emotional wellbeing affects physical",
    "Mars":    "inflammation, accidents, surgery risk — pitta imbalance, anger affects health",
    "Mercury": "nervous system — stress, anxiety, skin issues during Mercury periods",
    "Jupiter": "liver, weight — overeating, fat-related issues, liver care needed",
    "Venus":   "kidney, reproductive — sugar intake, relationship stress affects physical",
    "Saturn":  "bones, joints, chronic — slow-building issues, cold/damp environments harmful",
    "Rahu":    "unusual/undiagnosed — foreign bacteria, neurological, anxiety, unknown causes",
    "Ketu":    "mysterious illness — spiritual connection to health, fevers, past-life karma",
}

def run_health_engine(
    planets: dict,
    lagna_sign: str,
    house_lords: dict,
    current_md_lord: str,
    current_ad_lord: str,
    birth_date: str,
) -> dict:
    """Map planetary positions to health risk areas deterministically."""

    try:
        born = date.fromisoformat(birth_date[:10])
        age  = (date.today() - born).days // 365
    except Exception:
        age = 35

    def house(planet): return planets.get(planet, {}).get("house", 0)
    def sign(planet):  return planets.get(planet, {}).get("sign","")

    watch_areas  = []
    risk_planets = []
    active_themes = []

    # Planets in 6th (disease), 8th (chronic), 12th (hospitalization)
    for planet in planets:
        h = house(planet)
        if h == 6:
            parts = PLANET_BODY_PARTS.get(planet,[])
            watch_areas.extend(parts[:2])
            risk_planets.append(f"{planet} in 6th — {parts[0] if parts else 'general'} vulnerability")
        elif h == 8:
            parts = PLANET_BODY_PARTS.get(planet,[])
            watch_areas.extend(parts[:2])
            risk_planets.append(f"{planet} in 8th — chronic {parts[0] if parts else 'issues'}, surgery possible")
        elif h == 12:
            risk_planets.append(f"{planet} in 12th — hospitalization or isolation risk during its dasha")

    # Lagna lord condition
    lagna_lord = SIGN_LORDS.get(lagna_sign,"")
    lagna_lord_house = house(lagna_lord)
    if lagna_lord_house in [6, 8, 12]:
        watch_areas.append("overall vitality")
        risk_planets.append(f"Lagna lord {lagna_lord} in house {lagna_lord_house} — general health needs attention")

    # Debilitated planets
    for planet, debil_sign in DEBILITATION.items():
        if sign(planet) == debil_sign:
            parts = PLANET_BODY_PARTS.get(planet,[])
            watch_areas.extend(parts[:1])
            risk_planets.append(f"{planet} debilitated in {debil_sign} — {parts[0] if parts else ''} weakness")

    # Current dasha themes
    if current_md_lord:
        active_themes.append(f"MD ({current_md_lord}): {DASHA_HEALTH_THEMES.get(current_md_lord,'general health')}")
    if current_ad_lord and current_ad_lord != current_md_lord:
        active_themes.append(f"AD ({current_ad_lord}): {DASHA_HEALTH_THEMES.get(current_ad_lord,'')}")

    # Age-related
    if age > 50:
        watch_areas.extend(["cardiovascular","joint health"])
    if age > 60:
        watch_areas.extend(["bone density","cognitive health"])

    # Dedup
    watch_areas = list(dict.fromkeys(watch_areas))[:6]

    # Overall health score (higher = fewer risk indicators)
    health_score = max(30, 90 - len(risk_planets) * 12)

    return {
        "score":          health_score,
        "watch_areas":    watch_areas,
        "risk_planets":   risk_planets,
        "active_themes":  active_themes,
        "current_md":     current_md_lord,
        "current_ad":     current_ad_lord,
        "age":            age,
        "priority_remedies": _health_remedies(risk_planets, current_md_lord),
    }


def _health_remedies(risk_planets: list, md_lord: str) -> list:
    remedies = {
        "Mars":    "Avoid anger and overexertion. Regular blood pressure checks. Hanuman worship on Tuesdays.",
        "Saturn":  "Joint care, warm clothing, avoid cold. Regular bone density checks after 40.",
        "Rahu":    "Avoid untested medications. Get second opinions on diagnoses. Meditation for neurological health.",
        "Moon":    "Emotional health is physical health. Meditation, journaling. Avoid late nights.",
        "Jupiter": "Liver care — reduce fatty foods and alcohol. Regular liver function tests.",
        "Ketu":    "Spiritual practice improves mysterious health issues. Avoid self-medication.",
        "Sun":     "Heart health — cardio exercise, reduce sodium. Eye check-ups annually.",
        "Venus":   "Kidney health — hydration. Reproductive health check-ups. Reduce sugar.",
        "Mercury": "Nervous system — reduce screen time and stress. Breathing exercises.",
    }
    result = []
    if md_lord:
        r = remedies.get(md_lord)
        if r:
            result.append(f"Current MD ({md_lord}): {r}")
    for rp in risk_planets[:2]:
        planet = rp.split()[0]
        r = remedies.get(planet)
        if r and not any(planet in x for x in result):
            result.append(f"{planet}: {r}")
    return result[:3]


# ═══════════════════════════════════════════════════════════════
# ENGINE 5 — TIMING WINDOWS
# ═══════════════════════════════════════════════════════════════

TIMING_CONCERN_MAP = {
    "wealth":       ["Jupiter","Venus","Rahu","Sun","Moon"],
    "career":       ["Sun","Mars","Saturn","Rahu","Mercury","Jupiter"],
    "relationship": ["Venus","Moon","Jupiter"],
    "marriage":     ["Venus","Moon","Jupiter"],
    "children":     ["Jupiter","Moon","Venus"],
    "health":       ["Sun","Moon","Mars"],
    "foreign":      ["Rahu","Jupiter","Saturn","Moon"],
    "property":     ["Mars","Moon","Saturn","Venus"],
    "spiritual":    ["Ketu","Jupiter","Saturn"],
    "general":      ["Jupiter","Venus","Rahu"],
}

def run_timing_engine(
    planets: dict,
    dashas: dict,
    concern: str,
    birth_date: str,
) -> dict:
    """
    Find specific timing windows for a concern.
    Uses dasha confluence — when relevant planets run MD or AD.
    """
    now = datetime.utcnow()
    relevant_lords = TIMING_CONCERN_MAP.get(concern, TIMING_CONCERN_MAP["general"])

    try:
        born_date = date.fromisoformat(birth_date[:10])
    except Exception:
        born_date = date(1970,1,1)

    windows = []
    current_window = None

    vim = dashas.get("vimsottari", [])

    for row in vim:
        lord  = row.get("lord_or_sign") or row.get("planet_or_sign","")
        level = row.get("level") or row.get("type","")
        if lord not in relevant_lords:
            continue
        try:
            sd = datetime.strptime(str(row.get("start_date",""))[:10], "%Y-%m-%d")
            ed = datetime.strptime(str(row.get("end_date",""))[:10], "%Y-%m-%d")
        except Exception:
            continue

        if ed < now:
            continue  # past

        # House position of this lord
        lord_house = planets.get(lord, {}).get("house", 0)
        lord_sign  = planets.get(lord, {}).get("sign","")

        # Score this window
        window_score = 0.5
        if lord == "Jupiter" and lord_house in [2, 5, 9, 11]:
            window_score = 0.90
        elif lord == "Rahu" and lord_house in [11, 3, 6]:
            window_score = 0.85
        elif lord == "Venus" and lord_house in [1, 2, 7, 11]:
            window_score = 0.80
        elif lord_house in [1, 4, 7, 10]:
            window_score = 0.75
        elif lord_house in [5, 9, 11]:
            window_score = 0.80

        # Malefic in dusthana = bad window
        if lord in ["Saturn","Mars","Rahu","Ketu"] and lord_house in [6, 8, 12]:
            window_score = 0.30

        is_current = sd <= now <= ed

        entry = {
            "lord":          lord,
            "level":         level,
            "start_year":    sd.year,
            "end_year":      ed.year,
            "start_date":    str(sd.date()),
            "end_date":      str(ed.date()),
            "window_score":  window_score,
            "quality":       "excellent" if window_score >= 0.80 else "good" if window_score >= 0.65 else "moderate" if window_score >= 0.50 else "challenging",
            "is_current":    is_current,
            "lord_house":    lord_house,
            "lord_sign":     lord_sign,
        }

        if is_current:
            current_window = entry
        else:
            windows.append(entry)

    # Sort future windows by score then proximity
    windows.sort(key=lambda x: (-x["window_score"], x["start_year"]))
    best_windows = windows[:3]

    # Confluence check — when 2+ relevant planets overlap
    confluence_note = ""
    if current_window and best_windows:
        nw = best_windows[0]
        if nw["start_year"] <= (current_window["end_year"] + 2):
            confluence_note = (
                f"High confluence: current {current_window['lord']} period "
                f"transitions directly into {nw['lord']} period — "
                f"sustained momentum for {concern}"
            )

    return {
        "concern":          concern,
        "current_window":   current_window,
        "best_windows":     best_windows,
        "primary_window":   best_windows[0] if best_windows else current_window,
        "confluence_note":  confluence_note,
        "relevant_lords":   relevant_lords,
    }


# ═══════════════════════════════════════════════════════════════
# MASTER RUNNER — run all 5 engines
# ═══════════════════════════════════════════════════════════════

def run_all_domain_engines(
    chart_data: dict,
    dashas: dict,
    birth_date: str,
    concern: str = "general",
    current_md_lord: str = "",
    current_ad_lord: str = "",
) -> dict:
    """Run all 5 domain engines and return complete verdicts dict."""
    planets    = chart_data.get("planets", {})
    lagna      = chart_data.get("lagna", {})
    lagna_sign = lagna.get("sign","") if isinstance(lagna, dict) else str(lagna)
    house_lords = chart_data.get("house_lords", {})
    yogas      = chart_data.get("yogas", [])
    atmakaraka = chart_data.get("atmakaraka","")
    divs       = chart_data.get("divisional_charts", {})
    d2         = divs.get("d2", {})

    wealth = run_wealth_engine(planets, lagna_sign, house_lords, yogas, dashas, d2)
    career = run_career_engine(planets, lagna_sign, house_lords, yogas, atmakaraka, divs)
    relationship = run_relationship_engine(planets, lagna_sign, house_lords, divs, birth_date)
    health = run_health_engine(planets, lagna_sign, house_lords, current_md_lord, current_ad_lord, birth_date)
    timing = run_timing_engine(planets, dashas, concern, birth_date)

    return {
        "wealth":       wealth,
        "career":       career,
        "relationship": relationship,
        "health":       health,
        "timing":       timing,
    }


def build_domain_verdicts_block(verdicts: dict, concern: str = "general") -> str:
    """
    Convert all 5 engine verdicts into a structured block for the LLM.
    These are FACTS — the LLM explains them, never contradicts them.
    """
    w = verdicts.get("wealth", {})
    c = verdicts.get("career", {})
    r = verdicts.get("relationship", {})
    h = verdicts.get("health", {})
    t = verdicts.get("timing", {})

    lines = [
        "═══════════════════════════════════════════════════════",
        "PYTHON-CALCULATED DOMAIN VERDICTS",
        "THESE ARE FACTS — explain them, do not change them.",
        "═══════════════════════════════════════════════════════",
        "",
        f"WEALTH ENGINE (score: {w.get('score',0)}/100):",
        f"  Verdict: {w.get('verdict','')}",
        f"  Billionaire possible: {'YES' if w.get('billionaire_possible') else 'NO — significant but not exceptional'}",
        f"  Wealth type: {w.get('wealth_type','')}",
        f"  Peak window: {w.get('peak_window','')}",
        f"  Combinations found ({w.get('combinations_found',0)}):",
    ]
    for combo in w.get("combinations", []):
        lines.append(f"    ✓ {combo['desc']} (weight: {combo['weight']})")

    lines += [
        "",
        f"CAREER ENGINE (score: {c.get('score',0)}/100):",
        f"  Top career: {c.get('top_career','')}",
        f"  Top 3 domains: {', '.join(c.get('top_3_careers',[]))}",
        f"  D10 lagna: {c.get('d10_lagna','')} → {c.get('d10_career_type','')}",
        f"  Planets in 10th: {c.get('planets_in_10th',[])}",
        f"  10th lord: {c.get('10th_lord','')} in house {c.get('10th_lord_house','')}",
        "",
        f"RELATIONSHIP ENGINE (score: {r.get('score',0)}/100):",
        f"  Partner nature: {r.get('partner_nature','')}",
        f"  Marriage timing: {r.get('marriage_timing','')}",
        f"  D9 lagna: {r.get('d9_lagna','')}",
        f"  Venus in house: {r.get('venus_house','')} | D9 Venus house: {r.get('d9_venus_house','')}",
    ]
    if r.get("warnings"):
        for warning in r["warnings"][:2]:
            lines.append(f"  ⚠ {warning}")
    if r.get("strengths"):
        for strength in r["strengths"][:2]:
            lines.append(f"  ✓ {strength}")

    lines += [
        "",
        f"HEALTH ENGINE (score: {h.get('score',0)}/100):",
        f"  Watch areas: {', '.join(h.get('watch_areas',[]))}",
        f"  Active theme: {' | '.join(h.get('active_themes',[]))}",
    ]
    for rp in h.get("risk_planets", [])[:3]:
        lines.append(f"  ⚠ {rp}")

    lines += [
        "",
        f"TIMING ENGINE ({concern.upper()} windows):",
    ]
    cw = t.get("current_window")
    if cw:
        lines.append(f"  CURRENT: {cw['lord']} {cw['level']} ({cw['start_year']}–{cw['end_year']}) — quality: {cw['quality'].upper()}")
    for bw in t.get("best_windows",[])[:2]:
        lines.append(f"  UPCOMING: {bw['lord']} {bw['level']} ({bw['start_year']}–{bw['end_year']}) — quality: {bw['quality'].upper()}")
    if t.get("confluence_note"):
        lines.append(f"  CONFLUENCE: {t['confluence_note']}")

    lines += [
        "",
        "INSTRUCTION TO LLM:",
        "  Use these verdicts as the foundation of your answer.",
        "  Wealth score, billionaire verdict, career domains, health watch areas,",
        "  relationship timing — ALL are pre-calculated. Explain them.",
        "  Do NOT invent different scores or contradictory verdicts.",
        "  Reference specific combinations listed above by name.",
        "═══════════════════════════════════════════════════════",
    ]

    return "\n".join(lines)
