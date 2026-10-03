"""
antar_engine/wa_templates.py — WhatsApp message templates (Meta-approved, sent
through Twilio's Content API) for the few moments Antar may write FIRST.

[wa-templates 2026-10-03] Product decision (owner): WhatsApp is the conversation
+ return channel — retention first. Outside the 24-hour window WhatsApp only
delivers pre-approved templates, so the "bring people back" moments need them:

  antar_checkin_v1        "did it happen?" on a dated reading (outcome loop)
  antar_window_alert_v1   an alert the person turned on: a window opens
  antar_chapter_alert_v1  an alert the person turned on: a new chapter starts
  antar_answer_ready_v1   an answer we owe them that missed the 24h window

Rules baked in (Meta utility-template policy + Antar's own):
  * UTILITY only: each is tied to something the person asked for or opted into
    (a reading they got, alerts they switched on). No promotion, no prices, no
    "upgrade", no emoji-heavy hype — that gets reclassified as marketing (paid,
    blockable) or rejected.
  * Never a variable at the very start or end of the body; no two variables
    side by side; quick-reply titles ≤ 20 chars.
  * EN / ES / PT-BR. Hinglish readers get English (Meta has no Latin-script
    Hindi locale; a mismatched language is a rejection reason).
  * Each live template's ContentSid comes from env WA_TPL_<NAME>_<LANG>, e.g.
    WA_TPL_ANTAR_CHECKIN_V1_ES. Missing env = template not approved yet → the
    caller falls back (push / in-app). Nothing here can send without approval.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

LANGS = ("en", "es", "pt_BR")

TEMPLATES = {
    "antar_checkin_v1": {
        "category": "UTILITY",
        "variables": {"1": "Harleen", "2": "Oct 2",
                      "3": "a new client signs between Nov 2026 and Jan 2027"},
        "body": {
            "en": "Hi {{1}}, on {{2}} your Antar reading said: “{{3}}”. "
                  "Did it happen? Your answer helps Antar get more accurate for you.",
            "es": "Hola {{1}}, el {{2}} tu lectura de Antar dijo: “{{3}}”. "
                  "¿Pasó? Tu respuesta ayuda a que Antar sea más preciso contigo.",
            "pt_BR": "Oi {{1}}, em {{2}} sua leitura do Antar disse: “{{3}}”. "
                     "Aconteceu? Sua resposta ajuda o Antar a ficar mais preciso para você.",
        },
        # ids 1-4 = the same numbers a typed reply uses (outcomes.OUTCOMES order)
        "buttons": {
            "en": [("Yes", "1"), ("Partly", "2"), ("No", "3"), ("Not sure yet", "4")],
            "es": [("Sí", "1"), ("En parte", "2"), ("No", "3"), ("Aún no sé", "4")],
            "pt_BR": [("Sim", "1"), ("Em parte", "2"), ("Não", "3"), ("Ainda não sei", "4")],
        },
    },
    "antar_window_alert_v1": {
        "category": "UTILITY",
        "variables": {"1": "Harleen", "2": "your strongest money window", "3": "Oct 14"},
        "body": {
            "en": "Hi {{1}}, an alert you turned on in Antar: {{2}} opens on {{3}}. "
                  "Reply here if you want to know how to make the most of it.",
            "es": "Hola {{1}}, una alerta que activaste en Antar: {{2}} se abre el {{3}}. "
                  "Responde aquí si quieres saber cómo aprovecharla.",
            "pt_BR": "Oi {{1}}, um alerta que você ativou no Antar: {{2}} abre em {{3}}. "
                     "Responda aqui se quiser saber como aproveitar.",
        },
        "buttons": {
            "en": [("How do I use it?", "alert_how"), ("Stop alerts", "alert_stop")],
            "es": [("¿Cómo la uso?", "alert_how"), ("Parar alertas", "alert_stop")],
            "pt_BR": [("Como aproveito?", "alert_how"), ("Parar alertas", "alert_stop")],
        },
    },
    "antar_chapter_alert_v1": {
        "category": "UTILITY",
        "variables": {"1": "Harleen", "2": "Nov 12", "3": "building your reputation at work"},
        "body": {
            "en": "Hi {{1}}, an alert you turned on in Antar: a new chapter in your reading "
                  "begins on {{2}}, and it centres on {{3}}. Reply here to ask how to use it well.",
            "es": "Hola {{1}}, una alerta que activaste en Antar: un nuevo capítulo de tu "
                  "lectura empieza el {{2}} y se centra en {{3}}. Responde aquí para saber "
                  "cómo aprovecharlo.",
            "pt_BR": "Oi {{1}}, um alerta que você ativou no Antar: um novo capítulo da "
                     "sua leitura começa em {{2}} e gira em torno de {{3}}. Responda aqui "
                     "para saber como aproveitar.",
        },
        "buttons": {
            "en": [("How do I use it?", "alert_how"), ("Stop alerts", "alert_stop")],
            "es": [("¿Cómo lo uso?", "alert_how"), ("Parar alertas", "alert_stop")],
            "pt_BR": [("Como aproveito?", "alert_how"), ("Parar alertas", "alert_stop")],
        },
    },
    "antar_answer_ready_v1": {
        "category": "UTILITY",
        "variables": {"1": "Harleen", "2": "When will my career take off?"},
        "body": {
            "en": "Hi {{1}}, your Antar answer to “{{2}}” is ready. Tap below to see it.",
            "es": "Hola {{1}}, tu respuesta de Antar a “{{2}}” está lista. "
                  "Toca abajo para verla.",
            "pt_BR": "Oi {{1}}, sua resposta do Antar para “{{2}}” está pronta. "
                     "Toque abaixo para ver.",
        },
        "buttons": {
            "en": [("Show my answer", "show_answer")],
            "es": [("Ver mi respuesta", "show_answer")],
            "pt_BR": [("Ver minha resposta", "show_answer")],
        },
    },
}


def wa_lang(lang: str) -> str:
    """Antar language → template language (Hinglish/other → English)."""
    l = (lang or "en").lower()
    return "es" if l.startswith("es") else "pt_BR" if l.startswith("pt") else "en"


def env_key(name: str, lang: str) -> str:
    return f"WA_TPL_{name.upper()}_{wa_lang(lang).upper()}"


def template_sid(name: str, lang: str) -> Optional[str]:
    """ContentSid of an APPROVED template, or None (not approved / not set)."""
    sid = (os.getenv(env_key(name, lang)) or "").strip()
    return sid or None


def content_payload(name: str, lang: str) -> dict:
    """Twilio Content API create body (quick-reply + plain-text fallback)."""
    t = TEMPLATES[name]
    wl = wa_lang(lang)
    body = t["body"][wl]
    return {
        "friendly_name": f"{name}_{wl.lower()}",
        "language": wl,
        "variables": t["variables"],
        "types": {
            "twilio/quick-reply": {
                "body": body,
                "actions": [{"title": title, "id": bid} for title, bid in t["buttons"][wl]],
            },
            "twilio/text": {"body": body},
        },
    }


def _clean_var(v, limit: int = 120) -> str:
    """Template variables: one line, no newlines/tabs, no 4+ spaces (Meta rule)."""
    s = " ".join(str(v or "").split())
    return (s[: limit - 1] + "…") if len(s) > limit else s


def send(to_number: str, name: str, lang: str, variables: dict) -> bool:
    """Send an approved template (works outside the 24h window). False when the
    template isn't approved/configured or Twilio refuses — caller falls back."""
    from antar_engine.messaging import wa_number, _twilio_auth, _TWILIO_MSG_API
    content_sid = template_sid(name, lang)
    acct, sender, auth = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_WHATSAPP_FROM"), _twilio_auth()
    to = wa_number(to_number)
    if not (content_sid and acct and sender and auth and to):
        return False
    if not sender.startswith("whatsapp:"):
        sender = "whatsapp:" + sender
    vars_ = {k: _clean_var(v) for k, v in (variables or {}).items()}
    try:
        data = urllib.parse.urlencode({"From": sender, "To": "whatsapp:" + to,
                                       "ContentSid": content_sid,
                                       "ContentVariables": json.dumps(vars_)}).encode()
        urllib.request.urlopen(urllib.request.Request(
            _TWILIO_MSG_API.format(sid=acct), data=data, method="POST",
            headers={"Authorization": "Basic " + auth,
                     "Content-Type": "application/x-www-form-urlencoded"}), timeout=15)
        return True
    except urllib.error.HTTPError as e:
        print(f"[whatsapp][template] {name} failed …{to[-4:]}: {e.code} {e.read()[:200]!r}")
    except Exception as e:
        print(f"[whatsapp][template] {name} failed …{to[-4:]}: {e}")
    return False
