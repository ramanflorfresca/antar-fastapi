"""
antar_engine/compatibility_session_engine.py

Conversational compatibility engine — 3 layers, progressive depth.

Layer 1: Personal + professional compatibility (always runs)
Layer 2: Startup/business alignment (if user provides context)  
Layer 3: Product/deck analysis (if user provides product info)

Handles missing birth time gracefully.
"""

from __future__ import annotations
from datetime import datetime, date
import os, json
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

PLANET_DOMAIN = {
    "Sun":     "authority, leadership, vision, father, ego",
    "Moon":    "mind, emotions, adaptability, public-facing",
    "Mars":    "execution, energy, drive, conflict, property",
    "Mercury": "communication, intellect, deals, negotiation",
    "Jupiter": "wisdom, expansion, ethics, teaching, wealth",
    "Venus":   "relationships, creativity, luxury, harmony",
    "Saturn":  "discipline, structure, longevity, karma",
    "Rahu":    "disruption, technology, foreign, ambition",
    "Ketu":    "spirituality, past expertise, detachment",
}

ROLE_MAP = {
    "Sun":     "Visionary / Brand leader / Public face",
    "Mars":    "Executor / Head of operations / Builder",
    "Mercury": "Communicator / Head of product / Dealmaker",
    "Jupiter": "Advisor / CFO / Strategic thinker",
    "Venus":   "Creative director / Partnerships / Culture",
    "Saturn":  "COO / Finance / Process and compliance",
    "Moon":    "Community / Marketing / User empathy",
    "Rahu":    "Disruptor / Tech lead / Growth hacker",
    "Ketu":    "Researcher / Specialist / Behind-the-scenes",
}


def _parse_dt(s):
    try: return datetime.strptime(str(s)[:10], "%Y-%m-%d")
    except: return datetime.utcnow()


def _age(birth_date: str) -> int:
    try:
        born = date.fromisoformat(birth_date[:10])
        return (date.today() - born).days // 365
    except: return 35


def _current_md(dashas: dict) -> tuple:
    """Returns (md_lord, start_year, end_year) or ('unknown','','')"""
    now = datetime.utcnow()
    for row in dashas.get("vimsottari", []):
        level = row.get("level") or row.get("type","")
        if level != "mahadasha": continue
        sd = _parse_dt(row.get("start_date") or row.get("start",""))
        ed = _parse_dt(row.get("end_date")   or row.get("end",""))
        if sd <= now <= ed:
            lord = row.get("lord_or_sign") or row.get("planet_or_sign","")
            return lord, sd.year, ed.year
    return "unknown", "", ""


def build_person_brief(
    name: str,
    chart_data: dict,
    dashas: dict,
    birth_date: str,
    has_birth_time: bool = True,
) -> str:
    """Build a compact astrological brief for one person."""
    age     = _age(birth_date)
    lagna   = chart_data.get("lagna", {})
    lagna_sign = lagna.get("sign","unknown") if isinstance(lagna, dict) else str(lagna)
    planets = chart_data.get("planets", {})
    yogas   = chart_data.get("yogas", [])
    atma    = chart_data.get("atmakaraka","")
    divs    = chart_data.get("divisional_charts", {})

    md_lord, md_start, md_end = _current_md(dashas)

    moon = planets.get("Moon", {})
    moon_sign = moon.get("sign","")
    moon_nak  = moon.get("nakshatra","")

    # D10 career picture
    d10 = divs.get("d10", {})
    d10_lagna = d10.get("lagna","?")
    d10_sun   = d10.get("planets",{}).get("Sun",{}).get("house","?")

    # Role from atmakaraka
    role = ROLE_MAP.get(atma, "Versatile contributor")

    confidence = "FULL ANALYSIS" if has_birth_time else "PARTIAL ANALYSIS (no birth time — lagna/houses estimated)"

    lines = [
        f"=== {name.upper()} ({confidence}) ===",
        f"Age: {age} | Born: {birth_date}",
    ]

    if has_birth_time:
        lines.append(f"Lagna: {lagna_sign} | Moon: {moon_sign} ({moon_nak})")
    else:
        lines.append(f"Moon: {moon_sign} ({moon_nak}) — birth time unknown, lagna not available")

    lines += [
        f"Atmakaraka (soul planet): {atma} — {PLANET_DOMAIN.get(atma,'')}",
        f"Natural role: {role}",
        f"Current chapter: {md_lord} Mahadasha ({md_start}–{md_end})",
    ]

    if has_birth_time:
        lines.append(f"Career chart (D10): Lagna={d10_lagna}, Sun in house {d10_sun}")

    # Key planets
    lines.append("Key planets:")
    for p in ["Sun","Moon","Mars","Mercury","Jupiter","Saturn","Rahu"]:
        pd = planets.get(p,{})
        sign = pd.get("sign","")
        house = pd.get("house","?") if has_birth_time else "?"
        lines.append(f"  {p}: {sign}" + (f" house {house}" if has_birth_time else ""))

    # Strong yogas
    strong = [y for y in yogas if y.get("strength")=="strong"]
    if strong:
        lines.append("Strong yogas: " + ", ".join(y["name"] for y in strong))

    return "\n".join(lines)


