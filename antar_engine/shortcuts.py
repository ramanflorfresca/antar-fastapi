"""[shortcuts 2026-10-13] The "Ask about" row on Home: life topics as shortcuts into the Ask thread, each with a live dot
(green = a window is open now, saffron = a care stretch is here or close), one plain status line from the Windows feed (the one
timing source), the opener Antar posts, and starter questions. Life moves (job change, moving home) and Legal are not calendar
windows; their status lines say so. Legal is deliberately limited to what an astrologer can honestly say.
Pure functions; the endpoint supplies the Windows feed. Never raises on missing data."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

DEFAULT = ("money", "love", "legal", "career", "health")
ALL = ("money", "love", "legal", "career", "health", "job", "home", "business")
_FEED = {"money": "money", "love": "love", "career": "career", "health": "health", "business": "business"}
_MON = {"en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        "es": ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")}

T = {
    "en": {
        "label": {"money": "Money", "love": "Love", "legal": "Legal and contracts", "career": "Career", "health": "Health", "job": "Job change", "home": "Moving home", "business": "Business"},
        "glyph": {"money": "$", "love": "L", "legal": "§", "career": "C", "health": "H", "job": "J", "home": "M", "business": "B"},
        "open": {"money": "What would you like to work out about money?", "love": "What is going on with the people closest to you?",
                 "legal": "What are you dealing with: a contract to sign, a dispute, or something else?", "career": "What is on your mind at work?",
                 "health": "What would you like to look after?", "job": "Thinking about a change of work? Tell me where you are.",
                 "home": "Thinking about moving? Tell me what is pulling you.", "business": "What is happening in the business?"},
        "q": {"money": ["What should I do about money this month?", "When does my strongest money window open?", "Is this a good time to ask for what I am owed?", "How do I protect my savings through my next care stretch?"],
              "love": ["What should I do about my relationship this month?", "Is this a good week for a serious conversation?", "How do I handle a tense conversation today?"],
              "legal": ["Is this a good week to sign a contract?", "When should I hold off on signing anything binding?", "How do I prepare before a difficult meeting?", "What should I double check before I commit?"],
              "career": ["What should I do at work this month?", "When is the best time to ask for more responsibility?", "Should I speak up or wait this week?"],
              "health": ["What should I look after this month?", "How do I get through my next care stretch?", "What routine should I build now?"],
              "job": ["When is the best time for me to change jobs?", "Should I stay or go this year?", "What should I prepare before I change jobs?"],
              "home": ["When is the best time for me to move?", "What should I check before I commit to a move?"],
              "business": ["What should I do for the business this month?", "What should I avoid in my next care stretch?", "Is this a good time to sign something?"]},
        "legal_stat": "I can tell you when to sign, when to hold off on anything binding, and which stretches call for care. I cannot tell you who will win, and this is not legal advice.",
        "move_stat": "This is not a calendar window. Ask me and I will read your chart for it, including whether it points to a change at all.",
        "quiet": "Nothing big marked in the next 12 months.",
        "open_now": "A window is open today.", "open_until": "A window is open until {d}.", "next_open": "Your next stretch runs {a} – {b}.",
        "care": "Take care {a} – {b}.", "care_now": "A care stretch is on now, until {d}.",
    },
    "es": {
        "label": {"money": "Dinero", "love": "Amor", "legal": "Legal y contratos", "career": "Carrera", "health": "Salud", "job": "Cambio de trabajo", "home": "Mudanza", "business": "Negocio"},
        "glyph": {"money": "$", "love": "A", "legal": "§", "career": "C", "health": "S", "job": "T", "home": "M", "business": "N"},
        "open": {"money": "¿Qué quieres resolver sobre el dinero?", "love": "¿Qué pasa con las personas más cercanas?",
                 "legal": "¿Qué estás enfrentando: un contrato por firmar, una disputa u otra cosa?", "career": "¿Qué tienes en mente en el trabajo?",
                 "health": "¿De qué quieres cuidarte?", "job": "¿Pensando en cambiar de trabajo? Cuéntame dónde estás.",
                 "home": "¿Pensando en mudarte? Cuéntame qué te atrae.", "business": "¿Qué pasa en el negocio?"},
        "q": {"money": ["¿Qué debo hacer con el dinero este mes?", "¿Cuándo se abre mi mejor ventana de dinero?"],
              "love": ["¿Qué debo hacer con mi relación este mes?", "¿Es buena semana para una conversación seria?"],
              "legal": ["¿Es buena semana para firmar un contrato?", "¿Cuándo debo esperar antes de firmar algo vinculante?"],
              "career": ["¿Qué debo hacer en el trabajo este mes?", "¿Cuándo es mejor pedir más responsabilidad?"],
              "health": ["¿De qué debo cuidarme este mes?", "¿Qué rutina debo construir ahora?"],
              "job": ["¿Cuándo es el mejor momento para cambiar de trabajo?", "¿Me quedo o me voy este año?"],
              "home": ["¿Cuándo es el mejor momento para mudarme?", "¿Qué debo revisar antes de decidir?"],
              "business": ["¿Qué debo hacer por el negocio este mes?", "¿Es buen momento para firmar algo?"]},
        "legal_stat": "Puedo decirte cuándo firmar, cuándo esperar antes de algo vinculante y qué tramos piden cuidado. No puedo decirte quién ganará, y esto no es asesoría legal.",
        "move_stat": "Esto no es una ventana de calendario. Pregúntame y leeré tu carta, incluso si apunta a un cambio.",
        "quiet": "Nada grande marcado en los próximos 12 meses.",
        "open_now": "Hay una ventana abierta hoy.", "open_until": "Hay una ventana abierta hasta el {d}.", "next_open": "Tu próximo tramo va del {a} al {b}.",
        "care": "Cuidado del {a} al {b}.", "care_now": "Hay un tramo de cuidado hasta el {d}.",
    },
}


def _lang(language) -> str:
    return "es" if str(language or "en").lower().startswith("es") else "en"


def _md(d: date, lg: str, today: Optional[date] = None) -> str:
    """"Oct 31", and "Aug 1, 2027" when the date is in another year or more than about six months away, so a stretch next year is
    never read as this year's."""
    base = f"{d.day} {_MON[lg][d.month - 1]}" if lg == "es" else f"{_MON[lg][d.month - 1]} {d.day}"
    if today is not None and (d.year != today.year or (d - today).days > 183):
        return f"{base} {d.year}" if lg == "es" else f"{base}, {d.year}"
    return base


