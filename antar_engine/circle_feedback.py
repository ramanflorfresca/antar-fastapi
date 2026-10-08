"""
antar_engine/circle_feedback.py - one-tap "does this fit?" on a pair's reading.

Nobody can read everyone's chats, and a user will not write to say a reading was wrong. So the Our-reading tab asks ONE
question at a time, answered in one tap: yes / partly / no.
  call     "Does the call above fit how things really are right now?"          (the Not now / With structure / Good time)
  me       "Does the card about you fit?"                                       (the viewer's OWN card: independent of the partner)
  reading  "Overall, does this reading fit the two of you?"
It goes through the EXISTING outcome loop: a prediction_claims row (source circle_fit, topic = the relation lens, claim_type
fit) and a prediction_outcomes row, which the accuracy board scores per (item, lens) with small-n suppression. No new table.
Each claim snapshots what produced the reading (lens, verdict, call, the viewer's tone / bond level / chapter) so we can
learn WHICH kinds of reads miss. Per person, per pair, per item, once per ~90 days (the reading changes as chapters turn).
Only while the reading is on (both opted in); never on the demo chart; fails open when the tables are missing.
Blocking Supabase calls: use from a `def` endpoint or a thread.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from antar_engine import circle_copy as CC
from antar_engine.outcomes import _table_missing

logger = logging.getLogger(__name__)

SOURCE = "circle_fit"
ITEMS = ("call", "me", "reading")
ANSWERS = ("yes", "partly", "no")
BUCKET_DAYS = 90

QUESTION = {
    "call": {"en": "Does the call above fit how things really are right now?", "es": "¿La conclusión de arriba coincide con cómo están realmente las cosas ahora?",
             "pt": "A conclusão acima combina com como as coisas realmente estão agora?", "hinglish": "Kya upar ka nirnay aaj ke asli haalaat se milta hai?"},
    "me": {"en": "Does the card about you fit?", "es": "¿La tarjeta sobre ti coincide contigo?", "pt": "O cartão sobre você combina com você?",
           "hinglish": "Kya aapke baare mein wala card aap par sahi baithta hai?"},
    "reading": {"en": "Overall, does this reading fit the two of you?", "es": "En general, ¿esta lectura les queda a los dos?",
                "pt": "No geral, esta leitura combina com vocês dois?", "hinglish": "Kul milakar, kya ye reading aap dono par sahi baithti hai?"},
}
LABEL = {
    "yes": {"en": "Yes, it fits", "es": "Sí, coincide", "pt": "Sim, combina", "hinglish": "Haan, sahi hai"},
    "partly": {"en": "Partly", "es": "En parte", "pt": "Em parte", "hinglish": "Kuch had tak"},
    "no": {"en": "No, not really", "es": "No, no mucho", "pt": "Não, nem tanto", "hinglish": "Nahin, zyada nahin"},
}
THANKS = {"en": "Thanks. Hits and misses both help us get this right.", "es": "Gracias. Los aciertos y los fallos nos ayudan a acertar.",
          "pt": "Obrigado. Acertos e erros nos ajudam a melhorar.", "hinglish": "Shukriya. Sahi aur galat, dono se hum behtar hote hain."}
TEXTS = (QUESTION["call"], QUESTION["me"], QUESTION["reading"], LABEL["yes"], LABEL["partly"], LABEL["no"], THANKS)


def thanks(language) -> str:
    return CC.pick(THANKS, CC.lang_of(language))


def options(language) -> list:
    lang = CC.lang_of(language)
    return [{"value": v, "label": CC.pick(LABEL[v], lang)} for v in ANSWERS]


def _bucket(today: date) -> int:
    return today.toordinal() // BUCKET_DAYS


def dedupe_key(chart_id: str, pair_id: str, item: str, today: date) -> str:
    return f"{chart_id}|{pair_id}|{SOURCE}:{item}|{_bucket(today)}"


def snapshot(item: str, reading: dict) -> dict:
    """What produced this reading, for the viewer (people[0] is always the viewer) - no names, no birth data."""
    brief = (reading or {}).get("brief") or {}
    me = (brief.get("people") or [{}])[0] or {}
    ph, vd = brief.get("phase") or {}, brief.get("verdict") or {}
    season = me.get("season") or {}
    bond = me.get("bond") or {}
    part = me.get("partnership") or {}
    return {"item": item, "lens": brief.get("lens"), "family": brief.get("family"), "verdict": vd.get("key"), "call": ph.get("call"),
            "phase": ph.get("status"), "fit_badge": (brief.get("fit") or {}).get("badge"), "score": (reading or {}).get("score"),
            "me_tone": season.get("tone"), "me_position": season.get("position"), "me_bond": bond.get("level") or part.get("lean"),
            "me_role": me.get("role")}


def shown_text(item: str, reading: dict) -> str:
    brief = (reading or {}).get("brief") or {}
    me = (brief.get("people") or [{}])[0] or {}
    if item == "call":
        ph = brief.get("phase") or {}
        return f"{ph.get('call_title') or ''}. {ph.get('line') or ''}".strip(" .")[:500]
    if item == "me":
        return " ".join(x for x in ((me.get("temperament") or {}).get("trait"), (me.get("season") or {}).get("label")) if x)[:500]
    return str((reading or {}).get("headline") or "")[:500]


def available_items(reading: Optional[dict]) -> tuple:
    """Items that can be asked for this reading: the call only when there is a brief with a phase."""
    brief = (reading or {}).get("brief") or {}
    out = ["reading"]
    if brief.get("phase"):
        out.insert(0, "call")
    if brief.get("people"):
        out.insert(1 if "call" in out else 0, "me")
    return tuple(i for i in ITEMS if i in out)


def _answered(sb, chart_id: str, pair_id: str, today: date) -> set:
    keys = {i: dedupe_key(chart_id, pair_id, i, today) for i in ITEMS}
    claims = (sb.table("prediction_claims").select("id,dedupe_key").eq("chart_id", chart_id).eq("source", SOURCE)
              .in_("dedupe_key", list(keys.values())).execute().data) or []
    if not claims:
        return set()
    outs = {o["claim_id"] for o in (sb.table("prediction_outcomes").select("claim_id,outcome")
                                    .in_("claim_id", [c["id"] for c in claims]).execute().data or [])
            if o.get("outcome") in ANSWERS}
    by_key = {c["dedupe_key"]: c["id"] for c in claims}
    return {i for i, k in keys.items() if by_key.get(k) in outs}


def next_item(sb, chart_id: str, pair_id: str, reading: Optional[dict], today: Optional[date] = None) -> Optional[str]:
    """The next unanswered item for this person on this pair, or None. Fail-open: None if the tables are missing."""
    today = today or date.today()
    try:
        done = _answered(sb, chart_id, pair_id, today)
    except Exception as e:
        if not _table_missing(e):
            logger.warning("[circle-feedback] lookup failed: %s", str(e)[:160])
        return None
    for i in available_items(reading):
        if i not in done:
            return i
    return None


def prompt(item: str, reading: dict, language=None) -> dict:
    lang = CC.lang_of(language)
    return {"item": item, "question": CC.pick(QUESTION[item], lang), "options": options(lang), "context": shown_text(item, reading)}


class FeedbackError(Exception):
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code, self.status = code, status


def record(sb, chart_id: str, pair_id: str, item: str, answer: str, reading: dict, language=None,
           today: Optional[date] = None, now: Optional[datetime] = None) -> dict:
    """Save one answer. Idempotent: a repeat answer to the same item in the same period keeps the FIRST answer
    (never overwritten). Raises FeedbackError(bad_item|bad_answer|unavailable)."""
    if item not in ITEMS:
        raise FeedbackError("bad_item", 422)
    if answer not in ANSWERS:
        raise FeedbackError("bad_answer", 422)
    today = today or date.today()
    now = now or datetime.now(timezone.utc)
    key = dedupe_key(chart_id, pair_id, item, today)
    snap = snapshot(item, reading)
    row = {"chart_id": chart_id, "source": SOURCE, "topic": str(snap.get("lens") or "pair"), "claim_type": "fit",
           "window_start": today.isoformat(), "window_end": today.isoformat(), "text_shown": shown_text(item, reading) or None,
           "language": CC.lang_of(language), "channel": "app", "verdict": str(snap.get("verdict") or snap.get("call") or "")[:40] or None,
           "engines": {"circle_fit": snap}, "dedupe_key": key, "checkin_due_at": now.isoformat(), "checkin_sent_at": now.isoformat(),
           "checkin_channel": "app"}
    try:
        sb.table("prediction_claims").upsert(row, on_conflict="dedupe_key", ignore_duplicates=True).execute()
        got = (sb.table("prediction_claims").select("id").eq("dedupe_key", key).limit(1).execute().data) or []
        if not got:
            raise FeedbackError("unavailable", 503)
        cid = got[0]["id"]
        prev = (sb.table("prediction_outcomes").select("claim_id,outcome").eq("claim_id", cid).limit(1).execute().data) or []
        if prev and prev[0].get("outcome") in ANSWERS:
            return {"saved": False, "already_answered": True, "outcome": prev[0]["outcome"]}
        sb.table("prediction_outcomes").upsert({"claim_id": cid, "outcome": answer, "note": None, "answered_at": now.isoformat(),
                                                "answered_via": "app"}, on_conflict="claim_id").execute()
    except FeedbackError:
        raise
    except Exception as e:
        if not _table_missing(e):
            logger.warning("[circle-feedback] record failed: %s", str(e)[:160])
        raise FeedbackError("unavailable", 503)
    return {"saved": True, "already_answered": False, "outcome": answer}
