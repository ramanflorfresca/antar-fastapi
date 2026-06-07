"""
antar_engine/lal_kitab_advanced.py

Three missing Lal Kitab features:
1. Enemy house detection — planet in enemy sign = trouble during its dasha
2. Sleeping planets — planets in dusthana with no benefic aspect
3. Varshphal — annual chart warnings for current year
4. Comprehensive Rin (karmic debts)
"""

from datetime import datetime, date

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

# Natural friendships (Naisargika Maitri)
PLANET_FRIENDS = {
    "Sun":     ["Moon","Mars","Jupiter"],
    "Moon":    ["Sun","Mercury"],
    "Mars":    ["Sun","Moon","Jupiter"],
    "Mercury": ["Sun","Venus"],
    "Jupiter": ["Sun","Moon","Mars"],
    "Venus":   ["Mercury","Saturn"],
    "Saturn":  ["Mercury","Venus"],
    "Rahu":    ["Venus","Saturn","Mercury"],
    "Ketu":    ["Mars","Venus","Saturn"],
}

PLANET_ENEMIES = {
    "Sun":     ["Saturn","Venus","Rahu"],
    "Moon":    ["Rahu","Ketu"],
    "Mars":    ["Mercury","Rahu"],
    "Mercury": ["Moon","Rahu"],
    "Jupiter": ["Mercury","Venus","Saturn","Rahu"],
    "Venus":   ["Sun","Moon","Rahu"],
    "Saturn":  ["Sun","Moon","Mars"],
    "Rahu":    ["Sun","Moon","Mars","Jupiter"],
    "Ketu":    ["Sun","Moon","Mercury","Jupiter"],
}

PLANET_NEUTRAL = {
    "Sun":     ["Mercury"],
    "Moon":    ["Mars","Jupiter","Venus","Saturn"],
    "Mars":    ["Venus","Saturn"],
    "Mercury": ["Mars","Jupiter","Saturn"],
    "Jupiter": [],
    "Venus":   ["Mars","Jupiter"],
    "Saturn":  ["Jupiter"],
    "Rahu":    ["Mars","Jupiter"],
    "Ketu":    ["Venus","Saturn","Mercury"],
}

# Own signs for each planet
OWN_SIGNS = {
    "Sun":     ["Leo"],
    "Moon":    ["Cancer"],
    "Mars":    ["Aries","Scorpio"],
    "Mercury": ["Gemini","Virgo"],
    "Jupiter": ["Sagittarius","Pisces"],
    "Venus":   ["Taurus","Libra"],
    "Saturn":  ["Capricorn","Aquarius"],
}

# Exaltation signs
EXALTATION = {
    "Sun":"Aries","Moon":"Taurus","Mars":"Capricorn","Mercury":"Virgo",
    "Jupiter":"Cancer","Venus":"Pisces","Saturn":"Libra",
}

# Debilitation signs
DEBILITATION = {
    "Sun":"Libra","Moon":"Scorpio","Mars":"Cancer","Mercury":"Pisces",
    "Jupiter":"Capricorn","Venus":"Virgo","Saturn":"Aries",
}

# Natural benefics and malefics
BENEFICS = ["Jupiter","Venus","Moon","Mercury"]
MALEFICS  = ["Saturn","Mars","Sun","Rahu","Ketu"]

# Dusthana houses (difficult)
DUSTHANA = [6, 8, 12]

# Lal Kitab — specific planet enemy house problems
LK_ENEMY_HOUSE_PROBLEMS = {
    ("Sun","Saturn"):    "Sun in Saturn's house — father issues, career blocks, authority conflicts during Sun dasha",
    ("Sun","Venus"):     "Sun in Venus's house — ego clashes in relationships, luxury-related problems during Sun dasha",
    ("Moon","Saturn"):   "Moon in Saturn's house — emotional depression, mother's difficulties, chronic worry during Moon dasha",
    ("Moon","Mercury"):  "Moon in Mercury's house — mental restlessness, communication creates emotional problems",
    ("Mars","Mercury"):  "Mars in Mercury's house — rash decisions in business, legal disputes during Mars dasha",
    ("Mars","Saturn"):   "Mars in Saturn's house — property disputes intensify, accidents during Mars dasha — keep Hanuman remedy active",
    ("Mercury","Moon"):  "Mercury in Moon's house — overthinking emotional matters, mother relationship complex",
    ("Mercury","Mars"):  "Mercury in Mars's house — business disputes, siblings create problems during Mercury dasha",
    ("Jupiter","Mercury"):"Jupiter in Mercury's house — wisdom conflicts with practicality, educational interruptions",
    ("Jupiter","Venus"):  "Jupiter in Venus's house — dharma vs pleasure conflict, marriage problems during Jupiter dasha",
    ("Jupiter","Saturn"): "Jupiter in Saturn's house — delayed fortune, hard-earned wisdom during Jupiter dasha",
    ("Venus","Sun"):      "Venus in Sun's house — relationship vs authority conflict, spouse and father issues",
    ("Venus","Moon"):     "Venus in Moon's house — emotional relationships, mother-spouse conflict during Venus dasha",
    ("Saturn","Sun"):     "Saturn in Sun's house — severe father-karma, government/authority obstacles during Saturn dasha",
    ("Saturn","Moon"):    "Saturn in Moon's house — emotional heaviness, mother's health, depression during Saturn dasha",
    ("Saturn","Mars"):    "Saturn in Mars's house — property losses, sibling conflict, accidents during Saturn dasha",
    ("Rahu","Sun"):       "Rahu in Sun's house — father karma activated, identity confusion during Rahu dasha",
    ("Rahu","Moon"):      "Rahu in Moon's house — mental health challenges, mother separation during Rahu dasha",
    ("Rahu","Mars"):      "Rahu in Mars's house — accidents, property disputes during Rahu dasha — critical remedy needed",
    ("Rahu","Jupiter"):   "Rahu in Jupiter's house — Guru-Chandala yoga — unconventional beliefs, spiritual challenges",
}

