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
  * EN / ES / PT-BR / HINGLISH. Meta has no Latin-script Hindi locale, so a Hinglish template is
    submitted under the locale in env WA_HINGLISH_LOCALE (default "en"); if Meta rejects it (language
    mismatch) simply leave its ContentSid unset — Hinglish readers then get the English template.
  * Each live template's ContentSid comes from env WA_TPL_<NAME>_<LANG>, e.g.
    WA_TPL_ANTAR_CHECKIN_V1_ES / ..._HINGLISH. Missing env = template not approved yet → the
    caller falls back (push / in-app). Nothing here can send without approval.
  * Templates are approved per WhatsApp Business Account, not per number: every sender in the pool
    (antar_engine/wa_numbers.py) that sits in the same WABA shares these ContentSids.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

LANGS = ("en", "es", "pt_BR", "hinglish")

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


# ── Hinglish (Roman-script Hindi) + the policy / decision templates ─────────────
# Added after the table so each language reads as one block; merged in below.
_HINGLISH = {
    "antar_checkin_v1": (
        "Namaste {{1}}, {{2}} ko aapki Antar reading mein likha tha: “{{3}}”. "
        "Kya yeh hua? Aapka jawab Antar ko aapke liye aur sahi banata hai.",
        [("Haan", "1"), ("Thoda", "2"), ("Nahi", "3"), ("Abhi pata nahi", "4")]),
    "antar_window_alert_v1": (
        "Namaste {{1}}, Antar mein aapne jo alert on kiya tha: {{2}}, jo {{3}} ko khulta hai. "
        "Iska poora faayda kaise uthayein, jaanna ho to yahin reply kijiye.",
        [("Kaise use karun?", "alert_how"), ("Alerts band karo", "alert_stop")]),
    "antar_chapter_alert_v1": (
        "Namaste {{1}}, Antar mein aapne jo alert on kiya tha: aapki reading ka naya chapter "
        "{{2}} ko shuru hota hai, aur uska focus {{3}} par hai. Ise achhe se kaise use karein, "
        "yahin reply karke poochhiye.",
        [("Kaise use karun?", "alert_how"), ("Alerts band karo", "alert_stop")]),
    "antar_answer_ready_v1": (
        "Namaste {{1}}, “{{2}}” ka Antar jawab taiyaar hai. Dekhne ke liye neeche tap kijiye.",
        [("Mera jawab dikhao", "show_answer")]),
}

