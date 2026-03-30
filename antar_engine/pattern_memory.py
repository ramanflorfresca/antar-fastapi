"""
pattern_memory.py
Sprint C3 — Pattern Memory (Layer 7)

Fetches a user's prediction history and builds two things:
  1. A memory context block — what Antar told this person before
  2. A diagnostic mode trigger — when the same domain is asked again
     after a timing window has passed (unresolved case)

Architecture:
  - Single DB query, no extra LLM call
  - Diagnostic mode is a changed instruction set, not a new AI call
  - Time-based inference: if user asks same domain after window passed = unresolved
  - User can override with explicit rating (accuracy_rating 1/0)

Used in /predict: fetched before the main Claude call, appended to context.
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# How many past predictions to load into memory
MEMORY_LIMIT = 20

# Domains that are considered the "same" for diagnostic detection
DOMAIN_GROUPS = {
    "funding":     ["funding", "loans", "business", "startup"],
    "career":      ["career", "business"],
    "wealth":      ["wealth", "loans", "property"],
    "love":        ["love", "children"],
    "health":      ["health"],
    "foreign":     ["foreign", "travel"],
    "legal":       ["legal", "enemies"],
    "spirituality":["spirituality"],
}

# Timing window patterns — extract how far in the future a window was
TIMING_PATTERNS = [
    r"before\s+(\w+\s+\d{4})",           # "before May 2026"
    r"through\s+(\w+\s+\d{4})",          # "through March 2026"
    r"until\s+(\w+\s+\d{4})",            # "until June 2026"
    r"by\s+(\w+\s+\d{4})",               # "by April 2026"
    r"next\s+(\d+)\s+weeks?",            # "next 3 weeks"
    r"next\s+(\d+)\s+months?",           # "next 2 months"
    r"(\w+\s+\d{4})\s+onward",           # "August 2026 onward"
]

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "oct": 10, "nov": 11, "dec": 12,
}


# ── Main public function ──────────────────────────────────────────────────────

def build_pattern_memory(
    chart_id: str,
    current_concern: str,
    current_question: str,
    supabase,
) -> dict:
    """
    Build the full pattern memory context for a /predict call.

    Returns:
        {
            "memory_block":      str  — formatted context for system prompt
            "diagnostic_mode":   bool — True if same domain asked after window passed
            "diagnostic_block":  str  — additional instruction for Claude if diagnostic
            "unresolved_case":   dict — the unresolved prediction if found, else None
            "past_predictions":  list — raw prediction rows
        }
    """
    past = _fetch_predictions(chart_id, supabase)

    if not past:
        return _empty_result()

    # Infer fulfillment for unrated predictions
    past = _infer_fulfillment(past)

    # Check for diagnostic mode trigger
    unresolved = _detect_unresolved(past, current_concern)
    diagnostic_mode = unresolved is not None

    # Build context blocks
    memory_block     = _build_memory_block(past, unresolved)
    diagnostic_block = _build_diagnostic_block(
        unresolved, current_question, current_concern
    ) if diagnostic_mode else ""

    return {
        "memory_block":     memory_block,
        "diagnostic_mode":  diagnostic_mode,
        "diagnostic_block": diagnostic_block,
        "unresolved_case":  unresolved,
        "past_predictions": past,
    }


# ── DB fetch ─────────────────────────────────────────────────────────────────

def _fetch_predictions(chart_id: str, supabase) -> list:
    """Fetch last N predictions for this chart. Single DB query."""
    try:
        result = supabase.table("predictions") \
            .select(
                "id, created_at, query, concern, "
                "plain_summary, action_item, signal_line, "
                "timing_window, signal_confidence, all_domains, "
                "accuracy_rating"
            ) \
            .eq("chart_id", chart_id) \
            .not_.is_("plain_summary", "null") \
            .order("created_at", desc=True) \
            .limit(MEMORY_LIMIT) \
            .execute()

        return result.data or []

    except Exception as e:
        logger.warning(f"[C3] Failed to fetch predictions for {chart_id}: {e}")
        return []


# ── Fulfillment inference ─────────────────────────────────────────────────────

def _infer_fulfillment(predictions: list) -> list:
    """
    For unrated predictions, infer fulfillment status from timing window.
    If the timing window has passed and no rating → mark as inferred_unresolved.
    Does NOT write to DB — inference only, user rating overrides.
    """
    now = datetime.now(timezone.utc)

    for pred in predictions:
        if pred.get("accuracy_rating") is not None:
            # User already rated — trust that
            pred["fulfillment_status"] = (
                "confirmed" if pred["accuracy_rating"] == 1 else "did_not_happen"
            )
            continue

        timing = pred.get("timing_window", "") or ""
        window_end = _parse_timing_window(timing, pred.get("created_at"))

        if window_end and now > window_end:
            pred["fulfillment_status"] = "inferred_unresolved"
            pred["window_end_parsed"]  = window_end.isoformat()
        else:
            pred["fulfillment_status"] = "pending"

    return predictions


def _parse_timing_window(timing: str, created_at: str) -> Optional[datetime]:
    """
    Try to extract a datetime from a timing_window string.
    Returns None if unparseable.
    """
    if not timing:
        return None

    timing_lower = timing.lower()
    now = datetime.now(timezone.utc)

    # "next N weeks"
    m = re.search(r"next\s+(\d+)\s+weeks?", timing_lower)
    if m:
        try:
            base = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            ) if created_at else now
            return base + timedelta(weeks=int(m.group(1)))
        except Exception:
            pass

    # "next N months"
    m = re.search(r"next\s+(\d+)\s+months?", timing_lower)
    if m:
        try:
            base = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            ) if created_at else now
            return base + timedelta(days=int(m.group(1)) * 30)
        except Exception:
            pass

    # "before/through/until/by Month YYYY" or "Month YYYY onward"
    for pattern in [
        r"(?:before|through|until|by)\s+(\w+)\s+(\d{4})",
        r"(\w+)\s+(\d{4})\s+onward",
        r"(\w+)\s+(\d{4})",
    ]:
        m = re.search(pattern, timing_lower)
        if m:
            month_str = m.group(1)
            year_str  = m.group(2)
            month_num = MONTH_MAP.get(month_str)
            if month_num:
                try:
                    return datetime(
                        int(year_str), month_num, 28,
                        tzinfo=timezone.utc
                    )
                except Exception:
                    pass

    return None


# ── Diagnostic detection ──────────────────────────────────────────────────────

def _detect_unresolved(
    predictions: list,
    current_concern: str
) -> Optional[dict]:
    """
    Detect if the current question is about the same domain as a previous
    unresolved prediction whose timing window has passed.

    Returns the unresolved prediction dict if found, else None.
    """
    if not current_concern:
        return None

    # Find all domains related to current concern
    related_domains = _get_related_domains(current_concern)

    for pred in predictions:
        if pred.get("fulfillment_status") != "inferred_unresolved":
            continue

        pred_domains  = pred.get("all_domains") or []
        pred_concern  = pred.get("concern", "")
        pred_domains_set = set(pred_domains + [pred_concern])

        # Check overlap with current concern's domain group
        if pred_domains_set & set(related_domains):
            return pred  # Return the most recent unresolved match

    return None


def _get_related_domains(concern: str) -> list:
    """Return all domains considered related to the given concern."""
    for group_key, domains in DOMAIN_GROUPS.items():
        if concern in domains:
            return domains
    return [concern]


# ── Context block builders ────────────────────────────────────────────────────

def _build_memory_block(
    predictions: list,
    unresolved: Optional[dict]
) -> str:
    """
    Build the PATTERN MEMORY block appended to the /predict system prompt.
    """
    if not predictions:
        return ""

    lines = ["PATTERN MEMORY — What Antar has told this person before:"]

    # Flag the unresolved case first if present
    if unresolved:
        tw       = unresolved.get("timing_window", "")
        concern  = unresolved.get("concern", "")
        signal   = unresolved.get("signal_line", "") or unresolved.get("plain_summary", "")[:80]
        created  = _format_age(unresolved.get("created_at"))
        lines.append(
            f"\n⚠ UNRESOLVED CASE — {concern.upper()} ({created}):\n"
            f'  Previous signal: "{signal}"\n'
            f"  Timing window stated: {tw} — THIS WINDOW HAS PASSED\n"
            f"  Status: User is asking about this again → window did not close as predicted"
        )

    # Recent predictions
    lines.append("\nRECENT PREDICTIONS:")
    shown = 0
    for pred in predictions:
        if shown >= 8:
            break
        if pred is unresolved:
            shown += 1
            continue  # already shown above

        concern   = pred.get("concern", "general")
        signal    = pred.get("signal_line", "") or (pred.get("plain_summary", "") or "")[:80]
        created   = _format_age(pred.get("created_at"))
        status    = pred.get("fulfillment_status", "pending")
        rating    = pred.get("accuracy_rating")
        accuracy  = (
            " ✓ confirmed" if rating == 1
            else " ✗ did not happen" if rating == 0
            else " ⏳ pending" if status == "pending"
            else " ⚠ unresolved"
        )

        if signal:
            lines.append(f"  {created} ({concern}): \"{signal}\"{accuracy}")
            shown += 1

    # Recurring themes
    themes = _detect_themes(predictions)
    if themes:
        lines.append(f"\nRECURRING THEMES: {', '.join(themes)}")

    # Accuracy summary
    acc_summary = _accuracy_summary(predictions)
    if acc_summary:
        lines.append(f"ACCURACY SO FAR: {acc_summary}")

    return "\n".join(lines)


def _build_diagnostic_block(
    unresolved: dict,
    current_question: str,
    current_concern: str,
) -> str:
    """
    Build the diagnostic instruction block — tells Claude exactly how to
    handle a repeated question after a timing window has passed.
    """
    tw      = unresolved.get("timing_window", "the stated window")
    signal  = unresolved.get("signal_line", "") or (unresolved.get("plain_summary", "") or "")[:100]
    concern = unresolved.get("concern", current_concern)

    return f"""
