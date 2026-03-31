"""
antar_engine/annual_planning.py
Sprint E — Annual Planning Session

Generated on user's birthday and January 1st.
The most comprehensive proactive output Antar produces:
  - Year lord analysis (what this year is fundamentally about)
  - Peak windows per domain (when to act in each area of life)
  - What to build, protect, and release this year
  - Remedies for the year specific to this chart
  - One-paragraph summary for sharing

Cached per chart per year. Available via GET /api/v1/annual-plan/{chart_id}
"""

import logging
import json
import re
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

ANNUAL_TABLE = "annual_plans"

ANNUAL_SYSTEM_PROMPT = """You are Antar — a precise, warm life navigation advisor.

Generate a full annual planning session. This is the most important reading Antar produces.
It covers the full year ahead — what it's about, when to act in each domain, what remedies to follow.

RULES:
- ALWAYS start year_summary with the user's first name if provided e.g. "Ramandeep, this year..."
- Plain English throughout. Zero jargon.
- Specific timing windows: name months, not vague periods
- Peak windows per domain: at least 4 domains covered
- Be specific to the chart data — actual planetary periods and positions
- ALWAYS address the user by first name in year_summary e.g. 'Ramandeep, this year...'
- The year summary should feel like a wise advisor's view of the year ahead
- Remedies: practical, tied to specific chart placements, maintainable year-round

Return ONLY this JSON:
{
  "year":          2026,
  "year_theme":    "One sentence — what this year is fundamentally about. Under 12 words.",
  "year_quality":  "expansion OR consolidation OR transformation OR harvest OR building",
  "year_summary":  "3-4 sentences. The arc of the year. What will grow, what will shift, what will resolve.",
  "peak_windows": {
    "career":       {"months": "March–August", "signal": "One sentence what career energy does this period."},
    "wealth":       {"months": "August–December", "signal": "One sentence."},
    "relationships":{"months": "April–June", "signal": "One sentence."},
    "health":       {"months": "January–March", "signal": "One sentence about health focus."},
    "foreign":      {"months": "September–November", "signal": "One sentence."},
    "spiritual":    {"months": "November–January", "signal": "One sentence."}
  },
  "build_this_year":    ["thing1", "thing2", "thing3"],
  "protect_this_year":  ["thing1", "thing2"],
  "release_this_year":  ["thing1", "thing2"],
  "yearly_remedies": [
    {"planet": "Saturn", "practice": "Year-long remedy. Specific and practical."},
    {"planet": "Jupiter", "practice": "Year-long remedy. Specific and practical."},
    {"planet": "current_dasha_lord", "practice": "Remedy for the current planetary period lord."}
  ],
  "year_mantra":   "One plain English affirmation for the year. Under 10 words.",
  "critical_dates": [
    {"date": "August 2026", "event": "What happens astrologically and what it means."},
    {"date": "November 2026", "event": "What changes and how to navigate it."}
  ]
}"""


async def generate_annual_plan(
    chart_id:       str,
    chart_data:     dict,
    dashas:         dict,
    first_name:     Optional[str],
    lagna:          Optional[str],
    moon_sign:      Optional[str],
    current_dasha:  Optional[str],
    birth_date:     Optional[str],
    age:            Optional[int],
    country_code:   Optional[str],
    dkp_context:    Optional[str],
    lk_context:     Optional[str],
    supabase,
    claude_client,
    force_refresh:  bool = False,
) -> dict:
    """
    Generate or return cached annual plan.
    Regenerates on birthday, January 1st, or if force_refresh=True.
    """
    now      = datetime.now(timezone.utc)
    year_key = str(now.year)

    # Check cache
    if not force_refresh:
        cached = _read_cache(chart_id, year_key, supabase)
        if cached:
            return cached

    # Build context
    context = _build_annual_context(
        chart_data, dashas, first_name, lagna,
        moon_sign, current_dasha, birth_date,
        age, country_code, dkp_context, lk_context, now
    )

    # Call Claude
    result = await _call_claude(context, claude_client)
    result["chart_id"] = chart_id
    result["year_key"] = year_key

    # Inject first_name into year_summary
    if first_name and result.get("year_summary"):
        ys = result["year_summary"]
        if not ys.startswith(first_name):
            result["year_summary"] = f"{first_name}, {ys[0].lower()}{ys[1:]}"
    if first_name and result.get("year_theme"):
        yt = result["year_theme"]
        if not yt.startswith(first_name):
            result["year_theme"] = f"{first_name}: {yt}"  

    # Save to cache
    try:
        supabase.table(ANNUAL_TABLE).upsert({
            "chart_id":  chart_id,
            "year_key":  year_key,
            "plan":      result,
            "created_at": now.isoformat(),
        }).execute()
        logger.info(f"[annual] Plan saved for {chart_id[:8]} {year_key}")
    except Exception as e:
        logger.warning(f"[annual] Cache save failed: {e}")

    return result


