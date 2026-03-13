"""
antar_engine/life_question_engine.py

Master Orchestrator — Any Life Question
──────────────────────────────────────────────────────────────────────
THIS IS THE ONE FUNCTION TO CALL FOR ANY LIFE QUESTION.

call build_life_question_context() and it:
  1. Routes the question to the right domain
  2. Calculates the right D-charts (real-time, < 50ms)
  3. Runs yoga detection
  4. Finds timing windows from stored dashas
  5. Selects remedies
  6. Assembles one complete context block for the LLM

The LLM then takes this context + the user's question and
generates the human narrative.

USAGE in main.py predict endpoint:

    from antar_engine.life_question_engine import (
        build_life_question_context,
        QUESTION_KEYWORDS,
    )

    # After detecting concern:
    life_context = build_life_question_context(
        question=request.question,
        chart_data=chart_data,
        dashas=dashas_response,
        patra=patra,
    )

    # Inject into prompt:
    prompt = build_predict_prompt(
        ...
        life_question_context=life_context,
        ...
    )

NOTHING IS SAVED TO DB.
All divisional charts are calculated real-time.
Only chart_data + dasha_periods (already in DB) are needed.
"""

from __future__ import annotations

from antar_engine.d_charts_calculator import (
    get_d_chart, get_all_d_charts, get_house_lord,
    SIGN_INDEX, SIGNS, SIGN_LORDS,
)
from antar_engine.yoga_engine import detect_yogas_for_question
from antar_engine.timing_engine_v2 import get_timing_windows, build_timing_context
from antar_engine.remedy_engine import select_remedies, remedies_to_context_block


# ── Question → Domain → Charts map ───────────────────────────────────────────

QUESTION_KEYWORDS = {
    "billionaire": ["billionaire","crore","million","ultra rich","massive wealth",
                    "generational wealth","empire","dynasty","tata","ambani"],
    "wealth":      ["money","wealth","rich","financial","income","earn","savings",
                    "investment","profitable","revenue","net worth","affluent"],
    "funding":     ["funding","investor","raise money","venture","vc","angel",
                    "startup funding","seed","series a","series b","capital raise",
                    "pitch","term sheet"],
    "legal":       ["legal","court","lawsuit","case","judge","lawyer","attorney",
                    "dispute","litigation","fight","win case","lose case","verdict",
                    "justice","settlement","arbitration","property dispute","fir",
                    "police","arrest","jail","bail","fraud case","cheating case"],
    "health":      ["health","sick","disease","illness","recover","medical","hospital",
                    "surgery","chronic","heal","cure","treatment","diagnosis","pain",
                    "energy","vitality","depression","anxiety","cancer","diabetes"],
    "marriage":    ["marriage","marry","married","partner","spouse","wedding",
                    "relationship","boyfriend","girlfriend","husband","wife",
                    "soulmate","when will i meet","love life","divorce","separation"],
    "children":    ["children","child","baby","pregnant","pregnancy","fertility",
                    "son","daughter","kids","conceive","ivf","adoption","no children"],
    "property":    ["property","house","home","real estate","land","buy home",
                    "apartment","flat","plot","construction","bungalow","villa"],
    "foreign":     ["foreign","abroad","immigrate","settle","move","relocate",
                    "visa","immigration","overseas","expat","migrate","green card",
                    "pr","citizenship","usa","canada","uk","australia","germany"],
    "education":   ["education","study","degree","exam","university","college",
                    "scholarship","course","learn","school","phd","masters","mba",
                    "gre","gmat","ielts","sat","jee","neet"],
    "career":      ["career","job","work","profession","business","promotion",
                    "salary","role","opportunity","startup","entrepreneur"],
    "spirituality":["spiritual","moksha","liberation","meditation","purpose",
                    "soul","karma","dharma","guru","ashram","enlightenment"],
}

DOMAIN_CHARTS = {
    "billionaire": [2, 10],
    "wealth":      [2, 11],
    "funding":     [2, 10],
    "legal":       [6],
    "health":      [6],
    "marriage":    [9],
    "children":    [7],
    "property":    [4],
    "foreign":     [12],
    "education":   [24],
    "career":      [9, 10],
    "spirituality":[20],
}

