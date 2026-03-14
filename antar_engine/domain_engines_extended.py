"""
antar_engine/domain_engines_extended.py

Extended domain engines — 25+ life areas.
Python calculates verdict. LLM narrates.

Covers:
  Children/progeny, divorce/separation, foreign settlement,
  job vs business, property, education, legal cases, jail yoga,
  hospital visits, accidents, addiction, mental health, anxiety,
  affairs/girlfriend, startup funding, loan repayment,
  father, mother, siblings, spirituality/moksha, debt
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
EXALTATION = {
    "Sun":"Aries","Moon":"Taurus","Mars":"Capricorn","Mercury":"Virgo",
    "Jupiter":"Cancer","Venus":"Pisces","Saturn":"Libra"
}
DEBILITATION = {
    "Sun":"Libra","Moon":"Scorpio","Mars":"Cancer","Mercury":"Pisces",
    "Jupiter":"Capricorn","Venus":"Virgo","Saturn":"Aries"
}
BENEFICS = ["Jupiter","Venus","Moon","Mercury"]
MALEFICS  = ["Saturn","Mars","Sun","Rahu","Ketu"]

def _house(planet, planets): return planets.get(planet,{}).get("house",0)
def _sign(planet, planets):  return planets.get(planet,{}).get("sign","")
def _lord(h, house_lords):
    if not isinstance(house_lords,dict): return ""
    return house_lords.get(h,{}).get("lord","")
def _age(birth_date):
    try: return (date.today()-date.fromisoformat(birth_date[:10])).days//365
    except: return 35


# ── CHILDREN / PROGENY ──────────────────────────────────────────
def engine_children(planets, house_lords, divisional_charts, birth_date, gender=""):
    d7 = divisional_charts.get("d7",{})
    lord_5  = _lord(5, house_lords)
    lord_5h = _house(lord_5, planets) if lord_5 else 0
    jup_h   = _house("Jupiter", planets)
    jup_sign= _sign("Jupiter", planets)
    d7_lagna= d7.get("lagna","")
    d7_jup  = d7.get("planets",{}).get("Jupiter",{}).get("house",0)
    age     = _age(birth_date)

    signals = []
    warnings = []

    # Jupiter strong = children blessed
    if jup_h in [1,2,4,5,9,11]:
        signals.append(f"Jupiter in house {jup_h} — children are blessed and bring joy")
    if jup_sign == EXALTATION.get("Jupiter"):
        signals.append("Jupiter exalted — exceptional children, highly accomplished")

    # 5th house analysis
    planets_in_5 = [p for p,d in planets.items() if d.get("house")==5]
    if "Jupiter" in planets_in_5:
        signals.append("Jupiter in 5th — first child brings wisdom and blessings")
    if "Venus" in planets_in_5:
        signals.append("Venus in 5th — creative, beautiful children")
    if "Saturn" in planets_in_5:
        warnings.append("Saturn in 5th — delayed children, karmic relationship with children, possible adoption")
    if "Ketu" in planets_in_5:
        warnings.append("Ketu in 5th — difficulties with conception, children may be spiritually inclined, adoption possible")
    if "Rahu" in planets_in_5:
        warnings.append("Rahu in 5th — unconventional children or child-related karma, IVF/adoption possible")
    if "Mars" in planets_in_5 and "Jupiter" not in planets_in_5:
        warnings.append("Mars in 5th without Jupiter — miscarriage risk, aggressive children, son more likely")

    # 5th lord in dusthana
    if lord_5 and lord_5h in [6,8,12]:
        warnings.append(f"5th lord {lord_5} in house {lord_5h} — children require extra effort, possible delays")

    # D7 chart
    if d7_lagna:
        signals.append(f"D7 lagna {d7_lagna} — children chart activated")
    if d7_jup in [1,5,9]:
        signals.append(f"Jupiter in D7 house {d7_jup} — children blessed in soul chart")

    score = max(20, min(95, 60 + len(signals)*10 - len(warnings)*15))
    verdict = "Blessed with children" if score>=70 else "Children possible with effort" if score>=45 else "Significant challenges — consult specialist"

    # Timing
    timing = "25-35 for first child typically" if age < 25 else "Depends on current dasha activation"
    if "Saturn" in planets_in_5 or (lord_5 and lord_5h in [6,8,12]):
        timing = "After 30 more likely — Saturn indicates delay not denial"

    return {
        "score": score, "verdict": verdict, "timing": timing,
        "signals": signals, "warnings": warnings,
        "lord_5": lord_5, "lord_5_house": lord_5h,
        "planets_in_5": planets_in_5, "d7_lagna": d7_lagna,
    }


# ── DIVORCE / SEPARATION ────────────────────────────────────────
def engine_divorce(planets, house_lords, divisional_charts):
    d9 = divisional_charts.get("d9",{})
    lord_7  = _lord(7, house_lords)
    lord_7h = _house(lord_7, planets) if lord_7 else 0
    venus_h = _house("Venus", planets)
    mars_h  = _house("Mars", planets)
    rahu_h  = _house("Rahu", planets)
    d9_venus= d9.get("planets",{}).get("Venus",{}).get("house",0)
    d9_mars = d9.get("planets",{}).get("Mars",{}).get("house",0)

    risk_factors  = []
    stable_factors= []

    # High-risk indicators
    if lord_7h in [6,8,12]:
        risk_factors.append(f"7th lord {lord_7} in house {lord_7h} — major marriage stress, separation possible")
    if mars_h == 7:
        risk_factors.append("Mars in 7th — conflict-driven relationship, Manglik consideration")
    if rahu_h == 7:
        risk_factors.append("Rahu in 7th — unconventional marriage, karmic partnership, possible foreign spouse or separation")
    if _house("Saturn", planets) == 7:
        risk_factors.append("Saturn in 7th — delayed marriage, serious/older spouse, OR karmic burden in marriage")
    if d9_mars in [6,8,12]:
        risk_factors.append(f"Mars in D9 house {d9_mars} — soul-level conflict in marriage")
    if d9_venus in [6,8,12]:
        risk_factors.append(f"Venus in D9 house {d9_venus} — soul-level dissatisfaction in partnership")

    # Stable indicators
    if _house("Jupiter", planets) == 7:
        stable_factors.append("Jupiter in 7th — blessed marriage, wise spouse, stability")
    if venus_h in [1,2,4,7,11]:
        stable_factors.append(f"Venus in house {venus_h} — relationship harmony")
    if lord_7h in [1,4,5,9,11]:
        stable_factors.append(f"7th lord in house {lord_7h} — favorable for marriage")

    risk_score = len(risk_factors) * 20
    divorce_risk = min(risk_score, 90)

    if divorce_risk >= 60:
        verdict = "High divorce risk — multiple stress indicators present. Remedies strongly recommended."
    elif divorce_risk >= 35:
        verdict = "Moderate marriage stress — relationship requires conscious effort and communication"
    else:
        verdict = "Marriage generally stable — normal relationship challenges expected"

    return {
        "divorce_risk_score": divorce_risk,
        "verdict": verdict,
        "risk_factors": risk_factors,
        "stable_factors": stable_factors,
        "lord_7": lord_7, "lord_7_house": lord_7h,
    }


# ── FOREIGN SETTLEMENT ──────────────────────────────────────────
def engine_foreign(planets, house_lords, lagna_sign, divisional_charts):
    lord_12 = _lord(12, house_lords)
    lord_9  = _lord(9, house_lords)
    lord_12h= _house(lord_12, planets) if lord_12 else 0
    lord_9h = _house(lord_9, planets) if lord_9 else 0
    rahu_h  = _house("Rahu", planets)
    ketu_h  = _house("Ketu", planets)
    saturn_h= _house("Saturn", planets)
    moon_h  = _house("Moon", planets)
    d9      = divisional_charts.get("d9",{})

    FOREIGN_SIGNS = ["Gemini","Virgo","Sagittarius","Pisces","Aquarius","Capricorn"]
    rahu_sign = _sign("Rahu", planets)
    moon_sign = _sign("Moon", planets)

    indicators = []
    strong = []

    if rahu_h in [1,7,9,12]:
        strong.append(f"Rahu in house {rahu_h} — foreign connection strong, possible settlement abroad")
    if lord_12h in [1,7,9,10,12]:
        strong.append(f"12th lord {lord_12} in house {lord_12h} — foreign lands activated")
    if moon_h == 12:
        indicators.append("Moon in 12th — emotional connection to foreign lands, possible settlement")
    if moon_sign in FOREIGN_SIGNS:
        indicators.append(f"Moon in {moon_sign} — dual/foreign nature in mind")
    if saturn_h in [9,12]:
        indicators.append(f"Saturn in house {saturn_h} — long-term foreign work or residence")
    if rahu_sign in FOREIGN_SIGNS:
        indicators.append(f"Rahu in {rahu_sign} — foreign ambitions, unconventional path abroad")
    if lord_9h == 12 or lord_12h == 9:
        strong.append("9th-12th house exchange — strong foreign destiny indicator")
    if ketu_h == 12:
        indicators.append("Ketu in 12th — past life foreign connection, spiritual journey abroad")

    score = min(95, len(strong)*25 + len(indicators)*10)
    if score >= 70:
        verdict = "Strong foreign settlement indicators — abroad is likely part of life path"
    elif score >= 40:
        verdict = "Foreign travel and work likely — permanent settlement depends on choice and timing"
    else:
        verdict = "Home country more favorable — foreign connections present but not dominant"

    return {
        "score": score, "verdict": verdict,
        "strong_indicators": strong, "indicators": indicators,
        "rahu_house": rahu_h, "rahu_sign": rahu_sign,
        "lord_12": lord_12, "lord_12_house": lord_12h,
    }


# ── JOB VS BUSINESS ─────────────────────────────────────────────
def engine_job_vs_business(planets, house_lords, yogas):
    lord_6  = _lord(6, house_lords)   # service/job
    lord_7  = _lord(7, house_lords)   # business/partnerships
    lord_10 = _lord(10, house_lords)  # career authority
    lord_6h = _house(lord_6, planets) if lord_6 else 0
    lord_7h = _house(lord_7, planets) if lord_7 else 0

    merc_h = _house("Mercury", planets)
    jup_h  = _house("Jupiter", planets)
    sun_h  = _house("Sun", planets)
    sat_h  = _house("Saturn", planets)
    rahu_h = _house("Rahu", planets)

    job_score  = 0
    biz_score  = 0
    job_reasons  = []
    biz_reasons  = []

    # Job indicators
    if sun_h in [6,10]:
        job_score += 20; job_reasons.append(f"Sun in house {sun_h} — government/corporate job favored")
    if sat_h == 6:
        job_score += 20; job_reasons.append("Saturn in 6th — service-oriented career, disciplined employee")
    if lord_6h in [1,10]:
        job_score += 15; job_reasons.append(f"6th lord in {lord_6h} — service/employment dominant")
    if merc_h == 6:
        job_score += 10; job_reasons.append("Mercury in 6th — analytical service work")

    # Business indicators
    if merc_h in [7,11]:
        biz_score += 25; biz_reasons.append(f"Mercury in house {merc_h} — business communication and trade")
    if rahu_h in [7,10,11]:
        biz_score += 20; biz_reasons.append(f"Rahu in house {rahu_h} — unconventional business, startup energy")
    if jup_h in [7,11]:
        biz_score += 20; biz_reasons.append(f"Jupiter in house {jup_h} — business expansion and wisdom")
    if lord_7h in [1,10,11]:
        biz_score += 20; biz_reasons.append(f"7th lord in house {lord_7h} — partnership/business dominant")
    if any("Raj" in y.get("name","") for y in yogas):
        biz_score += 15; biz_reasons.append("Raj Yoga — leadership and authority, own venture favored")

    total = job_score + biz_score
    if total == 0:
        verdict = "Both paths viable — timing and choice determine outcome"
    elif biz_score > job_score * 1.5:
        verdict = f"Business strongly favored (business {biz_score} vs job {job_score}) — entrepreneurial chart"
    elif job_score > biz_score * 1.5:
        verdict = f"Employment/service favored (job {job_score} vs business {biz_score}) — career in organization"
    else:
        verdict = "Both viable — business partnerships better than solo venture"

    return {
        "job_score": job_score, "business_score": biz_score,
        "verdict": verdict,
        "job_reasons": job_reasons, "business_reasons": biz_reasons,
        "recommendation": "business" if biz_score > job_score else "job",
    }


# ── MENTAL HEALTH / ANXIETY ─────────────────────────────────────
def engine_mental_health(planets, house_lords, current_md_lord="", current_ad_lord=""):
    moon_h    = _house("Moon", planets)
    moon_sign = _sign("Moon", planets)
    mercury_h = _house("Mercury", planets)
    rahu_h    = _house("Rahu", planets)
    saturn_h  = _house("Saturn", planets)
    lord_4    = _lord(4, house_lords)
    lord_4h   = _house(lord_4, planets) if lord_4 else 0

    risk_factors = []
    strengths    = []

    # Moon affliction = primary mental health indicator
    if moon_h in [6,8,12]:
        risk_factors.append(f"Moon in house {moon_h} — emotional vulnerability, depression/anxiety risk")
    if moon_sign == DEBILITATION.get("Moon"):
        risk_factors.append("Moon debilitated in Scorpio — deep emotional struggles, transformation through pain")
    if rahu_h == 4:
        risk_factors.append("Rahu in 4th — restlessness, anxiety, mind never fully at peace, foreign obsessions")
    if rahu_h == 1:
        risk_factors.append("Rahu in 1st — identity confusion, obsessive thoughts, anxiety about self")
    if saturn_h in [1,4]:
        risk_factors.append(f"Saturn in house {saturn_h} — depression tendency, chronic low mood, heavy thoughts")
    if mercury_h in [6,8,12]:
        risk_factors.append(f"Mercury in house {mercury_h} — nervous system vulnerability, overthinking, anxiety")

    # Current dasha lords affecting mental health
    if current_md_lord in ["Rahu","Saturn","Ketu"]:
        risk_factors.append(f"Current MD lord {current_md_lord} — this period activates mental/emotional themes")
    if current_ad_lord in ["Rahu","Saturn","Ketu"] and current_ad_lord != current_md_lord:
        risk_factors.append(f"Current AD lord {current_ad_lord} — sub-period adds mental pressure")

    # Strengths
    if _house("Jupiter", planets) in [1,4,5,9]:
        strengths.append("Jupiter aspecting mind areas — wisdom and optimism protect mental health")
    if moon_h in [2,4,10,11]:
        strengths.append(f"Moon in house {moon_h} — emotional stability and public connection")
    if mercury_h in [1,4,10,11]:
        strengths.append(f"Mercury in house {mercury_h} — clear thinking and communication")

    risk_score = min(90, len(risk_factors) * 18)
    if risk_score >= 60:
        verdict = "Significant mental health indicators — proactive care and spiritual practice essential"
    elif risk_score >= 35:
        verdict = "Moderate emotional sensitivity — stress management and routine important"
    else:
        verdict = "Generally stable mind — emotional resilience present"

    remedies = []
    if moon_h in [6,8,12] or moon_sign == "Scorpio":
        remedies.append("Moon remedy: Offer milk to Shiva on Mondays. Keep silver. Meditate near water.")
    if rahu_h in [1,4]:
        remedies.append("Rahu remedy: Feed crows daily. Meditate morning. Keep elephant figurine.")
    if current_md_lord == "Rahu":
        remedies.append("During Rahu period: Avoid overthinking. Physical exercise critical. Spiritual anchor essential.")

    return {
        "risk_score": risk_score, "verdict": verdict,
        "risk_factors": risk_factors, "strengths": strengths,
        "remedies": remedies,
        "moon_house": moon_h, "moon_sign": moon_sign,
    }


# ── AFFAIRS / GIRLFRIEND / SECRET RELATIONSHIPS ─────────────────
def engine_affairs(planets, house_lords, gender=""):
    lord_5  = _lord(5, house_lords)   # love affairs
    lord_12 = _lord(12, house_lords)  # secret/bedroom
    lord_7  = _lord(7, house_lords)   # marriage
    venus_h = _house("Venus", planets)
    rahu_h  = _house("Rahu", planets)
    mars_h  = _house("Mars", planets)
    moon_h  = _house("Moon", planets)
    lord_5h = _house(lord_5, planets) if lord_5 else 0
    lord_12h= _house(lord_12, planets) if lord_12 else 0

    indicators = []
    warnings   = []

    # Strong romantic indicators
    if venus_h in [1,5,7,11]:
        indicators.append(f"Venus in house {venus_h} — strong romantic nature, love life prominent")
    if _house("Venus", planets) == 5:
        indicators.append("Venus in 5th — love affairs, romantic creativity, passionate relationships")
    if rahu_h in [5,7,12]:
        indicators.append(f"Rahu in house {rahu_h} — unconventional or secret romantic connections")
    if lord_5h == 12 or lord_12h == 5:
        indicators.append("5th-12th exchange — secret love affairs, bedroom matters with romantic partners")
    if mars_h in [5,7,8,12]:
        indicators.append(f"Mars in house {mars_h} — passionate, physical relationships")

    # Secret relationship indicators
    if _house("Venus", planets) == 12:
        warnings.append("Venus in 12th — secret relationships, bedroom pleasures, possible affairs after marriage")
    if rahu_h == 5:
        warnings.append("Rahu in 5th — karmic love connections, obsessive attractions, unconventional romance")
    if lord_7h == 12:
        warnings.append("7th lord in 12th — marriage partner may have secret life, or marriage goes to bed/separation")

    return {
        "romantic_strength": len(indicators) * 20,
        "affair_risk": len(warnings) * 25,
        "indicators": indicators,
        "warnings": warnings,
        "venus_house": venus_h,
        "verdict": "Active romantic life — multiple relationship connections possible" if len(indicators) >= 3
                   else "Normal romantic life" if len(indicators) >= 1
                   else "Reserved in romantic matters",
    }


# ── STARTUP FUNDING ─────────────────────────────────────────────
def engine_startup_funding(planets, house_lords, yogas, dashas, birth_date):
    lord_11 = _lord(11, house_lords)  # investors/gains
    lord_2  = _lord(2, house_lords)   # own capital
    lord_9  = _lord(9, house_lords)   # fortune/luck in funding
    rahu_h  = _house("Rahu", planets)
    jup_h   = _house("Jupiter", planets)
    merc_h  = _house("Mercury", planets)
    sun_h   = _house("Sun", planets)
    lord_11h= _house(lord_11, planets) if lord_11 else 0
    lord_9h = _house(lord_9, planets) if lord_9 else 0

    positive = []
    challenges = []

    # Investor indicators
    if lord_11h in [1,5,9,10,11]:
        positive.append(f"11th lord {lord_11} in house {lord_11h} — investors and gains strongly supported")
    if rahu_h in [10,11]:
        positive.append(f"Rahu in house {rahu_h} — foreign investors, VC funding, unconventional capital sources")
    if jup_h in [2,5,9,11]:
        positive.append(f"Jupiter in house {jup_h} — institutional money, ethical investors, expansion capital")
    if merc_h in [7,11]:
        positive.append(f"Mercury in house {merc_h} — business deals, partnership capital, network funding")
    if any("Dhana" in y.get("name","") for y in yogas):
        positive.append("Dhana Yoga present — wealth accumulation yoga supports funding rounds")
    if sun_h in [9,10,11]:
        positive.append(f"Sun in house {sun_h} — government grants, authority backing, institutional credibility")

    if lord_9h in [6,8,12]:
        challenges.append(f"9th lord {lord_9} in house {lord_9h} — luck in funding is tested, multiple rounds needed")
    if _house("Saturn", planets) in [2,11]:
        positive.append("Saturn in wealth houses — slow but institutional, patient capital (PE not VC)")

    # Best timing window
    timing_windows = []
    now = datetime.utcnow()
    for row in dashas.get("vimsottari",[]):
        lord  = row.get("lord_or_sign") or row.get("planet_or_sign","")
        level = row.get("level") or row.get("type","")
        if lord not in ["Jupiter","Rahu","Sun","Venus","Mercury"] or level!="mahadasha":
            continue
        try:
            sd = datetime.strptime(str(row.get("start_date",""))[:10],"%Y-%m-%d")
            ed = datetime.strptime(str(row.get("end_date",""))[:10],"%Y-%m-%d")
            if ed > now:
                timing_windows.append(f"{lord} MD {sd.year}-{ed.year}")
        except: pass

    score = min(95, len(positive)*18 - len(challenges)*10 + 30)
    verdict = ("Strong funding chart — multiple investor indicators present" if score>=70
               else "Moderate funding potential — good story but timing matters" if score>=45
               else "Challenging funding environment — bootstrap or patient capital recommended")

    return {
        "score": score, "verdict": verdict,
        "positive_indicators": positive, "challenges": challenges,
        "best_timing": timing_windows[:2],
        "recommended_type": "VC/Foreign" if rahu_h in [10,11] else "Institutional/Angel" if jup_h in [2,11] else "Bootstrap first",
    }


# ── LOAN REPAYMENT ──────────────────────────────────────────────
def engine_loan(planets, house_lords):
    lord_6  = _lord(6, house_lords)   # debt house
    lord_8  = _lord(8, house_lords)   # borrowed money
    lord_12 = _lord(12, house_lords)  # expenditure
    lord_6h = _house(lord_6, planets) if lord_6 else 0
    lord_8h = _house(lord_8, planets) if lord_8 else 0
    sat_h   = _house("Saturn", planets)
    rahu_h  = _house("Rahu", planets)
    mars_h  = _house("Mars", planets)

    debt_indicators  = []
    repay_indicators = []

    # Debt accumulation
    if rahu_h in [6,8,12]:
        debt_indicators.append(f"Rahu in house {rahu_h} — foreign loans, credit card debt, hidden liabilities")
    if sat_h == 6:
        debt_indicators.append("Saturn in 6th — service-related debt, employee loans, structured debt")
    if mars_h == 6:
        debt_indicators.append("Mars in 6th — sudden debt from disputes or property")
    if lord_6h in [1,8,12]:
        debt_indicators.append(f"6th lord in house {lord_6h} — debt is a recurring theme in life")

    # Repayment strength
    if _house("Jupiter", planets) in [2,6,11]:
        repay_indicators.append(f"Jupiter in house {_house('Jupiter',planets)} — ability to repay through wisdom and expansion")
    if _house("Saturn", planets) in [11]:
        repay_indicators.append("Saturn in 11th — slow but certain gains clear debts over time")
    if lord_8h in [2,11]:
        repay_indicators.append(f"8th lord in house {lord_8h} — borrowed money can be repaid through gains")

    debt_score = min(80, len(debt_indicators)*20)
    repay_score = min(80, len(repay_indicators)*25 + 20)

    if repay_score > debt_score:
        verdict = "Good repayment ability — income sources support debt clearance"
    elif debt_score > repay_score:
        verdict = "Debt accumulation tendency — active management and Saturn remedy needed"
    else:
        verdict = "Debt comes but can be managed — discipline is key"

    return {
        "debt_score": debt_score, "repay_score": repay_score,
        "verdict": verdict,
        "debt_indicators": debt_indicators,
        "repay_indicators": repay_indicators,
        "remedy": "Saturn remedy: Serve poor on Saturdays. Keep accounts clean. Avoid new loans during Saturn AD.",
    }


# ── LEGAL CASES / COURT ─────────────────────────────────────────
def engine_legal(planets, house_lords, current_md_lord=""):
    lord_6  = _lord(6, house_lords)   # enemies/litigation
    lord_7  = _lord(7, house_lords)   # contracts/legal
    lord_6h = _house(lord_6, planets) if lord_6 else 0
    mars_h  = _house("Mars", planets)
    rahu_h  = _house("Rahu", planets)
    sat_h   = _house("Saturn", planets)

    risk    = []
    win_ind = []

    if mars_h in [6,7,12]:
        risk.append(f"Mars in house {mars_h} — disputes, aggression leading to legal action")
    if rahu_h in [6,7]:
        risk.append(f"Rahu in house {rahu_h} — foreign legal matters, unconventional disputes, government issues")
    if lord_6h in [7,10,12]:
        risk.append(f"6th lord in house {lord_6h} — enemies reach courts or public forums")
    if sat_h in [6,7]:
        risk.append(f"Saturn in house {sat_h} — chronic legal battles, property disputes, labor issues")
    if current_md_lord in ["Mars","Rahu","Saturn"]:
        risk.append(f"Current {current_md_lord} dasha — legal matters more likely in this period")

    # Winning indicators
    if sat_h == 6:
        win_ind.append("Saturn in 6th — defeats enemies through patience, wins in court")
    if _house("Sun", planets) in [6,10]:
        win_ind.append("Sun in 6/10 — government/authority supports in legal matters")
    if _house("Jupiter", planets) in [6,9,10]:
        win_ind.append("Jupiter in legal houses — dharma supports, ethical victories")

    risk_score = min(85, len(risk)*20)
    win_score  = min(85, len(win_ind)*25 + 15)

    verdict = ("High legal risk — multiple dispute indicators. Apply Mars/Saturn remedies urgently." if risk_score >= 60
               else "Moderate legal exposure — be careful with contracts and agreements" if risk_score >= 35
               else "Low legal risk — natural caution protects from disputes")

    return {
        "risk_score": risk_score, "win_score": win_score,
        "verdict": verdict, "risk_factors": risk,
        "winning_indicators": win_ind,
        "remedy": "Mars remedy: Donate blood. Visit Hanuman temple Tuesdays. Saturn remedy: Serve poor Saturdays.",
    }


# ── JAIL / IMPRISONMENT YOGA ────────────────────────────────────
def engine_jail_yoga(planets, house_lords):
    lord_12 = _lord(12, house_lords)
    lord_8  = _lord(8, house_lords)
    lord_12h= _house(lord_12, planets) if lord_12 else 0
    lord_8h = _house(lord_8, planets) if lord_8 else 0
    sat_h   = _house("Saturn", planets)
    rahu_h  = _house("Rahu", planets)
    mars_h  = _house("Mars", planets)
    sun_h   = _house("Sun", planets)

    indicators = []
    protective = []

    # Classical jail yogas
    if sat_h == 12 and rahu_h in [1,6,8]:
        indicators.append("Saturn in 12th + Rahu in angular/dusthana — confinement yoga (jail or hospital)")
    if mars_h in [6,8,12] and rahu_h in [6,8,12]:
        indicators.append("Mars + Rahu both in dusthana — criminal or confinement risk if activated together")
    if lord_12h in [6,8] and lord_8h == 12:
        indicators.append("8th-12th exchange with malefics — hidden enemies and confinement link")
    if sun_h in [6,8,12] and sat_h in [6,8,12]:
        indicators.append("Sun + Saturn both in dusthana — authority issues, government conflict")

    # Protective
    if _house("Jupiter", planets) in [1,5,9]:
        protective.append("Jupiter in trikona — dharma protection from extreme outcomes")
    if _house("Jupiter", planets) in [6,9]:
        protective.append("Jupiter in 6/9 — legal and dharmic protection")

    risk = len(indicators) * 20
    if risk == 0:
        verdict = "No jail yoga indicators in chart"
    elif risk <= 20:
        verdict = "Minor confinement possibility — hospitalization more likely than jail. Avoid legal gray areas."
    elif risk <= 40:
        verdict = "Moderate risk — stay strictly legal. Avoid associations with criminal elements during Rahu/Saturn periods."
    else:
        verdict = "Significant confinement yoga — legal, ethical, and karmic discipline essential. Apply remedies."

    return {
        "risk_score": risk, "verdict": verdict,
        "indicators": indicators, "protective_factors": protective,
        "note": "Jail yoga indicates potential for any confinement — hospital, isolation, or legal detention. Context depends on overall chart.",
    }


# ── HOSPITAL / SURGERY RISK ─────────────────────────────────────
def engine_hospital(planets, house_lords, current_md_lord="", current_ad_lord=""):
    lord_6  = _lord(6, house_lords)
    lord_8  = _lord(8, house_lords)
    lord_12 = _lord(12, house_lords)
    sat_h   = _house("Saturn", planets)
    mars_h  = _house("Mars", planets)
    rahu_h  = _house("Rahu", planets)
    sun_h   = _house("Sun", planets)
    lord_6h = _house(lord_6, planets) if lord_6 else 0

    indicators = []

    if mars_h in [1,6,8]:
        indicators.append(f"Mars in house {mars_h} — surgery or accident risk, inflammation")
    if sat_h in [6,8,12]:
        indicators.append(f"Saturn in house {sat_h} — chronic illness, long hospital stays possible")
    if rahu_h in [6,8]:
        indicators.append(f"Rahu in house {rahu_h} — unusual diseases, foreign medical issues")
    if lord_6h == 8 or _house(lord_8, planets) == 6:
        indicators.append("6th-8th exchange — disease leading to surgery or serious medical events")
    if current_md_lord in ["Mars","Saturn","Rahu","Ketu","Sun"]:
        indicators.append(f"Current {current_md_lord} dasha — health events more likely this period")
    if current_ad_lord in ["Mars","Saturn","Rahu","Ketu"]:
        indicators.append(f"Current AD {current_ad_lord} — short health challenges possible")

    risk = min(85, len(indicators)*18)
    verdict = ("High hospital/surgery risk — preventive health care essential" if risk>=55
               else "Moderate health events possible — annual checkups important" if risk>=30
               else "Low hospital risk — general health maintenance sufficient")

    return {
        "risk_score": risk, "verdict": verdict,
        "indicators": indicators,
        "recommendation": "Annual full health checkup. Mars remedy: Hanuman worship. Saturn: Serve poor Saturdays.",
    }


# ── ACCIDENTS ───────────────────────────────────────────────────
def engine_accidents(planets, house_lords, current_md_lord=""):
    mars_h  = _house("Mars", planets)
    rahu_h  = _house("Rahu", planets)
    sat_h   = _house("Saturn", planets)
    lord_8  = _lord(8, house_lords)
    lord_8h = _house(lord_8, planets) if lord_8 else 0

    indicators = []

    if mars_h in [1,6,8,12]:
        indicators.append(f"Mars in house {mars_h} — accident and injury risk, head/blood/surgery")
    if rahu_h in [1,6,8]:
        indicators.append(f"Rahu in house {rahu_h} — sudden/unexpected accidents, foreign incidents")
    if lord_8h in [1,6,8]:
        indicators.append(f"8th lord in house {lord_8h} — 8th house themes (accidents) activated")
    if sat_h in [1,8] and mars_h in [6,8,12]:
        indicators.append("Saturn + Mars in difficult houses — serious accident risk during their periods")
    if current_md_lord in ["Mars","Rahu","Ketu"]:
        indicators.append(f"Current {current_md_lord} dasha — accident caution needed in this period")

    risk = min(80, len(indicators)*20)
    verdict = ("High accident risk — drive carefully, avoid risky activities, apply Mars remedy" if risk>=60
               else "Moderate caution advised — especially during Mars/Rahu periods" if risk>=35
               else "Normal accident risk — standard caution sufficient")

    return {
        "risk_score": risk, "verdict": verdict,
        "indicators": indicators,
        "remedy": "Mars: Pray to Hanuman on Tuesdays. Avoid confrontations. Wear coral if Mars is strong.",
        "caution_periods": f"Most risky during {current_md_lord} MD" if current_md_lord in ["Mars","Rahu"] else "Standard caution",
    }


# ── ADDICTION ───────────────────────────────────────────────────
def engine_addiction(planets, house_lords, current_md_lord=""):
    moon_h   = _house("Moon", planets)
    venus_h  = _house("Venus", planets)
    rahu_h   = _house("Rahu", planets)
    ketu_h   = _house("Ketu", planets)
    sat_h    = _house("Saturn", planets)
    moon_sign= _sign("Moon", planets)

    indicators = []

    # Rahu aspects Moon = primary addiction indicator
    if abs(rahu_h - moon_h) in [0,5,7]:
        indicators.append("Rahu influencing Moon — addictive tendencies, obsessive patterns, substance risk")
    if rahu_h in [1,4,5,12]:
        indicators.append(f"Rahu in house {rahu_h} — addictive personality traits, obsession patterns")
    if moon_h in [6,8,12]:
        indicators.append(f"Moon in house {moon_h} — emotional emptiness seeking external filling")
    if moon_sign == "Scorpio":
        indicators.append("Moon in Scorpio — emotional intensity can drive addictive coping")
    if venus_h in [6,8,12]:
        indicators.append(f"Venus in house {venus_h} — pleasure-seeking leads to excess")
    if sat_h in [1,4] and rahu_h in [4,12]:
        indicators.append("Saturn + Rahu in depression-prone houses — substance use as escape risk")
    if current_md_lord == "Rahu":
        indicators.append("Rahu Mahadasha active — 18-year period of obsessive patterns, addictive risk heightened")

    risk = min(80, len(indicators)*18)
    verdict = ("High addiction risk — spiritual grounding and professional support essential" if risk>=55
               else "Moderate addiction vulnerability — healthy routines and awareness important" if risk>=30
               else "Low addiction risk — generally balanced relationship with pleasures")

    return {
        "risk_score": risk, "verdict": verdict, "indicators": indicators,
        "remedy": "Moon remedy: Meditate near water. Fast Mondays. Rahu remedy: Feed crows. Morning meditation.",
        "note": "Addiction yoga indicates potential — free will and environment matter greatly.",
    }


# ── PROPERTY / REAL ESTATE ──────────────────────────────────────
def engine_property(planets, house_lords, yogas, dashas, birth_date):
    lord_4  = _lord(4, house_lords)
    lord_4h = _house(lord_4, planets) if lord_4 else 0
    mars_h  = _house("Mars", planets)
    moon_h  = _house("Moon", planets)
    sat_h   = _house("Saturn", planets)
    venus_h = _house("Venus", planets)

    indicators = []
    challenges  = []

    if lord_4h in [1,2,4,9,10,11]:
        indicators.append(f"4th lord {lord_4} in house {lord_4h} — property ownership strongly favored")
    if mars_h in [4,11]:
        indicators.append(f"Mars in house {mars_h} — property acquisition through effort and action")
    if mars_h == 4 and _house("Jupiter", planets) in [4,9,11]:
        indicators.append("Mars + Jupiter influencing 4th — multiple properties possible")
    if sat_h in [4,10]:
        indicators.append(f"Saturn in house {sat_h} — property through sustained effort, inherited property")
    if venus_h in [4,11]:
        indicators.append(f"Venus in house {venus_h} — beautiful property, luxury real estate")
    if moon_h == 4:
        indicators.append("Moon in 4th — home is emotional sanctuary, multiple moves or large home")

    if lord_4h in [6,8,12]:
        challenges.append(f"4th lord in house {lord_4h} — property disputes or losses during 4th lord's dasha")
    if mars_h in [6,7,8]:
        challenges.append(f"Mars in house {mars_h} — property disputes, legal battles over property")

    score = min(90, len(indicators)*18 - len(challenges)*12 + 25)
    verdict = ("Strong property yoga — real estate is a natural wealth vehicle" if score>=70
               else "Moderate property potential — property possible with planning" if score>=45
               else "Property requires extra effort — disputes or delays likely")

    return {
        "score": score, "verdict": verdict,
        "indicators": indicators, "challenges": challenges,
        "lord_4": lord_4, "lord_4_house": lord_4h, "mars_house": mars_h,
    }


# ── EDUCATION / HIGHER STUDIES ──────────────────────────────────
def engine_education(planets, house_lords, divisional_charts):
    lord_4  = _lord(4, house_lords)   # education foundation
    lord_5  = _lord(5, house_lords)   # intelligence
    lord_9  = _lord(9, house_lords)   # higher education
    lord_4h = _house(lord_4, planets) if lord_4 else 0
    lord_5h = _house(lord_5, planets) if lord_5 else 0
    lord_9h = _house(lord_9, planets) if lord_9 else 0
    merc_h  = _house("Mercury", planets)
    jup_h   = _house("Jupiter", planets)

    indicators = []
    challenges  = []

    if merc_h in [1,4,5,9,10]:
        indicators.append(f"Mercury in house {merc_h} — sharp intellect, academic excellence")
    if jup_h in [1,2,4,5,9]:
        indicators.append(f"Jupiter in house {jup_h} — higher learning, teaching ability, philosophical depth")
    if lord_5h in [1,9,10,11]:
        indicators.append(f"5th lord {lord_5} in house {lord_5h} — intelligence applied to achievement")
    if lord_9h in [1,5,10,11]:
        indicators.append(f"9th lord {lord_9} in house {lord_9h} — higher education favorable, foreign study possible")

    if lord_4h in [6,8,12]:
        challenges.append(f"4th lord in house {lord_4h} — educational interruptions possible")
    if merc_h in [6,8,12]:
        challenges.append(f"Mercury in house {merc_h} — nervous system affects learning, alternative learning styles")
    if _house("Saturn", planets) in [4,5]:
        challenges.append("Saturn in 4/5 — delayed but deep learning, studies through struggle lead to mastery")

    score = min(92, len(indicators)*18 - len(challenges)*10 + 30)
    verdict = ("Exceptional educational potential — academic or research career natural" if score>=75
               else "Good education — consistent effort yields strong results" if score>=50
               else "Education possible with extra support — alternative paths valid")

    return {
        "score": score, "verdict": verdict,
        "indicators": indicators, "challenges": challenges,
        "foreign_education": _house("Rahu", planets) in [4,5,9,12] or lord_9h == 12,
    }


# ── SPIRITUALITY / MOKSHA ───────────────────────────────────────
def engine_spirituality(planets, house_lords):
    ketu_h  = _house("Ketu", planets)
    sat_h   = _house("Saturn", planets)
    jup_h   = _house("Jupiter", planets)
    moon_h  = _house("Moon", planets)
    lord_12 = _lord(12, house_lords)
    lord_9  = _lord(9, house_lords)
    lord_12h= _house(lord_12, planets) if lord_12 else 0

    indicators = []

    if ketu_h in [1,4,8,9,12]:
        indicators.append(f"Ketu in house {ketu_h} — strong spiritual pull, past-life spiritual practice")
    if sat_h in [8,12]:
        indicators.append(f"Saturn in house {sat_h} — spiritual depth through renunciation and discipline")
    if jup_h in [9,12]:
        indicators.append(f"Jupiter in house {jup_h} — dharmic wisdom, teacher energy, philosophical life")
    if moon_h == 12:
        indicators.append("Moon in 12th — spiritual liberation, emotional transcendence")
    if lord_12h in [1,9,10]:
        indicators.append(f"12th lord in house {lord_12h} — moksha themes prominent in life purpose")

    score = min(90, len(indicators)*20)
    verdict = ("Strong spiritual path — this chart carries moksha yoga" if score>=60
               else "Spiritual interests present — practice deepens over time" if score>=35
               else "Worldly orientation — spirituality comes later in life typically")

    return {
        "score": score, "verdict": verdict, "indicators": indicators,
        "ketu_house": ketu_h, "note": "Spirituality develops most during Ketu and Saturn dashas",
    }


# ══════════════════════════════════════════════════════════════
# MASTER RUNNER — extended domains
# ══════════════════════════════════════════════════════════════

CONCERN_TO_ENGINE = {
    "children":    "children",
    "progeny":     "children",
    "baby":        "children",
    "divorce":     "divorce",
    "separation":  "divorce",
    "affair":      "affairs",
    "girlfriend":  "affairs",
    "love affair": "affairs",
    "foreign":     "foreign",
    "abroad":      "foreign",
    "immigration": "foreign",
    "job":         "job_vs_business",
    "business":    "job_vs_business",
    "startup":     "startup_funding",
    "funding":     "startup_funding",
    "investor":    "startup_funding",
    "loan":        "loan",
    "debt":        "loan",
    "legal":       "legal",
    "court":       "legal",
    "case":        "legal",
    "jail":        "jail",
    "arrest":      "jail",
    "hospital":    "hospital",
    "surgery":     "hospital",
    "accident":    "accidents",
    "addiction":   "addiction",
    "alcohol":     "addiction",
    "mental":      "mental_health",
    "anxiety":     "mental_health",
    "depression":  "mental_health",
    "property":    "property",
    "real estate": "property",
    "house":       "property",
    "education":   "education",
    "study":       "education",
    "spiritual":   "spirituality",
    "moksha":      "spirituality",
}


def run_extended_engines(
    chart_data: dict,
    dashas: dict,
    birth_date: str,
    concern: str = "general",
    current_md_lord: str = "",
    current_ad_lord: str = "",
    gender: str = "",
) -> dict:
    """Run relevant extended domain engines based on concern."""
    planets    = chart_data.get("planets", {})
    lagna      = chart_data.get("lagna", {})
    lagna_sign = lagna.get("sign","") if isinstance(lagna, dict) else str(lagna)
    house_lords= chart_data.get("house_lords", {})
    yogas      = chart_data.get("yogas", [])
    divs       = chart_data.get("divisional_charts", {})

    concern_lower = concern.lower()
    matched_engine = None
    for keyword, engine_name in CONCERN_TO_ENGINE.items():
        if keyword in concern_lower:
            matched_engine = engine_name
            break

    results = {}

    # Always run these for every prediction
    results["mental_health"] = engine_mental_health(
        planets, house_lords, current_md_lord, current_ad_lord)
    results["accidents"]     = engine_accidents(planets, house_lords, current_md_lord)

    # Run concern-specific engine
    if matched_engine == "children":
        results["children"] = engine_children(planets, house_lords, divs, birth_date, gender)
    elif matched_engine == "divorce":
        results["divorce"]  = engine_divorce(planets, house_lords, divs)
    elif matched_engine == "affairs":
        results["affairs"]  = engine_affairs(planets, house_lords, gender)
    elif matched_engine == "foreign":
        results["foreign"]  = engine_foreign(planets, house_lords, lagna_sign, divs)
    elif matched_engine == "job_vs_business":
        results["job_vs_business"] = engine_job_vs_business(planets, house_lords, yogas)
    elif matched_engine == "startup_funding":
        results["startup_funding"] = engine_startup_funding(
            planets, house_lords, yogas, dashas, birth_date)
    elif matched_engine == "loan":
        results["loan"] = engine_loan(planets, house_lords)
    elif matched_engine == "legal":
        results["legal"] = engine_legal(planets, house_lords, current_md_lord)
    elif matched_engine == "jail":
        results["jail"]  = engine_jail_yoga(planets, house_lords)
    elif matched_engine == "hospital":
        results["hospital"] = engine_hospital(
            planets, house_lords, current_md_lord, current_ad_lord)
    elif matched_engine == "addiction":
        results["addiction"] = engine_addiction(planets, house_lords, current_md_lord)
    elif matched_engine == "property":
        results["property"] = engine_property(planets, house_lords, yogas, dashas, birth_date)
    elif matched_engine == "education":
        results["education"] = engine_education(planets, house_lords, divs)
    elif matched_engine == "spirituality":
        results["spirituality"] = engine_spirituality(planets, house_lords)
    elif matched_engine == "mental_health":
        pass  # already run above

    return results


def build_extended_verdicts_block(extended_results: dict) -> str:
    """Format extended engine results for LLM context."""
    if not extended_results:
        return ""

    lines = [
        "═══════════════════════════════════════════════════════",
        "EXTENDED DOMAIN ENGINE VERDICTS (Python-calculated facts)",
        "═══════════════════════════════════════════════════════",
    ]

    ENGINE_LABELS = {
        "mental_health":  "MENTAL HEALTH",
        "accidents":      "ACCIDENT RISK",
        "children":       "CHILDREN / PROGENY",
        "divorce":        "DIVORCE / SEPARATION RISK",
        "affairs":        "ROMANTIC / AFFAIR INDICATORS",
        "foreign":        "FOREIGN SETTLEMENT",
        "job_vs_business":"JOB VS BUSINESS",
        "startup_funding":"STARTUP FUNDING",
        "loan":           "LOAN / DEBT",
        "legal":          "LEGAL CASES",
        "jail":           "CONFINEMENT / JAIL YOGA",
        "hospital":       "HOSPITAL / SURGERY",
        "addiction":      "ADDICTION RISK",
        "property":       "PROPERTY / REAL ESTATE",
        "education":      "EDUCATION",
        "spirituality":   "SPIRITUALITY / MOKSHA",
    }

    for engine, data in extended_results.items():
        if not data:
            continue
        label = ENGINE_LABELS.get(engine, engine.upper())
        lines.append(f"\n{label}:")

        # Score
        score_key = next((k for k in ["score","risk_score","divorce_risk_score",
                          "romantic_strength","job_score","business_score"] if k in data), None)
        if score_key:
            lines.append(f"  Score: {data[score_key]}/100")

        # Verdict
        if data.get("verdict"):
            lines.append(f"  Verdict: {data['verdict']}")

        # Key indicators (max 3)
        for ind_key in ["indicators","signals","positive_indicators","risk_factors","strong_indicators"]:
            items = data.get(ind_key, [])
            if items:
                for item in items[:3]:
                    lines.append(f"  ✓ {item}")
                break

        # Warnings (max 2)
        for warn_key in ["warnings","challenges","risk_factors","debt_indicators"]:
            items = data.get(warn_key, [])
            if items:
                for item in items[:2]:
                    lines.append(f"  ⚠ {item}")
                break

        # Remedy
        if data.get("remedy"):
            lines.append(f"  Remedy: {data['remedy']}")

        # Special fields
        if engine == "foreign" and data.get("verdict"):
            lines.append(f"  Rahu in house: {data.get('rahu_house','?')}")
        if engine == "job_vs_business":
            lines.append(f"  Recommendation: {data.get('recommendation','').upper()}")
        if engine == "startup_funding":
            lines.append(f"  Best timing: {', '.join(data.get('best_timing',[]))}")
            lines.append(f"  Recommended type: {data.get('recommended_type','')}")
        if engine == "children" and data.get("timing"):
            lines.append(f"  Timing: {data['timing']}")

    lines += [
        "\nINSTRUCTION: Use these pre-calculated verdicts as facts.",
        "Explain what they mean. Do not change the scores.",
        "Always mention remedies when risk scores are above 40.",
        "═══════════════════════════════════════════════════════",
    ]
    return "\n".join(lines)
