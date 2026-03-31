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
from antar_engine.age_utils import (
    calculate_current_age, get_floor_age,
    filter_umra_activations, filter_future_dasha_transitions,
    format_timing_pill,
)

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

AGE RULES — CRITICAL:
- The user's current age and temporal floor are in the context — read them first
- NEVER reference themes, events, or life stages from before the floor age
- All timing references must be FUTURE dates — never past
- Career signals for 55+ = authority, legacy, succession — NOT starting out
- Relationship signals for 60+ = depth, companionship — NOT first relationship
- Never reference childhood, teenage years, or early adulthood for users over 40

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

    # Inject first_name into output regardless of what Claude returned
    if first_name and result:
        headline = result.get("headline", "")
        summary  = result.get("summary", "")
        if headline and not headline.startswith(first_name):
            result["headline"] = f"{first_name}, {headline[0].lower()}{headline[1:]}"
        if summary and not summary.startswith(first_name):
            result["summary"] = f"{first_name}, {summary[0].lower()}{summary[1:]}"

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
    birth_date:    Optional[str] = None,
) -> str:
    # ── Age intelligence (Sprint W) ───────────────────────────────
    if birth_date:
        current_age = calculate_current_age(birth_date[:10])
    elif age:
        current_age = age
    else:
        current_age = None

    floor_age = get_floor_age(current_age) if current_age else None

    umra_block = ""
    if current_age:
        umra_items = filter_umra_activations(current_age, max_upcoming=2)
        if umra_items:
            umra_lines = [
                f"  House {u['house']} (age {u['activation_age']}): {u['theme']}"
                for u in umra_items
            ]
            umra_block = "Upcoming age activations:\n" + "\n".join(umra_lines)

    # ── Dasha — future transitions only ──────────────────────────
    dasha_text = current_dasha or ""
    future_transition = ""
    if not dasha_text and dashas:
        vim = dashas.get("vimsottari", [])
        if vim:
            first = vim[0]
            dasha_text = first.get("lord_or_sign") or first.get("planet_or_sign", "")

    raw_ts = []
    for d in dashas.get("vimsottari", []) if dashas else []:
        if d.get("end_date"):
            raw_ts.append({
                "planet": d.get("lord_or_sign") or d.get("planet_or_sign", ""),
                "end_date": d["end_date"],
            })
    future_ts = filter_future_dasha_transitions(raw_ts)
    if future_ts:
        future_transition = f"Current period ends: {format_timing_pill(future_ts[0]['end_date'])}"

    # ── Chart facts ───────────────────────────────────────────────
    planets   = chart_data.get("planets", {})
    sun_sign  = planets.get("Sun",  {}).get("sign", "")
    mars_sign = planets.get("Mars", {}).get("sign", "")
    yogas     = chart_data.get("yogas", [])
    top_yoga  = yogas[0].get("name", "") if yogas else ""

    # ── Assemble — temporal grounding first ───────────────────────
    lines = []
    if current_age and floor_age:
        lines.append(f"TEMPORAL GROUNDING: This user is {current_age} years old.")
        lines.append(f"Temporal floor: never reference themes or events from before age {floor_age}.")
        lines.append(f"Today: {datetime.now().strftime('%B %d, %Y')}")
        lines.append("")

    if first_name:    lines.append(f"User's name: {first_name}")
    if country_code:  lines.append(f"Country: {country_code}")
    lines.append(f"Rising sign (Lagna): {lagna or 'unknown'}")
    lines.append(f"Moon sign: {moon_sign or 'unknown'}")
    lines.append(f"Sun sign: {sun_sign}")
    lines.append(f"Current planetary period: {dasha_text}")
    if future_transition: lines.append(future_transition)
    if top_yoga:    lines.append(f"Strongest yoga in chart: {top_yoga}")
    if mars_sign:   lines.append(f"Mars in: {mars_sign}")
    if umra_block:  lines.append(umra_block)

    age_note = f"someone who is currently {current_age} years old." if current_age else "an adult."
    lines.append(
        "\nGenerate a welcome signal that makes this person feel immediately understood. "
        "Reference their rising sign and current planetary period specifically. "
        "Tell them what chapter of life they are in and what it means for right now. "
        "All content must be appropriate for " + age_note
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
