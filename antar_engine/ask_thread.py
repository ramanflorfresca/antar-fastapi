"""
The Ask Antar thread: every question a person has asked and every answer, as one conversation (like a messaging app), with the
"Did this hold?" check-ins arriving as messages from Antar.

Pure shaping only: the history rows and the due check-ins come in, the ordered items the screen renders come out. The backend owns every
label (day dividers, times, starter questions) so the app never formats a date or writes a sentence. Fail-open and read-only.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

MON = {"en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
       "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]}
TX = {"en": {"today": "Today", "yesterday": "Yesterday", "title": "Ask Antar",
             "empty_title": "Ask me anything, or tell me what is on your mind.",
             "empty_note": "Your questions and my answers stay here, so you can come back to them."},
      "es": {"today": "Hoy", "yesterday": "Ayer", "title": "Pregunta a Antar",
             "empty_title": "Pregúntame lo que quieras, o cuéntame qué tienes en mente.",
             "empty_note": "Tus preguntas y mis respuestas se quedan aquí, para que puedas volver a ellas."}}
# every starter is a question the product answers quickly (the Home chips and the time-aware routing)
STARTERS = {"en": ["What is the one thing I should focus on today?", "How are the next 4 days for my work?",
                   "What is the one thing I should focus on this month?"],
            "es": ["¿En qué debo enfocarme hoy?", "¿Cómo están los próximos 4 días para mi trabajo?",
                   "¿En qué debo enfocarme este mes?"]}


def _lang(l) -> str:
    return "es" if str(l or "en").lower().startswith("es") else "en"


def offset_hours(tz) -> float:
    """The client's timezone as hours east of UTC: minutes (IST = 330) or hours (-5) are both accepted, as on the other endpoints."""
    try:
        v = float(tz)
    except (TypeError, ValueError):
        return 0.0
    v = v / 60.0 if abs(v) > 14 else v
    return max(-12.0, min(14.0, v))


def parse_ts(s) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def local(dt: datetime, tz) -> datetime:
    return dt.astimezone(timezone.utc) + timedelta(hours=offset_hours(tz))


def day_label(d: date, today: date, lang: str) -> str:
    t = TX[_lang(lang)]
    if d == today:
        return t["today"]
    if d == today - timedelta(days=1):
        return t["yesterday"]
    lg = _lang(lang)
    core = f"{MON[lg][d.month - 1]} {d.day}" if lg == "en" else f"{d.day} {MON[lg][d.month - 1]}"
    return core if d.year == today.year else f"{core}, {d.year}"


def time_label(dt: datetime, lang: str) -> str:
    if _lang(lang) == "es":
        return f"{dt.hour:02d}:{dt.minute:02d}"
    return f"{(dt.hour % 12) or 12}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"


def build(messages: List[dict], checkins: Optional[List[dict]], tz, today: date, lang: str = "en") -> dict:
    """Ordered thread items (oldest first, so the app appends to the bottom) with day dividers and times, plus the starter questions when
    the thread is empty. `messages` are history exchanges (id, question, answer, next, domain, created_at), already oldest first."""
    lg = _lang(lang)
    items, prev_day = [], None
    for m in messages or []:
        dt = parse_ts(m.get("created_at"))
        if dt is None or not (m.get("question") or m.get("answer")):
            continue
        ld = local(dt, tz)
        d = ld.date()
        items.append({"kind": "exchange", "id": m.get("id"), "question": m.get("question") or "", "answer": m.get("answer") or "",
                      "next": m.get("next") or "", "domain": m.get("domain") or "general", "created_at": m.get("created_at"),
                      "day": d.isoformat(), "day_label": day_label(d, today, lg), "time_label": time_label(ld, lg),
                      "show_day_label": d != prev_day})
        prev_day = d
    for c in checkins or []:
        items.append({"kind": "checkin", "claim_id": c.get("claim_id"), "text": c.get("text") or "", "topic": c.get("topic"),
                      "options": c.get("options") or [], "day": today.isoformat(), "day_label": TX[lg]["today"],
                      "show_day_label": prev_day != today})
        prev_day = today
    out = {"title": TX[lg]["title"], "items": items}
    if not items:
        out["empty"] = {"title": TX[lg]["empty_title"], "note": TX[lg]["empty_note"], "starters": STARTERS[lg]}
    return out
