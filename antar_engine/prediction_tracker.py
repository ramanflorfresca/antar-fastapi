"""
antar_engine/prediction_tracker.py

Extracts a trackable claim from each prediction and records
user feedback (yes / partial / no) to build an accuracy score.
"""

import re
import uuid
from datetime import datetime, timedelta, timezone


FEEDBACK_DELAY_DAYS = {
    "finance":      30,
    "career":       21,
    "health":       14,
    "relationship": 21,
    "marriage":     45,
    "legal":        60,
    "foreign":      45,
    "spiritual":    14,
    "daily":         1,
    "general":      21,
}


def extract_trackable_claim(prediction_text: str, concern: str) -> dict:
    """Pull the single most verifiable claim + timing from prediction text."""
    # Try the window/timing section first
    window_match = re.search(
        r"\*\*(?:Your [Ww]indow|[Ww]hen|[Tt]iming|[Pp]eak)[^*]*\*\*\s*\n([^\n*]{20,200})",
        prediction_text,
    )
    answer_match = re.search(
        r"\*\*[^*]+\*\*\s*\n([^\n*]{30,200})",
        prediction_text,
    )

    months = re.findall(
        r"(January|February|March|April|May|June|July|"
        r"August|September|October|November|December)\s+20\d\d",
        prediction_text,
    )
    years = re.findall(r"20\d\d", prediction_text)

    if window_match:
        claim = re.sub(r"\s+", " ", window_match.group(1)).strip()[:200]
    elif answer_match:
        claim = re.sub(r"\s+", " ", answer_match.group(1)).strip()[:200]
    else:
        claim = re.sub(r"\*\*|\*", "", prediction_text[:200]).strip()

    if months:
        window = months[0]
    elif years:
        window = years[0]
    else:
        delay = FEEDBACK_DELAY_DAYS.get(concern, 21)
        window = (datetime.now() + timedelta(days=delay)).strftime("%B %Y")

    delay_days = FEEDBACK_DELAY_DAYS.get(concern, 21)
    show_after = datetime.now(timezone.utc) + timedelta(days=delay_days)

    return {
        "trackable_claim":     claim,
        "claim_window":        window,
        "show_feedback_after": show_after.isoformat(),
    }


def save_trackable_claim(
    chart_id: str,
    prediction_id: str,
    prediction_text: str,
    concern: str,
    sb,
) -> dict:
    """Extract claim and persist to user_correlations."""
    if concern == "daily":
        return {}
    tracking = extract_trackable_claim(prediction_text, concern)
    res = sb.table("user_correlations").insert({
        "chart_id":        chart_id,
        "prediction_id":   prediction_id,
        "trackable_claim": tracking["trackable_claim"],
        "claim_window":    tracking["claim_window"],
        "concern":         concern,
        "show_after":      tracking["show_feedback_after"],
        "feedback_status": "pending",
    }).execute()
    return res.data[0] if res.data else {}


def get_pending_feedback(chart_id: str, sb) -> list:
    """Return up to 3 predictions ready for user verification."""
    now = datetime.now(timezone.utc).isoformat()
    res = (
        sb.table("user_correlations")
        .select("*")
        .eq("chart_id", chart_id)
        .eq("feedback_status", "pending")
        .lte("show_after", now)
        .order("show_after", desc=False)
        .limit(3)
        .execute()
    )
    return res.data or []


def _looks_like_uuid(value) -> bool:
    """True if value parses as a UUID. Distinguishes a real
    user_correlations.id from a frontend pattern-card slug like 'jaimini-0'."""
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def record_feedback(
    correlation_id: str,
    status: str,
    note: str,
    sb,
    chart_id: str = None,
) -> dict:
    """Persist yes / no / partial / skipped feedback.

    correlation_id may be either:
      * a real user_correlations.id (UUID) -> update that row in place. This
        is the existing prediction-tracking flow (rows created by
        save_trackable_claim, surfaced via /pending-feedback).
      * a frontend pattern-card slug, e.g. 'jaimini-0' -> the card is computed
        on the fly and has no pre-existing row, so the first feedback click
        creates a row keyed by (chart_id, correlation_key). The slug is only
        unique within a chart, hence chart_id is required.
    """
    score_map = {"yes": 1.0, "partial": 0.5, "no": 0.0, "skipped": None}
    score = score_map.get(status)
    update = {
        "feedback_status": status,
        "feedback_at":     datetime.now(timezone.utc).isoformat(),
        "feedback_note":   note,
    }
    if score is not None:
        update["accuracy_score"] = score

    # Path 1 -- real UUID id: update the existing row directly.
    if _looks_like_uuid(correlation_id):
        res = sb.table("user_correlations").update(update).eq("id", correlation_id).execute()
        return res.data[0] if res.data else {}

    # Path 2 -- pattern-card slug (e.g. 'jaimini-0'): scope it to the chart and
    # upsert. First click inserts the trackable row, repeat clicks update it.
    if not chart_id:
        raise ValueError(
            "chart_id is required to record feedback for a pattern-card slug"
        )
    row = dict(update)
    row["chart_id"]        = chart_id
    row["correlation_key"] = str(correlation_id)
    res = (
        sb.table("user_correlations")
        .upsert(row, on_conflict="chart_id,correlation_key")
        .execute()
    )
    return res.data[0] if res.data else {}


def get_accuracy_score(chart_id: str, sb) -> dict:
    """Return accuracy summary for this chart."""
    try:
        res = sb.table("prediction_accuracy").select("*").eq("chart_id", chart_id).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass
    return {
        "total_tracked": 0,
        "confirmed":     0,
        "denied":        0,
        "accuracy_pct":  None,
        "message":       "Verify a few predictions to see your accuracy score",
    }
