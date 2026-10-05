"""Decisions the user chose to keep, and the reminder when their window opens.

[saved-decisions 2026-10-05] Antar already recorded every dated answer as a
prediction_claim and came back when the window CLOSED to ask "did it happen?".
That is the engine scoring itself — silent, automatic, and invisible to the
person using the app.

This is the other half, and it is a different thing: the USER deliberately
saves a decision they are waiting on, and Antar tells them when the window
OPENS. A horoscope app cannot do that, because it never commits to a window in
the first place. It also changes what the app takes in — the user now supplies
the decision, instead of only supplying a birth date — which is the part that
actually changes how the product is classified.

Everything here is pure: no DB, no clock reads except what is passed in. The
scheduling rule, the status rule and the copy are all testable without network.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

__all__ = [
    "LOCAL_HOUR", "STATUSES",
    "lang_of", "status_for", "open_reminder_due", "build_row",
    "push_message", "whatsapp_message",
]

# Same hour the outcome check-in uses, so a person never gets two Antar
# notifications at different times of the same morning.
LOCAL_HOUR = 8

STATUSES = ("upcoming", "open", "closed")


def lang_of(language) -> str:
    """en | es | pt | hi — the engine's four-language contract.

    Hinglish takes the 'hi' strings. An English-only lookup here would be the
    same silent-i18n bug that has bitten every other surface.
    """
    l = str(language or "en").strip().lower()
    if l in ("hi", "hinglish") or l.startswith("hi"):
        return "hi"
    b = l.split("_")[0].split("-")[0][:2]
    return b if b in ("es", "pt") else "en"


def status_for(window_start: Optional[date], window_end: Optional[date],
               today: Optional[date] = None) -> str:
    """Where this decision sits relative to its window."""
    t = today or date.today()
    if window_end and t > window_end:
        return "closed"
    if window_start and t < window_start:
        return "upcoming"
    return "open"


def open_reminder_due(window_start: Optional[date], tz_offset_hours: float = 0.0,
                      now: Optional[datetime] = None) -> Optional[datetime]:
    """When to tell them the window is open, as an aware UTC timestamp.

    At LOCAL_HOUR on the day the window starts. If the window is already open
    when they save it — which is the common case, because people save the
    answer they just read — the reminder goes to the NEXT local morning rather
    than firing instantly or being dropped. Saving something already live is
    exactly when a nudge is useful; sending it the same second is not.

    None when there is no start date: nothing to announce.
    """
    if not window_start:
        return None
    now = now or datetime.now(timezone.utc)
    off = timedelta(hours=float(tz_offset_hours or 0.0))

    def _utc_at_local_hour(d: date) -> datetime:
        return datetime.combine(d, time(hour=LOCAL_HOUR), tzinfo=timezone.utc) - off

    due = _utc_at_local_hour(window_start)
    if due <= now:
        local_today = (now + off).date()
        due = _utc_at_local_hour(local_today)
        if due <= now:
            due = _utc_at_local_hour(local_today + timedelta(days=1))
    return due


def _d(v) -> Optional[date]:
    if isinstance(v, date):
        return v
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def build_row(chart_id: str, question: str, answer: dict, *,
              language: str = "en", note: Optional[str] = None,
              claim_id: Optional[str] = None, tz_offset_hours: float = 0.0,
              now: Optional[datetime] = None) -> dict:
    """A saved_decisions row from the answer the user is looking at.

    Window dates come from the answer when it carries them; the timing label is
    kept verbatim for display because it is already localized and already the
    string the person read.
    """
    a = answer or {}
    ws, we = _d(a.get("window_start")), _d(a.get("window_end"))
    due = open_reminder_due(ws, tz_offset_hours, now)
    return {
        "chart_id": chart_id,
        "claim_id": claim_id,
        "question": (question or "").strip()[:500],
        "verdict": (str(a.get("verdict") or "").upper().strip() or None),
        "timing_label": (str(a.get("timing") or "").strip() or None),
        "window_start": ws.isoformat() if ws else None,
        "window_end": we.isoformat() if we else None,
        "note": (note or "").strip()[:1000] or None,
        "language": lang_of(language),
        "open_reminder_due_at": due.isoformat() if due else None,
    }


_PUSH = {
    "en": ("Your window is open", "{q} — the window you saved opens now. {move}"),
    "es": ("Tu ventana está abierta", "{q} — la ventana que guardaste se abre ahora. {move}"),
    "pt": ("Sua janela está aberta", "{q} — a janela que você salvou abre agora. {move}"),
    "hi": ("Aapki window khul gayi", "{q} — jo window aapne save ki thi woh ab khul rahi hai. {move}"),
}
_MOVE = {
    "en": "Open Antar to see what to do first.",
    "es": "Abre Antar para ver qué hacer primero.",
    "pt": "Abra o Antar para ver o que fazer primeiro.",
    "hi": "Pehla kadam dekhne ke liye Antar kholein.",
}


def _short_q(question: str, limit: int = 60) -> str:
    q = re.sub(r"\s+", " ", (question or "").strip()).rstrip("?").strip()
    return q if len(q) <= limit else q[: limit - 1].rstrip() + "…"


def push_message(row: dict) -> tuple:
    """(title, body) for the window-open push, in the saved language."""
    l = lang_of((row or {}).get("language"))
    title, body = _PUSH.get(l, _PUSH["en"])
    return title, body.format(q=_short_q((row or {}).get("question") or ""),
                              move=_MOVE.get(l, _MOVE["en"])).strip()


def whatsapp_message(row: dict) -> str:
    """One line for WhatsApp, inside the 24h free-form window."""
    l = lang_of((row or {}).get("language"))
    _, body = _PUSH.get(l, _PUSH["en"])
    label = (row or {}).get("timing_label")
    line = body.format(q=_short_q((row or {}).get("question") or ""),
                       move=_MOVE.get(l, _MOVE["en"])).strip()
    return f"{line} ({label})" if label else line