DOMAIN_CONTEXT_HEADERS = {
    "billionaire": "ULTRA-WEALTH & BILLIONAIRE POTENTIAL ANALYSIS",
    "wealth":      "WEALTH & FINANCIAL GROWTH ANALYSIS",
    "funding":     "FUNDING & INVESTMENT TIMING ANALYSIS",
    "legal":       "LEGAL CASE & CONFLICT RESOLUTION ANALYSIS",
    "health":      "HEALTH, RECOVERY & VITALITY ANALYSIS",
    "marriage":    "MARRIAGE, PARTNERSHIP & LOVE ANALYSIS",
    "children":    "CHILDREN, FERTILITY & PARENTHOOD ANALYSIS",
    "property":    "PROPERTY & REAL ESTATE ANALYSIS",
    "foreign":     "FOREIGN TRAVEL & SETTLEMENT ANALYSIS",
    "education":   "EDUCATION & LEARNING ANALYSIS",
    "career":      "CAREER & PROFESSIONAL DESTINY ANALYSIS",
    "spirituality":"SPIRITUAL GROWTH & SOUL PURPOSE ANALYSIS",
}

DOMAIN_LLM_INSTRUCTIONS = {
    "billionaire": """
Structure your response:
1. POTENTIAL ASSESSMENT — Does this chart have ultra-wealth combinations? Be direct.
   "Your chart carries X out of 5 wealth indicators. This is [high/moderate/limited] potential."
2. WHAT NEEDS TO ALIGN — What field, effort, and timing must come together?
3. THE PEAK WINDOW — When is the primary wealth-building period? Give actual years.
4. WHAT TO DO NOW — One concrete action aligned with the current dasha.
""",
    "wealth": """
Structure your response:
1. WEALTH POTENTIAL — What the chart says about earning and accumulation
2. HOW WEALTH FLOWS — Through which channel (salary/business/investment/windfall)
3. PEAK PERIODS — When does financial energy peak? Give actual years.
4. NOW — What to do in the current dasha to maximise financial growth
""",
    "funding": """
Structure your response:
1. FUNDING POTENTIAL — What the chart says about attracting investment
2. INVESTOR TYPE — What kind of investor/funding is most aligned (VC/angel/bank/foreign)
3. TIMING WINDOW — When is the primary funding window? Be specific with years.
4. WHAT INVESTORS SEE IN YOU — What your chart says you project to investors
5. PREPARE NOW — One actionable step
""",
    "legal": """
Structure your response:
1. CASE ASSESSMENT — What does the chart say about this legal matter? 
   Don't hedge excessively — be honest about what the chart shows.
2. WIN PROBABILITY — What factors support victory? What factors work against?
3. RESOLUTION WINDOW — When does the case most likely resolve? Give actual window.
4. STRATEGY — Fight or settle? What approach is most aligned with the chart?
5. IMMEDIATE ACTION — What to do right now
""",
    "health": """
Structure your response:
1. CONSTITUTION — What the chart says about fundamental health and recovery ability
2. CURRENT HEALTH ENERGY — What the active dasha says about health right now
3. RECOVERY WINDOW — When is healing energy strongest? Give actual timing.
4. WHAT TO ADDRESS — Which aspect of health needs most attention (physical/emotional/spiritual)
5. PRACTICAL SUPPORT — Lifestyle, timing, and approach aligned with the chart
""",
    "marriage": """
Structure your response:
1. RELATIONSHIP POTENTIAL — What the chart says about love and partnership
2. PARTNER PROFILE — What kind of person the chart indicates (don't be too specific — energy language)
3. TIMING WINDOW — When is the primary marriage/meeting window? Be specific with years.
4. WHAT TO WORK ON — What the chart suggests needs to be ready before the partner arrives
5. RIGHT NOW — What to do in the current dasha
""",
    "children": """
Structure your response:
1. FERTILITY ASSESSMENT — What the chart says about parenthood potential
2. TIMING WINDOW — When is the primary fertility window? Give actual years.
3. WHAT SUPPORTS CONCEPTION — Lifestyle, timing, and approach from chart
4. KARMIC CONTEXT — Why children come (or don't) and what it means
""",
    "property": """
Structure your response:
1. PROPERTY POTENTIAL — What the chart says about property and real estate
2. TIMING WINDOW — When is the best window to buy/build? Give actual years.
3. TYPE OF PROPERTY — What the chart indicates suits them (city/nature/large/small)
4. RIGHT NOW — Should they be looking, waiting, or preparing?
""",
    "foreign": """
Structure your response:
1. FOREIGN DESTINY — Does the chart show strong foreign connections?
2. DESTINATION ENERGY — What kind of country/environment suits them
3. TIMING WINDOW — When does the foreign opportunity open? Give actual years.
4. IMMIGRATION vs TRAVEL — Is this a long-term settlement or temporary?
5. PREPARE NOW — What to do to align with the foreign timing
""",
    "education": """
Structure your response:
1. LEARNING POTENTIAL — What the chart says about intellectual gifts
2. BEST FIELDS — What subjects/disciplines the chart supports most
3. TIMING WINDOW — When is the peak learning and academic success period?
4. NOW — What to study, pursue, or prepare in the current dasha
""",
    "career": """
Structure your response:
1. PROFESSIONAL DESTINY — What this person is built to DO
2. BEST CAREER FIELDS — Specific fields from the chart (3-5, with brief WHY)
3. ENTREPRENEUR vs EMPLOYMENT — Be direct
4. CAREER PEAK — When do career and income peak? Give actual years.
5. RIGHT NOW — Current career phase and what to focus on
""",
    "spirituality": """
Structure your response:
1. SOUL PURPOSE — What the chart says about this person's spiritual path
2. SPIRITUAL GIFTS — What practices, traditions, or paths suit them
3. CURRENT PHASE — What the active dasha is asking them to explore spiritually
4. PRACTICE — One specific suggestion aligned with their chart
""",
}


