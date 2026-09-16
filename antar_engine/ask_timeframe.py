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
import unicodedata
from datetime import date, timedelta
from typing import Optional

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# question vocabulary → a CONCERN_MAP key (places_concern). EN + es/pt so a
# localized question routes to the same concern houses as its English twin.
_CONCERN_ALIAS = {
    "speculation": "money", "speculate": "money", "investment": "money",
    "invest": "money", "investing": "money", "trading": "money", "trade": "money",
    "stocks": "money", "stock": "money", "gambling": "money", "bet": "money",
    "lottery": "money", "wealth": "money", "finance": "money", "financial": "money",
    "funding": "money", "income": "money", "money": "money",
    # es/pt money
    "especulacion": "money", "especular": "money", "especulacao": "money",
    "inversion": "money", "invertir": "money", "investimento": "money",
    "investir": "money", "dinero": "money", "dinheiro": "money",
    "finanzas": "money", "financas": "money", "renta": "money", "renda": "money",
    "business": "business", "startup": "business", "venture": "business",
    "negocio": "business", "empresa": "business", "emprendimiento": "business",
    "job": "career", "work": "career", "career": "career", "promotion": "career",
    "trabajo": "career", "empleo": "career", "carrera": "career",
    "trabalho": "career", "emprego": "career", "carreira": "career",
    "relationship": "love", "romance": "love", "marriage": "love",
    "partner": "love", "love": "love", "dating": "love",
    "relacion": "love", "pareja": "love", "amor": "love", "matrimonio": "love",
    "relacionamento": "love", "parceiro": "love", "casamento": "love",
    "health": "health", "peace": "peace", "family": "family",
    "salud": "health", "saude": "health", "paz": "peace",
    "familia": "family",
}


def _norm(s: str) -> str:
    """Lowercase + strip accents so es/pt phrasing matches ASCII patterns
    ('próximos'->'proximos', 'mañana'->'manana', 'qué'->'que')."""
    s = (s or "").lower()
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


# unit token (accent-stripped, en/es/pt) → (days multiplier, canonical kind)
_UNIT_MULT = {
    "day": (1, "day"), "days": (1, "day"), "dia": (1, "day"), "dias": (1, "day"),
    "week": (7, "week"), "weeks": (7, "week"),
    "semana": (7, "week"), "semanas": (7, "week"),
    "month": (30, "month"), "months": (30, "month"),
    "mes": (30, "month"), "meses": (30, "month"),
}
_UNIT_RE = r"(days?|weeks?|months?|dias?|semanas?|mes|meses)"
_NEXT_RE = r"(?:next|proxim[oa]s?|dentro de)"


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
    q = _norm(question)
    today = today or date.today()

    has_today = bool(re.search(
        r"\btoday\b|\bright now\b|\btonight\b|\bhoy\b|\bahora\b|"
        r"\besta noche\b|\bhoje\b|\bagora\b|\besta noite\b", q))
    has_tom = bool(re.search(r"\btomorrow\b|\bmanana\b|\bamanha\b", q))
    wants_day = bool(re.search(
        r"\b(which|what)\s+day\b|\bbest\s+day\b|\bwhen\b|\bwhat\s+time\b|"
        r"\bwhich\s+time\b|"                                    # en
        r"\b(que|cual)\s+dia\b|\bmejor\s+dia\b|\bcuando\b|\ba\s+que\s+hora\b|"  # es
        r"\bqual\s+dia\b|\bmelhor\s+dia\b|\bquando\b|\bque\s+horas?\b", q))     # pt

    # ── enumerable days ─────────────────────────────────────────────────────
    if has_today and has_tom:
        return {"kind": "days", "days": [today, today + timedelta(days=1)],
                "label": "today and tomorrow"}
    if has_tom:
        return {"kind": "days", "days": [today + timedelta(days=1)], "label": "tomorrow"}
    if has_today:
        return {"kind": "days", "days": [today], "label": "today"}

    # ── explicit bounded windows ("next 45 to 90 days", "próximos 45 a 90 días") ──
    m_rng = re.search(
        _NEXT_RE + r"\s+(\d+)\s*(?:to|-|–|and|a|e|y)\s*(\d+)\s*" + _UNIT_RE, q)
    if m_rng:
        a, b = int(m_rng.group(1)), int(m_rng.group(2))
        mult, kind = _UNIT_MULT[m_rng.group(3)]
        return {"kind": "window", "start": today + timedelta(days=a * mult),
                "end": today + timedelta(days=b * mult), "scan": True,
                "label": f"the next {a}–{b} {kind}s"}
    m_n = re.search(_NEXT_RE + r"\s+(\d+)\s*" + _UNIT_RE, q)
    if m_n:
        n = int(m_n.group(1))
        mult, kind = _UNIT_MULT[m_n.group(2)]
        return {"kind": "window", "start": today, "end": today + timedelta(days=n * mult),
                "scan": wants_day, "label": f"the next {n} {kind}s",
                "month": kind == "month"}

    # ── named windows (en / es / pt) ─────────────────────────────────────────
    if re.search(r"next week|proxima semana|semana que viene|semana entrante", q):
        start = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
        return {"kind": "window", "start": start, "end": start + timedelta(days=6),
                "scan": wants_day, "label": "next week"}
    if re.search(r"this week|coming days|next few days|coming week|"
                 r"esta semana|proximos dias|proxima semana|"
                 r"proximos dias", q):
        return {"kind": "window", "start": today, "end": today + timedelta(days=6),
                "scan": wants_day, "label": "the week ahead"}
    if re.search(r"next month|proximo mes|mes que viene|proximo mes", q):
        return {"kind": "window", "start": today + timedelta(days=1),
                "end": today + timedelta(days=45), "scan": wants_day,
                "label": "the month ahead", "month": True}
    if re.search(r"this month|wider month|the month|coming month|"
                 r"este mes|este mes|proximo mes", q):
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
