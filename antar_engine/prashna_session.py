"""
antar_engine/prashna_session.py

Prashna Session System
======================
One Prashna session = one chart cast at question time.
Follow-up questions reuse the same chart — analyzed from different angles.

Session flow:
  Q1: "Will I get this job?"        → cast chart, store session
  Q2: "Which company?"              → reuse chart, compare planets
  Q3: "Will salary be good?"        → reuse chart, analyze 2nd/11th
  Q4: "When exactly?"               → reuse chart, degree-based timing
"""

from datetime import datetime
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
BENEFICS = ["Jupiter","Venus","Moon","Mercury"]
MALEFICS  = ["Saturn","Mars","Sun","Rahu","Ketu"]
KENDRA    = [1, 4, 7, 10]
TRIKONA   = [1, 5, 9]
DUSTHANA  = [6, 8, 12]


# ── Follow-up question type detection ────────────────────────────

FOLLOWUP_PATTERNS = {
    "which_option": [
        "which","or","option","better","prefer","choose","vs",
        "startup vs","company vs","a or b","this or that"
    ],
    "timing_exact": [
        "when exactly","how long","how many","this month","next month",
        "this year","how soon","days","weeks","months"
    ],
    "salary_money": [
        "salary","pay","compensation","money","package","ctc",
        "how much","income","earn"
    ],
    "location": [
        "where","city","country","location","place","abroad","remote"
    ],
    "person": [
        "who","person","partner","colleague","boss","manager","founder"
    ],
    "should_i": [
        "should i","what should","what do i","how should","approach",
        "strategy","how to"
    ],
    "will_it_last": [
        "last","stable","long term","permanent","sustainable","future",
        "grow","expand"
    ],
    "more_detail": [
        "tell me more","explain","why","what does","clarify","elaborate",
        "what about","and what"
    ],
}

def detect_followup_type(question: str) -> str:
    """Detect what angle the follow-up question is asking about."""
    q_lower = question.lower()
    scores  = {}
    for ftype, keywords in FOLLOWUP_PATTERNS.items():
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > 0:
            scores[ftype] = score
    if not scores:
        return "more_detail"
    return max(scores, key=scores.get)


# ── Follow-up analysis functions ─────────────────────────────────

def analyze_which_option(
    prashna_chart: dict,
    question: str,
    original_verdict: dict,
) -> dict:
    """
    "Which option" follow-up — compare two paths using planetary strength.
    
    Logic:
    - Identify the two options from the question
    - Map each to a planetary karaka
    - Stronger planet = recommended option
    - Sun/Mars/government = established path
    - Mercury/Rahu/startup = unconventional path
    - Venus = creative/beautiful option
    - Saturn = slow/disciplined option
    - Jupiter = wise/educational option
    """
    planets = prashna_chart.get("planets", {})
    q_lower = question.lower()

    OPTIONS_MAP = {
        "startup":    ("Mercury","Rahu",  "unconventional, fast-growth, risky"),
        "mnc":        ("Saturn", "Sun",   "structured, stable, slower growth"),
        "corporate":  ("Saturn", "Sun",   "structured, hierarchical, steady"),
        "government": ("Sun",    "Saturn","authority, security, slow"),
        "freelance":  ("Mercury","Rahu",  "independent, variable income"),
        "abroad":     ("Rahu",   "Moon",  "foreign, unfamiliar, transformative"),
        "stay":       ("Saturn", "Moon",  "stable, familiar, grounded"),
        "now":        ("Mars",   "Rahu",  "immediate action, impatient"),
        "wait":       ("Saturn", "Jupiter","patient, strategic, better timing"),
        "partner":    ("Venus",  "Jupiter","collaborative, shared"),
        "solo":       ("Sun",    "Mars",  "independent, self-reliant"),
    }

    # Find which options are mentioned
    found_options = {}
    for option, (planet1, planet2, desc) in OPTIONS_MAP.items():
        if option in q_lower:
            # Score this option by its planetary strength
            p1_house = planets.get(planet1, {}).get("house", 0)
            p2_house = planets.get(planet2, {}).get("house", 0)
            p1_score = 20 if p1_house in KENDRA else 15 if p1_house in TRIKONA else 5 if p1_house in DUSTHANA else 10
            p2_score = 20 if p2_house in KENDRA else 15 if p2_house in TRIKONA else 5 if p2_house in DUSTHANA else 10
            found_options[option] = {
                "score":  p1_score + p2_score,
                "planets": [planet1, planet2],
                "desc":   desc,
            }

    if len(found_options) >= 2:
        sorted_options = sorted(found_options.items(), key=lambda x: x[1]["score"], reverse=True)
        winner = sorted_options[0]
        loser  = sorted_options[1] if len(sorted_options) > 1 else None

        return {
            "followup_type": "which_option",
            "recommendation": winner[0].title(),
            "score":          winner[1]["score"],
            "reasoning":      f"{winner[0].title()} ({winner[1]['desc']}) is supported by stronger planetary positions at this moment",
            "caution":        f"{loser[0].title()} faces weaker planetary support right now" if loser else "",
            "verdict":        f"GO WITH {winner[0].upper()} — the chart at this moment favors it",
        }

    # Generic comparison using benefic/malefic balance
    benefic_houses = [planets.get(p,{}).get("house",0) for p in BENEFICS]
    benefic_in_good = sum(1 for h in benefic_houses if h in KENDRA + TRIKONA)

    return {
        "followup_type": "which_option",
        "recommendation": "The more structured/established option",
        "reasoning":      f"With {benefic_in_good} benefic planets in strong positions, stability is favored over risk",
        "verdict":        "Choose the path that aligns with your current dasha lord's energy",
    }


