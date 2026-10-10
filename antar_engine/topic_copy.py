"""
antar_engine/topic_copy.py
──────────────────────────
Plain-words copy for the topic picker (GET /chart/{id}/topics) and the topic
read (GET /chart/{id}/topic-read). Every user-facing string the topic engine
emits comes from here, so the no-jargon guard (tests/test_topic_engine.py)
has ONE place to prove clean.

Languages: en, es, pt, hinglish (Roman-script Hindi). Anything else —
including Devanagari `hi` (a separate task) and `fr` — is served in English and
the response says `language: "en"`, so a card is never half one language and
half another. English-only keyword logic is a known silent bug class: nothing
in the engine branches on words, only on these keyed tables.

Owner rules baked into the wording (do not loosen):
  • Money / Business speak about TIMING and approach only — never "you will be
    rich" and never a promise a venture works (closed negative studies).
  • Health speaks rhythm and routine only — never a diagnosis.
  • No system names ("dasha", "Jaimini", "transit", planets, houses…).
  • No prices, no consent logic.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Optional

TOPIC_KEYS = ("money", "career", "love", "health", "business", "peace", "family")
SCALES = ("today", "month", "season", "year")

# [decisions-topic 2026-10-08] ONE table from the words other engines store for a question's
# area (Ask's detect_concern output, prediction_claims.topic, plain domain words) onto the seven
# topic keys. Anything not listed — general, speculation, loss, legal, property, foreign,
# fame — is null: the icon is a courtesy, a wrong one is worse than none.
CONCERN_TO_TOPIC = {
    **{k: k for k in TOPIC_KEYS},
    "finance": "money", "wealth": "money", "income": "money", "salary": "money",
    "work": "career", "job": "career", "promotion": "career",
    "marriage": "love", "relationship": "love", "relationships": "love", "romance": "love",
    "divorce": "love", "reconciliation": "love",
    "body": "health", "energy": "health",
    "venture": "business", "startup": "business", "partnership": "business", "cofounder": "business",
    "spiritual": "peace", "spirituality": "peace", "mind": "peace", "stress": "peace", "sleep": "peace",
    "parents": "family", "children": "family", "home": "family",
    # understand.explicit_area() labels (the multilingual single-topic matcher Ask already runs)
    "separation": "love", "health_self": "health", "income_money": "money", "marriage": "love",
}


def topic_for_concern(raw) -> Optional[str]:
    """A topic key for a stored concern/domain/topic word, else None (never a guess)."""
    return CONCERN_TO_TOPIC.get(str(raw or "").strip().lower())


def topic_for_question(question) -> Optional[str]:
    """Topic key for free question text via the Ask pipeline's own routers, no new classifier:
    understand.explicit_area (EN/ES/PT/Hinglish, fires only on ONE unambiguous topic word),
    then detect_concern. None when neither is sure."""
    q = str(question or "").strip()
    if not q:
        return None
    try:
        from antar_engine.understand import explicit_area
        t = topic_for_concern(explicit_area(q))
        if t:
            return t
    except Exception:
        pass
    try:
        from antar_engine.astrological_rules import detect_concern
        return topic_for_concern(detect_concern(q))
    except Exception:
        return None
COPY_LANGUAGES = ("en", "es", "pt", "hinglish")


def serve_language(raw) -> str:
    """The language the copy will actually be written in."""
    try:
        from antar_engine.lang_registry import normalize_language
        lang = normalize_language(raw, log=False)
    except Exception:
        lang = "en"
    return lang if lang in COPY_LANGUAGES else "en"


# ── labels, areas ────────────────────────────────────────────────────────────
LABEL: Dict[str, Dict[str, str]] = {
    "en": {"money": "Money", "career": "Career", "love": "Love", "health": "Health",
           "business": "Business", "peace": "Peace", "family": "Family"},
    "es": {"money": "Dinero", "career": "Carrera", "love": "Amor", "health": "Salud",
           "business": "Negocio", "peace": "Paz", "family": "Familia"},
    "pt": {"money": "Dinheiro", "career": "Carreira", "love": "Amor", "health": "Saúde",
           "business": "Negócio", "peace": "Paz", "family": "Família"},
    "hinglish": {"money": "Paisa", "career": "Career", "love": "Pyaar", "health": "Sehat",
                 "business": "Business", "peace": "Sukoon", "family": "Parivaar"},
}

# lower-case noun phrase used mid-sentence ("the chapter you're in is tied to …")
AREA: Dict[str, Dict[str, str]] = {
    "en": {"money": "money and income", "career": "your work", "love": "close relationships",
           "health": "your body's rhythm", "business": "ventures and partnerships",
           "peace": "your inner calm", "family": "home and family"},
    "es": {"money": "el dinero y los ingresos", "career": "tu trabajo",
           "love": "las relaciones cercanas", "health": "el ritmo de tu cuerpo",
           "business": "los negocios y las alianzas", "peace": "tu calma interior",
           "family": "el hogar y la familia"},
    "pt": {"money": "o dinheiro e a renda", "career": "o seu trabalho",
           "love": "as relações próximas", "health": "o ritmo do seu corpo",
           "business": "os negócios e as parcerias", "peace": "a sua calma interior",
           "family": "a casa e a família"},
    "hinglish": {"money": "paise aur income", "career": "aapka kaam",
                 "love": "kareebi rishte", "health": "aapke sharir ki lay",
                 "business": "business aur partnerships", "peace": "aapka andar ka sukoon",
                 "family": "ghar aur parivaar"},
}

# ── status tags ──────────────────────────────────────────────────────────────
TAG: Dict[str, Dict[str, str]] = {
    # one of four plain states per tile; {d} is a day ("Oct 30"), {my} a month + year ("Nov 2027")
    "en": {"open_now": "Open now", "open_now_until": "Open now, until {d}",
           "opens": "Opens {d}", "opens_far": "Opens {my}",
           "care_now": "Care now", "care_now_until": "Care now, until {d}",
           "care_from": "Care from {d}", "care_from_far": "Care from {my}",
           "quiet": "Quiet"},
    "es": {"open_now": "Abierto ahora", "open_now_until": "Abierto ahora, hasta el {d}",
           "opens": "Abre el {d}", "opens_far": "Abre en {my}",
           "care_now": "Con cuidado ahora", "care_now_until": "Con cuidado ahora, hasta el {d}",
           "care_from": "Con cuidado desde {d}", "care_from_far": "Con cuidado desde {my}",
           "quiet": "Tranquilo"},
    "pt": {"open_now": "Aberto agora", "open_now_until": "Aberto agora, até {d}",
           "opens": "Abre em {d}", "opens_far": "Abre em {my}",
           "care_now": "Com cuidado agora", "care_now_until": "Com cuidado agora, até {d}",
           "care_from": "Com cuidado a partir de {d}", "care_from_far": "Com cuidado a partir de {my}",
           "quiet": "Tranquilo"},
    "hinglish": {"open_now": "Abhi khula hai", "open_now_until": "Abhi khula hai, {d} tak",
                 "opens": "{d} ko khulega", "opens_far": "{my} ko khulega",
                 "care_now": "Abhi savdhaani", "care_now_until": "Abhi savdhaani, {d} tak",
                 "care_from": "{d} se savdhaani", "care_from_far": "{my} se savdhaani",
                 "quiet": "Shaant"},
}

MONTHS: Dict[str, tuple] = {
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "es": ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"),
    "pt": ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"),
    "hinglish": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
}


def month_name(d: date, lang: str) -> str:
    return MONTHS.get(lang, MONTHS["en"])[d.month - 1]


def month_year_short(d: date, lang: str) -> str:
    """'Jun 2028' — a month that is far enough out to need its year."""
    return f"{month_name(d, lang)} {d.year}"


def add_months(d: date, n: int) -> date:
    """d + n calendar months, the day clamped to the target month's length."""
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    m += 1
    last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(d.day, last))


def day_label(d: date, lang: str) -> str:
    m = month_name(d, lang)
    return f"{m} {d.day}" if lang in ("en", "hinglish") else f"{d.day} {m}"


def day_label_y(d: date, lang: str) -> str:
    return f"{day_label(d, lang)}, {d.year}" if lang in ("en", "hinglish") else f"{day_label(d, lang)} {d.year}"


def range_label(start: date, end: date, lang: str) -> str:
    if start == end:
        return day_label(start, lang)
    return f"{day_label(start, lang)} – {day_label(end, lang)}"


# ── segmented-control chips + rung order ─────────────────────────────────────
# `period.chip` is the short chip text; `period.rung` names the rung. The year chip is
# the numeric birthday-to-birthday range; never "this year" / "365" / "season".
RUNG_BY_SCALE = {"today": "now", "month": "30d", "year": "year", "season": "stretch", "chapter": "chapter"}
CHIP: Dict[str, Dict[str, str]] = {
    "en": {"today": "Right now", "month": "Next 30 days", "season": "Life chapter", "chapter": "Whole chapter"},
    "es": {"today": "Ahora", "month": "Próximos 30 días", "season": "Capítulo de vida", "chapter": "Capítulo completo"},
    "pt": {"today": "Agora", "month": "Próximos 30 dias", "season": "Capítulo de vida", "chapter": "Capítulo completo"},
    "hinglish": {"today": "Abhi", "month": "Agle 30 din", "season": "Life chapter", "chapter": "Poora chapter"},
}


def year_chip(start: date, bday: date, lang: str) -> str:
    """The birthday range as numbers, in the reader's date order: en 11/26/25 – 11/26/26,
    es / pt / hinglish 26/11/25 – 26/11/26. `start` = last birthday, `bday` = next birthday."""
    def num(d: date) -> str:
        yy = f"{d.year % 100:02d}"
        return f"{d.month}/{d.day}/{yy}" if lang == "en" else f"{d.day}/{d.month}/{yy}"
    return f"{num(start)} – {num(bday)}"


