"""Questions for you: up to three timing questions worth asking right now, taken from the
Windows feed (the topic engine's own scans) and the person's recent Ask history.

Order: (1) a window open now that closes soonest, (2) the next window opening within ~90 days,
(3) a care window within ~45 days, then a follow-up to a recent Ask question, then an evergreen
timing question. One question per topic, never one already in the last 20 Ask rows. Every
question is about TIMING ("Is November a good time to ...?"), never about an outcome. Each text
is a standalone question the front end can send straight to Ask. Deterministic, no LLM; the
caller fails open to evergreen questions. Hindi falls back to English."""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import date
from typing import Dict, List, Optional

from antar_engine import topic_copy as C

logger = logging.getLogger(__name__)

KINDS = ("open_now", "opening_soon", "care", "followup")
SOON_DAYS = 90
CARE_DAYS = 45
HISTORY_ROWS = 20
FOLLOWUP_DAYS = 14
MAX_LIMIT = 5
TOPIC_ORDER = ("money", "career", "love", "health", "business", "peace", "family")

# ── hand-written phrase tables ───────────────────────────────────────────────
# DO[lang][topic] = (phrase for "this week", phrase for "in <month>"), fitted to the frames below.
DO: Dict[str, Dict[str, tuple]] = {
    "en": {
        "money": ("make the money decision I have been putting off", "increase my prices"),
        "career": ("make my ask at work", "apply for a new role"),
        "love": ("have the honest talk I have been putting off", "take the next step in a close relationship"),
        "health": ("start a new health routine", "book the check-up I have been delaying"),
        "business": ("start the co-founder talk", "launch something new in my business"),
        "peace": ("slow down and reset", "start a daily quiet practice"),
        "family": ("have the family conversation I have been avoiding", "plan something with my family"),
    },
    "es": {
        "money": ("tomar la decisión de dinero que he estado posponiendo", "subir mis precios"),
        "career": ("pedir lo que quiero en el trabajo", "postularme a un nuevo puesto"),
        "love": ("tener la conversación sincera que he estado posponiendo",
                 "dar el siguiente paso en una relación cercana"),
        "health": ("empezar una nueva rutina de salud", "reservar el chequeo que he estado aplazando"),
        "business": ("iniciar la conversación sobre la alianza", "lanzar algo nuevo en mi negocio"),
        "peace": ("bajar el ritmo y reiniciar", "empezar una práctica diaria de calma"),
        "family": ("tener la conversación familiar que he estado evitando", "planear algo con mi familia"),
    },
    "pt": {
        "money": ("tomar a decisão de dinheiro que venho adiando", "aumentar os meus preços"),
        "career": ("pedir o que quero no trabalho", "me candidatar a uma nova vaga"),
        "love": ("ter a conversa sincera que venho adiando", "dar o próximo passo numa relação próxima"),
        "health": ("começar uma nova rotina de saúde", "marcar o check-up que venho adiando"),
        "business": ("iniciar a conversa sobre a parceria", "lançar algo novo no meu negócio"),
        "peace": ("desacelerar e recomeçar", "começar uma prática diária de calma"),
        "family": ("ter a conversa em família que venho evitando", "planejar algo com a minha família"),
    },
    "hinglish": {
        "money": ("paise ka woh faisla lene jo main taalta raha hoon", "apne daam badhane"),
        "career": ("kaam par apni baat rakhne", "nayi job ke liye apply karne"),
        "love": ("woh sachchi baat karne jo main taalta raha hoon", "rishte mein agla kadam uthane"),
        "health": ("sehat ki nayi routine shuru karne", "woh check-up book karne jo main taalta raha hoon"),
        "business": ("apne co-founder se baat shuru karne", "kaarobaar mein kuch naya shuru karne"),
        "peace": ("thoda ruk kar khud ko reset karne", "roz ki shaant practice shuru karne"),
        "family": ("parivaar se woh baat karne jo main taalta raha hoon", "parivaar ke saath kuch plan karne"),
    },
}

# the frames: {do} and {month} (full month name) filled in
NOW_FRAME = {"en": "Is this a good week to {do}?",
             "es": "¿Es esta una buena semana para {do}?",
             "pt": "Esta é uma boa semana para {do}?",
             "hinglish": "Kya yeh hafta {do} ke liye accha hai?"}
SOON_FRAME = {"en": "Is {month} a good time to {do}?",
              "es": "¿Es {month} un buen momento para {do}?",
              "pt": "{month} é um bom momento para {do}?",
              "hinglish": "Kya {month} {do} ke liye accha samay hai?"}