DIAGNOSTIC MODE ACTIVE — Same domain asked again after window passed.

Previous prediction about {concern}: "{signal}"
Timing window stated: {tw} — has now passed.
User is asking about {concern} again → the predicted outcome did not happen.

YOU MUST ADDRESS THIS DIRECTLY. Structure your response as follows:

1. ACKNOWLEDGE: Reference the previous prediction briefly. Do not pretend it 
   didn't happen. One sentence.

2. DIAGNOSE: Using the current chart data provided, explain WHY the outcome 
   did not happen. Look for: planetary blockages, timing miscalculation, 
   additional hurdles in the chart, karmic patterns (Rin), sleeping planets.
   Be specific — name the planet and house causing the delay.

3. ASSESS: State clearly one of:
   - "The window has EXTENDED — new deadline is [specific date]"
   - "The window has CLOSED — this opportunity is no longer active"  
   - "A NEW window is opening — [specific date/period]"

4. ACTION: Give ONE specific action that is DIFFERENT from what was 
   advised before. If the previous action was "keep applying", do not 
   say "keep applying" again. The situation has changed — the advice must change.

Do NOT give an open-ended answer. Do NOT say "it depends". 
This person came back because they need a clear diagnosis and a new direction.
"""


# ── Helper utilities ──────────────────────────────────────────────────────────

def _format_age(created_at: Optional[str]) -> str:
    """Convert ISO timestamp to human-readable age string."""
    if not created_at:
        return "previously"
    try:
        dt  = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        days  = delta.days
        if days == 0:    return "today"
        if days == 1:    return "yesterday"
        if days < 7:     return f"{days} days ago"
        if days < 30:    return f"{days // 7} week{'s' if days // 7 > 1 else ''} ago"
        if days < 365:   return f"{days // 30} month{'s' if days // 30 > 1 else ''} ago"
        return f"{days // 365} year{'s' if days // 365 > 1 else ''} ago"
    except Exception:
        return "previously"


def _detect_themes(predictions: list) -> list:
    """Detect domains that appear 2+ times = recurring theme."""
    domain_count: dict = {}
    for pred in predictions:
        domains = pred.get("all_domains") or [pred.get("concern", "")]
        for d in domains:
            if d:
                domain_count[d] = domain_count.get(d, 0) + 1

    return [d for d, count in domain_count.items() if count >= 2]


def _accuracy_summary(predictions: list) -> str:
    """Build a short accuracy summary from rated predictions."""
    rated     = [p for p in predictions if p.get("accuracy_rating") is not None]
    confirmed = [p for p in rated if p.get("accuracy_rating") == 1]

    if len(rated) < 2:
        return ""

    pct = round(len(confirmed) / len(rated) * 100)
    return f"{pct}% accurate ({len(confirmed)}/{len(rated)} predictions confirmed by user)"


def _empty_result() -> dict:
    return {
        "memory_block":     "",
        "diagnostic_mode":  False,
        "diagnostic_block": "",
        "unresolved_case":  None,
        "past_predictions": [],
    }
