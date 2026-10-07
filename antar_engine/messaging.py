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
                        channel: str = "telegram", extra: Optional[dict] = None) -> dict:
    """Create a pending link row; returns {available, code} (or available:False
    when the table isn't set up yet). `extra` = additional columns (e.g. consent)."""
    code = gen_link_code()
    row = {
        "chart_id": chart_id, "user_id": user_id, "channel": channel,
        "link_code": code, "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    row.update(extra or {})
    try:
        _insert_link_row(sb, row)
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
    # [tg-disclaimer 2026-10-05] same domain disclaimer the app card and WhatsApp carry;
    # plain text (Telegram is sent without a parse mode, so no italic markers)
    dz = p.get("disclaimer")
    if isinstance(dz, str) and dz.strip():
        lines.append(re.sub(r"\s+", " ", dz.strip()))
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
import os
import re
import time
import urllib.parse

_TWILIO_MSG_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
WA_MAX_CHARS = 1600          # Twilio's per-message body limit for WhatsApp
WA_WINDOW_SECONDS = 24 * 3600
WA_LINK_CODE_MAX_AGE_MIN = 15
# [whatsapp-consent] Bump when the consent wording shown in the app changes; the
# backend only links a number whose row carries consent to the CURRENT version.
WA_CONSENT_VERSION = "wa-2026-10-06"


# [wa-marketing 2026-10-05] Offers / news on WhatsApp are a SEPARATE, optional, unticked opt-in (Meta
# WhatsApp Business policy + TCPA / DPDP / LGPD / GDPR): never implied by linking or by the Terms box.
WA_MARKETING_CONSENT_VERSION = "wa-mkt-2026-10-05"
# optional columns (sql_wa_marketing_consent.sql); a write that carries them retries without them if the
# columns don't exist yet — linking must never fail because marketing consent can't be recorded
OPTIONAL_LINK_COLS = ("marketing_opt_in", "marketing_opt_in_at", "marketing_consent_version",
                      "alerts_opt_in", "alerts_opt_in_at",
                      "training_opt_in", "training_opt_in_at", "training_consent_version")

# [wa-training 2026-10-06] A THIRD, separate, optional, unticked opt-in: may Antar learn from this
# person's de-identified conversations to improve its own model. Never implied by linking, the Terms
# or the offers opt-in. Wording lives in docs/WA_TRAINING_CONSENT_wording.md; bump on any change.
WA_TRAINING_CONSENT_VERSION = "wa-train-2026-10-06"


def training_row(opt_in: bool) -> dict:
    """Columns recording the training opt-in (off unless explicitly given; withdrawing clears it)."""
    on = bool(opt_in)
    return {"training_opt_in": on,
            "training_opt_in_at": datetime.now(timezone.utc).isoformat() if on else None,
            "training_consent_version": WA_TRAINING_CONSENT_VERSION if on else None}


def can_train(link: Optional[dict]) -> bool:
    """Only a linked number that opted in to training under the current wording."""
    l = link or {}
    return (l.get("status") == "linked" and l.get("training_opt_in") is True
            and l.get("training_consent_version") == WA_TRAINING_CONSENT_VERSION)


def marketing_row(opt_in: bool) -> dict:
    """Columns recording the separate offers/news opt-in (off unless explicitly ticked)."""
    on = bool(opt_in)
    return {"marketing_opt_in": on,
            "marketing_opt_in_at": datetime.now(timezone.utc).isoformat() if on else None,
            "marketing_consent_version": WA_MARKETING_CONSENT_VERSION if on else None}


def alerts_row(opt_in: bool) -> dict:
    on = bool(opt_in)
    return {"alerts_opt_in": on, "alerts_opt_in_at": datetime.now(timezone.utc).isoformat() if on else None}


def _insert_link_row(sb, row: dict):
    """Insert a messaging_links row; on an unknown optional column, retry without the optional columns."""
    try:
        return sb.table("messaging_links").insert(row).execute()
    except Exception as e:
        # a missing COLUMN names it ("Could not find the 'marketing_opt_in' column…" / "column … does not
        # exist"); a missing TABLE does not — only the former is retried
        msg_ = str(e)
        if not any(k in row and k in msg_ for k in OPTIONAL_LINK_COLS):
            raise
        print(f"[messaging] optional consent columns missing — linking without them: {e}")
        return sb.table("messaging_links").insert(
            {k: v for k, v in row.items() if k not in OPTIONAL_LINK_COLS}).execute()


def can_send_marketing(link: Optional[dict]) -> bool:
    """Only a linked number that explicitly opted in to offers, under the current marketing wording."""
    l = link or {}
    return (l.get("status") == "linked" and l.get("marketing_opt_in") is True
            and l.get("marketing_consent_version") == WA_MARKETING_CONSENT_VERSION)


# ── [wa-policy 2026-10-05] in-chat data-policy acceptance ──────────────────────
# Owner: like Wompi's "Política de tratamiento de datos — para continuar, acepta…". Colombia's Ley 1581 de
# 2012 (and India DPDP / Brazil LGPD) want PRIOR, EXPRESS, informed authorisation before personal data is
# processed. A number that hasn't accepted the CURRENT wording (WA_CONSENT_VERSION) is asked first; nothing
# else happens until it accepts. App-linked numbers already accepted in the app and aren't asked again.
WA_POLICY_URL = os.getenv("WA_POLICY_URL") or "https://antar.world/privacy"
_POLICY_YES = frozenset({"acepto", "accept", "i accept", "accepted", "aceito", "aceptar", "aceitar", "yes i accept",
                         "si acepto", "sí acepto", "sim aceito", "manzoor", "manzoor hai", "agree", "i agree",
                         "de acuerdo", "concordo", "1"})
_POLICY_NO = frozenset({"no acepto", "no", "não", "nao", "não aceito", "nao aceito", "decline", "i decline",
                        "don't accept", "do not accept", "nahi", "manzoor nahi", "2"})


TERMS_URL = os.getenv("WA_TERMS_URL") or "https://antar.world/terms"


def parse_optin_reply(body: str, choice_id: str = "") -> Optional[str]:
    """'yes' / 'no' to an optional alerts / offers / training question (buttons or typed)."""
    if choice_id.startswith("opt:"):
        return choice_id.rsplit(":", 1)[-1] if choice_id.rsplit(":", 1)[-1] in ("yes", "no") else None
    t = (body or "").strip().lower().strip(" .!¡?¿*")
    if t in ("yes", "y", "si", "sí", "sim", "haan", "ha", "1", "yes please", "claro", "ok"):
        return "yes"
    if t in ("no", "n", "não", "nao", "nahi", "2", "no thanks", "no gracias", "não obrigado", "skip"):
        return "no"
    return None


def policy_url(lang: str = "en") -> str:
    l = (lang or "en").lower()
    l = "es" if l.startswith("es") else "pt" if l.startswith("pt") else "en"
    return WA_POLICY_URL + ("" if l == "en" else ("&" if "?" in WA_POLICY_URL else "?") + "lang=" + l)


def parse_policy_reply(body: str, choice_id: str = "") -> Optional[str]:
    """'yes' / 'no' for an answer to the policy prompt, else None."""
    if choice_id in ("pol:yes", "pol:no"):
        return choice_id.split(":")[1]
    t = (body or "").strip().lower().strip(" .!¡?¿*")
    if t in _POLICY_YES:
        return "yes"
    if t in _POLICY_NO:
        return "no"
    return None


def policy_accepted(sb, number: str) -> Optional[bool]:
    """Has this number accepted the CURRENT wording in chat? None when the table isn't set up yet."""
    try:
        rows = (sb.table("wa_policy_acceptances").select("decision")
                .eq("number", wa_number(number)).eq("policy_version", WA_CONSENT_VERSION)
                .order("created_at", desc=True).limit(1).execute()).data or []
        return bool(rows) and rows[0].get("decision") == "accepted"
    except Exception as e:
        if _table_missing(e):
            return None
        print(f"[wa-policy] lookup failed: {e}")
        return None


def policy_state(sb, number: str, link: Optional[dict]) -> str:
    """'ok' (accepted the current wording — in the app or in chat), 'needed', or 'unknown' (storage not set
    up: fail open to today's behaviour rather than lock everyone out)."""
    if link and link.get("consent_version") == WA_CONSENT_VERSION:
        return "ok"
    acc = policy_accepted(sb, number)
    if acc is None:
        return "unknown"
    return "ok" if acc else "needed"


def record_policy(sb, number: str, decision: str, lang: str = "en", link: Optional[dict] = None) -> bool:
    """Append-only evidence row; on acceptance a linked number's consent is refreshed to the current wording."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        sb.table("wa_policy_acceptances").insert({
            "number": wa_number(number), "policy_version": WA_CONSENT_VERSION,
            "decision": "accepted" if decision == "yes" else "declined",
            "language": (lang or "en")[:12], "policy_url": policy_url(lang), "source": "whatsapp",
            "created_at": now}).execute()
    except Exception as e:
        print(f"[wa-policy] record failed: {e}")
        return False
    if decision == "yes" and link and link.get("id"):
        try:
            sb.table("messaging_links").update(consent_row("whatsapp")).eq("id", link["id"]).execute()
        except Exception as e:
            print(f"[wa-policy] link consent refresh failed: {e}")
    return True


def consent_row(source: str) -> dict:
    """Columns recording the user's WhatsApp opt-in + Terms/Privacy acceptance."""
    return {"consent_at": datetime.now(timezone.utc).isoformat(),
            "consent_version": WA_CONSENT_VERSION, "consent_source": source}


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
    from antar_engine import wa_numbers as _wn
    sender = _wn.effective_sender() or os.getenv("TWILIO_WHATSAPP_FROM")   # pool-aware: the number this user writes to
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
            _r = urllib.request.urlopen(req, timeout=15)
            try:
                _osid = json.loads(_r.read()).get("sid", "")
            except Exception:
                _osid = ""
            from antar_engine import wa_log as _wl
            _wl.record("out", to, part, sender=sender, sid=_osid)
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
    if low in ("tips", "tip", "consejos", "dicas", "guide", "how to use", "rules"):
        return ("tips", "")
    if low in ("stop training", "stop learning", "training off", "parar entrenamiento",
               "parar entrenamiento de ia", "parar treinamento", "training band", "stop ai training"):
        return ("training_off", "")
    if low in ("stop alerts", "alerts off", "no alerts", "parar alertas", "sin alertas",
               "sem alertas", "alerts band", "alert band"):
        return ("alerts_off", "")
    if low in ("stop offers", "stop promos", "stop promotions", "no offers", "no promos", "stop marketing",
               "parar ofertas", "sin ofertas", "sin promociones", "sem ofertas", "parar promoções",
               "parar promocoes", "offers band", "offer band", "promotion band"):
        return ("marketing_off", "")
    return ("", "")


def bind_link_whatsapp(sb, code: str, number: str, consent: Optional[dict] = None) -> Optional[str]:
    """Bind a pending in-app code to a WhatsApp number (Path A). Enforces
    uniqueness: the number and the account each keep ONE active whatsapp link —
    the newest proven link wins, older ones are revoked. Returns chart_id.
    [wa-qr-consent 2026-10-06] Consent is normally given IN CHAT after the QR scan (Terms + Privacy +
    receiving messages, ACCEPT); pass it as `consent` (consent_row("whatsapp")). A code with no consent —
    neither recorded in the app nor passed here — is never bound."""
    code = (code or "").strip()
    number = wa_number(number)
    if not code or not number:
        return None
    try:
        rows = (sb.table("messaging_links").select("*")
                .eq("link_code", code).eq("channel", "whatsapp")
                .eq("status", "pending").limit(1).execute()).data or []
        if not rows:
            return None
        row = rows[0]
        if not row.get("consent_at") and not consent:   # [whatsapp-consent] never link without opt-in
            print("[whatsapp] bind refused: pending code has no recorded consent")
            return None
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
        (sb.table("messaging_links").update(dict({
            "channel_user_id": number, "status": "linked", "link_code": None,
            "linked_at": datetime.now(timezone.utc).isoformat(),
        }, **(consent or {}))).eq("id", row["id"]).execute())
        return row["chart_id"]
    except Exception as e:
        if _table_missing(e):
            return None
        print(f"[whatsapp] bind_link failed: {e}")
        return None


def peek_pending_code(sb, code: str) -> Optional[dict]:
    """The pending WhatsApp link row for a code, if it exists and hasn't expired (no writes)."""
    code = (code or "").strip()
    if not code:
        return None
    try:
        rows = (sb.table("messaging_links").select("*").eq("link_code", code).eq("channel", "whatsapp")
                .eq("status", "pending").limit(1).execute()).data or []
    except Exception as e:
        if not _table_missing(e):
            print(f"[whatsapp] peek code failed: {e}")
        return None
    if not rows:
        return None
    try:
        created = datetime.fromisoformat(str(rows[0].get("created_at")).replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - created).total_seconds() / 60 > WA_LINK_CODE_MAX_AGE_MIN:
            return None
    except Exception:
        pass
    return rows[0]


def hold_code_for_number(sb, code: str, number: str) -> bool:
    """[wa-qr-consent] The QR / code arrived but the number hasn't accepted the policy yet: remember which
    number sent it (row stays 'pending', so it is NOT linked) until they reply ACCEPT."""
    row = peek_pending_code(sb, code)
    if not row:
        return False
    try:
        sb.table("messaging_links").update({"channel_user_id": wa_number(number)}).eq("id", row["id"]).execute()
        return True
    except Exception as e:
        print(f"[whatsapp] hold code failed: {e}")
        return False


def held_code_for(sb, number: str) -> Optional[str]:
    """The still-valid code this number sent before accepting, if any."""
    try:
        rows = (sb.table("messaging_links").select("*").eq("channel", "whatsapp").eq("status", "pending")
                .eq("channel_user_id", wa_number(number)).order("created_at", desc=True).limit(1)
                .execute()).data or []
    except Exception:
        return None
    if not rows or not rows[0].get("link_code"):
        return None
    return rows[0]["link_code"] if peek_pending_code(sb, rows[0]["link_code"]) else None


def link_whatsapp_direct(sb, chart_id: str, user_id: Optional[str], number: str,
                         consent: Optional[dict] = None) -> bool:
    """Path B: the signed-in user confirmed a number proven by a signed token.
    `consent` (consent_row) is required — no opt-in, no link."""
    number = wa_number(number)
    if not (chart_id and number and consent):
        return False
    try:
        _revoke_whatsapp(sb, number=number, user_id=user_id)
        row = {
            "chart_id": chart_id, "user_id": user_id, "channel": "whatsapp",
            "channel_user_id": number, "status": "linked", "link_code": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "linked_at": datetime.now(timezone.utc).isoformat(),
        }
        row.update(consent)
        _insert_link_row(sb, row)
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


def make_connect_token(secret: str, number: str, ttl_s: int = 15 * 60, sender: str = "") -> str:
    """Signed, expiring token carrying a Twilio-verified number (Path B link) and, when the
    deployment runs a number pool, the Antar number that person wrote to (so the welcome goes out
    from the same number — the 24h window belongs to it)."""
    payload = {"n": wa_number(number), "e": int(time.time()) + ttl_s, "r": secrets.token_hex(4)}
    if sender:
        payload["s"] = wa_number(sender)
    body = base64.urlsafe_b64encode(json.dumps(
        payload, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def read_connect_token(secret: str, token: str) -> Optional[str]:
    """The number inside a valid, unexpired token, else None."""
    return (read_connect_token_full(secret, token) or {}).get("number") or None


def read_connect_token_full(secret: str, token: str) -> Optional[dict]:
    """{'number', 'sender'} from a valid, unexpired token, else None."""
    try:
        body, sig = (token or "").rsplit(".", 1)
        good = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(good, sig):
            return None
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if int(data.get("e") or 0) < time.time():
            return None
        n = wa_number(data.get("n"))
        return {"number": n, "sender": wa_number(data.get("s"))} if n else None
    except Exception:
        return None


def _wa_disclaimer(p: dict) -> str:
    """The payload's domain disclaimer as one WhatsApp italic line, or ''."""
    dz = (p or {}).get("disclaimer")
    if not isinstance(dz, str) or not dz.strip():
        return ""
    return "_" + re.sub(r"\s+", " ", dz.strip()) + "_"


def format_ask_for_whatsapp(payload: dict, language: str = "en") -> str:
    """Telegram's chat rendering + WhatsApp markup (*bold* verdict, _italic_ labels)."""
    p = payload or {}
    text = format_ask_for_telegram(p, language)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)          # markdown bold → WA bold
    _dz = _wa_disclaimer(p)
    if _dz and _dz.strip("_") not in text:
        text = f"{text}\n\n{_dz}"
    verdict = p.get("verdict")
    if isinstance(verdict, str) and verdict.strip() and verdict.strip().lower() not in text.lower()[:80]:
        text = f"*{verdict.strip()}*\n\n{text}"
    return text


def whatsapp_status(sb, user_id: str) -> dict:
    """The signed-in user's active WhatsApp link, for the app's settings row.
    Never returns the full number — only its last 4 digits."""
    try:
        rows = (sb.table("messaging_links").select("*")
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
            "chart_id": r.get("chart_id"), "linked_at": r.get("linked_at"),
            "alerts_opt_in": bool(r.get("alerts_opt_in")),
            "marketing_opt_in": can_send_marketing(r)}


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


_OPENER = re.compile(r"^[A-ZÁÉÍÓÚÑ][\w'-]{1,20},\s")      # "Raman, the wait is real…"
# An opener is only small talk when it's about feelings; "Raman, tomorrow looks
# like a day to protect…" IS the answer and stays the bold line. EN/ES/PT/Hinglish.
_EMPATHY = re.compile(
    r"(?i)\b(wait|waiting|frustrat\w*|hard|heavy|tough|worr\w*|anxious|understand|"
    r"feel\w*|hear you|carrying|exhaust\w*|tired|lonely|hurt\w*|"
    r"espera|frustra\w*|dif[ií]cil|pesad\w*|preocupa\w*|entiendo|sientes|cansad\w*|"
    r"esperar|frustrante|entendo|sente|cansativ\w*|preocupad\w*|"
    r"intezaar|pareshan|mushkil|samajh|thak\w*)\b")


def _norm_q(q: str) -> set:
    return set(re.findall(r"[a-záéíóúñãõç]+", (q or "").lower())) - {
        "is", "the", "for", "me", "my", "a", "how", "what", "de", "la", "el", "o", "para", "mi", "meu"}


def _same_question(a: str, b: str) -> bool:
    x, y = _norm_q(a), _norm_q(b)
    return bool(x and y) and len(x & y) / len(x | y) >= 0.6
_OFFER = re.compile(
    r"(?i)^(want me to|shall i|should i (look|check)|would you like( me)? to|do you want me to|"
    r"quieres que|te gustar[ií]a que|quer que|gostaria que|kya main|kya aap chahte)")


def _split_sentences(text: str) -> list:
    return [x.strip() for x in _SENT_END.split(text.strip()) if x.strip()]


# [whatsapp-compact 2026-10-02] WhatsApp collapses long messages behind "Read
# more", which hid the numbered follow-ups on every answer. Compact mode keeps
# the bold answer, one short supporting sentence, the window and the move; the
# full read is one reply away ("more"). The practice line is shown at most once
# a day per practice (the caller decides via include_practice).
_TIMING_HINT = re.compile(
    r"(?i)\b(window|morning|afternoon|evening|tonight|midday|noon|before|after|until|"
    r"today|tomorrow|weeks?|months?|days?|\d{1,2}:\d{2}|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
    r"mañana|tarde|noche|semana|mes|manhã|noite|mês|subah|shaam|raat|hafte|mahine)\b")
# The WHOLE message (answer + follow-ups) must fit before WhatsApp folds it; the
# caller's one-line "more" hint (~40 chars) rides on top. Live: 650 chars folded.
_WHEN_Q = re.compile(
    r"(?i)\b(when|what time|which (day|week|month|year|date)|how soon|how long|by when|"
    r"best time|today|tomorrow|this week|next week|cu[aá]ndo|qu[eé] d[ií]a|mañana|"
    r"quando|que dia|amanhã|kab|aaj|kal)\b")
_SPECIFIC_TIME = re.compile(
    r"(?i)\b(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|june?|july?|aug(ust)?|sep(t(ember)?)?|"
    r"oct(ober)?|nov(ember)?|dec(ember)?|enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|octubre|noviembre|diciembre|janeiro|fevereiro|março|maio|junho|julho|"
    r"setembro|outubro|novembro|dezembro|\d{1,2}:\d{2}|\d{4})\b")
WA_COMPACT_BUDGET = 500
WA_MORE_WORDS = frozenset({"more", "full", "read more", "tell me more", "más", "mas info",
                           "leer más", "mais", "ver mais", "aur batao", "poora batao",
                           "detail", "details"})


# [whatsapp-yesno 2026-10-02] The app has a Yes/No toggle (KP Prashna); WhatsApp
# has no toggle, so a question SHAPED as yes/no goes to KP automatically.
# A choice ("…alone OR with a partner?") is not yes/no. EN/ES/PT/Hinglish.
_YN_START = re.compile(
    r"(?i)^\s*¿?\s*("
    r"will|would|should|shall|is|are|am|can|could|do|does|did|has|have|was|were|may|might|"
    r"voy a|vas a|va a|debo|debería|deberia|será|sera|puedo|podré|podre|tendré|tendre|"
    r"conseguiré|conseguire|lograré|lograre|me va|hay|habrá|habra|es buen|está|esta bien|"
    r"vou|devo|deveria|posso|poderei|terei|vai|consigo|conseguirei|é bom|e bom|haverá|"
    r"kya)\b")
_YN_END_HINGLISH = re.compile(r"(?i)\b(hoga|hogi|honge|milega|milegi|karun|karoon|chahiye|"
                              r"ho jayega|ho jayegi|banega|banegi)\s*\??\s*$")
_YN_CHOICE = re.compile(r"(?i)\b(or|ou|ya|either|whether)\b")
_YN_CHOICE_ES = re.compile(r"(?i)\bo\b")     # Spanish "or" — but Portuguese "the"
_YN_OPEN = re.compile(r"(?i)\b(when|where|which|what|how|why|who|cu[aá]ndo|d[oó]nde|qu[eé]|"
                      r"c[oó]mo|quando|onde|como|kab|kahan|kaise|kyun|kaun)\b")


def is_yesno_question(text: str) -> bool:
    t = (text or "").strip()
    if not t or len(t) > 200 or _YN_CHOICE.search(t):
        return False
    if t.lstrip().startswith("¿") and _YN_CHOICE_ES.search(t):
        return False
    if _YN_START.search(t):
        first = re.sub(r"^\s*¿?\s*", "", t).split()[0].lower() if t.split() else ""
        # "Is it…/Will…" are yes/no, but a later open word ("Will you tell me
        # WHEN…") makes it an open question
        return not _YN_OPEN.search(t) or first == "kya"
    if _YN_END_HINGLISH.search(t) and not _YN_OPEN.search(t):
        return True
    # [question-forms 2026-10-03] the shared lexicon's yes/no forms (will / should /
    # could / would in EN/ES/PT/Hinglish — "me conviene…", "vale a pena…", "…chalega",
    # "…sakta") when no open word decides it
    from antar_engine import question_forms as _qf
    forms = _qf.detect(t)
    return bool(forms) and _qf.primary(t) in _qf.YES_NO_FORMS and not (set(forms) & _qf.OPEN_FORMS)


_LEAN_HEAD = {
    "en": {"yes": "Leaning yes.", "not_now": "Not right now — the timing isn't there yet.",
           "conditional": "Possible — on one condition.", "no": "Leaning no."},
    "es": {"yes": "Inclina a que sí.", "not_now": "Ahora no — el momento aún no llega.",
           "conditional": "Posible — con una condición.", "no": "Inclina a que no."},
    "pt": {"yes": "Tende a sim.", "not_now": "Agora não — o momento ainda não chegou.",
           "conditional": "Possível — com uma condição.", "no": "Tende a não."},
    "hinglish": {"yes": "Haan ki taraf jhukav hai.", "not_now": "Abhi nahi — sahi waqt abhi nahi aaya.",
                 "conditional": "Ho sakta hai — ek shart par.",
                 "no": "Na ki taraf jhukav hai."},
}
_CHECKBACK = {"en": "_I'll check back after {d} to ask if it happened._",
              "es": "_Te preguntaré después del {d} si pasó._",
              "pt": "_Vou perguntar depois de {d} se aconteceu._",
              "hinglish": "_{d} ke baad main poochunga ki hua ya nahi._"}


def _yesno_as_read(p: dict, language: str) -> dict:
    """A Yes/No payload has a lean + why and no read; give it a headline."""
    lang = language if language in _LEAN_HEAD else "en"
    head = _LEAN_HEAD[lang].get(str(p.get("lean") or "").lower())
    if not head:
        v = str(p.get("verdict") or "").upper()
        head = _LEAN_HEAD[lang]["yes" if v == "YES" else "no" if v == "NO" else "conditional"]
    q = dict(p)
    q["read"] = (head + " " + (p.get("why") or "")).strip()
    # [kp-conditions] the specific condition rides as the move line
    if p.get("condition") and not p.get("next"):
        q["next"] = f"*{p.get('condition_label') or 'What it hinges on'}:* {p['condition']}"
        # [kp-one-condition 2026-10-03] the narrated "why" restated the same
        # condition in vaguer words right above it — say it once.
        q["read"] = head
    return q


_OWN_LINE = {"en": "_…or just type your own question._",
             "es": "_…o escribe tu propia pregunta._",
             "pt": "_…ou escreva sua própria pergunta._",
             "hinglish": "_…ya apna koi bhi sawaal likhiye._"}


def format_ask_whatsapp_v2(payload: dict, language: str = "en",
                           header: Optional[str] = None, asked: str = "",
                           compact: bool = False, include_practice: bool = True) -> tuple:
    """(text, followups). Layout per the UX spec: optional 'Antar · <name>' header,
    the answer sentence in *bold* (a warm "Name, …" opener stays plain above it),
    the rest of the read, 🗓 _window_, → your move, 🧘 practice + its step, then
    numbered follow-ups (max 3). Ask's own closing offer ("Want me to…?") is
    dropped when numbered follow-ups replace it. compact=True trims to fit one
    WhatsApp screen (see WA_COMPACT_BUDGET)."""
    p = payload or {}
    # [wa-disclaimer 2026-10-05] the /ask payload carries a domain `disclaimer` (health /
    # money / legal / fertility); the app card renders it but this formatter dropped it,
    # so WhatsApp answers — incl. named Ayurvedic herbs — went out with no qualifier.
    # Never trimmed by compact mode: safety copy outranks the one-screen budget.
    disc = _wa_disclaimer(p)
    checkback = ""
    if p.get("mode") == "yesno":
        p = _yesno_as_read(p, language)
        if p.get("verify_after") and not p.get("locked"):
            try:
                _d = datetime.fromisoformat(str(p["verify_after"])[:10])
                lang_cb = language if language in _CHECKBACK else "en"
                checkback = _CHECKBACK[lang_cb].format(d=f"{_d.strftime('%b')} {_d.day}")
            except ValueError:
                checkback = ""
    fus = [q.strip() for q in (p.get("suggested_questions") or [])
           if isinstance(q, str) and q.strip() and not _same_question(q, asked)][:3]
    read = re.sub(r"\*\*(.+?)\*\*", r"\1", (p.get("read") or p.get("why") or "").strip())
    read = re.sub(r"^[\s,;:.\-—–]+", "", read)          # e.g. ", Oct 5 is…" from Ask
    sents = _split_sentences(read) if read else []
    if fus and len(sents) > 1 and sents[-1].endswith("?") and _OFFER.match(sents[-1]):
        sents = sents[:-1]
    opener = head = rest = ""
    if sents:
        if (len(sents) > 1 and _OPENER.match(sents[0]) and len(sents[0]) <= 90
                and _EMPATHY.search(sents[0])):
            opener, sents = sents[0], sents[1:]
        head = sents[0]
        rest = " ".join(sents[1:])
        if compact:
            # keep the sentence(s) that carry WHEN (a window, a time of day, a date)
            # over general colour — the timing is what the reader acts on
            more = sents[1:]
            if _WHEN_Q.search(asked or ""):
                timed = [x for x in more if _TIMING_HINT.search(x) or _SPECIFIC_TIME.search(x)]
                # a named month / date / clock time beats a vague "months ahead"
                timed.sort(key=lambda x: 0 if _SPECIFIC_TIME.search(x) else 1)
                pick = (timed or more)[:2]
            else:
                # where / how / who / why: the substance comes first — keep the
                # supporting sentences in order (live: preferring the "coming
                # weeks" line dropped "Your network is your fastest path" and
                # left "that short list" pointing at nothing)
                pick = more[:2]
            rest = " ".join(pick)
            if len(rest) > 220:
                rest = pick[0] if len(pick[0]) <= 220 else ""
    timing = (p.get("timing") or "").strip()
    win = (f"🗓 _{_wl('window', language)}: {timing}_"
           if timing and timing.lower() not in read.lower() else "")
    nxt = (p.get("next") or "").strip()
    move = ("→ " + nxt) if nxt else ""
    pc = p.get("practice_cta") or {}
    practice = ""
    if include_practice and pc.get("available") and pc.get("label"):
        step = (pc.get("step") or "").strip()
        practice = "🧘 " + pc["label"].strip() + (("\n" + step) if step and len(step) <= 200 else "")

    def build(opener_, rest_, practice_, move_, fus_):
        parts = []
        if header:
            parts.append(f"_Antar · {header}_")
        if opener_:
            parts.append(opener_)
        if head:
            parts.append(f"*{head}*" if len(head) <= 180 else head)
        parts += [x for x in (rest_, win, move_, practice_, checkback, disc) if x]
        if fus_:
            # [followup-flows] same paragraph as the numbers → dropped when the tappable list
            # (which has its own "Ask your own" row) replaces them
            parts.append("\n".join(f"{i}  {q}" for i, q in enumerate(fus_, 1))
                         + "\n" + _OWN_LINE.get(language, _OWN_LINE["en"]))
        return "\n\n".join(parts).strip()

    text = build(opener, rest, practice, move, fus)
    if compact:
        # Over budget (whole message) → drop, in order: the practice, the warm
        # opener, the second supporting sentence, the third follow-up, the move's
        # extra sentences, then the supporting sentence. The bold answer, window,
        # the move's first sentence and two follow-ups always stay.
        rest_sents = _split_sentences(rest) if rest else []
        move_sents = _split_sentences(nxt) if nxt else []
        steps = ("practice", "opener", "rest2", "fus3", "move1", "rest")
        for step in steps:
            if len(text) <= WA_COMPACT_BUDGET:
                break
            if step == "practice":
                practice = ""
            elif step == "opener":
                opener = ""
            elif step == "rest2" and len(rest_sents) > 1:
                rest = rest_sents[0]
            elif step == "fus3":
                fus = fus[:2]
            elif step == "move1" and len(move_sents) > 1:
                move = "→ " + move_sents[0]
            elif step == "rest":
                rest = ""
            text = build(opener, rest, practice, move, fus)
    return text, fus


# ── typing indicator (Twilio Messaging v3, public beta) ──
# [whatsapp-typing] Shows "typing…" under Antar's name and marks the user's
# message read (blue ticks). Lasts until our reply is delivered or 25s; re-send
# to extend. Replaces any "Reading your chart…" holding message: the user only
# ever receives COMPLETE answers. Fail-soft (beta; may be blocked pre-approval).
_TWILIO_TYPING_API = "https://messaging.twilio.com/v3/Indicators/Typing.json"


def whatsapp_typing(message_sid: str) -> bool:
    import os
    sid, token = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
    if not (sid and token and message_sid):
        return False
    try:
        auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
        req = urllib.request.Request(
            _TWILIO_TYPING_API, method="POST",
            data=json.dumps({"channel": "WHATSAPP", "messageId": message_sid}).encode(),
            headers={"Authorization": "Basic " + auth, "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=8)
        return True
    except urllib.error.HTTPError as e:
        print(f"[whatsapp] typing failed: {e.code} {e.read()[:200]!r}")
        return False
    except Exception as e:
        print(f"[whatsapp] typing failed: {e}")
        return False


_GREETINGS = frozenset("""
hi hello hey hola oi ola olá namaste namaskar hii hiii yo hallo buenas
waiting wait still there anyone ping hello? hey? hmm
""".split())


def is_nudge(text: str) -> bool:
    """A short non-question: greeting, 'waiting', 'still there', 'ok', thanks.
    Never sent to Ask as a question."""
    t = (text or "").strip().lower().strip(" .!¡¿")
    if not t:
        return True
    if is_thanks(text) or t in ("?", "??", "???"):
        return True
    words = re.findall(r"[\w']+", t)
    if not words or len(words) > 3 or (t.endswith("?") and len(words) > 1):
        return False
    return all(w in _GREETINGS or w in _THANKS for w in words)


# ── interactive lists (Twilio Content API, twilio/list-picker) ──
# [whatsapp-lists] Numbered follow-ups/starters/chart choices become a tappable
# "Choose" list. In-session only (no Meta approval), REST-only (not TwiML), so
# they're used once replies go through the REST API. One content template per
# item count, every field a variable; created on first use and cached.
_CONTENT_API = "https://content.twilio.com/v1/Content"
_LIST_SIDS: dict = {}
LIST_MAX_ITEMS = 10


def short_title(text: str, limit: int = 24) -> str:
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    cut = t[: limit - 1].rsplit(" ", 1)[0].rstrip(",.;:—-")
    return (cut or t[: limit - 1]) + "…"


def _twilio_auth() -> Optional[str]:
    import os
    sid, token = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
    return base64.b64encode(f"{sid}:{token}".encode()).decode() if sid and token else None


def list_template_sid(n: int) -> Optional[str]:
    """ContentSid of the all-variable list-picker with n items (find or create)."""
    if n in _LIST_SIDS:
        return _LIST_SIDS[n]
    auth = _twilio_auth()
    if not auth or not (1 <= n <= LIST_MAX_ITEMS):
        return None
    name = f"antar_list_{n}_v1"
    hdr = {"Authorization": "Basic " + auth, "Content-Type": "application/json"}
    try:
        url = _CONTENT_API + "?PageSize=200"
        while url:
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=10) as r:
                page = json.loads(r.read())
            for c in page.get("contents") or []:
                if c.get("friendly_name") == name:
                    _LIST_SIDS[n] = c["sid"]
                    return c["sid"]
            url = (page.get("meta") or {}).get("next_page_url")
        variables = {"1": "Here is your answer.", "2": "Ask next"}
        items = []
        for k in range(n):
            a, b, c = 3 + 3 * k, 4 + 3 * k, 5 + 3 * k
            variables.update({str(a): f"Question {k + 1}", str(b): f"q:{k + 1}",
                              str(c): f"Full question {k + 1}"})
            items.append({"item": "{{%d}}" % a, "id": "{{%d}}" % b, "description": "{{%d}}" % c})
        body = json.dumps({"friendly_name": name, "language": "en", "variables": variables,
                           "types": {"twilio/list-picker": {
                               "body": "{{1}}", "button": "{{2}}", "items": items}}}).encode()
        with urllib.request.urlopen(urllib.request.Request(
                _CONTENT_API, data=body, headers=hdr, method="POST"), timeout=10) as r:
            sid = json.loads(r.read()).get("sid")
        if sid:
            _LIST_SIDS[n] = sid
        return sid
    except urllib.error.HTTPError as e:
        print(f"[whatsapp] list template {n} failed: {e.code} {e.read()[:200]!r}")
    except Exception as e:
        print(f"[whatsapp] list template {n} failed: {e}")
    return None


def whatsapp_send_list(to_number: str, body: str, button: str, items: list,
                       last_inbound_ts: Optional[float]) -> bool:
    """items = [(title, id, description)]. False → caller falls back to text."""
    import os
    from antar_engine import wa_numbers as _wn
    sid, sender, auth = os.getenv("TWILIO_ACCOUNT_SID"), (_wn.effective_sender() or os.getenv("TWILIO_WHATSAPP_FROM")), _twilio_auth()
    to = wa_number(to_number)
    items = list(items)[:LIST_MAX_ITEMS]
    if not (sid and sender and auth and to and items and len(body) <= 1024):
        return False
    if not wa_window_open(last_inbound_ts):
        return False
    content_sid = list_template_sid(len(items))
    if not content_sid:
        return False
    if not sender.startswith("whatsapp:"):
        sender = "whatsapp:" + sender
    variables = {"1": body, "2": short_title(button, 20)}
    for k, (title, iid, desc) in enumerate(items):
        variables[str(3 + 3 * k)] = short_title(title, 24)
        variables[str(4 + 3 * k)] = (iid or "")[:200]
        variables[str(5 + 3 * k)] = short_title(desc or title, 72)
    try:
        data = urllib.parse.urlencode({"From": sender, "To": "whatsapp:" + to,
                                       "ContentSid": content_sid,
                                       "ContentVariables": json.dumps(variables)}).encode()
        _r = urllib.request.urlopen(urllib.request.Request(
            _TWILIO_MSG_API.format(sid=sid), data=data, method="POST",
            headers={"Authorization": "Basic " + auth,
                     "Content-Type": "application/x-www-form-urlencoded"}), timeout=15)
        try:
            _osid = json.loads(_r.read()).get("sid", "")
        except Exception:
            _osid = ""
        from antar_engine import wa_log as _wl
        _wl.record("out", to, body, sender=sender, sid=_osid, kind="list",
                   meta={"button": button, "items": [{"title": t, "id": i} for t, i, _d in items]})
        return True
    except urllib.error.HTTPError as e:
        print(f"[whatsapp] list send failed …{to[-4:]}: {e.code} {e.read()[:200]!r}")
    except Exception as e:
        print(f"[whatsapp] list send failed …{to[-4:]}: {e}")
    return False


# ── travel: where is the sender right now? ──
# [whatsapp-travel 2026-10-02] A number keeps its home area code abroad, so the
# number alone gets "today" wrong for travellers. Stronger, fresher signals win:
#   1. a shared WhatsApp location or "I'm in London" → a 14-day override;
#   2. the app's device clock, if seen in the last 48 hours;
#   3. the number (libphonenumber) — the fallback.
TRAVEL_OVERRIDE_DAYS = 14
DEVICE_TZ_FRESH_S = 48 * 3600

_IM_IN = re.compile(
    r"(?i)^\s*(?:i'?m|i am|im|currently|now|estoy|estou|main|mai)\s+"
    r"(?:in|en|em|at|currently in|now in|ahora en|agora em)?\s*"
    r"([a-záéíóúñãõçü .'-]{2,40}?)"
    r"\s*(?:now|ahora|agora|mein hoon|mein hu|me hoon|me hu|hoon)?\s*[.!]?\s*$")
_HOME_AGAIN = re.compile(
    r"(?i)^\s*(?:i'?m|i am|im|back)\s+(?:back\s+)?home\b|^\s*(?:estoy en casa|"
    r"volv[ií] a casa|estou em casa|voltei para casa|ghar aa gaya|ghar aa gayi)\b")
_NOT_A_PLACE = frozenset("""
fine good ok okay well sad tired confused stuck worried scared happy great busy
back here there home ready done lost a an the not so very really still also just
bien mal cansado cansada triste feliz bem cansada ghar theek
love trouble debt pain doubt hurry charge control danger shock denial between
transition crisis business school college office work meeting hospital bed car
traffic line queue doubt dilemma limbo pieces shape form position touch amor
deuda problemas oficina trabajo reunión dívida problema escritório trabalho reunião
pyaar pareshani karz kaam office
""".split())


def parse_travel(text: str):
    """('home', None) | ('city', 'London') | (None, None)."""
    t = (text or "").strip()
    if not t or "?" in t or len(t.split()) > 7:
        return None, None
    if _HOME_AGAIN.search(t):
        return "home", None
    m = _IM_IN.match(t)
    if not m:
        return None, None
    place = m.group(1).strip(" .'-")
    words = place.lower().split()
    if not words or words[0] in _NOT_A_PLACE or any(w in _NOT_A_PLACE for w in words[:1]):
        return None, None
    return "city", place


def tz_label(tzname: str) -> str:
    """'Asia/Kolkata' → 'Kolkata', 'America/New_York' → 'New York'."""
    return (tzname or "").split("/")[-1].replace("_", " ")


def tz_from_coords(lat, lon) -> Optional[str]:
    try:
        from timezonefinder import TimezoneFinder
        return TimezoneFinder().timezone_at(lat=float(lat), lng=float(lon))
    except Exception:
        return None



# ── KP Prashna on WhatsApp ──
# [whatsapp-prashna 2026-10-02] "prashna: will I get the job?" forces the KP path
# even when the wording isn't a clean yes/no; "skip" during the number ritual
# reads the moment horary instead of a 1-249 number.
# [whatsapp-yesno-prefix 2026-10-03] plain-language prefixes (shown in *help*):
# "yes or no: …" / "sí o no: …" / "sim ou não: …" do the same as "prashna: …".
_PRASHNA_CMD = re.compile(
    r"(?i)^\s*(?:prashna|prashn|prashan|horary|horaria|horária"
    r"|yes\s*(?:or|/|-)\s*no|s[ií]\s*(?:o|/)\s*no|sim\s*(?:ou|/)\s*n[aã]o|haan\s*(?:ya|/)\s*naa?)"
    r"\s*[:,\-]?\s+(.{3,})$")
KP_SKIP_WORDS = frozenset({"skip", "saltar", "pular", "chhodo", "chodo", "moment", "no number",
                           "sin número", "sem número", "none"})


_BARE_PRASHNA = frozenset({"prashna", "prashn", "prashan", "horary", "horaria", "horária",
                           "yes or no", "yes/no", "yesno", "yes-no", "yes no",
                           "sí o no", "si o no", "sí/no", "si/no",
                           "sim ou não", "sim ou nao", "sim/não", "sim/nao",
                           "haan ya na", "haan ya naa", "haan/na"})


def is_bare_prashna(text: str) -> bool:
    """The reply to the yes/no offer ('yes or no' / 'sí o no' / 'sim ou não' /
    'prashna') on its own: cast the question just asked."""
    t = " ".join((text or "").strip().lower().strip(" .!¡?¿*_").split())
    return t in _BARE_PRASHNA


_DETAIL_WORDS = frozenset({"detailed", "detailed reading", "detail", "details", "full", "full reading",
                           "reading", "detallada", "lectura detallada", "detalle", "completa",
                           "detalhada", "leitura detalhada", "completo", "poora", "vistar"})


def parse_answer_choice(text: str, choice_id: str = "") -> Optional[str]:
    """Reply to 'yes or no, or a detailed reading?': 'yesno' | 'detail' | None."""
    if choice_id == "yn:kp":
        return "yesno"
    if choice_id == "yn:read":
        return "detail"
    t = " ".join((text or "").strip().lower().strip(" .!¡?¿*_#").split())
    if t in ("1",) or is_bare_prashna(t):
        return "yesno"
    if t in ("2",) or t in _DETAIL_WORDS:
        return "detail"
    return None


def parse_prashna_command(text: str) -> Optional[str]:
    m = _PRASHNA_CMD.match(text or "")
    return m.group(1).strip() if m else None



_READ_CMD = re.compile(r"(?i)^\s*(?:read|regular|lectura|leitura|normal)\s*[:,\-]\s*(.{3,})$")


def parse_read_command(text: str) -> Optional[str]:
    """'read: will I…' forces a regular read even for a yes/no question."""
    m = _READ_CMD.match(text or "")
    return m.group(1).strip() if m else None



# ── voice notes (speech-to-text) ──
# [wa-voice 2026-10-03] Owner: voice-to-text on WhatsApp. A voice note arrives as
# MediaUrl0 (audio/ogg; codecs=opus). We download it from Twilio (account auth)
# and transcribe it with ElevenLabs Speech-to-Text (Scribe; auto language —
# English, Spanish, Portuguese, Hindi…). The text then goes through the normal
# Ask flow. Needs ELEVENLABS_API_KEY; kill switch WHATSAPP_VOICE=off.
VOICE_MAX_BYTES = 10 * 1024 * 1024
_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
_STT_LANG = {"eng": "en", "en": "en", "spa": "es", "es": "es", "por": "pt", "pt": "pt",
             "hin": "hinglish", "hi": "hinglish"}


def voice_enabled() -> bool:
    import os
    if (os.getenv("WHATSAPP_VOICE") or "on").strip().lower() in ("0", "off", "false", "no"):
        return False
    return bool((os.getenv("ELEVENLABS_API_KEY") or "").strip())


def is_voice(content_type: str) -> bool:
    return (content_type or "").lower().startswith("audio/")


def transcribe_voice(media_url: str, content_type: str = "audio/ogg") -> tuple:
    """(text, lang) from a Twilio voice note, or ("", None). Never raises."""
    import os
    try:
        import requests
        auth = (os.getenv("TWILIO_ACCOUNT_SID") or "", os.getenv("TWILIO_AUTH_TOKEN") or "")
        r = requests.get(media_url, auth=auth if all(auth) else None, timeout=20)
        if r.status_code != 200 or not r.content or len(r.content) > VOICE_MAX_BYTES:
            print(f"[whatsapp][voice] download failed: {r.status_code} {len(r.content or b'')}B")
            return "", None
        ext = "ogg" if "ogg" in (content_type or "") else (content_type or "audio/x").split("/")[-1][:5]
        resp = requests.post(
            _STT_URL, headers={"xi-api-key": os.getenv("ELEVENLABS_API_KEY") or ""},
            data={"model_id": "scribe_v1", "tag_audio_events": "false"},
            files={"file": (f"voice.{ext}", r.content, content_type or "audio/ogg")}, timeout=45)
        if resp.status_code != 200:
            print(f"[whatsapp][voice] stt failed: {resp.status_code} {resp.text[:200]!r}")
            return "", None
        d = resp.json()
        text = " ".join(str(d.get("text") or "").split())
        lang = _STT_LANG.get(str(d.get("language_code") or "").lower()[:3]) or \
            _STT_LANG.get(str(d.get("language_code") or "").lower()[:2])
        return text[:1000], lang
    except Exception as e:
        print(f"[whatsapp][voice] transcribe failed: {type(e).__name__}: {e}")
        return "", None