def _read_cache(chart_id: str, year_key: str, supabase) -> Optional[dict]:
    try:
        result = supabase.table(ANNUAL_TABLE) \
            .select("plan") \
            .eq("chart_id", chart_id) \
            .eq("year_key", year_key) \
            .execute()
        if result.data:
            return result.data[0]["plan"]
    except Exception as e:
        logger.warning(f"[annual] Cache read failed: {e}")
    return None


def _build_annual_context(
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    birth_date:    Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    dkp_context:   Optional[str],
    lk_context:    Optional[str],
    now:           datetime,
) -> str:
    year = now.year
    planets = chart_data.get("planets", {})

    # Get upcoming dasha transitions
    dasha_transitions = []
    vim = dashas.get("vimsottari", [])
    for p in vim[:4]:
        lord = p.get("lord_or_sign") or p.get("planet_or_sign", "")
        end  = str(p.get("end_date") or p.get("end", ""))[:10]
        if lord and end:
            dasha_transitions.append(f"{lord} period ends: {end}")

    # Key planet positions
    saturn_sign  = planets.get("Saturn",  {}).get("sign", "")
    jupiter_sign = planets.get("Jupiter", {}).get("sign", "")
    rahu_sign    = planets.get("Rahu",    {}).get("sign", "")

    lines = [
        f"ANNUAL PLAN REQUEST — Year {year}",
        f"Name: {first_name or 'not provided'}",
        f"Rising sign: {lagna or 'unknown'}",
        f"Moon sign: {moon_sign or 'unknown'}",
        f"Current planetary period: {current_dasha or 'unknown'}",
        f"Age this year: {age or 'unknown'}",
        f"Birth date: {birth_date or 'unknown'}",
        f"Country: {country_code or 'unknown'}",
        "",
        "KEY PLANETARY POSITIONS:",
        f"Saturn in: {saturn_sign or 'unknown'}",
        f"Jupiter in: {jupiter_sign or 'unknown'}",
        f"Rahu in: {rahu_sign or 'unknown'}",
        "",
        "UPCOMING DASHA TRANSITIONS:",
    ] + dasha_transitions

    if dkp_context:
        dkp_lines = [l for l in dkp_context.split("\n") if l.strip()][:3]
        lines.append("\nECONOMIC CONTEXT:")
        lines.extend(dkp_lines)

    if lk_context:
        lk_lines = lk_context.split("\n")[:3]
        lines.append("\nLAL KITAB ANNUAL CONTEXT:")
        lines.extend(lk_lines)

    lines.append(
        f"\nGenerate a complete annual plan for {year}. "
        "Identify the year's dominant theme from the current dasha and transits. "
        "Give specific monthly windows for each major life domain. "
        "Identify 2-3 critical dates or transition points in the year. "
        "Give year-long remedies that are practical and maintainable."
    )

    return "\n".join(str(l) for l in lines)


async def _call_claude(context: str, claude_client) -> dict:
    try:
        response = await claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            system=ANNUAL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}]
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*",     "", text)
        text = re.sub(r"\s*```$",     "", text)
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"[annual] Claude call failed: {e}")
        return _fallback_annual()


def _fallback_annual() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "year":         now.year,
        "year_theme":   "A year of building towards your next major life chapter.",
        "year_quality": "building",
        "year_summary": "This year asks you to lay foundations for what comes next. "
                        "Focus on the areas where consistent effort compounds over time. "
                        "Ask Antar specific questions to get precise timing for each domain.",
        "peak_windows": {
            "career":       {"months": "Q2-Q3", "signal": "Career momentum builds mid-year."},
            "wealth":       {"months": "Q3-Q4", "signal": "Financial consolidation in second half."},
            "relationships":{"months": "Q1-Q2", "signal": "Relationship clarity early in the year."},
            "health":       {"months": "All year", "signal": "Consistent practices matter most."},
        },
        "build_this_year":   ["Professional expertise", "Financial reserves", "Key relationships"],
        "protect_this_year": ["Health and energy", "Core relationships"],
        "release_this_year": ["Outdated commitments", "Draining situations"],
        "yearly_remedies": [
            {"planet": "general", "practice": "Morning sunlight and grounding practice daily."},
        ],
        "year_mantra":   "Build what lasts, release what doesn't.",
        "critical_dates": [],
    }
