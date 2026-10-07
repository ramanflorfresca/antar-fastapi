"""
antar_engine/topic_checkback.py — "did it hold?" for the dated windows a topic read showed.

[topic-checkback 2026-10-07] A "did this feel right?" tap is weak evidence — people
agree with personal-sounding readings. The real accuracy signal is asked AFTER a
window has ended: did the stretch we called good hold, did the caution we raised
turn out to matter. The answer goes into the existing outcome loop, not a parallel
one:

  record   → prediction_claims   (source "topic_read", claim_type "window")
  answer   → prediction_outcomes (yes | no | not_sure — the board's own vocabulary)
  board    → accuracy_board.build() reads source "topic_read" as its own rows

No new table: prediction_claims / prediction_outcomes already exist (sql_outcome_loop.sql),
are already in the chart-delete PII purge and the account-delete cascade, and
outcomes ride ON DELETE CASCADE. If those tables are missing everything here fails
OPEN and quietly — a topic read is never slowed or broken by bookkeeping.

What counts as a hit (written down before any data, mirrored in the board):
  best  window + "yes, it held"            -> hit   (outcome yes)
  best  window + "no"                      -> miss  (outcome no)
  watch window + "yes, it mattered"        -> hit   (outcome yes)
  watch window + "no, it didn't matter"    -> miss  (outcome no)
  "not sure yet"                           -> neither; asked once more after 30 days, then never

Pure helpers + thin Supabase calls (all synchronous — call from a def endpoint or a
thread, never bare inside an async def).
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from antar_engine import topic_copy as C
from antar_engine.outcomes import REASK_AFTER_DAYS, REASK_MARK, _table_missing

logger = logging.getLogger(__name__)

SOURCE = "topic_read"
# "today" is a one-day window re-shown every morning; asking "did it hold?" about each
# one would be noise and would flood the board with near-identical claims.
RECORDED_SCALES = ("month", "season", "year")
KINDS = ("best", "watch")
ANSWERS = ("yes", "no", "not_sure")
# a window is due the day AFTER its last day
DUE_AFTER_END_DAYS = 1
MAX_PER_REQUEST = 3
LOOKBACK_DAYS = 120            # a window that ended months ago is no longer a fair thing to ask

_warned = set()


def is_demo(sb, chart_id) -> bool:
    """True when chart_id is the public demo chart. The demo is read-only, so a claim
    recorded on it could never be answered. Refreshes demo_mode's id cache (a tiny sync
    read, ~30s TTL) — so call from a def endpoint / thread like everything here.
    Fail-open to False on any read error (demo_chart_id keeps its last known value)."""
    try:
        from antar_engine import demo_mode
        demo_mode.demo_chart_id(sb)
        return demo_mode.is_demo_chart(chart_id)
    except Exception:
        return False


def _warn_once(key: str, msg: str):
    if key not in _warned:
        _warned.add(key)
        logger.warning(msg)


# ── RECORD ───────────────────────────────────────────────────────────────────
def _rolling_horizon(scale: str, period_end: date, today: date) -> Optional[date]:
    """The date a scan stops at when that stop MOVES with today (so a window touching
    it has been cut short, not truly ended). None when the frame is fixed."""
    if scale == "month":
        return period_end
    if scale in ("season", "year"):
        from antar_engine.topic_engine import SEASON_SCAN_CAP_DAYS
        cap = today + timedelta(days=SEASON_SCAN_CAP_DAYS)
        return cap if cap < period_end else None
    return None


def build_claims(out: Optional[dict], chart_id: str, today: Optional[date] = None) -> list:
    """prediction_claims rows for the windows in one topic-read response — [] when
    there is nothing honest to record (no window, a locked replay, a scale we skip)."""
    if not isinstance(out, dict) or out.get("locked"):
        return []
    scale, topic = out.get("scale"), out.get("topic")
    if scale not in RECORDED_SCALES or topic not in C.TOPIC_KEYS:
        return []
    today = today or date.today()
    try:
        period_end = date.fromisoformat(str((out.get("period") or {}).get("end"))[:10])
    except ValueError:
        period_end = None
    horizon = _rolling_horizon(scale, period_end, today) if period_end else None
    rows = []
    for kind in KINDS:
        w = out.get(f"{kind}_window")
        if not isinstance(w, dict):
            continue
        try:
            s, e = date.fromisoformat(str(w["start"])[:10]), date.fromisoformat(str(w["end"])[:10])
        except (KeyError, ValueError):
            continue
        if e < s or e < today:
            continue
        # A window running into a MOVING scan edge is a view of its start, not a window
        # with a known end — recording it would mint a new claim every day. It is picked
        # up once its real end falls inside the scan.
        if horizon and e >= horizon:
            continue
        rows.append({
            "chart_id": chart_id,
            "source": SOURCE,
            "topic": topic,
            "claim_type": "window",
            "window_start": s.isoformat(),
            "window_end": e.isoformat(),
            "text_shown": str(out.get("claim") or "")[:500] or None,
            "language": out.get("language") or "en",
            "channel": "app",
            "verdict": str(out.get("tone") or "")[:40] or None,
            "engines": {"topic_read": {"kind": kind, "scale": scale, "tone": out.get("tone")}},
            "dedupe_key": f"{chart_id}|{topic}|topic_read:{scale}:{kind}|{s.isoformat()}|{e.isoformat()}",
            "checkin_due_at": datetime.combine(e + timedelta(days=DUE_AFTER_END_DAYS),
                                               datetime.min.time(), tzinfo=timezone.utc).isoformat(),
        })
    return rows


def _meta(row: dict) -> dict:
    return ((row.get("engines") or {}).get("topic_read")) or {}


def _overlaps(a_s, a_e, b_s, b_e) -> bool:
    return bool(a_s and a_e and b_s and b_e and a_s <= b_e and b_s <= a_e)


def record_windows(sb, out: Optional[dict], chart_id: str, today: Optional[date] = None) -> int:
    """Record one claim per (chart, topic, scale, kind, window). Idempotent and
    overlap-aware: the engine's windows are bucketed from TODAY, so the same stretch
    comes back with a start/end a few days off tomorrow; a window that overlaps one
    already recorded for the same (topic, scale, kind) is the same stretch, not a new
    claim. Returns how many new claims were written. Never raises. Never records on
    the public demo chart (read-only: nobody could answer)."""
    try:
        if is_demo(sb, chart_id):
            return 0
        rows = build_claims(out, chart_id, today)
        if not rows:
            return 0
        wrote = 0
        for row in rows:
            m = _meta(row)
            existing = (sb.table("prediction_claims")
                        .select("id,window_start,window_end,engines")
                        .eq("chart_id", chart_id).eq("source", SOURCE)
                        .eq("topic", row["topic"])
                        .gte("window_end", row["window_start"])
                        .lte("window_start", row["window_end"])
                        .limit(20).execute()).data or []
            if any(_meta(x).get("kind") == m["kind"] and _meta(x).get("scale") == m["scale"]
                   for x in existing):
                continue
            res = (sb.table("prediction_claims")
                   .upsert(row, on_conflict="dedupe_key", ignore_duplicates=True).execute())
            wrote += len(res.data or [])
        return wrote
    except Exception as e:
        if _table_missing(e):
            _warn_once("missing", "[topic-checkback] prediction_claims not available yet — "
                                  "not recording topic windows")
        else:
            logger.warning("[topic-checkback] record failed: %s", e)
        return 0


# ── COPY (en / es / pt / hinglish; anything else is served in English) ───────
_QUESTION = {
    "best": {
        "en": "Your {topic} window, {range}, has passed. Did it hold?",
        "es": "Tu ventana de {topic}, {range}, ya pasó. ¿Se cumplió?",
        "pt": "Sua janela de {topic}, {range}, já passou. Ela se confirmou?",
        "hinglish": "Aapka {topic} ka window, {range}, nikal gaya. Kya woh sahi nikla?",
    },
    "watch": {
        "en": "The caution we flagged for your {topic}, {range}, has passed. Did it turn out to matter?",
        "es": "La precaución que marcamos para tu {topic}, {range}, ya pasó. ¿Resultó importar?",
        "pt": "O cuidado que apontamos para seu {topic}, {range}, já passou. Ele fez diferença?",
        "hinglish": "Aapke {topic} ke liye jo savdhaani batayi thi, {range}, nikal gayi. Kya woh sach mein matter kiya?",
    },
}
_LABELS = {
    "best": {
        "en": {"yes": "Yes, it held", "no": "No, it didn't", "not_sure": "Not sure yet"},
        "es": {"yes": "Sí, se cumplió", "no": "No", "not_sure": "Aún no sé"},
        "pt": {"yes": "Sim, se confirmou", "no": "Não", "not_sure": "Ainda não sei"},
        "hinglish": {"yes": "Haan, sahi nikla", "no": "Nahi", "not_sure": "Abhi pata nahi"},
    },
    "watch": {
        "en": {"yes": "Yes, it mattered", "no": "No, it didn't", "not_sure": "Not sure yet"},
        "es": {"yes": "Sí, importó", "no": "No", "not_sure": "Aún no sé"},
        "pt": {"yes": "Sim, fez diferença", "no": "Não", "not_sure": "Ainda não sei"},
        "hinglish": {"yes": "Haan, matter kiya", "no": "Nahi", "not_sure": "Abhi pata nahi"},
    },
}
_REASK_LEAD = {
    "en": "Last time you weren't sure yet.",
    "es": "La última vez aún no estabas seguro.",
    "pt": "Da última vez você ainda não tinha certeza.",
    "hinglish": "Pichhli baar aapko pakka nahi tha.",
}
_THANKS = {
    "en": "Thanks — noted. Hits and misses both help us get this right.",
    "es": "Gracias — anotado. Los aciertos y los fallos nos ayudan a acertar.",
    "pt": "Obrigado — anotado. Acertos e erros nos ajudam a melhorar.",
    "hinglish": "Shukriya — note kar liya. Sahi aur galat, dono se hum behtar hote hain.",
}
TEXTS = (_QUESTION, _LABELS, _REASK_LEAD, _THANKS)    # for the jargon guard


def _lang(raw) -> str:
    return C.serve_language(raw)


def _range(s: date, e: date, lang: str) -> str:
    if s.year != e.year or (e - s).days >= 90:
        return f"{C.day_label_y(s, lang)} – {C.day_label_y(e, lang)}"
    return C.range_label(s, e, lang)


def _parse_day(v) -> Optional[date]:
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def option_labels(kind: str, language) -> dict:
    return _LABELS[kind if kind in KINDS else "best"][_lang(language)]


def thanks(language) -> str:
    return _THANKS[_lang(language)]


def build_item(row: dict, language=None, reask: bool = False) -> Optional[dict]:
    """One check-back card from a claim row, in plain words. None if the row is unusable."""
    kind = _meta(row).get("kind")
    topic = row.get("topic")
    s, e = _parse_day(row.get("window_start")), _parse_day(row.get("window_end"))
    if kind not in KINDS or topic not in C.TOPIC_KEYS or not (s and e):
        return None
    lang = _lang(language or row.get("language"))
    rng = _range(s, e, lang)
    q = _QUESTION[kind][lang].format(topic=C.LABEL[lang][topic].lower(), range=rng)
    if reask:
        q = f"{_REASK_LEAD[lang]} {q}"
    labels = option_labels(kind, lang)
    return {
        "id": row["id"],
        "topic": topic,
        "topic_label": C.LABEL[lang][topic],
        "kind": kind,
        "scale": _meta(row).get("scale"),
        "window": {"start": s.isoformat(), "end": e.isoformat(), "label": rng},
        "question": q,
        "options": [{"value": v, "label": labels[v]} for v in ANSWERS],
        "reask": bool(reask),
        "language": lang,
    }


# ── CHECK-BACK DUE ───────────────────────────────────────────────────────────
def _answered_at(o) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(str(o.get("answered_at")).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def select_due(claims: list, outcomes: dict, now: datetime, limit: int = 1) -> list:
    """Pure: which claims to ask about now, oldest first. A claim is due when its window
    has ENDED and it is either unanswered, or was answered "not sure" at least
    REASK_AFTER_DAYS ago and has not been re-asked yet."""
    out = []
    for c in sorted(claims, key=lambda r: r.get("checkin_due_at") or ""):
        if c.get("source") != SOURCE:
            continue
        due = _parse_ts(c.get("checkin_due_at"))
        if not due or due > now:
            continue
        o = outcomes.get(c["id"])
        if o is None:
            if now - due > timedelta(days=LOOKBACK_DAYS):
                continue
            out.append((c, False))
        elif (o.get("outcome") == "not_sure" and REASK_MARK not in (c.get("checkin_channel") or "")):
            at = _answered_at(o)
            if at and now - at >= timedelta(days=REASK_AFTER_DAYS):
                out.append((c, True))
    return out[:max(1, min(int(limit or 1), MAX_PER_REQUEST))]


def _parse_ts(v) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def due_items(sb, chart_id: str, language=None, now: Optional[datetime] = None,
              limit: int = 1) -> list:
    """The check-back cards due for this chart. Fail-open: [] if the tables are missing.
    Always [] for the demo chart, without touching the store."""
    if is_demo(sb, chart_id):
        return []
    now = now or datetime.now(timezone.utc)
    try:
        claims = (sb.table("prediction_claims").select("*").eq("chart_id", chart_id)
                  .eq("source", SOURCE).lte("checkin_due_at", now.isoformat())
                  .order("checkin_due_at").limit(50).execute()).data or []
        if not claims:
            return []
        outs = {o["claim_id"]: o for o in (sb.table("prediction_outcomes")
                .select("claim_id,outcome,answered_at")
                .in_("claim_id", [c["id"] for c in claims]).execute().data or [])}
    except Exception as e:
        if _table_missing(e):
            _warn_once("missing", "[topic-checkback] prediction_claims not available yet")
        else:
            logger.warning("[topic-checkback] due lookup failed: %s", e)
        return []
    items = []
    for c, reask in select_due(claims, outs, now, limit):
        it = build_item(c, language, reask)
        if it:
            items.append(it)
            mark_shown(sb, c, reask, now)
    return items


def mark_shown(sb, claim: dict, reask: bool, now: datetime):
    """Stamp checkin_sent_at the first time a claim is put in front of someone, so the
    board can tell "shown, not answered" from "never shown" (answer rate). Best effort."""
    if claim.get("checkin_sent_at") and not reask:
        return
    try:
        sb.table("prediction_claims").update(
            {"checkin_sent_at": claim.get("checkin_sent_at") or now.isoformat(),
             "checkin_channel": claim.get("checkin_channel") or "app"}
        ).eq("id", claim["id"]).execute()
    except Exception as e:
        logger.warning("[topic-checkback] could not stamp shown: %s", e)


# ── ANSWER ───────────────────────────────────────────────────────────────────
class UnknownCheckback(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class DemoReadOnly(Exception):
    pass


def record_answer(sb, chart_id: str, claim_id: str, answer: str,
                  now: Optional[datetime] = None) -> dict:
    """Save the answer. Idempotent: a final answer (yes/no) is never overwritten, a
    "not sure" can be replaced by a real answer, and a repeat "not sure" is a no-op.
    Raises UnknownCheckback (not this chart's topic-read claim) / ValueError (bad answer)
    / StoreUnavailable (could not read or write) / DemoReadOnly (the public demo chart)."""
    if answer not in ANSWERS:
        raise ValueError(f"answer must be one of {list(ANSWERS)}")
    try:
        uuid.UUID(str(claim_id))
    except ValueError:
        raise UnknownCheckback(claim_id)     # a malformed id can never be a claim
    if is_demo(sb, chart_id):
        raise DemoReadOnly(chart_id)
    now = now or datetime.now(timezone.utc)
    try:
        rows = (sb.table("prediction_claims").select("*").eq("id", claim_id)
                .eq("chart_id", chart_id).eq("source", SOURCE).limit(1).execute()).data or []
        if not rows:
            raise UnknownCheckback(claim_id)
        claim = rows[0]
        prev = (sb.table("prediction_outcomes").select("claim_id,outcome,answered_at")
                .eq("claim_id", claim_id).limit(1).execute()).data or []
    except UnknownCheckback:
        raise
    except Exception as e:
        raise StoreUnavailable(str(e))
    prev = prev[0] if prev else None
    if prev and prev.get("outcome") in ("yes", "no", "partly"):
        return {"saved": False, "already_answered": True, "outcome": prev["outcome"]}
    if prev and answer == "not_sure":
        at = _answered_at(prev)
        if not (at and now - at >= timedelta(days=REASK_AFTER_DAYS)):
            return {"saved": False, "already_answered": True, "outcome": "not_sure"}
    try:
        sb.table("prediction_outcomes").upsert({
            "claim_id": claim_id, "outcome": answer, "note": None,
            "answered_at": now.isoformat(), "answered_via": "app",
        }, on_conflict="claim_id").execute()
    except Exception as e:
        raise StoreUnavailable(str(e))
    at = _answered_at(prev) if prev else None
    if prev and prev.get("outcome") == "not_sure" and at and now - at >= timedelta(days=REASK_AFTER_DAYS):
        # this was the one allowed re-ask — whatever they said, it is never asked again.
        # (A "not sure" settled sooner than that was never a re-ask, so it is not marked.)
        try:
            ch = claim.get("checkin_channel") or "app"
            if REASK_MARK not in ch:
                sb.table("prediction_claims").update({"checkin_channel": ch + REASK_MARK}) \
                    .eq("id", claim_id).execute()
        except Exception as e:
            logger.warning("[topic-checkback] could not mark re-ask: %s", e)
    return {"saved": True, "already_answered": False, "outcome": answer}