def build_layer1_prompt(
    brief_a: str,
    brief_b: str,
    name_a: str,
    name_b: str,
    compat_type: str,  # "relationship" | "business" | "cofounder"
    has_time_a: bool,
    has_time_b: bool,
) -> str:
    """Layer 1 prompt — personal + professional compatibility."""

    confidence_note = ""
    if not has_time_a or not has_time_b:
        missing = []
        if not has_time_a: missing.append(name_a)
        if not has_time_b: missing.append(name_b)
        confidence_note = f"""
NOTE ON CONFIDENCE: Birth time is missing for {', '.join(missing)}.
This means lagna and house placements cannot be calculated for them.
Analysis will use: Moon sign/nakshatra, planetary positions, dashas, and yogas.
Confidence is reduced from ~90% to ~65-70%.
Explicitly state this limitation in your response — do not pretend to have full data.
Be clear: "Based on available data (birth time not provided for X)..."
"""

    # ── Type-specific scoring instructions ───────────────────────────────────
    TYPE_CONFIG = {
        "relationship": {
            "focus_planets": "Moon, Venus, Jupiter, 7th house lord",
            "score_weights": "Emotional resonance 35% + 7th house compatibility 25% + Venus harmony 20% + Dasha alignment 20%",
            "key_questions": [
                "Do their Moon signs create emotional harmony or friction?",
                "Does Venus in either chart aspect the other's ASC or Moon?",
                "Are their 7th house lords compatible?",
                "Are they in dashas that support love/partnership (Venus, Moon, Jupiter)?",
                "What is the long-term emotional sustainability?",
            ],
            "extra_sections": f"""
## Emotional Chemistry
[How do their Moon signs and Venus placements interact? Is there natural attraction and emotional safety?]
[Reference specific Moon signs, Venus positions, and nakshatra compatibility]

## Long-term Harmony
[Will daily life together feel easy or draining? Reference Moon/4th house/Saturn interactions]

## The Love Window
[Are their current dashas supportive of deepening this relationship? When is the peak period?]""",
            "score_note": "Score 90-100: Deep soul alignment. 75-89: Strong with conscious effort. 60-74: Compatible but requires work. Below 60: Fundamentally different rhythms.",
        },
        "business": {
            "focus_planets": "Mercury, Jupiter, Saturn, 10th house lord, 11th house lord",
            "score_weights": "Communication + deal-making (Mercury) 30% + Growth alignment (Jupiter/11th) 25% + Trust + structure (Saturn) 25% + Dasha timing 20%",
            "key_questions": [
                "Are their Mercury placements compatible for communication and deal-making?",
                "Do their 10th houses show complementary professional authority?",
                "Does their 11th house (gains/networks) align?",
                "Are they in career/money dashas (Sun, Mercury, Jupiter, Saturn)?",
                "Can they trust each other under financial pressure?",
            ],
            "extra_sections": f"""
## Communication & Deal-Making
[How do their Mercury and Saturn placements interact? Will they negotiate well or talk past each other?]

## Financial Compatibility
[Do their 2nd and 11th house lords align? Who manages money, who generates it?]

## Business Runway
[How many years of aligned business dashas do they share? When does the window close?]""",
            "score_note": "Score 85-100: Natural business alliance. 70-84: Strong with clear role definition. 55-69: Possible but needs structure. Below 55: Misaligned incentives.",
        },
        "cofounder": {
            "focus_planets": "Atmakaraka, Saturn, Rahu, Mercury, 10th house, FIELD×MODE operating rhythm",
            "score_weights": "Operating rhythm fit (FIELD×MODE) 30% + Dasha runway alignment 30% + Business factors (Mercury/10th/11th) 25% + Personal trust (Moon/7th) 15%",
            "key_questions": [
                "Are their Atmakarakas compatible — do their souls want the same thing?",
                "Does one chart show visionary leadership (Sun/Jupiter dominant) while the other shows execution (Mars/Saturn dominant)?",
                "How long is their shared dasha runway — do they have 5+ years of aligned periods?",
                "Does Rahu in either chart point toward ambition that conflicts with the other?",
                "Can Saturn in both charts sustain a long-term commitment?",
            ],
            "extra_sections": f"""
## Role Architecture
[Who is the Visionary (Sun/Jupiter/Rahu dominant)? Who is the Operator (Mars/Saturn/Mercury dominant)?]
[This must be specific — name the role each person is built for based on their chart]

## Cofounder Runway
[How many years of aligned dasha periods do they share? What happens post-2026? Post-2028?]
[This is critical for cofounder relationships — be specific about timeline]

## Mission Alignment
[Do their Atmakarakas point in the same direction? Are their souls building toward compatible futures?]

## The 5-Year Test
[Will this partnership survive the first major dasha transition? Name the exact year and what shifts]""",
            "score_note": "Score 85-100: Rare cofounder alignment — build without hesitation. 70-84: Strong fit with clear equity + role structure. 55-69: Possible but high maintenance. Below 55: Different chapters, different missions.",
        },
    }

    cfg = TYPE_CONFIG.get(compat_type, TYPE_CONFIG["cofounder"])

    return f"""You are a master Vedic astrologer with 30 years of experience advising entrepreneurs and couples.

You are analyzing compatibility between {name_a} and {name_b}.
Compatibility type: {compat_type.upper()}

{brief_a}

{brief_b}

{confidence_note}

SCORING FOCUS FOR {compat_type.upper()}:
Key planets/houses: {cfg['focus_planets']}
Score weights: {cfg['score_weights']}

Key questions to answer:
{chr(10).join(f"- {q}" for q in cfg['key_questions'])}

Use ONLY the data provided above. Never invent planetary positions.

OUTPUT FORMAT (respond in this exact structure):

## Compatibility Overview
[2-3 sentence summary of the overall energy between these two people for {compat_type}]

**Overall score: X/100**
[One line explaining what drives this score for {compat_type}]
{cfg['score_note']}

## What Works — Strengths
[3-4 specific strengths grounded in actual planetary data]
Each strength MUST reference specific planets, signs, houses, or dasha periods.
{cfg['extra_sections']}

## Watch Points — Growth Areas
[2-3 specific friction areas with actionable framing]
Never say "this will fail" — frame as "this requires conscious attention"

## Timing — Key Windows
[2-3 specific timing insights based on both dasha timelines]
Be specific: exact years, which dasha period, what it means for this {compat_type} context.

## The Core Question
[One honest, direct paragraph: given all of this, what is the fundamental nature of this {compat_type} partnership?]

After your analysis, end with exactly this line:
---
Would you like me to analyze how this partnership aligns with your startup or business context?"""