_NEW = {
    # the consent wording changed (messaging.WA_CONSENT_VERSION) and the person is outside the 24h
    # window: ask for acceptance so their readings can continue. Buttons = the handler's pol:yes/no.
    "antar_policy_update_v1": {
        "category": "UTILITY",
        "variables": {"1": "Harleen"},
        "body": {
            "en": "Hi {{1}}, we updated how Antar handles your data on WhatsApp. To keep your "
                  "readings coming here, please review and accept the updated data policy.",
            "es": "Hola {{1}}, actualizamos cómo Antar trata tus datos en WhatsApp. Para seguir "
                  "recibiendo tus lecturas aquí, revisa y acepta la política de datos actualizada.",
            "pt_BR": "Oi {{1}}, atualizamos como o Antar trata seus dados no WhatsApp. Para continuar "
                     "recebendo suas leituras aqui, revise e aceite a política de dados atualizada.",
            "hinglish": "Namaste {{1}}, humne WhatsApp par aapke data ko Antar kaise sambhalta hai, "
                        "yeh update kiya hai. Readings yahin milti rahein, iske liye updated data "
                        "policy dekhkar accept kijiye.",
        },
        "buttons": {
            "en": [("Accept", "pol:yes"), ("Decline", "pol:no")],
            "es": [("Acepto", "pol:yes"), ("No acepto", "pol:no")],
            "pt_BR": [("Aceito", "pol:yes"), ("Não aceito", "pol:no")],
            "hinglish": [("Accept karta hoon", "pol:yes"), ("Accept nahi", "pol:no")],
        },
    },
    # a decision the person saved (feat #207): the window Antar was asked to watch opens.
    "antar_decision_window_v1": {
        "category": "UTILITY",
        "variables": {"1": "Harleen", "2": "changing jobs", "3": "Oct 14"},
        "body": {
            "en": "Hi {{1}}, you asked Antar to watch the timing for “{{2}}”. The window you saved "
                  "opens on {{3}}. Reply here if you want to talk it through.",
            "es": "Hola {{1}}, le pediste a Antar que vigilara el momento para “{{2}}”. La ventana "
                  "que guardaste se abre el {{3}}. Responde aquí si quieres comentarlo.",
            "pt_BR": "Oi {{1}}, você pediu ao Antar para acompanhar o momento de “{{2}}”. A janela "
                     "que você salvou abre em {{3}}. Responda aqui se quiser conversar sobre isso.",
            "hinglish": "Namaste {{1}}, aapne Antar se “{{2}}” ke timing par nazar rakhne ko kaha tha. "
                        "Jo window aapne save ki thi woh {{3}} ko khulti hai. Baat karni ho to yahin "
                        "reply kijiye.",
        },
        "buttons": {
            "en": [("What should I do?", "alert_how"), ("Stop reminders", "alert_stop")],
            "es": [("¿Qué hago?", "alert_how"), ("Parar avisos", "alert_stop")],
            "pt_BR": [("O que eu faço?", "alert_how"), ("Parar avisos", "alert_stop")],
            "hinglish": [("Main kya karun?", "alert_how"), ("Reminders band", "alert_stop")],
        },
    },
}
TEMPLATES.update(_NEW)

# ── Offers & news (MARKETING category) ─────────────────────────────────────────
# [wa-offers-news 2026-10-05] What the app's "Offers & news" switch actually sends. Rules:
#   * sent ONLY to a linked number whose row opted in under the CURRENT marketing wording
#     (messaging.can_send_marketing — send() enforces it; this module cannot bypass it);
#   * MARKETING is a separate, paid Meta category: never dressed up as UTILITY, and the opt-out
#     ("Reply STOP OFFERS") is IN the body, plus a Stop-offers button (handled as `stop offers`);
#   * owner rule (2026-10-03): WhatsApp carries NO prices and NO payments. Offer text is therefore
#     checked by marketing_text_ok() — a price, discount or "buy/upgrade" wording is refused;
#   * no hype, no emoji, no urgency pressure; one idea per message; the 2nd button is "Ask Antar"
#     (the existing `own` choice: it invites a free-text question, no quota burned).
_MARKETING = {
    # product news — a real, shipped thing, one line. {{2}}=headline, {{3}}=one plain sentence.
    "antar_news_v1": {
        "category": "MARKETING",
        "variables": {"1": "Harleen", "2": "save a decision and Antar watches its window",
                      "3": "Tell Antar what you are deciding and it will message you when the timing opens."},
        "body": {
            "en": "Hi {{1}}, new in Antar: {{2}}. {{3}} Reply STOP OFFERS any time to stop news and offers.",
            "es": "Hola {{1}}, novedad en Antar: {{2}}. {{3}} Responde PARAR OFERTAS cuando quieras para dejar de recibir novedades y ofertas.",
            "pt_BR": "Oi {{1}}, novidade no Antar: {{2}}. {{3}} Responda PARAR OFERTAS quando quiser para deixar de receber novidades e ofertas.",
            "hinglish": "Namaste {{1}}, Antar mein naya: {{2}}. {{3}} News aur offers band karne ke liye kabhi bhi STOP OFFERS likh dijiye.",
        },
        "buttons": {
            "en": [("Ask Antar", "own"), ("Stop offers", "mkt_stop")],
            "es": [("Preguntar a Antar", "own"), ("Parar ofertas", "mkt_stop")],
            "pt_BR": [("Perguntar ao Antar", "own"), ("Parar ofertas", "mkt_stop")],
            "hinglish": [("Antar se poochho", "own"), ("Offers band", "mkt_stop")],
        },
    },
    # an offer the OWNER writes at send time (no prices — see marketing_text_ok).
    # {{2}}=the offer in one sentence, {{3}}=until when.
    "antar_offer_v1": {
        "category": "MARKETING",
        "variables": {"1": "Harleen", "2": "an extra week of daily alerts", "3": "Oct 31"},
        "body": {
            "en": "Hi {{1}}, a note for Antar members: {{2}}. Open until {{3}}. Reply STOP OFFERS any time to stop these messages.",
            "es": "Hola {{1}}, un aviso para miembros de Antar: {{2}}. Disponible hasta el {{3}}. Responde PARAR OFERTAS cuando quieras para dejar de recibir estos mensajes.",
            "pt_BR": "Oi {{1}}, um aviso para membros do Antar: {{2}}. Disponível até {{3}}. Responda PARAR OFERTAS quando quiser para deixar de receber estas mensagens.",
            "hinglish": "Namaste {{1}}, Antar members ke liye ek suchna: {{2}}. {{3}} tak khula hai. Yeh messages band karne ke liye kabhi bhi STOP OFFERS likh dijiye.",
        },
        "buttons": {
            "en": [("Ask Antar", "own"), ("Stop offers", "mkt_stop")],
            "es": [("Preguntar a Antar", "own"), ("Parar ofertas", "mkt_stop")],
            "pt_BR": [("Perguntar ao Antar", "own"), ("Parar ofertas", "mkt_stop")],
            "hinglish": [("Antar se poochho", "own"), ("Offers band", "mkt_stop")],
        },
    },
}
TEMPLATES.update(_MARKETING)

