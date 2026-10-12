"""[daily-loop 2026-10-12] The 3-step daily loop: read today's call, do the practice, ask today's question.

A streak day is counted when all three are done (gamification.touch is still the single writer and stays
same-day idempotent; it is just called from here instead of from /home once the `loop_streak` flag is on).
Days are the user's LOCAL day (tz_offset = minutes east of UTC, same as gamification).

The practice step is done at MANTRA_TARGET (11) mantra repeats, or when a non-mantra practice is completed.
The day's question comes from the same ranked candidates as "Questions for you" (what is active in the chart),
is stored on the day's row so it stays the same all day, and skips a question already used in the last
QUESTION_NO_REPEAT_DAYS loop days, preferring a theme different from yesterday's.

Fail-open contract: every function swallows storage trouble (the table may not exist yet) and returns a
valid, empty-ish loop. A loop problem must never break Home or the Ask."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

STEPS = ("read", "practice", "ask")
MANTRA_TARGET = 11
MANTRA_FULL = 108
MANTRA_MAX = 1080            # a runaway client cannot write a silly number
QUESTION_NO_REPEAT_DAYS = 14
TABLE = "daily_loop_log"
CARRY_OVER_DAYS = 3          # a login streak this fresh is carried into the loop streak, once

# Insight unlocks at streak milestones (decision 1, 2026-10-12): a short personal reading, not points.
# The content is built from existing deterministic readings (see main.py get_daily_loop_unlock).
UNLOCKS = {
    7:   {"id": "hidden_strength", "label": "A hidden strength, in your own words"},
    21:  {"id": "ninety_day", "label": "Your next 90 days"},
    40:  {"id": "chapter_deeper", "label": "The chapter you're in, deeper"},
    108: {"id": "full_reading", "label": "Your full reading"},
}


def unlock_for(streak: int) -> Optional[dict]:
    u = UNLOCKS.get(int(streak or 0))
    return {**u, "at": int(streak)} if u else None


def unlock_list(longest: int) -> List[dict]:
    """Every unlock with whether the user has reached it (by their longest streak)."""
    return [{**u, "at": n, "unlocked": int(longest or 0) >= n} for n, u in sorted(UNLOCKS.items())]


def carry_over(sb, chart_id: str, d: date, user_id=None) -> bool:
    """Once, on a chart's FIRST completed loop: a login streak that was alive within the last
    CARRY_OVER_DAYS days continues instead of resetting (so switching the streak to "finish the loop"
    resets nobody). Done by moving last_active_date to yesterday so gamification.touch sees a consecutive day."""
    try:
        done = (sb.table(TABLE).select("id").eq("chart_id", chart_id).lt("local_date", d.isoformat())
                .not_.is_("completed_at", "null").limit(1).execute().data)
        if done:
            return False
        from antar_engine import gamification as _gam
        uid = user_id or _gam._uid(sb, chart_id)
        if not uid:
            return False
        row = (sb.table("user_streaks").select("current_streak,last_active_date").eq("user_id", uid)
               .limit(1).execute().data or [None])[0]
        if not row or int(row.get("current_streak") or 0) < 1:
            return False
        last = _gam._d(row.get("last_active_date"))
        if not last or (d - last).days > CARRY_OVER_DAYS or last >= d - timedelta(days=1):
            return False
        sb.table("user_streaks").update({"last_active_date": (d - timedelta(days=1)).isoformat()}).eq("user_id", uid).execute()
        return True
    except Exception as e:
        print(f"[daily-loop] carry-over skipped (non-blocking): {e!r}")
        return False


def local_date(tz_offset: int = 0) -> date:
    return (datetime.now(timezone.utc) + timedelta(minutes=int(tz_offset or 0))).date()


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().casefold())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _steps(row: Optional[dict]) -> Dict[str, bool]:
    row = row or {}
    return {"read": bool(row.get("read_at")), "practice": bool(row.get("practice_at")),
            "ask": bool(row.get("ask_at"))}


def get_row(sb, chart_id: str, d: date) -> Optional[dict]:
    try:
        got = (sb.table(TABLE).select("*").eq("chart_id", chart_id)
               .eq("local_date", d.isoformat()).limit(1).execute().data)
        return (got or [None])[0]
    except Exception as e:
        print(f"[daily-loop] read failed (non-blocking): {e!r}")
        return None


def recent_rows(sb, chart_id: str, d: date, days: int = QUESTION_NO_REPEAT_DAYS) -> List[dict]:
    try:
        return (sb.table(TABLE).select("local_date, question_text, question_theme")
                .eq("chart_id", chart_id).gte("local_date", (d - timedelta(days=days)).isoformat())
                .lt("local_date", d.isoformat()).order("local_date", desc=True).execute().data) or []
    except Exception as e:
        print(f"[daily-loop] recent read failed (non-blocking): {e!r}")
        return []


def pick_question(candidates: List[dict], recent: List[dict], today: date) -> Optional[dict]:
    """Deterministic pick from ranked candidates [{id, topic, text, reason, ...}] (best first).
    Skips a text used in the recent loop days; prefers a topic other than yesterday's. Returns the
    candidate plus `next_topic`, the next-ranked topic that is not today's (a hint, never a promise)."""
    cands = [c for c in (candidates or []) if c and c.get("text")]
    if not cands:
        return None
    used = {_norm(r.get("question_text")) for r in (recent or []) if r.get("question_text")}
    fresh = [c for c in cands if _norm(c.get("text")) not in used] or cands
    yday = None
    for r in recent or []:
        try:
            if date.fromisoformat(str(r.get("local_date"))[:10]) == today - timedelta(days=1):
                yday = r.get("question_theme")
        except Exception:
            continue
    chosen = next((c for c in fresh if yday and c.get("topic") != yday), fresh[0])
    nxt = next((c.get("topic") for c in cands if c.get("topic") and c.get("topic") != chosen.get("topic")), None)
    return {**chosen, "next_topic": nxt}


