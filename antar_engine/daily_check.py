"""
antar_engine/daily_check.py
───────────────────────────
The daily check: one tap, "How did today go?", about a day we rated.

Why this exists. The outcome loop learns from "did it hold?" answers, but windows are long (the
median topic window is ~2 months), so real answers arrive slowly. Every day already carries our own
rating (steady / light / friction, plus a 1-10 score). Asking how the day actually went gives about
one answer per person per day, and the comparison needs no decoy windows: the board checks whether
the days we called steady are rated better than the days we called friction, by the SAME people.

Design rules (written before any data):
  * The card never shows the engine's rating before the answer (no expectation effect).
  * good / mixed / hard are stored as yes / partly / no in prediction_outcomes (1 / .5 / 0).
  * One claim per chart per local day (dedupe_key chart|day|daily_check|date|date).
  * Offered from ~5 PM local; yesterday's unanswered one is offered until noon the next day.
  * The board (accuracy_board.daily_check_summary) reports totals only, with a minimum of 30 answers
    per group, a 95% interval on the difference, and both chart halves.

Pure helpers; the Supabase calls live in main.py. Never raises.
"""
from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timedelta, timezone
from typing import Optional

SOURCE = "daily_check"
RATINGS = {"good": "yes", "mixed": "partly", "hard": "no"}
SCORE = {"good": 1.0, "mixed": 0.5, "hard": 0.0}
CLASSES = ("steady", "light", "friction")
SHOW_FROM_HOUR = 17          # local: the day is mostly lived
SHOW_UNTIL_NEXT_HOUR = 12    # local, next day: "How did yesterday go?"
MIN_N = 30
PUSH_HOUR = 20

_TEXT = {
    "en": {"today": "How did today go?", "yesterday": "How did yesterday go?",
           "good": "Went well", "mixed": "Mixed", "hard": "Hard",
           "thanks": "Thanks. That helps us get this right.",
           "push_title": "How did today go?", "push_body": "One tap. It takes two seconds."},
    "es": {"today": "¿Cómo te fue hoy?", "yesterday": "¿Cómo te fue ayer?",
           "good": "Bien", "mixed": "Regular", "hard": "Difícil",
           "thanks": "Gracias. Nos ayuda a acertar más.",
           "push_title": "¿Cómo te fue hoy?", "push_body": "Un toque. Toma dos segundos."},
    "pt": {"today": "Como foi o seu dia?", "yesterday": "Como foi ontem?",
           "good": "Foi bem", "mixed": "Mais ou menos", "hard": "Difícil",
           "thanks": "Obrigado. Isso nos ajuda a acertar mais.",
           "push_title": "Como foi o seu dia?", "push_body": "Um toque. Leva dois segundos."},
}


def lang_of(language) -> str:
    l = str(language or "en").split("-")[0].lower()
    return l if l in _TEXT else "en"


def day_class(signal: dict) -> Optional[dict]:
    """The engine's own rating of the day from a daily-signal payload, or None when it is a
    fallback / pending / unrated payload (those are never recorded)."""
    try:
        if not isinstance(signal, dict) or signal.get("fallback") or signal.get("pending"):
            return None
        de = signal.get("day_energy") or {}
        key = str(de.get("key") or "").lower()
        if key not in CLASSES:
            return None
        score = de.get("score", signal.get("score"))
        return {"class": key, "score": int(score) if isinstance(score, (int, float)) else None,
                "label": str(de.get("label") or "")[:60] or None}
    except Exception:
        return None


def build_claim(chart_id: str, local_date: date, signal: dict, language: str = "en") -> Optional[dict]:
    """A prediction_claims row for the day, or None."""
    dc = day_class(signal)
    if not (chart_id and local_date and dc):
        return None
    d = local_date.isoformat()
    return {
        "chart_id": chart_id, "source": SOURCE, "topic": "day", "claim_type": "day",
        "window_start": d, "window_end": d,
        "text_shown": str((signal or {}).get("verdict_subline") or "")[:500] or None,
        "question": None, "language": lang_of(language), "channel": "app",
        "verdict": dc["class"].upper(), "confidence_word": None,
        "engines": {"daily": dc},
        "dedupe_key": f"{chart_id}|day|{SOURCE}|{d}|{d}",
        "checkin_due_at": datetime(local_date.year, local_date.month, local_date.day, 20, tzinfo=timezone.utc).isoformat(),
    }