# The news catalogue: ONLY things that are live in the product today (verified in the 5 Oct
# production bundle / API). Add an item here only when it ships — never announce a plan.
NEWS_ITEMS = {
    "decisions": {
        "en": ("save a decision and Antar watches its window",
               "Tell Antar what you are deciding and it will message you when the timing opens."),
        "es": ("guarda una decisión y Antar vigila su ventana",
               "Cuéntale a Antar qué estás decidiendo y te avisará cuando se abra el momento."),
        "pt_BR": ("salve uma decisão e o Antar acompanha a janela dela",
                  "Conte ao Antar o que você está decidindo e ele avisa quando o momento abrir."),
        "hinglish": ("ek decision save kijiye aur Antar uski window par nazar rakhta hai",
                     "Antar ko batayiye aap kya decide kar rahe hain, timing khulte hi woh aapko batayega."),
    },
    "daily_wisdom": {
        "en": ("a daily verse chosen for your season",
               "Open Practice each day for a short passage matched to where you are right now."),
        "es": ("un verso diario elegido para tu momento",
               "Abre Práctica cada día para leer un pasaje corto acorde a tu momento actual."),
        "pt_BR": ("um verso diário escolhido para a sua fase",
                  "Abra Prática todos os dias para ler uma passagem curta ligada ao seu momento."),
        "hinglish": ("aapke daur ke hisaab se roz ek shlok",
                     "Roz Practice kholiye aur apne abhi ke samay se jodi ek chhoti panktiyan padhiye."),
    },
    "people_timing": {
        "en": ("see how your days line up with someone close to you",
               "Add a partner, co-founder or parent and compare the timing between you."),
        "es": ("mira cómo se alinean tus días con alguien cercano",
               "Añade a tu pareja, socio o a un familiar y compara el momento entre ustedes."),
        "pt_BR": ("veja como seus dias se alinham com alguém próximo",
                  "Adicione seu parceiro, sócio ou um familiar e compare o momento entre vocês."),
        "hinglish": ("dekhiye aapke din kisi apne ke saath kaise milte hain",
                     "Partner, co-founder ya parent ko jodiye aur dono ki timing compare kijiye."),
    },
    "places": {
        "en": ("where on Earth your timing works best",
               "Pick what you are focused on in Places and see the cities that suit it."),
        "es": ("dónde en el mundo tu momento funciona mejor",
               "Elige en Lugares lo que te importa y mira las ciudades que le van bien."),
        "pt_BR": ("onde no mundo o seu momento funciona melhor",
                  "Escolha em Lugares o que importa para você e veja as cidades que combinam."),
        "hinglish": ("duniya mein kahan aapki timing sabse achhi chalti hai",
                     "Places mein apna focus chuniye aur dekhiye kaun se shehar aapke liye theek hain."),
    },
}