# Lal Kitab Rin (karmic debts) — comprehensive
LK_RIN_RULES = {
    # Sun-related debts
    ("Sun", 6):   {"rin": "Father's debt (Pitra Rin)", "cause": "Disrespect or neglect of father in past life", "remedy": "Serve father daily. Offer water to Sun at sunrise. Donate wheat on Sundays."},
    ("Sun", 12):  {"rin": "Government/authority debt", "cause": "Misuse of authority in past life", "remedy": "Serve in government capacity. Donate copper. Eye care important."},
    # Moon-related debts
    ("Moon", 8):  {"rin": "Mother's debt (Matru Rin)", "cause": "Neglect of mother or women in past life", "remedy": "Care for mother actively. Offer milk to Shiva. Keep silver."},
    ("Moon", 12): {"rin": "Emotional debt", "cause": "Past life emotional harm to others", "remedy": "Meditate near water. Fast on Mondays. Serve women."},
    # Mars-related debts
    ("Mars", 4):  {"rin": "Property debt (Bhoomi Rin)", "cause": "Past life property injustice", "remedy": "Share property generously. Plant trees. Help brothers."},
    ("Mars", 7):  {"rin": "Partnership debt", "cause": "Past life betrayal of partner", "remedy": "Never deceive spouse. Gift copper. Donate blood."},
    ("Mars", 8):  {"rin": "Accident/violence debt", "cause": "Past life violence or sudden harm to others", "remedy": "Pray to Hanuman. Avoid risky activities. Donate red items."},
    # Mercury-related debts
    ("Mercury", 8): {"rin": "Intellectual debt", "cause": "Misuse of knowledge or deception in past life", "remedy": "Teach freely. Donate books. Never deceive in business."},
    # Jupiter-related debts
    ("Jupiter", 6): {"rin": "Teacher's debt (Guru Rin)", "cause": "Disrespect to teachers or gurus in past life", "remedy": "Respect all teachers. Donate to educational causes. Serve religious leaders."},
    ("Jupiter", 8): {"rin": "Wisdom debt", "cause": "Hoarding of wisdom without sharing", "remedy": "Teach and share knowledge freely. Donate yellow items on Thursdays."},
    # Venus-related debts
    ("Venus", 6):  {"rin": "Relationship debt", "cause": "Betrayal in love or marriage in past life", "remedy": "Honor all commitments. Gift spouse regularly. Donate white items on Fridays."},
    ("Venus", 8):  {"rin": "Pleasure debt", "cause": "Overindulgence or harm through pleasure in past life", "remedy": "Practice discipline in relationships. Keep intimate life pure."},
    # Saturn-related debts
    ("Saturn", 1): {"rin": "Servant's debt (Dasa Rin)", "cause": "Mistreatment of servants or workers in past life", "remedy": "Serve workers with respect. Donate shoes to poor. Oil lamps on Saturdays."},
    ("Saturn", 5): {"rin": "Children's debt (Putra Rin)", "cause": "Neglect of children's welfare in past life", "remedy": "Serve orphaned children. Donate to child welfare. Be present for your children."},
    ("Saturn", 7): {"rin": "Spouse's debt", "cause": "Abandonment or harsh treatment of spouse in past life", "remedy": "Honor spouse with deep respect. Serve together. Never argue publicly."},
    # Rahu/Ketu debts
    ("Rahu", 1):  {"rin": "Foreign karmic debt", "cause": "Past life connection to foreign lands or unconventional acts", "remedy": "Keep elephant figurine. Feed crows. Donate blue items on Saturdays."},
    ("Rahu", 7):  {"rin": "Partnership karmic debt", "cause": "Complex karmic history with spouse/partner from past life", "remedy": "Never deceive partner. Respect all relationships. Serve widows."},
    ("Ketu", 1):  {"rin": "Spiritual debt (Moksha Rin)", "cause": "Unfinished spiritual practice from past life", "remedy": "Meditate daily. Keep cat as pet. Donate blankets to poor."},
    ("Ketu", 8):  {"rin": "Past life occult debt", "cause": "Misuse of spiritual powers in past life", "remedy": "Practice spirituality purely. Never use knowledge to harm. Study sacred texts."},
}