def analyze_exact_timing(prashna_chart: dict, original_verdict: dict) -> dict:
    """
    Timing follow-up — convert planetary degrees to time units.
    
    Classical rule:
    - Moon's degrees to next aspect = time units
    - Movable sign Moon = days
    - Fixed sign Moon = months  
    - Dual sign Moon = weeks
    - Each degree = 1 time unit
    """
    planets   = prashna_chart.get("planets", {})
    moon_sign = planets.get("Moon", {}).get("sign", "")
    moon_deg  = planets.get("Moon", {}).get("degree", 0)

    MOVABLE = ["Aries","Cancer","Libra","Capricorn"]
    FIXED   = ["Taurus","Leo","Scorpio","Aquarius"]
    DUAL    = ["Gemini","Virgo","Sagittarius","Pisces"]

    # Degrees remaining in current sign
    degrees_remaining = 30 - moon_deg

    if moon_sign in MOVABLE:
        unit = "days"
        estimate = f"{int(degrees_remaining)} to {int(degrees_remaining) + 7} days"
    elif moon_sign in FIXED:
        unit = "months"
        estimate = f"{max(1, int(degrees_remaining/5))} to {int(degrees_remaining/3)} months"
    else:
        unit = "weeks"
        estimate = f"{max(1, int(degrees_remaining/4))} to {int(degrees_remaining/2)} weeks"

    # Refine by score
    score = original_verdict.get("score", 50)
    if score >= 70:
        prefix = "Soon —"
    elif score >= 50:
        prefix = "After some effort —"
    else:
        prefix = "If conditions improve —"

    return {
        "followup_type": "timing_exact",
        "estimate":      f"{prefix} approximately {estimate}",
        "moon_unit":     unit,
        "moon_sign":     moon_sign,
        "degrees_left":  round(degrees_remaining, 1),
        "verdict":       f"Moon in {moon_sign} (remaining {round(degrees_remaining,1)}°) suggests {estimate}",
    }


