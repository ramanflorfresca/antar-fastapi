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


# ── WhatsApp over Twilio ──
# [whatsapp 2026-10-02] Same identity model as Telegram: messaging_links rows with
# channel="whatsapp" and channel_user_id = the sender's E.164 number. A number is
# only trusted because Twilio's request signature is verified (twilio_signature_ok);
# a number typed into a form is never trusted. Ask-only: the user always writes
# first, so every reply is inside WhatsApp's 24-hour window (wa_window_open guards
# it anyway, so a later proactive feature can't break the rule by accident).
import base64
import hashlib
import hmac
import re
import time
import urllib.parse

_TWILIO_MSG_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
WA_MAX_CHARS = 1600          # Twilio's per-message body limit for WhatsApp
WA_WINDOW_SECONDS = 24 * 3600
WA_LINK_CODE_MAX_AGE_MIN = 15


def wa_number(addr: Optional[str]) -> str:
    """'whatsapp:+919812345678' → '+919812345678' ('' when unusable)."""
    s = (addr or "").strip()
    if s.lower().startswith("whatsapp:"):
        s = s[9:]
    s = re.sub(r"[^\d+]", "", s)
    if s and not s.startswith("+"):
        s = "+" + s
    return s if re.fullmatch(r"\+\d{7,15}", s) else ""


def twilio_signature_ok(auth_token: str, url: str, params: dict, signature: str) -> bool:
    """Twilio X-Twilio-Signature check: base64(HMAC-SHA1(url + sorted k+v)).
    `params` = the POSTed form fields (first value per key)."""
    if not auth_token or not signature:
        return False
    data = url + "".join(k + (params.get(k) or "") for k in sorted(params))
    digest = hmac.new(auth_token.encode(), data.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature)


def wa_window_open(last_inbound_ts: Optional[float], now: Optional[float] = None) -> bool:
    """True while a free-form reply is allowed (< 24h since the user last wrote)."""
    if not last_inbound_ts:
        return False
    return ((now or time.time()) - float(last_inbound_ts)) < WA_WINDOW_SECONDS


def wa_split(text: str, limit: int = WA_MAX_CHARS) -> list:
    """Split on paragraph, then line, then hard breaks so each part ≤ limit."""
    text = (text or "").strip()
    if len(text) <= limit:
        return [text] if text else []
    parts, cur = [], ""
    for para in text.split("\n\n"):
        cand = (cur + "\n\n" + para) if cur else para
        if len(cand) <= limit:
            cur = cand
            continue
        if cur:
            parts.append(cur)
        while len(para) > limit:
            cut = para.rfind("\n", 0, limit)
            cut = cut if cut > limit // 2 else para.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            parts.append(para[:cut].rstrip())
            para = para[cut:].lstrip()
        cur = para
    if cur:
        parts.append(cur)
    return parts


def whatsapp_send(to_number: str, text: str, last_inbound_ts: Optional[float]) -> bool:
    """Send free-form text through Twilio. Refuses outside the 24h window (that
    needs an approved template — not in v1). Fail-soft (logs, returns False)."""
    import os
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    sender = os.getenv("TWILIO_WHATSAPP_FROM")       # e.g. whatsapp:+14155238886
    to = wa_number(to_number)
    if not (sid and token and sender and to and text):
        print("[whatsapp] send skipped: twilio env or recipient missing")
        return False
    if not wa_window_open(last_inbound_ts):
        print(f"[whatsapp] send blocked: 24h window closed for …{to[-4:]}")
        return False
    if not sender.startswith("whatsapp:"):
        sender = "whatsapp:" + sender
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    ok = True
    for part in wa_split(text):
        try:
            data = urllib.parse.urlencode(
                {"From": sender, "To": "whatsapp:" + to, "Body": part}).encode()
            req = urllib.request.Request(
                _TWILIO_MSG_API.format(sid=sid), data=data, method="POST",
                headers={"Authorization": "Basic " + auth,
                         "Content-Type": "application/x-www-form-urlencoded"})
            urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as e:
            print(f"[whatsapp] send failed …{to[-4:]}: {e.code} {e.read()[:300]!r}")
            ok = False
            break
        except Exception as e:
            print(f"[whatsapp] send failed …{to[-4:]}: {e}")
            ok = False
            break
    return ok


