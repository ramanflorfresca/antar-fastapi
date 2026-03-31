"""
antar_engine/welcome_signal.py
Sprint E — Welcome Signal

Generated immediately after chart creation.
This is the first thing a new user sees — it must prove Antar is different.

Rules:
  - 3 sentences maximum in plain_summary
  - Zero jargon
  - One specific action for this week
  - Calculated from their exact chart — not generic
  - Generated async in background after chart save
  - Cached in welcome_signals table — never regenerated
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

WELCOME_SYSTEM_PROMPT = """You are Antar — a precise, warm life navigation advisor.

A new user has just submitted their birth details. This is the FIRST thing they will 
read from Antar. It must feel personal, specific, and immediately useful.

RULES:
- 3 sentences MAXIMUM in the summary
- Zero Sanskrit or astrological jargon
- Reference their actual rising sign and current planetary period
- Tell them what phase of life they are in right now
- End with ONE specific action they can take THIS WEEK
- Warm but precise — like a trusted advisor who knows them well
- ALWAYS start with the user's first name if provided e.g. 'Ramandeep, your chart shows...'
- If no name provided, start directly with the insight
- Do NOT say "Welcome to Antar" or any generic greeting

The goal: in 3 sentences, make them feel that Antar sees them specifically — 
not a sun sign, not a generic reading, but their exact life situation right now.

CRITICAL: If the user's name is provided, you MUST start the headline and summary 
with their first name. e.g. "Ramandeep, your chart shows..." Never skip the name.

Return ONLY this JSON:
{
  "headline": "One sentence — the single most important thing about their chart right now. Under 12 words.",
  "summary": "2-3 sentences. What phase of life they are in + what it means practically. Zero jargon.",
  "action": "ONE specific action for this week. Verb-first. One sentence.",
  "signal_type": "opportunity OR caution OR transition OR peak",
  "chapter_name": "3-4 word name for their current life chapter e.g. 'Authority Building Phase'"
}"""


async def generate_welcome_signal(
    chart_id:    str,
    chart_data:  dict,
    dashas:      dict,
    first_name:  Optional[str],
    lagna:       Optional[str],
    moon_sign:   Optional[str],
    current_dasha: Optional[str],
    age:         Optional[int],
    country_code: Optional[str],
    supabase,
    claude_client,
) -> dict:
    """
    Generate and save the welcome signal for a new chart.
    Called async after chart creation — non-blocking.

    Returns the welcome signal dict.
    """
    # Check if already generated
    try:
        existing = supabase.table("welcome_signals") \
            .select("*") \
            .eq("chart_id", chart_id) \
            .execute()
        if existing.data:
            return existing.data[0]
    except Exception:
        pass

    # Build the context block for Claude
    context = _build_welcome_context(
        chart_data, dashas, first_name, lagna,
        moon_sign, current_dasha, age, country_code
    )

    # Call Claude
    result = await _call_claude(context, claude_client)

    # Save to DB
    try:
        row = {
            "chart_id":    chart_id,
            "headline":    result.get("headline"),
            "summary":     result.get("summary"),
            "action":      result.get("action"),
            "signal_type": result.get("signal_type", "opportunity"),
            "chapter_name":result.get("chapter_name"),
            "created_at":  datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("welcome_signals").insert(row).execute()
        logger.info(f"[welcome] Signal saved for chart {chart_id[:8]}")
        return row
    except Exception as e:
        logger.error(f"[welcome] DB save failed: {e}")
        return result


def _build_welcome_context(
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
) -> str:
    name_line = f"User's name: {first_name}" if first_name else "User's name: not provided"
    age_line  = f"Age: {age}" if age else ""
    country_line = f"Country: {country_code}" if country_code else ""

    # Extract key chart facts
    planets = chart_data.get("planets", {})
    sun_sign  = planets.get("Sun",  {}).get("sign", "")
    mars_sign = planets.get("Mars", {}).get("sign", "")

    # Get top yoga if available
    yogas = chart_data.get("yogas", [])
    top_yoga = yogas[0].get("name", "") if yogas else ""

    # Get current dasha
    dasha_text = current_dasha or ""
    if not dasha_text and dashas:
        vim = dashas.get("vimsottari", [])
        if vim:
            first = vim[0]
            lord = first.get("lord_or_sign") or first.get("planet_or_sign", "")
            dasha_text = lord

    lines = [
        name_line,
        f"Rising sign (Lagna): {lagna or 'unknown'}",
        f"Moon sign: {moon_sign or 'unknown'}",
        f"Sun sign: {sun_sign}",
        f"Current planetary period: {dasha_text}",
    ]
    if age_line:    lines.append(age_line)
    if country_line: lines.append(country_line)
    if top_yoga:    lines.append(f"Strongest yoga in chart: {top_yoga}")
    if mars_sign:   lines.append(f"Mars in: {mars_sign}")

    lines.append(
        "\nGenerate a welcome signal that makes this person feel immediately understood. "
        "Reference their rising sign and current planetary period specifically. "
        "Tell them what chapter of life they are in and what it means for right now."
    )

    return "\n".join(lines)


async def _call_claude(context: str, claude_client) -> dict:
    """Call Claude and parse the welcome signal JSON."""
    import json, re

    try:
        response = await claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            system=WELCOME_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}]
        )
        text = response.content[0].text.strip()

        # Strip markdown fences
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*",     "", text)
        text = re.sub(r"\s*```$",     "", text)

        return json.loads(text.strip())

    except Exception as e:
        import traceback
        print(f"[welcome] Claude call FAILED: {type(e).__name__}: {e}")
        print(f"[welcome] Traceback: {traceback.format_exc()}")
        logger.error(f"[welcome] Claude call failed: {e}")
        return _fallback_signal()


def _fallback_signal() -> dict:
    return {
        "headline":    "Your chart is calculated — here's what it shows right now.",
        "summary":     "Your birth chart reveals a specific moment in your life's pattern. "
                       "Ask Antar any question to get a precise reading for your situation.",
        "action":      "Ask your first question to start your personalised reading.",
        "signal_type": "opportunity",
        "chapter_name": "New Chapter",
    }


# ── Sync wrapper for reading cached signal ────────────────────────────────────

def get_welcome_signal(chart_id: str, supabase) -> Optional[dict]:
    """Read cached welcome signal. Returns None if not yet generated."""
    try:
        result = supabase.table("welcome_signals") \
            .select("*") \
            .eq("chart_id", chart_id) \
            .execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.warning(f"[welcome] Read failed: {e}")
        return None