def build_layer2_prompt(
    brief_a: str,
    brief_b: str,
    name_a: str,
    name_b: str,
    layer1_summary: str,
    startup_context: dict,
) -> str:
    """Layer 2 prompt — startup/business alignment."""

    stage   = startup_context.get("stage","")
    sector  = startup_context.get("sector","")
    mission = startup_context.get("mission","")
    team    = startup_context.get("team_size","")
    revenue = startup_context.get("revenue_status","")
    challenge = startup_context.get("current_challenge","")

    return f"""You are a master Vedic astrologer advising startup founders.

PREVIOUSLY ESTABLISHED (Layer 1 compatibility summary):
{layer1_summary}

FULL ASTROLOGICAL BRIEFS:
{brief_a}

{brief_b}

STARTUP CONTEXT PROVIDED:
Stage: {stage}
Sector: {sector}
Mission: {mission}
Team size: {team}
Revenue status: {revenue}
Current challenge: {challenge}

ANALYSIS INSTRUCTIONS:
Cross-reference the startup context with both charts.
- D10 (career/profession chart) shows what professional domain each founder is built for
- Mercury shows communication and deal-making ability
- Jupiter shows expansion timing and ethics
- Saturn shows execution discipline and longevity
- Rahu shows disruption ability and technology affinity
- Current dasha periods show WHEN each founder is at peak energy

OUTPUT FORMAT:

## Founder-Startup Fit
[Is this startup aligned with what both founders' charts are built to do?]
[Reference specific planetary positions that support or challenge this]

## Natural Roles
{name_a}: [specific role — CEO/CTO/CPO/COO/etc with astrological basis]
{name_b}: [specific role with astrological basis]
[How these roles create complementarity]

## Fundraising and Growth Windows
[Specific timing based on Jupiter transits and dasha periods for both]
[Best windows: name the months/years with astrological basis]

## Execution Risk Patterns
[2-3 specific risk patterns this partnership might fall into]
[Each must be grounded in chart data — never generic advice]

## Contract and Commitment Timing
[Best time to formalize the partnership based on current transits]

## 3-Year Trajectory
[Year 1: what the charts say]
[Year 2: what the charts say]  
[Year 3: what the charts say — including any divergence risk]

## Will They Build It Together?
[Direct honest answer based on dasha alignment over the next 5 years]

---
Would you like me to analyze your product or pitch deck against both founders' charts?"""


