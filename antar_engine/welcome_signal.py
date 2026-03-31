"""
antar_engine/welcome_signal.py
Sprint W — Welcome Signal: 3 WOW Moments

Generated immediately after chart creation.
This is the first thing a new user sees — the entire product audition.

Three signals:
  Signal 1 — The Mirror: identity/character insight (no events, no dates)
  Signal 2 — The Chapter: names the life chapter + specific future timing
  Signal 3 — The Signal: one thing to watch for in 60-90 days + domain + action

Rules:
  - Zero Sanskrit, zero jargon
  - All dates must be in the future
  - Age-appropriate: never reference themes below floor_age
  - Cached in welcome_signals table — never regenerated
  - Generated async in background after chart save
"""

import json
import logging
import os
import re
from datetime import datetime, date, timezone
from typing import Optional

from antar_engine.age_utils import (
    calculate_current_age,
    get_floor_age,
    filter_umra_activations,
    filter_future_dasha_transitions,
    format_timing_pill,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# System prompt — the 3-signal WOW structure
# ─────────────────────────────────────────────────────────────────────────────

WELCOME_SYSTEM_PROMPT = """You are Antar — a precise, empathetic life navigation advisor.

A new user has just submitted their birth details. Generate three signals.
This is their FIRST impression of Antar. It must be unforgettable.

SIGNAL 1 — THE MIRROR
One precise character insight based on their rising sign + moon sign + nakshatra.
This is about IDENTITY — who they are, how they process the world.
Personal. Slightly uncomfortable in its accuracy. NOT an event — a truth.
2-3 sentences. No dates. No predictions. No events.

SIGNAL 2 — THE CHAPTER
Name the exact life chapter they are in right now.
Include: what this planetary period governs, what it is asking of them,
and one specific event or decision arriving before a named future date.
The chapter name should be 3-5 words (e.g. "The Inheritance Phase", "The Authority Window").
3-4 sentences. The timing field MUST be a specific future Month YYYY.

SIGNAL 3 — THE SIGNAL
One specific thing to watch for in the next 60-90 days.
Based on current planetary period + slow planet transits.
Name the domain. Name the date range. End with one action or thing to watch for.
2-3 sentences.

ABSOLUTE RULES:
1. This user is {{current_age}} years old. NEVER reference events or themes from before age {{floor_age}}.
2. Zero Sanskrit terms. Zero jargon. Plain English only.
3. Each signal is 2-4 sentences. No padding. No hedging. No filler.
4. Do NOT say "your chart shows" or "astrologically speaking." State facts directly.
5. All dates in Signal 2 and Signal 3 must be in the FUTURE. Never reference a date that has passed.
6. Signal 2 timing must be a specific Month YYYY at least 1 month in the future.
7. Signal 3 domain must be one of: career / relationship / financial / health / travel / legal
8. Signal 3 watch_for must be one concrete sentence — what to watch for or do.
9. If the user's name is provided, start Signal 1 headline with their name.
10. Career signals for 55+ = authority, legacy, succession — NOT starting out.
11. Relationship signals for 60+ = depth, companionship — NOT first relationship.
12. Never reference childhood, teenage years, or early adulthood for users over 40.

Return EXACTLY this JSON and nothing else:
{
  "signal_1": {
    "type": "mirror",
    "headline": "<user's name if provided>, <insight in under 12 words>",
    "body": "2-3 sentences. Character/identity only. No events. No dates."
  },
  "signal_2": {
    "type": "chapter",
    "headline": "<chapter name 3-5 words>",
    "body": "3-4 sentences. What this period governs + what decision/event is arriving.",
    "timing": "Month YYYY"
  },
  "signal_3": {
    "type": "signal",
    "headline": "<one sentence under 12 words>",
    "body": "2-3 sentences. Specific domain + date range + what to do.",
    "domain": "career",
    "watch_for": "One sentence — the specific thing to watch for or act on."
  }
}"""


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point — same signature as before so main.py needs zero changes
# ─────────────────────────────────────────────────────────────────────────────

async def generate_welcome_signal(
    chart_id:      str,
    chart_data:    dict,
    dashas:        dict,
    first_name:    Optional[str],
    lagna:         Optional[str],
    moon_sign:     Optional[str],
    current_dasha: Optional[str],
    age:           Optional[int],
    country_code:  Optional[str],
    supabase,
    claude_client,
    birth_date:    Optional[str] = None,
) -> dict:
    """
    Generate and save the 3-signal welcome for a new chart.
    Called async after chart creation — non-blocking.
    Returns the welcome signal dict with signal_1, signal_2, signal_3.
    """
    # ── Check if already generated ────────────────────────────────
    try:
        existing = supabase.table("welcome_signals") \
            .select("*") \
            .eq("chart_id", chart_id) \
            .execute()
        if existing.data:
            row = existing.data[0]
            # If it has signal_1_type, it's the new 3-signal format — return as structured
            if row.get("signal_1_type"):
                return _row_to_response(row)
            # Old format — delete and regenerate
            try:
                supabase.table("welcome_signals") \
                    .delete() \
                    .eq("chart_id", chart_id) \
                    .execute()
                logger.info(f"[welcome] Deleted old-format signal for {chart_id[:8]}, regenerating")
            except Exception:
                pass
    except Exception:
        pass

    # ── Build context ─────────────────────────────────────────────
    context = _build_welcome_context(
        chart_data, dashas, first_name, lagna,
        moon_sign, current_dasha, age, country_code,
        birth_date=birth_date,
    )

    # ── Call Claude ───────────────────────────────────────────────
    result = await _call_claude(context, claude_client)

    # ── Inject first_name into Signal 1 headline if missing ──────
    if first_name and result:
        s1 = result.get("signal_1", {})
        headline = s1.get("headline", "")
        if headline and not headline.lower().startswith(first_name.lower()):
            s1["headline"] = f"{first_name}, {headline[0].lower()}{headline[1:]}"
            result["signal_1"] = s1

    # ── Save to DB (flattened for Supabase) ──────────────────────
    try:
        s1 = result.get("signal_1", {})
        s2 = result.get("signal_2", {})
        s3 = result.get("signal_3", {})

        row = {
            "chart_id":          chart_id,
            # Signal 1 — Mirror
            "signal_1_type":     s1.get("type", "mirror"),
            "signal_1_headline": s1.get("headline", ""),
            "signal_1_body":     s1.get("body", ""),
            # Signal 2 — Chapter
            "signal_2_type":     s2.get("type", "chapter"),
            "signal_2_headline": s2.get("headline", ""),
            "signal_2_body":     s2.get("body", ""),
            "signal_2_timing":   s2.get("timing", ""),
            # Signal 3 — Signal
            "signal_3_type":     s3.get("type", "signal"),
            "signal_3_headline": s3.get("headline", ""),
            "signal_3_body":     s3.get("body", ""),
            "signal_3_domain":   s3.get("domain", ""),
            "signal_3_watch_for": s3.get("watch_for", ""),
            # Legacy fields (for backward compat if Lovable still reads old shape)
            "headline":          s1.get("headline", ""),
            "summary":           s2.get("body", ""),
            "action":            s3.get("watch_for", ""),
            "signal_type":       s3.get("domain", "opportunity"),
            "chapter_name":      s2.get("headline", ""),
            "created_at":        datetime.now(timezone.utc).isoformat(),
        }

        supabase.table("welcome_signals").insert(row).execute()
        logger.info(f"[welcome] 3-signal saved for chart {chart_id[:8]}")
        return _row_to_response(row)

    except Exception as e:
        logger.error(f"[welcome] DB save failed: {e}")
        # Return structured response even if DB save fails
        return result


def _row_to_response(row: dict) -> dict:
    """Convert a flattened DB row back to the structured 3-signal response."""
    return {
        "chart_id": row.get("chart_id", ""),
        "signal_1": {
            "type":     row.get("signal_1_type", "mirror"),
            "headline": row.get("signal_1_headline", ""),
            "body":     row.get("signal_1_body", ""),
        },
        "signal_2": {
            "type":     row.get("signal_2_type", "chapter"),
            "headline": row.get("signal_2_headline", ""),
            "body":     row.get("signal_2_body", ""),
            "timing":   row.get("signal_2_timing", ""),
        },
        "signal_3": {
            "type":     row.get("signal_3_type", "signal"),
            "headline": row.get("signal_3_headline", ""),
            "body":     row.get("signal_3_body", ""),
            "domain":   row.get("signal_3_domain", ""),
            "watch_for": row.get("signal_3_watch_for", ""),
        },
        # Legacy fields for backward compat
        "headline":     row.get("headline", ""),
        "summary":      row.get("summary", ""),
        "action":       row.get("action", ""),
        "signal_type":  row.get("signal_type", "opportunity"),
        "chapter_name": row.get("chapter_name", ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Context builder — temporal grounding + chart facts
# ─────────────────────────────────────────────────────────────────────────────

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

    # ── Umra — filtered to upcoming only ─────────────────────────
    umra_block = ""
    if current_age:
        umra_items = filter_umra_activations(current_age, max_upcoming=2)
        if umra_items:
            umra_lines = []
            for u in umra_items:
                years_away = u['activation_age'] - current_age
                if years_away <= 0:
                    distance = "currently active"
                elif years_away == 1:
                    distance = "activates next year"
                else:
                    distance = f"activates in {years_away} years"
                umra_lines.append(
                    f"  House {u['house']} (age {u['activation_age']}, {distance}): {u['theme']}. "
                    f"Tell the user what this house unlocks and what to start building toward now."
                )
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
        future_transition = f"Current period ends: {format_timing_pill(future_ts[0]['end_date'])} ({future_ts[0]['end_date']})"

    # ── Chart facts ──────────────────────────────────────────────
    planets    = chart_data.get("planets", {})
    moon_nak   = planets.get("Moon", {}).get("nakshatra", "")
    sun_sign   = planets.get("Sun", {}).get("sign", "")
    mars_sign  = planets.get("Mars", {}).get("sign", "")
    jupiter_sign = planets.get("Jupiter", {}).get("sign", "")
    saturn_sign  = planets.get("Saturn", {}).get("sign", "")
    yogas      = chart_data.get("yogas", [])
    top_yoga   = yogas[0].get("name", "") if yogas else ""
    house_lords = chart_data.get("house_lords", {})

    # ── Assemble context — temporal grounding first ──────────────
    lines = []

    # Temporal grounding — must be the first thing Claude sees
    if current_age and floor_age:
        lines.append(f"TEMPORAL GROUNDING — READ THIS FIRST:")
        if birth_date:
            _bday_month = datetime.strptime(birth_date[:10], "%Y-%m-%d").strftime("%B")
            _turning = current_age + 1
            lines.append(f"This user is {current_age} years old (turning {_turning} in {_bday_month}).")
        else:
            lines.append(f"This user is {current_age} years old.")
        lines.append(f"Temporal floor: NEVER reference themes or events from before age {floor_age}.")
        lines.append(f"Today: {datetime.now().strftime('%B %d, %Y')}")
        lines.append("")

    # Identity facts for Signal 1 (Mirror)
    lines.append("── IDENTITY (for Signal 1 — Mirror) ──")
    if first_name:
        lines.append(f"User's name: {first_name}")
    lines.append(f"Rising sign (Lagna): {lagna or 'unknown'}")
    lines.append(f"Moon sign: {moon_sign or 'unknown'}")
    if moon_nak:
        lines.append(f"Moon nakshatra: {moon_nak}")
    lines.append(f"Sun sign: {sun_sign}")
    if top_yoga:
        lines.append(f"Strongest yoga: {top_yoga}")
    lines.append("")

    # Timing facts for Signal 2 (Chapter)
    lines.append("── TIMING (for Signal 2 — Chapter) ──")
    lines.append(f"Current planetary period: {dasha_text}")
    if future_transition:
        lines.append(future_transition)
    if house_lords:
        # Show what houses the current dasha lord rules
        dasha_lord = dasha_text.split("-")[0].strip() if dasha_text else ""
        ruled_houses = [
            h for h, lord in house_lords.items()
            if str(lord).strip().lower() == dasha_lord.lower()
        ]
        if ruled_houses:
            lines.append(f"{dasha_lord} rules houses: {', '.join(str(h) for h in ruled_houses)}")
    if umra_block:
        lines.append(umra_block)
    lines.append("")

    # Transit facts for Signal 3 (Signal)
    lines.append("── TRANSITS (for Signal 3 — Signal) ──")
    if jupiter_sign:
        lines.append(f"Jupiter currently in: {jupiter_sign}")
    if saturn_sign:
        lines.append(f"Saturn currently in: {saturn_sign}")
    if mars_sign:
        lines.append(f"Mars currently in: {mars_sign}")
    if country_code:
        lines.append(f"Country: {country_code}")
    lines.append("")

    # Final instruction
    age_note = f"someone who is currently {current_age} years old" if current_age else "an adult"
    lines.append(
        f"Generate three WOW signals for {age_note}. "
        f"Signal 1 must be about identity/character ONLY — no events. "
        f"Signal 2 must name the life chapter and include a specific future date. "
        f"Signal 3 must name a domain and a 60-90 day watch window. "
        f"All content must be age-appropriate. All dates must be in the future."
    )

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Claude call — parse 3-signal JSON
# ─────────────────────────────────────────────────────────────────────────────

async def _call_claude(context: str, claude_client) -> dict:
    """Call Claude Sonnet and parse the 3-signal welcome JSON."""
    try:
        # Interpolate age into system prompt
        response = await claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=WELCOME_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}],
        )
        text = response.content[0].text.strip()

        # Strip markdown fences
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        result = json.loads(text.strip())

        # Validate structure — must have all 3 signals
        if "signal_1" not in result or "signal_2" not in result or "signal_3" not in result:
            logger.warning("[welcome] Claude returned incomplete 3-signal structure, using fallback")
            return _fallback_signal()

        # Validate Signal 2 timing is future
        timing = result.get("signal_2", {}).get("timing", "")
        if timing:
            try:
                timing_date = datetime.strptime(timing, "%B %Y")
                if timing_date.replace(day=1) < datetime.now().replace(day=1):
                    logger.warning(f"[welcome] Signal 2 timing is past ({timing}), will regenerate")
                    # Don't fail — let it through, the prompt should prevent this
            except ValueError:
                pass  # Non-standard format, let it through

        # Validate Signal 3 domain
        valid_domains = {"career", "relationship", "financial", "health", "travel", "legal"}
        s3_domain = result.get("signal_3", {}).get("domain", "")
        if s3_domain and s3_domain.lower() not in valid_domains:
            result["signal_3"]["domain"] = "career"  # Safe default

        return result

    except json.JSONDecodeError as e:
        logger.error(f"[welcome] JSON parse failed: {e}")
        return _fallback_signal()
    except Exception as e:
        import traceback
        print(f"[welcome] Claude call FAILED: {type(e).__name__}: {e}")
        print(f"[welcome] Traceback: {traceback.format_exc()}")
        logger.error(f"[welcome] Claude call failed: {e}")
        return _fallback_signal()