CARE: Dict[str, Dict[str, str]] = {
    "en": {"money": "Why does my chart ask for care with money until {date}?",
           "career": "Why does my chart ask for care at work until {date}?",
           "love": "Why does my chart ask for care in my relationships until {date}?",
           "health": "Why does my chart ask for care with my health until {date}?",
           "business": "Why does my chart ask for care in my business until {date}?",
           "peace": "Why does my chart ask for care with my peace of mind until {date}?",
           "family": "Why does my chart ask for care with my family until {date}?"},
    "es": {"money": "¿Por qué mi carta pide cuidado con el dinero hasta el {date}?",
           "career": "¿Por qué mi carta pide cuidado en el trabajo hasta el {date}?",
           "love": "¿Por qué mi carta pide cuidado en mis relaciones hasta el {date}?",
           "health": "¿Por qué mi carta pide cuidado con mi salud hasta el {date}?",
           "business": "¿Por qué mi carta pide cuidado en mi negocio hasta el {date}?",
           "peace": "¿Por qué mi carta pide cuidado con mi paz interior hasta el {date}?",
           "family": "¿Por qué mi carta pide cuidado con mi familia hasta el {date}?"},
    "pt": {"money": "Por que meu mapa pede cuidado com o dinheiro até {date}?",
           "career": "Por que meu mapa pede cuidado no trabalho até {date}?",
           "love": "Por que meu mapa pede cuidado nas minhas relações até {date}?",
           "health": "Por que meu mapa pede cuidado com minha saúde até {date}?",
           "business": "Por que meu mapa pede cuidado no meu negócio até {date}?",
           "peace": "Por que meu mapa pede cuidado com minha paz interior até {date}?",
           "family": "Por que meu mapa pede cuidado com minha família até {date}?"},
    "hinglish": {"money": "{date} tak mera chart paise mein dhyaan kyun maangta hai?",
                 "career": "{date} tak mera chart kaam mein dhyaan kyun maangta hai?",
                 "love": "{date} tak mera chart rishton mein dhyaan kyun maangta hai?",
                 "health": "{date} tak mera chart sehat mein dhyaan kyun maangta hai?",
                 "business": "{date} tak mera chart kaarobaar mein dhyaan kyun maangta hai?",
                 "peace": "{date} tak mera chart mere sukoon mein dhyaan kyun maangta hai?",
                 "family": "{date} tak mera chart parivaar mein dhyaan kyun maangta hai?"},
}

EVERGREEN: Dict[str, Dict[str, str]] = {
    "en": {"money": "When is my next good window for a money decision?",
           "career": "When is a good time to make a move at work?",
           "love": "When is a good time to have an important talk in my relationship?",
           "health": "When is a good time to start a new health habit?",
           "business": "When is a good time to take the next step in my business?",
           "peace": "When is a good time to slow down and rest?",
           "family": "When is a good time to talk with my family about something important?"},
    "es": {"money": "¿Cuándo es mi próxima buena ventana para una decisión de dinero?",
           "career": "¿Cuándo es un buen momento para dar un paso en el trabajo?",
           "love": "¿Cuándo es un buen momento para una conversación importante en mi relación?",
           "health": "¿Cuándo es un buen momento para empezar un nuevo hábito de salud?",
           "business": "¿Cuándo es un buen momento para dar el siguiente paso en mi negocio?",
           "peace": "¿Cuándo es un buen momento para bajar el ritmo y descansar?",
           "family": "¿Cuándo es un buen momento para hablar con mi familia de algo importante?"},
    "pt": {"money": "Quando é a minha próxima boa janela para uma decisão de dinheiro?",
           "career": "Quando é um bom momento para dar um passo no trabalho?",
           "love": "Quando é um bom momento para uma conversa importante na minha relação?",
           "health": "Quando é um bom momento para começar um novo hábito de saúde?",
           "business": "Quando é um bom momento para dar o próximo passo no meu negócio?",
           "peace": "Quando é um bom momento para desacelerar e descansar?",
           "family": "Quando é um bom momento para falar com a minha família sobre algo importante?"},
    "hinglish": {"money": "Paise ke faisle ke liye meri agli achhi window kab hai?",
                 "career": "Kaam mein agla kadam uthane ka achha samay kab hai?",
                 "love": "Rishte mein zaroori baat karne ka achha samay kab hai?",
                 "health": "Sehat ki nayi aadat shuru karne ka achha samay kab hai?",
                 "business": "Kaarobaar mein agla kadam uthane ka achha samay kab hai?",
                 "peace": "Thoda ruk kar aaraam karne ka achha samay kab hai?",
                 "family": "Parivaar se zaroori baat karne ka achha samay kab hai?"},
}

