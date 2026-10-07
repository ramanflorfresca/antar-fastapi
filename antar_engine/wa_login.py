"""[wa-scan-login 2026-10-06] "Continue with WhatsApp": the web/app shows a QR (or a button on a phone); the person
taps Send on a pre-typed message and the browser that asked is signed in as that number's account.

No link is ever pasted into a chat. The browser holds a secret (`browser_token`) that only it knows; the code on
the QR is useless without it, so a forwarded or photographed QR cannot sign anyone in. Codes are one-use and live
2 minutes. Storage: `wa_login_codes` (sql_wa_login_codes.sql); until it exists the feature reports unavailable.
"""
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

TTL_S = 120
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"      # no 0/O/1/I/L


def sign_in_text(code: str) -> str:
    return f"Hi Antar! Sign me in: {code}"


_RX = re.compile(r"(?i)\b(?:sign me in|sign in|log me in|login|log in|iniciar sesi[oó]n|entrar|"
                 r"inicia mi sesi[oó]n|me conecta)\s*[:#-]?\s*([A-Za-z0-9]{6})\s*[.!]?\s*$")


def parse_login(text: str) -> Optional[str]:
    """The code from 'Hi Antar! Sign me in: K7Q2MX' (any language edits), else None."""
    m = _RX.search((text or "").strip())
    return m.group(1).upper() if m else None


T = {
    "ok": {"en": "✅ Signed in — you can go back to your browser.",
           "es": "✅ Sesión iniciada — ya puedes volver a tu navegador.",
           "pt": "✅ Login feito — pode voltar ao navegador.",
           "hinglish": "✅ Sign-in ho gaya — ab aap browser par wapas ja sakte hain."},
    "bad": {"en": "That sign-in code isn't valid any more. Tap *Continue with WhatsApp* again for a fresh one.",
            "es": "Ese código ya no es válido. Toca *Continuar con WhatsApp* otra vez para uno nuevo.",
            "pt": "Esse código não vale mais. Toque em *Continuar com o WhatsApp* de novo para um novo.",
            "hinglish": "Yeh sign-in code ab valid nahi hai. Naya code lene ke liye *Continue with WhatsApp* dobara dabaiye."},
    "no_account": {"en": "I don't have an account for this number yet. Say *hi* and I'll set you up right here in chat.",
                   "es": "Aún no tengo una cuenta para este número. Escribe *hola* y te la creo aquí mismo.",
                   "pt": "Ainda não tenho uma conta para este número. Diga *oi* e eu crio aqui mesmo no chat.",
                   "hinglish": "Is number ka abhi koi account nahi hai. *hi* bhejiye, main yahin chat mein bana dunga."},
}


def text(key: str, lang: str) -> str:
    return T[key].get(lang) or T[key]["en"]


def _missing(e) -> bool:
    m = str(e).lower()
    return "pgrst205" in m or "could not find the table" in m or "does not exist" in m


def _hash(browser_token: str) -> str:
    return hashlib.sha256((browser_token or "").encode()).hexdigest()


def issue(sb) -> Optional[dict]:
    """New pending code + the browser's secret. None when storage isn't set up."""
    code = "".join(secrets.choice(_ALPHABET) for _ in range(6))
    browser_token = secrets.token_urlsafe(24)
    try:
        sb.table("wa_login_codes").insert({
            "code": code, "browser_hash": _hash(browser_token), "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()}).execute()
    except Exception as e:
        if not _missing(e):
            print(f"[wa-login] issue failed: {e}")
        return None
    return {"code": code, "browser_token": browser_token, "expires_in_s": TTL_S}


def _row(sb, code: str) -> Optional[dict]:
    try:
        rows = sb.table("wa_login_codes").select("*").eq("code", code).limit(1).execute().data or []
    except Exception as e:
        if not _missing(e):
            print(f"[wa-login] lookup failed: {e}")
        return None
    return rows[0] if rows else None


def _fresh(row: dict, now: Optional[datetime] = None) -> bool:
    try:
        made = datetime.fromisoformat(str(row.get("created_at")).replace("Z", "+00:00"))
    except Exception:
        return False
    return ((now or datetime.now(timezone.utc)) - made) <= timedelta(seconds=TTL_S)


def approve(sb, code: str, number: str, user_id: str) -> bool:
    """The number tapped Send: bind this pending code to its account. Only a still-pending, unexpired code."""
    row = _row(sb, code)
    if not row or row.get("status") != "pending" or not _fresh(row):
        return False
    try:
        sb.table("wa_login_codes").update({
            "status": "approved", "number": number, "user_id": user_id,
            "approved_at": datetime.now(timezone.utc).isoformat()}) \
            .eq("code", code).eq("status", "pending").execute()
        return True
    except Exception as e:
        print(f"[wa-login] approve failed: {e}")
        return False


def poll(sb, code: str, browser_token: str) -> dict:
    """{status: pending|expired|approved, user_id?}. 'approved' is returned exactly ONCE (the row is consumed
    first), and only to the browser that holds the token — a wrong token is indistinguishable from 'expired'."""
    row = _row(sb, (code or "").upper())
    if not row or not hmac.compare_digest(str(row.get("browser_hash") or ""), _hash(browser_token)):
        return {"status": "expired"}
    st = row.get("status")
    if st == "pending":
        return {"status": "pending"} if _fresh(row) else {"status": "expired"}
    if st != "approved" or not _fresh(row):
        return {"status": "expired"}
    try:   # consume: only one poll wins the approved → consumed flip
        res = sb.table("wa_login_codes").update({"status": "consumed"}) \
            .eq("code", row["code"]).eq("status", "approved").execute()
        if not (getattr(res, "data", None) or []):
            return {"status": "expired"}
    except Exception as e:
        print(f"[wa-login] consume failed: {e}")
        return {"status": "expired"}
    return {"status": "approved", "user_id": row.get("user_id")}