# Sleeping planet rules
LK_SLEEPING_PLANET = {
    "Sun":     {"sleeping_in": [6,8,12], "awakening": "Offer water to Sun daily at sunrise for 43 days"},
    "Moon":    {"sleeping_in": [6,8,12], "awakening": "Offer milk to Shiva on Mondays. Keep silver article."},
    "Mars":    {"sleeping_in": [8,12],   "awakening": "Visit Hanuman temple on Tuesdays. Donate blood once."},
    "Mercury": {"sleeping_in": [8,12],   "awakening": "Donate books to students. Feed green grass to cow."},
    "Jupiter": {"sleeping_in": [3,6,8,12],"awakening": "Donate yellow sweets on Thursdays. Respect teachers."},
    "Venus":   {"sleeping_in": [6,8,12], "awakening": "Gift wife white clothes. Donate on Fridays."},
    "Saturn":  {"sleeping_in": [1,5,9],  "awakening": "Serve workers and poor on Saturdays. Donate oil."},
    "Rahu":    {"sleeping_in": [5,9],    "awakening": "Feed crows. Keep elephant figurine. Donate on Saturdays."},
    "Ketu":    {"sleeping_in": [2,7,11], "awakening": "Keep cat. Donate blankets. Spiritual practice daily."},
}

# Varshphal year lords (simplified Tajika system)
# The year lord is determined by the day of birth in the week for birth time
YEAR_LORD_SEQUENCE = [
    "Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"
]


def detect_enemy_houses(planets: dict) -> list:
    """
    Detect planets in enemy signs (Lal Kitab enemy house).
    Returns list of warnings with remedies.
    """
    warnings = []

    for planet, data in planets.items():
        sign      = data.get("sign","")
        house     = data.get("house", 0)
        sign_lord = SIGN_LORDS.get(sign,"")

        if not sign_lord or sign_lord == planet:
            continue  # own sign — not an enemy house

        # Check if this planet is in an enemy's sign
        enemies = PLANET_ENEMIES.get(planet, [])
        if sign_lord in enemies:
            lk_key = (planet, sign_lord)
            problem = LK_ENEMY_HOUSE_PROBLEMS.get(lk_key,
                f"{planet} in {sign_lord}'s house — natural tension, problems related to {planet} themes during its dasha period")

            warnings.append({
                "planet":       planet,
                "house":        house,
                "sign":         sign,
                "sign_lord":    sign_lord,
                "relationship": "enemy",
                "problem":      problem,
                "active_when":  f"During {planet} Mahadasha or Antardasha",
                "severity":     "high" if planet in ["Saturn","Rahu","Mars"] else "moderate",
            })

    return sorted(warnings, key=lambda x: 0 if x["severity"]=="high" else 1)


def detect_sleeping_planets(planets: dict) -> list:
    """
    Detect sleeping planets — in dusthana with no benefic support.
    """
    sleeping = []

    # Find which houses have benefics
    benefic_houses = set()
    for p in BENEFICS:
        h = planets.get(p, {}).get("house", 0)
        if h:
            benefic_houses.add(h)

    for planet, data in planets.items():
        house = data.get("house", 0)
        sign  = data.get("sign","")

        sleeping_houses = LK_SLEEPING_PLANET.get(planet, {}).get("sleeping_in", [])
        if house not in sleeping_houses:
            continue

        # Check if any benefic is in the same house or aspects it
        same_house_planets = [p for p, d in planets.items() if d.get("house")==house and p!=planet]
        has_benefic_support = any(p in BENEFICS for p in same_house_planets)

        # Simple aspect check — 7th house aspect
        seventh_from = ((house - 1 + 6) % 12) + 1
        has_7th_aspect = seventh_from in benefic_houses

        if not has_benefic_support and not has_7th_aspect:
            awakening = LK_SLEEPING_PLANET.get(planet, {}).get("awakening","")
            sleeping.append({
                "planet":    planet,
                "house":     house,
                "sign":      sign,
                "problem":   f"{planet} is sleeping in house {house} — its significations are dormant and need activation",
                "impact":    _sleeping_planet_impact(planet),
                "awakening": awakening,
            })

    return sleeping


