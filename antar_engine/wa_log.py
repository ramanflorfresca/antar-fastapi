"""
antar_engine/wa_log.py — the WhatsApp conversation record (table wa_messages, sql_wa_messages.sql).

[wa-log 2026-10-06] Every inbound and outbound WhatsApp message is written here with its time, the
Antar number that carried it, language and (via annotate) what the NLU layer understood — topic,
subject, intent. It is the raw material for reviewing answer quality and, ONLY for people who have
consented to it, for training.

Rules
  * Never slows or breaks a send/receive: writes run on a small thread pool and swallow every error
    (table not created yet → stdout only).
  * The rows hold PII (the number and the text). The table is in main.py's chart-delete purge list;
    rows written before a number is linked have chart_id NULL and are purged by number.
  * Capturing a conversation is not consent to train on it: nothing here decides that. An export for
    training must filter to numbers whose link row carries a training-consent version.
"""
from __future__ import annotations

import contextvars
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="wa-log")
sb = None                       # bound once by main.py (bind)
inbound_sid: contextvars.ContextVar = contextvars.ContextVar("wa_inbound_sid", default="")


def bind(client) -> None:
    global sb
    sb = client


def _digits_number(n) -> str:
    raw = str(n or "").replace("whatsapp:", "").strip()
    if re.match(r"^[A-Za-z]{2}\.[A-Za-z0-9]{6,64}$", raw):   # a WhatsApp user ID (no phone number): keep it whole
        return raw[:2].upper() + raw[2:]
    d = re.sub(r"\D", "", raw)
    return ("+" + d) if d else ""


def _write(row: dict) -> None:
    if sb is None:
        return
    try:
        link = (sb.table("messaging_links").select("chart_id,consent_version")
                .eq("channel", "whatsapp").eq("channel_user_id", row["wa_number"])
                .eq("status", "linked").limit(1).execute().data or [None])[0]
        if link:
            row.setdefault("chart_id", link.get("chart_id"))
            row.setdefault("consent_version", link.get("consent_version"))
        sb.table("wa_messages").insert(row).execute()
    except Exception as e:
        print(f"[wa-log] not recorded (non-fatal): {str(e)[:120]}")


def record(direction: str, number: str, body: str = "", *, sender: str = "", sid: str = "",
           kind: str = "text", template: str = "", lang: str = "", meta: Optional[dict] = None) -> None:
    """Fire-and-forget. direction 'in' | 'out'."""
    try:
        from antar_engine.wa_numbers import country_of
        n = _digits_number(number)
        if not n:
            return
        row = {"direction": direction, "wa_number": n, "sender_number": _digits_number(sender) or None,
               "message_sid": sid or None, "kind": kind, "template": template or None,
               "body": (body or "")[:4000], "lang": lang or None, "country": country_of(n) or None,
               "meta": meta or {}}
        _pool.submit(_write, row)
    except Exception as e:
        print(f"[wa-log] skipped (non-fatal): {e}")


def annotate(sid: str, **fields) -> None:
    """Add what we learned about an inbound message (lang, topic, subject, intent, engine) to its row."""
    if not (sid and fields):
        return

    def _do():
        if sb is None:
            return
        try:
            cur = (sb.table("wa_messages").select("id,meta").eq("message_sid", sid)
                   .eq("direction", "in").limit(1).execute().data or [None])[0]
            if not cur:
                return
            meta = dict(cur.get("meta") or {})
            lang = fields.pop("lang", None)
            meta.update({k: v for k, v in fields.items() if v is not None})
            patch = {"meta": meta}
            if lang:
                patch["lang"] = lang
            sb.table("wa_messages").update(patch).eq("id", cur["id"]).execute()
        except Exception as e:
            print(f"[wa-log] annotate skipped (non-fatal): {str(e)[:120]}")

    _pool.submit(_do)
