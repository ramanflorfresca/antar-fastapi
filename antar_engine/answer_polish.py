"""[audit 2026-10-04] One final deterministic pass over every Ask answer.

Built from the conversation audit (scripts/conversation_audit.py), not one screenshot:
  R2  internal prompt jargon copied into answers ("wealth engine", "your grain runs
      strongest", "swings hard", "gains dissolve") → everyday words, EN/ES/PT.
  R4  a "pick the one venture / double down on one" sentence on a chart whose money
      reading says SPREAD (contradicts the answer two turns earlier) → dropped; the
      move falls back to a role-focused step.
  ·   funding / investors / raising brought into an answer nobody asked about it →
      sentence dropped (never empties the text).
  ·   an answer that reaches the user with NO move → a concern-specific fallback move.

Every guard is sentence-level, never empties `read`, and is skipped when the person's
own words raised the topic. Mutates `payload` in place; never raises.
"""
import re

_SENT = re.compile(r"(?<=[.!?])\s+")
_FRAGMENT = re.compile(
    r"^(?:[a-zà-ÿ]|(?i:before|after|until|untouched|while|because|so that|"
    r"antes de|después de|hasta que|mientras|porque|depois de|até que|enquanto)\b)")

# ── R2: internal vocabulary → everyday words ──
_JARGON = {
    "en": [
        (r"\b(an? )?(exceptional|large|solid|modest|big|strong)?,? ?(work-it )?wealth engine\b",
         lambda m: f"{m.group(1) or ''}{(m.group(2) + ' ') if m.group(2) else ''}earning power"),
        (r"\byour (natural )?grain runs (strongest|best) (with|in|through)\b", "you do best in"),
        (r"\b(runs|goes|works) (with|against) (your|the|their) (natural )?grain\b",
         lambda m: f"{m.group(1)} {m.group(2)} your natural strengths"),
        (r"\b(on|off)-grain( for you)?\b", lambda m: "a natural fit for you" if m.group(1).lower() == "on" else "not a natural fit for you"),
        (r"\byour (natural )?grain\b", "your natural strengths"),
        (r"\bwealth capacity\b", "earning power"),
        (r"\bbank (your )?gains as they land\b", "move part of every gain into savings as it comes in"),
        (r"\bswings hard\b", "rises and falls sharply"),
        (r"\bswingy\b", "uneven"),
        (r"\b(tend to |can |will )?dissolve\b", lambda m: f"{m.group(1) or ''}slip away"),
        (r"\bdissolves\b", "slips away"),
    ],
    "es": [
        (r"\bmotor de (riqueza|ganancias)\b", "capacidad de generar ingresos"),
        (r"\btienden a disolverse\b", "tienden a esfumarse"),
        (r"\bse disuelven\b", "se esfuman"),
        (r"\bdisolverse\b", "esfumarse"),
    ],
    "pt": [
        (r"\bmotor de (riqueza|ganhos)\b", "capacidade de gerar renda"),
        (r"\btendem a se dissolver\b", "tendem a escapar"),
        (r"\bse dissolvem\b", "escapam"),
    ],
}

# ── R4: "pick one / double down" on a SPREAD chart ──
_PICK_ONE = re.compile(
    r"(?i)\b(pick|choose|select) (just |only )?(the |one |a single )?(one )?(venture|business|project|option|"
    r"company|idea)\b|\bdouble down (on|there)\b|\bgo deep on one\b|\bput your (full|whole) (weight|effort)"
    r" behind (one|it)\b|\bel[ií]ge (un|una) (solo |sola )?(negocio|proyecto|emprendimiento|empresa|opci[oó]n|"
    r"servicio)\b|\bescolha (um|uma) (s[oó] )?(neg[oó]cio|projeto|empresa|op[cç][aã]o)\b|"
    r"\bek (hi )?(project|venture|option|business) (choose|chuno|chuniye|chun)|\bdouble down kar")

_ROLE_MOVE = {
    "en": "Write down the kind of work where people come to you for your judgment, and give it more of your week.",
    "es": "Anota el tipo de trabajo en el que la gente acude a ti por tu criterio, y dale más horas de tu semana.",
    "pt": "Anote o tipo de trabalho em que as pessoas procuram você pelo seu critério, e dê mais horas da sua semana a ele.",
    "hi": "Likhiye kis tarah ke kaam mein log aapki samajh ke liye aate hain, aur hafte ka zyada samay usko dijiye.",
}

# ── funding brought in unasked ──
_FUND = re.compile(r"(?i)\b(fund(ing|raise|raising)?|raise (capital|money|funds|a round)|investors?|backers?|"
                   r"financiaci[oó]n|financiamiento|financiamento|captar (capital|recursos|inversi[oó]n)|"
                   r"inversionistas?|investidor(es)?)\b")
_FUND_OK_CONCERNS = {"funding", "business", "startup"}