def analyze_financial_aspect(prashna_chart: dict, original_q_type: str) -> dict:
    """Salary/money follow-up — analyze 2nd and 11th house."""
    planets  = prashna_chart.get("planets", {})
    lagna    = prashna_chart.get("lagna", {})
    lagna_sign = lagna.get("sign","Aries")
    lagna_idx  = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0

    # 2nd house (wealth/salary) and 11th (gains)
    planets_in_2 = [p for p,d in planets.items() if d.get("house")==2]
    planets_in_11= [p for p,d in planets.items() if d.get("house")==11]

    jup_h  = planets.get("Jupiter",{}).get("house",0)
    ven_h  = planets.get("Venus",{}).get("house",0)
    sat_h  = planets.get("Saturn",{}).get("house",0)
    rahu_h = planets.get("Rahu",{}).get("house",0)

    wealth_score = 0
    signals = []

    if jup_h in [2,5,9,11]:
        wealth_score += 25
        signals.append(f"Jupiter in house {jup_h} — financial expansion supported")
    if ven_h in [2,11]:
        wealth_score += 20
        signals.append(f"Venus in house {ven_h} — material gains flow easily")
    if rahu_h == 11:
        wealth_score += 20
        signals.append("Rahu in 11th — unconventional but significant income gains")
    if any(p in BENEFICS for p in planets_in_11):
        wealth_score += 15
        signals.append(f"Benefic in 11th house — gains are supported")
    if sat_h in [2,11]:
        signals.append(f"Saturn in house {sat_h} — income comes but slowly and steadily")
        wealth_score += 10

    if wealth_score >= 50:
        verdict = "YES — financial aspect looks favorable. Compensation should be satisfying."
    elif wealth_score >= 30:
        verdict = "MODERATE — some financial benefit but may need negotiation."
    else:
        verdict = "LOWER THAN EXPECTED — the financial terms may disappoint. Negotiate hard."

    return {
        "followup_type": "salary_money",
        "wealth_score":  wealth_score,
        "verdict":       verdict,
        "signals":       signals[:3],
    }


def analyze_should_i(prashna_chart: dict, question: str, original_verdict: dict) -> dict:
    """Strategy/approach follow-up — how to improve odds."""
    planets  = prashna_chart.get("planets", {})
    score    = original_verdict.get("score", 50)

    # Which planet is strongest in the chart right now?
    planet_scores = {}
    for planet, data in planets.items():
        house = data.get("house", 0)
        if house in KENDRA:    planet_scores[planet] = 3
        elif house in TRIKONA: planet_scores[planet] = 2
        elif house in DUSTHANA:planet_scores[planet] = 0
        else:                  planet_scores[planet] = 1

    if planet_scores:
        strongest = max(planet_scores, key=planet_scores.get)
    else:
        strongest = "Jupiter"

    STRATEGY_BY_PLANET = {
        "Sun":     "Lead with authority and confidence. Don't undersell yourself. Be direct.",
        "Moon":    "Appeal to emotions and relationships. Build personal connection first.",
        "Mars":    "Act decisively and quickly. Don't overthink. Move fast.",
        "Mercury": "Communicate clearly in writing. Follow up systematically. Use data.",
        "Jupiter": "Be generous and principled. Trust the process. Expand your network.",
        "Venus":   "Make it beautiful and harmonious. Be charming. Build relationships.",
        "Saturn":  "Be patient and persistent. Show discipline. Play the long game.",
        "Rahu":    "Be unconventional. Think outside the box. Use technology and networks.",
        "Ketu":    "Be detached from outcome. Focus on the work, not the result.",
    }

    strategy = STRATEGY_BY_PLANET.get(strongest, "Follow your strongest instinct.")

    if score >= 60:
        approach = "The chart supports action. Move forward with:"
    else:
        approach = "The chart suggests patience first. When you do move:"

    return {
        "followup_type": "should_i",
        "strongest_planet": strongest,
        "strategy":        strategy,
        "verdict":         f"{approach} {strategy}",
        "timing_note":     "Best window: when the planetary hour matches your strongest planet",
    }


# ── Session manager ───────────────────────────────────────────────

