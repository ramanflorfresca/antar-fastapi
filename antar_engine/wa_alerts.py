"""
antar_engine/wa_alerts.py — which life alert (if any) Antar sends on WhatsApp,
and how it reads. Pure helpers; main.py's hourly job does the I/O.

[wa-alert-senders 2026-10-03] Owner: WhatsApp is the return channel. Alerts go
out only to people who turned alerts on, at ~9 AM their time, at most one a
week, and only the CALM, forward-looking kinds:

  wealth_window → antar_window_alert_v1  ("your strongest money window opens…")
  dasha_turn    → antar_chapter_alert_v1 ("a new chapter… centres on …")

Caution alerts (risk_window, strain_window, lean_stretch) are NEVER pushed to
WhatsApp unasked — "a testing stretch for your relationship" arriving out of
the blue reads as fear. They stay in the app, where the person chooses to look.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

SENDABLE = {"wealth_window": "antar_window_alert_v1",
            "dasha_turn": "antar_chapter_alert_v1"}
NEVER_PUSH = frozenset({"risk_window", "strain_window", "lean_stretch"})

LOCAL_HOUR = 9            # ~9 AM in the person's own time
MIN_GAP_DAYS = 7          # at most one alert a week
LEAD_DAYS = 7             # send up to a week before it opens…
GRACE_DAYS = 2            # …or within 2 days after (a missed morning)

# what a new chapter centres on — by the period that begins (plain words only)
CHAPTER_THEME = {
    "en": {"Sun": "recognition and stepping into leadership",
           "Moon": "home, family and your emotional footing",
           "Mars": "drive, courage and decisive action",
           "Mercury": "skills, communication and trade",
           "Jupiter": "growth, learning and good guidance",
           "Venus": "relationships, comfort and creative work",
           "Saturn": "building something lasting through steady work",
           "Rahu": "ambition and new, unconventional paths",
           "Ketu": "letting go and finding your inner direction"},
    "es": {"Sun": "el reconocimiento y asumir el liderazgo",
           "Moon": "el hogar, la familia y tu equilibrio emocional",
           "Mars": "el impulso, el coraje y la acción decidida",
           "Mercury": "las habilidades, la comunicación y el comercio",
           "Jupiter": "el crecimiento, el aprendizaje y una buena guía",
           "Venus": "las relaciones, el bienestar y el trabajo creativo",
           "Saturn": "construir algo duradero con trabajo constante",
           "Rahu": "la ambición y caminos nuevos y poco convencionales",
           "Ketu": "soltar y encontrar tu dirección interior"},
    "pt": {"Sun": "reconhecimento e assumir a liderança",
           "Moon": "casa, família e seu equilíbrio emocional",
           "Mars": "impulso, coragem e ação decidida",
           "Mercury": "habilidades, comunicação e comércio",
           "Jupiter": "crescimento, aprendizado e boa orientação",
           "Venus": "relacionamentos, bem-estar e trabalho criativo",
           "Saturn": "construir algo duradouro com trabalho constante",
           "Rahu": "ambição e caminhos novos e fora do comum",
           "Ketu": "desapegar e encontrar sua direção interior"},
}
_GENERIC_THEME = {"en": "what you want this next season to build",
                  "es": "lo que quieres que construya esta nueva etapa",
                  "pt": "o que você quer que esta nova fase construa"}

_WINDOW_WHAT = {"en": "your strongest money window", "es": "tu mejor ventana de dinero",
                "pt": "sua melhor janela de dinheiro"}

# the question a "How do I use it?" tap asks on their behalf
_HOW_Q = {
    "antar_window_alert_v1": {"en": "How do I make the most of my money window that opens on {d}?",
                              "es": "¿Cómo aprovecho mi ventana de dinero que se abre el {d}?",
                              "pt": "Como aproveito minha janela de dinheiro que abre em {d}?"},
    "antar_chapter_alert_v1": {"en": "How do I make the most of the new chapter that begins on {d}?",
                               "es": "¿Cómo aprovecho la nueva etapa que empieza el {d}?",
                               "pt": "Como aproveito a nova fase que começa em {d}?"},
}

_MONTHS = {"es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
           "pt": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]}


def lang2(lang: str) -> str:
    l = (lang or "en").lower()[:2]
    return l if l in ("es", "pt") else "en"


def fmt_day(d: date, lang: str) -> str:
    l = lang2(lang)
    if l in _MONTHS:
        return f"{d.day} {_MONTHS[l][d.month - 1]}"
    return f"{d.strftime('%b')} {d.day}"


def _start(a: dict) -> Optional[date]:
    try:
        return date.fromisoformat(str(a.get("window_start"))[:10])
    except Exception:
        return None


def pick(alerts: list, sent: list, today: date) -> Optional[dict]:
    """The one alert to send today, or None. `sent` = [{"id", "at"(iso date)}]."""
    sent_ids = {str(s.get("id")) for s in (sent or [])}
    for s in sent or []:
        try:
            if today - date.fromisoformat(str(s.get("at"))[:10]) < timedelta(days=MIN_GAP_DAYS):
                return None                      # one a week at most
        except Exception:
            continue
    best = None
    for a in alerts or []:
        t = a.get("alert_type")
        if t not in SENDABLE or t in NEVER_PUSH or str(a.get("id")) in sent_ids:
            continue
        if a.get("dismissed_at"):
            continue
        s = _start(a)
        if not s or not (today - timedelta(days=GRACE_DAYS) <= s <= today + timedelta(days=LEAD_DAYS)):
            continue
        if best is None or s < _start(best):
            best = a
    return best


def render(alert: dict, lang: str, first_name: str, lord: Optional[str] = None) -> dict:
    """{template, variables, text (free-form, inside 24h), how_q}."""
    from antar_engine import wa_templates as wt
    l = lang2(lang)
    tpl = SENDABLE[alert["alert_type"]]
    s = _start(alert)
    d = fmt_day(s, l) if s else ""
    name = (first_name or "").strip() or {"es": "de nuevo", "pt": "de novo"}.get(
        l, "dost" if wt.wa_lang(lang) == "hinglish" else "there")
    body = wt.TEMPLATES[tpl]["body"][wt.wa_lang(lang)]
    if tpl == "antar_window_alert_v1":
        variables = {"1": name, "2": _WINDOW_WHAT[l], "3": d}
    else:
        theme = CHAPTER_THEME[l].get((lord or "").strip().title()) or _GENERIC_THEME[l]
        variables = {"1": name, "2": d, "3": theme}
    text = body
    for k, v in variables.items():
        text = text.replace("{{" + k + "}}", v)
    return {"template": tpl, "variables": variables, "text": text,
            "how_q": _HOW_Q[tpl][l].format(d=d)}


def lord_for(alert: dict, maha_rows: list) -> Optional[str]:
    """The period that begins on the chapter alert's start date."""
    s = _start(alert)
    for m in maha_rows or []:
        if m.get("start") == s:
            return m.get("lord")
    return None