def rung_order(year_end: Optional[date], stretch_end: Optional[date]) -> list:
    """now, 30d, then year/stretch by end date ascending (year first on a tie), chapter."""
    mid = sorted([r for r in (("year", year_end), ("stretch", stretch_end)) if r[1]],
                 key=lambda r: (r[1], r[0] != "year"))
    return ["now", "30d"] + [r[0] for r in mid] + ["chapter"]

# ── time-scale lead-ins ──────────────────────────────────────────────────────
SPAN_LEAD: Dict[str, Dict[str, str]] = {
    "en": {"today": "Today", "month": "Over the next 30 days", "season": "Over this stretch", "year": "Over your year, to your birthday"},
    "es": {"today": "Hoy", "month": "Durante los próximos 30 días", "season": "En este tramo", "year": "Durante tu año, hasta tu cumpleaños"},
    "pt": {"today": "Hoje", "month": "Nos próximos 30 dias", "season": "Neste trecho", "year": "Ao longo do seu ano, até o seu aniversário"},
    "hinglish": {"today": "Aaj", "month": "Agle 30 din mein", "season": "Is stretch mein", "year": "Aapke saal mein, janamdin tak"},
}

PERIOD_LABEL: Dict[str, Dict[str, str]] = {
    "en": {"today": "Today", "month": "Next 30 days", "season": "The next few months",
           "year": "Your year · birthday to birthday"},
    "es": {"today": "Hoy", "month": "Próximos 30 días", "season": "Los próximos meses",
           "year": "Tu año · de cumpleaños a cumpleaños"},
    "pt": {"today": "Hoje", "month": "Próximos 30 dias", "season": "Os próximos meses",
           "year": "O seu ano · de aniversário a aniversário"},
    "hinglish": {"today": "Aaj", "month": "Agle 30 din", "season": "Agle kuch mahine",
                 "year": "Aapka saal · janamdin se janamdin tak"},
}

# ── the "season" scale, framed by its real length ────────────────────────────
# The scale key stays `season`; it is the user's current long stretch, which can
# run from a few months to ~3 years. Users see the length, never the word.
# Rule: months = round(days from today to the end / 30.44), at least 1.
#   <=3 few | 4-10 "N months" | 11-14 1 year | 15-20 1½ years | 21-26 2 years
#   | 27-32 2½ years | 33+ 3 years
SPAN_KINDS = ("few", "months", "1y", "1.5y", "2y", "2.5y", "3y")
SPAN_TEXT: Dict[str, Dict[str, str]] = {   # label form; "{n}" for the month count
    "en": {"few": "The next few months", "months": "The next {n} months", "1y": "The next year",
           "1.5y": "The next 1½ years", "2y": "The next 2 years", "2.5y": "The next 2½ years", "3y": "The next 3 years"},
    "es": {"few": "Los próximos meses", "months": "Los próximos {n} meses", "1y": "El próximo año",
           "1.5y": "Los próximos 1½ años", "2y": "Los próximos 2 años", "2.5y": "Los próximos 2½ años", "3y": "Los próximos 3 años"},
    "pt": {"few": "Os próximos meses", "months": "Os próximos {n} meses", "1y": "O próximo ano",
           "1.5y": "Os próximos 1½ anos", "2y": "Os próximos 2 anos", "2.5y": "Os próximos 2½ anos", "3y": "Os próximos 3 anos"},
    "hinglish": {"few": "Agle kuch mahine", "months": "Agle {n} mahine", "1y": "Agla saal",
                 "1.5y": "Agle 1½ saal", "2y": "Agle 2 saal", "2.5y": "Agle 2½ saal", "3y": "Agle 3 saal"},
}
SPAN_LEAD_SEASON: Dict[str, Dict[str, str]] = {   # "<lead>, <core>."
    "en": {"few": "Over the next few months", "months": "Over the next {n} months", "1y": "Over the next year",
           "1.5y": "Over the next 1½ years", "2y": "Over the next 2 years", "2.5y": "Over the next 2½ years", "3y": "Over the next 3 years"},
    "es": {"few": "Durante los próximos meses", "months": "Durante los próximos {n} meses", "1y": "Durante el próximo año",
           "1.5y": "Durante los próximos 1½ años", "2y": "Durante los próximos 2 años", "2.5y": "Durante los próximos 2½ años", "3y": "Durante los próximos 3 años"},
    "pt": {"few": "Nos próximos meses", "months": "Nos próximos {n} meses", "1y": "No próximo ano",
           "1.5y": "Nos próximos 1½ anos", "2y": "Nos próximos 2 anos", "2.5y": "Nos próximos 2½ anos", "3y": "Nos próximos 3 anos"},
    "hinglish": {"few": "Agle kuch mahine mein", "months": "Agle {n} mahine mein", "1y": "Agle saal mein",
                 "1.5y": "Agle 1½ saal mein", "2y": "Agle 2 saal mein", "2.5y": "Agle 2½ saal mein", "3y": "Agle 3 saal mein"},
}
CHAPTER_LABEL: Dict[str, str] = {   # the whole current major period; the stretch label stays the secondary line
    "en": "Your current life chapter · to {end}", "es": "Tu capítulo de vida actual · hasta {end}",
    "pt": "O seu capítulo de vida atual · até {end}", "hinglish": "Aapka maujooda life chapter · {end} tak"}
CHAPTER_LABEL_WHOLE: Dict[str, str] = {   # the chapter rung's own label, distinct from the stretch's "current life chapter"
    "en": "Your whole life chapter · to {end}", "es": "Todo tu capítulo de vida · hasta {end}",
    "pt": "Todo o seu capítulo de vida · até {end}", "hinglish": "Aapka poora life chapter · {end} tak"}
CHAPTER_LEAD: Dict[str, str] = {
    "en": "Across your current life chapter", "es": "A lo largo de tu capítulo de vida actual",
    "pt": "Ao longo do seu capítulo de vida atual", "hinglish": "Aapke maujooda life chapter mein"}
KEEP_SMALL: Dict[str, str] = {   # appended to Your move when the day's read says to go easy on risk
    "en": "But keep any bet small.", "es": "Eso sí, mantén cualquier apuesta pequeña.",
    "pt": "Mas mantenha qualquer aposta pequena.", "hinglish": "Bas koi bhi daav chhota rakhein."}
SPAN_END: Dict[str, str] = {"en": "{span} · to {end}", "es": "{span} · hasta {end}",
                            "pt": "{span} · até {end}", "hinglish": "{span} · {end} tak"}
WHOLE_SEASON: Dict[str, Dict[str, str]] = {   # "All of <this>"
    "en": {"few": "the next few months", "months": "the next {n} months", "1y": "the next year",
           "1.5y": "the next 1½ years", "2y": "the next 2 years", "2.5y": "the next 2½ years", "3y": "the next 3 years"},
    "es": {"few": "los próximos meses", "months": "los próximos {n} meses", "1y": "el próximo año",
           "1.5y": "los próximos 1½ años", "2y": "los próximos 2 años", "2.5y": "los próximos 2½ años", "3y": "los próximos 3 años"},
    "pt": {"few": "os próximos meses", "months": "os próximos {n} meses", "1y": "o próximo ano",
           "1.5y": "os próximos 1½ anos", "2y": "os próximos 2 anos", "2.5y": "os próximos 2½ anos", "3y": "os próximos 3 anos"},
    "hinglish": {"few": "agle kuch mahine", "months": "agle {n} mahine", "1y": "agla saal",
                 "1.5y": "agle 1½ saal", "2y": "agle 2 saal", "2.5y": "agle 2½ saal", "3y": "agle 3 saal"},
}


def span_info(today: date, end: date) -> Dict[str, object]:
    """{'months': N, 'bucket': one of SPAN_KINDS} for a period running today -> end."""
    m = max(1, round((end - today).days / 30.44))
    bucket = ("few" if m <= 3 else "months" if m <= 10 else "1y" if m <= 14 else "1.5y" if m <= 20
              else "2y" if m <= 26 else "2.5y" if m <= 32 else "3y")
    return {"months": m, "bucket": bucket}


def season_text(table: Dict[str, Dict[str, str]], lang: str, span: Dict[str, object]) -> str:
    t = table.get(lang) or table["en"]
    return t[span["bucket"]].format(n=span["months"])


# the Windows feed's "big picture" chapter line ("{end}" = "Apr 2040")
WINDOWS_CHAPTER: Dict[str, str] = {
    "en": "Your current chapter · to {end}", "es": "Tu capítulo actual · hasta {end}",
    "pt": "O seu capítulo atual · até {end}", "hinglish": "Aapka maujooda chapter · {end} tak",
}


WINDOW_LABEL: Dict[str, Dict[str, str]] = {
    "en": {"best": "Best window", "watch": "Watch", "whole": "All of {span}"},
    "es": {"best": "Mejor ventana", "watch": "Ojo", "whole": "Todo: {span}"},
    "pt": {"best": "Melhor janela", "watch": "Atenção", "whole": "Todo: {span}"},
    "hinglish": {"best": "Best window", "watch": "Dhyaan", "whole": "Poora {span}"},
}
WHOLE_SPAN: Dict[str, Dict[str, str]] = {
    "en": {"today": "today", "month": "the next 30 days", "season": "this stretch", "year": "this year"},
    "es": {"today": "hoy", "month": "los próximos 30 días", "season": "este tramo", "year": "este año"},
    "pt": {"today": "hoje", "month": "os próximos 30 dias", "season": "este trecho", "year": "este ano"},
    "hinglish": {"today": "aaj", "month": "agle 30 din", "season": "yeh stretch", "year": "yeh saal"},
}