def _save_row(sb, chart_id: str, d: date, fields: dict) -> Optional[dict]:
    """Insert-or-update the day's row. Returns the stored row (or None on trouble)."""
    row = get_row(sb, chart_id, d)
    try:
        if row:
            sb.table(TABLE).update({**fields, "updated_at": _now()}).eq("id", row["id"]).execute()
            return {**row, **fields}
        new = {"chart_id": chart_id, "local_date": d.isoformat(), **fields}
        got = sb.table(TABLE).insert(new).execute().data
        return (got or [new])[0]
    except Exception as e:
        print(f"[daily-loop] write failed (non-blocking): {e!r}")
        return None


def ensure_question(sb, chart_id: str, d: date, candidates: List[dict]) -> Optional[dict]:
    """The day's question: the stored one if there is one, else pick and store it."""
    row = get_row(sb, chart_id, d)
    if row and row.get("question_text"):
        nxt = next((c.get("topic") for c in (candidates or [])
                    if c.get("topic") and c.get("topic") != row.get("question_theme")), None)
        return {"id": row.get("question_id"), "text": row["question_text"], "topic": row.get("question_theme"),
                "reason": next((c.get("reason") for c in (candidates or []) if c.get("text") == row["question_text"]), None),
                "next_topic": nxt}
    q = pick_question(candidates, recent_rows(sb, chart_id, d), d)
    if q:
        _save_row(sb, chart_id, d, {"question_id": q.get("id"), "question_text": q["text"],
                                    "question_theme": q.get("topic")})
    return q


def record_step(sb, chart_id: str, step: str, tz_offset: int = 0, mantra_count: Optional[int] = None,
                other_practice: bool = False, user_id=None) -> dict:
    """Mark one step done for the user's local today. Idempotent. When all three are done for the first
    time, the streak day is counted (gamification.touch) and the result is returned under `streak`."""
    if step not in STEPS:
        return {"ok": False, "reason": "bad_step"}
    d = local_date(tz_offset)
    row = get_row(sb, chart_id, d) or {}
    fields: dict = {}
    if step == "read" and not row.get("read_at"):
        fields["read_at"] = _now()
    elif step == "ask" and not row.get("ask_at"):
        fields["ask_at"] = _now()
    elif step == "practice":
        n = max(0, min(MANTRA_MAX, int(mantra_count or 0)))
        if n > int(row.get("mantra_count") or 0):
            fields["mantra_count"] = n
        best = max(n, int(row.get("mantra_count") or 0))
        if not row.get("practice_at") and (other_practice or best >= MANTRA_TARGET):
            fields["practice_at"] = _now()
    stored = _save_row(sb, chart_id, d, fields) if (fields or not row) else row
    merged = {**row, **(stored or {}), **fields}
    steps = _steps(merged)
    out = {"ok": stored is not None, "local_date": d.isoformat(), "steps": steps,
           "mantra_count": int(merged.get("mantra_count") or 0), "complete": all(steps.values()),
           "just_completed": False, "awards": [], "unlock": None}
    if out["complete"] and not merged.get("completed_at") and stored is not None:
        _save_row(sb, chart_id, d, {"completed_at": _now()})
        out["just_completed"] = True
        try:
            from antar_engine import gamification as _gam
            out["carried_over"] = carry_over(sb, chart_id, d, user_id)
            res = _gam.touch(sb, chart_id, tz_offset or 0, user_id) or {}
            out["awards"] = res.get("awards") or []
            out["unlock"] = unlock_for(res.get("streak"))
            out["streak_counted"] = bool(res.get("changed"))
            out["freeze_used"] = bool(res.get("freeze_used"))
        except Exception as e:
            print(f"[daily-loop] streak touch failed (non-blocking): {e!r}")
    return out


def totals(sb, chart_id: str) -> Dict[str, int]:
    """Lifetime tallies for the streak screen. Each part fails to 0 on its own."""
    t = {"mantra_repeats": 0, "practice_days": 0, "questions_asked": 0}
    days = set()
    try:
        rows = sb.table(TABLE).select("local_date, mantra_count, practice_at").eq("chart_id", chart_id).execute().data or []
        t["mantra_repeats"] = sum(int(r.get("mantra_count") or 0) for r in rows)
        days |= {str(r["local_date"])[:10] for r in rows if r.get("practice_at")}
    except Exception as e:
        print(f"[daily-loop] totals loop skipped: {e!r}")
    try:
        rows = (sb.table("practice_log").select("completed_at").eq("chart_id", chart_id)
                .not_.is_("completed_at", "null").execute().data) or []
        days |= {str(r["completed_at"])[:10] for r in rows if r.get("completed_at")}
    except Exception as e:
        print(f"[daily-loop] totals practice_log skipped: {e!r}")
    t["practice_days"] = len(days)
    try:
        res = sb.table("chat_messages").select("id", count="exact").eq("chart_id", chart_id).limit(1).execute()
        t["questions_asked"] = int(getattr(res, "count", 0) or 0)
    except Exception as e:
        print(f"[daily-loop] totals asks skipped: {e!r}")
    return t