# the short "why this now" lines; {area} is the topic label in lower case
REASON: Dict[str, Dict[str, str]] = {
    "en": {"open_now": "Your {area} window is open until {end}.",
           "opening_soon": "A {area} window opens {start}.",
           "care": "A careful stretch for {area}: {start} – {end}.",
           "followup": "Following up on your question about {area}.",
           "evergreen": "Timing is worth checking for {area}."},
    "es": {"open_now": "Tu ventana de {area} está abierta hasta el {end}.",
           "opening_soon": "Una ventana de {area} se abre el {start}.",
           "care": "Un tramo de cuidado para {area}: {start} – {end}.",
           "followup": "Sigue a tu pregunta sobre {area}.",
           "evergreen": "Vale la pena mirar el momento en {area}."},
    "pt": {"open_now": "Sua janela de {area} está aberta até {end}.",
           "opening_soon": "Uma janela de {area} abre em {start}.",
           "care": "Um período de cuidado para {area}: {start} – {end}.",
           "followup": "Continua a sua pergunta sobre {area}.",
           "evergreen": "Vale a pena olhar o momento em {area}."},
    "hinglish": {"open_now": "Aapki {area} ki window {end} tak khuli hai.",
                 "opening_soon": "{area} ki ek window {start} ko khulti hai.",
                 "care": "{area} ke liye dhyaan ka daur: {start} – {end}.",
                 "followup": "{area} ke baare mein aapke sawaal ka agla kadam.",
                 "evergreen": "{area} mein samay dekhna kaam ka hai."},
}

# bucket names the follow-up engine uses, per topic
_FOLLOWUP_BUCKET = {"money": "money", "career": "career", "love": "love", "health": "health",
                    "business": "business", "peace": "spiritual", "family": "family"}

# a timing question never asks about an outcome (also enforced in tests)
OUTCOME_WORDS = re.compile(
    r"(?i)\b(will i|will my|am i going to|going to get|win|succeed|success|marry|married|"
    r"guarantee\w*|promise\w*|ganhar\w*|vencer|casar\w*|garantia|ganar\w*|casarme|casarse|"
    r"jeetoon\w*|jeet\w*|shaadi)\b")


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().casefold())


def _area(lang: str, topic: str) -> str:
    return C.LABEL[lang][topic].lower()


def _fmt(d: date, lang: str, today: date) -> str:
    return C.day_label(d, lang) if d.year == today.year else C.day_label_y(d, lang)


def _qid(chart_id: str, today: date, topic: str, kind: str) -> str:
    h = hashlib.sha1(f"{chart_id}|{today.isoformat()}|{topic}|{kind}".encode()).hexdigest()
    return "q_" + h[:12]


def _mk(chart_id, today, topic, kind, text, reason) -> dict:
    return {"id": _qid(chart_id, today, topic, kind), "topic": topic, "text": text,
            "reason": reason, "kind": kind}


# ── candidates ───────────────────────────────────────────────────────────────
def window_candidates(feed: Optional[dict], chart_id: str, today: date, lang: str) -> Dict[str, List[dict]]:
    """{"open_now": [...], "opening_soon": [...], "care": [...]} from a Windows feed, best first."""
    out = {"open_now": [], "opening_soon": [], "care": []}
    if not isinstance(feed, dict):
        return out
    try:
        for w in feed.get("now") or []:                    # already ordered soonest-ending first
            t = w.get("topic")
            if t not in DO[lang]:
                continue
            e = date.fromisoformat(w["end"])
            if w.get("kind") == "open":
                text = NOW_FRAME[lang].format(do=DO[lang][t][0])
                why = REASON[lang]["open_now"].format(area=_area(lang, t), end=_fmt(e, lang, today))
                out["open_now"].append(_mk(chart_id, today, t, "open_now", text, why))
            elif w.get("kind") == "care":
                out["care"].append(_care(chart_id, today, lang, t, date.fromisoformat(w["start"]), e,
                                         sort=(0, e.isoformat())))
        for w in sorted(feed.get("next") or [], key=lambda x: x.get("start") or ""):
            t = w.get("topic")
            if t not in DO[lang] or w.get("kind") != "open":
                continue
            s = date.fromisoformat(w["start"])
            if 0 < (s - today).days <= SOON_DAYS:
                text = SOON_FRAME[lang].format(month=C.pick(C.FULL_MONTHS, lang)[s.month - 1],
                                               do=DO[lang][t][1])
                why = REASON[lang]["opening_soon"].format(area=_area(lang, t), start=_fmt(s, lang, today))
                out["opening_soon"].append(_mk(chart_id, today, t, "opening_soon", text, why))
        for w in sorted(feed.get("care") or [], key=lambda x: x.get("start") or ""):
            t = w.get("topic")
            if t not in DO[lang]:
                continue
            s, e = date.fromisoformat(w["start"]), date.fromisoformat(w["end"])
            if 0 < (s - today).days <= CARE_DAYS:
                out["care"].append(_care(chart_id, today, lang, t, s, e, sort=(1, s.isoformat())))
        out["care"] = [c for _k, c in sorted(((c.pop("_sort"), c) for c in out["care"]), key=lambda x: x[0])]
    except Exception:
        logger.exception("[suggested-questions] window candidates skipped")
        return {"open_now": [], "opening_soon": [], "care": []}
    return out