# Owner rule: no prices / payments on WhatsApp. Refuse anything that reads like one.
import re as _re
_PRICEY = _re.compile(
    r"(?i)[$€£₹]|\b\d+\s*%|\b(usd|inr|eur|gbp|rs\.?|rupees?|dollars?|euros?|pesos?|reais)\b|"
    r"\b(discount|coupon|promo ?code|voucher|sale|deal|cheap|price|pricing|pay|paid|buy|purchase|"
    r"upgrade|subscribe|subscription|plan|premium|checkout|offer ends|limited time|hurry|last chance|"
    r"descuento|cup[oó]n|precio|comprar|pagar|suscri\w+|desconto|pre[cç]o|comprar|assinar|assinatura|"
    r"chhoot|kharid\w*|paise|daam)\b")


def marketing_text_ok(text: str) -> bool:
    """False for price / discount / purchase / pressure wording — WhatsApp never carries those."""
    return not _PRICEY.search(text or "")


def build_marketing(kind: str, name: str, lang: str, *, item: Optional[str] = None,
                    offer: Optional[str] = None, until: Optional[str] = None) -> Optional[tuple]:
    """(template_name, variables) for an Offers & news message, or None when it must not be sent
    (unknown kind/item, empty fields, or offer text that reads like a price). Sending still goes
    through send(), which re-checks the recipient's opt-in."""
    wl = wa_lang(lang)
    first = " ".join(str(name or "").split()).split(" ")[0] or ("there" if wl == "en" else "")
    first = first or {"es": "hola", "pt_BR": "olá", "hinglish": "dost"}.get(wl, "there")
    if kind == "news":
        entry = NEWS_ITEMS.get(item or "")
        if not entry:
            return None
        head, line = entry[wl]
        if not (marketing_text_ok(head) and marketing_text_ok(line)):
            return None
        return "antar_news_v1", {"1": first, "2": head, "3": line}
    if kind == "offer":
        text = " ".join(str(offer or "").split()).rstrip(".")
        when = " ".join(str(until or "").split())
        if not text or not when or not marketing_text_ok(text):
            return None
        return "antar_offer_v1", {"1": first, "2": text, "3": when}
    return None


def send_marketing(link: dict, to_number: str, kind: str, lang: str, **kw) -> bool:
    """Build + send one Offers & news message. False (and nothing sent) if the recipient has not opted
    in under the current wording, the template isn't approved yet, or the text fails the no-prices rule."""
    from antar_engine.messaging import can_send_marketing
    if not can_send_marketing(link):
        return False
    built = build_marketing(kind, (link or {}).get("display_name") or kw.pop("name", ""), lang, **kw)
    if not built:
        return False
    name, variables = built
    return send(to_number, name, lang, variables, link=link)
for _n, (_b, _btn) in _HINGLISH.items():
    TEMPLATES[_n]["body"]["hinglish"] = _b
    TEMPLATES[_n]["buttons"]["hinglish"] = _btn


