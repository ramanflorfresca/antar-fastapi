"""
antar_engine/domain_engines_tier234.py

Tier 2: Chronic disease, eye problems, business partnership,
         bankruptcy risk, pilgrimage, loss of parent timing

Tier 3: Widowhood, awards, vehicle/transport

Tier 4 (Special): New house, new vehicle (Lal Kitab Venus rules)
         + WOW effects: Vargottama, Kala Sarpa, Gandanta,
           Parivartana Yoga, Pushkara Navamsa, eclipse birth,
           Atmakaraka strength, rare combinations
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
MOVABLE = ["Aries","Cancer","Libra","Capricorn"]
FIXED   = ["Taurus","Leo","Scorpio","Aquarius"]
DUAL    = ["Gemini","Virgo","Sagittarius","Pisces"]

def _h(p,pl): return pl.get(p,{}).get("house",0)
def _s(p,pl): return pl.get(p,{}).get("sign","")
def _d(p,pl): return pl.get(p,{}).get("degree",0)
def _l(n,hl):
    if not isinstance(hl,dict): return ""
    return hl.get(n,{}).get("lord","")
def _age(bd):
    try: return (date.today()-date.fromisoformat(bd[:10])).days//365
    except: return 35


# ══════════════════════════════════════════════════════════════
# TIER 2
# ══════════════════════════════════════════════════════════════

def engine_chronic_disease(planets, house_lords, birth_date):
    """Chronic disease potential — Saturn, 6th house, 8th house."""
    lord_6  = _l(6, house_lords)
    lord_6h = _h(lord_6, planets) if lord_6 else 0
    sat_h   = _h("Saturn", planets)
    sat_s   = _s("Saturn", planets)
    rahu_h  = _h("Rahu", planets)
    mars_h  = _h("Mars", planets)
    sun_h   = _h("Sun", planets)
    moon_h  = _h("Moon", planets)
    age     = _age(birth_date)

    indicators = []
    systems    = []

    # Primary chronic indicators
    if sat_h in [1,6,8]:
        indicators.append(f"Saturn in house {sat_h} — bones, joints, chronic cold/damp conditions")
        systems.append("skeletal/joints")
    if sat_s == DEBILITATION.get("Saturn"):
        indicators.append("Saturn debilitated in Aries — bone density, immune system weakness")
    if lord_6h in [1,6,8,12]:
        indicators.append(f"6th lord {lord_6} in house {lord_6h} — chronic disease pattern in life")
    if rahu_h in [1,6,8]:
        indicators.append(f"Rahu in house {rahu_h} — unusual or undiagnosed chronic conditions")
        systems.append("neurological/autoimmune")
    if _h("Jupiter",planets) in [6,8] and _s("Jupiter",planets)==DEBILITATION.get("Jupiter"):
        indicators.append("Jupiter debilitated near 6/8 — liver, diabetes, weight-related chronic issues")
        systems.append("metabolic/liver")
    if sun_h in [6,8,12]:
        systems.append("cardiac/vitality")
    if moon_h in [6,8,12]:
        systems.append("digestive/lymphatic")

    score = min(80, len(indicators)*20 + (10 if age>50 else 0))
    verdict = ("Chronic disease indicators present — preventive care and regular monitoring essential" if score>=50
               else "Moderate health caution — maintain lifestyle discipline" if score>=25
               else "Generally good health constitution — standard care sufficient")

    return {
        "score": score, "verdict": verdict, "indicators": indicators,
        "vulnerable_systems": list(set(systems)),
        "age_factor": f"Age {age} — {'heightened monitoring recommended' if age>50 else 'preventive lifestyle important'}",
        "remedy": "Saturn: Serve poor Saturdays, warm oil massage. Rahu: Feed crows, avoid chemicals.",
    }


def engine_eye_problems(planets, house_lords):
    """Eye problem indicators — Sun, Moon, 2nd house (right eye), 12th (left eye)."""
    sun_h  = _h("Sun", planets)
    sun_s  = _s("Sun", planets)
    moon_h = _h("Moon", planets)
    moon_s = _s("Moon", planets)
    venus_h= _h("Venus", planets)
    lord_2 = _l(2, house_lords)
    lord_2h= _h(lord_2, planets) if lord_2 else 0
    lord_12= _l(12, house_lords)
    lord_12h=_h(lord_12, planets) if lord_12 else 0
    rahu_h = _h("Rahu", planets)
    sat_h  = _h("Saturn", planets)

    indicators = []
    eye_type   = []

    if sun_h in [6,8,12]:
        indicators.append(f"Sun in house {sun_h} — right eye vulnerability, vision issues")
        eye_type.append("right eye")
    if sun_s == DEBILITATION.get("Sun"):
        indicators.append("Sun debilitated — eye weakness, light sensitivity, headaches")
    if moon_h in [6,8,12]:
        indicators.append(f"Moon in house {moon_h} — left eye issues, night vision, watery eyes")
        eye_type.append("left eye")
    if moon_s == DEBILITATION.get("Moon"):
        indicators.append("Moon debilitated in Scorpio — chronic eye inflammation, emotional vision issues")
    if rahu_h in [2,12]:
        indicators.append(f"Rahu in house {rahu_h} — unusual eye conditions, spectacles needed")
    if sat_h in [2,12]:
        indicators.append(f"Saturn in house {sat_h} — chronic eye weakness, cataracts in older age")
    if lord_2h in [6,8,12]:
        indicators.append(f"2nd lord {lord_2} in house {lord_2h} — right eye and face area challenges")
    if venus_h in [6,8,12]:
        indicators.append(f"Venus in house {venus_h} — eye aesthetics, kidney-eye connection")

    risk = min(75, len(indicators)*18)
    verdict = ("Eye care is important — regular checkups essential" if risk>=50
               else "Some eye sensitivity — screen time management important" if risk>=25
               else "Eyes generally healthy — standard care sufficient")

    return {
        "risk_score": risk, "verdict": verdict, "indicators": indicators,
        "eye_type": eye_type,
        "remedy": "Sun remedy: Donate copper on Sundays. Moon: Offer milk Mondays. Avoid staring at screens for extended periods.",
    }


def engine_business_partnership(planets, house_lords, yogas):
    """Business partnership vs solo business analysis."""
    lord_7  = _l(7, house_lords)
    lord_7h = _h(lord_7, planets) if lord_7 else 0
    lord_11 = _l(11, house_lords)
    lord_11h= _h(lord_11, planets) if lord_11 else 0
    merc_h  = _h("Mercury", planets)
    venus_h = _h("Venus", planets)
    rahu_h  = _h("Rahu", planets)
    sat_h   = _h("Saturn", planets)
    jup_h   = _h("Jupiter", planets)
    mars_h  = _h("Mars", planets)

    partner_ind = []
    solo_ind    = []
    risk_ind    = []

    # Partnership indicators
    if lord_7h in [1,7,10,11]:
        partner_ind.append(f"7th lord {lord_7} in house {lord_7h} — business partnerships highly favorable")
    if merc_h == 7:
        partner_ind.append("Mercury in 7th — communication-based partnerships, deals through partners")
    if venus_h in [7,11]:
        partner_ind.append(f"Venus in house {venus_h} — harmonious partnerships, creative collaborations")
    if jup_h in [7,9,11]:
        partner_ind.append(f"Jupiter in house {jup_h} — ethical wise partner, expansion through partnership")
    if any("Raj" in y.get("name","") and "conjunction" in y.get("name","") for y in yogas):
        partner_ind.append("Raj Yoga from conjunction — success through combining with right partner")

    # Solo indicators
    if mars_h in [1,10]:
        solo_ind.append(f"Mars in house {mars_h} — independent action, solo execution stronger")
    if _h("Sun",planets) in [1,10]:
        solo_ind.append("Sun in 1/10 — solo authority, natural leader, partnership dilutes strength")
    if sat_h in [7]:
        solo_ind.append("Saturn in 7th — partnerships carry karmic weight, choose very carefully")

    # Partnership risks
    if rahu_h == 7:
        risk_ind.append("Rahu in 7th — partner may be foreign, unconventional, or karmic — due diligence essential")
    if lord_7h in [6,8,12]:
        risk_ind.append(f"7th lord in house {lord_7h} — partnerships have conflict potential, legal safeguards needed")
    if mars_h in [6,7,8] and venus_h in [6,8]:
        risk_ind.append("Mars + Venus in difficult houses — romantic-business mixing leads to complications")

    partner_score = len(partner_ind) * 20
    solo_score    = len(solo_ind) * 20

    if partner_score > solo_score:
        verdict = f"Partnership strongly favored — multiple co-founder/partner indicators ({partner_score} vs solo {solo_score})"
        recommendation = "partnership"
    elif solo_score > partner_score:
        verdict = f"Solo business more natural — self-reliant chart ({solo_score} vs partnership {partner_score})"
        recommendation = "solo"
    else:
        verdict = "Both viable — choose partner who complements your weakness"
        recommendation = "selective_partnership"

    return {
        "partner_score": partner_score, "solo_score": solo_score,
        "verdict": verdict, "recommendation": recommendation,
        "partnership_indicators": partner_ind,
        "solo_indicators": solo_ind,
        "partnership_risks": risk_ind,
        "advice": "If partnering: formalize with legal agreements. 7th lord period = best time to enter partnerships.",
    }


def engine_bankruptcy_risk(planets, house_lords, yogas):
    """Bankruptcy and severe financial loss indicators."""
    lord_6  = _l(6, house_lords)
    lord_8  = _l(8, house_lords)
    lord_12 = _l(12, house_lords)
    lord_2  = _l(2, house_lords)
    lord_11 = _l(11, house_lords)
    lord_6h = _h(lord_6, planets) if lord_6 else 0
    lord_8h = _h(lord_8, planets) if lord_8 else 0
    lord_12h= _h(lord_12, planets) if lord_12 else 0
    lord_2h = _h(lord_2, planets) if lord_2 else 0
    sat_h   = _h("Saturn", planets)
    rahu_h  = _h("Rahu", planets)
    mars_h  = _h("Mars", planets)
    jup_h   = _h("Jupiter", planets)

    risk_factors   = []
    protection     = []

    # High risk patterns
    if lord_2h in [6,8,12]:
        risk_factors.append(f"2nd lord {lord_2} in house {lord_2h} — wealth house lord in loss/debt/transformation")
    if lord_11h := _h(_l(11,house_lords), planets):
        if lord_11h in [6,8,12]:
            risk_factors.append(f"11th lord in house {lord_11h} — gains house lord weakened")
    if rahu_h in [2,11] and sat_h in [6,8,12]:
        risk_factors.append("Rahu in wealth house + Saturn in dusthana — sudden wealth destruction possible")
    if lord_6h in [2,11] and lord_8h in [2,11]:
        risk_factors.append("Debt (6th) and transformation (8th) lords in wealth houses — debt crisis pattern")
    if lord_12h in [2,11]:
        risk_factors.append(f"12th lord in wealth house — expenditure eats into income, leakage pattern")
    if mars_h in [2,7,8] and rahu_h in [2,8,11]:
        risk_factors.append("Mars + Rahu in financial houses — aggressive financial risk-taking leads to losses")

    # Protection factors
    if jup_h in [2,5,9,11]:
        protection.append(f"Jupiter in house {jup_h} — Jupiter protects wealth, bankruptcy unlikely")
    if any("Dhana" in y.get("name","") for y in yogas):
        protection.append("Dhana Yoga present — wealth is protected despite challenges")
    if sat_h == 11:
        protection.append("Saturn in 11th — slow steady gains prevent catastrophic loss")

    risk = max(0, min(80, len(risk_factors)*20 - len(protection)*15))
    verdict = ("Significant bankruptcy risk — financial discipline and safeguards essential" if risk>=60
               else "Moderate financial stress possible — maintain reserves, avoid over-leverage" if risk>=35
               else "Low bankruptcy risk — chart supports wealth protection")

    return {
        "risk_score": risk, "verdict": verdict,
        "risk_factors": risk_factors, "protection": protection,
        "remedy": "Saturn remedy: Never default on loans. Serve poor Saturdays. Keep accounts clean.",
        "advice": "Avoid debt during Rahu and Saturn Antardasha periods especially.",
    }


def engine_pilgrimage(planets, house_lords, birth_date):
    """Pilgrimage and religious journey indicators."""
    lord_9  = _l(9, house_lords)
    lord_9h = _h(lord_9, planets) if lord_9 else 0
    jup_h   = _h("Jupiter", planets)
    ketu_h  = _h("Ketu", planets)
    moon_h  = _h("Moon", planets)
    sat_h   = _h("Saturn", planets)
    age     = _age(birth_date)

    indicators = []

    if lord_9h in [1,9,12]:
        indicators.append(f"9th lord {lord_9} in house {lord_9h} — pilgrimage is part of life dharma")
    if jup_h in [9,12]:
        indicators.append(f"Jupiter in house {jup_h} — religious journeys bring profound blessings")
    if ketu_h in [9,12]:
        indicators.append(f"Ketu in house {ketu_h} — spiritual pilgrimage is soul's calling")
    if moon_h in [9,12]:
        indicators.append(f"Moon in house {moon_h} — emotional fulfillment through sacred travel")
    if sat_h in [9,12]:
        indicators.append(f"Saturn in house {sat_h} — karmic pilgrimage, sacred sites healing")

    # Best timing
    timing = "During Jupiter or Ketu Mahadasha/Antardasha — most spiritually potent"
    if ketu_h in [9,12]:
        timing = "Ketu period is strongly indicated for pilgrimage — it fulfills past-life spiritual promises"

    score = min(90, len(indicators)*20)
    verdict = ("Pilgrimage strongly indicated — sacred travel transforms this person deeply" if score>=60
               else "Religious travel beneficial — at least one significant pilgrimage recommended" if score>=30
               else "Pilgrimage is personally rewarding but not specifically indicated in chart")

    return {
        "score": score, "verdict": verdict, "indicators": indicators,
        "timing": timing,
        "note": f"Age {age} — {'later life pilgrimage (50+) is deeply transformative for this chart' if age<40 else 'now is a good time for sacred travel'}",
    }


def engine_loss_of_parent(planets, house_lords, birth_date):
    """Timing indicators for loss of parents — handled sensitively."""
    sun_h   = _h("Sun", planets)
    moon_h  = _h("Moon", planets)
    sat_h   = _h("Saturn", planets)
    lord_9  = _l(9, house_lords)
    lord_4  = _l(4, house_lords)
    lord_9h = _h(lord_9, planets) if lord_9 else 0
    lord_4h = _h(lord_4, planets) if lord_4 else 0
    age     = _age(birth_date)

    father_indicators = []
    mother_indicators = []

    # Father vulnerability
    if sun_h in [6,8,12]:
        father_indicators.append(f"Sun in house {sun_h} — father's health needs attention")
    if lord_9h in [6,8,12]:
        father_indicators.append(f"9th lord {lord_9} in house {lord_9h} — father karma is active")
    if sat_h == 9:
        father_indicators.append("Saturn in 9th — father faces delays and hardships in life")

    # Mother vulnerability
    if moon_h in [6,8,12]:
        mother_indicators.append(f"Moon in house {moon_h} — mother's health needs careful attention")
    if lord_4h in [6,8,12]:
        mother_indicators.append(f"4th lord {lord_4} in house {lord_4h} — mother karma is active")
    if sat_h == 4:
        mother_indicators.append("Saturn in 4th — mother faces hardships, home life affected")

    father_risk = min(70, len(father_indicators)*25)
    mother_risk = min(70, len(mother_indicators)*25)

    timing_note = ""
    if age > 60:
        timing_note = "At this life stage, parent health naturally becomes a priority — chart indicators heighten the need for care."
    elif father_risk >= 50 or mother_risk >= 50:
        timing_note = "During Sun/9th lord dasha (father) or Moon/4th lord dasha (mother) — most sensitive periods."

    return {
        "father_risk": father_risk,
        "mother_risk": mother_risk,
        "father_indicators": father_indicators,
        "mother_indicators": mother_indicators,
        "timing_note": timing_note,
        "remedy": "Sun remedy: Offer water daily at sunrise. Respect father actively. Moon: Serve mother. Keep mother healthy.",
        "sensitivity_note": "This is karmic timing — remedies and care can ease but not always prevent.",
    }


# ══════════════════════════════════════════════════════════════
# TIER 3
# ══════════════════════════════════════════════════════════════

def engine_widowhood(planets, house_lords, divisional_charts, gender=""):
    """Widowhood and spouse longevity indicators — handled with sensitivity."""
    lord_7  = _l(7, house_lords)
    lord_7h = _h(lord_7, planets) if lord_7 else 0
    lord_8  = _l(8, house_lords)
    lord_8h = _h(lord_8, planets) if lord_8 else 0
    venus_h = _h("Venus", planets)
    mars_h  = _h("Mars", planets)
    sat_h   = _h("Saturn", planets)
    d9      = divisional_charts.get("d9",{})
    d9_7th  = d9.get("planets",{})

    risk_factors = []
    protection   = []

    if lord_7h in [6,8,12]:
        risk_factors.append(f"7th lord {lord_7} in house {lord_7h} — spouse faces challenges in this lifetime")
    if lord_8h == 7 or lord_7h == 8:
        risk_factors.append("7th-8th exchange — longevity of spouse and marriage transformation connected")
    if mars_h in [7,8] and sat_h in [7,8]:
        risk_factors.append("Mars and Saturn both in 7th/8th — dual malefic influence on spouse longevity")
    if venus_h in [6,8,12]:
        risk_factors.append(f"Venus in house {venus_h} — spouse's wellbeing challenged")
    if sat_h == 8 and lord_7h in [6,12]:
        risk_factors.append("Saturn in 8th + 7th lord in dusthana — serious longevity concern")

    if _h("Jupiter",planets) in [7,8]:
        protection.append("Jupiter in 7th/8th — divine protection for spouse longevity")
    if venus_h in [1,4,7,11]:
        protection.append(f"Venus in house {venus_h} — spouse is healthy and supported")
    if lord_7h in [1,4,9,10,11]:
        protection.append(f"7th lord in house {lord_7h} — spouse flourishes in this relationship")

    risk = max(0, min(70, len(risk_factors)*18 - len(protection)*12))
    verdict = ("Spouse health requires active care and attention — apply Venus and 7th house remedies" if risk>=45
               else "Moderate caution for spouse wellbeing — annual health checkups for spouse" if risk>=25
               else "Spouse longevity indicators are generally positive")

    return {
        "risk_score": risk, "verdict": verdict,
        "risk_factors": risk_factors, "protection": protection,
        "remedy": "Venus remedy: Gift spouse white items Fridays. Never disrespect spouse. Jupiter: Donate yellow on Thursdays.",
        "sensitivity_note": "These are tendencies — karma can be modified through remedy and conscious care.",
    }


def engine_awards_recognition(planets, house_lords, yogas, divisional_charts):
    """Awards, honors, and official recognition."""
    sun_h   = _h("Sun", planets)
    jup_h   = _h("Jupiter", planets)
    rahu_h  = _h("Rahu", planets)
    sat_h   = _h("Saturn", planets)
    lord_10h= _h(_l(10,house_lords), planets) if _l(10,house_lords) else 0
    d10     = divisional_charts.get("d10",{})
    d10_sun = d10.get("planets",{}).get("Sun",{}).get("house",0) if d10 else 0

    indicators = []
    award_type = []

    if sun_h in [1,9,10,11]:
        indicators.append(f"Sun in house {sun_h} — natural authority, recognition by institutions")
        award_type.append("government/institutional honor")
    if jup_h in [1,9,10,11]:
        indicators.append(f"Jupiter in house {jup_h} — recognition for wisdom, teaching, public good")
        award_type.append("academic/wisdom award")
    if rahu_h in [10,11]:
        indicators.append(f"Rahu in house {rahu_h} — mass recognition, viral fame, unconventional award")
        award_type.append("mass media recognition")
    if any("Raj" in y.get("name","") for y in yogas):
        indicators.append("Raj Yoga — authority recognized by society, people follow this person")
        award_type.append("leadership recognition")
    if any("Amala" in y.get("name","") for y in yogas):
        indicators.append("Amala Yoga — spotless reputation, recognized for ethical conduct")
    if d10_sun in [1,10,11]:
        indicators.append(f"Sun in D10 house {d10_sun} — career chart confirms public recognition")
    if lord_10h in [1,9,10,11]:
        indicators.append(f"10th lord in house {lord_10h} — career peak triggers recognition")

    score = min(90, len(indicators)*16 + 10)
    timing = "During Sun or Jupiter Mahadasha/Antardasha — peak recognition periods"
    if rahu_h in [10,11]:
        timing = "Rahu MD (2026+) — mass recognition possible through unconventional achievement"

    return {
        "score": score,
        "verdict": ("High recognition potential — awards and honors are part of life path" if score>=65
                    else "Professional recognition in chosen field — respected not famous" if score>=40
                    else "Work is the reward — recognition comes quietly if at all"),
        "indicators": indicators,
        "award_types": list(set(award_type)),
        "timing": timing,
    }


def engine_vehicle_transport(planets, house_lords, divisional_charts):
    """Vehicle ownership and transport — 4th house, Venus, Mars."""
    lord_4  = _l(4, house_lords)
    lord_4h = _h(lord_4, planets) if lord_4 else 0
    venus_h = _h("Venus", planets)
    mars_h  = _h("Mars", planets)
    sat_h   = _h("Saturn", planets)
    rahu_h  = _h("Rahu", planets)

    positive  = []
    challenges= []

    if venus_h in [4,1,11,2]:
        positive.append(f"Venus in house {venus_h} — luxury vehicles, enjoys comfortable transport")
    if lord_4h in [1,2,9,10,11]:
        positive.append(f"4th lord {lord_4} in house {lord_4h} — vehicles are a natural possession")
    if mars_h in [4,11]:
        positive.append(f"Mars in house {mars_h} — multiple vehicles, fast/sporty vehicles")
    if rahu_h in [4]:
        positive.append("Rahu in 4th — foreign vehicles, unconventional transport, frequent change of vehicles")

    if sat_h == 4:
        challenges.append("Saturn in 4th — vehicle comes late in life, or old/second-hand vehicles first")
    if lord_4h in [6,8,12]:
        challenges.append(f"4th lord in house {lord_4h} — vehicle-related expenses or accidents possible")
    if mars_h in [6,8,12] and venus_h in [6,8,12]:
        challenges.append("Mars + Venus in difficult houses — vehicle accidents during their dashas")

    score = max(20, min(90, len(positive)*20 - len(challenges)*15 + 20))
    return {
        "score": score,
        "verdict": ("Multiple vehicles, luxury transport indicated" if score>=70
                    else "Vehicle ownership natural — standard quality" if score>=45
                    else "Vehicle comes with delay or has maintenance challenges"),
        "positive": positive, "challenges": challenges,
        "vehicle_type": "luxury/foreign" if venus_h in [1,4,11] and rahu_h in [4] else "standard/practical",
        "accident_caution": "Drive carefully during Mars and Saturn Antardasha" if challenges else "Generally safe",
    }


# ══════════════════════════════════════════════════════════════
# TIER 4 — SPECIAL VENUS / NEW HOUSE / NEW VEHICLE
# ══════════════════════════════════════════════════════════════

def engine_new_house_lk(planets, house_lords, birth_date, current_md_lord="", current_ad_lord=""):
    """
    Lal Kitab rules for new house/residence purchase.
    Specific combinations that indicate when new home happens.
    """
    lord_4  = _l(4, house_lords)
    lord_4h = _h(lord_4, planets) if lord_4 else 0
    mars_h  = _h("Mars", planets)
    moon_h  = _h("Moon", planets)
    venus_h = _h("Venus", planets)
    sat_h   = _h("Saturn", planets)
    jup_h   = _h("Jupiter", planets)
    rahu_h  = _h("Rahu", planets)
    age     = _age(birth_date)

    lk_indicators = []
    timing_signals = []
    challenges     = []

    # Lal Kitab positive indicators for new home
    if mars_h in [4,11]:
        lk_indicators.append(f"LK: Mars in house {mars_h} — property acquisition through effort, new home possible")
    if moon_h in [4]:
        lk_indicators.append("LK: Moon in 4th — home is emotional center, purchasing own home is natural")
    if venus_h in [4,11,2]:
        lk_indicators.append(f"LK: Venus in house {venus_h} — beautiful home, luxury residence indicated")
    if lord_4h in [1,4,9,11]:
        lk_indicators.append(f"LK: 4th lord {lord_4} in house {lord_4h} — home ownership strongly favored")
    if jup_h in [4,9,11]:
        lk_indicators.append(f"LK: Jupiter in house {jup_h} — divine blessing for home acquisition")
    if sat_h in [10,11]:
        lk_indicators.append(f"LK: Saturn in house {sat_h} — sustained effort rewards with property")
    if rahu_h in [4]:
        lk_indicators.append("LK: Rahu in 4th — foreign or unconventional home, apartment in different city/country")

    # Timing signals (dasha-based)
    if current_md_lord in ["Mars","Venus","Moon","Jupiter","Saturn"]:
        planet_house = _h(current_md_lord, planets)
        if planet_house in [4,11,2]:
            timing_signals.append(f"Current MD ({current_md_lord}) in house {planet_house} — active home-buying period")
    if current_ad_lord in ["Mars","Venus","Jupiter"]:
        planet_house = _h(current_ad_lord, planets)
        if planet_house in [4,9,11]:
            timing_signals.append(f"AD ({current_ad_lord}) in house {planet_house} — sub-period activates home purchase")

    # Lal Kitab challenges
    if mars_h in [6,7,12]:
        challenges.append(f"LK: Mars in house {mars_h} — property disputes possible, check legal titles")
    if sat_h == 4:
        challenges.append("LK: Saturn in 4th — home comes after 36 years of age typically, or second home")
    if lord_4h in [6,8,12]:
        challenges.append(f"LK: 4th lord {lord_4} in house {lord_4h} — legal or financial complications in home purchase")

    # Auspicious timing advice
    auspicious = []
    if not challenges:
        auspicious.append("Buy home during Jupiter transit over natal 4th house lord")
        auspicious.append("Avoid home purchase during Rahu or Saturn Antardasha if challenges present")
        auspicious.append("Best day for registration: Thursday (Jupiter) or Friday (Venus)")

    score = min(90, len(lk_indicators)*18 - len(challenges)*12 + 20)
    verdict = ("Strong home ownership yoga — property is natural for this chart" if score>=70
               else "Home possible — patience and right timing required" if score>=45
               else "Home comes after struggle — persistent effort and remedies needed")

    return {
        "score": score, "verdict": verdict,
        "lk_indicators": lk_indicators, "challenges": challenges,
        "timing_signals": timing_signals,
        "auspicious_advice": auspicious,
        "lk_remedy": "Mars remedy: Plant tulsi at home entrance. Moon: Keep water pot in NE direction. Venus: Keep white flowers at home.",
        "age_note": f"Age {age} — {'First home likely coming soon based on indicators' if age<40 and score>=60 else 'Right timing is key'}",
    }


def engine_new_vehicle_lk(planets, house_lords, current_md_lord="", current_ad_lord=""):
    """
    Lal Kitab rules for new vehicle purchase timing.
    """
    venus_h = _h("Venus", planets)
    mars_h  = _h("Mars", planets)
    rahu_h  = _h("Rahu", planets)
    moon_h  = _h("Moon", planets)
    sat_h   = _h("Saturn", planets)
    lord_4h = _h(_l(4, house_lords), planets) if _l(4, house_lords) else 0

    lk_signals = []
    cautions   = []

    # LK vehicle signals
    if venus_h in [1,4,11]:
        lk_signals.append(f"LK: Venus in house {venus_h} — vehicle comes naturally, luxury vehicle possible")
    if rahu_h in [4]:
        lk_signals.append("LK: Rahu in 4th — foreign vehicle, black/dark colored vehicle, frequent vehicle changes")
    if moon_h in [4,2]:
        lk_signals.append(f"LK: Moon in house {moon_h} — white vehicle, multiple vehicles, vehicle near water")
    if mars_h in [4,11]:
        lk_signals.append(f"LK: Mars in house {mars_h} — red vehicle, fast vehicle, property + vehicle together")

    # Best timing
    timing_note = ""
    if current_md_lord == "Venus" or current_ad_lord == "Venus":
        timing_note = "Venus period ACTIVE — excellent time for new vehicle purchase"
    elif current_md_lord == "Mars" or current_ad_lord == "Mars":
        timing_note = "Mars period — vehicle purchase possible, choose carefully (check 4th house Mars)"
    elif current_md_lord in ["Saturn","Rahu","Ketu"]:
        timing_note = "Current period is not ideal for vehicle purchase — wait for Venus or Jupiter period"

    # Cautions
    if mars_h in [6,8,12]:
        cautions.append(f"LK: Mars in house {mars_h} — accident risk with vehicles, drive carefully")
    if sat_h == 4:
        cautions.append("LK: Saturn in 4th — vehicle maintenance needed, older vehicles may cause issues")
    if rahu_h in [6,8,12]:
        cautions.append(f"LK: Rahu in house {rahu_h} — unexpected vehicle problems, insurance essential")

    # Auspicious purchase advice (Lal Kitab)
    lk_muhurta = [
        "Purchase on Friday (Venus day) for luxury/comfort vehicles",
        "Tuesday (Mars day) for commercial/work vehicles",
        "Avoid Saturday and Tuesday for new vehicle registration if Saturn/Mars in 4th",
        "Keep copper coin in new vehicle glove box (Lal Kitab remedy)",
        "Donate old clothes before taking delivery of new vehicle",
    ]

    return {
        "signals": lk_signals, "cautions": cautions,
        "timing_note": timing_note,
        "vehicle_color_lk": ("White" if moon_h==4 else "Red" if mars_h==4
                             else "Black/Dark" if rahu_h==4 else "Silver/Grey"),
        "lk_muhurta_advice": lk_muhurta[:3],
        "lk_remedy": "Venus remedy before vehicle purchase: Offer white flowers to Goddess Lakshmi on Friday.",
    }


# ══════════════════════════════════════════════════════════════
# WOW EFFECTS — Rare and powerful chart combinations
# ══════════════════════════════════════════════════════════════

def engine_wow_effects(chart_data, birth_date=""):
    """
    Detect rare and powerful astrological combinations.
    These are WOW moments — unexpected, profound, or extraordinary
    indicators that make this chart unique.
    """
    planets  = chart_data.get("planets", {})
    lagna    = chart_data.get("lagna", {})
    lagna_sign = lagna.get("sign","") if isinstance(lagna,dict) else str(lagna)
    lagna_idx  = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0
    house_lords= chart_data.get("house_lords",{})
    yogas      = chart_data.get("yogas",[])
    divs       = chart_data.get("divisional_charts",{})
    d9         = divs.get("d9",{})
    atmakaraka = chart_data.get("atmakaraka","")

    wow_effects = []

    # ── 1. VARGOTTAMA PLANETS ────────────────────────────────────
    # Planet in same sign in D1 and D9 — extremely powerful
    d9_planets = d9.get("planets",{})
    for planet, data in planets.items():
        d1_sign = data.get("sign","")
        d9_sign = d9_planets.get(planet,{}).get("sign","")
        if d1_sign and d9_sign and d1_sign == d9_sign:
            wow_effects.append({
                "name":        f"Vargottama {planet}",
                "category":    "extraordinary_strength",
                "description": f"{planet} is in {d1_sign} in BOTH D1 and D9 — this is Vargottama. The planet's strength is multiplied dramatically. What it signifies in your life will be exceptional, lasting, and deeply karmic.",
                "impact":      "This planet's life area delivers its promises fully and profoundly",
                "rarity":      "rare",
            })

    # ── 2. KALA SARPA YOGA ──────────────────────────────────────
    # All planets between Rahu and Ketu (one hemisphere)
    rahu_idx = SIGNS.index(_s("Rahu",planets)) if _s("Rahu",planets) in SIGNS else 0
    ketu_idx = SIGNS.index(_s("Ketu",planets)) if _s("Ketu",planets) in SIGNS else 0

    all_planets_between = True
    for planet in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]:
        p_sign = _s(planet, planets)
        if p_sign not in SIGNS:
            all_planets_between = False
            break
        p_idx = SIGNS.index(p_sign)
        # Check if between Rahu and Ketu (going forward from Rahu)
        steps = (p_idx - rahu_idx) % 12
        total = (ketu_idx - rahu_idx) % 12
        if not (0 <= steps <= total):
            all_planets_between = False
            break

    if all_planets_between:
        wow_effects.append({
            "name":        "Kala Sarpa Yoga",
            "category":    "karmic_intensity",
            "description": "ALL planets are between Rahu and Ketu — Kala Sarpa Yoga. This creates intense karmic acceleration. Life moves in dramatic waves — great highs and deep lows. Extraordinary achievement IS possible, but the path is never smooth. This chart is never ordinary.",
            "impact":      "Serpent of time — karmic debts from multiple lifetimes resolve in THIS life",
            "rarity":      "very_rare",
            "remedy":      "Naga Dosha puja at Trimbakeshwar or Kukke Subramanya. Offer milk to snake on Naga Panchami.",
        })

    # ── 3. GANDANTA DEGREES ──────────────────────────────────────
    # Last 3° of water signs or first 3° of fire signs = karmic knot
    GANDANTA_ZONES = [
        ("Pisces", 27, 30, "Pisces-Aries junction"),
        ("Cancer", 27, 30, "Cancer-Leo junction"),
        ("Scorpio",27, 30, "Scorpio-Sagittarius junction"),
        ("Aries",  0,  3,  "Pisces-Aries junction"),
        ("Leo",    0,  3,  "Cancer-Leo junction"),
        ("Sagittarius", 0, 3, "Scorpio-Sagittarius junction"),
    ]
    for planet, data in planets.items():
        p_sign = data.get("sign","")
        p_deg  = data.get("degree",0)
        for g_sign, g_start, g_end, g_name in GANDANTA_ZONES:
            if p_sign == g_sign and g_start <= p_deg <= g_end:
                wow_effects.append({
                    "name":        f"Gandanta {planet} ({g_name})",
                    "category":    "karmic_knot",
                    "description": f"{planet} is at {p_deg:.1f}° in {p_sign} — the Gandanta zone ({g_name}). This is a karmic knot point. The planet's significations carry deep past-life unresolved energy. Mastering this planet's domain is a core soul mission.",
                    "impact":      f"Profound karmic lessons around {planet}'s life themes — struggle leads to mastery",
                    "rarity":      "rare",
                    "remedy":      f"Jatakarma (birth remedies) for Gandanta {planet}. Specific puja for this planet's deity.",
                })

    # ── 4. PARIVARTANA YOGA (Sign Exchange) ──────────────────────
    # Two planets in each other's signs = mutual exchange of energy
    for p1, data1 in planets.items():
        for p2, data2 in planets.items():
            if p1 >= p2: continue
            sign1 = data1.get("sign","")
            sign2 = data2.get("sign","")
            # p1 in p2's sign AND p2 in p1's sign
            p1_owns = [s for s,l in SIGN_LORDS.items() if l==p1]
            p2_owns = [s for s,l in SIGN_LORDS.items() if l==p2]
            if sign1 in p2_owns and sign2 in p1_owns:
                h1 = data1.get("house",0)
                h2 = data2.get("house",0)
                wow_effects.append({
                    "name":        f"Parivartana Yoga ({p1}-{p2})",
                    "category":    "powerful_exchange",
                    "description": f"{p1} and {p2} are in each other's signs — Parivartana Yoga. They exchange houses {h1} and {h2}. Both planets become extremely powerful and their life areas are deeply interlinked. What happens in house {h1} always affects house {h2} and vice versa.",
                    "impact":      f"Houses {h1} and {h2} are merged in their destiny — success in one fuels the other",
                    "rarity":      "uncommon",
                })

    # ── 5. ATMAKARAKA IN OWN SIGN OR EXALTED ────────────────────
    if atmakaraka:
        ak_sign = _s(atmakaraka, planets)
        ak_own  = [s for s,l in SIGN_LORDS.items() if l==atmakaraka]
        if ak_sign == EXALTATION.get(atmakaraka):
            wow_effects.append({
                "name":        f"Exalted Atmakaraka ({atmakaraka})",
                "category":    "soul_strength",
                "description": f"The soul planet ({atmakaraka}) is EXALTED in {ak_sign}. This is extraordinary — the soul's core purpose is fully supported by the universe. Whatever this soul came to do, it has exceptional capacity to do it. Life may be difficult but the soul WILL fulfill its mission.",
                "impact":      "Soul strength is maximum — this person can achieve their deepest purpose",
                "rarity":      "rare",
            })
        elif ak_sign in ak_own:
            wow_effects.append({
                "name":        f"Atmakaraka ({atmakaraka}) in Own Sign",
                "category":    "soul_strength",
                "description": f"The soul planet ({atmakaraka}) is in its own sign ({ak_sign}). The soul is comfortable and powerful in its mission. Clear sense of purpose, strong self-knowledge, natural authority in soul's domain.",
                "impact":      "Soul is at home — purpose and action are naturally aligned",
                "rarity":      "uncommon",
            })

    # ── 6. GRAHAN YOGA (Eclipse Birth) ──────────────────────────
    sun_h  = _h("Sun", planets)
    moon_h = _h("Moon", planets)
    rahu_h = _h("Rahu", planets)
    ketu_h = _h("Ketu", planets)
    if sun_h == rahu_h or sun_h == ketu_h:
        node = "Rahu" if sun_h == rahu_h else "Ketu"
        wow_effects.append({
            "name":        f"Surya Grahan Yoga (Sun-{node})",
            "category":    "eclipse_birth",
            "description": f"Sun is conjunct {node} — Solar Eclipse energy in the birth chart. This gives unusual magnetic personality, strong public impact, and karmic life purpose. Father relationship may be complex. Authority and transformation are intertwined themes.",
            "impact":      "Eclipse-born — intense karmic personality, public magnetism, transformative life",
            "rarity":      "uncommon",
            "remedy":      f"Offer water to Sun at sunrise without fail. {node} remedy essential.",
        })
    if moon_h == rahu_h or moon_h == ketu_h:
        node = "Rahu" if moon_h == rahu_h else "Ketu"
        wow_effects.append({
            "name":        f"Chandra Grahan Yoga (Moon-{node})",
            "category":    "eclipse_birth",
            "description": f"Moon is conjunct {node} — Lunar Eclipse energy in the birth chart. This creates profound emotional intensity, psychic sensitivity, and complex relationship with mother and public. Mind works differently — often brilliantly, sometimes obsessively.",
            "impact":      "Eclipse mind — psychic depth, emotional intensity, complex inner world",
            "rarity":      "uncommon",
            "remedy":      f"Moon remedy: Offer milk to Shiva Mondays. {node} remedy essential. Meditation critical.",
        })

    # ── 7. ALL PLANETS IN ONE SIGN (STELLIUM) ───────────────────
    house_planet_count = {}
    for p, data in planets.items():
        h = data.get("house",0)
        house_planet_count[h] = house_planet_count.get(h,0) + 1

    for house, count in house_planet_count.items():
        if count >= 4:
            planets_here = [p for p,d in planets.items() if d.get("house")==house]
            from antar_engine.domain_engines import _house_meaning_simple
            meanings = {1:"self",2:"wealth",3:"courage",4:"home",5:"children",
                       6:"enemies",7:"marriage",8:"transformation",9:"dharma",
                       10:"career",11:"gains",12:"spirituality"}
            meaning = meanings.get(house, f"house {house}")
            wow_effects.append({
                "name":        f"Stellium in House {house} ({count} planets)",
                "category":    "concentrated_power",
                "description": f"{', '.join(planets_here)} are ALL in house {house} ({meaning}). This is a stellium — massive concentrated energy in one life area. This house's themes will dominate the entire life. Everything else revolves around {meaning}.",
                "impact":      f"House {house} ({meaning}) is the gravitational center of this life",
                "rarity":      "rare" if count >= 5 else "uncommon",
            })

    # ── 8. NEECHABHANGA RAJ YOGA ─────────────────────────────────
    for y in yogas:
        if "Neechabhanga" in y.get("name",""):
            wow_effects.append({
                "name":        y["name"],
                "category":    "cancellation_of_weakness",
                "description": f"A planet that appears weak (debilitated) has its weakness cancelled — creating Neechabhanga Raj Yoga. This is one of the most powerful Raj Yogas precisely BECAUSE it comes from apparent weakness. The very thing that seems like a limitation becomes the source of unusual strength and success.",
                "impact":      "Weakness transformed into exceptional strength — success through apparent limitation",
                "rarity":      "uncommon",
            })

    # ── 9. MULTIPLE RAJ YOGAS ───────────────────────────────────
    raj_yogas = [y for y in yogas if "Raj Yoga" in y.get("name","")]
    if len(raj_yogas) >= 2:
        wow_effects.append({
            "name":        f"Multiple Raj Yogas ({len(raj_yogas)} present)",
            "category":    "authority_chain",
            "description": f"This chart has {len(raj_yogas)} Raj Yogas simultaneously. Each Raj Yoga gives authority, recognition, and societal impact. Multiple Raj Yogas create a compounding effect — this person has the chart of someone who leads, builds institutions, and is remembered. The activation timing depends on dashas.",
            "impact":      "Leadership destiny — multiple authority combinations point to significant public role",
            "rarity":      "rare" if len(raj_yogas) >= 3 else "uncommon",
        })

    # ── 10. PUSHKARA NAVAMSA ────────────────────────────────────
    # Special degrees in D9 that amplify the planet
    PUSHKARA_DEGREES = {
        "Aries": [21], "Taurus": [14], "Gemini": [7], "Cancer": [21],
        "Leo": [14], "Virgo": [7,21], "Libra": [14], "Scorpio": [7],
        "Sagittarius": [21], "Capricorn": [14], "Aquarius": [7],
        "Pisces": [21],
    }
    for planet, data in planets.items():
        p_sign = data.get("sign","")
        p_deg  = round(data.get("degree",0))
        push_degs = PUSHKARA_DEGREES.get(p_sign,[])
        if any(abs(p_deg - pd) <= 1 for pd in push_degs):
            wow_effects.append({
                "name":        f"Pushkara Degree — {planet} at {data.get('degree',0):.1f}° {p_sign}",
                "category":    "auspicious_degree",
                "description": f"{planet} is at a Pushkara (auspicious amplification) degree — {data.get('degree',0):.1f}° in {p_sign}. This special degree doubles the planet's positive output. Whatever this planet promises, it delivers with unusual completeness.",
                "impact":      f"{planet}'s blessings are amplified — its life areas flourish beyond expectation",
                "rarity":      "uncommon",
            })

    # Sort by rarity
    rarity_order = {"very_rare":0,"rare":1,"uncommon":2,"notable":3}
    wow_effects.sort(key=lambda x: rarity_order.get(x.get("rarity","notable"),3))

    return {
        "wow_count":  len(wow_effects),
        "wow_effects": wow_effects,
        "has_extraordinary": any(e.get("rarity")=="very_rare" for e in wow_effects),
        "summary": (f"This chart has {len(wow_effects)} extraordinary combination(s). "
                    f"{'Including VERY RARE formations — this is an exceptional chart.' if any(e.get('rarity')=='very_rare' for e in wow_effects) else 'Notable rare combinations present.'}"),
    }


# ══════════════════════════════════════════════════════════════
# MASTER RUNNER — Tier 2/3/4
# ══════════════════════════════════════════════════════════════

TIER234_CONCERN_MAP = {
    "chronic":         "chronic",
    "long-term health":"chronic",
    "diabetes":        "chronic",
    "eye":             "eye",
    "vision":          "eye",
    "spectacles":      "eye",
    "partner":         "business_partner",
    "co-founder":      "business_partner",
    "bankrupt":        "bankruptcy",
    "financial loss":  "bankruptcy",
    "pilgrimage":      "pilgrimage",
    "temple":          "pilgrimage",
    "holy":            "pilgrimage",
    "parent":          "parent_loss",
    "widow":           "widowhood",
    "award":           "awards",
    "prize":           "awards",
    "car":             "vehicle",
    "vehicle":         "vehicle",
    "new house":       "new_house",
    "home buy":        "new_house",
    "property buy":    "new_house",
    "new car":         "new_vehicle",
    "buy vehicle":     "new_vehicle",
}


def run_tier234_engines(
    chart_data: dict,
    dashas: dict,
    birth_date: str,
    concern: str = "general",
    gender: str = "",
    current_md_lord: str = "",
    current_ad_lord: str = "",
    run_wow: bool = True,
) -> dict:
    planets    = chart_data.get("planets",{})
    house_lords= chart_data.get("house_lords",{})
    yogas      = chart_data.get("yogas",[])
    divs       = chart_data.get("divisional_charts",{})
    lagna      = chart_data.get("lagna",{})
    lagna_sign = lagna.get("sign","") if isinstance(lagna,dict) else str(lagna)

    concern_lower = concern.lower()
    matched = None
    for kw, eng in TIER234_CONCERN_MAP.items():
        if kw in concern_lower:
            matched = eng
            break

    results = {}

    # Always run WOW effects
    if run_wow:
        results["wow"] = engine_wow_effects(chart_data, birth_date)

    if matched == "chronic":
        results["chronic_disease"] = engine_chronic_disease(planets, house_lords, birth_date)
    elif matched == "eye":
        results["eye_problems"] = engine_eye_problems(planets, house_lords)
    elif matched == "business_partner":
        results["business_partnership"] = engine_business_partnership(planets, house_lords, yogas)
    elif matched == "bankruptcy":
        results["bankruptcy"] = engine_bankruptcy_risk(planets, house_lords, yogas)
    elif matched == "pilgrimage":
        results["pilgrimage"] = engine_pilgrimage(planets, house_lords, birth_date)
    elif matched == "parent_loss":
        results["parent_loss"] = engine_loss_of_parent(planets, house_lords, birth_date)
    elif matched == "widowhood":
        results["widowhood"] = engine_widowhood(planets, house_lords, divs, gender)
    elif matched == "awards":
        results["awards"] = engine_awards_recognition(planets, house_lords, yogas, divs)
    elif matched == "vehicle":
        results["vehicle"] = engine_vehicle_transport(planets, house_lords, divs)
    elif matched == "new_house":
        results["new_house"] = engine_new_house_lk(
            planets, house_lords, birth_date, current_md_lord, current_ad_lord)
    elif matched == "new_vehicle":
        results["new_vehicle"] = engine_new_vehicle_lk(
            planets, house_lords, current_md_lord, current_ad_lord)

    return results


def build_tier234_verdicts_block(results: dict) -> str:
    if not results:
        return ""

    lines = [
        "═══════════════════════════════════════════════════════",
        "TIER 2/3/4 + WOW EFFECTS (Python-calculated)",
        "═══════════════════════════════════════════════════════",
    ]

    # WOW effects first — they're the most powerful
    wow = results.get("wow",{})
    if wow and wow.get("wow_count",0) > 0:
        lines += ["", "⭐ WOW EFFECTS — EXTRAORDINARY CHART COMBINATIONS:"]
        lines.append(f"  {wow.get('summary','')} ")
        for effect in wow.get("wow_effects",[])[:5]:
            rarity = effect.get("rarity","")
            star = "⭐⭐" if rarity=="very_rare" else "⭐" if rarity=="rare" else "✦"
            lines.append(f"  {star} {effect['name']} [{rarity.upper()}]")
            lines.append(f"     {effect['description'][:120]}...")
            lines.append(f"     Impact: {effect['impact']}")
            if effect.get("remedy"):
                lines.append(f"     Remedy: {effect['remedy']}")

    LABELS = {
        "chronic_disease":    "CHRONIC DISEASE",
        "eye_problems":       "EYE HEALTH",
        "business_partnership":"BUSINESS PARTNERSHIP",
        "bankruptcy":         "BANKRUPTCY RISK",
        "pilgrimage":         "PILGRIMAGE / SACRED TRAVEL",
        "parent_loss":        "PARENT HEALTH",
        "widowhood":          "SPOUSE LONGEVITY",
        "awards":             "AWARDS / RECOGNITION",
        "vehicle":            "VEHICLE / TRANSPORT",
        "new_house":          "NEW HOUSE PURCHASE (Lal Kitab)",
        "new_vehicle":        "NEW VEHICLE (Lal Kitab)",
    }

    for engine, data in results.items():
        if engine == "wow" or not data:
            continue
        label = LABELS.get(engine, engine.upper())
        lines.append(f"\n{label}:")

        score_key = next((k for k in ["score","risk_score","partner_score"] if k in data),None)
        if score_key: lines.append(f"  Score/Risk: {data[score_key]}/100")
        if data.get("verdict"): lines.append(f"  Verdict: {data['verdict']}")

        for ind_key in ["lk_indicators","indicators","positive","gain_indicators","support_indicators"]:
            items = data.get(ind_key,[])
            if items:
                for i in items[:3]: lines.append(f"  ✓ {i}")
                break

        for warn_key in ["challenges","risk_factors","cautions","disputes"]:
            items = data.get(warn_key,[])
            if items:
                for i in items[:2]: lines.append(f"  ⚠ {i}")
                break

        for extra in ["timing_signals","timing","best_periods","award_types",
                      "vehicle_color_lk","lk_muhurta_advice","auspicious_advice",
                      "vehicle_type","recommended_type","age_note"]:
            if data.get(extra):
                val = data[extra]
                if isinstance(val,list): val = " | ".join(val[:2])
                lines.append(f"  → {extra.replace('_',' ').title()}: {val}")

        if data.get("lk_remedy") or data.get("remedy"):
            r = data.get("lk_remedy") or data.get("remedy")
            lines.append(f"  LK Remedy: {r}")

    lines += [
        "",
        "INSTRUCTION: WOW effects are RARE combinations — mention them prominently.",
        "They make this chart unique. Explain why they matter for this person.",
        "═══════════════════════════════════════════════════════",
    ]
    return "\n".join(lines)
