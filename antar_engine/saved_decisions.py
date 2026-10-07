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
    "ASK_CLAIM_SOURCES", "CLAIM_PREFIX", "claim_decision_id", "parse_claim_decision_id",
    "claims_to_decisions", "claim_timing_label",
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
    # [hi 2026-10-07] "hi" = Devanagari ("hindi" copy); the legacy "hi" key is Roman-script
    # Hinglish. A stored legacy "hi" row stays Hinglish (it was written before the split).
    if l in ("hinglish", "hi-latn") or l.startswith("hinglish"):
        return "hi"
    if l in ("hindi",) or l.startswith("hi-") or l.startswith("hi_"):
        return "hindi"
    if l == "hi":
        return "hindi"
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
    if not (ws or we):
        # [saved-decisions] The /ask payload carries the LABEL ("Nov 2026 – Jan
        # 2027") but not the parsed dates, so a client can only ever send the
        # label. Derive the window here rather than pushing date parsing into
        # the FE — same parser the outcome loop already uses on the same string,
        # so a saved decision and its claim can never disagree about the window.
        try:
            from antar_engine.outcomes import parse_window as _pw
            ws, we = _pw(a.get("timing") or "", (now or datetime.now(timezone.utc)).date())
        except Exception:
            ws = we = None
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
    "hindi": ("आपकी समय-खिड़की खुल गई", "{q} — आपने जो समय-खिड़की सहेजी थी, वह अब खुल रही है। {move}"),
}
_MOVE = {
    "en": "Open Antar to see what to do first.",
    "es": "Abre Antar para ver qué hacer primero.",
    "pt": "Abra o Antar para ver o que fazer primeiro.",
    "hi": "Pehla kadam dekhne ke liye Antar kholein.",
    "hindi": "पहला कदम देखने के लिए Antar खोलिए।",
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


# ── Your questions: every dated Ask answer, without a "save" tap ───────────────
# [your-questions 2026-10-07] The Your questions screen used to list ONLY rows the
# user deliberately saved, so it was empty for anyone who had asked 40 questions
# and never tapped save. Every dated answer from the app AND from WhatsApp is
# already recorded in prediction_claims (question, window, verdict, channel). The
# list endpoint now merges those in at READ time. Nothing is copied into
# saved_decisions: that table keeps meaning "something the user chose to keep".
ASK_CLAIM_SOURCES = ("ask_explore", "ask_yesno")
CLAIM_PREFIX = "claim:"

_SOURCE_LABEL = {
    "en": {"app": "From the app", "whatsapp": "From WhatsApp"},
    "es": {"app": "Desde la app", "whatsapp": "Desde WhatsApp"},
    "pt": {"app": "Pelo app", "whatsapp": "Pelo WhatsApp"},
}


def claim_decision_id(claim_id) -> str:
    return f"{CLAIM_PREFIX}{claim_id}"


def parse_claim_decision_id(decision_id) -> Optional[str]:
    """The claim uuid inside a 'claim:<uuid>' id, else None."""
    d = str(decision_id or "")
    if d.startswith(CLAIM_PREFIX) and len(d) > len(CLAIM_PREFIX):
        return d[len(CLAIM_PREFIX):]
    return None


def _src_label(channel, language) -> Optional[str]:
    l = lang_of(language)
    table = _SOURCE_LABEL.get(l, _SOURCE_LABEL["en"])
    c = str(channel or "").strip().lower()
    return table.get(c) or (table["app"] if c in ("", "app", "web") else None)


def claim_timing_label(ws: Optional[date], we: Optional[date], language="en",
                       today: Optional[date] = None) -> Optional[str]:
    """'Oct 14 – Oct 20' for a near window; month + year when it is not this year."""
    if not (ws or we):
        return None
    from antar_engine import topic_copy as C
    t = today or date.today()
    ws = ws or we
    we = we or ws
    l = lang_of(language)
    cl = l if l in ("en", "es", "pt") else "en"
    if ws.year != t.year or we.year != t.year:
        a, b = C.month_year_short(ws, cl), C.month_year_short(we, cl)
        return a if a == b else f"{a} – {b}"
    return C.range_label(ws, we, cl)


def claims_to_decisions(claims: list, saved_rows: list, *, today: Optional[date] = None) -> list:
    """Rows shaped like saved decisions, built from recorded Ask claims.

    saved_rows is EVERY saved_decisions row for the chart, archived ones included:
    a claim the user already saved, archived or deleted must not come back.
    One row per distinct question (the newest), dated claims only.
    """
    t = today or date.today()
    hidden_ids = {str(r.get("claim_id")) for r in saved_rows if r.get("claim_id")}
    live_q = {(r.get("question") or "").strip().lower()
              for r in saved_rows if not r.get("archived_at")}
    seen, out = set(), []
    for c in sorted(claims, key=lambda x: str(x.get("created_at") or ""), reverse=True):
        q = (c.get("question") or "").strip()
        if not q or c.get("source") not in ASK_CLAIM_SOURCES:
            continue
        if str(c.get("id")) in hidden_ids:
            continue
        k = q.lower()
        if k in live_q or k in seen:
            continue
        ws, we = _d(c.get("window_start")), _d(c.get("window_end"))
        if not we:
            continue
        if ws and ws > we:      # a mis-parsed window ("Jan 2027 – Nov 2026"): put it in order
            ws, we = we, ws
        seen.add(k)
        lang = lang_of(c.get("language"))
        out.append({
            "id": claim_decision_id(c.get("id")),
            "chart_id": c.get("chart_id"),
            "claim_id": c.get("id"),
            "question": q[:500],
            "verdict": (str(c.get("verdict") or "").upper().strip() or None),
            "timing_label": claim_timing_label(ws, we, lang, t),
            "window_start": ws.isoformat() if ws else None,
            "window_end": we.isoformat(),
            "note": None,
            "summary": None,
            "language": lang,
            "source": _src_label(c.get("channel"), lang),
            "created_at": c.get("created_at"),
            "auto": True,
            "status": status_for(ws, we, t),
        })
    return out