def parse_wa_command(text: str) -> tuple:
    """(command, arg) for channel commands, else ("", "") = an Ask question.
    Whole-message match only, so a question that merely contains 'stop' is a question."""
    t = (text or "").strip()
    m = re.fullmatch(r"(?i)(?:link|conectar|ligar|connect)\s+([A-Za-z0-9_\-]{4,32})", t)
    if m:
        return ("link", m.group(1))
    low = t.lower().strip(" .!¡?¿")
    if low in ("stop", "unlink", "parar", "desconectar", "band", "band karo", "unsubscribe"):
        return ("unlink", "")
    if low in ("help", "ayuda", "ajuda", "menu", "madad", "?"):
        return ("help", "")
    return ("", "")


def bind_link_whatsapp(sb, code: str, number: str) -> Optional[str]:
    """Bind a pending in-app code to a WhatsApp number (Path A). Enforces
    uniqueness: the number and the account each keep ONE active whatsapp link —
    the newest proven link wins, older ones are revoked. Returns chart_id."""
    code = (code or "").strip()
    number = wa_number(number)
    if not code or not number:
        return None
    try:
        rows = (sb.table("messaging_links").select("id,chart_id,user_id,created_at")
                .eq("link_code", code).eq("channel", "whatsapp")
                .eq("status", "pending").limit(1).execute()).data or []
        if not rows:
            return None
        row = rows[0]
        try:
            created = datetime.fromisoformat(str(row.get("created_at")).replace("Z", "+00:00"))
            age_min = (datetime.now(timezone.utc) - created).total_seconds() / 60
            if age_min > WA_LINK_CODE_MAX_AGE_MIN:
                sb.table("messaging_links").update({"status": "expired", "link_code": None}) \
                    .eq("id", row["id"]).execute()
                return None
        except Exception:
            pass
        _revoke_whatsapp(sb, number=number, user_id=row.get("user_id"), keep_id=row["id"])
        (sb.table("messaging_links").update({
            "channel_user_id": number, "status": "linked", "link_code": None,
            "linked_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", row["id"]).execute())
        return row["chart_id"]
    except Exception as e:
        if _table_missing(e):
            return None
        print(f"[whatsapp] bind_link failed: {e}")
        return None


def link_whatsapp_direct(sb, chart_id: str, user_id: Optional[str], number: str) -> bool:
    """Path B: the signed-in user confirmed a number proven by a signed token."""
    number = wa_number(number)
    if not (chart_id and number):
        return False
    try:
        _revoke_whatsapp(sb, number=number, user_id=user_id)
        sb.table("messaging_links").insert({
            "chart_id": chart_id, "user_id": user_id, "channel": "whatsapp",
            "channel_user_id": number, "status": "linked", "link_code": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "linked_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return True
    except Exception as e:
        print(f"[whatsapp] direct link failed: {e}")
        return False


def unlink_whatsapp(sb, number: str) -> bool:
    return _revoke_whatsapp(sb, number=wa_number(number))


def _revoke_whatsapp(sb, number: str = "", user_id: Optional[str] = None,
                     keep_id=None) -> bool:
    try:
        for col, val in (("channel_user_id", number), ("user_id", user_id)):
            if not val:
                continue
            q = (sb.table("messaging_links").update({"status": "revoked"})
                 .eq("channel", "whatsapp").eq("status", "linked").eq(col, val))
            if keep_id is not None:
                q = q.neq("id", keep_id)
            q.execute()
        return True
    except Exception as e:
        if not _table_missing(e):
            print(f"[whatsapp] revoke failed: {e}")
        return False


def make_connect_token(secret: str, number: str, ttl_s: int = 15 * 60) -> str:
    """Signed, expiring token carrying a Twilio-verified number (Path B link)."""
    body = base64.urlsafe_b64encode(json.dumps(
        {"n": wa_number(number), "e": int(time.time()) + ttl_s,
         "r": secrets.token_hex(4)}, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def read_connect_token(secret: str, token: str) -> Optional[str]:
    """The number inside a valid, unexpired token, else None."""
    try:
        body, sig = (token or "").rsplit(".", 1)
        good = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(good, sig):
            return None
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if int(data.get("e") or 0) < time.time():
            return None
        return wa_number(data.get("n")) or None
    except Exception:
        return None


def format_ask_for_whatsapp(payload: dict, language: str = "en") -> str:
    """Telegram's chat rendering + WhatsApp markup (*bold* verdict, _italic_ labels)."""
    p = payload or {}
    text = format_ask_for_telegram(p, language)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)          # markdown bold → WA bold
    verdict = p.get("verdict")
    if isinstance(verdict, str) and verdict.strip() and verdict.strip().lower() not in text.lower()[:80]:
        text = f"*{verdict.strip()}*\n\n{text}"
    return text


def whatsapp_status(sb, user_id: str) -> dict:
    """The signed-in user's active WhatsApp link, for the app's settings row.
    Never returns the full number — only its last 4 digits."""
    try:
        rows = (sb.table("messaging_links").select("chart_id,channel_user_id,linked_at")
                .eq("channel", "whatsapp").eq("user_id", user_id).eq("status", "linked")
                .order("linked_at", desc=True).limit(1).execute()).data or []
    except Exception as e:
        if not _table_missing(e):
            print(f"[whatsapp] status failed: {e}")
        return {"linked": False}
    if not rows:
        return {"linked": False}
    r = rows[0]
    return {"linked": True, "number_last4": (r.get("channel_user_id") or "")[-4:],
            "chart_id": r.get("chart_id"), "linked_at": r.get("linked_at")}


# ── WhatsApp conversation layer (UX spec 2026-10-02) ──
# Per-number conversation state lives on the link row (messaging_links.context,
# jsonb) because Railway runs several uvicorn workers — process memory isn't
# shared. Fail-open: if the column doesn't exist yet, numbered replies just
# behave like ordinary questions.
WA_OPTIONS_TTL_S = 24 * 3600

_THANKS = frozenset("""
thanks thank thx ty ok okay okk k cool great nice perfect amazing awesome got it
gracias vale genial perfecto listo obrigado obrigada valeu beleza otimo ótimo
shukriya dhanyavad dhanyawad theek thik accha acha badhiya
""".split()) | {"thank you", "got it", "muchas gracias", "muito obrigado",
                "muito obrigada", "thik hai", "theek hai", "bahut badhiya", "🙏", "👍", "❤️", "🙌"}


def is_thanks(text: str) -> bool:
    """A pure acknowledgement (no question in it) — answered without using quota."""
    t = (text or "").strip().lower().strip(" .!¡?¿")
    if not t or "?" in (text or "") or len(t) > 30:
        return False
    if t in _THANKS:
        return True
    words = re.findall(r"[\w']+|[^\w\s]", t)
    return bool(words) and all(w in _THANKS for w in words)


def parse_switch(text: str) -> Optional[str]:
    """'switch' → '' (show the list); 'switch Mom' / 'ask about Ana' / 'cambiar a Ana'
    → the name; anything else → None."""
    t = (text or "").strip()
    m = re.fullmatch(r"(?i)(?:switch|cambiar|trocar|badlo|change)(?:\s+(?:to|a|para|pe)?\s*(.+))?", t)
    if m:
        return (m.group(1) or "").strip(" .!?")
    m = re.fullmatch(r"(?i)(?:ask about|read|pregunta sobre|preguntar por|perguntar sobre)\s+(.+?)[\s.!?]*", t)
    if m and len(m.group(1)) <= 40:
        return m.group(1).strip()
    return None


def parse_pick(text: str) -> Optional[int]:
    """A bare digit 1-9 picks from Antar's last numbered list."""
    t = (text or "").strip().strip(".)")
    return int(t) if re.fullmatch(r"[1-9]", t) else None


def get_whatsapp_link(sb, number: str) -> Optional[dict]:
    """The active link row for a number (select * so a missing optional column
    never fails the whole call)."""
    try:
        rows = (sb.table("messaging_links").select("*")
                .eq("channel", "whatsapp").eq("channel_user_id", wa_number(number))
                .eq("status", "linked").limit(1).execute()).data or []
        return rows[0] if rows else None
    except Exception as e:
        if not _table_missing(e):
            print(f"[whatsapp] get_link failed: {e}")
        return None


def link_context(link: Optional[dict]) -> dict:
    c = (link or {}).get("context")
    if isinstance(c, str):
        try:
            c = json.loads(c)
        except Exception:
            c = None
    return c if isinstance(c, dict) else {}


def save_link_context(sb, link: dict, ctx: dict) -> bool:
    if not link or "context" not in link:      # column not created yet → fail-open
        return False
    try:
        sb.table("messaging_links").update({"context": ctx}).eq("id", link["id"]).execute()
        link["context"] = ctx
        return True
    except Exception as e:
        print(f"[whatsapp] save context failed: {e}")
        return False


def set_link_chart(sb, link: dict, chart_id: str) -> bool:
    try:
        sb.table("messaging_links").update({"chart_id": chart_id}).eq("id", link["id"]).execute()
        link["chart_id"] = chart_id
        return True
    except Exception as e:
        print(f"[whatsapp] set chart failed: {e}")
        return False


def remember_options(ctx: dict, kind: str, options: list, now: Optional[float] = None) -> dict:
    """Store the numbered list we just sent: kind 'ask' (question strings) or
    'chart' ([chart_id, name] pairs)."""
    ctx = dict(ctx or {})
    ctx["options"] = {"kind": kind, "items": list(options)[:9], "at": int(time.time() if now is None else now)}
    return ctx


def pick_option(ctx: dict, n: int, now: Optional[float] = None):
    """(kind, item) for digit n from the last list, or (None, None) if expired/absent."""
    o = (ctx or {}).get("options") or {}
    items = o.get("items") or []
    if not items or (time.time() if now is None else now) - int(o.get("at") or 0) > WA_OPTIONS_TTL_S:
        return None, None
    if 1 <= n <= len(items):
        return o.get("kind"), items[n - 1]
    return None, None


def list_user_charts(sb, user_id: str, primary_id: Optional[str]) -> list:
    """[(chart_id, name, is_self)] — the user's own chart first, then saved people."""
    try:
        rows = (sb.table("charts").select("id,name,created_at").eq("user_id", user_id)
                .is_("deleted_at", "null").order("created_at").limit(20).execute()).data or []
    except Exception as e:
        print(f"[whatsapp] list charts failed: {e}")
        return []
    out = [(r["id"], (r.get("name") or "").strip() or "Chart", r["id"] == primary_id) for r in rows]
    out.sort(key=lambda x: (not x[2],))
    return out


def match_chart(charts: list, name: str):
    """The one chart whose name matches (exact, then first-name / substring)."""
    n = (name or "").strip().lower()
    if not n:
        return None
    exact = [c for c in charts if c[1].lower() == n]
    if len(exact) == 1:
        return exact[0]
    hits = [c for c in charts if n in c[1].lower() or c[1].lower().split()[0] == n]
    return hits[0] if len(hits) == 1 else None


_SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡\"'*])")


def _first_sentence(text: str) -> tuple:
    parts = _SENT_END.split(text.strip(), maxsplit=1)
    head = parts[0].strip()
    rest = parts[1].strip() if len(parts) > 1 else ""
    return head, rest


_WA_LABELS = {
    "window": {"en": "Window", "es": "Ventana", "pt": "Janela", "hinglish": "Window"},
    "also":   {"en": "Reply with a number:", "es": "Responde con un número:",
               "pt": "Responda com um número:", "hinglish": "Number bhejiye:"},
}


def _wl(key: str, lang: str) -> str:
    return _WA_LABELS[key].get(lang) or _WA_LABELS[key]["en"]


def format_ask_whatsapp_v2(payload: dict, language: str = "en",
                           header: Optional[str] = None) -> tuple:
    """(text, followups). Layout per the UX spec: optional 'Antar · <name>' header,
    *bold first sentence*, the rest of the read, 🗓 _window_, → your move,
    🧘 practice, then numbered follow-ups (max 3)."""
    p = payload or {}
    lines = []
    if header:
        lines.append(f"_Antar · {header}_")
    read = re.sub(r"\*\*(.+?)\*\*", r"\1", (p.get("read") or p.get("why") or "").strip())
    if read:
        head, rest = _first_sentence(read)
        lines.append(f"*{head}*" if 0 < len(head) <= 180 else head)
        if rest:
            lines.append(rest)
    timing = (p.get("timing") or "").strip()
    if timing and timing.lower() not in read.lower():
        lines.append(f"🗓 _{_wl('window', language)}: {timing}_")
    nxt = (p.get("next") or "").strip()
    if nxt:
        lines.append("→ " + nxt)
    pc = p.get("practice_cta") or {}
    if pc.get("available") and pc.get("label"):
        lines.append("🧘 " + pc["label"].strip())
    fus = [q.strip() for q in (p.get("suggested_questions") or [])
           if isinstance(q, str) and q.strip()][:3]
    if fus:
        lines.append("\n".join(f"{i}  {q}" for i, q in enumerate(fus, 1)))
    text = "\n\n".join(l for l in lines if l).strip()
    return text, fus