# ── claims: lower-case sentence cores, joined to the span lead ───────────────
# mode: open (a real supportive stretch) | care (a real demanding stretch) | steady
CORE: Dict[str, Dict[str, Dict[str, str]]] = {
    "en": {
        "money": {"open": "money matters have better backing than usual, so it is a good stretch to act on income, pricing and plans",
                  "care": "money asks for care, so slow down on big commitments and re-read the terms"},
        "career": {"open": "work moves get real support, so it is a good time to speak up, apply or make your case",
                   "care": "work asks for patience, so avoid forcing a decision and keep your record clean"},
        "love": {"open": "close relationships are more open than usual, so it is a good time to reach out and be direct",
                 "care": "relationships need gentleness, so avoid big conversations when you are tired or rushed"},
        "health": {"open": "your rhythm is easier to build on, so it is a good time to restart a routine of sleep, food and movement",
                   "care": "your body asks for a steadier rhythm, so protect sleep and rest and do not push through tiredness"},
        "business": {"open": "decisions and partnerships are better timed than usual, so commit to a step you have already prepared",
                     "care": "commitments are better held back, so test small before you put money or people behind anything"},
        "peace": {"open": "inner calm is easier to reach, so it is a good time to simplify and make room for stillness",
                  "care": "your mind runs more restless than usual, so keep evenings quiet and cut what you can"},
        "family": {"open": "home and family feel more connected, so it is a good time to be together and settle household matters",
                   "care": "family matters need care, so listen first and leave big household decisions for later"},
    },
    "es": {
        "money": {"open": "los asuntos de dinero tienen mejor respaldo que de costumbre, así que es buen momento para actuar sobre ingresos, precios y planes",
                  "care": "el dinero pide cuidado, así que baja el ritmo en compromisos grandes y relee las condiciones"},
        "career": {"open": "tus movimientos en el trabajo reciben apoyo real, así que es buen momento para hablar, postularte o defender tu caso",
                   "care": "el trabajo pide paciencia, así que evita forzar una decisión y cuida tu historial"},
        "love": {"open": "las relaciones cercanas están más abiertas que de costumbre, así que es buen momento para acercarte y ser directo",
                 "care": "las relaciones piden suavidad, así que evita las conversaciones grandes cuando estés cansado o apurado"},
        "health": {"open": "tu ritmo es más fácil de construir, así que es buen momento para retomar una rutina de sueño, comida y movimiento",
                   "care": "tu cuerpo pide un ritmo más estable, así que protege el sueño y el descanso y no te exijas pasando el cansancio"},
        "business": {"open": "las decisiones y las alianzas están mejor ubicadas en el tiempo que de costumbre, así que compromete un paso que ya tengas preparado",
                     "care": "conviene aplazar los compromisos, así que prueba en pequeño antes de poner dinero o gente detrás de algo"},
        "peace": {"open": "la calma interior es más fácil de alcanzar, así que es buen momento para simplificar y dejar espacio a la quietud",
                  "care": "tu mente anda más inquieta que de costumbre, así que mantén las noches tranquilas y recorta lo que puedas"},
        "family": {"open": "el hogar y la familia se sienten más unidos, así que es buen momento para estar juntos y resolver asuntos de la casa",
                   "care": "los asuntos familiares piden cuidado, así que escucha primero y deja las decisiones grandes del hogar para después"},
    },
    "pt": {
        "money": {"open": "os assuntos de dinheiro têm mais respaldo que o habitual, então é um bom momento para agir sobre renda, preços e planos",
                  "care": "o dinheiro pede cuidado, então vá mais devagar em compromissos grandes e releia as condições"},
        "career": {"open": "os seus movimentos no trabalho recebem apoio real, então é um bom momento para falar, se candidatar ou defender o seu caso",
                   "care": "o trabalho pede paciência, então evite forçar uma decisão e cuide do seu histórico"},
        "love": {"open": "as relações próximas estão mais abertas que o habitual, então é um bom momento para se aproximar e ser direto",
                 "care": "as relações pedem delicadeza, então evite conversas grandes quando estiver cansado ou com pressa"},
        "health": {"open": "o seu ritmo está mais fácil de construir, então é um bom momento para retomar uma rotina de sono, comida e movimento",
                   "care": "o seu corpo pede um ritmo mais estável, então proteja o sono e o descanso e não force o cansaço"},
        "business": {"open": "as decisões e as parcerias estão mais bem situadas no tempo que o habitual, então assuma um passo que você já preparou",
                     "care": "é melhor adiar compromissos, então teste em pequeno antes de pôr dinheiro ou pessoas por trás de algo"},
        "peace": {"open": "a calma interior está mais fácil de alcançar, então é um bom momento para simplificar e abrir espaço para a quietude",
                  "care": "a sua mente está mais inquieta que o habitual, então mantenha as noites calmas e corte o que puder"},
        "family": {"open": "a casa e a família parecem mais unidas, então é um bom momento para estarem juntos e resolver assuntos da casa",
                   "care": "os assuntos de família pedem cuidado, então ouça primeiro e deixe as decisões grandes da casa para depois"},
    },
    "hinglish": {
        "money": {"open": "paise ke maamle ko is baar behtar support hai, isliye income, pricing aur plans par kaam karne ka achha waqt hai",
                  "care": "paise mein dhyaan chahiye, isliye bade commitments mein ruk kar chalein aur terms dobara padhein"},
        "career": {"open": "kaam mein aapki chaal ko sach mein support mil raha hai, isliye bolne, apply karne ya apni baat rakhne ka achha waqt hai",
                   "care": "kaam mein sabr chahiye, isliye faisla zabardasti na karein aur apna record saaf rakhein"},
        "love": {"open": "kareebi rishte aam se zyada khule hain, isliye pehal karne aur seedhi baat karne ka achha waqt hai",
                 "care": "rishton mein narmi chahiye, isliye thake ya jaldi mein bade baat-cheet se bachein"},
        "health": {"open": "aapki lay banana aasaan hai, isliye neend, khaane aur halchal ki routine dobara shuru karne ka achha waqt hai",
                   "care": "sharir ek sthir lay maangta hai, isliye neend aur aaram bachayein aur thakaan ke bawajood khud ko na kheenchein"},
        "business": {"open": "faisle aur partnerships ka timing aam se behtar hai, isliye jo kadam aap pehle se taiyaar kar chuke hain wo uthayein",
                     "care": "commitments ko rokna behtar hai, isliye paisa ya log lagane se pehle chhote star par test karein"},
        "peace": {"open": "andar ka sukoon paana aasaan hai, isliye cheezein saral karne aur shaanti ko jagah dene ka achha waqt hai",
                  "care": "mann aam se zyada bechain hai, isliye shaamein shaant rakhein aur jo kaat sakein kaatein"},
        "family": {"open": "ghar aur parivaar zyada jude mehsoos honge, isliye saath rehne aur ghar ke maamle suljhane ka achha waqt hai",
                   "care": "parivaar ke maamlon mein dhyaan chahiye, isliye pehle sunein aur ghar ke bade faisle baad ke liye chhodein"},
    },
}

# "nothing sharp" — one template per language, {label} = lower-case topic phrase
STEADY_CORE: Dict[str, str] = {
    "en": "nothing sharp is pulling on {area}, so keep your usual pace",
    "es": "nada fuerte tira sobre {area}, así que mantén tu ritmo habitual",
    "pt": "nada forte puxa sobre {area}, então mantenha o seu ritmo habitual",
    "hinglish": "{area} par kuch tez nahin kheench raha, isliye apni aam raftaar rakhein",
}
YEAR_CAUTION_CORE: Dict[str, str] = {   # a steady year read that still has one demanding stretch for the topic
    "en": "it is steady overall for {area}, with {when} the one stretch to watch",
    "es": "en general todo está estable en {area}, con {when} como el tramo a vigilar",
    "pt": "no geral tudo está estável em {area}, com {when} como o trecho a observar",
    "hinglish": "{area} mein aam taur par sthirta hai, bas {when} par nazar rakhein"}
MONTH_CAUTION_CORE: Dict[str, str] = {   # a steady 30-day read that still has one demanding week for the topic
    "en": "it is steady overall for {area}, with one stretch to watch",
    "es": "en general todo está estable en {area}, con un tramo a vigilar",
    "pt": "no geral tudo está estável em {area}, com um trecho a observar",
    "hinglish": "{area} mein aam taur par sthirta hai, bas ek daur par nazar rakhein"}
MONTH_OPEN_TODAY: Dict[str, str] = {   # a 30-day claim that does not lead with today's one-day open window
    "en": "Today itself is open for {area}.", "es": "El día de hoy está abierto para {area}.",
    "pt": "O dia de hoje está aberto para {area}.", "hinglish": "Aaj ka din {area} ke liye khula hai."}
MONTH_WATCH_TAIL: Dict[str, str] = {   # after MONTH_CAUTION_CORE when the month's focus window is known
    "en": "That stretch is {when}.", "es": "Ese tramo va del {when}.",
    "pt": "Esse trecho vai de {when}.", "hinglish": "Woh daur {when} hai."}
TODAY_CAUTION_CORE: Dict[str, str] = {   # a steady Right-now read on a day that advises going easy on risk
    "en": "keep it quiet on {area}", "es": "ve con calma en {area}",
    "pt": "vá com calma em {area}", "hinglish": "{area} mein shaant rahein"}
YEAR_KEY_MONTH: Dict[str, str] = {   # appended to a year claim with no caution stretch when the year plan marks a month for this topic
    "en": "{when} is the month to note for {area}.", "es": "{when} es el mes a tener presente en {area}.",
    "pt": "{when} é o mês a ter em mente em {area}.", "hinglish": "{area} ke liye {when} dhyaan dene wala mahina hai."}
YEAR_CAUTION_TAIL: Dict[str, str] = {   # appended to a year read that has a window but also a demanding stretch
    "en": "Watch {when}.", "es": "Vigila {when}.", "pt": "Observe {when}.", "hinglish": "{when} par nazar rakhein."}
