"""
antar_engine/monthly_deepdive.py
Sprint E — Monthly Deep-Dive

On the 1st of each month, Antar generates a full monthly reading:
  - Which planets are strong/weak this month (Masik Phal)
  - 3 priority actions for the month
  - Remedies specific to this chart this month
  - Key timing windows — best and worst weeks

Cached per chart per month. Generated on the 1st via cron.
Also available on-demand via GET /api/v1/monthly-deepdive/{chart_id}
"""

import logging
import json
import re
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

DEEPDIVE_TABLE = "monthly_deepdives"

MONTHLY_SYSTEM_PROMPT = """You are Antar — a precise, warm life navigation advisor.

Generate a full monthly deep-dive reading. This is proactive coaching for the month ahead.
The user did not ask a specific question — Antar is providing a complete monthly overview.

RULES:
- Plain English throughout. Zero jargon.
- Be specific to the chart data provided — actual planets, actual timing
- 3 priority actions: specific, actionable, different domains
- Remedies: practical and tied to specific chart placements
- Timing windows: name specific weeks, not vague periods

Return ONLY this JSON:
{
  "month":          "April 2026",
  "month_theme":    "One sentence — what this month is fundamentally about for this person.",
  "energy_level":   "high OR moderate OR low OR mixed",
  "strong_planets": ["planet1", "planet2"],
  "weak_planets":   ["planet1"],
  "overview":       "2-3 sentences. Overall energy of the month. What is the dominant theme.",
  "priority_actions": [
    {"domain": "career",  "action": "Specific action for this month. Verb-first."},
    {"domain": "wealth",  "action": "Specific action for this month. Verb-first."},
    {"domain": "health",  "action": "Specific action for this month. Verb-first."}
  ],
  "best_week":  "Week of [date] — [reason in 6 words]",
  "caution_week": "Week of [date] — [what to avoid in 5 words]",
  "remedies": [
    {"planet": "Saturn", "practice": "Specific remedy. One sentence."},
    {"planet": "Moon",   "practice": "Specific remedy. One sentence."}
  ],
  "monthly_mantra": "One plain English affirmation for this month. Under 10 words."
}"""


async def generate_monthly_deepdive(
    chart_id:      str,
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    lk_context:    Optional[str],
    supabase,
    claude_client,
    force_refresh: bool = False,
) -> dict:
    """
    Generate or return cached monthly deep-dive.
    Regenerates on the 1st of each month or if force_refresh=True.
    """
    now        = datetime.now(timezone.utc)
    month_key  = now.strftime("%Y-%m")

    # Check cache
    if not force_refresh:
        cached = _read_cache(chart_id, month_key, supabase)
        if cached:
            return cached

    # Build context
    context = _build_deepdive_context(
        chart_data, dashas, first_name, lagna,
        moon_sign, current_dasha, age, country_code,
        lk_context, now
    )

    # Call Claude
    result = await _call_claude(context, claude_client)
    result["chart_id"]  = chart_id
    result["month_key"] = month_key

    # Save to cache
    try:
        supabase.table(DEEPDIVE_TABLE).upsert({
            "chart_id":  chart_id,
            "month_key": month_key,
            "deepdive":  result,
            "created_at": now.isoformat(),
        }).execute()
        logger.info(f"[monthly] Deep-dive saved for {chart_id[:8]} {month_key}")
    except Exception as e:
        logger.warning(f"[monthly] Cache save failed: {e}")

    return result


def _read_cache(chart_id: str, month_key: str, supabase) -> Optional[dict]:
    try:
        result = supabase.table(DEEPDIVE_TABLE) \
            .select("deepdive") \
            .eq("chart_id", chart_id) \
            .eq("month_key", month_key) \
            .execute()
        if result.data:
            return result.data[0]["deepdive"]
    except Exception as e:
        logger.warning(f"[monthly] Cache read failed: {e}")
    return None


def _build_deepdive_context(
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    lk_context:    Optional[str],
    now:           datetime,
) -> str:
    month_str = now.strftime("%B %Y")
    planets   = chart_data.get("planets", {})

    # Planet positions
    planet_positions = []
    for planet, data in planets.items():
        if isinstance(data, dict):
            sign = data.get("sign", "")
            house = data.get("house", "")
            if sign:
                planet_positions.append(f"{planet} in {sign}" + (f" (house {house})" if house else ""))

    # Lal Kitab monthly context
    lk_note = ""
    if lk_context:
        lk_lines = lk_context.split("\n")[:3]
        lk_note = "Lal Kitab context: " + " ".join(lk_lines)

    lines = [
        f"MONTHLY DEEP-DIVE REQUEST — {month_str}",
        f"Name: {first_name or 'not provided'}",
        f"Rising sign: {lagna or 'unknown'}",
        f"Moon sign: {moon_sign or 'unknown'}",
        f"Current planetary period: {current_dasha or 'unknown'}",
        f"Age: {age or 'unknown'}",
        f"Country: {country_code or 'unknown'}",
        "",
        "PLANET POSITIONS:",
    ] + planet_positions[:9]

    if lk_note:
        lines.append(lk_note)

    lines.append(
        f"\nGenerate a complete monthly deep-dive for {month_str}. "
        "Identify which planets are strong and weak this month. "
        "Give 3 specific priority actions across different domains. "
        "Name specific weeks for best timing and caution periods."
    )

    return "\n".join(lines)


async def _call_claude(context: str, claude_client) -> dict:
    try:
        response = await claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system=MONTHLY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}]
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*",     "", text)
        text = re.sub(r"\s*```$",     "", text)
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"[monthly] Claude call failed: {e}")
        return _fallback_deepdive()


def _fallback_deepdive() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "month":       now.strftime("%B %Y"),
        "month_theme": "A month of consolidation and forward movement.",
        "energy_level":"moderate",
        "strong_planets": [],
        "weak_planets":   [],
        "overview":    "This month calls for focused action on your most important priorities. "
                       "Ask Antar a specific question for a precise reading.",
        "priority_actions": [
            {"domain": "career",  "action": "Identify your top professional priority and work on it daily."},
            {"domain": "wealth",  "action": "Review and reduce one unnecessary expense."},
            {"domain": "health",  "action": "Establish one consistent daily health practice."},
        ],
        "best_week":    "First week of the month — fresh energy",
        "caution_week": "Last week — avoid major decisions",
        "remedies": [
            {"planet": "general", "practice": "Morning sunlight for 10 minutes daily."},
        ],
        "monthly_mantra": "Steady progress beats urgent rushing.",
    }