def analyze_prashna_followup(
    session: dict,
    followup_question: str,
) -> dict:
    """
    Analyze a follow-up question using the SAME Prashna chart.
    No new chart cast — same chart, different analytical angle.
    """
    prashna_chart    = session.get("prashna_chart", {})
    original_verdict = session.get("analysis", {})
    original_q_type  = session.get("question_type", "career")
    original_question= session.get("question", "")

    followup_type = detect_followup_type(followup_question)

    if followup_type == "which_option":
        result = analyze_which_option(prashna_chart, followup_question, original_verdict)
    elif followup_type == "timing_exact":
        result = analyze_exact_timing(prashna_chart, original_verdict)
    elif followup_type == "salary_money":
        result = analyze_financial_aspect(prashna_chart, original_q_type)
    elif followup_type == "should_i":
        result = analyze_should_i(prashna_chart, followup_question, original_verdict)
    else:
        # Generic — refer back to original analysis with elaboration
        result = {
            "followup_type": "more_detail",
            "verdict":       f"On the matter of '{original_question}': {original_verdict.get('explanation','')}",
            "elaboration":   f"The chart cast at the moment of your original question continues to guide this aspect.",
            "key_factor":    original_verdict.get("yes_factors",[""])[0] if original_verdict.get("yes_factors") else "",
        }

    result["reuses_chart_from"] = session.get("asked_at","")
    result["followup_question"] = followup_question

    # Build LLM prompt for this follow-up
    result["llm_prompt"] = _build_followup_prompt(
        original_question=original_question,
        followup_question=followup_question,
        original_verdict=original_verdict,
        followup_analysis=result,
        prashna_chart=prashna_chart,
    )

    return result


def _build_followup_prompt(
    original_question: str,
    followup_question: str,
    original_verdict: dict,
    followup_analysis: dict,
    prashna_chart: dict,
) -> str:
    moon_nak  = prashna_chart.get("moon_nakshatra","")
    moon_qual = prashna_chart.get("moon_nak_quality","")
    orig_score= original_verdict.get("score", 50)
    orig_verd = original_verdict.get("verdict","")

    return f"""You are Antar answering a FOLLOW-UP Prashna question.
The SAME chart (cast at original question time) is being used.

ORIGINAL QUESTION: "{original_question}"
ORIGINAL VERDICT: {orig_verd} (score: {orig_score}/100)

FOLLOW-UP QUESTION: "{followup_question}"
FOLLOW-UP TYPE: {followup_analysis.get('followup_type','')}
FOLLOW-UP ANALYSIS: {followup_analysis.get('verdict','')}

Moon at time of question: {moon_nak} ({moon_qual})
Chart reused from: {followup_analysis.get('reuses_chart_from','')}

RULES:
- Reference the ORIGINAL question and verdict first
- Answer the follow-up specifically
- Never use Sanskrit terms
- Plain psychological language only
- Under 150 words
- End with one concrete action

Respond:
**On your follow-up:**
[Direct answer to the follow-up question]

**Reading from the same chart:**
[1-2 sentences connecting chart to this specific angle]

**Do this:**
[One concrete action based on this follow-up analysis]"""


def create_prashna_session(prashna_result: dict) -> dict:
    """Create a session object from initial Prashna result."""
    import uuid
    return {
        "session_id":    str(uuid.uuid4()),
        "created_at":    datetime.utcnow().isoformat(),
        "question":      prashna_result.get("question",""),
        "question_type": prashna_result.get("question_type",""),
        "asked_at":      prashna_result.get("asked_at",""),
        "prashna_chart": prashna_result.get("prashna_chart",{}),
        "analysis":      prashna_result.get("analysis",{}),
        "verdict":       prashna_result.get("verdict",""),
        "score":         prashna_result.get("score",50),
        "conversation":  [
            {
                "role":     "user",
                "content":  prashna_result.get("question",""),
                "type":     "initial",
            },
            {
                "role":     "antar",
                "content":  prashna_result.get("verdict",""),
                "analysis": prashna_result.get("analysis",{}),
                "type":     "initial_verdict",
            }
        ],
    }
