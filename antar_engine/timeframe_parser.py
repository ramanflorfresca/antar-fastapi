"""
antar_engine/timeframe_parser.py
─────────────────────────────────
WS1 Layer 0 — parse the asked question (+ prior conversation_history)
into a concrete timeframe + target_date in the user's local day.

WHY THIS EXISTS:
  /predict was returning a today read for tomorrow questions because
  the engine scored "now", produced today's intraday window, and
  phrased the conclusion in today's tense regardless of what the user
  actually asked. This module is the explicit Layer 0 step that maps
  "tomorrow" / "this week" / "on the 14th" / a bare elliptical
  "Tomorrow?" follow-up into the concrete scoring anchor the rest of
  the engine threads through.

PUBLIC CONTRACT — parse_timeframe() returns a dict:

    {
      "kind":            one of TF_KIND_* below,
      "target_date_utc": datetime,   # the day we score (UTC)
      "window_start":    datetime,   # UTC window start
      "window_end":      datetime,   # UTC window end (inclusive day)
      "label_en":        "today" | "tomorrow" | "this week" | ...,
      "label_es":        "hoy"   | "mañana"   | "esta semana" | ...,
      "is_tactical":     bool,        # today/now/tomorrow → True
      "horizon_days":    int,         # 1 / 7 / 31 / 366 / 0
      "elliptical":      bool,        # we resolved from history
    }

INVARIANTS:
  - Never raises. Every failure path returns the TF_KIND_NONE default,
    which the resolver already handles as "general status of area".
  - Pure function. No LLM. No network. No DB.
  - tz_offset_hours is in HOURS (matches charts.tz_offset on
    /predict's chart_record, which is read as `float(tz_offset)`).
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import re

# ─────────────────────────────────────────────────────────────────────
# Kind constants
# ─────────────────────────────────────────────────────────────────────

TF_KIND_TODAY         = "today"
TF_KIND_NOW           = "now"
TF_KIND_TOMORROW      = "tomorrow"
TF_KIND_THIS_WEEK     = "this_week"
TF_KIND_THIS_MONTH    = "this_month"
TF_KIND_THIS_YEAR     = "this_year"
TF_KIND_EXPLICIT_DATE = "explicit_date"
TF_KIND_WHEN          = "when"
TF_KIND_NONE          = "none"

# Tactical = answer must reference the asked single day, not a horizon.
TACTICAL_KINDS = {TF_KIND_TODAY, TF_KIND_NOW, TF_KIND_TOMORROW, TF_KIND_EXPLICIT_DATE}

# Non-today kinds that the leakage guard must scrub today-framing from.
NON_TODAY_KINDS = {
    TF_KIND_TOMORROW, TF_KIND_THIS_WEEK, TF_KIND_THIS_MONTH,
    TF_KIND_THIS_YEAR, TF_KIND_EXPLICIT_DATE,
}


# ─────────────────────────────────────────────────────────────────────
# Marker tables
# Order matters — most specific first. Spanish + English in one pass.
# ─────────────────────────────────────────────────────────────────────

_MARKERS: List[tuple] = [
    (TF_KIND_NOW, [
        "right now", "this very moment", "at this moment",
        "in this moment", "this minute", "now?", " now.", " now,",
        "ahora mismo", "en este instante", "en este momento",
    ]),
    (TF_KIND_TOMORROW, [
        "tomorrow", "tomorrow's", "by tomorrow", "for tomorrow",
        "next day", "mañana", "manana",
    ]),
    (TF_KIND_TODAY, [
        "today", "tonight", "this morning", "this afternoon",
        "this evening", "today's", "for today", "this hour",
        "hoy", "esta tarde", "esta noche", "esta mañana",
    ]),
    (TF_KIND_THIS_WEEK, [
        "this week", "the next 7 days", "the next seven days",
        "the coming week", "next week",
        "esta semana", "la próxima semana", "la proxima semana",
    ]),
    (TF_KIND_THIS_MONTH, [
        "this month", "the next 30 days", "the next month",
        "next month",
        "este mes", "el próximo mes", "el proximo mes",
    ]),
    (TF_KIND_THIS_YEAR, [
        "this year", "the next 12 months", "in 2026", "in 2027",
        "este año", "el próximo año", "el proximo ano",
    ]),
    (TF_KIND_WHEN, [
        "when will", "when can", "when do", "when does", "when is",
        "what year", "which year", "by when",
        "cuándo voy", "cuando voy", "cuándo será", "cuando sera",
        "en qué año", "en que año",
    ]),
]

# Bare-token / elliptical follow-ups. If the question is a fragment
# AND matches one of these tokens we infer it carries the timeframe
# forward applied to the prior turn's concern.
_ELLIPTICAL_TOKENS = {
    "tomorrow":     TF_KIND_TOMORROW,
    "tomorrow?":    TF_KIND_TOMORROW,
    "mañana":       TF_KIND_TOMORROW,
    "manana":       TF_KIND_TOMORROW,
    "mañana?":      TF_KIND_TOMORROW,
    "today":        TF_KIND_TODAY,
    "today?":       TF_KIND_TODAY,
    "hoy":          TF_KIND_TODAY,
    "hoy?":         TF_KIND_TODAY,
    "now":          TF_KIND_NOW,
    "now?":         TF_KIND_NOW,
    "ahora":        TF_KIND_NOW,
    "ahora?":       TF_KIND_NOW,
    "next week":    TF_KIND_THIS_WEEK,
    "this week":    TF_KIND_THIS_WEEK,
    "this week?":   TF_KIND_THIS_WEEK,
    "next month":   TF_KIND_THIS_MONTH,
    "this month":   TF_KIND_THIS_MONTH,
    "next year":    TF_KIND_THIS_YEAR,
    "this year":    TF_KIND_THIS_YEAR,
}

_LABELS_EN = {
    TF_KIND_TODAY:         "today",
    TF_KIND_NOW:           "right now",
    TF_KIND_TOMORROW:      "tomorrow",
    TF_KIND_THIS_WEEK:     "this week",
    TF_KIND_THIS_MONTH:    "this month",
    TF_KIND_THIS_YEAR:     "this year",
    TF_KIND_EXPLICIT_DATE: "on that date",
    TF_KIND_WHEN:          "ahead",
    TF_KIND_NONE:          "",
}

_LABELS_ES = {
    TF_KIND_TODAY:         "hoy",
    TF_KIND_NOW:           "ahora mismo",
    TF_KIND_TOMORROW:      "mañana",
    TF_KIND_THIS_WEEK:     "esta semana",
    TF_KIND_THIS_MONTH:    "este mes",
    TF_KIND_THIS_YEAR:     "este año",
    TF_KIND_EXPLICIT_DATE: "en esa fecha",
    TF_KIND_WHEN:          "más adelante",
    TF_KIND_NONE:          "",
}

_HORIZON_DAYS = {
    TF_KIND_TODAY:         1,
    TF_KIND_NOW:           1,
    TF_KIND_TOMORROW:      1,
    TF_KIND_THIS_WEEK:     7,
    TF_KIND_THIS_MONTH:    31,
    TF_KIND_THIS_YEAR:     366,
    TF_KIND_EXPLICIT_DATE: 1,
    TF_KIND_WHEN:          366,
    TF_KIND_NONE:          0,
}

# Explicit-date regex — matches "January 14", "Jan 14", "the 14th",
# "on the 14th", "14th of January", ISO "2026-06-14". Conservative —
# only fires when there is enough signal to be unambiguous.
_MONTHS = (
    "january|february|march|april|may|june|july|august|"
    "september|october|november|december|"
    "enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    "septiembre|octubre|noviembre|diciembre"
)
_RE_ISO_DATE   = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_RE_MONTH_DAY  = re.compile(rf"\b({_MONTHS})\s+(\d{{1,2}})\b", re.I)
_RE_ON_THE_DAY = re.compile(r"\bon\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\b", re.I)
_RE_NEXT_DOW   = re.compile(
    r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.I,
)
_DOW_INDEX = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


# ─────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────

def _normalise(q: Optional[str]) -> str:
    return (q or "").strip().lower()


def _local_now(now_utc: datetime, tz_offset_hours: float) -> datetime:
    return now_utc + timedelta(hours=float(tz_offset_hours or 0.0))


def _local_to_utc(local_dt: datetime, tz_offset_hours: float) -> datetime:
    return local_dt - timedelta(hours=float(tz_offset_hours or 0.0))


def _midday_local(local_date_anchor: datetime) -> datetime:
    """Midday on the asked local date — chosen so the scoring date is
    unambiguous regardless of tz wrap-around at midnight boundaries."""
    return datetime(
        local_date_anchor.year, local_date_anchor.month,
        local_date_anchor.day, 12, 0, 0,
    )


def _match_marker(q: str) -> Optional[str]:
    """Scan _MARKERS in order, return first matched TF_KIND_*."""
    for kind, markers in _MARKERS:
        for m in markers:
            if m in q:
                return kind
    return None


def _match_explicit_date(
    q: str, local_now: datetime
) -> Optional[datetime]:
    """Return a local datetime midday for an explicit date mentioned
    in the question, or None when none is present."""
    # ISO
    m = _RE_ISO_DATE.search(q)
    if m:
        try:
            yr, mo, dy = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return datetime(yr, mo, dy, 12, 0, 0)
        except Exception:
            pass
    # Month + day
    m = _RE_MONTH_DAY.search(q)
    if m:
        month_name = m.group(1).lower()
        try:
            day = int(m.group(2))
            month_idx = (
                "january|february|march|april|may|june|july|august|"
                "september|october|november|december"
            ).split("|").index(month_name) + 1 if month_name in (
                "january february march april may june july "
                "august september october november december"
            ).split() else None
            if month_idx is None:
                _es = "enero febrero marzo abril mayo junio julio agosto " \
                      "septiembre octubre noviembre diciembre".split()
                if month_name in _es:
                    month_idx = _es.index(month_name) + 1
            if month_idx and 1 <= day <= 31:
                yr = local_now.year
                cand = datetime(yr, month_idx, day, 12, 0, 0)
                # If the candidate is more than 30 days in the past,
                # bump to next year.
                if (local_now - cand).days > 30:
                    cand = datetime(yr + 1, month_idx, day, 12, 0, 0)
                return cand
        except Exception:
            pass
    # Next <day-of-week>
    m = _RE_NEXT_DOW.search(q)
    if m:
        dow = _DOW_INDEX.get(m.group(1).lower())
        if dow is not None:
            today_dow = local_now.weekday()
            delta = (dow - today_dow) % 7
            if delta == 0:
                delta = 7
            anchor = local_now + timedelta(days=delta)
            return _midday_local(anchor)
    # "on the 14th" — only when there is no other timeframe marker.
    m = _RE_ON_THE_DAY.search(q)
    if m:
        try:
            day = int(m.group(1))
            if 1 <= day <= 31:
                # Same month if the day is in the future; otherwise next month.
                yr = local_now.year
                mo = local_now.month
                if day < local_now.day:
                    if mo == 12:
                        mo, yr = 1, yr + 1
                    else:
                        mo += 1
                return datetime(yr, mo, day, 12, 0, 0)
        except Exception:
            pass
    return None


def _last_user_concern_text_from_history(
    history: Optional[List[Dict[str, str]]]
) -> str:
    """Return the most recent prior user message text (excluding the
    current turn, which is passed separately as `question`)."""
    if not history:
        return ""
    user_turns: List[str] = []
    for turn in history:
        try:
            if (turn.get("role") or "").lower() == "user":
                t = (turn.get("content") or "").strip()
                if t:
                    user_turns.append(t)
        except Exception:
            continue
    return user_turns[-1] if user_turns else ""


# ─────────────────────────────────────────────────────────────────────
# Public entry — parse_timeframe()
# ─────────────────────────────────────────────────────────────────────

def parse_timeframe(
    question: Optional[str],
    history: Optional[List[Dict[str, str]]] = None,
    tz_offset_hours: float = 0.0,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Return the TimeframeContext dict for this question. Never
    raises — failures return TF_KIND_NONE with target_date = today
    so the resolver answers the general status of the area."""

    now_utc = now_utc or datetime.utcnow()
    local_now = _local_now(now_utc, tz_offset_hours)
    today_local = _midday_local(local_now)

    def _build(
        kind: str,
        target_local: datetime,
        window_start_local: datetime,
        window_end_local: datetime,
        elliptical: bool = False,
    ) -> Dict[str, Any]:
        return {
            "kind":            kind,
            "target_date_utc": _local_to_utc(target_local, tz_offset_hours),
            "window_start":    _local_to_utc(window_start_local, tz_offset_hours),
            "window_end":      _local_to_utc(window_end_local, tz_offset_hours),
            "label_en":        _LABELS_EN.get(kind, ""),
            "label_es":        _LABELS_ES.get(kind, ""),
            "is_tactical":     kind in TACTICAL_KINDS,
            "horizon_days":    _HORIZON_DAYS.get(kind, 0),
            "elliptical":      elliptical,
        }

    q = _normalise(question)
    if not q:
        return _build(TF_KIND_NONE, today_local, today_local, today_local)

    # 1) Elliptical follow-up — short fragment that IS a timeframe.
    #    Only triggers when the entire normalised question is one of
    #    the bare tokens (or that token + trailing punctuation).
    bare = q.strip(" .!?,;:")
    if bare in _ELLIPTICAL_TOKENS:
        kind = _ELLIPTICAL_TOKENS[bare]
        if kind == TF_KIND_TOMORROW:
            anchor = today_local + timedelta(days=1)
            return _build(kind, anchor, anchor, anchor, elliptical=True)
        if kind == TF_KIND_TODAY:
            return _build(kind, today_local, today_local, today_local, elliptical=True)
        if kind == TF_KIND_NOW:
            return _build(kind, today_local, today_local, today_local, elliptical=True)
        if kind == TF_KIND_THIS_WEEK:
            return _build(
                kind, today_local, today_local,
                today_local + timedelta(days=7), elliptical=True,
            )
        if kind == TF_KIND_THIS_MONTH:
            return _build(
                kind, today_local, today_local,
                today_local + timedelta(days=31), elliptical=True,
            )
        if kind == TF_KIND_THIS_YEAR:
            return _build(
                kind, today_local, today_local,
                today_local + timedelta(days=366), elliptical=True,
            )

    # 2) Explicit date (highest-precision signal in a full question).
    explicit = _match_explicit_date(q, local_now)
    if explicit is not None:
        return _build(
            TF_KIND_EXPLICIT_DATE, explicit, explicit, explicit,
        )

    # 3) Phrase markers — ordered most specific first.
    kind = _match_marker(q)
    if kind == TF_KIND_TOMORROW:
        anchor = today_local + timedelta(days=1)
        return _build(kind, anchor, anchor, anchor)
    if kind in (TF_KIND_TODAY, TF_KIND_NOW):
        return _build(kind, today_local, today_local, today_local)
    if kind == TF_KIND_THIS_WEEK:
        return _build(kind, today_local, today_local, today_local + timedelta(days=7))
    if kind == TF_KIND_THIS_MONTH:
        return _build(kind, today_local, today_local, today_local + timedelta(days=31))
    if kind == TF_KIND_THIS_YEAR:
        return _build(kind, today_local, today_local, today_local + timedelta(days=366))
    if kind == TF_KIND_WHEN:
        return _build(kind, today_local, today_local, today_local + timedelta(days=366))

    # 4) Nothing matched — return NONE, anchored on today.
    return _build(TF_KIND_NONE, today_local, today_local, today_local)