# ── one balanced headline: "<lead>, good for X, but careful with Y" (open window + a caution) ──
BAL_GOOD: Dict[str, Dict[str, str]] = {
    "en": {"money": "good for income and pricing", "career": "open for making your ask",
           "love": "good for honest, warm conversations", "health": "good for steady movement and rest",
           "business": "good for talks and follow-ups", "peace": "good for quiet focus and reflection",
           "family": "good for time with the people at home"},
    "es": {"money": "bueno para ingresos y precios", "career": "abierto para hacer tu petición",
           "love": "bueno para conversaciones cálidas y sinceras", "health": "bueno para moverte con constancia y descansar",
           "business": "bueno para conversaciones y seguimientos", "peace": "bueno para el enfoque tranquilo y la reflexión",
           "family": "bueno para estar con la gente de casa"},
    "pt": {"money": "bom para renda e preços", "career": "aberto para fazer o seu pedido",
           "love": "bom para conversas calorosas e sinceras", "health": "bom para movimento constante e descanso",
           "business": "bom para conversas e acompanhamentos", "peace": "bom para foco tranquilo e reflexão",
           "family": "bom para o tempo com as pessoas de casa"},
    "hinglish": {"money": "income aur pricing ke liye achha", "career": "apni baat rakhne ke liye khula",
                 "love": "saaf, garm baat-cheet ke liye achha", "health": "sthir movement aur aaram ke liye achha",
                 "business": "baat-cheet aur follow-up ke liye achha", "peace": "shaant focus aur sochne ke liye achha",
                 "family": "ghar ke logon ke saath samay ke liye achha"},
}
# the careful half, by what the caution is about: risk (spending / speculation), timing (talk / commitments),
# conflict (friction), neutral (cannot tell). Each reads after "but" and after the Your-move hedge prefix.
BAL_CARE: Dict[str, Dict[str, Dict[str, str]]] = {
    "en": {
        "money": {"risk": "careful with speculative moves", "timing": "careful with signing or committing fast",
                  "conflict": "careful with money arguments", "neutral": "gentle with big commitments"},
        "career": {"risk": "careful with risky bets", "timing": "careful with rushed decisions",
                   "conflict": "careful about burning bridges", "neutral": "gentle with big commitments"},
        "love": {"risk": "careful with big leaps", "timing": "careful with rushed promises",
                 "conflict": "careful with sharp words", "neutral": "gentle with big commitments"},
        "health": {"risk": "careful with pushing too hard", "timing": "careful with skipping rest",
                   "conflict": "careful with stress and strain", "neutral": "gentle with big commitments"},
        "business": {"risk": "careful with risky bets", "timing": "careful with signing too fast",
                     "conflict": "careful with tense negotiations", "neutral": "gentle with big commitments"},
        "peace": {"risk": "careful with overreaching", "timing": "careful with overloading your day",
                  "conflict": "careful with heated moments", "neutral": "gentle with big commitments"},
        "family": {"risk": "careful with big family spending", "timing": "careful with rushed decisions at home",
                   "conflict": "careful with old arguments", "neutral": "gentle with big commitments"},
    },
    "es": {
        "money": {"risk": "con cuidado con las jugadas especulativas", "timing": "con cuidado al firmar o comprometerte rápido",
                  "conflict": "con cuidado con las discusiones de dinero", "neutral": "con calma con los grandes compromisos"},
        "career": {"risk": "con cuidado con las apuestas arriesgadas", "timing": "con cuidado con las decisiones apuradas",
                   "conflict": "con cuidado de no quemar puentes", "neutral": "con calma con los grandes compromisos"},
        "love": {"risk": "con cuidado con los grandes saltos", "timing": "con cuidado con las promesas apuradas",
                 "conflict": "con cuidado con las palabras duras", "neutral": "con calma con los grandes compromisos"},
        "health": {"risk": "con cuidado de no exigirte demasiado", "timing": "con cuidado de no saltarte el descanso",
                   "conflict": "con cuidado con el estrés y la tensión", "neutral": "con calma con los grandes compromisos"},
        "business": {"risk": "con cuidado con las apuestas arriesgadas", "timing": "con cuidado al firmar demasiado rápido",
                     "conflict": "con cuidado con las negociaciones tensas", "neutral": "con calma con los grandes compromisos"},
        "peace": {"risk": "con cuidado de no abarcar demasiado", "timing": "con cuidado de no sobrecargar el día",
                  "conflict": "con cuidado con los momentos acalorados", "neutral": "con calma con los grandes compromisos"},
        "family": {"risk": "con cuidado con los grandes gastos familiares", "timing": "con cuidado con las decisiones apuradas en casa",
                   "conflict": "con cuidado con las viejas discusiones", "neutral": "con calma con los grandes compromisos"},
    },
    "pt": {
        "money": {"risk": "com cuidado com jogadas especulativas", "timing": "com cuidado ao assinar ou se comprometer rápido",
                  "conflict": "com cuidado com discussões de dinheiro", "neutral": "com calma nos grandes compromissos"},
        "career": {"risk": "com cuidado com apostas arriscadas", "timing": "com cuidado com decisões apressadas",
                   "conflict": "com cuidado para não queimar pontes", "neutral": "com calma nos grandes compromissos"},
        "love": {"risk": "com cuidado com grandes saltos", "timing": "com cuidado com promessas apressadas",
                 "conflict": "com cuidado com palavras duras", "neutral": "com calma nos grandes compromissos"},
        "health": {"risk": "com cuidado para não se exigir demais", "timing": "com cuidado para não pular o descanso",
                   "conflict": "com cuidado com o estresse e a tensão", "neutral": "com calma nos grandes compromissos"},
        "business": {"risk": "com cuidado com apostas arriscadas", "timing": "com cuidado ao assinar rápido demais",
                     "conflict": "com cuidado com negociações tensas", "neutral": "com calma nos grandes compromissos"},
        "peace": {"risk": "com cuidado para não abraçar demais", "timing": "com cuidado para não sobrecarregar o dia",
                  "conflict": "com cuidado com momentos acalorados", "neutral": "com calma nos grandes compromissos"},
        "family": {"risk": "com cuidado com grandes gastos da família", "timing": "com cuidado com decisões apressadas em casa",
                   "conflict": "com cuidado com discussões antigas", "neutral": "com calma nos grandes compromissos"},
    },
    "hinglish": {
        "money": {"risk": "risky daav se savdhaan", "timing": "jaldi sign ya commit karne se savdhaan",
                  "conflict": "paison ki behes se savdhaan", "neutral": "bade commitments se pehle savdhaan"},
        "career": {"risk": "risky daav se savdhaan", "timing": "jaldbaazi ke faislon se savdhaan",
                   "conflict": "rishte bigaadne se savdhaan", "neutral": "bade commitments se pehle savdhaan"},
        "love": {"risk": "bade chhalaang se savdhaan", "timing": "jaldbaazi ke vaadon se savdhaan",
                 "conflict": "tikhe shabdon se savdhaan", "neutral": "bade commitments se pehle savdhaan"},
        "health": {"risk": "zyada zor lagane se savdhaan", "timing": "aaram chhodne se savdhaan",
                   "conflict": "stress aur khichaav se savdhaan", "neutral": "bade commitments se pehle savdhaan"},
        "business": {"risk": "risky daav se savdhaan", "timing": "bahut jaldi sign karne se savdhaan",
                     "conflict": "tanaav bhari negotiation se savdhaan", "neutral": "bade commitments se pehle savdhaan"},
        "peace": {"risk": "zyada bojh lene se savdhaan", "timing": "din par zyada bojh daalne se savdhaan",
                  "conflict": "garm pallon se savdhaan", "neutral": "bade commitments se pehle savdhaan"},
        "family": {"risk": "ghar ke bade kharch se savdhaan", "timing": "ghar mein jaldbaazi ke faislon se savdhaan",
                   "conflict": "purani behes se savdhaan", "neutral": "bade commitments se pehle savdhaan"},
    },
}
BAL_JOIN: Dict[str, str] = {   # {lead}, {good}, but {care}{tail}.
    "en": "{lead}, {good}, but {care}{tail}.", "es": "{lead}, {good}, pero {care}{tail}.",
    "pt": "{lead}, {good}, mas {care}{tail}.", "hinglish": "{lead} {good}, lekin {care}{tail}."}
BAL_TAIL: Dict[str, str] = {   # the specific week or month, inside the same sentence
    "en": ", especially {when}", "es": ", sobre todo {when}", "pt": ", principalmente {when}",
    "hinglish": ", khaaskar {when}"}
BAL_WEEK: Dict[str, str] = {"en": "the {w}", "es": "la {w}", "pt": "a {w}", "hinglish": "{w}"}
BAL_MOVE: Dict[str, str] = {   # Your move hedge when the caution is not about risk (risk uses KEEP_SMALL)
    "en": "But stay {care}.", "es": "Eso sí, ve {care}.", "pt": "Mas vá {care}.", "hinglish": "Bas {care} rahein."}
LEAD_JOIN: Dict[str, str] = {"en": "{lead}, {core}.", "es": "{lead}, {core}.",
                             "pt": "{lead}, {core}.", "hinglish": "{lead} {core}."}

