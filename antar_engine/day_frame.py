"""
antar_engine/day_frame.py

[frame-contract 2026-07-24] ONE deterministic orientation for the day, shared by
the two independent LLM calls that write the daily card.

The card used to state a thesis and then contradict it. Narration opened with
"a rare nodal return is active — today asks you to notice what is COMPLETING,
not what is starting", and the action block directly beneath it said: step into
the pitch, open the strained conversation, chase what you're owed. All three are
STARTING things.

The cause is architectural, not a writing failure. headline/highlight come from
today_narration.build_narration_system(); haz_hoy/evita_hoy come from the signal
call in daily_prediction_engine. Two prompts, no shared input — so each invented
its own frame. Narration also runs AFTER the actions already exist, so the frame
cannot simply be handed downstream.

The fix is to derive the orientation from the chart's own arithmetic BEFORE
either call, and hand the same constraint to both. Neither writer invents a
frame; they agree by construction. No reordering, no extra LLM call, no added
latency.

"open" is the default and imposes NOTHING. A day the chart does not decisively
mark reads exactly as it does today — this only binds the days that have earned
a frame.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

# Rarity signal types that mean "something is ending / coming full circle".
# Returns are the whole point: a Saturn or nodal return is the closing of a
# cycle that opened one full revolution ago.
_COMPLETING_TYPES = {
    "saturn_return",
    "jupiter_return",
    "rahu_ketu_return",
    "dasha_sandhi_ending",
}
# Age milestones are life-stage junctions; only the two that are explicitly
# described as completions count (see _detect_age_milestones' own copy).
_COMPLETING_AGE_PREFIXES = ("age_milestone_rahu_ketu", "age_milestone_saturn")

# Deliberately narrow. A new period genuinely opening is the only thing that
# earns "starting"; anything vaguer leaves the day open rather than mislabelling
# it, because a wrong frame is worse than no frame.
_STARTING_TYPES = {"dasha_sandhi_opening"}

# How close to a period's edge counts as its opening / closing stretch.
# Scale-free on purpose: antardashas run from weeks to years, so a fixed number
# of days would mean something different in each.
_EDGE_FRACTION = 0.10

_LEVELS_ANTARDASHA = ("antardasha", "bhukti")


def _as_rows(dashas: Any) -> List[dict]:
    """The vimsottari rows out of whatever shape the caller has."""
    if isinstance(dashas, dict):
        rows = dashas.get("vimsottari") or []
    else:
        rows = dashas or []
    return [r for r in rows if isinstance(r, dict)]


def _running_antardasha(dashas: Any, now: datetime) -> Optional[dict]:
    """The antardasha covering `now`, with parsed dates, or None."""
    for r in _as_rows(dashas):
        if (r.get("level") or "").lower() not in _LEVELS_ANTARDASHA:
            continue
        try:
            sd = datetime.strptime(str(r.get("start_date", ""))[:10], "%Y-%m-%d")
            ed = datetime.strptime(str(r.get("end_date", ""))[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            continue
        if sd <= now <= ed and ed > sd:
            return {"start": sd, "end": ed}
    return None


def _rarity_orientation(rarity_signals: Any) -> str:
    """Orientation implied by the active rarity signals, or ''."""
    for s in (rarity_signals or []):
        if not isinstance(s, dict):
            continue
        t = str(s.get("type") or "")
        if t in _COMPLETING_TYPES or t.startswith(_COMPLETING_AGE_PREFIXES):
            return "completing"
        if t in _STARTING_TYPES:
            return "starting"
    return ""


def resolve_day_frame(
    rarity_signals: Any = None,
    dashas: Any = None,
    now: Optional[datetime] = None,
) -> Dict[str, str]:
    """{orientation, reason, source} — the day's binding frame.

    orientation: "completing" | "starting" | "open"

    Precedence: a rarity signal outranks dasha position. A Saturn return is a
    louder statement about the shape of the day than being 92% of the way
    through an antardasha, and when both fire they usually agree anyway.
    """
    now = now or datetime.utcnow()

    orient = _rarity_orientation(rarity_signals)
    if orient:
        return {
            "orientation": orient,
            "reason": "a rare cycle-level signal is active",
            "source": "rarity",
        }

    ad = _running_antardasha(dashas, now)
    if ad:
        span = (ad["end"] - ad["start"]).total_seconds()
        if span > 0:
            elapsed = (now - ad["start"]).total_seconds() / span
            if elapsed >= 1.0 - _EDGE_FRACTION:
                return {
                    "orientation": "completing",
                    "reason": "the running sub-period is in its final stretch",
                    "source": "dasha",
                }
            if elapsed <= _EDGE_FRACTION:
                return {
                    "orientation": "starting",
                    "reason": "the running sub-period has just opened",
                    "source": "dasha",
                }

    return {"orientation": "open", "reason": "", "source": "none"}


# ── Prompt constraint ───────────────────────────────────────────────────────
# Written as a binding instruction, not a hint. Both prompts receive the same
# text, so "the frame" means the same thing to the narrator and to the action
# writer. Domains are untouched — only the VERB changes.
# [silent-frame 2026-07-27] These are SILENT shaping rules, not content. A prior
# version let the model verbalize the framing — a live card opened with "A rare
# nodal return is active… notice what is completing, not what is starting," which
# is meta-narration plus an invented astronomy claim. The frame must only bend
# the VERBS of the actions; the reader must never see the framing named.
_SILENT_RULE = (
    "- SILENT RULE (critical): NEVER state or hint at this framing. Do not write\n"
    "  'completing', 'closing', 'coming full circle', 'a new cycle', 'ending',\n"
    "  'a chapter', or any cosmic/astronomical reason (no 'return', 'cycle',\n"
    "  'nodal', 'phase', 'the stars/energy/universe', no 'once every N years').\n"
    "  Apply this ONLY by choosing the verb of each concrete action. If you\n"
    "  cannot phrase an action without naming the framing, write a plainer action.\n"
)
_CONSTRAINT = {
    "completing": (
        "## DAY SHAPING — lean toward finishing (silent)\n"
        "Shape today's concrete actions toward completing what already exists.\n"
        "- Actions are about finishing, collecting, closing, repairing, or\n"
        "  releasing something ALREADY in motion — not new launches.\n"
        "- Keep the same life domains — change only the verb. Not 'make the\n"
        "  pitch' but 'follow up on the pitch you already made'; not 'chase new\n"
        "  income' but 'collect what you're already owed'.\n"
        + _SILENT_RULE
    ),
    "starting": (
        "## DAY SHAPING — lean toward initiating (silent)\n"
        "Shape today's concrete actions toward first moves on something new.\n"
        "- Actions are about initiating, proposing, or reaching out.\n"
        "- Keep the same life domains — change only the verb.\n"
        + _SILENT_RULE
    ),
}


def frame_constraint_block(frame: Any) -> str:
    """The prompt text for this frame. '' for an open day, which binds nothing."""
    if not isinstance(frame, dict):
        return ""
    return _CONSTRAINT.get(str(frame.get("orientation") or ""), "")