def _care(chart_id, today, lang, topic, s, e, sort) -> dict:
    q = _mk(chart_id, today, topic, "care", CARE[lang][topic].format(date=_fmt(e, lang, today)),
            REASON[lang]["care"].format(area=_area(lang, topic), start=_fmt(s, lang, today),
                                        end=_fmt(e, lang, today)))
    q["_sort"] = sort
    return q


def _recent(row: dict, today: date) -> bool:
    """True when the Ask row is dated and at most FOLLOWUP_DAYS old (undated rows do not count)."""
    try:
        d = date.fromisoformat(str(row.get("created_at") or "")[:10])
    except ValueError:
        return False
    return 0 <= (today - d).days <= FOLLOWUP_DAYS


def followup_candidates(rows: List[dict], chart_id: str, today: date, lang: str) -> List[dict]:
    """One timing ("when") follow-up per Ask question from the last FOLLOWUP_DAYS days that has a
    known topic, newest first, from the existing follow-up engine (no new classifier)."""
    out = []
    try:
        from antar_engine import ask_followups as F
        for r in rows or []:
            q = str(r.get("question") or "").strip()
            t = C.topic_for_concern(r.get("domain")) or C.topic_for_question(q)
            if not q or t not in _FOLLOWUP_BUCKET or not _recent(r, today):
                continue
            # the follow-up engine's own timing ("when") question for that topic; read from its
            # table because pick() drops the lane the reader just asked about
            wq = (F._Q[F._lang(lang)].get(_FOLLOWUP_BUCKET[t]) or {}).get("when")
            if wq and F._norm(wq) != F._norm(q) and not OUTCOME_WORDS.search(wq) \
                    and C.topic_for_question(wq) in (t, None):   # timing, never an outcome; stays on its topic
                out.append(_mk(chart_id, today, t, "followup", wq,
                               REASON[lang]["followup"].format(area=_area(lang, t))))
    except Exception:
        logger.exception("[suggested-questions] followups skipped")
    return out


def evergreen_candidates(chart_id: str, today: date, lang: str, order=TOPIC_ORDER) -> List[dict]:
    return [_mk(chart_id, today, t, "followup", EVERGREEN[lang][t],
                REASON[lang]["evergreen"].format(area=_area(lang, t))) for t in order]


# ── selection ────────────────────────────────────────────────────────────────
def select(cands: Dict[str, List[dict]], follow: List[dict], evergreen: List[dict],
           history_texts, limit: int = 3) -> List[dict]:
    """First valid of each window category in order, then fill from follow-ups, evergreen, then
    the remaining window candidates. One per topic; nothing already in the Ask history."""
    seen = {_norm(t) for t in history_texts or []}
    used, picked = set(), []

    def take(c) -> bool:
        if c["topic"] in used or _norm(c["text"]) in seen or len(picked) >= limit:
            return False
        used.add(c["topic"])
        picked.append({k: v for k, v in c.items() if not k.startswith("_")})
        return True

    for kind in ("open_now", "opening_soon", "care"):
        for c in cands.get(kind, []):
            if take(c):
                break
    for pool in (follow, evergreen, cands.get("open_now", []), cands.get("opening_soon", []),
                 cands.get("care", [])):
        for c in pool:
            take(c)
    return picked


def build(feed: Optional[dict], history_rows: List[dict], chart_id: str, today: date,
          language: str = "en", limit: int = 3, cands: Optional[Dict[str, List[dict]]] = None) -> dict:
    """The response body. `feed` None (engine trouble) still gives evergreen questions; `cands`
    is the already-built window part (the caller caches it per chart, language and day)."""
    lang = C.serve_language(language)
    limit = max(1, min(MAX_LIMIT, int(limit or 3)))
    rows = list(history_rows or [])[:HISTORY_ROWS]
    qs = select(cands if cands is not None else window_candidates(feed, chart_id, today, lang),
                followup_candidates(rows, chart_id, today, lang),
                evergreen_candidates(chart_id, today, lang),
                [r.get("question") for r in rows], limit)
    return {"questions": qs, "count": len(qs)}