# ── your move (one action) ───────────────────────────────────────────────────
MOVE: Dict[str, Dict[str, Dict[str, str]]] = {
    "en": {
        "money": {"open": "Pick the one money decision you have been putting off and act on it within the window.",
                  "care": "Wait a night before any money commitment, and write down the most you are comfortable spending or risking.",
                  "steady": "Keep your routine and review one recurring expense."},
        "career": {"open": "Make the one ask or application you have been rehearsing, inside the window.",
                   "care": "Finish what is open before you start anything new.",
                   "steady": "Keep your head down and do one piece of work you can be proud of."},
        "love": {"open": "Reach out to the person on your mind and say one honest, kind thing.",
                 "care": "Pause before replying when you feel tense, and choose a calmer hour to talk.",
                 "steady": "Spend one unhurried hour with someone who matters."},
        "health": {"open": "For the next seven days, go to sleep and wake up at the same time every day — pick your two times today.",
                   "care": "This week, go to bed at a reasonable hour on at least one night you would normally stay up late, and do not skip meals.",
                   "steady": "Keep your usual routine and add a ten-minute walk."},
        "business": {"open": "Take the one step you have already prepared, and keep it small enough to reverse.",
                     "care": "Test with something small before you commit money, people or a date.",
                     "steady": "Use the quiet to tidy numbers and notes rather than start something new."},
        "peace": {"open": "Give yourself ten quiet minutes at the same time each day.",
                  "care": "Switch your screen off an hour before sleep and keep one evening free.",
                  "steady": "Keep a short daily pause, even five minutes."},
        "family": {"open": "Plan one meal or outing together, with phones away.",
                   "care": "Listen first in the next family talk, and decide nothing big that day.",
                   "steady": "Check in with one relative you have not spoken to lately."},
    },
    "es": {
        "money": {"open": "Elige la decisión de dinero que has ido posponiendo y actúa dentro de la ventana.",
                  "care": "Espera una noche antes de cualquier compromiso de dinero y anota el máximo que te sientes cómodo gastando o arriesgando.",
                  "steady": "Mantén tu rutina y revisa un gasto recurrente."},
        "career": {"open": "Haz la petición o la postulación que has estado ensayando, dentro de la ventana.",
                   "care": "Termina lo que tienes abierto antes de empezar algo nuevo.",
                   "steady": "Mantén el foco y haz un trabajo del que te sientas orgulloso."},
        "love": {"open": "Escribe a esa persona que tienes en mente y dile algo honesto y amable.",
                 "care": "Haz una pausa antes de responder cuando estés tenso y elige una hora más calmada para hablar.",
                 "steady": "Pasa una hora sin prisa con alguien que importa."},
        "health": {"open": "Durante los próximos siete días, duerme y despierta a la misma hora cada día: elige hoy tus dos horas.",
                   "care": "Esta semana, acuéstate a una hora razonable al menos una noche en que normalmente te quedarías hasta tarde, y no te saltes comidas.",
                   "steady": "Mantén tu rutina y suma una caminata de diez minutos."},
        "business": {"open": "Da el paso que ya tienes preparado y mantenlo lo bastante pequeño como para poder revertirlo.",
                     "care": "Prueba con algo pequeño antes de comprometer dinero, gente o una fecha.",
                     "steady": "Aprovecha la calma para ordenar cifras y notas en vez de empezar algo nuevo."},
        "peace": {"open": "Regálate diez minutos de silencio a la misma hora cada día.",
                  "care": "Apaga la pantalla una hora antes de dormir y deja una noche libre.",
                  "steady": "Mantén una pausa diaria corta, aunque sean cinco minutos."},
        "family": {"open": "Planea una comida o salida juntos, sin celulares.",
                   "care": "Escucha primero en la próxima conversación familiar y no decidas nada grande ese día.",
                   "steady": "Escribe a un familiar con quien hace tiempo no hablas."},
    },
    "pt": {
        "money": {"open": "Escolha a decisão de dinheiro que você vem adiando e aja dentro da janela.",
                  "care": "Espere uma noite antes de qualquer compromisso de dinheiro e anote o máximo que você se sente confortável em gastar ou arriscar.",
                  "steady": "Mantenha a rotina e revise uma despesa recorrente."},
        "career": {"open": "Faça o pedido ou a candidatura que você vem ensaiando, dentro da janela.",
                   "care": "Termine o que está em aberto antes de começar algo novo.",
                   "steady": "Mantenha o foco e faça um trabalho do qual você se orgulhe."},
        "love": {"open": "Procure a pessoa em quem você pensa e diga algo honesto e gentil.",
                 "care": "Faça uma pausa antes de responder quando estiver tenso e escolha uma hora mais calma para conversar.",
                 "steady": "Passe uma hora sem pressa com alguém importante."},
        "health": {"open": "Pelos próximos sete dias, durma e acorde sempre no mesmo horário: escolha hoje os seus dois horários.",
                   "care": "Esta semana, vá para a cama num horário razoável em pelo menos uma noite em que normalmente ficaria acordado até tarde, e não pule refeições.",
                   "steady": "Mantenha a rotina e inclua uma caminhada de dez minutos."},
        "business": {"open": "Dê o passo que você já preparou e mantenha-o pequeno o bastante para poder reverter.",
                     "care": "Teste com algo pequeno antes de comprometer dinheiro, pessoas ou uma data.",
                     "steady": "Aproveite a calma para organizar números e anotações em vez de começar algo novo."},
        "peace": {"open": "Reserve dez minutos de silêncio no mesmo horário todos os dias.",
                  "care": "Desligue a tela uma hora antes de dormir e deixe uma noite livre.",
                  "steady": "Mantenha uma pausa diária curta, mesmo que sejam cinco minutos."},
        "family": {"open": "Planeje uma refeição ou um passeio juntos, sem celulares.",
                   "care": "Ouça primeiro na próxima conversa de família e não decida nada grande nesse dia.",
                   "steady": "Procure um parente com quem você não fala há tempo."},
    },
    "hinglish": {
        "money": {"open": "Paise ka wo ek faisla chuniye jo aap taal rahe hain aur window ke andar uspar kaam kijiye.",
                  "care": "Paise ke kisi bhi commitment se pehle ek raat ruk jaiye aur wo adhiktam rakam likhiye jo aap kharch ya risk karne mein comfortable hain.",
                  "steady": "Apni routine rakhiye aur ek baar-baar aane wala kharcha dekhiye."},
        "career": {"open": "Wo ek maang ya application kijiye jiski aap taiyaari kar rahe the, window ke andar.",
                   "care": "Naya kuch shuru karne se pehle jo khula hai use poora kijiye.",
                   "steady": "Dhyaan se kaam kijiye aur ek aisa kaam kijiye jispar garv ho."},
        "love": {"open": "Jis insaan ka khayal aa raha hai use sampark kijiye aur ek sachchi, pyaari baat kahiye.",
                 "care": "Tanaav mein jawab dene se pehle ruk jaiye aur baat karne ke liye shaant waqt chuniye.",
                 "steady": "Kisi khaas ke saath ek aaram ka ghanta bitaiye."},
        "health": {"open": "Agle saat din roz ek hi waqt par sona aur uthna — aaj apne do waqt chun lijiye.",
                   "care": "Is hafte kam se kam ek raat jab aap der tak jaagte, samay par so jaiye, aur khaana mat chhodiye.",
                   "steady": "Apni routine rakhiye aur das minute ki sair jodiye."},
        "business": {"open": "Wo ek kadam uthaiye jo aap pehle se taiyaar kar chuke hain, aur use itna chhota rakhiye ki palta ja sake.",
                     "care": "Paisa, log ya tareekh lagane se pehle chhoti cheez se test kijiye.",
                     "steady": "Shaanti ka use hisaab aur notes sahi karne mein kijiye, naya shuru karne mein nahin."},
        "peace": {"open": "Roz ek hi waqt par khud ko das minute ki chuppi dijiye.",
                  "care": "Sone se ek ghanta pehle screen band kijiye aur ek shaam khaali rakhiye.",
                  "steady": "Roz ek chhota pause rakhiye, paanch minute hi sahi."},
        "family": {"open": "Saath mein ek khaana ya outing plan kijiye, phone door rakh kar.",
                   "care": "Agli parivaar ki baat mein pehle sunein aur us din koi bada faisla na karein.",
                   "steady": "Kisi aise rishtedaar se baat kijiye jisse kaafi samay se baat nahin hui."},
    },
}

