"""
antar_engine/messaging.py — channel-agnostic /ask-over-messaging adapter.

[messaging 2026-10-01] /ask is already a clean pipeline; this wraps it for chat
channels. Telegram first (free, no approval); the same helpers port to WhatsApp.
Pure helpers only (NO import of main) so there's no circular import — main.py owns
the webhook ORCHESTRATION (it has ask_endpoint + AskRequest). Fail-open: a missing
`messaging_links` table never 500s a webhook.

Identity: a chat message arrives from a channel user id; we map it to a chart_id
via a one-time link code the user generates in-app and sends to the bot.
"""
from __future__ import annotations

import json
import secrets
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

_TG_API = "https://api.telegram.org/bot{token}/{method}"


def _table_missing(e) -> bool:
    m = str(e).lower()
    return ("pgrst205" in m or "could not find the table" in m or "does not exist" in m)


def gen_link_code() -> str:
    """Short, URL-safe, unambiguous one-time code (for t.me/<bot>?start=<code>)."""
    return secrets.token_urlsafe(6)


def create_pending_link(sb, chart_id: str, user_id: Optional[str],
                        channel: str = "telegram") -> dict:
    """Create a pending link row; returns {available, code} (or available:False
    when the table isn't set up yet)."""
    code = gen_link_code()
    row = {
        "chart_id": chart_id, "user_id": user_id, "channel": channel,
        "link_code": code, "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        sb.table("messaging_links").insert(row).execute()
        return {"available": True, "code": code, "channel": channel}
    except Exception as e:
        if _table_missing(e):
            return {"available": False, "reason": "messaging storage not set up yet"}
        print(f"[messaging] create_pending_link failed: {e}")
        return {"available": False, "reason": "error"}


def bind_link(sb, code: str, channel: str, channel_user_id: str) -> Optional[str]:
    """Bind a pending code to a channel user. Returns the chart_id on success."""
    code = (code or "").strip()
    if not code:
        return None
    try:
        res = (sb.table("messaging_links").select("id,chart_id")
               .eq("link_code", code).eq("channel", channel)
               .eq("status", "pending").limit(1).execute())
        rows = res.data or []
        if not rows:
            return None
        rid, cid = rows[0]["id"], rows[0]["chart_id"]
        (sb.table("messaging_links").update({
            "channel_user_id": str(channel_user_id), "status": "linked",
            "link_code": None,
            "linked_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", rid).execute())
        return cid
    except Exception as e:
        if _table_missing(e):
            return None
        print(f"[messaging] bind_link failed: {e}")
        return None


def resolve_chart(sb, channel: str, channel_user_id: str) -> Optional[str]:
    """chart_id for a linked channel user, or None if not linked."""
    try:
        res = (sb.table("messaging_links").select("chart_id")
               .eq("channel", channel).eq("channel_user_id", str(channel_user_id))
               .eq("status", "linked").limit(1).execute())
        rows = res.data or []
        return rows[0]["chart_id"] if rows else None
    except Exception as e:
        if _table_missing(e):
            return None
        print(f"[messaging] resolve_chart failed: {e}")
        return None


def telegram_send(token: str, chat_id, text: str) -> bool:
    """Send a plain-text message. Fail-soft (logs, returns False)."""
    if not token:
        return False
    try:
        data = json.dumps({"chat_id": chat_id, "text": text,
                           "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(
            _TG_API.format(token=token, method="sendMessage"),
            data=data, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=15)
        return True
    except Exception as e:
        print(f"[messaging] telegram_send failed: {e}")
        return False


def telegram_lang(update_lang: Optional[str]) -> str:
    """Telegram's from.language_code → our supported set (en/es/pt)."""
    base = (update_lang or "en").split("-")[0].split("_")[0].lower()
    return base if base in ("en", "es", "pt") else "en"


def format_ask_for_telegram(payload: dict, language: str = "en") -> str:
    """Render an /ask payload as readable chat text (no rich cards)."""
    p = payload or {}
    lines = []
    read = (p.get("read") or p.get("why") or "").strip()
    if read:
        lines.append(read)
    timing = (p.get("timing") or "").strip()
    if timing and timing.lower() not in read.lower():
        lines.append({"es": "🗓 Ventana: ", "pt": "🗓 Janela: "}.get(language, "🗓 Window: ") + timing)
    nxt = (p.get("next") or "").strip()
    if nxt:
        lines.append(("→ " + nxt))
    pc = p.get("practice_cta") or {}
    if pc.get("available") and pc.get("label"):
        step = (pc.get("step") or "").strip()
        body = "🧘 " + pc["label"] + (("\n" + step) if step else "")
        lines.append(body)
    sq = [q for q in (p.get("suggested_questions") or []) if isinstance(q, str) and q.strip()][:3]
    if sq:
        head = {"es": "También puedes preguntar:", "pt": "Você também pode perguntar:"}.get(
            language, "You could also ask:")
        lines.append(head + "\n" + "\n".join("• " + q for q in sq))
    out = "\n\n".join(lines).strip()
    return out or {"es": "No pude leer una señal clara ahora — intenta de nuevo en un momento.",
                   "pt": "Não consegui ler um sinal claro agora — tente novamente em instantes.",
                   }.get(language, "I couldn't read a clear signal just now — try again in a moment.")