def local_now(now_utc: datetime, tz_minutes) -> datetime:
    try:
        return now_utc + timedelta(minutes=int(tz_minutes or 0))
    except (TypeError, ValueError):
        return now_utc


def which_day(local: datetime) -> Optional[str]:
    """'today' from SHOW_FROM_HOUR, 'yesterday' until SHOW_UNTIL_NEXT_HOUR the next morning, else None."""
    if local.hour >= SHOW_FROM_HOUR:
        return "today"
    if local.hour < SHOW_UNTIL_NEXT_HOUR:
        return "yesterday"
    return None


def target_date(local: datetime, which: str) -> date:
    return local.date() if which == "today" else (local.date() - timedelta(days=1))


def card(claim_id: str, local_date: date, which: str, language: str = "en") -> dict:
    t = _TEXT[lang_of(language)]
    return {"claim_id": claim_id, "date": local_date.isoformat(), "day": which,
            "question": t[which],
            "options": [{"value": k, "label": t[k]} for k in ("good", "mixed", "hard")]}


def thanks(language: str = "en") -> str:
    return _TEXT[lang_of(language)]["thanks"]


def push_message(language: str = "en") -> tuple:
    t = _TEXT[lang_of(language)]
    return t["push_title"], t["push_body"]


# ── the board section ────────────────────────────────────────────────────────
def _half(chart_id: str) -> str:
    return "A" if int(hashlib.sha1((chart_id or "").encode()).hexdigest(), 16) % 2 == 0 else "B"


def _mean_var(xs: list) -> tuple:
    n = len(xs)
    if not n:
        return (None, None, 0)
    m = sum(xs) / n
    v = (sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    return (m, v, n)


def _diff_ci(a: list, b: list) -> tuple:
    """(difference of means a-b, 95% CI low, high) by the normal approximation; (None,)*3 if too small."""
    ma, va, na = _mean_var(a)
    mb, vb, nb = _mean_var(b)
    if na < 2 or nb < 2:
        return (None, None, None)
    se = math.sqrt(va / na + vb / nb)
    d = ma - mb
    return (round(d, 3), round(d - 1.96 * se, 3), round(d + 1.96 * se, 3))


def summarize(claims: list, outcomes: dict) -> dict:
    """Board section from daily_check claims + {claim_id: outcome row}. Totals only."""
    groups = {k: [] for k in CLASSES}
    by_half = {"A": {k: [] for k in CLASSES}, "B": {k: [] for k in CLASSES}}
    charts, shown, answered_n, not_sure = set(), 0, 0, 0
    for c in claims:
        if c.get("source") != SOURCE:
            continue
        shown += 1
        cls = (((c.get("engines") or {}).get("daily") or {}).get("class") or "").lower()
        o = (outcomes.get(c.get("id")) or {}).get("outcome")
        inv = {"yes": 1.0, "partly": 0.5, "no": 0.0}
        if o == "not_sure":
            not_sure += 1
            continue
        if cls not in groups or o not in inv:
            continue
        groups[cls].append(inv[o])
        by_half[_half(c.get("chart_id"))][cls].append(inv[o])
        charts.add(c.get("chart_id"))
        answered_n += 1
    rows = {}
    for k, xs in groups.items():
        m, _, n = _mean_var(xs)
        rows[k] = {"n": n, "mean_rating": round(m, 3) if m is not None else None}
    lift = _diff_ci(groups["steady"], groups["friction"])
    halves = {h: _diff_ci(g["steady"], g["friction"])[0] for h, g in by_half.items()}
    enough = len(groups["steady"]) >= MIN_N and len(groups["friction"]) >= MIN_N
    if not enough:
        status = "Too few answers"
    elif (lift[1] is not None and lift[1] > 0
          and all(h is not None and h > 0 for h in halves.values())):
        status = "Steady days rate higher"
    else:
        status = "No difference yet"
    return {"asked": shown, "answered": answered_n, "not_sure": not_sure,
            "distinct_charts": len(charts), "by_class": rows,
            "steady_minus_friction": {"diff": lift[0], "ci95": [lift[1], lift[2]], "halves": halves},
            "min_answers_per_group": MIN_N, "status": status}
