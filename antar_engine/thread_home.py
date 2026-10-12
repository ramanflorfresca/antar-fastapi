"""[thread-home 2026-10-12, P1] The conversation Home: Antar's opening message, the reply router and the cards.

DETERMINISTIC. Every number, date and window in a message or card comes from an engine that already exists (the day's
decision block, the Windows feed, the topic reads, the phase view, the daily loop). The sentences around them are templates
in en and es; engine text (headline, move, claim, prediction) is reused verbatim. No LLM is involved in P1, so nothing here can
invent a date. A later phase may let an LLM phrase these sentences, behind the integrity gate; the cards stay as they are.

This module is pure (no I/O). main.py fetches the engine outputs and passes them in; tests pass fixtures.

Card contract (what the app renders):
  {"type": str, "title": str|None, "data": dict, "source": str, "link": {"route": str}|None}
Reply contract:
  {"intent": str, "messages": [{"role": "antar", "text": str}], "cards": [card], "quick_replies": [{"label", "send"}]}
"""
from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Any, Dict, List, Optional

from antar_engine import topic_copy as TC

LANGS = ("en", "es")
TOPICS = ("money", "career", "love", "health", "business", "peace", "family")


def lang_of(language) -> str:
    return "es" if str(language or "").lower().startswith("es") else "en"


