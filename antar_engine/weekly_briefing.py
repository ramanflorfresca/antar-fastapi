"""
antar_engine/weekly_briefing.py
Sprint E — Weekly Briefing

Every Monday, Antar proactively delivers a 5-domain briefing for the week ahead.
No user action required. Pulled from /api/v1/weekly-briefing/{chart_id}.

The briefing covers:
  Career / Wealth / Relationships / Health / Spirit
  One overall focus recommendation for the week
  Key timing window (best day this week for important actions)

Uses: Masik Phal overlay + current transits + dasha + DKP context
Cached per chart per week — regenerated on Monday.
"""

import logging
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

BRIEFING_TABLE = "weekly_briefings"

WEEKLY_SYSTEM_PROMPT = """You are Antar — a precise, warm life navigation advisor.

Generate a weekly briefing for the upcoming week. This is proactive coaching — 
the user did not ask a question. Antar is watching their chart and flagging what matters.

RULES:
- ALWAYS start weekly_focus with the user's first name if provided e.g. "Ramandeep, this week..."
- Each domain signal: 2 sentences maximum. Plain English. Zero jargon.
- The weekly focus: one paragraph, the single most important theme this week
- Best day: name a specific day of the week for important actions
- ALWAYS address the user by first name in weekly_focus e.g. 'Ramandeep, this week...'
- Be specific to the chart data provided — not generic weekly horoscope language
- Warm but precise. Like a trusted advisor's Monday morning message.

Return ONLY this JSON:
{
  "week_of": "March 31, 2026",
  "weekly_focus": "One paragraph — the dominant theme for this week and what it means practically.",
  "best_day": "Wednesday — [reason in 5 words]",
  "domains": {
    "career":       "2 sentences. What career/work energy is active this week.",
    "wealth":       "2 sentences. What financial energy is active this week.",
    "relationships":"2 sentences. What relationship energy is active this week.",
    "health":       "2 sentences. What health/body energy is active this week.",
    "spirit":       "2 sentences. What spiritual/inner energy is active this week."
  },
  "one_action": "The single most important action to take before Sunday. Verb-first."
}"""


async def generate_weekly_briefing(
    chart_id:      str,
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    dkp_context:   Optional[str],
    supabase,
    claude_client,
    force_refresh: bool = False,
) -> dict:
    """
    Generate or return cached weekly briefing for a chart.
    Regenerates on Mondays or if force_refresh=True.
    """
    now       = datetime.now(timezone.utc)
    week_start = _get_week_start(now)

    # Check cache
    if not force_refresh:
        cached = _read_cache(chart_id, week_start, supabase)
        if cached:
            return cached

    # Build context
    context = _build_briefing_context(
        chart_data, dashas, first_name, lagna,
        moon_sign, current_dasha, age, country_code,
        dkp_context, now
    )

    # Call Claude
    result = await _call_claude(context, claude_client)
    result["chart_id"]   = chart_id
    result["week_start"] = week_start.isoformat()
    result["week_of"]    = week_start.strftime("%B %d, %Y")

    # Inject first_name into weekly_focus
    if first_name and result.get("weekly_focus"):
        wf = result["weekly_focus"]
        if not wf.startswith(first_name):
            result["weekly_focus"] = f"{first_name}, {wf[0].lower()}{wf[1:]}"
    if first_name and result.get("one_action"):
        oa = result["one_action"]
        if not oa.startswith(first_name):
            result["one_action"] = oa  # action stays verb-first

    # Save to cache
    try:
        supabase.table(BRIEFING_TABLE).upsert({
            "chart_id":   chart_id,
            "week_start": week_start.isoformat(),
            "briefing":   result,
            "created_at": now.isoformat(),
        }).execute()
        logger.info(f"[weekly] Briefing saved for chart {chart_id[:8]}")
    except Exception as e:
        logger.warning(f"[weekly] Cache save failed: {e}")

    return result


def _get_week_start(dt: datetime) -> datetime:
    """Return Monday of the current week."""
    days_since_monday = dt.weekday()
    return (dt - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def _read_cache(chart_id: str, week_start: datetime, supabase) -> Optional[dict]:
    try:
        result = supabase.table(BRIEFING_TABLE) \
            .select("briefing") \
            .eq("chart_id", chart_id) \
            .eq("week_start", week_start.isoformat()) \
            .execute()
        if result.data:
            return result.data[0]["briefing"]
    except Exception as e:
        logger.warning(f"[weekly] Cache read failed: {e}")
    return None


def _build_briefing_context(
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    dkp_context:   Optional[str],
    now:           datetime,
) -> str:
    week_str  = now.strftime("Week of %B %d, %Y")
    name_str  = f"Name: {first_name}" if first_name else ""
    age_str   = f"Age: {age}" if age else ""

    planets   = chart_data.get("planets", {})
    moon_nak  = planets.get("Moon", {}).get("nakshatra", "")
    sun_sign  = planets.get("Sun",  {}).get("sign", "")

    # Get transits if available
    transits  = chart_data.get("current_transits", {})
    saturn_transit = transits.get("Saturn", {}).get("sign", "")
    jupiter_transit = transits.get("Jupiter", {}).get("sign", "")

    lines = [
        f"WEEKLY BRIEFING REQUEST — {week_str}",
        name_str,
        f"Rising sign: {lagna or 'unknown'}",
        f"Moon sign: {moon_sign or 'unknown'}, Moon nakshatra: {moon_nak}",
        f"Sun sign: {sun_sign}",
        f"Current planetary period: {current_dasha or 'unknown'}",
    ]

    if age_str:          lines.append(age_str)
    if country_code:     lines.append(f"Country: {country_code}")
    if saturn_transit:   lines.append(f"Saturn currently in: {saturn_transit}")
    if jupiter_transit:  lines.append(f"Jupiter currently in: {jupiter_transit}")

    if dkp_context:
        # Add first 2 lines of DKP only
        dkp_lines = [l for l in dkp_context.split("\n") if l.strip()][:2]
        lines.append("Economic context: " + " ".join(dkp_lines))

    lines.append(
        f"\nGenerate a weekly briefing for the week ahead ({week_str}). "
        "Cover all 5 life domains. Be specific to this chart's current period."
    )

    return "\n".join(l for l in lines if l)


async def _call_claude(context: str, claude_client) -> dict:
    try:
        response = await claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            system=WEEKLY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}]
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*",     "", text)
        text = re.sub(r"\s*```$",     "", text)
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"[weekly] Claude call failed: {e}")
        return _fallback_briefing()


def _fallback_briefing() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "week_of":       now.strftime("%B %d, %Y"),
        "weekly_focus":  "Your chart is active this week. Ask Antar a specific question to get a precise reading.",
        "best_day":      "Wednesday — mid-week clarity",
        "domains": {
            "career":        "Focus on completing existing projects before starting new ones.",
            "wealth":        "Review your financial commitments this week.",
            "relationships": "Invest time in your most important relationship.",
            "health":        "Prioritise sleep and reduce stimulants.",
            "spirit":        "A quiet 10 minutes in the morning will anchor your week."
        },
        "one_action": "Identify your single most important task and do it first thing Monday.",
    }