def _sleeping_planet_impact(planet: str) -> str:
    impacts = {
        "Sun":     "Career lacks authority, father relationship may suffer, government matters delayed",
        "Moon":    "Emotional blocks, mother's health may suffer, public recognition elusive",
        "Mars":    "Energy blocks, property matters stalled, courage needed but unavailable",
        "Mercury": "Business communication ineffective, education interrupted, deals fall through",
        "Jupiter": "Wealth doesn't grow despite effort, children may have difficulties, wisdom blocked",
        "Venus":   "Relationship happiness elusive, creative output blocked, comfort lacks",
        "Saturn":  "Actually better when Saturn sleeps — less suffering, but career delayed",
        "Rahu":    "Foreign opportunities missed, technology adoption slow",
        "Ketu":    "Spiritual practice feels empty, research lacks insight",
    }
    return impacts.get(planet, f"{planet} significations blocked")


def calculate_comprehensive_rin(planets: dict) -> list:
    """
    Comprehensive Lal Kitab Rin (karmic debt) detection.
    More complete than the basic version in lal_kitab_engine.py.
    """
    rins = []

    for planet, data in planets.items():
        house = data.get("house", 0)
        if not house:
            continue

        rin_data = LK_RIN_RULES.get((planet, house))
        if rin_data:
            rins.append({
                "planet":  planet,
                "house":   house,
                "rin":     rin_data["rin"],
                "cause":   rin_data["cause"],
                "remedy":  rin_data["remedy"],
                "urgency": "high" if house in [6,8,12] else "moderate",
            })

    return sorted(rins, key=lambda x: 0 if x["urgency"]=="high" else 1)


def calculate_varshphal_warnings(
    planets: dict,
    lagna_sign: str,
    birth_date: str,
    current_md_lord: str = "",
    current_ad_lord: str = "",
) -> dict:
    """
    Varshphal — annual Lal Kitab predictions for the current year.
    Uses the natal chart planets but applies annual house overlays.
    
    Simplified Lal Kitab annual technique:
    - Year lord activates specific houses in the natal chart
    - Current dasha lord's natal house gets annual focus
    - Planets in 1/4/7/10 from year lord = strong annual activation
    """
    try:
        born = date.fromisoformat(birth_date[:10])
        today = date.today()
        age = (today - born).days // 365
        # Most recent birthday
        last_bday = born.replace(year=today.year)
        if last_bday > today:
            last_bday = born.replace(year=today.year - 1)
        next_bday = last_bday.replace(year=last_bday.year + 1)
    except Exception:
        return {}

    # Year lord based on day of week of last birthday
    day_of_week = last_bday.weekday()  # 0=Monday
    # LK year lord sequence: Sun=Sun, Mon=Moon, Tue=Mars, Wed=Mercury, Thu=Jupiter, Fri=Venus, Sat=Saturn
    day_lords = ["Moon","Mars","Mercury","Jupiter","Venus","Saturn","Sun"]
    year_lord = day_lords[day_of_week]

    # Active year themes
    year_lord_house = planets.get(year_lord, {}).get("house", 0)
    year_lord_sign  = planets.get(year_lord, {}).get("sign","")

    warnings = []
    highlights = []

    # Year lord in dusthana = difficult year
    if year_lord_house in DUSTHANA:
        warnings.append({
            "type":    "year_lord_dusthana",
            "message": f"Year lord {year_lord} is in house {year_lord_house} — this year brings {_house_difficulty(year_lord_house)}",
            "remedy":  f"Activate {year_lord}'s remedy immediately: {_quick_remedy(year_lord)}",
        })

    # Current dasha lord in enemy house during this year
    if current_md_lord:
        md_house = planets.get(current_md_lord, {}).get("house", 0)
        md_sign  = planets.get(current_md_lord, {}).get("sign","")
        md_lord_of_sign = SIGN_LORDS.get(md_sign,"")
        if md_lord_of_sign in PLANET_ENEMIES.get(current_md_lord, []):
            warnings.append({
                "type":    "dasha_lord_enemy",
                "message": f"Current MD lord {current_md_lord} sits in enemy sign ({md_sign}) — its themes face obstacles this year",
                "remedy":  f"Strengthen {current_md_lord}: {_quick_remedy(current_md_lord)}",
            })

    # Year lord in good house = strong year for that domain
    if year_lord_house in [1, 2, 5, 9, 10, 11]:
        highlights.append({
            "type":    "favorable_year",
            "message": f"Year lord {year_lord} in house {year_lord_house} — strong year for {_house_theme_lk(year_lord_house)}",
        })

    # Any planet with sleeping status active this year
    sleeping = detect_sleeping_planets(planets)
    for sp in sleeping[:2]:
        warnings.append({
            "type":    "sleeping_active",
            "message": f"{sp['planet']} sleeping in house {sp['house']} — needs awakening this year",
            "remedy":  sp["awakening"],
        })

    return {
        "year_lord":       year_lord,
        "year_lord_house": year_lord_house,
        "year_lord_sign":  year_lord_sign,
        "birthday_year":   last_bday.year,
        "valid_until":     str(next_bday),
        "warnings":        warnings,
        "highlights":      highlights,
        "year_summary":    _year_summary(year_lord, year_lord_house, warnings, highlights),
    }


