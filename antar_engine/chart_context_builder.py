"""
antar_engine/chart_context_builder.py

THE MASTER CONTEXT BUILDER
Assembles ALL astrological data into one comprehensive brief
for the LLM. This is what replaces the LLM "hallucinating" —
it has zero need to guess because everything is provided.

Architecture:
  D1 chart → house lords → aspects → yogas
  D9 → soul/marriage picture
  D10 → career picture  
  Vimsottari + Jaimini + Ashtottari dashas
  Current transits
  Lal Kitab house analysis
  Age + gender + life stage context
  
The LLM receives ALL of this, then generates predictions
grounded entirely in the provided data.
"""

from datetime import date, datetime

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

PLANET_KARAKAS = {
    "Sun":     "Self, soul, father, authority, government, health",
    "Moon":    "Mind, mother, emotions, public, liquids, home",
    "Mars":    "Energy, siblings, property, courage, disputes, surgery",
    "Mercury": "Intellect, communication, business, mathematics, skin",
    "Jupiter": "Wisdom, children, wealth, teachers, dharma, liver",
    "Venus":   "Marriage, luxury, vehicles, beauty, reproduction, kidneys",
    "Saturn":  "Discipline, longevity, servants, delays, karma, bones",
    "Rahu":    "Foreign, technology, ambition, obsession, sudden events",
    "Ketu":    "Spirituality, liberation, past life, hidden, sudden losses",
}

HOUSE_KARAKAS = {
    1:  "self, body, personality, vitality, overall life",
    2:  "wealth, family, speech, accumulated assets, food",
    3:  "courage, siblings, short travel, communication, hands",
    4:  "home, mother, vehicles, property, education, heart",
    5:  "children, intelligence, creativity, past karma, speculation",
    6:  "enemies, disease, debt, service, litigation, digestive",
    7:  "marriage, partnerships, business deals, foreign travel",
    8:  "transformation, longevity, inheritance, occult, sudden events",
    9:  "dharma, father, fortune, higher education, religion, hips",
    10: "career, public life, authority, government, status, knees",
    11: "gains, income, elder siblings, aspirations, large organizations",
    12: "loss, foreign lands, spirituality, moksha, expenses, feet",
}

BILLIONAIRE_INDICATORS = [
    "2nd lord in 11th", "11th lord in 2nd", "2nd and 11th lords conjunct",
    "5th and 9th lords conjunct (Lakshmi Yoga)",
    "Jupiter in 2nd, 5th, 9th, or 11th",
    "Dhana yoga present", "Raj yoga in 2nd/10th/11th",
    "Rahu in 2nd or 11th (unconventional massive wealth)",
    "Exalted Jupiter in kendra",
    "Multiple planets in 11th house",
    "Venus and Jupiter exchanging houses",
]


def calculate_age(birth_date: str) -> int:
    try:
        born = date.fromisoformat(birth_date[:10])
        return (date.today() - born).days // 365
    except Exception:
        return 35


def get_life_stage(age: int) -> dict:
    if age < 28:
        return {
            "stage": "Brahmacharya — Formation",
            "erikson": "Identity vs Role Confusion",
            "core_question": "Who am I and what do I stand for?",
            "prediction_lens": "Focus on identity formation, education, early career, first relationships. Saturn return approaching.",
            "wealth_lens": "Wealth is being built. Expect growth trajectory, not peak.",
            "relationship_lens": "Relationships are formative. Marriage timing depends on 7th house.",
        }
    elif age < 50:
        return {
            "stage": "Grihastha — Building",
            "erikson": "Generativity vs Stagnation",
            "core_question": "Am I building something that matters?",
            "prediction_lens": "Peak building energy. Career, family, wealth all active. Saturn return completed.",
            "wealth_lens": "Prime wealth accumulation window. Dhana yogas manifest now.",
            "relationship_lens": "Relationship depth and commitment themes. Children questions.",
        }
    elif age < 72:
        return {
            "stage": "Vanaprastha — Legacy",
            "erikson": "Integrity vs Despair",
            "core_question": "Has my life meant something?",
            "prediction_lens": "Legacy, wisdom, health. Deepening over broadening. Second Saturn return territory.",
            "wealth_lens": "Wealth conservation and distribution more than accumulation.",
            "relationship_lens": "Relationship depth and family legacy. Romance is secondary to companionship.",
        }
    else:
        return {
            "stage": "Sannyasa — Liberation",
            "erikson": "Integrity and Acceptance",
            "core_question": "What is truly essential?",
            "prediction_lens": "Spiritual completion, legacy, health. Liberation themes dominant.",
            "wealth_lens": "Wealth distribution and legacy planning.",
            "relationship_lens": "Family relationships and peace with past.",
        }


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d")
    except Exception:
        return datetime.utcnow()


