"""[day-strip 2026-10-15] The 7 days back / today / 7 days ahead strip for "Today in detail".

Every day is shaped from the SAME deterministic input the Today card already trusts: the day's score
(daily_v2.day_energy: friction < 4, steady >= 7, else light). No LLM text and no saved prose, so a day's chip can never
contradict the card for that day, and the strip agrees with /daily-week by construction.

Past days are RE-READ from the chart for that date (the saved daily cache only holds days warmed ahead of time, so most
past days were never stored). They say so (`source: "recomputed"`): honest, never presented as something we told the
user at the time."""
from __future__ import annotations

from datetime import date as _date, timedelta as _td
from typing import Optional

from antar_engine.daily_v2 import day_energy as _day_energy

VERSION = "day-strip-1"
DAYS_BACK = 7
DAYS_AHEAD = 7


def _d(x) -> Optional[_date]:
    try:
        return _date.fromisoformat(str(x)[:10])
    except Exception:
        return None


def build_strip(days: list, today: _date, language: str = "en") -> dict:
    """days: engine day dicts (need `date` and `score`). Returns the strip; days with no usable date/score are left out."""
    lang = (language or "en").split("-")[0].lower()
    by_date = {}
    for raw in days or []:
        dt = _d((raw or {}).get("date"))
        if dt is not None and raw.get("score") is not None:
            by_date[dt] = raw
    out = []
    for off in range(-DAYS_BACK, DAYS_AHEAD + 1):
        dt = today + _td(days=off)
        raw = by_date.get(dt)
        if raw is None:
            out.append({"date": dt.isoformat(), "offset": off,
                        "kind": "today" if off == 0 else ("past" if off < 0 else "future"), "status": "no_reading"})
            continue
        de = _day_energy(raw, lang)
        out.append({"date": dt.isoformat(), "weekday": dt.strftime("%a"), "offset": off,
                    "kind": "today" if off == 0 else ("past" if off < 0 else "future"),
                    "status": "ready", "energy": {"key": de["key"], "label": de["label"], "tone": de["tone"]},
                    "score": de["score"], "source": "recomputed" if off < 0 else "live"})
    ahead = [x for x in out if x["kind"] == "future" and x["status"] == "ready"]
    return {"date": today.isoformat(), "language": lang, "days": out,
            "best_ahead": (max(ahead, key=lambda x: x["score"])["date"] if ahead else None),
            "care_ahead": (min(ahead, key=lambda x: x["score"])["date"] if ahead else None),
            "version": VERSION}
