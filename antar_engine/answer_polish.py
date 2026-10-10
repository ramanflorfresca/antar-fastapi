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
    "hi": [
        (r"\b(jo )?(main )?trigger( jo)?( chahiye)?\s*[—-]?\s*woh abhi bana nahi hai", "sahi mauka abhi nahi aaya hai"),
        (r"\b(main )?trigger abhi (bana )?nahi (bana )?hai", "sahi mauka abhi nahi aaya hai"),
    ],
    "en": [
        # [family-answers 2026-10-05] internal event-engine labels echoed to the reader
        (r"\bthe trigger (that|which) (turns|converts|makes)[^.—;]*?(hasn'?t|has not|isn'?t|is not|hasn’t)\s+(formed|fired|clicked|arrived|come|here|happened)( yet)?",
         "the right moment hasn't come yet"),
        (r"\bthe trigger (hasn'?t|has not|isn'?t|is not|hasn’t|isn’t)[^.—;,]{0,25}?(in place|there|here|ready|set|formed|fired|clicked|arrived|come)( yet)?",
         "the right moment hasn't come yet"),
        (r"\bthe trigger (forms?|comes?|arrives?)\b", "the right moment comes"),
        (r"\bthe board (shows|says|reads|suggests)\b", lambda m: f"the reading {m.group(1)}"),
        # keep the space before the phrase ("Your wealth engine" must not become "Yourearning power")
        (r"(?:(?<=\s)|^)(an? )?((?:exceptional|large|solid|modest|big|strong),? )?(work-it )?wealth engine\b",
         lambda m: ((m.group(1) or "") + m.group(2) + "earning power") if m.group(2) else "earning power"),
        (r"\byour (natural )?grain runs (strongest|best) (with|in|through)\b", "you do best in"),
        (r"\b(runs|goes|works) (with|against) (your|the|their) (natural )?grain\b",
         lambda m: f"{m.group(1)} {m.group(2)} your natural strengths"),
        (r"\b(on|off)-grain( for you)?\b", lambda m: "a natural fit for you" if m.group(1).lower() == "on" else "not a natural fit for you"),
        # [layers 2026-10-05] "runs with your timing's grain" / "against the grain of your timing"
    (r"\b(with|against) (your|the|their|its) ([\w -]{0,20}?)(?:'s|’s) grain\b", lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}".strip()),
    (r"\b(with|against) the grain of (your|the|their) ([\w -]{0,20}?)\b(?=[.,;—])", lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}".strip()),
    (r"\b([\w-]+)(?:'s|’s) grain\b", lambda m: f"{m.group(1)}'s natural pattern"),
    # leftover forms the prompt no longer asks for, but the model still produces now and then
    (r"\b([\w-]+)(?:'s|’s) (?:strongest |natural |own |real )?grain\b", lambda m: f"{m.group(1)}'s natural fit"),
    (r"\bruns? with (that|this|the|your|their) grain\b", lambda m: f"fits {m.group(1)}" if m.group(1) in ("that", "this") else "fits"),
    (r"\bruns? against (that|this|the|your|their) grain\b", lambda m: f"cuts against {m.group(1)}" if m.group(1) in ("that", "this") else "cuts against it"),
    (r"\b(that|this) grain\b", lambda m: f"{m.group(1)} natural fit"),
    (r"\b(with|against|along) the grain\b", lambda m: f"{m.group(1)} the natural fit"),
    (r"\byour (natural )?grain\b", "your natural strengths"),
    (r"\b(strongest |natural )?grain\b(?=\s*(?:—|-|,|which|that|is|exactly|and))", "natural fit"),
        (r"\bwealth capacity\b", "earning power"),
        (r"\bbank (your )?gains as they land\b", "move part of every gain into savings as it comes in"),
        (r"\bswings hard\b", "rises and falls sharply"),
        (r"\bswingy\b", "uneven"),
        (r"\b(tend to |can |will )?dissolve\b", lambda m: f"{m.group(1) or ''}slip away"),
        (r"\bdissolves\b", "slips away"),
    ],
    "es": [
        # [family-answers 2026-10-05] internal event-engine labels echoed to the reader
        (r"\bel detonador que (convierte|transforma|hace)[^.—;]*", "el momento justo"),
        (r"\bel detonador\b", "el momento justo"),
        (r"\bel tablero (muestra|dice|indica|sugiere)\b", lambda m: f"la lectura {m.group(1)}"),
        (r"\bmotor de (riqueza|ganancias)\b", "capacidad de generar ingresos"),
        (r"\btienden a disolverse\b", "tienden a esfumarse"),
        (r"\bse disuelven\b", "se esfuman"),
        (r"\bdisolverse\b", "esfumarse"),
    ],
    "pt": [
        (r"\bo (tabuleiro|painel) (mostra|diz|indica|sugere)\b", lambda m: f"a leitura {m.group(2)}"),
        (r"\bo gatilho que (converte|transforma|faz)[^.—;]*", "o momento certo"),
        (r"\bmotor de (riqueza|ganhos)\b", "capacidade de gerar renda"),
        (r"\btendem a se dissolver\b", "tendem a escapar"),
        (r"\bse dissolvem\b", "escapam"),
    ],
}