# ── window not open yet: the claim names the date, the move is to prepare ────
# {date} = the day the primary window starts ("Apr 6"; year added when it is not this year).
CORE_AHEAD: Dict[str, Dict[str, Dict[str, str]]] = {
    "en": {
        "money": {"open": "your best stretch for money starts {date}", "care": "money asks for care from {date}"},
        "career": {"open": "your best stretch for work starts {date}", "care": "work asks for care from {date}"},
        "love": {"open": "your best stretch for close relationships starts {date}", "care": "relationships ask for care from {date}"},
        "health": {"open": "your best stretch for building a routine starts {date}", "care": "your body asks for care from {date}"},
        "business": {"open": "your best stretch for decisions and partnerships starts {date}", "care": "business commitments ask for care from {date}"},
        "peace": {"open": "your best stretch for inner calm starts {date}", "care": "your peace of mind asks for care from {date}"},
        "family": {"open": "your best stretch for home and family starts {date}", "care": "family matters ask for care from {date}"},
    },
    "es": {
        "money": {"open": "tu mejor tramo para el dinero empieza el {date}", "care": "el dinero pide cuidado desde el {date}"},
        "career": {"open": "tu mejor tramo para el trabajo empieza el {date}", "care": "el trabajo pide cuidado desde el {date}"},
        "love": {"open": "tu mejor tramo para las relaciones cercanas empieza el {date}", "care": "las relaciones piden cuidado desde el {date}"},
        "health": {"open": "tu mejor tramo para armar una rutina empieza el {date}", "care": "tu cuerpo pide cuidado desde el {date}"},
        "business": {"open": "tu mejor tramo para decisiones y alianzas empieza el {date}", "care": "los compromisos del negocio piden cuidado desde el {date}"},
        "peace": {"open": "tu mejor tramo para la calma interior empieza el {date}", "care": "tu tranquilidad pide cuidado desde el {date}"},
        "family": {"open": "tu mejor tramo para el hogar y la familia empieza el {date}", "care": "los asuntos familiares piden cuidado desde el {date}"},
    },
    "pt": {
        "money": {"open": "o seu melhor trecho para o dinheiro começa em {date}", "care": "o dinheiro pede cuidado a partir de {date}"},
        "career": {"open": "o seu melhor trecho para o trabalho começa em {date}", "care": "o trabalho pede cuidado a partir de {date}"},
        "love": {"open": "o seu melhor trecho para as relações próximas começa em {date}", "care": "as relações pedem cuidado a partir de {date}"},
        "health": {"open": "o seu melhor trecho para montar uma rotina começa em {date}", "care": "o seu corpo pede cuidado a partir de {date}"},
        "business": {"open": "o seu melhor trecho para decisões e parcerias começa em {date}", "care": "os compromissos do negócio pedem cuidado a partir de {date}"},
        "peace": {"open": "o seu melhor trecho para a calma interior começa em {date}", "care": "a sua tranquilidade pede cuidado a partir de {date}"},
        "family": {"open": "o seu melhor trecho para a casa e a família começa em {date}", "care": "os assuntos de família pedem cuidado a partir de {date}"},
    },
    "hinglish": {
        "money": {"open": "paise ke liye aapka sabse achha daur {date} se shuru hota hai", "care": "paise mein {date} se dhyaan chahiye"},
        "career": {"open": "kaam ke liye aapka sabse achha daur {date} se shuru hota hai", "care": "kaam mein {date} se dhyaan chahiye"},
        "love": {"open": "kareebi rishton ke liye aapka sabse achha daur {date} se shuru hota hai", "care": "rishton mein {date} se narmi chahiye"},
        "health": {"open": "routine banane ke liye aapka sabse achha daur {date} se shuru hota hai", "care": "sharir ko {date} se dhyaan chahiye"},
        "business": {"open": "faisle aur partnerships ke liye aapka sabse achha daur {date} se shuru hota hai", "care": "business ke commitments mein {date} se dhyaan chahiye"},
        "peace": {"open": "andar ke sukoon ke liye aapka sabse achha daur {date} se shuru hota hai", "care": "mann ki shaanti ko {date} se dhyaan chahiye"},
        "family": {"open": "ghar aur parivaar ke liye aapka sabse achha daur {date} se shuru hota hai", "care": "parivaar ke maamlon mein {date} se dhyaan chahiye"},
    },
}

MOVE_AHEAD: Dict[str, Dict[str, Dict[str, str]]] = {
    "en": {
        "money": {"open": "Use the time before {date} to pick the one money decision you have been putting off; act on it from {date}.",
                  "care": "Until {date}, write down the most you are comfortable spending or risking, and wait a night before any money commitment."},
        "career": {"open": "Use the time before {date} to get the one ask or application ready; make it from {date}.",
                   "care": "Until {date}, finish what is open so you start the careful stretch with a clean record."},
        "love": {"open": "Use the time before {date} to think of what you want to say; reach out from {date}.",
                 "care": "Until {date}, notice what tires you in close talks, so you can choose calmer hours from {date}."},
        "health": {"open": "Use the time before {date} to choose the times you will go to sleep and wake up each day; keep them from {date}.",
                   "care": "Until {date}, settle your sleep and meals, so you are already steady when the careful stretch begins."},
        "business": {"open": "Use the time before {date} to prepare the one step you will take; take it from {date}, kept small.",
                     "care": "Until {date}, plan a small test, so nothing big is committed once the careful stretch begins."},
        "peace": {"open": "Use the time before {date} to clear one evening a week; use it for quiet from {date}.",
                  "care": "Until {date}, start winding down earlier, so quiet evenings are already a habit by {date}."},
        "family": {"open": "Use the time before {date} to plan one meal or outing together; hold it from {date}.",
                   "care": "Until {date}, check in gently with the family, so big household decisions are not left for {date}."},
    },
    "es": {
        "money": {"open": "Usa el tiempo antes del {date} para elegir la decisión de dinero que has ido posponiendo; actúa desde el {date}.",
                  "care": "Hasta el {date}, anota el máximo que te sientes cómodo gastando o arriesgando y espera una noche antes de cualquier compromiso de dinero."},
        "career": {"open": "Usa el tiempo antes del {date} para dejar lista la petición o postulación; hazla desde el {date}.",
                   "care": "Hasta el {date}, termina lo que tienes abierto para empezar el tramo de cuidado con el historial limpio."},
        "love": {"open": "Usa el tiempo antes del {date} para pensar qué quieres decir; acércate desde el {date}.",
                 "care": "Hasta el {date}, fíjate qué te cansa en las conversaciones cercanas y elige horas más calmadas desde el {date}."},
        "health": {"open": "Usa el tiempo antes del {date} para elegir a qué hora te dormirás y te despertarás cada día; cúmplelas desde el {date}.",
                   "care": "Hasta el {date}, ordena tu sueño y tus comidas para llegar ya estable al tramo de cuidado."},
        "business": {"open": "Usa el tiempo antes del {date} para preparar el paso que darás; dalo desde el {date}, en pequeño.",
                     "care": "Hasta el {date}, planea una prueba pequeña para no comprometer nada grande cuando empiece el tramo de cuidado."},
        "peace": {"open": "Usa el tiempo antes del {date} para despejar una noche a la semana; úsala para la quietud desde el {date}.",
                  "care": "Hasta el {date}, empieza a bajar el ritmo más temprano para que las noches tranquilas sean ya un hábito."},
        "family": {"open": "Usa el tiempo antes del {date} para planear una comida o salida juntos; hazla desde el {date}.",
                   "care": "Hasta el {date}, conversa con calma con tu familia para no dejar las decisiones grandes del hogar para esa fecha."},
    },
    "pt": {
        "money": {"open": "Use o tempo antes de {date} para escolher a decisão de dinheiro que você vem adiando; aja a partir de {date}.",
                  "care": "Até {date}, anote o máximo que você se sente confortável em gastar ou arriscar e espere uma noite antes de qualquer compromisso de dinheiro."},
        "career": {"open": "Use o tempo antes de {date} para deixar pronto o pedido ou a candidatura; faça-o a partir de {date}.",
                   "care": "Até {date}, termine o que está em aberto para começar o trecho de cuidado com o histórico limpo."},
        "love": {"open": "Use o tempo antes de {date} para pensar no que quer dizer; procure a pessoa a partir de {date}.",
                 "care": "Até {date}, repare no que o cansa nas conversas próximas e escolha horas mais calmas a partir de {date}."},
        "health": {"open": "Use o tempo antes de {date} para escolher a que horas vai dormir e acordar a cada dia; cumpra-os a partir de {date}.",
                   "care": "Até {date}, organize o sono e as refeições para chegar já estável ao trecho de cuidado."},
        "business": {"open": "Use o tempo antes de {date} para preparar o passo que vai dar; dê-o a partir de {date}, em pequeno.",
                     "care": "Até {date}, planeje um teste pequeno para não comprometer nada grande quando o trecho de cuidado começar."},
        "peace": {"open": "Use o tempo antes de {date} para liberar uma noite por semana; use-a para o silêncio a partir de {date}.",
                  "care": "Até {date}, comece a desacelerar mais cedo para que as noites calmas já sejam um hábito."},
        "family": {"open": "Use o tempo antes de {date} para planejar uma refeição ou um passeio juntos; faça-o a partir de {date}.",
                   "care": "Até {date}, converse com calma com a família para não deixar as decisões grandes da casa para essa data."},
    },
    "hinglish": {
        "money": {"open": "{date} se pehle ka waqt paise ka wo ek faisla chunne mein lagaiye jo aap taal rahe hain; {date} se kaam kijiye.",
                  "care": "{date} tak wo adhiktam rakam likh lijiye jo aap kharch ya risk karne mein comfortable hain, aur paise ke commitment se pehle ek raat ruk jaiye."},
        "career": {"open": "{date} se pehle ka waqt wo ek maang ya application taiyaar karne mein lagaiye; {date} se kijiye.",
                   "care": "{date} tak jo khula hai use poora kijiye, taaki dhyaan wale daur mein record saaf rahe."},
        "love": {"open": "{date} se pehle soch lijiye ki kya kehna hai; {date} se sampark kijiye.",
                 "care": "{date} tak dekhiye ki kareebi baat-cheet mein kya thakata hai, aur {date} se shaant waqt chuniye."},
        "health": {"open": "{date} se pehle chun lijiye ki roz kitne baje sona aur uthna hai; {date} se use nibhaiye.",
                   "care": "{date} tak neend aur khaana theek kar lijiye, taaki dhyaan wale daur mein aap pehle se sthir hon."},
        "business": {"open": "{date} se pehle wo ek kadam taiyaar kijiye; {date} se uthaiye, chhota rakh kar.",
                     "care": "{date} tak ek chhota test plan kijiye, taaki dhyaan wala daur shuru hone par kuch bada na lage."},
        "peace": {"open": "{date} se pehle hafte mein ek shaam khaali kijiye; {date} se use shaanti ke liye rakhiye.",
                  "care": "{date} tak thoda jaldi thehrna shuru kijiye, taaki shaant shaamein aadat ban jayein."},
        "family": {"open": "{date} se pehle saath mein ek khaana ya outing plan kijiye; {date} se kijiye.",
                   "care": "{date} tak parivaar se narmi se baat kijiye, taaki ghar ke bade faisle usi tareekh par na atkein."},
    },
}