# ───────────────────────────── copy ─────────────────────────────
_T: Dict[str, Dict[str, str]] = {
    "en": {
        "morning": "Good morning, {n}.", "afternoon": "Good afternoon, {n}.", "evening": "Good evening, {n}.",
        "hello": "Good to see you, {n}.",
        "closing": "Your {t} window closes tonight.", "open_days": "Your {t} window is open for {d} more days.",
        "care_now": "A careful stretch for {t} is running until {e}.", "care_soon": "A careful stretch for {t} starts {s}.",
        "heads_up": "{p} has a tender day today.",
        "two": "Two things matter today. {a} {b}", "one": "One thing matters today. {a}",
        "walk": "Want me to walk you through it?", "one_thing": "Want the one thing for today?",
        "heads_nudge": "If you need something from {p}, ask tomorrow or go gently.",
        "closing_nudge": "If you have been putting off a {t} decision, today is easier than the weeks after.",
        "q_walk": "Yes, walk me through it", "q_move": "What's my move today?", "q_year": "Show me my year", "q_else": "Something else",
        "q_chapter": "What chapter am I in?", "q_month": "How's this month?", "q_loop": "Where am I today?",
        "today_lead": "Here is the one thing for today.", "move_missing": "I couldn't pull today's read up just now. Try again in a moment.",
        "year_lead": "Your year runs birthday to birthday. Here is how it looks.", "month_lead": "The next thirty days, in short.",
        "chapter_lead": "Here is the long chapter you are in, and the shift inside it.", "chapter_missing": "I can't read your chapter dates right now.",
        "loop_lead": "Here is where you are today.", "topic_lead": "Here is {t}.", "heads_none": "Nobody you follow has a tender day today.",
        "heads_lead": "You asked me to watch the people you starred.", "heads_unset": "Star up to three people in People and I'll tell you when their day looks hard.",
        "deciding": "Good. Tell me the decision in one line, and the date you need to make it by, if there is one. I'll check it against your windows and tell you how confident I am.",
        "stuck": "Before I answer: is it a decision you're weighing, a worry that's sitting on you, or timing for something you already know you'll do?",
        "worry": "Then I'll go gently. Is it about money, work, a person, or your health? I won't forecast how someone else feels, but I can tell you what's yours to do about it.",
        "timing": "Then tell me what you're planning and I'll find the stretch. Or start with the big picture.",
        "vague": "I want to get this right rather than guess. Is this about a decision, a worry, or timing?",
        "reframed": "I can't tell you what another person feels or will do, and I won't pretend to. Here is your side of it.",
        "ask_fail": "I couldn't read that one just now. Try again in a moment.",
        "starters_lead": "No need to type. Pick where to start.",
        "a_decision": "A decision", "a_worry": "A worry", "just_timing": "Just timing", "retry": "Try again",
        "src_day": "today's day read, computed from your chart", "src_topic": "your {t} read, computed from your chart",
        "src_year": "your birthday-year windows, computed", "src_month": "your next 30 days, computed",
        "src_phase": "your main period and shift, dates from your chart", "src_loop": "your daily loop",
        "src_people": "the day read for people you starred", "src_ask": "your question, answered from your chart",
        "src_windows": "your windows, computed",
    },
    "es": {
        "morning": "Buenos días, {n}.", "afternoon": "Buenas tardes, {n}.", "evening": "Buenas noches, {n}.", "hello": "Qué bueno verte, {n}.",
        "closing": "Tu ventana de {t} se cierra esta noche.", "open_days": "Tu ventana de {t} sigue abierta {d} días más.",
        "care_now": "Un tramo de cuidado en {t} dura hasta el {e}.", "care_soon": "Un tramo de cuidado en {t} empieza el {s}.",
        "heads_up": "{p} tiene un día sensible hoy.",
        "two": "Hoy importan dos cosas. {a} {b}", "one": "Hoy importa una cosa. {a}",
        "walk": "¿Quieres que lo veamos paso a paso?", "one_thing": "¿Quieres lo único importante de hoy?",
        "heads_nudge": "Si necesitas algo de {p}, pídelo mañana o ve con calma.",
        "closing_nudge": "Si has estado posponiendo una decisión de {t}, hoy es más fácil que en las semanas siguientes.",
        "q_walk": "Sí, vamos paso a paso", "q_move": "¿Cuál es mi jugada de hoy?", "q_year": "Muéstrame mi año", "q_else": "Otra cosa",
        "q_chapter": "¿En qué etapa estoy?", "q_month": "¿Cómo va este mes?", "q_loop": "¿Cómo voy hoy?",
        "today_lead": "Esto es lo único importante de hoy.", "move_missing": "No pude cargar tu lectura de hoy. Inténtalo de nuevo en un momento.",
        "year_lead": "Tu año va de cumpleaños a cumpleaños. Así se ve.", "month_lead": "Los próximos treinta días, en breve.",
        "chapter_lead": "Esta es la etapa larga en la que estás y el cambio dentro de ella.", "chapter_missing": "No puedo leer las fechas de tu etapa ahora.",
        "loop_lead": "Así vas hoy.", "topic_lead": "Esto es {t}.", "heads_none": "Nadie de los que sigues tiene un día sensible hoy.",
        "heads_lead": "Me pediste vigilar a las personas que marcaste.", "heads_unset": "Marca hasta tres personas en Personas y te aviso cuando su día se vea difícil.",
        "deciding": "Bien. Cuéntame la decisión en una línea y la fecha límite, si la hay. La reviso con tus ventanas y te digo qué tan segura es.",
        "stuck": "Antes de responder: ¿es una decisión que estás pensando, una preocupación que te pesa, o el momento para algo que ya sabes que harás?",
        "worry": "Entonces iré con calma. ¿Es sobre dinero, trabajo, una persona o tu salud? No pronostico lo que siente otra persona, pero sí puedo decirte qué te toca a ti.",
        "timing": "Entonces cuéntame qué planeas y busco el tramo. O empecemos por el panorama general.",
        "vague": "Quiero acertar en lugar de adivinar. ¿Es sobre una decisión, una preocupación o el momento?",
        "reframed": "No puedo decirte lo que siente o hará otra persona, y no voy a fingir que puedo. Esta es tu parte.",
        "ask_fail": "No pude leer eso ahora. Inténtalo de nuevo en un momento.",
        "starters_lead": "No hace falta escribir. Elige por dónde empezar.",
        "a_decision": "Una decisión", "a_worry": "Una preocupación", "just_timing": "Solo el momento", "retry": "Reintentar",
        "src_day": "tu lectura de hoy, calculada con tu carta", "src_topic": "tu lectura de {t}, calculada con tu carta",
        "src_year": "las ventanas de tu año de cumpleaños, calculadas", "src_month": "tus próximos 30 días, calculados",
        "src_phase": "tu etapa y cambio actuales, fechas de tu carta", "src_loop": "tu ciclo diario",
        "src_people": "la lectura del día de las personas que marcaste", "src_ask": "tu pregunta, respondida con tu carta",
        "src_windows": "tus ventanas, calculadas",
    },
}


def t(lg: str, key: str, **kw) -> str:
    s = _T[lg_of(lg)][key]
    return s.format(**kw) if kw else s


def lg_of(lg) -> str:
    return lg if lg in LANGS else "en"


def _label(lg: str, topic: str) -> str:
    return (TC.LABEL.get(lg) or TC.LABEL["en"]).get(topic, topic)