def _fallback_signal() -> dict:
    """Fallback if Claude fails — returns valid 3-signal structure."""
    return {
        "signal_1": {
            "type": "mirror",
            "headline": "Your chart is calculated — here is what stands out.",
            "body": "Your birth chart reveals a specific pattern in how you process decisions and relationships. Ask Antar any question to explore what your chart says about your life right now.",
        },
        "signal_2": {
            "type": "chapter",
            "headline": "New Chapter Ahead",
            "body": "You are entering a period of transition. The next several months bring a decision point that will shape the direction ahead. Ask Antar about a specific area of your life to get precise timing.",
            "timing": "",
        },
        "signal_3": {
            "type": "signal",
            "headline": "Ask your first question to activate your signal.",
            "body": "Your chart has specific signals for the next 90 days. Ask Antar about career, relationships, finances, or any life area to see what is arriving and when.",
            "domain": "career",
            "watch_for": "Ask your first question to get a specific signal with timing.",
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sync reader — for GET /api/v1/welcome/{chart_id}
# ─────────────────────────────────────────────────────────────────────────────

def get_welcome_signal(chart_id: str, supabase) -> Optional[dict]:
    """Read cached welcome signal. Returns None if not yet generated."""
    try:
        result = supabase.table("welcome_signals") \
            .select("*") \
            .eq("chart_id", chart_id) \
            .execute()
        if not result.data:
            return None
        row = result.data[0]
        # Check if it's the new 3-signal format
        if row.get("signal_1_type"):
            return _row_to_response(row)
        # Old format — return None so the endpoint regenerates
        return None
    except Exception as e:
        logger.warning(f"[welcome] Read failed: {e}")
        return None