def _house_difficulty(house: int) -> str:
    d = {6:"health challenges, enemy activity, debt", 8:"sudden events, accidents, hidden problems", 12:"losses, isolation, expenditure"}
    return d.get(house, "obstacles")

def _house_theme_lk(house: int) -> str:
    t = {1:"self and identity",2:"wealth and family",5:"children and creativity",
         9:"fortune and father",10:"career",11:"income and gains"}
    return t.get(house, f"house {house}")

def _quick_remedy(planet: str) -> str:
    remedies = {
        "Sun":     "Offer water to Sun daily",
        "Moon":    "Offer milk to Shiva on Mondays",
        "Mars":    "Visit Hanuman temple on Tuesdays",
        "Mercury": "Donate books to students",
        "Jupiter": "Donate yellow sweets on Thursdays",
        "Venus":   "Gift wife white clothes on Fridays",
        "Saturn":  "Serve poor on Saturdays, donate oil",
        "Rahu":    "Feed crows, keep elephant figurine",
        "Ketu":    "Keep cat, donate blankets",
    }
    return remedies.get(planet, f"Strengthen {planet} through its natural remedy")

def _year_summary(year_lord: str, year_lord_house: int, warnings: list, highlights: list) -> str:
    if len(warnings) > len(highlights):
        return f"This year requires caution. Year lord {year_lord} in house {year_lord_house} activates {_house_theme_lk(year_lord_house)} — apply remedies proactively."
    elif highlights:
        return f"Strong year ahead. Year lord {year_lord} in house {year_lord_house} supports {_house_theme_lk(year_lord_house)} — capitalize on this window."
    return f"Moderate year. Year lord {year_lord} in house {year_lord_house} — steady progress with consistent effort."


def build_lk_advanced_context(
    planets: dict,
    lagna_sign: str,
    birth_date: str,
    current_md_lord: str = "",
    current_ad_lord: str = "",
) -> str:
    """
    Build the complete advanced Lal Kitab context block for LLM.
    """
    enemy_warnings  = detect_enemy_houses(planets)
    sleeping        = detect_sleeping_planets(planets)
    rins            = calculate_comprehensive_rin(planets)
    varshphal       = calculate_varshphal_warnings(
        planets, lagna_sign, birth_date, current_md_lord, current_ad_lord
    )

    lines = [
        "═══════════════════════════════════════════════════════",
        "LAL KITAB ADVANCED ANALYSIS",
        "═══════════════════════════════════════════════════════",
    ]

    # Varshphal — most urgent
    lines += [
        "",
        f"VARSHPHAL {varshphal.get('birthday_year','')} (Annual Chart — valid until {varshphal.get('valid_until','')[:10]}):",
        f"  Year lord: {varshphal.get('year_lord','')} in house {varshphal.get('year_lord_house','')}",
        f"  {varshphal.get('year_summary','')}",
    ]
    for w in varshphal.get("warnings",[]):
        lines.append(f"  ⚠ {w['message']}")
        lines.append(f"    Remedy: {w['remedy']}")
    for h in varshphal.get("highlights",[]):
        lines.append(f"  ✓ {h['message']}")

    # Enemy house warnings
    if enemy_warnings:
        lines += ["", "ENEMY HOUSE WARNINGS (problems during dasha of these planets):"]
        for w in enemy_warnings:
            lines.append(f"  ⚠ {w['planet']} in {w['sign']} (house {w['house']}) — {w['problem']}")
            lines.append(f"    Active during: {w['active_when']}")

    # Sleeping planets
    if sleeping:
        lines += ["", "SLEEPING PLANETS (need awakening — significations blocked):"]
        for sp in sleeping:
            lines.append(f"  💤 {sp['planet']} in house {sp['house']} — {sp['impact']}")
            lines.append(f"     Awakening remedy: {sp['awakening']}")

    # Karmic debts
    if rins:
        lines += ["", "KARMIC DEBTS (Rin) — past life obligations:"]
        for rin in rins:
            lines.append(f"  🔴 {rin['rin']}: {rin['planet']} in house {rin['house']}")
            lines.append(f"     Cause: {rin['cause']}")
            lines.append(f"     Remedy: {rin['remedy']}")

    lines += [
        "",
        "LAL KITAB RULES TO APPLY:",
        "  • Always mention specific remedies when problems are identified",
        "  • Enemy house planet = its dasha/antardasha will bring that problem",
        "  • Sleeping planet = its life area is blocked until remedy is applied",
        "  • Rin must be repaid — mention the remedy as urgent, not optional",
        "  • Varshphal is most urgent — applies THIS year specifically",
        "═══════════════════════════════════════════════════════",
    ]

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# LK Daily Diagnostic — weekday × user chart → personalized day read
# ──────────────────────────────────────────────────────────────