# ── remedy block ─────────────────────────────────────────────────────────────
REMEDY_SUMMARY: Dict[str, str] = {
    "en": "Start with the free steps. Each one is small and works on its own.",
    "es": "Empieza con los pasos gratuitos. Cada uno es pequeño y funciona por sí solo.",
    "pt": "Comece pelos passos gratuitos. Cada um é pequeno e funciona sozinho.",
    "hinglish": "Muft kadamon se shuru kijiye. Har kadam chhota hai aur akele bhi kaam karta hai.",
}
FREE_STEPS: Dict[str, Dict[str, tuple]] = {
    "en": {
        "money": ("Before any money decision this week, wait one night and write down the most you are comfortable spending or risking.",
                  "Give a small amount, or an hour of your time, to someone who needs it, quietly."),
        "career": ("Finish one task you have been avoiding before you start anything new.",
                   "Thank one person who helped your work, in writing."),
        "love": ("Say one honest, kind thing to someone close, in person if you can.",
                 "Put your phone away for one meal with them."),
        "health": ("For seven days, go to sleep and wake up at the same time every day.",
                   "Take a ten-minute walk after your main meal."),
        "business": ("Write down the one commitment you are weighing and what you would lose if it failed, then decide.",
                     "Talk it through with one person who will tell you honestly."),
        "peace": ("Sit in silence for five minutes at the same time each day.",
                  "Switch your screen off an hour before sleep."),
        "family": ("Share one meal with your family without phones.",
                   "Call one relative you have been meaning to call."),
    },
    "es": {
        "money": ("Antes de cualquier decisión de dinero esta semana, espera una noche y anota el máximo que te sientes cómodo gastando o arriesgando.",
                  "Da una pequeña cantidad, o una hora de tu tiempo, a alguien que lo necesite, en silencio."),
        "career": ("Termina una tarea que has estado evitando antes de empezar algo nuevo.",
                   "Agradece por escrito a una persona que ayudó a tu trabajo."),
        "love": ("Dile algo honesto y amable a alguien cercano, en persona si puedes.",
                 "Guarda el celular durante una comida con esa persona."),
        "health": ("Durante siete días, duerme y despierta a la misma hora cada día.",
                   "Camina diez minutos después de tu comida principal."),
        "business": ("Anota el compromiso que estás pensando y lo que perderías si fallara, y luego decide.",
                     "Háblalo con una persona que te dirá la verdad."),
        "peace": ("Siéntate en silencio cinco minutos a la misma hora cada día.",
                  "Apaga la pantalla una hora antes de dormir."),
        "family": ("Compartan una comida en familia sin celulares.",
                   "Llama a un familiar a quien querías llamar."),
    },
    "pt": {
        "money": ("Antes de qualquer decisão de dinheiro esta semana, espere uma noite e anote o máximo que você se sente confortável em gastar ou arriscar.",
                  "Dê uma pequena quantia, ou uma hora do seu tempo, a alguém que precise, em silêncio."),
        "career": ("Termine uma tarefa que você vem evitando antes de começar algo novo.",
                   "Agradeça por escrito a uma pessoa que ajudou o seu trabalho."),
        "love": ("Diga algo honesto e gentil a alguém próximo, pessoalmente se puder.",
                 "Guarde o celular durante uma refeição com essa pessoa."),
        "health": ("Por sete dias, durma e acorde sempre no mesmo horário.",
                   "Caminhe dez minutos depois da refeição principal."),
        "business": ("Anote o compromisso que você está pensando e o que perderia se falhasse, e depois decida.",
                     "Converse com uma pessoa que vai dizer a verdade."),
        "peace": ("Sente-se em silêncio por cinco minutos no mesmo horário todos os dias.",
                  "Desligue a tela uma hora antes de dormir."),
        "family": ("Façam uma refeição em família sem celulares.",
                   "Ligue para um parente para quem você queria ligar."),
    },
    "hinglish": {
        "money": ("Is hafte paise ke kisi bhi faisle se pehle ek raat ruk kar wo adhiktam rakam likhiye jo aap kharch ya risk karne mein comfortable hain.",
                  "Kisi zarooratmand ko chupke se thodi rakam ya ek ghanta apna waqt dijiye."),
        "career": ("Naya kuch shuru karne se pehle ek taala hua kaam poora kijiye.",
                   "Jisne aapke kaam mein madad ki use likhkar shukriya kahiye."),
        "love": ("Kisi kareebi se ek sachchi, pyaari baat kahiye, ho sake to aamne-saamne.",
                 "Unke saath ek khaane ke dauran phone door rakhiye."),
        "health": ("Saat din tak roz ek hi waqt par sona aur uthna.",
                   "Mukhya khaane ke baad das minute tahliye."),
        "business": ("Jis commitment par soch rahe hain use likhiye aur ye bhi ki fail hone par kya khoyenge, phir faisla kijiye.",
                     "Ek aise insaan se baat kijiye jo sach bolega."),
        "peace": ("Roz ek hi waqt par paanch minute chup baithiye.",
                  "Sone se ek ghanta pehle screen band kijiye."),
        "family": ("Parivaar ke saath ek khaana phone ke bina khaiye.",
                   "Ek rishtedaar ko phone kijiye jise karna chahte the."),
    },
}
MANTRA_STEP: Dict[str, str] = {
    "en": "If it feels right, chant {name}: 11 times, or 108 if you have the time.",
    "es": "Si lo sientes adecuado, recita {name}: 11 veces, o 108 si tienes tiempo.",
    "pt": "Se parecer certo, recite {name}: 11 vezes, ou 108 se tiver tempo.",
    "hinglish": "Agar theek lage to {name} ka jaap kijiye: 11 baar, ya samay ho to 108 baar.",
}
STONE_STEP: Dict[str, str] = {
    "en": "Optional, and only if you want it: {stone} is the traditional supporting stone for your chart. The free steps come first, and you can skip this one.",
    "es": "Opcional, y solo si quieres: {stone} es la piedra de apoyo tradicional para tu carta. Primero van los pasos gratuitos, y puedes omitir este.",
    "pt": "Opcional, e só se quiser: {stone} é a pedra de apoio tradicional para o seu mapa. Os passos gratuitos vêm primeiro, e você pode pular este.",
    "hinglish": "Optional, aur sirf agar aap chahein: {stone} aapke chart ka paramparik sahayak patthar hai. Muft kadam pehle, aur ise chhod bhi sakte hain.",
}

# ── why / reasoning ──────────────────────────────────────────────────────────
WHY_BULLET: Dict[str, Dict[str, str]] = {
    "en": {
        "chapter_core": "The chapter you are in right now is tied directly to {area}.",
        "chapter_theme": "The chapter you are in right now touches the themes behind {area}.",
        "agree": "A second way of reading your timeline points the same way.",
        "signals_open": "Slow-moving influences support {area} between {start} and {end}.",
        "signals_care": "Slow-moving influences press on {area} between {start} and {end}.",
        "signals_open_day": "Slow-moving influences support {area} on {start}.",
        "signals_care_day": "Slow-moving influences press on {area} on {start}.",
        "none_dated": "Nothing is dated sharply inside this stretch, so this is a steady read and not a dated window.",
        "approx_time": "Your birth time is not exact, so treat the dates as approximate.",
        "no_time": "Without your birth time, this read is a rough guide, not a precise one.",
    },
    "es": {
        "chapter_core": "La etapa en la que estás ahora está ligada directamente a {area}.",
        "chapter_theme": "La etapa en la que estás ahora toca los temas detrás de {area}.",
        "agree": "Una segunda forma de leer tu línea de tiempo apunta en la misma dirección.",
        "signals_open": "Influencias lentas apoyan {area} entre el {start} y el {end}.",
        "signals_care": "Influencias lentas presionan {area} entre el {start} y el {end}.",
        "signals_open_day": "Influencias lentas apoyan {area} el {start}.",
        "signals_care_day": "Influencias lentas presionan {area} el {start}.",
        "none_dated": "Nada está fechado con precisión en este tramo, así que es una lectura estable y no una ventana con fechas.",
        "approx_time": "Tu hora de nacimiento no es exacta, así que toma las fechas como aproximadas.",
        "no_time": "Sin tu hora de nacimiento, esta lectura es una guía aproximada, no precisa.",
    },
    "pt": {
        "chapter_core": "A fase em que você está agora está ligada diretamente a {area}.",
        "chapter_theme": "A fase em que você está agora toca os temas por trás de {area}.",
        "agree": "Uma segunda forma de ler a sua linha do tempo aponta na mesma direção.",
        "signals_open": "Influências lentas apoiam {area} entre {start} e {end}.",
        "signals_care": "Influências lentas pressionam {area} entre {start} e {end}.",
        "signals_open_day": "Influências lentas apoiam {area} em {start}.",
        "signals_care_day": "Influências lentas pressionam {area} em {start}.",
        "none_dated": "Nada está datado com precisão neste trecho, então é uma leitura estável e não uma janela com datas.",
        "approx_time": "A sua hora de nascimento não é exata, então trate as datas como aproximadas.",
        "no_time": "Sem a sua hora de nascimento, esta leitura é um guia aproximado, não preciso.",
    },
    "hinglish": {
        "chapter_core": "Aap jis daur mein hain wo seedha {area} se juda hai.",
        "chapter_theme": "Aap jis daur mein hain wo {area} ke peeche ke vishayon ko chhooti hai.",
        "agree": "Aapki timeline padhne ka doosra tareeka bhi isi taraf ishara karta hai.",
        "signals_open": "Dheemi chalne wale prabhav {start} se {end} ke beech {area} ko support karte hain.",
        "signals_care": "Dheemi chalne wale prabhav {start} se {end} ke beech {area} par dabaav daalte hain.",
        "signals_open_day": "Dheemi chalne wale prabhav {start} ko {area} ko support karte hain.",
        "signals_care_day": "Dheemi chalne wale prabhav {start} ko {area} par dabaav daalte hain.",
        "none_dated": "Is stretch mein kuch bhi tez taareekh ke saath nahin hai, isliye ye sthir padhai hai, dated window nahin.",
        "approx_time": "Aapka janm samay exact nahin hai, isliye taareekhon ko lagbhag maniye.",
        "no_time": "Janm samay ke bina ye padhai ek mota andaaza hai, sahi nahin.",
    },
}
BASED_ON: Dict[str, Dict[str, str]] = {
    "en": {"chapter": "Your current chapter", "today": "Today's movement",
           "month": "The next 30 days", "year": "Your year",
           "second": "A second reading of your timeline", "dated": "Dated movements in this window"},
    "es": {"chapter": "Tu etapa actual", "today": "El movimiento de hoy",
           "month": "Los próximos 30 días", "year": "Tu año",
           "second": "Una segunda lectura de tu línea de tiempo", "dated": "Movimientos con fecha en esta ventana"},
    "pt": {"chapter": "A sua fase atual", "today": "O movimento de hoje",
           "month": "Os próximos 30 dias", "year": "O seu ano",
           "second": "Uma segunda leitura da sua linha do tempo", "dated": "Movimentos com data nesta janela"},
    "hinglish": {"chapter": "Aapka maujooda daur", "today": "Aaj ki chaal",
                 "month": "Agle 30 din", "year": "Aapka saal",
                 "second": "Aapki timeline ki doosri padhai", "dated": "Is window ki tareekh wali halchal"},
}
CONFIDENCE_NOTE: Dict[str, Dict[str, str]] = {
    "en": {"high": "High confidence: several independent signs agree and the dates are specific.",
           "medium": "Medium confidence: the main signs agree, but the dates are broad.",
           "low": "Lower confidence: treat this as a gentle lean, not a promise."},
    "es": {"high": "Confianza alta: varias señales independientes coinciden y las fechas son concretas.",
           "medium": "Confianza media: las señales principales coinciden, pero las fechas son amplias.",
           "low": "Confianza menor: tómalo como una inclinación suave, no como una promesa."},
    "pt": {"high": "Confiança alta: vários sinais independentes concordam e as datas são específicas.",
           "medium": "Confiança média: os sinais principais concordam, mas as datas são amplas.",
           "low": "Confiança menor: encare como uma inclinação suave, não uma promessa."},
    "hinglish": {"high": "Zyada bharosa: kai alag sanket sahmat hain aur taareekhein khaas hain.",
                 "medium": "Madhyam bharosa: mukhya sanket sahmat hain, par taareekhein chaudi hain.",
                 "low": "Kam bharosa: ise halka jhukaav samjhein, vaada nahin."},
}