def _lower(s: str) -> str:
    return (s or "").lower()


def _dlabel(lg: str, iso: Any, today: Optional[date] = None) -> str:
    try:
        d = date.fromisoformat(str(iso)[:10])
        return TC.day_label(d, lg)
    except Exception:
        return str(iso or "")


# ───────────────────────────── cards ─────────────────────────────
def card(type_: str, data: dict, source: str, route: Optional[str] = None, title: Optional[str] = None) -> dict:
    return {"type": type_, "title": title, "data": data, "source": source, "link": {"route": route} if route else None}


def move_card(decision: Optional[dict], lg: str) -> Optional[dict]:
    """Today's move from the day's decision block (already plain words, en/es). None when there is no block."""
    if not isinstance(decision, dict) or not (decision.get("move") or decision.get("prediction")):
        return None
    w = decision.get("window") or {}
    return card("move", {"prediction": decision.get("prediction"), "move": decision.get("move"), "holds": decision.get("holds"),
                         "breaks": decision.get("breaks"), "window": {"best": w.get("best"), "avoid": w.get("avoid"),
                                                                       "best_start": w.get("best_start"), "best_end": w.get("best_end")}},
                t(lg, "src_day"), "/full/day")


def topic_card(read: Optional[dict], lg: str) -> Optional[dict]:
    if not isinstance(read, dict) or not read.get("topic"):
        return None
    return card("topic", {k: read.get(k) for k in ("topic", "label", "scale", "period", "tone", "claim", "best_window", "watch_window",
                                                    "your_move", "confidence_note", "why")},
                t(lg, "src_topic", t=_lower(read.get("label") or "")), f"/ask/topic/{read.get('topic')}")


def span_card(kind: str, reads: List[dict], lg: str) -> Optional[dict]:
    """kind: "year" | "month": one line per main topic from the topic reads at that scale."""
    rows = [{"topic": r.get("topic"), "label": r.get("label"), "tone": r.get("tone"), "claim": r.get("claim"),
             "best_window": r.get("best_window"), "watch_window": r.get("watch_window"), "your_move": r.get("your_move")}
            for r in (reads or []) if isinstance(r, dict) and r.get("topic")]
    if not rows:
        return None
    period = next((r.get("period") for r in reads if isinstance(r, dict) and r.get("period")), None)
    return card(kind, {"period": period, "topics": rows}, t(lg, "src_" + kind), f"/timeline?view={kind}")


def phase_card(phase: Optional[dict], lg: str) -> Optional[dict]:
    if not isinstance(phase, dict) or not phase.get("available"):
        return None
    return card("phase", {k: phase.get(k) for k in ("chapter", "shift", "how_they_combine", "life_areas", "upcoming_shifts", "turning_points")},
                t(lg, "src_phase"), "/timeline?view=phase")


def loop_card(loop: Optional[dict], lg: str) -> Optional[dict]:
    if not isinstance(loop, dict):
        return None
    st = loop.get("streak") or {}
    return card("loop", {"steps": loop.get("steps"), "complete": loop.get("complete"), "practice": loop.get("practice"),
                         "question": loop.get("question"), "streak": {k: st.get(k) for k in ("streak", "longest_streak", "freeze_available", "next_milestone")}},
                t(lg, "src_loop"), "/streak")


def heads_up_card(person: Optional[dict], lg: str) -> Optional[dict]:
    if not person:
        return None
    return card("heads_up", {"name": person.get("name"), "connection_chart_id": person.get("connection_chart_id"),
                             "text": t(lg, "heads_up", p=person.get("name") or "") + " " + t(lg, "heads_nudge", p=person.get("name") or "")},
                t(lg, "src_people"), "/circle")


def ask_card(ask: Optional[dict], lg: str) -> Optional[dict]:
    if not isinstance(ask, dict) or ask.get("error"):
        return None
    return card("ask_answer", ask, t(lg, "src_ask"), "/ask")


# ───────────────────────────── the opening message ─────────────────────────────
def starters(lg: str) -> dict:
    lg = lg_of(lg)
    en = lg == "en"
    return {"lead": t(lg, "starters_lead"),
            "primary": {"label": "Just tell me my day" if en else "Dime mi día", "send": "Just tell me my day"},
            "items": [
                {"label": "I'm deciding something" if en else "Estoy decidiendo algo", "sub": "Timing for a choice" if en else "El momento para una decisión", "send": "I'm deciding something"},
                {"label": "What's coming for me" if en else "Lo que viene para mí", "sub": "Your year and chapter" if en else "Tu año y tu etapa", "send": "What's coming for me?"},
                {"label": "Someone in my life" if en else "Alguien en mi vida", "sub": "Your people" if en else "Tus personas", "send": "Someone in my life"},
                {"label": "I just feel stuck" if en else "Me siento estancado", "sub": "Talk it through" if en else "Hablarlo", "send": "I just feel stuck"}]}