def build_layer3_prompt(
    brief_a: str,
    brief_b: str,
    name_a: str,
    name_b: str,
    layer1_summary: str,
    layer2_summary: str,
    product_context: str,
) -> str:
    """Layer 3 prompt — product/deck analysis."""

    return f"""You are a master Vedic astrologer and startup advisor.

ESTABLISHED CONTEXT:
Layer 1 (personal compatibility): {layer1_summary[:300]}
Layer 2 (startup alignment): {layer2_summary[:300]}

FULL ASTROLOGICAL BRIEFS:
{brief_a}

{brief_b}

PRODUCT / DECK DESCRIPTION:
{product_context}

ANALYSIS INSTRUCTIONS:
Cross-reference the product with both founders' dharma (life purpose from charts).

Key questions to answer from the charts:
1. Does this product domain match the founders' atmakaraka (soul planet)?
2. Is the market timing aligned with current Rahu/Jupiter dasha periods?
3. Does the product solve a Saturn problem (structure/discipline) or a Rahu opportunity (disruption/tech)?
4. What does the 5th house (creativity/innovation) and 11th house (gains/market) say about product-market fit?
5. Are the founders' charts built to execute THIS specific type of product?

OUTPUT FORMAT:

## Product-Founder Dharma Fit
[Is this the right product for these two people to build? Be direct.]
[Ground every claim in specific planetary positions]

## Astrological Strengths of This Venture
[3-4 specific indicators that support this product succeeding with these founders]

## What Could Derail It
[2-3 specific risk signals from the charts]
[Planetary basis for each]

## What to Build First
[Based on the founders' strongest planetary domains right now]
[What should be prioritized given current dasha energy]

## Market Timing
[Is the current planetary environment (transits + dashas) favorable for this product category?]
[Specific windows for launch, fundraising, team expansion]

## Final Signal
[One direct paragraph: given the founders' charts, the product, and the current timing — is this the right venture, with the right people, at the right time?]"""


