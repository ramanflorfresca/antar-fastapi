"""
yesno_checkback.py — the Yes/No "did it happen?" reminder (push, email fallback)
==============================================================================

Every Yes/No answer promises "We'll check back with you around {date}". The
in-app card (Ask → AskFollowUp) keeps that promise only if the person opens
Ask. This module brings them back: once a Yes/No claim's `show_after` passes,
send ONE reminder at the person's local morning.

Pure helpers live here (tested); the hourly job that queries Supabase and sends
is `_yesno_checkback_job` in main.py.

DEDUPE WITHOUT DDL
  Lovable owns the schema, so there is no `notified_at` column. The reminder
  stamp rides inside the row's machine marker (`correlation_key`, never shown to
  users): "[YN;...;moment=...]" -> "[YN;...;moment=...;notified=push@<iso>]".
  kp_prashna._parse_marker reads it as one more key, harmless to calibration.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

LOCAL_HOUR = 8            # ~8 AM local, like the daily nudge and check-in ping
LOOKBACK_DAYS = 30        # never remind about a check-back that went due long ago
ROUTE = "/ask"            # where the check-back card lives

_NOTIFIED = re.compile(r";notified=([a-z]+)@([^;\]]*)")


def is_notified(correlation_key) -> bool:
    return bool(_NOTIFIED.search(str(correlation_key or "")))


def mark_notified(correlation_key, channel, when_iso) -> str:
    """Stamp the marker. Keeps it a valid [YN;...] marker; idempotent."""
    k = str(correlation_key or "")
    if is_notified(k):
        return k
    stamp = f";notified={channel}@{when_iso}"
    if k.startswith("[YN;") and k.endswith("]"):
        return k[:-1] + stamp + "]"
    return (k + " " if k else "") + f"[YN{stamp}]"


def norm_lang(*candidates) -> str:
    for c in candidates:
        c = str(c or "").split("-")[0].lower()
        if c in ("en", "es", "pt"):
            return c
    return "en"


_MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"],
    "pt": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
}


def _asked_on(created_at, lang) -> str:
    try:
        d = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except Exception:
        return ""
    m = _MONTHS[lang][d.month - 1]
    return f"{m} {d.day}" if lang == "en" else f"{d.day} {m}"


def _clip(text, limit=90) -> str:
    t = " ".join(str(text or "").split())
    if len(t) <= limit:
        return t
    cut = t[: limit - 1]
    i = cut.rfind(" ")
    if i >= limit * 0.5:
        cut = cut[:i]
    return cut.rstrip(" ,;:—-?") + "…"


def build_message(question, created_at, lang="en") -> tuple:
    """-> (title, body). Plain, no astrology terms — the question is the user's own."""
    lang = norm_lang(lang)
    q = _clip(question)
    on = _asked_on(created_at, lang)
    if lang == "es":
        title = "¿Sucedió?"
        body = (f"El {on} preguntaste: “{q}”. Cuéntanos cómo fue." if on
                else f"Preguntaste: “{q}”. Cuéntanos cómo fue.")
    elif lang == "pt":
        title = "Aconteceu?"
        body = (f"Em {on} você perguntou: “{q}”. Conte como foi." if on
                else f"Você perguntou: “{q}”. Conte como foi.")
    else:
        title = "Did it happen?"
        body = (f"On {on} you asked: “{q}”. Tell us how it went." if on
                else f"You asked: “{q}”. Tell us how it went.")
    return title, body


def is_due(row, now_utc) -> bool:
    """Pending, past show_after, within the lookback, not yet reminded."""
    if str(row.get("feedback_status") or "").lower() != "pending":
        return False
    if str(row.get("concern") or "") != "yesno":
        return False
    if is_notified(row.get("correlation_key")):
        return False
    try:
        sa = datetime.fromisoformat(str(row.get("show_after")).replace("Z", "+00:00"))
    except Exception:
        return False
    if sa.tzinfo is None:
        sa = sa.replace(tzinfo=timezone.utc)
    return now_utc - timedelta(days=LOOKBACK_DAYS) <= sa <= now_utc


def is_local_morning(now_utc, tz_hours) -> bool:
    return (now_utc + timedelta(hours=float(tz_hours or 0.0))).hour == LOCAL_HOUR


def email_html(question, created_at, lang="en", base_url="https://antar.world") -> tuple:
    """-> (subject, html) for the email fallback. Links to Ask, where the card is."""
    import html as _html
    title, body = build_message(question, created_at, lang)
    title, body = _html.escape(title), _html.escape(body)   # the question is user-typed
    cta = {"en": "Answer in Antar", "es": "Responder en Antar", "pt": "Responder no Antar"}[norm_lang(lang)]
    url = f"{base_url.rstrip('/')}{ROUTE}"
    html = f"""
<div style="font-family:-apple-system,sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;
            background:#0f0f0f;color:#e8e0d0;border-radius:16px;">
  <p style="font-size:12px;color:#00D9B8;letter-spacing:2px;margin:0 0 8px;">ANTAR</p>
  <h2 style="font-size:22px;font-weight:600;margin:0 0 16px;color:#e8e0d0;">{title}</h2>
  <p style="font-size:15px;line-height:1.6;margin:0 0 24px;color:#c9c2b4;">{body}</p>
  <a href="{url}" style="display:inline-block;padding:12px 20px;border-radius:8px;
     background:#00D9B8;color:#060608;text-decoration:none;font-weight:600;">{cta}</a>
</div>"""
    return f"Antar — {build_message(question, created_at, lang)[0]}", html
