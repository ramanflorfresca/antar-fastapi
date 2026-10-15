"""
The Home chips ("What is the one thing I should focus on today / this month / this year?") are answered from the SAME calculation Home
already shows, not by a second pipeline.

The daily engine (today) and the period composer (month, year) are the authority: they already use the chart, the running period,
the transits, the Moon's star and place and time. The chip asks a question Home has already answered, so its answer is that result,
word for word: Today's read, Your move and (for the detail) what holds and what breaks. Two methods answering one question was the
bug: Home said "lock the deal in before midday", Ask said "protect what is already moving".

Anything else a person types still goes to the full Ask pipeline. Every function here is pure and fails open: when a field the answer
needs is missing, it returns None and the caller falls back to the full Ask.
"""
from __future__ import annotations

import re
from typing import Optional

# the question text the Home card sends (horizon.py `q_focus`), normalised
_Q = {
    "what is the one thing i should focus on today?": "today",
    "what is the one thing i should focus on this month?": "month",
    "what is the one thing i should focus on this year?": "year",
    "¿en qué debo enfocarme hoy?": "today",
    "¿en qué debo enfocarme este mes?": "month",
    "¿en qué debo enfocarme este año?": "year",
}


def _norm(q) -> str:
    return re.sub(r"\s+", " ", str(q or "").strip().lower())


def chip_scope(question) -> Optional[str]:
    """today | month | year when the question is exactly one of the Home focus chips, else None."""
    return _Q.get(_norm(question))


def _s(x) -> str:
    return re.sub(r"\s+", " ", x).strip() if isinstance(x, str) else ""


def answer_today(daily: dict, language: str = "en") -> Optional[dict]:
    """The Ask-shaped answer for today, from the daily payload's own fields (the ones Home renders)."""
    if not isinstance(daily, dict) or daily.get("pending"):
        return None
    sub, body, move = _s(daily.get("verdict_subline")), _s(daily.get("observa_hoy_text")), _s(daily.get("signal"))
    if not sub or not move:
        return None
    dec = daily.get("decision") if isinstance(daily.get("decision"), dict) else {}
    out = {"mode": "explore", "locked": False, "source": "daily", "chip": "focus_today",
           "read": (sub + " " + body).strip(), "next": move}
    block = {k: _s(dec.get(k)) for k in ("prediction", "holds", "breaks") if _s(dec.get(k))}
    if block:
        block["move"] = move
        out["decision"] = block                       # no `why`: it names houses and periods
    return out


def answer_period(period: dict, scope: str) -> Optional[dict]:
    """The Ask-shaped answer for a month or a year, from the /period composer's own fields."""
    if not isinstance(period, dict) or not _s(period.get("summary")):
        return None
    do = (period.get("do") or [])
    avoid = (period.get("avoid") or [])
    best = period.get("best_week") or period.get("best_month") or {}
    move = _s(do[0].get("text")) if do else ""
    if not move:
        return None
    summary = _s(period["summary"])
    read = summary + (f" {best['title']}: {best['label']}." if best.get("title") and best.get("label") else "")
    out = {"mode": "explore", "locked": False, "source": "period", "chip": f"focus_{scope}", "read": read, "next": move}
    block = {"prediction": summary, "move": move}
    if best.get("label") and best.get("text"):
        block["holds"] = f"{best['title']}: {best['label']}. {best['text']}"
    if avoid:
        a = avoid[0]
        block["breaks"] = _s(a.get("text")) + (f" {_s(a.get('instead'))}" if a.get("instead") else "")
    out["decision"] = block
    return out