# ─────────────────────────────────────────────────────────────────────
# Public entry — resolve_effective_concern()
# Walk the conversation_history when the new question is so short the
# concern detector returns "general". This is the doctrinal handling
# for elliptical follow-ups like a bare "Tomorrow?" after a prior
# speculation turn.
# ─────────────────────────────────────────────────────────────────────

def resolve_effective_concern(
    current_question: Optional[str],
    current_concern: Optional[str],
    history: Optional[List[Dict[str, str]]],
    detect_fn,
) -> str:
    """If current_concern is "general" / empty AND the new question is
    a short fragment, walk back through history's user turns and
    return the most recent non-general concern. Otherwise return
    current_concern unchanged."""
    cc = (current_concern or "").strip().lower()
    q = _normalise(current_question)

    is_short = bool(q) and (len(q) <= 40 or len(q.split()) <= 5)
    if cc and cc != "general":
        return current_concern  # already concrete
    if not is_short:
        return current_concern or "general"

    if not history or detect_fn is None:
        return current_concern or "general"

    # Walk newest-first.
    user_msgs = [
        (turn.get("content") or "")
        for turn in reversed(history)
        if (turn.get("role") or "").lower() == "user"
    ]
    for txt in user_msgs:
        try:
            c = detect_fn(txt) or ""
            c_l = c.strip().lower()
            if c_l and c_l != "general":
                return c
        except Exception:
            continue
    return current_concern or "general"