# ── R4: "pick one / double down" on a SPREAD chart ──
_PICK_ONE = re.compile(
    # [audit-b4] adjectives may sit between "one" and the noun ("pick the one client-facing or
    # investigative project"), and ES/PT/Hinglish forms
    r"(?i)\b(pick|choose|select|el[ií]ge|elige|escolha|chuno|chuniye|pick karo)\b[^.!?]{0,12}\b(one|un|una|um|uma|ek)\b"
    r"[^.!?]{0,40}\b(venture|business|project|option|company|idea|role|lane|track|area|field|stream|direction|path|priority|campo|pieza|"
    r"proyecto|negocio|emprendimiento|projeto|neg[oó]cio|kaam|cheez)s?\b|\bone clear (leadership )?(role|mandate|lane|focus|venture)\b|"
    r"\b(el[ií]ge|escolha|pick|choose)\s+(el|la|o|a|the)\s+(campo|[aá]rea|proyecto|projeto|negocio|neg[oó]cio|"
    r"emprendimiento|field|lane|track|project)\b|\blleva esa pieza al frente\b|"
    r"\b(pick|choose|select) (just |only )?(the |one |a single )?(one )?(venture|business|project|option|"
    r"company|idea)\b|\bdouble down (on|there)\b|\bgo deep on one\b|\bput your (full|whole) (weight|effort)"
    r" behind (one|it)\b|\bel[ií]ge (un|una) (solo |sola )?(negocio|proyecto|emprendimiento|empresa|opci[oó]n|"
    r"servicio)\b|\bescolha (um|uma) (s[oó] )?(neg[oó]cio|projeto|empresa|op[cç][aã]o)\b|"
    r"\bek (hi )?(project|venture|option|business) (choose|chuno|chuniye|chun)|\bdouble down kar|"
    # [audit-b3] the career "drive scatters" framing on a spread chart
    r"\bone clear (mandate|lane|focus|venture)\b|\bhalf-built (ventures|projects)\b|"
    # [layers] "Identify your single highest-paying service or client and put more of your time there"
    r"\b(identify|find|name|choose|pick) (your |the )?(single|one|top|best|highest|most)[- ][\w -]{0,30}"
    r"(service|client|venture|product|stream|source|customer|deal|business)\b|"
    r"\bput (more|most|all) of your (time|effort|focus|energy|week) (there|on (it|that)|into (it|that))\b|"
    r"\bchas(e|ing) (new )?ventures\b|\bnaye ventures chase\b|\bpick the one (active )?(work stream|stream|track)\b|"
    r"\b(presence|focus) double kar|"
    # [spread-profession] "unfocused, that same drive scatters into too many directions", "pick your focus and
    # commit to it" — a profession answer must not tell a SPREAD reader to narrow (EN/ES/PT/Hinglish)
    r"\bscatter(s|ed|ing)?\b|\btoo many directions\b|\bpick your focus\b|\bcommit to (it|one|that)\b|"
    r"\bunfocused\b|\bwithout focus\b|\bone clear (direction|lane|focus)\b|\bover three\b|"
    r"\bdispersa\w*|\bdemasiadas direcciones\b|\belige tu enfoque\b|\bespalha\w*\b|\bbikhar\w*|"
    r"\bel[ií]ge (el|la) (pr[oó]xim\w*|siguiente) (proyecto|negocio|emprendimiento)\b|"
    r"\bel[ií]ge\s+(un|una|el|la)\s+(?:\w+\s+){0,2}(?:[áa]rea|campo|l[ií]nea|cliente|proyecto|negocio|emprendimiento|servicio)\b|"
    r"\bescolha\s+(um|uma|o|a)\s+(?:\w+\s+){0,2}(?:[áa]rea|campo|linha|cliente|projeto|neg[oó]cio|servi[cç]o)\b|"
    r"\bescolha (o|a) (pr[oó]xim\w*|seguinte) (projeto|neg[oó]cio)\b")

