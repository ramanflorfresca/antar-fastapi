"""
Profile gaps — what we still need to ask before we can read precisely.

[profile-gaps 2026-07-20]

The product's model was: collect once at onboarding, then predict forever. That
fails in two directions. Charts created before a question existed never get
asked at all (which is why the founder's own marital status sat empty for
months while the engine talked about his spouse), and circumstances change --
a divorce or a new child silently leaves a stale fact steering every reading.

An astrologer does not do this. They ask what they need for the question in
front of them, and they ask because the answer changes the reading.

So this module answers one question: given this chart, what is missing that
would MATERIALLY change what we say? Two rules keep it from becoming a form:

  1. Never ask for something we already know, from EITHER column family
     (life_* from onboarding, patra from the profile card).
  2. Never ask just because a field is null. Every gap here has to earn its
     place by changing a reading -- which is why birth-time accuracy is only
     raised when the chart is genuinely near a cusp. A chart sitting mid-sign
     does not need the question, so it is not asked.

Ordered by how much precision the answer buys, not by how easy it is to ask.
"""

from __future__ import annotations

from typing import Optional

from antar_engine.life_context import resolve_life_facts
from antar_engine.birth_time_confidence import assess_chart_row

# Highest first. Birth time leads because it is the only gap that can invert
# EVERY house-based claim at once -- no amount of life context repairs a chart
# whose ascendant is in the wrong sign.
_ORDER = ["birth_time_accuracy", "marital_status", "children_status",
          "career_stage", "current_city"]

_GAP_COPY = {
    "birth_time_accuracy": {
        "question": "How sure are you of your birth time?",
        "why": "Your ascendant is close to a sign boundary. A small difference "
               "here changes which house every planet falls in.",
        "options": [
            {"value": "exact",       "label": "Exact — from a certificate or record"},
            {"value": "approximate", "label": "Approximate — roughly this time"},
            {"value": "unknown",     "label": "I don't know my birth time"},
        ],
    },
    "marital_status": {
        "question": "What's your relationship status?",
        "why": "So readings about partnership describe your actual situation.",
        "options": [
            {"value": "single",          "label": "Single"},
            {"value": "in_relationship", "label": "In a relationship"},
            {"value": "married",         "label": "Married"},
            {"value": "separated",       "label": "Separated"},
            {"value": "divorced",        "label": "Divorced"},
            {"value": "widowed",         "label": "Widowed"},
        ],
    },
    "children_status": {
        "question": "Do you have children?",
        "why": "The 5th house covers children and creative work — knowing which "
               "applies to you keeps that reading concrete.",
        "options": [
            {"value": "no_children", "label": "No children"},
            {"value": "expecting",   "label": "Expecting"},
            {"value": "has_children","label": "Yes, I have children"},
        ],
    },
    "career_stage": {
        "question": "Where are you in your working life?",
        "why": "Running your own business and holding a job read very "
               "differently in the same chart.",
        "options": [
            {"value": "student",      "label": "Studying"},
            {"value": "early_career", "label": "Early career"},
            {"value": "mid_career",   "label": "Established"},
            {"value": "entrepreneur", "label": "Running my own business"},
            {"value": "between_jobs", "label": "Between things"},
            {"value": "retired",      "label": "Retired"},
        ],
    },
    "current_city": {
        "question": "Which city do you live in now?",
        "why": "Timing is calculated for where you actually are, not where you "
               "were born.",
        "options": None,  # free text + geocode
    },
}


def _has(row: dict, *cols: str) -> bool:
    """True when any of `cols` holds a real value. Guards the placeholder
    strings the app has historically written for "not answered" — treating
    'unknown' as an answer is how a gap silently stops being asked."""
    for c in cols:
        v = row.get(c)
        if v is None:
            continue
        s = str(v).strip().lower()
        if s and s not in ("unknown", "none", "null", "not_sure", "no_children_unsure"):
            return True
    return False


def find_gaps(row: Optional[dict], limit: int = 2) -> list[dict]:
    """Return the highest-value missing facts for this chart.

    `limit` is deliberately small. The point is a nudge attached to a reading,
    not an interrogation — asking for six things at once is how you train
    someone to dismiss the card forever.
    """
    if not row:
        return []

    missing: list[str] = []

    # Birth time: only worth raising when the chart is actually near a cusp.
    if not _has(row, "birth_time_accuracy"):
        try:
            a = assess_chart_row(row)
            if a and a.get("house_risk") in ("unknown", "high", "critical"):
                missing.append("birth_time_accuracy")
        except Exception:
            pass  # never let the ephemeris block the rest of the gaps

    # Life facts: resolve_life_facts already reads BOTH column families, so a
    # user who answered at onboarding is never asked again via the patra card.
    life = None
    try:
        life = resolve_life_facts(row)
    except Exception:
        life = None
    if not (life and life.get("marital") is not None):
        missing.append("marital_status")
    if not (life and life.get("children") is not None):
        missing.append("children_status")

    if not _has(row, "career_stage", "life_work"):
        missing.append("career_stage")
    if not _has(row, "current_city"):
        missing.append("current_city")

    ordered = [k for k in _ORDER if k in missing]
    out = []
    for k in ordered[: max(0, limit)]:
        c = _GAP_COPY[k]
        out.append({
            "field":    k,
            "question": c["question"],
            "why":      c["why"],
            "options":  c["options"],
        })
    return out


def gap_summary(row: Optional[dict]) -> dict:
    """Everything a caller needs to decide whether to show a prompt."""
    gaps = find_gaps(row, limit=99)
    return {
        "gaps":        find_gaps(row, limit=2),
        "total_gaps":  len(gaps),
        "all_fields":  [g["field"] for g in gaps],
        "complete":    not gaps,
    }