def _windows(feed: Optional[dict], topic: str, today: date) -> List[tuple]:
    out = []
    for t in (feed or {}).get("tracks") or []:
        if t.get("topic") != topic:
            continue
        for w in t.get("windows") or []:
            try:
                s, e = date.fromisoformat(str(w["start"])[:10]), date.fromisoformat(str(w["end"])[:10])
            except (KeyError, ValueError):
                continue
            if w.get("kind") in ("open", "care") and e >= today:
                out.append((s, e, w["kind"]))
    return sorted(out)


def _dot_and_stat(topic: str, feed: Optional[dict], lg: str, today: date) -> Dict[str, str]:
    t = T[lg]
    if topic == "legal":
        return {"dot": "", "stat": t["legal_stat"]}
    if topic in ("job", "home"):
        return {"dot": "", "stat": t["move_stat"]}
    ws = _windows(feed, _FEED.get(topic, topic), today)
    if not ws:
        return {"dot": "", "stat": t["quiet"]}
    parts, dot = [], ""
    op_now = next((w for w in ws if w[2] == "open" and w[0] <= today <= w[1]), None)
    ca_now = next((w for w in ws if w[2] == "care" and w[0] <= today <= w[1]), None)
    op_next = next((w for w in ws if w[2] == "open" and w[0] > today), None)
    ca_next = next((w for w in ws if w[2] == "care" and w[0] > today), None)
    if op_now:
        dot = "g"
        parts.append(t["open_now"] if op_now[1] == today else t["open_until"].format(d=_md(op_now[1], lg, today)))
    if ca_now:
        dot = "c"
        parts.append(t["care_now"].format(d=_md(ca_now[1], lg, today)))
    if op_next:
        parts.append(t["next_open"].format(a=_md(op_next[0], lg, today), b=_md(op_next[1], lg, today)))
    if ca_next:
        parts.append(t["care"].format(a=_md(ca_next[0], lg, today), b=_md(ca_next[1], lg, today)))
        if not dot and ca_next[0] <= today + timedelta(days=45):
            dot = "c"
    return {"dot": dot, "stat": " ".join(parts)}


def build(feed: Optional[dict], language: str = "en", today: Optional[date] = None) -> Dict[str, Any]:
    lg = _lang(language)
    today = today or date.today()
    t = T[lg]
    topics = []
    for k in ALL:
        ds = _dot_and_stat(k, feed, lg, today)
        topics.append({"key": k, "label": t["label"][k], "glyph": t["glyph"][k], "dot": ds["dot"], "stat": ds["stat"],
                       "opener": t["open"][k], "questions": t["q"][k]})
    return {"version": "shortcuts-1", "default": list(DEFAULT), "max": 6, "topics": topics}
