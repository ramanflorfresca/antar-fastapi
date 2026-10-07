"""
antar_engine/wa_numbers.py — the WhatsApp sender pool and deterministic number routing.

[wa-numbers 2026-10-05] Antar runs several WhatsApp business numbers (all US-registered) and each
user is served by ONE of them, chosen by the user's country — so an Indian user always sees the same
"Antar" number, Colombians another, and a quality/ban event on one number is contained to its country.

Config (no DDL): env WA_SENDERS = JSON list, e.g.
  [{"number": "+14155550101", "label": "in-1", "countries": ["IN"], "langs": ["hinglish", "en"]},
   {"number": "+14155550102", "label": "in-2", "countries": ["IN"]},
   {"number": "+14155550103", "label": "co-1", "countries": ["CO", "AR", "MX"], "langs": ["es"]},
   {"number": "+14155550104", "label": "us-1", "countries": ["US", "CA"]},
   {"number": "+14155550199", "label": "world", "countries": ["*"]}]
  optional per sender: "paused": true (skip it for NEW assignments; existing users keep it until
  they message another number). With no WA_SENDERS the pool is the single TWILIO_WHATSAPP_FROM, so
  behaviour is unchanged until the pool is configured.

Rules
  * Assignment is a pure function of (user number, pool): candidates = senders serving the user's
    country (else the "*" senders, else everyone); among them sha256(number) picks one — stable,
    evenly spread, no state needed. Language only narrows the candidates when a sender declares
    `langs` AND a matching one exists (a number is never *required* to match the language).
  * A WhatsApp conversation (the 24h window) belongs to the business number the user wrote to, so the
    number they last messaged ALWAYS wins over the computed one (`messaging_links.context.sender`);
    proactive sends reuse it.
  * The sender in effect is carried in a ContextVar so the many send helpers need no new argument.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import os
import re
from typing import Optional

# E.164 calling code → ISO country. Longest prefix wins ("+1" is shared by US/CA; the NANP split
# below is by area code only for the countries we route differently).
_CC = {
    "1": "US", "7": "RU", "20": "EG", "27": "ZA", "30": "GR", "31": "NL", "32": "BE", "33": "FR",
    "34": "ES", "39": "IT", "44": "GB", "49": "DE", "51": "PE", "52": "MX", "53": "CU", "54": "AR",
    "55": "BR", "56": "CL", "57": "CO", "58": "VE", "60": "MY", "61": "AU", "62": "ID", "63": "PH",
    "64": "NZ", "65": "SG", "66": "TH", "81": "JP", "82": "KR", "84": "VN", "86": "CN", "90": "TR",
    "91": "IN", "92": "PK", "94": "LK", "95": "MM", "212": "MA", "234": "NG", "254": "KE",
    "351": "PT", "353": "IE", "358": "FI", "380": "UA", "420": "CZ", "506": "CR", "507": "PA",
    "591": "BO", "593": "EC", "595": "PY", "598": "UY", "880": "BD", "971": "AE", "966": "SA",
    "977": "NP", "972": "IL", "92": "PK",
}
_CA_AREA = {"204", "226", "236", "249", "250", "289", "306", "343", "365", "403", "416", "418", "431",
            "437", "438", "450", "506", "514", "519", "579", "581", "587", "604", "613", "639", "647",
            "672", "705", "709", "778", "780", "807", "819", "825", "867", "873", "902", "905"}

# a country with no sender of its own falls to its language neighbours before the global default
_NEIGHBOURS = {"CO": "es", "AR": "es", "MX": "es", "ES": "es", "CL": "es", "PE": "es", "EC": "es",
               "UY": "es", "VE": "es", "BO": "es", "PY": "es", "BR": "pt", "PT": "pt", "IN": "hinglish"}

current_sender: contextvars.ContextVar = contextvars.ContextVar("wa_sender", default="")


def country_of(number: str) -> str:
    """ISO country from an E.164 number ('' when unknown)."""
    d = re.sub(r"\D", "", number or "")
    if not d:
        return ""
    if d[0] == "1":
        return "CA" if d[1:4] in _CA_AREA else "US"
    for n in (3, 2, 1):
        if d[:n] in _CC:
            return _CC[d[:n]]
    return ""


def norm(n: Optional[str]) -> str:
    """'whatsapp:+1 (415) 555-0101' → '+14155550101'."""
    d = re.sub(r"\D", "", str(n or "").replace("whatsapp:", ""))
    return ("+" + d) if d else ""


def pool() -> list:
    """The configured senders (normalised); the single TWILIO_WHATSAPP_FROM when no pool is set."""
    raw = (os.getenv("WA_SENDERS") or "").strip()
    out = []
    if raw:
        try:
            for s in json.loads(raw):
                n = norm(s.get("number"))
                if n:
                    out.append({"number": n, "label": s.get("label") or n[-4:],
                                "countries": [str(c).upper() for c in (s.get("countries") or ["*"])],
                                "langs": [str(l).lower() for l in (s.get("langs") or [])],
                                "paused": bool(s.get("paused"))})
        except Exception as e:
            print(f"[wa-numbers] WA_SENDERS unreadable, using the default sender: {e}")
            out = []
    if not out:
        n = norm(os.getenv("TWILIO_WHATSAPP_FROM"))
        if n:
            out = [{"number": n, "label": "default", "countries": ["*"], "langs": [], "paused": False}]
    return out


def default_sender() -> str:
    p = pool()
    return p[0]["number"] if p else norm(os.getenv("TWILIO_WHATSAPP_FROM"))


def _pick(cands: list, number: str) -> str:
    cands = sorted(cands, key=lambda s: s["number"])
    h = int(hashlib.sha256(norm(number).encode()).hexdigest(), 16)
    return cands[h % len(cands)]["number"]


def assign(number: str, country: str = "", lang: str = "") -> str:
    """The sender a user (by their number, or an explicit country hint) is dedicated to. Pure/deterministic."""
    senders = [s for s in pool() if not s["paused"]] or pool()
    if not senders:
        return ""
    c = (country or country_of(number) or "").upper()
    cands = [s for s in senders if c and c in s["countries"]]
    if not cands and c in _NEIGHBOURS:
        want = _NEIGHBOURS[c]
        cands = [s for s in senders if want in s["langs"] and "*" not in s["countries"]]
    if not cands:
        cands = [s for s in senders if "*" in s["countries"]] or senders
    l = (lang or "").lower()
    if l:
        narrowed = [s for s in cands if l in s["langs"] or l[:2] in s["langs"]]
        cands = narrowed or cands
    return _pick(cands, number)


def sender_for(number: str, ctx: Optional[dict] = None, lang: str = "") -> str:
    """Who writes to this user: the number they last messaged (if still in the pool), else the assignment."""
    known = norm((ctx or {}).get("sender"))
    if known and any(s["number"] == known for s in pool()):
        return known
    chosen = assign(number, lang=lang)
    print(f"[wa-numbers] assigned …{norm(number)[-4:]} country={country_of(number) or '?'} -> {chosen}")
    return chosen


def use(sender: str):
    """Set the sender for this task/thread chain (returns the token for reset)."""
    return current_sender.set(norm(sender))


def effective_sender() -> str:
    """What a send helper should write 'From' — the context's sender, else the default."""
    cur = current_sender.get()
    if cur and (not pool() or any(s["number"] == cur for s in pool())):
        return cur
    return default_sender()


def deep_link_number(country: str = "", lang: str = "", key: str = "") -> str:
    """The number a not-yet-linked user from `country` should open (the wa.me button). `key` (the
    account id) spreads users across a country's numbers deterministically."""
    return assign(key or "anon", country=country, lang=lang) or default_sender()