# ── Domain detector ───────────────────────────────────────────────────────────

def detect_domain(question: str) -> str:
    """Detect the life domain from the question text."""
    q = question.lower()
    scores = {}
    for domain, keywords in QUESTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q)
        if score > 0:
            scores[domain] = score

    if not scores:
        return "career"   # sensible default

    # Resolve ties: billionaire > wealth, funding > wealth
    best = max(scores, key=scores.get)
    if scores.get("billionaire", 0) > 0 and best == "wealth":
        best = "billionaire"
    if scores.get("funding", 0) > 0 and best in ("wealth", "career"):
        best = "funding"

    return best


# ── Master context builder ────────────────────────────────────────────────────

def build_life_question_context(
    question: str,
    chart_data: dict,
    dashas: dict,
    patra=None,
) -> str:
    """
    THE MAIN FUNCTION. Call this for any life question.

    Returns a complete context block string ready to inject
    into the LLM prompt. Contains:
      - Domain header
      - Divisional chart analysis
      - Yoga detection results (present + absent)
      - Timing windows with actual years
      - Remedies
      - LLM instructions specific to this domain

    Everything calculated real-time. Nothing saved.
    """
    domain     = detect_domain(question)
    lagna_sign = chart_data["lagna"]["sign"]
    header     = DOMAIN_CONTEXT_HEADERS.get(domain, "LIFE QUESTION ANALYSIS")
    llm_inst   = DOMAIN_LLM_INSTRUCTIONS.get(domain, "")

    # ── Step 1: Calculate divisional charts ───────────────────────
    divisions  = DOMAIN_CHARTS.get(domain, [9])
    d_charts   = get_all_d_charts(chart_data, divisions)
    d_charts["D1"] = {}   # placeholder — yoga engine reads chart_data directly

    # ── Step 2: Detect yogas ──────────────────────────────────────
    yogas = detect_yogas_for_question(domain, chart_data, d_charts)

    active_yogas = [y for y in yogas if y.get("present")]
    absent_yogas = [y for y in yogas if not y.get("present")]
    strength_pct = int(len(active_yogas) / max(len(yogas), 1) * 100)

    # ── Step 3: Find timing windows ───────────────────────────────
    windows = get_timing_windows(
        domain=domain,
        dashas=dashas,
        lagna_sign=lagna_sign,
    )
    timing_block = build_timing_context(domain, windows, yogas)

    # ── Step 4: Select remedies ───────────────────────────────────
    # Find weak planets from yogas
    weak_planets = []
    for y in absent_yogas:
        desc = y.get("description", "")
        # Extract planet names from description (simple heuristic)
        for planet in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]:
            if planet in desc and "weak" in desc.lower():
                weak_planets.append(planet)

    remedies = select_remedies(
        domain=domain,
        chart_data=chart_data,
        dashas=dashas,
        patra=patra,
        weak_planets=weak_planets[:2],
        limit=3,
    )
    remedies_block = remedies_to_context_block(remedies)

    # ── Step 5: Assemble final context block ──────────────────────
    charts_used = ["D-1 (Rashi)"] + [f"D-{d}" for d in divisions]
    potential   = "HIGH" if strength_pct >= 60 else "MODERATE" if strength_pct >= 40 else "LIMITED"

    lines = [
        f"═══ {header} ═══",
        f"Charts analyzed: {', '.join(charts_used)}",
        f"Overall potential: {potential} ({strength_pct}% of key indicators present)",
        "",
    ]

    # Active yogas
    if active_yogas:
        lines.append("WHAT YOUR CHART SHOWS (PRESENT):")
        for y in active_yogas:
            lines.append(f"  ✓ [{y['strength'].upper()}] {y['name']}")
            lines.append(f"    {y['implication']}")
            if y.get("timing_note"):
                lines.append(f"    Timing: {y['timing_note']}")
            lines.append("")

    # Absent yogas (important for honesty)
    if absent_yogas:
        lines.append("WHAT IS NOT IN THE CHART (ABSENT):")
        for y in absent_yogas:
            lines.append(f"  ✗ {y['name']}")
            lines.append(f"    {y['implication']}")
        lines.append("")

    # Timing
    lines.append("─" * 50)
    lines.append(timing_block)
    lines.append("")

    # Remedies
    lines.append("─" * 50)
    lines.append(remedies_block)
    lines.append("")

    # LLM instructions
    lines += [
        "─" * 50,
        "RESPONSE INSTRUCTIONS (FOLLOW EXACTLY):",
        llm_inst,
        "",
        "TRANSLATION RULES (MANDATORY):",
        "  Never say 'D-10' or 'Dashamsha' — say 'professional destiny chart'",
        "  Never say 'Dhana Yoga' — say 'wealth combination in your chart'",
        "  Never say 'Atmakaraka' — say 'your soul's deepest drive'",
        "  Never say '10th lord' — say 'the planet governing your career'",
        "  Never say 'debilitated' — say 'under pressure' or 'needs support'",
        "  Always give actual years for timing (not 'in the future')",
        "  Be honest about limitations — if potential is LIMITED, say so kindly",
        f"═══ END {domain.upper()} ANALYSIS ═══",
    ]

    return "\n".join(lines)


