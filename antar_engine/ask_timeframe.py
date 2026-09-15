"""
antar_engine/ask_timeframe.py

[ask-timeframe 2026-09-15] Time-scope reads for /ask so day/window questions
answer like a real astrologer instead of collapsing to a single "today" verdict.

Two capabilities:
  1. detect_horizon(question) — parse the time scope the user actually asked for
     (today, tomorrow, today-or-tomorrow, this/next week, this/next month, or a
     bounded window like "which day in the next 45 to 90 days").
  2. score_day_for_concern(...) — a cheap per-day directional signal for a concern
     on ANY date, from that day's panchanga (Moon sign/nakshatra/weekday) + the
     Moon's transit house vs the concern's houses. Cheap enough to scan ~90 days.

Composition of these into the final read is done by the caller (/ask), which
feeds the facts to the narrator so the voice stays consistent.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# question vocabulary → a CONCERN_MAP key (places_concern)
_CONCERN_ALIAS = {
    "speculation": "money", "speculate": "money", "investment": "money",
    "invest": "money", "investing": "money", "trading": "money", "trade": "money",
    "stocks": "money", "stock": "money", "gambling": "money", "bet": "money",
    "lottery": "money", "wealth": "money", "finance": "money", "financial": "money",
    "funding": "money", "income": "money", "money": "money",
    "business": "business", "startup": "business", "venture": "business",
    "job": "career", "work": "career", "career": "career", "promotion": "career",
    "relationship": "love", "romance": "love", "marriage": "love",
    "partner": "love", "love": "love", "dating": "love",
    "health": "health", "peace": "peace", "family": "family",
}


def _concern_houses(concern: str):
    """(favorable_houses, caution_houses) for a concern, via places_concern."""
    try:
        from antar_engine.places_concern import CONCERN_MAP
    except Exception:
        return {1}, set()
    c = _CONCERN_ALIAS.get((concern or "").lower(), (concern or "").lower())
    cfg = CONCERN_MAP.get(c)
    if not cfg:
        return {1}, set()
    return set(cfg.get("houses") or [1]), set(cfg.get("neg_houses") or [])


def detect_horizon(question: str, today: Optional[date] = None) -> Optional[dict]:
    """Return a horizon spec, or None when the question has no day/window scope
    (so the caller keeps its normal behavior). Specs:
      {"kind":"days", "days":[date,...], "label":str}
      {"kind":"window", "start":date, "end":date, "scan":bool, "label":str,
       "month":bool}
    `scan`=True means "find the best day(s) in the window" (which-day / when).
    """
    q = (question or "").lower()
    today = today or date.today()

    has_today = bool(re.search(r"\btoday\b|\bright now\b|\btonight\b", q))
    has_tom = bool(re.search(r"\btomorrow\b", q))
    wants_day = bool(re.search(r"\b(which|what)\s+day\b|\bbest\s+day\b|\bwhen\b|"
                               r"\bwhat\s+time\b|\bwhich\s+time\b", q))

    # ── enumerable days ─────────────────────────────────────────────────────
    if has_today and has_tom:
        return {"kind": "days", "days": [today, today + timedelta(days=1)],
                "label": "today and tomorrow"}
    if has_tom:
        return {"kind": "days", "days": [today + timedelta(days=1)], "label": "tomorrow"}
    if has_today:
        return {"kind": "days", "days": [today], "label": "today"}

    # ── explicit bounded windows ("next 45 to 90 days", "next 30 days") ──────
    m_rng = re.search(r"next\s+(\d+)\s*(?:to|-|–|and)\s*(\d+)\s*(day|week|month)", q)
    if m_rng:
        a, b, unit = int(m_rng.group(1)), int(m_rng.group(2)), m_rng.group(3)
        mult = {"day": 1, "week": 7, "month": 30}[unit]
        return {"kind": "window", "start": today + timedelta(days=a * mult),
                "end": today + timedelta(days=b * mult), "scan": True,
                "label": f"the next {a}–{b} {unit}s"}
    m_n = re.search(r"next\s+(\d+)\s*(day|week|month)", q)
    if m_n:
        n, unit = int(m_n.group(1)), m_n.group(2)
        mult = {"day": 1, "week": 7, "month": 30}[unit]
        return {"kind": "window", "start": today, "end": today + timedelta(days=n * mult),
                "scan": wants_day, "label": f"the next {n} {unit}s",
                "month": unit == "month"}

    # ── named windows ───────────────────────────────────────────────────────
    if "next week" in q:
        start = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
        return {"kind": "window", "start": start, "end": start + timedelta(days=6),
                "scan": wants_day, "label": "next week"}
    if "this week" in q or "coming days" in q or "next few days" in q or "coming week" in q:
        return {"kind": "window", "start": today, "end": today + timedelta(days=6),
                "scan": wants_day, "label": "the week ahead"}
    if "next month" in q:
        return {"kind": "window", "start": today + timedelta(days=1),
                "end": today + timedelta(days=45), "scan": wants_day,
                "label": "the month ahead", "month": True}
    if "this month" in q or "wider month" in q or "the month" in q or "coming month" in q:
        return {"kind": "window", "start": today, "end": today + timedelta(days=30),
                "scan": wants_day, "label": "this month", "month": True}

    # ── "when / which day is good for X" with no explicit window → 60-day scan ─
    if wants_day:
        return {"kind": "window", "start": today, "end": today + timedelta(days=60),
                "scan": True, "label": "the next couple of months"}

    return None


def score_day_for_concern(natal_lagna_idx: int, natal_moon_sign: str, concern: str,
                          d: date, lat: float, lng: float, tz: float) -> Optional[dict]:
    """Cheap per-day directional read for `concern` on date `d`. Returns
    {date, band, score, moon_sign, nakshatra, moon_house, concern_hit} or None."""
    try:
        from antar_engine.daily_panchanga import calculate_panchanga
        from antar_engine.daily_prediction_engine import _score_day
    except Exception:
        return None
    try:
        p = calculate_panchanga(lat=lat, lng=lng, tz_offset=tz, target_date=d)
    except Exception:
        return None
    moon_sign = p.get("moon_sign")
    nak = p.get("nakshatra") or ""
    vara = p.get("vara") or ""
    if moon_sign not in SIGNS or natal_lagna_idx is None:
        return None
    moon_house = ((SIGNS.index(moon_sign) - int(natal_lagna_idx)) % 12) + 1
    fav, caution = _concern_houses(concern)
    try:
        gq, _friction = _score_day(moon_sign, natal_moon_sign or moon_sign, nak, vara)
    except Exception:
        gq = 5
    concern_hit = 0
    if moon_house in fav:
        concern_hit = 2
    elif moon_house in caution or moon_house in (6, 8, 12):
        concern_hit = -2
    total = int(gq) + concern_hit
    band = ("favorable" if total >= 8 else "cautious" if total <= 4 else "mixed")
    return {"date": d, "band": band, "score": total, "moon_sign": moon_sign,
            "nakshatra": nak, "moon_house": moon_house, "concern_hit": concern_hit}


def scan_window(natal_lagna_idx, natal_moon_sign, concern, start: date, end: date,
                lat, lng, tz, step: int = 1, cap: int = 100):
    """Score each day (every `step` days) in [start, end]; return the list plus
    the best and worst days for the concern. Bounded by `cap` scored days."""
    days = []
    d = start
    n = 0
    while d <= end and n < cap:
        s = score_day_for_concern(natal_lagna_idx, natal_moon_sign, concern, d, lat, lng, tz)
        if s:
            days.append(s)
        d += timedelta(days=step)
        n += 1
    if not days:
        return {"days": [], "best": None, "worst": None}
    best = max(days, key=lambda x: x["score"])
    worst = min(days, key=lambda x: x["score"])
    return {"days": days, "best": best, "worst": worst}