def _qr(lg: str, *keys: str) -> List[dict]:
    return [{"label": t(lg, k), "send": _T["en"][k]} for k in keys]


def _first_sentence(s: str) -> str:
    s = (s or "").strip()
    m = re.match(r"(.+?[.!?])(\s|$)", s)
    return m.group(1) if m else s


def _facts(windows: Optional[dict], heads_up: Optional[dict], lg: str) -> List[dict]:
    """Up to two facts worth opening with, most urgent first. Each: {kind, text, nudge}."""
    out: List[dict] = []
    feed = windows if isinstance(windows, dict) else {}
    now = [w for w in (feed.get("now") or []) if isinstance(w, dict)]
    closing = next((w for w in now if w.get("kind") == "open" and w.get("days_left") == 0), None)
    if closing:
        lab = _label(lg, closing.get("topic"))
        out.append({"kind": "closing", "text": t(lg, "closing", t=_lower(lab)),
                    "nudge": t(lg, "closing_nudge", t=_lower(lab)) + " " + t(lg, "walk")})
    if heads_up:
        out.append({"kind": "heads_up", "text": t(lg, "heads_up", p=heads_up.get("name") or ""),
                    "nudge": t(lg, "heads_nudge", p=heads_up.get("name") or "") + " " + t(lg, "one_thing")})
    care_now = next((w for w in now if w.get("kind") == "care"), None)
    if care_now:
        out.append({"kind": "care_now", "text": t(lg, "care_now", t=_lower(_label(lg, care_now.get("topic"))), e=_dlabel(lg, care_now.get("end"))),
                    "nudge": t(lg, "one_thing")})
    open_soon = next((w for w in now if w.get("kind") == "open" and isinstance(w.get("days_left"), int) and 0 < w["days_left"] <= 3), None)
    if open_soon:
        out.append({"kind": "open_days", "text": t(lg, "open_days", t=_lower(_label(lg, open_soon.get("topic"))), d=open_soon["days_left"]),
                    "nudge": ((open_soon.get("move") or "") + " " + t(lg, "walk")).strip()})
    return out[:2]


def opening(ctx: dict, language: str = "en") -> dict:
    """ctx: {name, hour (local 0-23), decision, windows, heads_up}. Returns the reply contract (intent "open")."""
    lg = lg_of(lang_of(language))
    name = (ctx.get("name") or "").strip().split(" ")[0] or ("amigo" if lg == "es" else "there")
    hour = ctx.get("hour")
    key = "morning" if isinstance(hour, int) and hour < 12 else "afternoon" if isinstance(hour, int) and hour < 18 else "evening" if isinstance(hour, int) else "hello"
    msgs = [{"role": "antar", "text": t(lg, key, n=name)}]
    facts = _facts(ctx.get("windows"), ctx.get("heads_up"), lg)
    dec = ctx.get("decision") if isinstance(ctx.get("decision"), dict) else {}
    if len(facts) == 2:
        msgs.append({"role": "antar", "text": t(lg, "two", a=facts[0]["text"], b=facts[1]["text"])})
    elif len(facts) == 1:
        msgs.append({"role": "antar", "text": t(lg, "one", a=facts[0]["text"])})
    elif dec.get("prediction"):
        msgs.append({"role": "antar", "text": dec["prediction"]})
    msgs.append({"role": "antar", "text": facts[0]["nudge"] if facts else t(lg, "one_thing")})
    qr = _qr(lg, "q_walk", "q_move", "q_year", "q_else") if facts and facts[0]["kind"] in ("closing", "open_days") else _qr(lg, "q_move", "q_year", "q_chapter", "q_else")
    return {"intent": "open", "messages": msgs, "cards": [], "quick_replies": qr, "starters": starters(lg)}