# ── Convenience: get structured data (not just text) ─────────────────────────

def get_life_question_data(
    question: str,
    chart_data: dict,
    dashas: dict,
    patra=None,
) -> dict:
    """
    Same as build_life_question_context() but returns structured dict
    instead of a string. Use this when you need the raw data for
    structured API responses (not just for the LLM prompt).
    """
    domain     = detect_domain(question)
    lagna_sign = chart_data["lagna"]["sign"]
    divisions  = DOMAIN_CHARTS.get(domain, [9])
    d_charts   = get_all_d_charts(chart_data, divisions)

    yogas    = detect_yogas_for_question(domain, chart_data, d_charts)
    windows  = get_timing_windows(domain=domain, dashas=dashas, lagna_sign=lagna_sign)
    remedies = select_remedies(domain=domain, chart_data=chart_data, dashas=dashas, patra=patra)

    active  = [y for y in yogas if y.get("present")]
    current = [w for w in windows if w["is_current"]]
    future  = [w for w in windows if w["is_future"]]
    pct     = int(len(active) / max(len(yogas), 1) * 100)

    return {
        "domain":          domain,
        "potential":       "high" if pct >= 60 else "moderate" if pct >= 40 else "limited",
        "strength_pct":    pct,
        "active_yogas":    active,
        "absent_yogas":    [y for y in yogas if not y.get("present")],
        "current_windows": current,
        "upcoming_windows": future[:3],
        "remedies":        remedies,
        "charts_used":     [f"D{d}" for d in divisions],
        "next_window":     future[0] if future else None,
        "is_in_window_now": len(current) > 0,
    }