_ROLE_MOVE = {
    "en": "Write down the kind of work where people come to you for your judgment, and give it more of your week.",
    "es": "Anota el tipo de trabajo en el que la gente acude a ti por tu criterio, y dale más horas de tu semana.",
    "pt": "Anote o tipo de trabalho em que as pessoas procuram você pelo seu critério, e dê mais horas da sua semana a ele.",
    "hi": "Likhiye kis tarah ke kaam mein log aapki samajh ke liye aate hain, aur hafte ka zyada samay usko dijiye.",
}

# ── funding brought in unasked ──
_FUND = re.compile(r"(?i)\b((?<!emergency )(?<!rainy-day )(?<!rainy day )(?<!savings )(?<!reserve )(?<!sinking )fund(ing|raise|raising)?|raise (capital|money|funds|a round)|investors?|backers?|backing|"
                   r"outside (money|capital|resources|funding)|other people'?s money|shared money|"
                   r"financiaci[oó]n|financiamiento|financiamento|captar (capital|recursos|inversi[oó]n)|"
                   r"inversionistas?|investidor(es)?)\b")
_FUND_OK_CONCERNS = {"funding", "business", "startup"}
_VAGUE_FILLER = re.compile(r"(?i)\bthe timing (genuinely )?shows\b|\bthe setup (for [\w ]{1,30})?is real\b|"
                           r"\bhasn'?t (fully )?(arrived|formed)\b|\bright moment\b|\bgenuine (pressure|promise)\b")
_FILLER_OPENER = re.compile(r"(?i)\b(this|that|your)\s+(concern|feeling|worry|stuck feeling|frustration|tiredness|exhaustion|"
                            r"anxiety|pattern|question)\b[^.]{0,40}\b(is|are) real\b|\bworth acting on,? not worrying\b|"
                            r"\bit won'?t last\b|\byou deserve a straight answer\b")
_COUNT_CLAIM = re.compile(r"(?i)\b(two|three|four|five|six|seven|\d+) (?:(?:separate|independent|different) )?"
                          r"(patterns|checks|layers|signals|reads|systems|timing systems)\b")
_THIRD_PARTY_CLAIM = re.compile(r"(?i)\b(your |the )?(ex|partner|he|she|they|his|her|their)(?:'s)?\s+(side|chart|timing|stars?|planets?)\b|"
                                r"\b(his|her|their) (chart|timing)\b")
_FINALITY = re.compile(r"(?i)\bchapter has closed\b|\bit'?s not coming back\b|\bmarriage ended\b|\bis over for good\b")
_THIRD_FEELING = re.compile(r"(?i)\b(they|he|she)(?:'re| is| are)\s+(open|ready|waiting|thinking|missing|still in love|willing|receptive)\b|"
                            r"\b(they|he|she) (will|would) (say yes|reply|respond|come back)\b|"
                            r"\bboth of you (are|is|seem|feel)\s+(open|ready|willing|receptive)\b")
_GENERIC_PARTNER_MOVE = re.compile(r"(?i)what a good partnership looks like|new connection rather than reopening|"
                                   r"honest,? unhurried conversation about what you need|reopening a closed door")
_PAST_MARRIAGE = re.compile(r"(?i)\byour (past|previous|former|earlier) (marriage|relationship)s?\b|\bpast marriage\b")
_HERB = re.compile(r"(?i)\b(brahmi|gotu kola|abhyanga|sesame|ashwagandha|neem|triphala|guduchi|shatavari|turmeric|amla)\b|"
                   r"traditionally, ayurveda")