# ───────────────────────────── the reply router ─────────────────────────────
_RX = [
    ("starters", re.compile(r"not sure what to ask|what can you do|what can i ask|\bhelp\b|^something else$|^otra cosa$|no sé qué preguntar|ayuda", re.I)),
    ("deciding", re.compile(r"^(i'?m deciding something|a decision|estoy decidiendo algo|una decisión)\.?$", re.I)),
    ("worry", re.compile(r"^(a worry|una preocupación)\.?$", re.I)),
    ("timing", re.compile(r"^(just timing|solo el momento)\.?$", re.I)),
    ("stuck", re.compile(r"\b(stuck|confused|lost|don'?t know what to do)\b|estancad|confundid|no sé qué hacer", re.I)),
    ("today", re.compile(r"^(just tell me my day|dime mi día|what'?s my move today\??|what should i do tonight\??|how'?s today\??|today|hoy|yes, walk me through it|sí, vamos paso a paso)$|\bmy day\b|\btonight\b|\bmy move\b|mi jugada|mi día", re.I)),
    ("coming", re.compile(r"what'?s coming for me|lo que viene para mí", re.I)),
    ("year", re.compile(r"\b(year|birthday|next year)\b|\baño\b|cumpleaños", re.I)),
    ("chapter", re.compile(r"\b(chapter|phase|dasha|long.?term|period)\b|etapa|capítulo", re.I)),
    ("month", re.compile(r"\bmonth\b|\bmes\b", re.I)),
    ("loop", re.compile(r"\b(my loop|streak|mantra|where am i today|my practice)\b|mi racha|cómo voy hoy", re.I)),
    ("people", re.compile(r"someone in my life|\bpeople\b|who should i check|my (partner|cofounder|co-founder|advisor)|alguien en mi vida|mis personas", re.I)),
]
_TOPIC_RX = [
    ("health", re.compile(r"\b(health|sleep|energy|body)\b|salud|sueño|energía", re.I)),
    ("money", re.compile(r"\b(money|income|cash|savings|salary|pricing)\b|dinero|ingresos|ahorros", re.I)),
    ("business", re.compile(r"\b(business|company|startup|venture)\b|negocio|empresa", re.I)),
    ("career", re.compile(r"\b(career|job|work|promotion)\b|carrera|trabajo|empleo", re.I)),
    ("love", re.compile(r"\b(love|relationship|marriage|romance)\b|amor|relación|pareja", re.I)),
    ("peace", re.compile(r"\b(peace|calm|stress|anxiety)\b|paz|calma|estrés", re.I)),
    ("family", re.compile(r"\b(family|kids|children|parents)\b|familia|hijos|padres", re.I)),
]
# a question about a decision, a person or an event goes to Ask (the real engines) even if it mentions a topic word
_ASKY = re.compile(r"\?|\bshould i\b|\bwhen (is|should|will|do)\b|\bwill (my|i|he|she)\b|\bcan i\b|\bis (it|now|this)\b|\bdo i\b|¿|\bdebería\b|\bcuándo\b|\bpuedo\b", re.I)


def classify(text: str) -> tuple:
    """(intent, arg). Intents: starters deciding worry timing stuck today coming year chapter month loop people topic ask."""
    s = (text or "").strip()
    if not s:
        return ("starters", None)
    for name, rx in _RX:
        if rx.search(s) and not (_ASKY.search(s) and name in ("year", "month", "chapter", "people") and len(s.split()) > 6):
            return (name, None)
    topic_hit = next((k for k, rx in _TOPIC_RX if rx.search(s)), None)
    # a short "how's my money?" reads a topic; a real question ("should I raise my prices?") goes to Ask
    if topic_hit and len(s.split()) <= 6 and not re.search(r"\bshould i\b|\bwhen\b|\bwill\b|¿cuándo|\bdebería", s, re.I):
        return ("topic", topic_hit)
    return ("ask", None)