LK_DAY_LORDS = {
    0: "Moon",     # Monday
    1: "Mars",     # Tuesday
    2: "Mercury",  # Wednesday
    3: "Jupiter",  # Thursday
    4: "Venus",    # Friday
    5: "Saturn",   # Saturday
    6: "Sun",      # Sunday
}

LK_DAY_DOMAINS = {
    "Sun":     ["authority", "leadership", "self-expression", "vitality", "father"],
    "Moon":    ["emotion", "home", "mother", "comfort", "intuition"],
    "Mars":    ["action", "courage", "property", "initiative", "conflict"],
    "Mercury": ["communication", "trade", "writing", "learning", "negotiation"],
    "Jupiter": ["wisdom", "teaching", "wealth-growth", "children", "law"],
    "Venus":   ["relationships", "beauty", "creativity", "luxury", "diplomacy"],
    "Saturn":  ["discipline", "structure", "labor", "elders", "long-term"],
}

LK_DAY_DOMAINS_ES = {
    "Sun":     ["autoridad", "liderazgo", "autoexpresión", "vitalidad", "padre"],
    "Moon":    ["emoción", "hogar", "madre", "confort", "intuición"],
    "Mars":    ["acción", "coraje", "propiedad", "iniciativa", "conflicto"],
    "Mercury": ["comunicación", "comercio", "escritura", "aprendizaje", "negociación"],
    "Jupiter": ["sabiduría", "enseñanza", "crecimiento financiero", "hijos", "ley"],
    "Venus":   ["relaciones", "belleza", "creatividad", "lujo", "diplomacia"],
    "Saturn":  ["disciplina", "estructura", "trabajo", "mayores", "largo plazo"],
}


def _get_planet_lk_house(planet: str, lk_data: dict, chart_data: dict) -> int:
    """Get the LK house for a planet, checking lk_data.natal_planets first, then chart_data.planets."""
    # Try LK natal_planets first
    natal_planets = lk_data.get("natal_planets", {})
    if planet in natal_planets:
        h = natal_planets[planet].get("house", 0)
        if h:
            return h
    # Fallback to chart_data.planets
    planets = chart_data.get("planets", {})
    if planet in planets:
        h = planets[planet].get("house", 0)
        if h:
            return h
    return 0


def _get_planet_sign(planet: str, lk_data: dict, chart_data: dict) -> str:
    """Get sign for a planet."""
    natal_planets = lk_data.get("natal_planets", {})
    if planet in natal_planets:
        s = natal_planets[planet].get("sign", "")
        if s:
            return s
    planets = chart_data.get("planets", {})
    if planet in planets:
        return planets[planet].get("sign", "")
    return ""


def _assess_dignity(planet: str, sign: str, house: int) -> str:
    """
    Assess planet dignity in LK terms.
    Returns: 'dignified', 'neutral', or 'afflicted'
    """
    if not sign or not house:
        return "neutral"
    # Exalted
    if EXALTATION.get(planet) == sign:
        return "dignified"
    # Debilitated
    if DEBILITATION.get(planet) == sign:
        return "afflicted"
    # Own sign
    if sign in OWN_SIGNS.get(planet, []):
        return "dignified"
    # Friend's sign
    sign_lord = SIGN_LORDS.get(sign, "")
    if sign_lord in PLANET_FRIENDS.get(planet, []):
        return "dignified"
    # Enemy's sign
    if sign_lord in PLANET_ENEMIES.get(planet, []):
        return "afflicted"
    # Dusthana house
    if house in DUSTHANA:
        return "afflicted"
    return "neutral"


def _is_planet_sleeping(planet: str, lk_data: dict) -> bool:
    """Check if planet is sleeping based on stored advanced data."""
    adv = lk_data.get("advanced", {})
    sleeping_list = adv.get("sleeping_planets", [])
    if isinstance(sleeping_list, list):
        for s in sleeping_list:
            if isinstance(s, dict) and s.get("planet") == planet:
                return True
            elif isinstance(s, str) and s == planet:
                return True
    return False