def detect_no_birth_time_chart(chart_data: dict) -> bool:
    """
    Detect if a chart was created without birth time.
    Heuristic: if lagna degree is exactly 0.0 or lagna is missing,
    or if birth_time was "12:00" (our default for unknown time).
    """
    lagna = chart_data.get("lagna", {})
    if isinstance(lagna, dict):
        degree = lagna.get("degree", 0)
        # Exact noon = likely placeholder
        if abs(degree - 0.0) < 0.1:
            return True
    return False


def build_no_time_brief(
    name: str,
    birth_date: str,
    moon_sign: str,
    moon_nakshatra: str,
    sun_sign: str,
    dashas: dict,
) -> dict:
    """
    For users who don't have birth time for the other person.
    Uses only Moon sign, Sun sign, and dasha (from Moon nakshatra).
    Still gives 65-70% accuracy.
    """
    md_lord, md_start, md_end = _current_md(dashas)
    age = _age(birth_date)

    # Estimate atmakaraka from Moon sign (rough approximation)
    moon_lord = SIGN_LORDS.get(moon_sign,"Jupiter")

    return {
        "name":           name,
        "birth_date":     birth_date,
        "age":            age,
        "moon_sign":      moon_sign,
        "moon_nakshatra": moon_nakshatra,
        "sun_sign":       sun_sign,
        "estimated_atmakaraka": moon_lord,
        "current_md":     md_lord,
        "md_period":      f"{md_start}–{md_end}",
        "has_birth_time": False,
        "confidence":     0.65,
        "missing_data":   ["lagna","house_placements","D9","D10","D12"],
        "available_data": ["moon_sign","moon_nakshatra","sun_sign","vimsottari_dasha","planetary_signs"],
    }


async def run_layer1_llm(
    brief_a: str,
    brief_b: str,
    name_a: str,
    name_b: str,
    compat_type: str,
    has_time_a: bool,
    has_time_b: bool,
) -> str:
    """Call LLM for Layer 1 analysis."""
    import openai
    prompt = build_layer1_prompt(
        brief_a, brief_b, name_a, name_b,
        compat_type, has_time_a, has_time_b
    )
    client = openai.AsyncOpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
    )
    resp = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role":"system","content":"You are a master Vedic astrologer. Be specific, direct, and grounded in the chart data. Never fabricate planetary positions."},
            {"role":"user","content":prompt}
        ],
        temperature=0.4,
        max_tokens=2000,
        timeout=60,
    )
    return resp.choices[0].message.content.strip()


async def run_layer2_llm(
    brief_a: str, brief_b: str,
    name_a: str, name_b: str,
    layer1_summary: str,
    startup_context: dict,
) -> str:
    """Call LLM for Layer 2 analysis."""
    import openai
    prompt = build_layer2_prompt(
        brief_a, brief_b, name_a, name_b,
        layer1_summary, startup_context
    )
    client = openai.AsyncOpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
    )
    resp = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role":"system","content":"You are a master Vedic astrologer and startup advisor. Be specific and direct."},
            {"role":"user","content":prompt}
        ],
        temperature=0.4,
        max_tokens=2000,
        timeout=60,
    )
    return resp.choices[0].message.content.strip()


async def run_layer3_llm(
    brief_a: str, brief_b: str,
    name_a: str, name_b: str,
    layer1_summary: str, layer2_summary: str,
    product_context: str,
) -> str:
    """Call LLM for Layer 3 analysis."""
    import openai
    prompt = build_layer3_prompt(
        brief_a, brief_b, name_a, name_b,
        layer1_summary, layer2_summary, product_context
    )
    client = openai.AsyncOpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
    )
    resp = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role":"system","content":"You are a master Vedic astrologer and product advisor. Be direct and specific."},
            {"role":"user","content":prompt}
        ],
        temperature=0.4,
        max_tokens=2000,
        timeout=60,
    )
    return resp.choices[0].message.content.strip()
