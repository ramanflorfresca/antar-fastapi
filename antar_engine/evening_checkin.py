"""
evening_checkin.py — the evening "did today land?" nudge + the weekly accuracy receipt
=====================================================================================

The daily claim (prediction_tracker.save_daily_claim, key "daily-<local date>")
is enrolled every day and answered on Today's check-in card — but only if the
person comes back to Today after the day has played out. Two light pulls close
that loop, both at the person's LOCAL time:

  * EVENING (~8 PM): today's claim is still unanswered → "Did today land?"
  * WEEKLY  (Sunday ~7 PM): "Your week: 5 of 6 reads landed." — only when
    enough was answered for the number to mean something.

Pure helpers live here (tested); the hourly jobs that query Supabase and send
are `_evening_checkin_job` / `_weekly_receipt_job` in main.py, and the receipt
is served by GET /api/v1/predictions/weekly-receipt/{chart_id}.

DEDUPE: like the morning nudge (_daily_push_job), each job runs once an hour and
acts only when the chart's local hour equals the target hour, so a chart is
reached at most once per local day/week. We deliberately do NOT stamp the
claim's correlation_key (as yesno_checkback does): "daily-<date>" is the upsert
identity, and changing it would make the next Today load enrol a duplicate.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

EVENING_HOUR = 20          # ~8 PM local — after the day's windows have played out
WEEKLY_HOUR = 19           # ~7 PM local
WEEKLY_WEEKDAY = 6         # Sunday (Mon=0)
MIN_ANSWERED_FOR_WEEKLY = 2
ROUTE_TODAY = "/dashboard"

_LANDED, _PARTLY, _MISSED = "yes", "partial", "no"


def norm_lang(*candidates) -> str:
    for c in candidates:
        c = str(c or "").split("-")[0].lower()
        if c in ("en", "es", "pt"):
            return c
    return "en"


def local_now(now_utc: datetime, tz_hours) -> datetime:
    return now_utc + timedelta(hours=float(tz_hours or 0.0))


def is_local_hour(now_utc: datetime, tz_hours, hour: int) -> bool:
    return local_now(now_utc, tz_hours).hour == hour


def is_local_weekly_slot(now_utc: datetime, tz_hours) -> bool:
    ln = local_now(now_utc, tz_hours)
    return ln.weekday() == WEEKLY_WEEKDAY and ln.hour == WEEKLY_HOUR


def daily_key_for(now_utc: datetime, tz_hours) -> str:
    """The correlation_key today's claim is stored under, in the person's local date."""
    return f"daily-{local_now(now_utc, tz_hours).date().isoformat()}"


def _clip(text, limit=110) -> str:
    t = " ".join(str(text or "").split())
    if len(t) <= limit:
        return t
    cut = t[: limit - 1]
    i = cut.rfind(" ")
    if i >= limit * 0.5:
        cut = cut[:i]
    return cut.rstrip(" ,;:—-") + "…"


def evening_due(row: dict, now_utc: datetime, tz_hours) -> bool:
    """Today's daily claim, still pending, whose ask time has passed, at ~8 PM local."""
    if str(row.get("feedback_status") or "").lower() != "pending":
        return False
    if str(row.get("correlation_key") or "") != daily_key_for(now_utc, tz_hours):
        return False
    if not is_local_hour(now_utc, tz_hours, EVENING_HOUR):
        return False
    sa = row.get("show_after")
    if sa:
        try:
            d = datetime.fromisoformat(str(sa).replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            if d > now_utc:
                return False
        except Exception:
            pass
    return bool((row.get("trackable_claim") or "").strip())


def build_evening_message(claim, lang="en") -> tuple:
    """-> (title, body). The claim is our own plain-language day read."""
    # drop the claim's own end stop so the quote isn't followed by "”." ("stop.”. Did…")
    c = _clip(claim).rstrip(" .")
    lang = norm_lang(lang)
    if lang == "es":
        return "¿Cómo te fue hoy?", f"Esta mañana leímos: “{c}”. ¿Se cumplió? Sí, en parte o no."
    if lang == "pt":
        return "Como foi o seu dia?", f"Hoje cedo lemos: “{c}”. Aconteceu? Sim, em parte ou não."
    return "Did today land?", f"This morning's read: “{c}”. Did it fit? Yes, partly or no."


def _parse(ts) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def weekly_receipt(rows: Iterable[dict], now_utc: datetime, tz_hours=0.0, days: int = 7) -> dict:
    """Summarise the last `days` local days of verification.

    tracked  = claims enrolled in the window (created_at, else show_after)
    answered = claims answered in the window (feedback_at) as yes/partial/no
    accuracy_pct = (landed + 0.5*partly) / answered — same rule as /accuracy.
    Skipped/expired/pending never count as answered.
    """
    ln = local_now(now_utc, tz_hours)
    start_local = (ln - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = start_local - timedelta(hours=float(tz_hours or 0.0))
    landed = partly = missed = tracked = 0
    best = None
    answered_days = set()
    for r in rows or []:
        made = _parse(r.get("created_at")) or _parse(r.get("show_after"))
        if made and made >= start_utc:
            tracked += 1
        st = str(r.get("feedback_status") or "").lower()
        fa = _parse(r.get("feedback_at"))
        if st not in (_LANDED, _PARTLY, _MISSED) or not fa or fa < start_utc or fa > now_utc:
            continue
        answered_days.add(local_now(fa, tz_hours).date())
        if st == _LANDED:
            landed += 1
            if best is None or fa > best[0]:
                best = (fa, r.get("trackable_claim"))
        elif st == _PARTLY:
            partly += 1
        else:
            missed += 1
    answered = landed + partly + missed
    return {
        "window_start": start_local.date().isoformat(),
        "window_end": ln.date().isoformat(),
        "tracked": tracked,
        "answered": answered,
        "landed": landed,
        "partly": partly,
        "missed": missed,
        "days_answered": len(answered_days),
        "accuracy_pct": round(100.0 * (landed + 0.5 * partly) / answered, 1) if answered else None,
        "best_landed": _clip(best[1], 140) if best and best[1] else None,
    }


def weekly_should_send(receipt: dict) -> bool:
    return int(receipt.get("answered") or 0) >= MIN_ANSWERED_FOR_WEEKLY


def build_weekly_message(receipt: dict, lang="en") -> tuple:
    """-> (title, body). Honest: landed and partly are named separately, out of
    what the person actually checked — never "5 of 6 landed" when 2 were partly."""
    lang = norm_lang(lang)
    a = int(receipt.get("answered") or 0)
    l = int(receipt.get("landed") or 0)
    p = int(receipt.get("partly") or 0)
    if lang == "es":
        core = (f"{l} se cumplieron y {p} en parte, de {a} que revisaste esta semana."
                if p else f"{l} de {a} lecturas que revisaste se cumplieron esta semana.")
        return "Tu semana con Antar", core + " Mira lo que viene."
    if lang == "pt":
        core = (f"{l} se confirmaram e {p} em parte, de {a} que você conferiu esta semana."
                if p else f"{l} de {a} leituras que você conferiu se confirmaram esta semana.")
        return "Sua semana com o Antar", core + " Veja o que vem aí."
    core = (f"{l} landed and {p} partly, out of {a} you checked this week."
            if p else f"{l} of {a} reads you checked landed this week.")
    return "Your week with Antar", core + " See what's next."