def _has_active_rin(planet: str, lk_data: dict) -> tuple:
    """Check if planet has active rin. Returns (bool, rin_name or '')."""
    adv = lk_data.get("advanced", {})
    rin_list = adv.get("rin_debts", [])
    if isinstance(rin_list, list):
        for r in rin_list:
            if isinstance(r, dict) and r.get("planet") == planet:
                return True, r.get("rin", "karmic debt")
    return False, ""


def compute_lk_daily_diagnostic(
    lk_data: dict,
    chart_data: dict,
    target_date: "date",
    language: str = "en",
) -> dict:
    """
    Compute today's LK diagnostic for this user.

    Combines:
    - Today's weekday -> ruling planet (LK day-lord)
    - User's LK condition for that planet
    - Sleeping/awake status of that planet for this user
    - LK rin status involving that planet
    - LK favorability for today's domains based on this combination

    Returns a structured diagnostic ready for prompt injection.
    NOT user-facing text. NOT a Claude call. Pure computation.
    """
    # Guard: no LK data
    if not lk_data or (not lk_data.get("natal_planets") and not chart_data.get("planets")):
        day_lord = LK_DAY_LORDS.get(target_date.weekday(), "Sun")
        return {
            "day_lord": day_lord,
            "available": False,
        }

    day_lord = LK_DAY_LORDS.get(target_date.weekday(), "Sun")
    lk_house = _get_planet_lk_house(day_lord, lk_data, chart_data)
    sign = _get_planet_sign(day_lord, lk_data, chart_data)

    # Guard: day-lord planet missing from chart
    if not lk_house:
        return {
            "day_lord": day_lord,
            "available": False,
        }

    # Assess condition
    dignity = _assess_dignity(day_lord, sign, lk_house)
    is_sleeping = _is_planet_sleeping(day_lord, lk_data)
    rin_active, rin_name = _has_active_rin(day_lord, lk_data)

    # Determine day quality
    if is_sleeping:
        day_quality = "caution"
    elif dignity == "afflicted" or rin_active:
        day_quality = "caution" if rin_active else "neutral"
        if dignity == "afflicted" and rin_active:
            day_quality = "caution"
        elif dignity == "afflicted":
            day_quality = "neutral"
    elif dignity == "dignified":
        day_quality = "favorable"
    else:
        day_quality = "neutral"

    # Domains
    domains_en = LK_DAY_DOMAINS.get(day_lord, [])
    domains_es = LK_DAY_DOMAINS_ES.get(day_lord, [])

    # Pick top 2 amplified domains when favorable, top 2 to avoid when caution
    if day_quality == "favorable":
        amplified = domains_en[:2]
        amplified_es = domains_es[:2]
        avoid = []
        avoid_es = []
    elif day_quality == "caution":
        amplified = []
        amplified_es = []
        avoid = domains_en[:2]
        avoid_es = domains_es[:2]
    else:  # neutral
        amplified = domains_en[:1]
        amplified_es = domains_es[:1]
        avoid = domains_en[3:4] if len(domains_en) > 3 else []
        avoid_es = domains_es[3:4] if len(domains_es) > 3 else []

    # Build summaries
    house_theme = _house_theme_lk(lk_house)
    sleeping_note = ", sleeping (dormant)" if is_sleeping else ", awake"
    rin_note = f", rin active ({rin_name})" if rin_active else ", no debts"

    summary_en = f"{day_lord} is {dignity} in House {lk_house} ({house_theme}){sleeping_note}{rin_note}."
    summary_es = _translate_summary_es(day_lord, dignity, lk_house, house_theme, is_sleeping, rin_active, rin_name)

    # User-facing hints (for prompt injection, NOT direct card text)
    if day_quality == "favorable":
        hint_en = f"Today amplifies your {' and '.join(amplified)} moves. The energy supports initiative in these areas."
        hint_es = f"Hoy se amplifican tus movimientos de {' y '.join(amplified_es)}. La energía apoya la iniciativa en estas áreas."
    elif day_quality == "caution":
        if is_sleeping:
            hint_en = f"Today's energy needs activation — the day's natural ruler is dormant in your chart. Proceed with awareness in {' and '.join(avoid)}."
            hint_es = f"La energía de hoy necesita activación — el regente natural del día está dormido en tu carta. Procede con conciencia en {' y '.join(avoid_es)}."
        else:
            hint_en = f"Today calls for caution in {' and '.join(avoid)}. Review and prepare rather than initiate."
            hint_es = f"Hoy se requiere precaución en {' y '.join(avoid_es)}. Revisa y prepara en lugar de iniciar."
    else:
        hint_en = f"Moderate day for {' and '.join(amplified)} domains. Steady effort, no dramatic moves needed."
        hint_es = f"Día moderado para los dominios de {' y '.join(amplified_es)}. Esfuerzo constante, sin necesidad de movimientos drásticos."

    # Evidence for el_movimiento (technical depth layer)
    evidence = f"{day_lord} (today's day-lord) is {dignity} in your LK chart, House {lk_house} ({house_theme})"
    if is_sleeping:
        evidence += ", currently sleeping (dormant significations)"
    if rin_active:
        evidence += f", with active {rin_name}"
    if not is_sleeping and not rin_active and dignity == "dignified":
        evidence += ", with no obstructions"
    evidence += "."

    return {
        "day_lord": day_lord,
        "available": True,
        "day_lord_status": {
            "lk_house": lk_house,
            "sign": sign,
            "dignity": dignity,
            "sleeping": is_sleeping,
            "rin_active": rin_active,
            "rin_name": rin_name if rin_active else "",
            "summary_en": summary_en,
            "summary_es": summary_es,
        },
        "day_quality_for_user": day_quality,
        "domains_amplified_today": amplified if language != "es" else amplified_es,
        "domains_to_avoid_today": avoid if language != "es" else avoid_es,
        "user_facing_hint_en": hint_en,
        "user_facing_hint_es": hint_es,
        "evidence_for_movement": evidence,
    }