_HERB_ASKED = re.compile(r"(?i)herb|remed|ayurved|natural|supplement|diet|\beat\b|food|medicine|treat|cure|"
                         r"what (can|should|do) i do|how (can|do|should) i")
_HOLDS = re.compile(r"(?i)\bit holds if\b|\bit breaks if\b|\bonly if\b|\bdepends on\b")
_NOT_IN_REL = re.compile(r"(?i)\byou(?:'re| are)\s+(?:not\s+(?:currently\s+|presently\s+)?(?:in|seeing)|(?:currently\s+)?single|between)|"
                         r"no current (?:relationship|partner)|\b(?:your|the)\s+past\s+(?:marriage|relationship)\b")

# ── receivables / debts nobody mentioned ([audit-b4]) ──
_OWED = re.compile(
    r"(?i)\b(owes? me|owed to me|owe me|me deben|me devem|mujhe .{0,20}dena hai|owed to you|you'?re (already )?owed|what you'?re owed|overdue (payments?|invoices?)|unpaid (amounts?|invoices?)|"
    r"outstanding (payments?|invoices?|receivables)|receivables?|collect (what|the money|payments?|on)|"
    r"your debts?|the debt|loan pressure|work-and-debt|"
    r"te deben|lo que te deben|pagos pendientes|cobrar lo que|cuentas por cobrar|tus deudas|"
    r"te devem|o que te devem|pagamentos (pendentes|atrasados)|suas d[ií]vidas|"
    r"paisa (already )?aana chahiye tha|udhaar wapas|overdue payment|baaki paisa)\b")