def _format_dr(sd: datetime, ed: datetime) -> str:
    if sd.year == ed.year:
        return f"during {sd.year}"
    elif ed.year - sd.year <= 2:
        return f"between {sd.year} and {ed.year}"
    return f"from {sd.year} to {ed.year}"


def build_complete_context(
    chart_data:      dict,
    dashas:          dict,
    birth_date:      str,
    first_name:      str = "",
    gender:          str = "",
    concern:         str = "general",
    question:        str = "",
    patra:           dict = None,
    transit_data:    dict = None,
    lk_analysis:     dict = None,
    yogas:           list = None,
    divisional_charts: dict = None,
) -> str:
    """
    Build the complete astrological context for LLM.
    This is the single source of truth that prevents hallucination.
    The LLM is explicitly told: ONLY use what is provided here.
    """
    age        = calculate_age(birth_date)
    life_stage = get_life_stage(age)
    now        = datetime.utcnow()

    if yogas is None:
        yogas = chart_data.get("yogas", [])
    if divisional_charts is None:
        divisional_charts = chart_data.get("divisional_charts", {})

    lagna = chart_data.get("lagna", {})
    lagna_sign = lagna.get("sign", "") if isinstance(lagna, dict) else str(lagna)
    lagna_deg  = lagna.get("degree", 0) if isinstance(lagna, dict) else 0
    lagna_lord = SIGN_LORDS.get(lagna_sign, "")
    planets    = chart_data.get("planets", {})
    atmakaraka = chart_data.get("atmakaraka", "")
    house_lords = chart_data.get("house_lords", {})

    name_str = first_name if first_name else "the person"
    gender_note = ""
    if gender and gender.lower() in ("female","woman","f"):
        gender_note = "Gender: Female"
    elif gender and gender.lower() in ("male","man","m"):
        gender_note = "Gender: Male"

    # ── D1 Planet positions ─────────────────────────────────────
    planet_lines = []
    for p, d in planets.items():
        sign   = d.get("sign","")
        house  = d.get("house","")
        nak    = d.get("nakshatra","")
        retro  = " (R)" if d.get("retrograde") else ""
        karaka = PLANET_KARAKAS.get(p,"")
        planet_lines.append(
            f"  {p}{retro}: {sign}, house {house} — {karaka}"
        )

    # ── House lords ─────────────────────────────────────────────
    hl_lines = []
    for h in range(1, 13):
        hl = house_lords.get(h, {}) if isinstance(house_lords, dict) else {}
        if hl:
            lord = hl.get("lord","")
            lord_house = planets.get(lord, {}).get("house","?")
            hl_lines.append(f"  H{h} lord: {lord} → in house {lord_house}")

    # ── Conjunctions ────────────────────────────────────────────
    conj_lines = []
    plist = list(planets.keys())
    for i, p1 in enumerate(plist):
        for p2 in plist[i+1:]:
            if planets[p1].get("house") == planets[p2].get("house"):
                h = planets[p1].get("house","?")
                conj_lines.append(
                    f"  {p1} + {p2} conjunct in house {h} "
                    f"({HOUSE_KARAKAS.get(int(h) if str(h).isdigit() else 0,'')})"
                )

    # ── Yogas ────────────────────────────────────────────────────
    strong_yogas   = [y for y in yogas if y.get("strength") == "strong"]
    moderate_yogas = [y for y in yogas if y.get("strength") == "moderate"]
    challenge_yogas = [y for y in yogas if y.get("category") == "challenge"]

    # ── Dashas ───────────────────────────────────────────────────
    vim = dashas.get("vimsottari", [])
    jai = dashas.get("jaimini", [])
    ash = dashas.get("ashtottari", [])

    past_mds, current_md, current_ad = [], None, None
    upcoming_mds = []

    for row in vim:
        lord  = row.get("lord_or_sign") or row.get("planet_or_sign","")
        level = row.get("level") or row.get("type","")
        sd    = _parse_dt(row.get("start_date") or row.get("start",""))
        ed    = _parse_dt(row.get("end_date")   or row.get("end",""))
        dr    = _format_dr(sd, ed)

        if level == "mahadasha":
            if ed < now:
                past_mds.append(f"  {lord} MD {dr}")
            elif sd <= now <= ed:
                current_md = (lord, sd, ed)
            elif sd > now and len(upcoming_mds) < 2:
                upcoming_mds.append(f"  {lord} MD starts {sd.year}")
        elif level == "antardasha":
            if sd <= now <= ed:
                current_ad = (lord, sd, ed)

    # Jaimini current
    jai_current = ""
    for row in jai:
        sd = _parse_dt(row.get("start_date") or row.get("start",""))
        ed = _parse_dt(row.get("end_date")   or row.get("end",""))
        if sd <= now <= ed:
            jai_current = row.get("lord_or_sign") or row.get("planet_or_sign","")
            break

    # ── D9 and D10 ───────────────────────────────────────────────
    d9  = divisional_charts.get("d9", {})
    d10 = divisional_charts.get("d10", {})
    d2  = divisional_charts.get("d2", {})
    d7  = divisional_charts.get("d7", {})

    d9_lagna  = d9.get("lagna","?")
    d10_lagna = d10.get("lagna","?")

    d9_venus  = d9.get("planets",{}).get("Venus",{})
    d9_moon   = d9.get("planets",{}).get("Moon",{})
    d10_sun   = d10.get("planets",{}).get("Sun",{})
    d10_jup   = d10.get("planets",{}).get("Jupiter",{})
    d10_sat   = d10.get("planets",{}).get("Saturn",{})
    d2_jupiter = d2.get("planets",{}).get("Jupiter",{})

    # ── Billionaire potential check ──────────────────────────────
    wealth_indicators = []
    lord_2  = house_lords.get(2, {}).get("lord","") if isinstance(house_lords, dict) else ""
    lord_11 = house_lords.get(11, {}).get("lord","") if isinstance(house_lords, dict) else ""
    lord_5  = house_lords.get(5, {}).get("lord","") if isinstance(house_lords, dict) else ""
    lord_9  = house_lords.get(9, {}).get("lord","") if isinstance(house_lords, dict) else ""

    if lord_2 and lord_11:
        h2 = planets.get(lord_2,{}).get("house",0)
        h11 = planets.get(lord_11,{}).get("house",0)
        if h2 == 11: wealth_indicators.append("2nd lord in 11th — strong wealth accumulation")
        if h11 == 2: wealth_indicators.append("11th lord in 2nd — income converts to assets")
        if h2 == h11: wealth_indicators.append("2nd and 11th lords conjunct — Dhana Yoga")

    jup_house = planets.get("Jupiter",{}).get("house",0)
    if jup_house in [2,5,9,11]:
        wealth_indicators.append(f"Jupiter in house {jup_house} — Dhana Yoga present")

    for y in strong_yogas:
        if "Dhana" in y["name"] or "Raj" in y["name"] or "Lakshmi" in y["name"]:
            wealth_indicators.append(f"{y['name']}: {y['effect'][:60]}")

    # ── Concern-specific context ──────────────────────────────────
    concern_context = ""
    if concern in ("career","business","profession"):
        concern_context = f"""
CAREER ANALYSIS CONTEXT:
  D10 lagna: {d10_lagna} (career chart rising sign)
  Sun in D10: house {d10_sun.get('house','?')} (authority/leadership)
  Jupiter in D10: house {d10_jup.get('house','?')} (expansion/wisdom)
  Saturn in D10: house {d10_sat.get('house','?')} (discipline/longevity)
  10th house lord: {house_lords.get(10,{}).get('lord','') if isinstance(house_lords,dict) else '?'}
  Relevant yogas: {', '.join(y['name'] for y in yogas if 'career' in y.get('effect','').lower() or 'Raj' in y['name'])[:200]}
"""
    elif concern in ("marriage","love","relationship","partner"):
        concern_context = f"""
RELATIONSHIP ANALYSIS CONTEXT:
  7th house: {house_lords.get(7,{}).get('sign','') if isinstance(house_lords,dict) else '?'} 
    lord: {house_lords.get(7,{}).get('lord','') if isinstance(house_lords,dict) else '?'}
  Venus: {planets.get('Venus',{}).get('sign','')} house {planets.get('Venus',{}).get('house','')}
  D9 lagna: {d9_lagna} (soul/marriage chart)
  Venus in D9: {d9_venus.get('sign','?')} house {d9_venus.get('house','?')}
  Moon in D9: {d9_moon.get('sign','?')} house {d9_moon.get('house','?')}
  D7 lagna: {d7.get('lagna','?')} (children chart)
  Life stage: {life_stage['relationship_lens']}
"""
    elif concern in ("wealth","money","finances","billionaire","rich","financial"):
        concern_context = f"""
WEALTH ANALYSIS CONTEXT:
  2nd house: {house_lords.get(2,{}).get('sign','') if isinstance(house_lords,dict) else '?'}
  11th house: {house_lords.get(11,{}).get('sign','') if isinstance(house_lords,dict) else '?'}
  Jupiter: house {jup_house} ({HOUSE_KARAKAS.get(jup_house,'')})
  Jupiter in D2: house {d2_jupiter.get('house','?')} (hora/wealth chart)
  
  WEALTH INDICATORS FOUND:
{chr(10).join('  ✓ '+w for w in wealth_indicators) if wealth_indicators else '  No exceptional wealth yogas — steady growth trajectory indicated'}
  
  Life stage wealth lens: {life_stage['wealth_lens']}
"""

    # ── Full context assembly ─────────────────────────────────────
    lk_block  = lal_kitab_prompt_block(lk_analysis) if lk_analysis else "LK analysis not available"
    trans_block = transits_prompt_block(transit_data) if transit_data else "Transit data not available"

    context = f"""
╔══════════════════════════════════════════════════════════════╗
║         COMPLETE ASTROLOGICAL CONTEXT — ANTAR ENGINE         ║
║   DO NOT FABRICATE. USE ONLY WHAT IS PROVIDED BELOW.         ║
╚══════════════════════════════════════════════════════════════╝

PERSON: {name_str}, Age {age}, Born {birth_date}
{gender_note}
Life Stage: {life_stage['stage']}
Core Question (psychology): {life_stage['core_question']}
Prediction Lens: {life_stage['prediction_lens']}

QUESTION ASKED: "{question}"
CONCERN DOMAIN: {concern}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
D1 NATAL CHART (Primary Chart)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rising Sign (Lagna): {lagna_sign} at {lagna_deg:.2f}°
Lagna Lord: {lagna_lord} in house {planets.get(lagna_lord,{}).get('house','?')}
Atmakaraka (Soul Significator): {atmakaraka}
  → Soul archetype: {PLANET_KARAKAS.get(atmakaraka,'').split(',')[0] if atmakaraka else ''}

PLANETARY POSITIONS:
{chr(10).join(planet_lines)}

HOUSE LORDS:
{chr(10).join(hl_lines) if hl_lines else '  (house lords not calculated)'}

CONJUNCTIONS:
{chr(10).join(conj_lines) if conj_lines else '  None'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOGAS (Planetary Combinations)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRONG YOGAS:
{chr(10).join('  ★ '+y['name']+': '+y['effect'] for y in strong_yogas) if strong_yogas else '  None detected'}

MODERATE YOGAS:
{chr(10).join('  • '+y['name']+': '+y['effect'] for y in moderate_yogas[:4]) if moderate_yogas else '  None'}

CHALLENGES:
{chr(10).join('  ⚠ '+y['name']+': '+y['effect'] for y in challenge_yogas) if challenge_yogas else '  None'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIVISIONAL CHARTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
D9 Navamsa (Soul, Marriage): Lagna = {d9_lagna}
  Venus in D9: {d9_venus.get('sign','?')} house {d9_venus.get('house','?')} (marriage/relationships)
  Moon in D9: {d9_moon.get('sign','?')} house {d9_moon.get('house','?')} (emotional fulfillment)

D10 Dashamsa (Career): Lagna = {d10_lagna}
  Sun in D10: house {d10_sun.get('house','?')} (authority in career)
  Jupiter in D10: house {d10_jup.get('house','?')} (expansion in career)
  Saturn in D10: house {d10_sat.get('house','?')} (discipline/longevity)

D2 Hora (Wealth): Jupiter in house {d2_jupiter.get('house','?')}
D7 Saptamsa (Children): Lagna = {d7.get('lagna','?')}
{concern_context}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VIMSOTTARI DASHA TIMELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLETED CHAPTERS:
{chr(10).join(past_mds[-5:]) if past_mds else '  (none completed yet)'}

CURRENT CHAPTER:
  {f"Mahadasha: {current_md[0]} ({current_md[1].year}–{current_md[2].year})" if current_md else 'unknown'}
  {f"Antardasha: {current_ad[0]} ({current_ad[1].strftime('%b %Y')}–{current_ad[2].strftime('%b %Y')})" if current_ad else ''}
  {f"Jaimini Chara Dasha current: {jai_current}" if jai_current else ''}

UPCOMING CHAPTERS:
{chr(10).join(upcoming_mds) if upcoming_mds else '  (current MD has many years remaining)'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{lk_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{trans_block}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANTI-HALLUCINATION INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ONLY reference planets, houses, and yogas listed above
2. NEVER invent planetary positions or yogas not mentioned
3. All date claims must reference the dasha periods above
4. Age {age}: {life_stage['prediction_lens']}
5. If asked about billionaire potential: check wealth indicators above
6. If no yoga supports a claim → say "the chart does not show this"
7. Specific windows must come from the dasha timeline above
8. Transit effects must reference the transit section above

"""
    return context


def _house_meaning(house: int) -> str:
    return HOUSE_KARAKAS.get(house, f"house {house} themes")


# Import helpers used above
try:
    from antar_engine.lal_kitab_engine import lal_kitab_prompt_block
except ImportError:
    def lal_kitab_prompt_block(lk, age=35): return "Lal Kitab: not available"

try:
    from antar_engine.transits_engine import transits_prompt_block
except ImportError:
    def transits_prompt_block(t): return "Transits: not available"