def compute_lk_month_diagnostic(lk_data: dict, chart_data: dict, now,
                                language: str = "en") -> dict:
    """
    Month-scale LK condition signal (2026-06-07). The daily diagnostic is
    weekday-lord driven, so iterating the 7 weekday-lords of the month gives
    this chart's recurring LK pattern for the month: which day-lords are
    dignified (amplified domains) vs afflicted/sleeping (caution domains),
    plus the natal sleeping-planet set (date-independent).

    Pure computation, no Claude. NOT user-facing text — structural facts +
    a votes trail for the monthly _debug_reasoning. Mirrors the daily LK
    condition logic so Month "earns" its nouns the same way Today does.
    """
    from datetime import timedelta
    planets = (chart_data or {}).get("planets") or {}

    # natal sleeping planets — date-independent (same detector the chart-create
    # flow uses); the single biggest LK signal currently absent from Month.
    sleeping = []
    try:
        sleeping = [s.get("planet") for s in detect_sleeping_planets(planets)
                    if isinstance(s, dict) and s.get("planet")]
    except Exception:
        sleeping = []

    amplified, caution, day_conditions, seen = {}, {}, [], set()
    base = (now.date() if hasattr(now, "date") else now).replace(day=1)
    for offset in range(7):                      # one per weekday-lord
        d = base + timedelta(days=offset)
        try:
            diag = compute_lk_daily_diagnostic(lk_data, chart_data, d, language)
        except Exception:
            continue
        lord = diag.get("day_lord")
        if not diag.get("available") or lord in seen:
            continue
        seen.add(lord)
        st = diag.get("day_lord_status") or {}
        day_conditions.append({
            "day_lord": lord, "dignity": st.get("dignity"),
            "sleeping": bool(st.get("sleeping")),
            "quality": diag.get("day_quality_for_user"),
        })
        for dom in (diag.get("domains_amplified_today") or []):
            amplified[dom] = amplified.get(dom, 0) + 1
        for dom in (diag.get("domains_to_avoid_today") or []):
            caution[dom] = caution.get(dom, 0) + 1

    amp_list = sorted(amplified, key=lambda k: -amplified[k])[:4]
    cau_list = sorted(caution, key=lambda k: -caution[k])[:4]

    votes = []
    for p in sleeping:
        votes.append(f"lk_sleeping:{p}")
    for dom in amp_list:
        votes.append(f"lk_amplify:{dom}")
    for dom in cau_list:
        votes.append(f"lk_caution:{dom}")

    return {
        "available": bool(day_conditions),
        "domains_amplified": amp_list,
        "domains_caution": cau_list,
        "sleeping_planets": sleeping,
        "day_lord_conditions": day_conditions,
        "votes": votes,
    }


def _translate_summary_es(day_lord, dignity, lk_house, house_theme, is_sleeping, rin_active, rin_name):
    """Build Spanish summary."""
    dignity_es = {"dignified": "dignificado", "neutral": "neutral", "afflicted": "afligido"}.get(dignity, dignity)
    sleeping_es = ", dormido (dormido)" if is_sleeping else ", activo"
    rin_es = f", rin activo ({rin_name})" if rin_active else ", sin deudas"
    return f"{day_lord} está {dignity_es} en la Casa {lk_house} ({house_theme}){sleeping_es}{rin_es}."