def wa_lang(lang: str) -> str:
    """Antar language → template language ('en' | 'es' | 'pt_BR' | 'hinglish'; anything else → English)."""
    l = (lang or "en").lower().replace("_", "-")
    # [hi 2026-10-07] ONLY Roman-script Hinglish takes the Hinglish template. Devanagari "hi" used to match
    # startswith("hi") and silently get the Roman-script one. No Hindi template is submitted to Meta yet
    # (it would need locale "hi"), so a Devanagari reader gets the ENGLISH template — explicit, and listed
    # in the PR as the follow-up — never Hinglish.
    return ("es" if l.startswith("es") else "pt_BR" if l.startswith("pt")
            else "hinglish" if l.startswith("hinglish") or l == "hi-latn" else "en")


def env_key(name: str, lang: str) -> str:
    return f"WA_TPL_{name.upper()}_{wa_lang(lang).upper()}"


def template_sid(name: str, lang: str) -> Optional[str]:
    """ContentSid of an APPROVED template, or None (not approved / not set). A Hinglish template that
    isn't approved falls back to the English one — the person still gets the message."""
    sid = (os.getenv(env_key(name, lang)) or "").strip()
    if not sid and wa_lang(lang) == "hinglish":
        sid = (os.getenv(env_key(name, "en")) or "").strip()
    return sid or None


def meta_locale(lang: str) -> str:
    """The language code a template is SUBMITTED under (Hinglish has no Meta locale of its own)."""
    wl = wa_lang(lang)
    return (os.getenv("WA_HINGLISH_LOCALE") or "en") if wl == "hinglish" else wl


def content_payload(name: str, lang: str) -> dict:
    """Twilio Content API create body (quick-reply + plain-text fallback)."""
    t = TEMPLATES[name]
    wl = wa_lang(lang)
    body = t["body"][wl]
    return {
        "friendly_name": f"{name}_{wl.lower()}",
        "language": meta_locale(lang),
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


def send(to_number: str, name: str, lang: str, variables: dict, link: Optional[dict] = None) -> bool:
    """Send an approved template (works outside the 24h window). False when the
    template isn't approved/configured or Twilio refuses — caller falls back.
    [wa-marketing] A MARKETING-category template is sent ONLY with the recipient's link row and only if
    that row explicitly opted in to offers (messaging.can_send_marketing)."""
    if str((TEMPLATES.get(name) or {}).get("category") or "").upper() == "MARKETING":
        from antar_engine.messaging import can_send_marketing
        if not can_send_marketing(link):
            print(f"[wa-templates] marketing template {name!r} blocked: no offers opt-in")
            return False
    from antar_engine.messaging import wa_number, _twilio_auth, _TWILIO_MSG_API
    content_sid = template_sid(name, lang)
    from antar_engine import wa_numbers as _wn
    acct, sender, auth = (os.getenv("TWILIO_ACCOUNT_SID"),
                          _wn.effective_sender() or os.getenv("TWILIO_WHATSAPP_FROM"), _twilio_auth())
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
        _r = urllib.request.urlopen(urllib.request.Request(
            _TWILIO_MSG_API.format(sid=acct), data=data, method="POST",
            headers={"Authorization": "Basic " + auth,
                     "Content-Type": "application/x-www-form-urlencoded"}), timeout=15)
        try:
            _osid = json.loads(_r.read()).get("sid", "")
        except Exception:
            _osid = ""
        from antar_engine import wa_log as _wl
        _wl.record("out", to, (TEMPLATES.get(name, {}).get("body", {}).get(wa_lang(lang)) or ""),
                   sender=sender, sid=_osid, kind="template", template=name, lang=lang,
                   meta={"variables": vars_})
        return True
    except urllib.error.HTTPError as e:
        print(f"[whatsapp][template] {name} failed …{to[-4:]}: {e.code} {e.read()[:200]!r}")
    except Exception as e:
        print(f"[whatsapp][template] {name} failed …{to[-4:]}: {e}")
    return False