# ── never ship without a move ──
_FALLBACK_NEXT = {
    "money": {"en": "Starting this week, move a fixed share of every payment — say 10% — into a separate savings account.",
              "es": "Desde esta semana, pasa una parte fija de cada pago — por ejemplo el 10% — a una cuenta de ahorro aparte.",
              "pt": "A partir desta semana, mova uma parte fixa de cada pagamento — por exemplo 10% — para uma conta poupança separada.",
              "hi": "Is hafte se har payment ka ek fixed hissa — jaise 10% — ek alag savings account mein daaliye."},
    "work": {"en": "Block one hour this week for the task that moves your work forward most, and do it first.",
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
# money: a second move for when the answer itself says money is tight ("10% of every payment" reads
# tone-deaf next to "outflow is running ahead of income"), and so a move is never repeated
_MONEY_CUT = {"en": "Write down this month's three biggest outflows and cut or pause one of them this week.",
              "es": "Anota las tres salidas de dinero más grandes de este mes y recorta o pausa una esta semana.",
              "pt": "Anote as três maiores saídas de dinheiro deste mês e corte ou pause uma esta semana.",
              "hi": "Is mahine ke teen sabse bade kharche likhiye aur is hafte unmein se ek kam ya band kijiye."}
_MONEY_TIGHT = re.compile(r"(?i)outflow|\bleak|pressure on (your )?savings|running ahead|\btight\b|squeez|overhead|"
                          r"salidas|gastos|presi[oó]n en (el )?ahorro|sa[ií]das|kharch|dabav")


def _norm_move(x) -> str:
    return re.sub(r"\W+", " ", (x or "").lower()).strip()


def _pick_fallback(grp: str, lang: str, read: str, prev_moves) -> str:
    opts = [_FALLBACK_NEXT[grp][lang]]
    if grp == "money":
        opts = ([_MONEY_CUT[lang], opts[0]] if _MONEY_TIGHT.search(read or "") else [opts[0], _MONEY_CUT[lang]])
    prev = {_norm_move(p) for p in (prev_moves or []) if p}
    for o in opts:
        if _norm_move(o) not in prev:
            return o
    return opts[0]


_CONCERN_GROUP = {
    "finance": "money", "wealth": "money", "loan": "money", "loss": "money", "funding": "money",
    "speculation": "money", "property": "money",
    "career": "work", "business": "work", "startup": "work", "sales": "work", "education": "work",
    "love": "people", "marriage": "people", "divorce": "people", "family": "people",
    "children": "people", "reconciliation": "people", "family": "people",
    "health": "health", "spiritual": "health",
}


# an internal astrology term ("the ruler of your home is weak", "ghar ka ruler") — drop the sentence
_INTERNAL_TERM = re.compile(r"(?i)\b(ruler|lord of the|house lord|karaka|dasha|nakshatra)\b")

# ── family / home-life answers ([family-answers 2026-10-05]) ──
FAMILY_GUARD = ("FAMILY LIFE — this is about peace and closeness at home with the people they live with "
                "or are close to. Do NOT bring up property, real estate, buying or selling a home, deals, "
                "money, finances, savings or the business unless the question did. Do not assume who is "
                "in their household. Never write the internal words 'trigger', 'board', 'promise'.")
_FAM_SWAP = [
    (re.compile(r"(?i)\b(home and property|property and home|home or property|home/property|home and real estate)\b"), "home"),
    (re.compile(r"(?i)\b(the )?(hogar y (la )?propiedad|casa y propiedad|propiedad y hogar)\b"), "el hogar"),
    (re.compile(r"(?i)\b(casa e propriedade|lar e propriedade|propriedade e casa)\b"), "a casa"),
    (re.compile(r"(?i)\b(property|home)\s+(ya|aur)\s+(home|property)\b"), "ghar"),
]
_FAM_OFFTOPIC = re.compile(
    r"(?i)\b(property|real estate|propiedad|inmueble|bienes ra[ií]ces|im[oó]vel|shared finances|family money|"
    r"money conversations?|financial|finances|savings|cushion|finanzas( familiares)?|ahorros?|colch[oó]n|dinero|"
    r"poupan[cç]a|finan[cç]as|dinheiro|paisa|property se|property ke)\b")


def _lang(language: str) -> str:
    l = (language or "en").lower()
    # [hi 2026-10-07] "hi" = Devanagari: these tables hold Roman-script copy under their legacy "hi" key, so a
    # Devanagari reader must NOT get them. Explicit English here; Ask's Devanagari guard translates the answer.
    return "hi" if l in ("hinglish", "hi-latn") else (l[:2] if l[:2] in ("en", "es", "pt") else "en")


def _keepcase(rep):
    """Replacement that keeps a sentence-initial capital ("The board shows" → "The reading shows")."""
    def sub(m):
        r = rep(m) if callable(rep) else m.expand(rep)
        return (r[:1].upper() + r[1:]) if (m.group(0)[:1].isupper() and r) else r
    return sub


def plain_words(text, language: str = "en"):
    if not isinstance(text, str) or not text:
        return text
    # Hinglish keeps its own words (EN "slip away" inside Hinglish read oddly) — only the
    # pure internal terms are replaced there
    extra = [r for r in _JARGON["en"] if "wealth" in r[0] or "grain" in r[0]] if _lang(language) == "hi" else []
    for rx, rep in _JARGON.get(_lang(language), []) + extra:
        text = re.sub(rx, _keepcase(rep), text, flags=re.I)
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


# a caution against bold moves, or the opposite, in an answer whose verdict says otherwise
_CAUTION_BOLD = re.compile(r"(?i)\bsteady,? grounded\b|\b(over|than|not|rather than) (bold|dramatic|big) (pivots?|bets?|moves?|decisions?)\b|"
                           r"\bbold (new )?(bets?|pivots?)\b|\bavoid (bold|big) (moves?|decisions?)\b|"
                           r"\bestable y (firme|tranquilo)\b.{0,30}\bque (los )?(cambios|movimientos) bruscos\b")
_SUPPORT_BOLD = re.compile(r"(?i)\b(strongly )?(supports?|backs|favou?rs|green-?lights?) (bold|big|dramatic|a big|a bold)\b")


def polish_answer(payload: dict, language: str = "en", typed_question: str = "",
                  concern: str = "general", chart_lean: str = "", thread_text: str = "",
                  prev_moves=(), chart_data=None, dashas=None) -> dict:
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
        if not _INTERNAL_TERM.search(own):
            payload["read"], d_i = _drop_sentences(payload.get("read"), _INTERNAL_TERM, keep_min=2)
            if d_i:
                print("[ask][polish] internal-term sentence dropped")
        # family / home life: no property or money talk nobody raised
        if (concern or "") == "family":
            for rx, rep in _FAM_SWAP:
                for f in ("read", "next"):
                    if isinstance(payload.get(f), str):
                        payload[f] = rx.sub(rep, payload[f])
            if not _FAM_OFFTOPIC.search(own):
                payload["read"], d_f = _drop_sentences(payload.get("read"), _FAM_OFFTOPIC, keep_min=2)
                nx = payload.get("next")
                if isinstance(nx, str) and _FAM_OFFTOPIC.search(nx):
                    nx2, _ = _drop_sentences(nx, _FAM_OFFTOPIC, keep_min=1)
                    payload["next"] = nx2 if (nx2 != nx and nx2.strip()) else None
                    print("[ask][polish] family: off-topic move replaced")
                if d_f:
                    print("[ask][polish] family: off-topic sentence dropped")
        # receivables / debts nobody mentioned
        if not _OWED.search(own):
            payload["read"], d0 = _drop_sentences(payload.get("read"), _OWED, keep_min=2)
            nx = payload.get("next")
            if isinstance(nx, str) and _OWED.search(nx):
                nx2, _ = _drop_sentences(nx, _OWED, keep_min=1)
                payload["next"] = nx2 if (nx2 != nx and nx2.strip()) else None
                print("[ask][polish] assumed-receivable move replaced")
            if d0:
                print("[ask][polish] assumed-receivable sentence dropped")
        # a YES / open-window answer must not also warn against moving ("steady, grounded over bold
        # pivots"), and a NOT-YET answer must not also "strongly support bold decisions"
        v = str(payload.get("verdict") or "").upper()
        if v in ("YES", "LIKELY") and not _CAUTION_BOLD.search(own):
            payload["read"], d_c = _drop_sentences(payload.get("read"), _CAUTION_BOLD, keep_min=2)
            if d_c:
                print("[ask][polish] caution-against-a-YES sentence dropped")
        elif v in ("NOT_YET", "NO"):
            payload["read"], d_s = _drop_sentences(payload.get("read"), _SUPPORT_BOLD, keep_min=2)
            if d_s:
                print("[ask][polish] bold-support-on-a-NOT-YET sentence dropped")
        # unasked funding talk
        if (concern or "") not in _FUND_OK_CONCERNS and not _FUND.search(own):
            payload["read"], d1 = _drop_sentences(payload.get("read"), _FUND, keep_min=2)
            nx = payload.get("next")
            if isinstance(nx, str) and _FUND.search(nx):
                nx2, _ = _drop_sentences(nx, _FUND, keep_min=1)
                payload["next"] = nx2 if (nx2 != nx and nx2.strip()) else None
            if d1:
                print("[ask][polish] unasked funding sentence dropped")
        # [ask-direct 2026-10-10] "is my current relationship going to last?" answered "you're not in a
        # relationship — so this reads as a question about your past marriage": the reader's own words win
        if re.search(r"(?i)\b(my|our)\s+(current\s+|present\s+)?(relationship|partner|boyfriend|girlfriend|husband|wife|spouse|fianc\w*)\b", own):
            payload["read"], d_rel = _drop_sentences(payload.get("read"), _NOT_IN_REL, keep_min=2)
            if d_rel:
                print("[ask][polish] contradicted 'not in a relationship' sentence dropped")
        # a move whose first sentence was cut ("Then build or improve it until it's perfect.") is no move
        nx = payload.get("next")
        if isinstance(nx, str) and re.match(r"(?i)\s*(then|and|but|so|also|that)\b", nx):
            print(f"[ask][polish] dangling move dropped: {nx[:60]!r}")
            payload["next"] = None
        # a move that is only a fragment ("before it touches either venture.",
        # "untouched by either venture.") is no move — conversation audit
        nx = payload.get("next")
        if isinstance(nx, str) and nx.strip() and _FRAGMENT.match(nx.strip()):
            print(f"[ask][polish] fragment move dropped: {nx[:60]!r}")
            payload["next"] = None
        # "book a medical check-up" as the move on a love / children question nobody asked about health on
        # is an invented worry ("The children area shows pressure that a doctor can help with")
        nx = payload.get("next")
        if (isinstance(nx, str) and (concern or "") in ("children", "love", "marriage", "reconciliation")
                and re.match(r"(?i)\s*(book|schedule|get)\b.{0,40}\b(medical|doctor|check-?up|consultation)", nx)
                and not re.search(r"(?i)health|fertil|pregnan|ivf|doctor|medical|conceive", own)):
            print(f"[ask][polish] invented-health move dropped: {nx[:60]!r}")
            payload["next"] = None
        # the same move twice in one conversation — the narrator is told not to, but still does
        nx_now = payload.get("next")
        if (isinstance(nx_now, str) and nx_now.strip() and prev_moves
                and _norm_move(nx_now) in {_norm_move(p) for p in prev_moves if p}):
            print("[ask][polish] repeated move → alternate")
            payload["next"] = None
        # ── [ask-direct 2026-10-10] prediction → what makes it true → what breaks it ──
        read0 = payload.get("read")
        if isinstance(read0, str) and read0.strip():
            for _rx, _why in ((_FILLER_OPENER, "filler opener"), (_VAGUE_FILLER, "vague filler"), (_THIRD_PARTY_CLAIM, "claim about another person's chart"),
                              (_THIRD_FEELING, "claim about another person's feelings"),
                              (_FINALITY, "harsh finality")):
                payload["read"], _d = _drop_sentences(payload.get("read"), _rx, keep_min=2)
                if _d:
                    print(f"[ask][polish] {_why} sentence dropped")
            payload["read"] = _COUNT_CLAIM.sub("several signals", payload.get("read") or "")
            if not re.search(r"(?i)marriage|married|divorc|separat|spouse|wife|husband", own):
                payload["read"], _d = _drop_sentences(payload.get("read"), _PAST_MARRIAGE, keep_min=2)
                if _d:
                    print("[ask][polish] unasked 'past marriage' sentence dropped")
            nx3 = payload.get("next")
            if isinstance(nx3, str) and _THIRD_FEELING.search(nx3):   # "they're open to hearing from you" is invented
                kept = [x for x in _SENT.split(nx3.strip()) if x.strip() and not _THIRD_FEELING.search(x)]
                payload["next"] = " ".join(kept) if kept else None
                print("[ask][polish] claim about another person's feelings dropped from the move")
            nx4 = payload.get("next")
            if isinstance(nx4, str) and _GENERIC_PARTNER_MOVE.search(nx4):   # self-help that ignores the question
                payload["next"] = None
                print("[ask][polish] generic partnership move dropped")
            if not _HERB_ASKED.search(own):
                payload["read"], _d = _drop_sentences(payload.get("read"), _HERB, keep_min=1)
                nxh = payload.get("next")
                if isinstance(nxh, str) and _HERB.search(nxh):
                    kept = [x for x in _SENT.split(nxh.strip()) if x.strip() and not _HERB.search(x)]
                    kept = [x for x in kept if not re.search(r"(?i)not medical advice|qualified doctor", x)] or []
                    payload["next"] = " ".join(kept) if kept else None   # only a disclaimer left = no move
                    print("[ask][polish] unasked herb advice dropped from the move")
            try:
                if not _HOLDS.search(payload.get("read") or ""):
                    from antar_engine.ask_basis import conditions as _cond
                    _c = _cond((concern or "general").lower(), chart_data, dashas, lang)
                    if _c:
                        payload["read"] = (payload["read"].rstrip() + " " + _c).strip()
                        print("[ask][polish] conditions appended")
            except Exception as _ce:
                print(f"[ask][polish] conditions skipped: {_ce}")
        # [ex-move 2026-10-10] a reconnection question's move follows from the ENGINE verdict, identically in en / es / pt
        # (the model's own move varied run to run: "send one message" / "don't send another" / "decide first")
        if (concern or "") in ("reconciliation", "marriage") and lang in ("en", "es", "pt"):
            try:
                from antar_engine.ask_basis import stable_reconnection_move as _srm
                _mv = _srm(payload.get("verdict"), chart_data, dashas, lang, payload.get("timing") or "", concern)
                if _mv:
                    payload["next"] = _mv
                    print("[ask][polish] stable reconnection move")
            except Exception as _sme:
                print(f"[ask][polish] stable move skipped: {_sme}")
        # never ship without a move
        if not (isinstance(payload.get("next"), str) and payload["next"].strip()):
            grp = _CONCERN_GROUP.get((concern or "general").lower(), "work")
            if (concern or "") == "family":
                grp = "people"
            try:   # "I'm 100% all in on X" is a money-placement statement whatever the concern
                from antar_engine.wealth_magnitude import is_allocation_statement as _ias
                if _ias(typed_question):
                    grp = "money"
            except Exception:
                pass
            _cm = ""
            try:   # [ask-direct 2026-10-10] a move that follows from this chart + topic before any canned line
                from antar_engine.ask_basis import chart_move as _cmove
                _cm = _cmove((concern or "general").lower(), chart_data, dashas, lang)
                if _cm and _norm_move(_cm) in {_norm_move(p) for p in (prev_moves or []) if p}:
                    _cm = ""
            except Exception:
                _cm = ""
            payload["next"] = _cm or _pick_fallback(grp, lang, payload.get("read") or "", prev_moves)
            print(f"[ask][polish] fallback move ({'chart' if _cm else grp})")
    except Exception as e:
        print(f"[ask][polish] non-fatal: {e}")
    return payload


# ── register scrub: the last pass on every shipped answer ──────────────────
# "reading" is the horoscope register (App Store 4.3 — the answer card is the
# landing screen); "timing" is what the product does. #196 fixed the repair layer
# and the source strings, but the LLM and the opener templates still produce
# "the reading shows…" on other paths, so this runs at the exit.
_READING_RX = re.compile(r"\b(the|your|this)\s+readings?\b", re.I)
# the body is "robust"/"strong" is a medical reassurance about a person who may be
# ill — not something timing can promise (product-liability, Guideline 1.4.1)
_BODY_REASSURE = re.compile(
    r"(?i)\b(constitution|body|health|system|immunity)\b[^.!?]{0,60}\b(robust|strong|sturdy|resilient|solid|healthy)\b"
    r"|\b(robust|strong|sturdy|resilient|solid)\b[^.!?]{0,40}\b(constitution|body|immunity)\b"
    r"|\bno (deep|serious|structural) (structural )?(problems?|issues?)\b|\bdeep structural\b")
_BUT = re.compile(r",?\s+but\s+|\s+—\s+|;\s+", re.I)


def _scrub_reading(m):
    return f"{m.group(1)} timing"


def _strip_body_reassurance(text):
    """Drop the clause (or sentence) that vouches for the body's strength; keep the rest."""
    if not isinstance(text, str) or not _BODY_REASSURE.search(text):
        return text
    out = []
    for sent in _SENT.split(text.strip()):
        if not _BODY_REASSURE.search(sent):
            out.append(sent)
            continue
        parts = _BUT.split(sent, maxsplit=1)
        if len(parts) == 2 and _BODY_REASSURE.search(parts[0]) and not _BODY_REASSURE.search(parts[1]):
            tail = parts[1].strip()
            if tail:
                out.append(tail[0].upper() + tail[1:])
        # otherwise the whole sentence is the reassurance — drop it
    return " ".join(out) if out else text


def scrub_register(payload: dict, language: str = "en") -> dict:
    """In-place: English "the reading" → "the timing" and no body-strength reassurance.
    Non-fatal; es/pt/hi sources were already reworded in #196."""
    try:
        if not isinstance(payload, dict) or _lang(language) != "en":
            return payload
        for f in ("read", "next", "why"):
            v = payload.get(f)
            if isinstance(v, str) and v:
                v = _READING_RX.sub(_scrub_reading, v)
                v2 = _strip_body_reassurance(v)
                payload[f] = v2 if v2.strip() else v
        acts = payload.get("actions")
        if isinstance(acts, list):
            payload["actions"] = [_READING_RX.sub(_scrub_reading, a) if isinstance(a, str) else a
                                  for a in acts]
    except Exception as e:
        print(f"[ask][scrub] non-fatal: {e}")
    return payload