# ── reveal lines ─────────────────────────────────────────────────────────────
PLANET: Dict[str, Dict[str, str]] = {
    "en": {"Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Mercury": "Mercury", "Jupiter": "Jupiter",
           "Venus": "Venus", "Saturn": "Saturn", "Rahu": "Rahu", "Ketu": "Ketu"},
    "es": {"Sun": "Sol", "Moon": "Luna", "Mars": "Marte", "Mercury": "Mercurio", "Jupiter": "Júpiter",
           "Venus": "Venus", "Saturn": "Saturno", "Rahu": "Rahu", "Ketu": "Ketu"},
    "pt": {"Sun": "Sol", "Moon": "Lua", "Mars": "Marte", "Mercury": "Mercúrio", "Jupiter": "Júpiter",
           "Venus": "Vênus", "Saturn": "Saturno", "Rahu": "Rahu", "Ketu": "Ketu"},
    "hinglish": {"Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Mercury": "Mercury", "Jupiter": "Jupiter",
                 "Venus": "Venus", "Saturn": "Saturn", "Rahu": "Rahu", "Ketu": "Ketu"},
}
REVEAL_BIG: Dict[str, str] = {
    "en": "Since {start} you are in a {planet} chapter. It runs until {end}.",
    "es": "Desde {start} estás en una etapa de {planet}. Dura hasta {end}.",
    "pt": "Desde {start} você está em uma fase de {planet}. Ela vai até {end}.",
    "hinglish": "{start} se aap {planet} ke daur mein hain. Ye {end} tak chalega.",
}
REVEAL_STRETCH: Dict[str, str] = {
    "en": "{area} stretch, from {start} to {end}.",
    "es": "Un tramo {area}, de {start} a {end}.",
    "pt": "Um trecho {area}, de {start} a {end}.",
    "hinglish": "{area} daur, {start} se {end} tak.",
}
# life-area adjective for the reveal's second line, keyed by house number
REVEAL_AREA: Dict[str, Dict[int, str]] = {
    "en": {1: "A self-focused", 2: "A money-focused", 3: "A drive-and-effort focused", 4: "A home-focused",
           5: "A creative and learning-focused", 6: "A service-and-effort focused", 7: "A partnership-focused",
           8: "A deep-change focused", 9: "A learning-and-luck focused", 10: "A work-focused",
           11: "A gains-and-network focused", 12: "A rest-and-letting-go focused"},
    "es": {1: "centrado en ti", 2: "centrado en el dinero", 3: "centrado en el esfuerzo y la iniciativa",
           4: "centrado en el hogar", 5: "centrado en la creatividad y el aprendizaje",
           6: "centrado en el servicio y el esfuerzo", 7: "centrado en las alianzas",
           8: "centrado en cambios profundos", 9: "centrado en el aprendizaje y la suerte",
           10: "centrado en el trabajo", 11: "centrado en logros y redes",
           12: "centrado en el descanso y en soltar"},
    "pt": {1: "focado em você", 2: "focado em dinheiro", 3: "focado em esforço e iniciativa",
           4: "focado na casa", 5: "focado em criatividade e aprendizado",
           6: "focado em serviço e esforço", 7: "focado em parcerias",
           8: "focado em mudanças profundas", 9: "focado em aprendizado e sorte",
           10: "focado no trabalho", 11: "focado em conquistas e rede de contatos",
           12: "focado em descanso e desapego"},
    "hinglish": {1: "Khud par kendrit", 2: "Paise par kendrit", 3: "Mehnat aur pehal par kendrit",
                 4: "Ghar par kendrit", 5: "Rachnatmakta aur seekhne par kendrit",
                 6: "Seva aur mehnat par kendrit", 7: "Partnership par kendrit",
                 8: "Gehre badlaav par kendrit", 9: "Seekhne aur kismat par kendrit",
                 10: "Kaam par kendrit", 11: "Laabh aur network par kendrit",
                 12: "Aaram aur chhodne par kendrit"},
}


# ── tile headline + verdict: what the Home row says in plain words (no status jargon) ──
TILE_QUIET: Dict[str, str] = {
    "en": "Nothing pressing right now.", "es": "Nada urgente por ahora.",
    "pt": "Nada urgente por enquanto.", "hinglish": "Abhi kuchh zaroori nahi."}
TILE_VERDICT: Dict[str, Dict[str, str]] = {      # by tag_kind
    "en": {"open_now": "Good time", "opens": "Good time ahead", "care_now": "Be careful",
           "care_from": "Be careful ahead", "quiet": "Quiet"},
    "es": {"open_now": "Buen momento", "opens": "Buen momento más adelante", "care_now": "Ten cuidado",
           "care_from": "Cuidado más adelante", "quiet": "Tranquilo"},
    "pt": {"open_now": "Bom momento", "opens": "Bom momento mais à frente", "care_now": "Tenha cuidado",
           "care_from": "Cuidado mais à frente", "quiet": "Tranquilo"},
    "hinglish": {"open_now": "Achha samay", "opens": "Aage achha samay", "care_now": "Savdhaan rahein",
                 "care_from": "Aage savdhaani", "quiet": "Shaant"},
}


def pick(table: Dict[str, dict], lang: str):
    """The language's table, English if the language has none."""
    return table.get(lang) or table["en"]


FULL_MONTHS: Dict[str, tuple] = {
    "en": ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"),
    "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
           "septiembre", "octubre", "noviembre", "diciembre"),
    "pt": ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
           "setembro", "outubro", "novembro", "dezembro"),
    "hinglish": ("January", "February", "March", "April", "May", "June", "July", "August",
                 "September", "October", "November", "December"),
}


def month_year(d: date, lang: str) -> str:
    m = pick(FULL_MONTHS, lang)[d.month - 1]
    return f"{m} {d.year}" if lang in ("en", "hinglish") else f"{m} de {d.year}"


REVEAL_BIG_FROM_BIRTH: Dict[str, str] = {
    "en": "You are in a {planet} chapter. It runs until {end}.",
    "es": "Estás en una etapa de {planet}. Dura hasta {end}.",
    "pt": "Você está em uma fase de {planet}. Ela vai até {end}.",
    "hinglish": "Aap {planet} ke daur mein hain. Ye {end} tak chalega.",
}

# ── long scales lead with the NEXT window; a later, stronger one is a second sentence ───────────
# {start} / {end} are full dates ("Jul 1, 2028").
STRONGEST_TAIL: Dict[str, Dict[str, str]] = {
    "en": {"open": "The strongest stretch is {start} to {end}.", "care": "The most demanding stretch is {start} to {end}."},
    "es": {"open": "El tramo más fuerte va del {start} al {end}.", "care": "El tramo más exigente va del {start} al {end}."},
    "pt": {"open": "O trecho mais forte vai de {start} a {end}.", "care": "O trecho mais exigente vai de {start} a {end}."},
    "hinglish": {"open": "Sabse mazboot daur {start} se {end} tak hai.", "care": "Sabse bhaari daur {start} se {end} tak hai."},
}
# detail.next_months rows built from the topic's own dated windows
WINDOW_ITEM: Dict[str, Dict[str, str]] = {
    "en": {"open": "A good stretch for {area}", "care": "A stretch that asks for care with {area}"},
    "es": {"open": "Un buen tramo para {area}", "care": "Un tramo que pide cuidado con {area}"},
    "pt": {"open": "Um bom trecho para {area}", "care": "Um trecho que pede cuidado com {area}"},
    "hinglish": {"open": "{area} ke liye achha daur", "care": "{area} mein dhyaan maangne wala daur"},
}