def reply(intent: str, arg: Optional[str], eng: dict, language: str = "en") -> dict:
    """Build the reply for a routed intent. `eng` holds the already-fetched engine outputs this intent needs:
    decision, topic_read, reads (list), phase, loop, heads_up (dict|None), heads_set (bool), ask, windows."""
    lg = lg_of(lang_of(language))
    cards: List[dict] = []
    msgs: List[dict] = []
    qr: List[dict] = []

    def say(x):
        msgs.append({"role": "antar", "text": x})

    if intent == "starters":
        say(t(lg, "starters_lead")); out = {"intent": intent, "messages": msgs, "cards": [], "quick_replies": [], "starters": starters(lg)}
        return out
    if intent == "deciding":
        say(t(lg, "deciding")); qr = [{"label": x, "send": x} for x in (["Raise my prices", "Leave my job", "Start something new"] if lg == "en" else ["Subir mis precios", "Dejar mi trabajo", "Empezar algo nuevo"])]
    elif intent == "worry":
        say(t(lg, "worry")); qr = [{"label": x, "send": x} for x in (["Money", "Work", "A person", "My health"] if lg == "en" else ["Dinero", "Trabajo", "Una persona", "Mi salud"])]
    elif intent == "timing":
        say(t(lg, "timing")); qr = _qr(lg, "q_year", "q_month")
    elif intent == "stuck":
        say(t(lg, "stuck")); qr = _qr(lg, "a_decision", "a_worry", "just_timing")
    elif intent == "today":
        c = move_card(eng.get("decision"), lg)
        if c:
            say(((eng.get("decision") or {}).get("prediction")) or t(lg, "today_lead")); cards.append(c)
            qr = _qr(lg, "q_year", "q_chapter", "q_loop")
        else:
            say(t(lg, "move_missing")); qr = _qr(lg, "retry")
    elif intent in ("year", "month"):
        c = span_card(intent, eng.get("reads") or [], lg)
        if c:
            say(t(lg, intent + "_lead")); cards.append(c); qr = _qr(lg, "q_chapter", "q_move") if intent == "year" else _qr(lg, "q_move", "q_year")
        else:
            say(t(lg, "move_missing")); qr = _qr(lg, "retry")
    elif intent == "coming":
        yc = span_card("year", eng.get("reads") or [], lg); pc = phase_card(eng.get("phase"), lg)
        if yc or pc:
            say(t(lg, "year_lead")); cards += [c for c in (yc, pc) if c]; qr = _qr(lg, "q_move", "q_month")
        else:
            say(t(lg, "move_missing")); qr = _qr(lg, "retry")
    elif intent == "chapter":
        c = phase_card(eng.get("phase"), lg)
        if c:
            say(t(lg, "chapter_lead")); cards.append(c); qr = _qr(lg, "q_year", "q_move")
        else:
            say(t(lg, "chapter_missing")); qr = _qr(lg, "q_year")
    elif intent == "loop":
        c = loop_card(eng.get("loop"), lg)
        if c:
            say(t(lg, "loop_lead")); cards.append(c)
        else:
            say(t(lg, "move_missing")); qr = _qr(lg, "retry")
    elif intent == "people":
        c = heads_up_card(eng.get("heads_up"), lg)
        if c:
            say(t(lg, "heads_lead")); cards.append(c)
        else:
            say(t(lg, "heads_none") if eng.get("heads_set") else t(lg, "heads_unset"))
        qr = _qr(lg, "q_move", "q_year")
    elif intent == "topic":
        c = topic_card(eng.get("topic_read"), lg)
        if c:
            say(c["data"].get("claim") or t(lg, "topic_lead", t=_lower(c["data"].get("label") or ""))); cards.append(c); qr = _qr(lg, "q_year", "q_move")
        else:
            say(t(lg, "move_missing")); qr = _qr(lg, "retry")
    elif intent == "ask":
        c = ask_card(eng.get("ask"), lg)
        if c:
            if (eng.get("ask") or {}).get("reframed"):
                say(t(lg, "reframed"))
            cards.append(c); qr = _qr(lg, "q_year", "q_move")
        else:
            say(t(lg, "ask_fail")); qr = _qr(lg, "retry")
    else:
        say(t(lg, "vague")); qr = _qr(lg, "a_decision", "a_worry", "just_timing")
        intent = "vague"
    return {"intent": intent, "messages": msgs, "cards": cards, "quick_replies": qr}


# ───────────────────────────── rollout flag ─────────────────────────────
def enabled(chart_id: str, pct: Any, allow: Any) -> bool:
    """Stable per-chart rollout: in the allow list, or its hash bucket (0-99) is below pct."""
    cid = str(chart_id or "").strip().lower()
    allowed = {x.strip().lower() for x in str(allow or "").split(",") if x.strip()}
    if cid in allowed:
        return True
    try:
        p = max(0, min(100, int(float(str(pct or "0")))))
    except Exception:
        p = 0
    if p <= 0:
        return False
    bucket = int(hashlib.sha1(("thread-home|" + cid).encode()).hexdigest()[:8], 16) % 100
    return bucket < p