# ── never ship without a move ──
_FALLBACK_NEXT = {
    "money": {"en": "Write down this month's three biggest outflows and cut or pause one of them this week.",
              "es": "Anota las tres salidas de dinero más grandes de este mes y recorta o pausa una esta semana.",
              "pt": "Anote as três maiores saídas de dinheiro deste mês e corte ou pause uma esta semana.",
              "hi": "Is mahine ke teen sabse bade kharche likhiye aur is hafte unmein se ek kam ya band kijiye."},
    "work": {"en": "Block one hour this week for the single task that moves your work forward most, and do it first.",
             "es": "Reserva una hora esta semana para la tarea que más hace avanzar tu trabajo, y hazla primero.",
             "pt": "Reserve uma hora esta semana para a tarefa que mais faz seu trabalho avançar, e faça-a primeiro.",
             "hi": "Is hafte ek ghanta us ek kaam ke liye rakhiye jo aapke kaam ko sabse aage badhata hai, aur pehle wahi kijiye."},
    "people": {"en": "Have one honest, unhurried conversation this week about what you need.",
               "es": "Ten esta semana una conversación honesta y sin prisa sobre lo que necesitas.",
               "pt": "Tenha esta semana uma conversa honesta e sem pressa sobre o que você precisa.",
               "hi": "Is hafte ek imaandaar, aaraam se baat kijiye ki aapko kya chahiye."},
    "health": {"en": "Pick one daily habit from this answer and keep it for the next seven days.",
               "es": "Elige un hábito diario de esta respuesta y mantenlo durante los próximos siete días.",
               "pt": "Escolha um hábito diário desta resposta e mantenha-o pelos próximos sete dias.",
               "hi": "Is jawab se ek roz ki aadat chuniye aur agle saat din usse nibhaiye."},
}
_CONCERN_GROUP = {
    "finance": "money", "wealth": "money", "loan": "money", "loss": "money", "funding": "money",
    "speculation": "money", "property": "money",
    "career": "work", "business": "work", "startup": "work", "sales": "work", "education": "work",
    "love": "people", "marriage": "people", "divorce": "people", "family": "people",
    "children": "people", "reconciliation": "people",
    "health": "health", "spiritual": "health",
}


def _lang(language: str) -> str:
    l = (language or "en").lower()
    return "hi" if l in ("hi", "hinglish") else (l[:2] if l[:2] in ("en", "es", "pt") else "en")


def plain_words(text, language: str = "en"):
    if not isinstance(text, str) or not text:
        return text
    for rx, rep in _JARGON.get(_lang(language), []) + (_JARGON["en"] if _lang(language) == "hi" else []):
        text = re.sub(rx, rep, text, flags=re.I)
    return text


def _drop_sentences(text, rx, keep_min: int = 1):
    """Drop sentences matching rx; never below keep_min sentences (then unchanged)."""
    if not isinstance(text, str) or not text.strip():
        return text, False
    sents = [x for x in _SENT.split(text.strip()) if x.strip()]
    kept = [x for x in sents if not rx.search(x)]
    if len(kept) == len(sents) or len(kept) < keep_min:
        return text, False
    return " ".join(kept), True


def polish_answer(payload: dict, language: str = "en", typed_question: str = "",
                  concern: str = "general", chart_lean: str = "", thread_text: str = "") -> dict:
    try:
        if not isinstance(payload, dict) or payload.get("needs_clarification"):
            return payload
        lang = _lang(language)
        own = f"{typed_question} {thread_text}"
        for f in ("read", "next"):
            payload[f] = plain_words(payload.get(f), language)
        # R4 — spread chart: no "pick one venture / double down" (unless they asked to pick one)
        if chart_lean == "spread" and not _PICK_ONE.search(own):
            payload["read"], _ = _drop_sentences(payload.get("read"), _PICK_ONE, keep_min=2)
            nx = payload.get("next")
            if isinstance(nx, str) and _PICK_ONE.search(nx):
                nx2, _ = _drop_sentences(nx, _PICK_ONE, keep_min=1)
                payload["next"] = nx2 if (nx2 != nx and nx2.strip()) else _ROLE_MOVE[lang]
                print(f"[ask][polish] spread chart: pick-one move replaced")
        # unasked funding talk
        if (concern or "") not in _FUND_OK_CONCERNS and not _FUND.search(own):
            payload["read"], d1 = _drop_sentences(payload.get("read"), _FUND, keep_min=2)
            nx = payload.get("next")
            if isinstance(nx, str) and _FUND.search(nx):
                nx2, _ = _drop_sentences(nx, _FUND, keep_min=1)
                payload["next"] = nx2 if (nx2 != nx and nx2.strip()) else None
            if d1:
                print("[ask][polish] unasked funding sentence dropped")
        # a move that is only a fragment ("before it touches either venture.",
        # "untouched by either venture.") is no move — conversation audit
        nx = payload.get("next")
        if isinstance(nx, str) and nx.strip() and _FRAGMENT.match(nx.strip()):
            print(f"[ask][polish] fragment move dropped: {nx[:60]!r}")
            payload["next"] = None
        # never ship without a move
        if not (isinstance(payload.get("next"), str) and payload["next"].strip()):
            grp = _CONCERN_GROUP.get((concern or "general").lower(), "work")
            payload["next"] = _FALLBACK_NEXT[grp][lang]
            print(f"[ask][polish] fallback move ({grp})")
    except Exception as e:
        print(f"[ask][polish] non-fatal: {e}")
    return payload
