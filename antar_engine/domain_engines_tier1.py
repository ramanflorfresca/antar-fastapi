"""
antar_engine/domain_engines_tier1.py

Tier 1 domain engines:
  Father, Mother, Siblings, Second Marriage,
  Government Job, Fame/Recognition,
  Stock Market/Speculation, Inheritance,
  Ashtottari confluence scoring
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
EXALTATION   = {"Sun":"Aries","Moon":"Taurus","Mars":"Capricorn","Mercury":"Virgo",
                "Jupiter":"Cancer","Venus":"Pisces","Saturn":"Libra"}
DEBILITATION = {"Sun":"Libra","Moon":"Scorpio","Mars":"Cancer","Mercury":"Pisces",
                "Jupiter":"Capricorn","Venus":"Virgo","Saturn":"Aries"}

def _h(planet, planets):  return planets.get(planet,{}).get("house",0)
def _s(planet, planets):  return planets.get(planet,{}).get("sign","")
def _lord(n, hl):
    if not isinstance(hl,dict): return ""
    return hl.get(n,{}).get("lord","")
def _age(bd):
    try: return (date.today()-date.fromisoformat(bd[:10])).days//365
    except: return 35


# ── FATHER ──────────────────────────────────────────────────────
def engine_father(planets, house_lords, divisional_charts, birth_date):
    """
    Father analysis:
    - 9th house = father (primary)
    - Sun = significator of father
    - D12 = parents chart
    - D9 = dharma/father's blessings
    """
    lord_9  = _lord(9, house_lords)
    lord_9h = _h(lord_9, planets) if lord_9 else 0
    sun_h   = _h("Sun", planets)
    sun_sign= _s("Sun", planets)
    sat_h   = _h("Saturn", planets)
    d12     = divisional_charts.get("d12",{})
    d12_sun = d12.get("planets",{}).get("Sun",{}).get("house",0) if d12 else 0

    blessings = []
    challenges= []

    # Strong father indicators
    if sun_h in [1,4,9,10,11]:
        blessings.append(f"Sun in house {sun_h} — father is influential and supportive")
    if sun_sign == EXALTATION.get("Sun"):
        blessings.append("Sun exalted in Aries — exceptionally strong father, government/authority figure")
    if lord_9h in [1,4,9,10,11]:
        blessings.append(f"9th lord {lord_9} in house {lord_9h} — father's blessings strong, fortune through father")
    if _h("Jupiter", planets) == 9:
        blessings.append("Jupiter in 9th — wise, religious, fortunate father, dharmic blessings")
    if d12_sun in [1,5,9,10]:
        blessings.append(f"Sun in D12 house {d12_sun} — father's chart strong, inheritance possible")

    # Challenges
    if sun_h in [6,8,12]:
        challenges.append(f"Sun in house {sun_h} — father faces difficulties, health issues, or separation")
    if sun_sign == DEBILITATION.get("Sun"):
        challenges.append("Sun debilitated in Libra — father's authority diminished, health challenges")
    if lord_9h in [6,8,12]:
        challenges.append(f"9th lord {lord_9} in house {lord_9h} — father relationship has karmic weight")
    if sat_h == 9:
        challenges.append("Saturn in 9th — father is strict/distant, OR dharma comes through hardship")

    score = max(20, min(95, 50 + len(blessings)*15 - len(challenges)*18))
    verdict = ("Strong father energy — father is a major support and blessing" if score >= 70
               else "Moderate father relationship — mixed blessings and challenges" if score >= 45
               else "Father karma is significant — healing this relationship is spiritually important")

    # Father longevity
    age = _age(birth_date)
    longevity_note = ""
    if sun_h in [6,8,12] or (lord_9h in [6,8]):
        if age > 50:
            longevity_note = "Sun/9th lord in difficult houses — father's health needs attention as you age"

    return {
        "score": score, "verdict": verdict,
        "blessings": blessings, "challenges": challenges,
        "sun_house": sun_h, "sun_sign": sun_sign,
        "lord_9": lord_9, "lord_9_house": lord_9h,
        "longevity_note": longevity_note,
        "remedy": "Sun remedy: Offer water at sunrise daily. Respect father. Donate wheat on Sundays.",
    }


# ── MOTHER ──────────────────────────────────────────────────────
def engine_mother(planets, house_lords, divisional_charts):
    """
    Mother analysis:
    - 4th house = mother (primary)
    - Moon = significator of mother
    - D12 = parents chart
    """
    lord_4  = _lord(4, house_lords)
    lord_4h = _h(lord_4, planets) if lord_4 else 0
    moon_h  = _h("Moon", planets)
    moon_s  = _s("Moon", planets)
    sat_h   = _h("Saturn", planets)
    d12     = divisional_charts.get("d12",{})
    d12_moon= d12.get("planets",{}).get("Moon",{}).get("house",0) if d12 else 0

    blessings = []
    challenges= []

    if moon_h in [1,2,4,7,10,11]:
        blessings.append(f"Moon in house {moon_h} — mother is nurturing and supportive, strong emotional bond")
    if moon_s == EXALTATION.get("Moon"):
        blessings.append("Moon exalted in Taurus — exceptionally blessed mother, wealth through mother's lineage")
    if lord_4h in [1,4,9,10,11]:
        blessings.append(f"4th lord {lord_4} in house {lord_4h} — mother's blessings strong, happy home life")
    if _h("Jupiter", planets) == 4:
        blessings.append("Jupiter in 4th — wise, generous mother, educational blessing from home")
    if _h("Venus", planets) == 4:
        blessings.append("Venus in 4th — beautiful home, loving mother, comfort and luxury from family")

    if moon_h in [6,8,12]:
        challenges.append(f"Moon in house {moon_h} — mother faces health issues or separation, emotional distance")
    if moon_s == DEBILITATION.get("Moon"):
        challenges.append("Moon debilitated in Scorpio — mother relationship intense and transformative, possible health issues")
    if sat_h == 4:
        challenges.append("Saturn in 4th — mother is strict or faces hardship, home lacks warmth, delayed domestic happiness")
    if lord_4h in [6,8,12]:
        challenges.append(f"4th lord {lord_4} in house {lord_4h} — mother health or home situation needs attention")
    if _h("Rahu", planets) == 4:
        challenges.append("Rahu in 4th — restless home environment, mother may be unconventional or foreign")

    score = max(20, min(95, 50 + len(blessings)*15 - len(challenges)*18))
    verdict = ("Strong maternal blessing — mother is a pillar of support and happiness" if score >= 70
               else "Moderate mother relationship — love present with challenges" if score >= 45
               else "Mother karma requires healing — Lal Kitab remedies essential")

    return {
        "score": score, "verdict": verdict,
        "blessings": blessings, "challenges": challenges,
        "moon_house": moon_h, "moon_sign": moon_s,
        "lord_4": lord_4, "lord_4_house": lord_4h,
        "remedy": "Moon remedy: Respect mother daily. Offer milk to Shiva on Mondays. Keep silver.",
    }


# ── SIBLINGS ────────────────────────────────────────────────────
def engine_siblings(planets, house_lords):
    """
    Siblings analysis:
    - 3rd house = younger siblings (primary)
    - 11th house = elder siblings
    - Mars = karaka for siblings
    """
    lord_3  = _lord(3, house_lords)
    lord_11 = _lord(11, house_lords)
    lord_3h = _h(lord_3, planets) if lord_3 else 0
    lord_11h= _h(lord_11, planets) if lord_11 else 0
    mars_h  = _h("Mars", planets)
    mars_s  = _s("Mars", planets)
    sat_h   = _h("Saturn", planets)

    support  = []
    friction = []

    # Younger siblings
    if lord_3h in [1,3,9,10,11]:
        support.append(f"3rd lord {lord_3} in house {lord_3h} — younger siblings are supportive and successful")
    if mars_h in [3,11]:
        support.append(f"Mars in house {mars_h} — energetic, courageous siblings, active sibling relationships")
    if _h("Jupiter", planets) == 3:
        support.append("Jupiter in 3rd — wise younger siblings, philosophical bonds")

    # Elder siblings
    if lord_11h in [1,3,9,10,11]:
        support.append(f"11th lord {lord_11} in house {lord_11h} — elder siblings bring gains and support")
    if _h("Sun", planets) == 11:
        support.append("Sun in 11th — elder siblings in positions of authority, gains through them")

    # Friction
    if mars_h in [6,8,12]:
        friction.append(f"Mars in house {mars_h} — sibling disputes, competition with brothers especially")
    if mars_s == DEBILITATION.get("Mars"):
        friction.append("Mars debilitated in Cancer — sibling relationships emotionally complex")
    if sat_h == 3:
        friction.append("Saturn in 3rd — younger siblings face hardships, relationship is serious and dutiful")
    if lord_3h in [6,8,12]:
        friction.append(f"3rd lord in house {lord_3h} — younger siblings face challenges, relationship needs work")
    if _h("Rahu", planets) == 3:
        friction.append("Rahu in 3rd — unconventional siblings, possible deception from them")
    if _h("Ketu", planets) == 3:
        friction.append("Ketu in 3rd — past life karma with siblings, separation or spiritual difference")

    num_siblings_indicator = len([p for p,d in planets.items()
                                   if d.get("house") in [3,11]])

    score = max(20, min(90, 50 + len(support)*15 - len(friction)*15))
    verdict = ("Siblings are assets — strong support system from brothers/sisters" if score >= 65
               else "Mixed sibling dynamics — some support, some friction" if score >= 40
               else "Sibling karma is active — boundary setting and remedies needed")

    return {
        "score": score, "verdict": verdict,
        "support_indicators": support, "friction_indicators": friction,
        "mars_house": mars_h, "lord_3": lord_3, "lord_3_house": lord_3h,
        "remedy": "Mars remedy: Help brothers. Feed crows on Tuesdays. Donate blood once a year.",
    }


# ── SECOND MARRIAGE ─────────────────────────────────────────────
def engine_second_marriage(planets, house_lords, divisional_charts, birth_date, gender=""):
    """
    Second marriage indicators:
    - 2nd marriage = 8th house from 7th = 2nd house (accumulated relationships)
    - Rahu in 7th or 1st
    - Multiple signs in 7th
    - D9 Venus in dusthana
    - Venus-Mars conjunction
    """
    lord_7  = _lord(7, house_lords)
    lord_7h = _h(lord_7, planets) if lord_7 else 0
    lord_2  = _lord(2, house_lords)
    venus_h = _h("Venus", planets)
    venus_s = _s("Venus", planets)
    rahu_h  = _h("Rahu", planets)
    mars_h  = _h("Mars", planets)
    sat_h   = _h("Saturn", planets)
    d9      = divisional_charts.get("d9",{})
    d9_venus= d9.get("planets",{}).get("Venus",{}).get("house",0) if d9 else 0

    indicators  = []
    protective  = []

    # Second marriage indicators
    if rahu_h in [7,1]:
        indicators.append(f"Rahu in house {rahu_h} — unconventional marriage path, second relationship likely")
    if venus_h in [6,8,12]:
        indicators.append(f"Venus in house {venus_h} — first marriage has challenges, second connection possible")
    if venus_s == DEBILITATION.get("Venus"):
        indicators.append("Venus debilitated in Virgo — first marriage dissatisfaction, second union possible")
    if mars_h in [7,8] and sat_h in [7,1]:
        indicators.append("Mars and Saturn both influencing 7th — double marital karma, possibly two marriages")
    if lord_7h in [6,8,12]:
        indicators.append(f"7th lord {lord_7} in house {lord_7h} — first marriage under stress, second possible")
    if d9_venus in [6,8,12]:
        indicators.append(f"Venus in D9 house {d9_venus} — soul-level dissatisfaction in first marriage")

    # Protective (single marriage)
    if _h("Jupiter", planets) in [7,2]:
        protective.append(f"Jupiter in house {_h('Jupiter',planets)} — blesses marriage, single stable union favored")
    if venus_h in [1,2,4,7,11]:
        protective.append(f"Venus in house {venus_h} — marriage harmony, single union satisfying")

    age = _age(birth_date)
    risk = min(80, len(indicators)*20 - len(protective)*10)
    verdict = ("Multiple relationship karma — second marriage or partnership likely" if risk >= 60
               else "Possible second marriage under stress circumstances" if risk >= 35
               else "Single marriage indicated — chart supports stable union")

    return {
        "risk_score": risk, "verdict": verdict,
        "indicators": indicators, "protective": protective,
        "note": "Second marriage yoga indicates potential — conscious choice always possible",
        "remedy": "Venus remedy: Honor spouse. Gift white items Fridays. Never lie in relationships.",
    }


# ── GOVERNMENT JOB ──────────────────────────────────────────────
def engine_government_job(planets, house_lords, yogas, divisional_charts):
    """
    Government job indicators:
    - Sun strong (authority)
    - 10th house + 6th house connection
    - Saturn in service houses
    - D10 Sun placement
    """
    lord_10 = _lord(10, house_lords)
    lord_6  = _lord(6, house_lords)
    lord_10h= _h(lord_10, planets) if lord_10 else 0
    lord_6h = _h(lord_6, planets) if lord_6 else 0
    sun_h   = _h("Sun", planets)
    sun_s   = _s("Sun", planets)
    sat_h   = _h("Saturn", planets)
    d10     = divisional_charts.get("d10",{})
    d10_sun = d10.get("planets",{}).get("Sun",{}).get("house",0) if d10 else 0

    indicators  = []
    challenges  = []

    # Strong indicators
    if sun_h in [1,9,10,11]:
        indicators.append(f"Sun in house {sun_h} — natural authority, government affinity")
    if sun_s == EXALTATION.get("Sun"):
        indicators.append("Sun exalted in Aries — exceptional government career, high post possible")
    if sun_h == 10:
        indicators.append("Sun in 10th — government career is primary life path, authority figure")
    if sat_h in [6,10]:
        indicators.append(f"Saturn in house {sat_h} — disciplined service career, government work through merit")
    if lord_10h in [6,10]:
        indicators.append(f"10th lord {lord_10} in house {lord_10h} — career in service/government strongly indicated")
    if lord_6h == 10 or lord_10h == 6:
        indicators.append("6th-10th house connection — service and career are the same thing = government")
    if d10_sun in [1,9,10,11]:
        indicators.append(f"Sun in D10 house {d10_sun} — career chart confirms authority/government")
    if any("Raj" in y.get("name","") for y in yogas):
        indicators.append("Raj Yoga — government recognition, high post in public service")

    # Challenges
    if sun_h in [6,8,12]:
        challenges.append(f"Sun in house {sun_h} — government role possible but after obstacles")
    if sun_s == DEBILITATION.get("Sun"):
        challenges.append("Sun debilitated — authority challenges, government career requires extra effort")

    score = min(95, len(indicators)*18 - len(challenges)*12 + 10)

    # Specific government sectors
    sectors = []
    if sun_h in [9,10]:  sectors.append("IAS/IPS/civil services")
    if sat_h in [6,10]:  sectors.append("public sector/PSU")
    if _h("Mars", planets) in [6,10]: sectors.append("police/military/paramilitary")
    if _h("Mercury", planets) in [6,10]: sectors.append("banking/finance/postal")
    if _h("Jupiter", planets) in [6,9,10]: sectors.append("judiciary/law/education")

    verdict = ("Strong government job yoga — public service is natural calling" if score >= 70
               else "Government job possible — competitive exams favorable during Sun/Saturn dashas" if score >= 45
               else "Private sector more natural — government is secondary option")

    return {
        "score": score, "verdict": verdict,
        "indicators": indicators, "challenges": challenges,
        "likely_sectors": sectors,
        "best_timing": "Sun or Saturn Mahadasha/Antardasha for government job entry",
        "remedy": "Sun remedy: Offer water at sunrise. Respect authority figures. Keep career ethical.",
    }


# ── FAME / PUBLIC RECOGNITION ───────────────────────────────────
def engine_fame(planets, house_lords, yogas, divisional_charts):
    """
    Fame and recognition:
    - 10th house (public life)
    - Sun (recognition)
    - Rahu (mass fame)
    - 11th house (large audiences)
    - D10 chart
    """
    sun_h   = _h("Sun", planets)
    rahu_h  = _h("Rahu", planets)
    moon_h  = _h("Moon", planets)
    jup_h   = _h("Jupiter", planets)
    lord_10h= _h(_lord(10, house_lords), planets) if _lord(10, house_lords) else 0
    d10     = divisional_charts.get("d10",{})
    d10_sun = d10.get("planets",{}).get("Sun",{}).get("house",0) if d10 else 0
    d10_rahu= d10.get("planets",{}).get("Rahu",{}).get("house",0) if d10 else 0

    indicators = []
    fame_type  = []

    if sun_h in [1,9,10,11]:
        indicators.append(f"Sun in house {sun_h} — natural recognition, authority figure, respected publicly")
    if rahu_h in [1,4,7,10]:
        indicators.append(f"Rahu in house {rahu_h} — mass appeal, viral fame possible, unconventional recognition")
        fame_type.append("mass/viral fame")
    if moon_h in [10,11]:
        indicators.append(f"Moon in house {moon_h} — public emotional connection, fame through nurturing/public")
        fame_type.append("public/emotional fame")
    if jup_h in [1,10,11]:
        indicators.append(f"Jupiter in house {jup_h} — respected teacher/advisor, institutional recognition")
        fame_type.append("intellectual/wisdom fame")
    if lord_10h in [1,10,11]:
        indicators.append(f"10th lord in house {lord_10h} — career recognition prominent")
    if d10_sun in [1,10,11]:
        indicators.append(f"Sun in D10 house {d10_sun} — career chart confirms recognition")
    if d10_rahu in [1,10]:
        indicators.append(f"Rahu in D10 house {d10_rahu} — unconventional career fame")

    # Special yogas
    if any("Raj" in y.get("name","") for y in yogas):
        indicators.append("Raj Yoga — authoritative recognition, people follow this person")
        fame_type.append("authority/leadership fame")
    if any("Gajakesari" in y.get("name","") for y in yogas):
        indicators.append("Gajakesari Yoga — public wisdom and recognition")

    score = min(95, len(indicators)*16 + 10)
    verdict = ("Strong fame yoga — public recognition is destined" if score >= 70
               else "Moderate recognition — known and respected in chosen field" if score >= 45
               else "Local/professional recognition — not mass fame, deep respect in small circle")

    return {
        "score": score, "verdict": verdict,
        "indicators": indicators,
        "fame_type": " + ".join(fame_type) if fame_type else "earned professional recognition",
        "peak_timing": "Rahu MD for mass fame, Sun/Jupiter MD for earned recognition",
    }


# ── STOCK MARKET / SPECULATION ──────────────────────────────────
def engine_speculation(planets, house_lords, yogas, dashas, birth_date):
    """
    Stock market and speculation:
    - 5th house (speculation, gambling, creativity)
    - Rahu (sudden gains/losses)
    - Jupiter (wisdom in markets)
    - Mercury (trading, analytics)
    - 11th house (gains)
    """
    lord_5  = _lord(5, house_lords)
    lord_5h = _h(lord_5, planets) if lord_5 else 0
    lord_11 = _lord(11, house_lords)
    lord_11h= _h(lord_11, planets) if lord_11 else 0
    rahu_h  = _h("Rahu", planets)
    jup_h   = _h("Jupiter", planets)
    merc_h  = _h("Mercury", planets)
    sat_h   = _h("Saturn", planets)
    mars_h  = _h("Mars", planets)

    gain_indicators = []
    risk_indicators = []

    # Gain indicators
    if jup_h in [2,5,9,11]:
        gain_indicators.append(f"Jupiter in house {jup_h} — wisdom in speculation, long-term gains")
    if merc_h in [5,10,11]:
        gain_indicators.append(f"Mercury in house {merc_h} — analytical mind for markets, trading ability")
    if lord_5h in [1,2,9,10,11]:
        gain_indicators.append(f"5th lord {lord_5} in house {lord_5h} — speculation favored")
    if lord_5h == 11 or lord_11h == 5:
        gain_indicators.append("5th-11th connection — speculation directly converts to gains")
    if rahu_h == 11:
        gain_indicators.append("Rahu in 11th — sudden large gains from unconventional sources including markets")
    if any("Dhana" in y.get("name","") for y in yogas):
        gain_indicators.append("Dhana Yoga — wealth accumulation through multiple channels including speculation")

    # Risk indicators
    if rahu_h == 5:
        risk_indicators.append("Rahu in 5th — gambling addiction risk, speculative losses, obsessive trading")
    if sat_h == 5:
        risk_indicators.append("Saturn in 5th — speculation brings heavy losses, avoid markets especially in Saturn periods")
    if mars_h == 5 and not jup_h == 5:
        risk_indicators.append("Mars in 5th without Jupiter — aggressive speculative moves, rash decisions in markets")
    if lord_5h in [6,8,12]:
        risk_indicators.append(f"5th lord in house {lord_5h} — speculation leads to debt or loss")

    score = max(10, min(90, len(gain_indicators)*20 - len(risk_indicators)*25 + 20))
    verdict = ("Favorable speculation chart — markets and investment can be wealth vehicles" if score >= 65
               else "Moderate speculation potential — selective, research-based investing only" if score >= 40
               else "Speculation is risky for this chart — stick to fixed income and real assets")

    # Best timing
    now = datetime.utcnow()
    good_periods = []
    for row in dashas.get("vimsottari",[]):
        lord  = row.get("lord_or_sign") or row.get("planet_or_sign","")
        level = row.get("level") or row.get("type","")
        if lord not in ["Jupiter","Mercury","Venus","Rahu"] or level!="antardasha":
            continue
        try:
            sd = datetime.strptime(str(row.get("start_date",""))[:10],"%Y-%m-%d")
            ed = datetime.strptime(str(row.get("end_date",""))[:10],"%Y-%m-%d")
            if sd <= now <= ed:
                good_periods.append(f"Current {lord} AD — active speculation period")
            elif sd > now and len(good_periods) < 2:
                good_periods.append(f"{lord} AD {sd.year} — upcoming favorable period")
        except: pass

    return {
        "score": score, "verdict": verdict,
        "gain_indicators": gain_indicators,
        "risk_indicators": risk_indicators,
        "best_periods": good_periods[:2],
        "avoid_periods": "Saturn and Ketu Antardasha — avoid speculation in these",
        "recommendation": "Long-term equity" if jup_h in [2,5,11] else "Fixed deposits/real assets safer",
    }


# ── INHERITANCE ─────────────────────────────────────────────────
def engine_inheritance(planets, house_lords, birth_date):
    """
    Inheritance indicators:
    - 8th house (inheritance, sudden gains from others)
    - 2nd house (accumulated family wealth)
    - 4th house (ancestral property)
    - Jupiter (benefactor)
    """
    lord_8  = _lord(8, house_lords)
    lord_8h = _h(lord_8, planets) if lord_8 else 0
    lord_4  = _lord(4, house_lords)
    lord_4h = _h(lord_4, planets) if lord_4 else 0
    lord_2  = _lord(2, house_lords)
    lord_2h = _h(lord_2, planets) if lord_2 else 0
    sat_h   = _h("Saturn", planets)
    jup_h   = _h("Jupiter", planets)
    rahu_h  = _h("Rahu", planets)
    mars_h  = _h("Mars", planets)

    indicators = []
    disputes   = []

    # Inheritance indicators
    if lord_8h in [1,2,4,9,10,11]:
        indicators.append(f"8th lord {lord_8} in house {lord_8h} — inheritance flows into life naturally")
    if lord_8h == 2 or lord_2h == 8:
        indicators.append("8th-2nd exchange — strong inheritance and accumulated wealth connection")
    if lord_8h == 4 or lord_4h == 8:
        indicators.append("8th-4th connection — ancestral property inheritance strongly indicated")
    if jup_h in [2,4,8,9,11]:
        indicators.append(f"Jupiter in house {jup_h} — blessed with inheritance, benefactors in life")
    if sat_h in [8,4]:
        indicators.append(f"Saturn in house {sat_h} — inheritance through elderly relatives, delayed but certain")
    if rahu_h in [2,8]:
        indicators.append(f"Rahu in house {rahu_h} — sudden or unconventional inheritance, foreign assets possible")

    # Disputes
    if mars_h in [4,8,12]:
        disputes.append(f"Mars in house {mars_h} — property/inheritance disputes with siblings or relatives")
    if lord_4h in [6,8]:
        disputes.append(f"4th lord in house {lord_4h} — ancestral property has legal complications")
    if _h("Rahu", planets) == 4 and mars_h in [1,4,7,8]:
        disputes.append("Rahu in 4th + Mars influence — serious property/inheritance disputes possible")

    score = max(15, min(90, len(indicators)*18 - len(disputes)*15 + 15))
    verdict = ("Strong inheritance indicators — ancestral/family wealth flows to you" if score >= 65
               else "Moderate inheritance possible — through effort and relationships" if score >= 40
               else "Limited inheritance — self-made wealth is the path")

    age = _age(birth_date)
    timing = ""
    if lord_8h in [1,4,9,11]:
        timing = "Inheritance most likely during 8th lord's Mahadasha or Antardasha"
    if age > 50 and sat_h in [8,4]:
        timing = "Saturn indicates late inheritance — after 50 more likely"

    return {
        "score": score, "verdict": verdict,
        "indicators": indicators, "disputes": disputes,
        "timing": timing,
        "lord_8": lord_8, "lord_8_house": lord_8h,
        "remedy": "Saturn remedy for delayed inheritance: Serve poor on Saturdays. Mars remedy for disputes: Donate blood, help brothers.",
    }


# ── ASHTOTTARI CONFLUENCE ───────────────────────────────────────
def engine_ashtottari_confluence(
    chart_data: dict,
    vimsottari_dashas: list,
    ashtottari_dashas: list,
    jaimini_current_sign: str = "",
) -> dict:
    """
    Confluence scoring across all 3 dasha systems.
    When 2+ systems agree on same theme → confidence increases.
    Ashtottari is especially relevant when Rahu is prominent.
    """
    now = datetime.utcnow()
    planets = chart_data.get("planets", {})
    rahu_h  = _h("Rahu", planets)

    # Is Ashtottari relevant for this chart?
    # Relevant when Rahu is in angular (1,4,7,10) or 11th house
    ashtottari_relevant = rahu_h in [1, 4, 7, 10, 11, 2]

    # Get current Vimsottari
    vim_md = vim_ad = ""
    for row in vimsottari_dashas:
        level = row.get("level") or row.get("type","")
        try:
            sd = datetime.strptime(str(row.get("start_date",""))[:10],"%Y-%m-%d")
            ed = datetime.strptime(str(row.get("end_date",""))[:10],"%Y-%m-%d")
            if sd <= now <= ed:
                lord = row.get("lord_or_sign") or row.get("planet_or_sign","")
                if level == "mahadasha": vim_md = lord
                elif level == "antardasha": vim_ad = lord
        except: pass

    # Get current Ashtottari
    ash_md = ash_ad = ""
    for row in ashtottari_dashas:
        level = row.get("level") or row.get("type","")
        try:
            sd = datetime.strptime(str(row.get("start_date",""))[:10],"%Y-%m-%d")
            ed = datetime.strptime(str(row.get("end_date",""))[:10],"%Y-%m-%d")
            if sd <= now <= ed:
                lord = row.get("lord_or_sign") or row.get("planet_or_sign","")
                if level == "mahadasha": ash_md = lord
                elif level == "antardasha": ash_ad = lord
        except: pass

    # Ashtottari sequence and themes
    ASH_THEMES = {
        "Sun":     "authority, father, career recognition, government",
        "Moon":    "emotions, mother, public life, mind",
        "Mars":    "energy, property, siblings, courage, conflict",
        "Mercury": "intellect, business, communication, trade",
        "Saturn":  "discipline, service, delays, karma, longevity",
        "Jupiter": "expansion, wealth, children, wisdom, fortune",
        "Rahu":    "transformation, foreign, technology, disruption, shadow",
        "Venus":   "relationships, luxury, creativity, pleasure, vehicles",
    }

    # Confluence analysis
    confluence_points = []
    confidence = 50  # base

    # Vimsottari + Ashtottari same MD lord
    if vim_md and ash_md and vim_md == ash_md:
        confidence += 25
        confluence_points.append(
            f"STRONG: Vimsottari MD ({vim_md}) = Ashtottari MD ({ash_md}) — "
            f"theme doubled: {ASH_THEMES.get(vim_md,'')}"
        )
    elif vim_md and ash_md:
        # Different lords — note the dual theme
        confluence_points.append(
            f"DUAL: Vimsottari MD={vim_md} ({ASH_THEMES.get(vim_md,'')}) "
            f"+ Ashtottari MD={ash_md} ({ASH_THEMES.get(ash_md,'')})"
        )

    # Jaimini adds third confirmation
    if jaimini_current_sign and vim_md:
        jaimini_lord = SIGN_LORDS.get(jaimini_current_sign,"")
        if jaimini_lord == vim_md:
            confidence += 15
            confluence_points.append(
                f"TRIPLE confluence: Jaimini sign lord ({jaimini_lord}) = "
                f"Vimsottari MD ({vim_md}) — 90%+ confidence on this period's theme"
            )

    # AD confluence
    if vim_ad and ash_ad and vim_ad == ash_ad:
        confidence += 15
        confluence_points.append(
            f"AD CONFLUENCE: Both systems in {vim_ad} sub-period — "
            f"theme intensified: {ASH_THEMES.get(vim_ad,'')}"
        )

    confidence = min(confidence, 95)

    return {
        "ashtottari_relevant": ashtottari_relevant,
        "rahu_house": rahu_h,
        "vimsottari_md": vim_md, "vimsottari_ad": vim_ad,
        "ashtottari_md": ash_md, "ashtottari_ad": ash_ad,
        "jaimini_sign": jaimini_current_sign,
        "confluence_points": confluence_points,
        "overall_confidence": confidence,
        "note": (
            f"Ashtottari is {'HIGHLY RELEVANT' if ashtottari_relevant else 'secondary'} "
            f"for this chart (Rahu in house {rahu_h}). "
            f"{'Use Ashtottari alongside Vimsottari for maximum accuracy.' if ashtottari_relevant else 'Vimsottari is primary.'}"
        ),
        "current_ash_theme": ASH_THEMES.get(ash_md,"") if ash_md else "",
    }


# ══════════════════════════════════════════════════════════════
# MASTER RUNNER — Tier 1
# ══════════════════════════════════════════════════════════════

TIER1_CONCERN_MAP = {
    "father":          "father",
    "dad":             "father",
    "mother":          "mother",
    "mom":             "mother",
    "sibling":         "siblings",
    "brother":         "siblings",
    "sister":          "siblings",
    "second marriage": "second_marriage",
    "remarriage":      "second_marriage",
    "government":      "government_job",
    "ias":             "government_job",
    "ips":             "government_job",
    "civil service":   "government_job",
    "fame":            "fame",
    "recognition":     "fame",
    "celebrity":       "fame",
    "stock":           "speculation",
    "market":          "speculation",
    "trading":         "speculation",
    "invest":          "speculation",
    "inherit":         "inheritance",
    "ancestral":       "inheritance",
    "will":            "inheritance",
}


def run_tier1_engines(
    chart_data: dict,
    dashas: dict,
    birth_date: str,
    concern: str = "general",
    gender: str = "",
    jaimini_current_sign: str = "",
) -> dict:
    planets    = chart_data.get("planets", {})
    lagna      = chart_data.get("lagna", {})
    lagna_sign = lagna.get("sign","") if isinstance(lagna, dict) else str(lagna)
    house_lords= chart_data.get("house_lords", {})
    yogas      = chart_data.get("yogas", [])
    divs       = chart_data.get("divisional_charts", {})

    concern_lower = concern.lower()
    matched = None
    for keyword, engine_name in TIER1_CONCERN_MAP.items():
        if keyword in concern_lower:
            matched = engine_name
            break

    results = {}

    # Always run Ashtottari confluence
    vim_rows = dashas.get("vimsottari",[])
    ash_rows = dashas.get("ashtottari",[])
    results["ashtottari_confluence"] = engine_ashtottari_confluence(
        chart_data, vim_rows, ash_rows, jaimini_current_sign
    )

    # Run concern-specific engine
    if matched == "father":
        results["father"] = engine_father(planets, house_lords, divs, birth_date)
    elif matched == "mother":
        results["mother"] = engine_mother(planets, house_lords, divs)
    elif matched == "siblings":
        results["siblings"] = engine_siblings(planets, house_lords)
    elif matched == "second_marriage":
        results["second_marriage"] = engine_second_marriage(
            planets, house_lords, divs, birth_date, gender)
    elif matched == "government_job":
        results["government_job"] = engine_government_job(planets, house_lords, yogas, divs)
    elif matched == "fame":
        results["fame"] = engine_fame(planets, house_lords, yogas, divs)
    elif matched == "speculation":
        results["speculation"] = engine_speculation(planets, house_lords, yogas, dashas, birth_date)
    elif matched == "inheritance":
        results["inheritance"] = engine_inheritance(planets, house_lords, birth_date)

    return results


def build_tier1_verdicts_block(results: dict) -> str:
    if not results:
        return ""

    lines = [
        "═══════════════════════════════════════════════════════",
        "TIER 1 DOMAIN VERDICTS (Python-calculated)",
        "═══════════════════════════════════════════════════════",
    ]

    LABELS = {
        "father":               "FATHER ANALYSIS",
        "mother":               "MOTHER ANALYSIS",
        "siblings":             "SIBLINGS ANALYSIS",
        "second_marriage":      "SECOND MARRIAGE",
        "government_job":       "GOVERNMENT JOB",
        "fame":                 "FAME / RECOGNITION",
        "speculation":          "STOCK MARKET / SPECULATION",
        "inheritance":          "INHERITANCE",
        "ashtottari_confluence":"ASHTOTTARI CONFLUENCE",
    }

    for engine, data in results.items():
        if not data:
            continue
        label = LABELS.get(engine, engine.upper())
        lines.append(f"\n{label}:")

        if engine == "ashtottari_confluence":
            lines.append(f"  Relevant: {'YES' if data.get('ashtottari_relevant') else 'SECONDARY'} (Rahu in house {data.get('rahu_house')})")
            lines.append(f"  Vimsottari: {data.get('vimsottari_md','?')} MD / {data.get('vimsottari_ad','?')} AD")
            lines.append(f"  Ashtottari: {data.get('ashtottari_md','?')} MD / {data.get('ashtottari_ad','?')} AD")
            lines.append(f"  Confidence: {data.get('overall_confidence',50)}%")
            for cp in data.get("confluence_points",[]):
                lines.append(f"  ✓ {cp}")
            lines.append(f"  {data.get('note','')}")
            continue

        score_key = next((k for k in ["score","risk_score","divorce_risk_score"] if k in data), None)
        if score_key:
            lines.append(f"  Score: {data[score_key]}/100")
        if data.get("verdict"):
            lines.append(f"  Verdict: {data['verdict']}")

        for ind_key in ["indicators","blessings","support_indicators",
                        "gain_indicators","positive_indicators"]:
            items = data.get(ind_key,[])
            if items:
                for i in items[:3]: lines.append(f"  ✓ {i}")
                break

        for warn_key in ["challenges","friction_indicators","risk_indicators",
                         "disputes","warnings"]:
            items = data.get(warn_key,[])
            if items:
                for i in items[:2]: lines.append(f"  ⚠ {i}")
                break

        for extra in ["likely_sectors","fame_type","recommendation",
                      "best_timing","timing","best_periods"]:
            if data.get(extra):
                val = data[extra]
                if isinstance(val, list): val = ", ".join(val)
                lines.append(f"  → {extra.replace('_',' ').title()}: {val}")

        if data.get("remedy"):
            lines.append(f"  Remedy: {data['remedy']}")

    lines += [
        "",
        "INSTRUCTION: These are pre-calculated facts. Explain them directly.",
        "Always give the verdict first, then explanation, then remedy.",
        "═══════════════════════════════════════════════════════",
    ]
    return "\n".join(lines)
