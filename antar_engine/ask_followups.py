"""[followup-flows 2026-10-04] Ask's "what next" questions, chosen by INTENT LANE.

A static three-per-topic list offered the same chips whatever was asked, so a
reader who asked WHEN got another WHEN, and a reader who said work feels stuck got
a timing chip before anything they could do about it. After a reading, people move
along a small set of needs; each topic carries one question per need:

  when — certainty: "when does it open / ease?"           (a sense of control)
  how  — agency:    "what do I actually do?"              (relieves helplessness)
  now  — status:    "where do I stand right now?"         (orientation)
  why  — meaning:   "what is this chapter about?"         (makes the read stick)
  wide — the bigger frame (day bucket: the week)

Rules (deterministic — no LLM cost or drift):
  1. The lane they just asked is satisfied → it goes last. If the answer already
     carried a dated window, WHEN is satisfied too.
  2. Next lanes follow what that kind of question leaves open (ORDER below).
  3. Distress words ("stuck", "anxious", "pareshan"…) → agency first, then hope
     (WHEN it eases) — never a "why" spiral for someone who is already struggling.
  4. Two in-domain questions, then ONE bridge to the neighbouring life area
     (money ↔ career, love ↔ family, health ↔ inner life): life isn't siloed and
     the reader may not know Antar reads the other areas.
Free text is always open — the WhatsApp list ends with an "Ask your own" row.
"""
import re

LANES = ("when", "how", "now", "why", "wide")

# asked lane → which lanes to offer next, in order
ORDER = {
    "when": ("how", "why", "now", "wide", "when"),
    "how":  ("when", "now", "why", "wide", "how"),
    "why":  ("how", "when", "now", "wide", "why"),
    "now":  ("when", "how", "why", "wide", "now"),
    None:   ("now", "when", "how", "why", "wide"),
}
DISTRESS_ORDER = ("how", "when", "now", "wide", "why")
DAY_ORDER = ("now", "when", "wide", "how")

# neighbouring life area for the bridge question (None → stay in-domain)
BRIDGE = {
    "money": "career", "funding": "business", "career": "money", "business": "money",
    "love": "family", "family": "love", "health": "spiritual", "spiritual": "health",
    "place": "money", "speculation": "money", "choice": "career", "general": "career",
    "day": None,
}

_Q = {
    "en": {
        "choice": {"when": "What is my timing window for the next year?",
                   "how": "Is this a good time to decide, or should I wait?",
                   "now": "What does my chart show about this decision?",
                   "why": "What is really pulling me each way?"},
        "money": {"when": "When does my strongest money window open?",
                  "how": "What can I do to strengthen my money period?",
                  "now": "How does this month look for my money?",
                  "why": "What in my chart explains the ups and downs with money?"},
        "funding": {"when": "When will funding most likely come through?",
                    "how": "What can I do to help the funding come through?",
                    "now": "How does my money look while I wait?",
                    "why": "What is slowing the money down?"},
        "career": {"when": "When will my career take off?",
                   "how": "What can I do to strengthen my career period?",
                   "now": "How does my career period look this year?",
                   "why": "Why does work feel stuck right now?"},
        # [business-followups 2026-10-02] timing + approach only — never "which business will succeed"
        "business": {"when": "When is the best time to raise funding?",
                     "how": "How do I make the most of this period for my venture?",
                     "now": "How do the next few months look for my venture?",
                     "why": "What does my chart say about how I work best?"},
        "love": {"when": "When is my best window for love?",
                 "how": "What helps love grow for me right now?",
                 "now": "How is my love life looking right now?",
                 "why": "What pattern do I keep repeating in love?"},
        "family": {"when": "When does the pressure at home ease?",
                   "how": "How do I handle the tension at home right now?",
                   "now": "How is my family life looking this year?",
                   "why": "What is this chapter at home asking of me?"},
        "health": {"when": "When does my energy pick up?",
                   "how": "Which daily practice fits me now?",
                   "now": "What should I focus on for my health this year?",
                   "why": "What is draining my energy right now?"},
        "place": {"when": "When is a good time to buy or move?",
                  "how": "Does real estate fit my chart?",
                  "now": "Where does my chart support me best?",
                  "why": "Why don't I feel at home where I am?"},
        # [spec-chips 2026-10-03] owner: "which day" stays — day and crypto traders plan by day
        "speculation": {"when": "When does my next window for unearned gains open?",
                        "how": "Is this a safe time to take a risk, or should I wait?",
                        "now": "Which day this week is best for me?",
                        "why": "What drives my urge to take risks?"},
        "spiritual": {"when": "When is my strongest spiritual window?",
                      "how": "How do I steady my mind this month?",
                      "now": "Which practice fits me best right now?",
                      "why": "What is this phase teaching me?"},
        "day": {"now": "How is tomorrow looking?",
                "when": "What is the best time of day for me today?",
                "how": "What should I avoid today?",
                "wide": "How is my week ahead?"},
        "general": {"when": "When does my next strong window open?",
                    "how": "What is this month asking of me?",
                    "now": "How is my money looking right now?",
                    "why": "What is this chapter of my life about?"},
    },
    # Hinglish (a Hinglish chat must not flip to English on a tap)
    "hi": {
        "choice": {"when": "Agle saal ke liye meri timing window kya hai?",
                   "how": "Kya abhi faisla lene ka sahi samay hai, ya ruk jaun?",
                   "now": "Mera chart is faisle ke baare mein kya dikhata hai?",
                   "why": "Mujhe asal mein dono taraf kya kheench raha hai?"},
        "money": {"when": "Mera sabse strong money window kab khulega?",
                  "how": "Apne paise ke daur ko mazboot karne ke liye main kya kar sakta hoon?",
                  "now": "Is mahine mera paisa kaisa dikh raha hai?",
                  "why": "Mere chart mein paise ke utaar-chadhav ki wajah kya hai?"},
        "funding": {"when": "Funding kab tak aane ke chance hain?",
                    "how": "Funding aane mein madad ke liye main kya kar sakta hoon?",
                    "now": "Intezaar ke dauran mera paisa kaisa dikh raha hai?",
                    "why": "Paisa kis wajah se ruka hua hai?"},
        "career": {"when": "Mera career kab take off karega?",
                   "how": "Apne career ke daur ko mazboot karne ke liye main kya kar sakta hoon?",
                   "now": "Is saal mera career daur kaisa dikh raha hai?",
                   "why": "Abhi kaam atka hua kyun lag raha hai?"},
        "business": {"when": "Funding raise karne ka best time kab hai?",
                     "how": "Is daur ko apne venture ke liye kaise kaam mein laun?",
                     "now": "Agle kuch mahine mere venture ke liye kaise dikh rahe hain?",
                     "why": "Mere chart ke hisaab se main kaise sabse achha kaam karta hoon?"},
        "love": {"when": "Pyaar ke liye meri best window kab hai?",
                 "how": "Abhi mere liye pyaar ko kya badhayega?",
                 "now": "Abhi meri love life kaisi dikh rahi hai?",
                 "why": "Pyaar mein mera kaun sa pattern baar baar aata hai?"},
        "family": {"when": "Ghar ka pressure kab kam hoga?",
                   "how": "Abhi ghar ki tension kaise sambhalun?",
                   "now": "Is saal meri family life kaisi dikh rahi hai?",
                   "why": "Ghar ka yeh daur mujhse kya maang raha hai?"},
        "health": {"when": "Meri energy kab badhegi?",
                   "how": "Abhi mere liye kaun si daily practice sahi hai?",
                   "now": "Is saal sehat ke liye mujhe kis par focus karna chahiye?",
                   "why": "Abhi meri energy kahan khatam ho rahi hai?"},
        "place": {"when": "Ghar kharidne ya shift hone ka sahi time kab hai?",
                  "how": "Kya real estate mere chart se match karta hai?",
                  "now": "Mera chart mujhe kahan sabse zyada support karta hai?",
                  "why": "Jahan hoon wahan bechaini kyun lagti hai?"},
        "speculation": {"when": "Unearned gains ki meri agli window kab khulegi?",
                        "how": "Kya abhi risk lene ka safe samay hai, ya ruk jaun?",
                        "now": "Is hafte mere liye kaun sa din best hai?",
                        "why": "Risk lene ki meri ichha kahan se aati hai?"},
        "spiritual": {"when": "Meri sabse strong spiritual window kab hai?",
                      "how": "Is mahine apna mann kaise shaant rakhun?",
                      "now": "Abhi mere liye kaun si practice sahi hai?",
                      "why": "Yeh daur mujhe kya sikha raha hai?"},
        "day": {"now": "Kal kaisa dikh raha hai?",
                "when": "Aaj mere liye din ka best time kaun sa hai?",
                "how": "Aaj mujhe kis cheez se bachna chahiye?",
                "wide": "Mera hafta kaisa hai?"},
        "general": {"when": "Meri agli strong window kab khulegi?",
                    "how": "Yeh mahina mujhse kya maang raha hai?",
                    "now": "Abhi mera paisa kaisa dikh raha hai?",
                    "why": "Meri zindagi ka yeh chapter kis baare mein hai?"},
    },
    "es": {
        "choice": {"when": "¿Cuál es mi ventana de tiempo para el próximo año?",
                   "how": "¿Es buen momento para decidir o debo esperar?",
                   "now": "¿Qué muestra mi carta sobre esta decisión?",
                   "why": "¿Qué me atrae realmente hacia cada lado?"},
        "money": {"when": "¿Cuándo se abre mi mejor ventana de dinero?",
                  "how": "¿Qué puedo hacer para fortalecer mi etapa de dinero?",
                  "now": "¿Cómo se ve este mes para mi dinero?",
                  "why": "¿Qué en mi carta explica los altibajos con el dinero?"},
        "funding": {"when": "¿Cuándo llegará la financiación con más probabilidad?",
                    "how": "¿Qué puedo hacer para que llegue la financiación?",
                    "now": "¿Cómo se ve mi dinero mientras espero?",
                    "why": "¿Qué está frenando el dinero?"},
        "career": {"when": "¿Cuándo despegará mi carrera?",
                   "how": "¿Qué puedo hacer para fortalecer mi etapa profesional?",
                   "now": "¿Cómo se ve mi etapa profesional este año?",
                   "why": "¿Por qué siento el trabajo estancado ahora?"},
        "business": {"when": "¿Cuándo es el mejor momento para conseguir financiación?",
                     "how": "¿Cómo aprovecho esta etapa para mi proyecto?",
                     "now": "¿Cómo se ven los próximos meses para mi proyecto?",
                     "why": "¿Qué dice mi carta sobre cómo trabajo mejor?"},
        "love": {"when": "¿Cuándo es mi mejor ventana para el amor?",
                 "how": "¿Qué ayuda a que el amor crezca para mí ahora?",
                 "now": "¿Cómo se ve mi vida amorosa ahora?",
                 "why": "¿Qué patrón repito en el amor?"},
        "family": {"when": "¿Cuándo baja la presión en casa?",
                   "how": "¿Cómo manejo la tensión en casa ahora?",
                   "now": "¿Cómo se ve mi vida familiar este año?",
                   "why": "¿Qué me pide esta etapa en casa?"},
        "health": {"when": "¿Cuándo sube mi energía?",
                   "how": "¿Qué práctica diaria me conviene ahora?",
                   "now": "¿En qué debo enfocarme para mi salud este año?",
                   "why": "¿Qué está drenando mi energía ahora?"},
        "place": {"when": "¿Cuándo es buen momento para comprar o mudarme?",
                  "how": "¿Encaja el sector inmobiliario con mi carta?",
                  "now": "¿Dónde me apoya mejor mi carta?",
                  "why": "¿Por qué no me siento en casa donde estoy?"},
        "speculation": {"when": "¿Cuándo se abre mi próxima ventana de ganancias no ganadas?",
                        "how": "¿Es un momento seguro para arriesgar o debo esperar?",
                        "now": "¿Qué día de esta semana es mejor para mí?",
                        "why": "¿Qué impulsa mis ganas de arriesgar?"},
        "spiritual": {"when": "¿Cuándo es mi ventana espiritual más fuerte?",
                      "how": "¿Cómo calmo mi mente este mes?",
                      "now": "¿Qué práctica me conviene más ahora?",
                      "why": "¿Qué me está enseñando esta etapa?"},
        "day": {"now": "¿Cómo se ve mañana?",
                "when": "¿Cuál es la mejor hora del día para mí hoy?",
                "how": "¿Qué debo evitar hoy?",
                "wide": "¿Cómo se ve mi semana?"},
        "general": {"when": "¿Cuándo se abre mi próxima ventana fuerte?",
                    "how": "¿Qué me pide este mes?",
                    "now": "¿Cómo está mi dinero ahora mismo?",
                    "why": "¿De qué se trata esta etapa de mi vida?"},
    },
    "pt": {
        "choice": {"when": "Qual é minha janela de tempo para o próximo ano?",
                   "how": "É um bom momento para decidir ou devo esperar?",
                   "now": "O que meu mapa mostra sobre essa decisão?",
                   "why": "O que realmente me puxa para cada lado?"},
        "money": {"when": "Quando abre minha melhor janela de dinheiro?",
                  "how": "O que posso fazer para fortalecer minha fase de dinheiro?",
                  "now": "Como este mês parece para meu dinheiro?",
                  "why": "O que no meu mapa explica os altos e baixos com o dinheiro?"},
        "funding": {"when": "Quando o financiamento deve chegar?",
                    "how": "O que posso fazer para o financiamento chegar?",
                    "now": "Como está meu dinheiro enquanto espero?",
                    "why": "O que está travando o dinheiro?"},
        "career": {"when": "Quando minha carreira vai decolar?",
                   "how": "O que posso fazer para fortalecer minha fase profissional?",
                   "now": "Como está minha fase profissional este ano?",
                   "why": "Por que o trabalho parece travado agora?"},
        "business": {"when": "Quando é o melhor momento para captar investimento?",
                     "how": "Como aproveito esta fase para meu projeto?",
                     "now": "Como estão os próximos meses para meu projeto?",
                     "why": "O que meu mapa diz sobre como trabalho melhor?"},
        "love": {"when": "Quando é minha melhor janela para o amor?",
                 "how": "O que ajuda o amor a crescer para mim agora?",
                 "now": "Como está minha vida amorosa agora?",
                 "why": "Que padrão eu repito no amor?"},
        "family": {"when": "Quando a pressão em casa alivia?",
                   "how": "Como lido com a tensão em casa agora?",
                   "now": "Como está minha vida familiar este ano?",
                   "why": "O que esta fase em casa está me pedindo?"},
        "health": {"when": "Quando minha energia melhora?",
                   "how": "Qual prática diária combina comigo agora?",
                   "now": "No que devo focar para minha saúde este ano?",
                   "why": "O que está drenando minha energia agora?"},
        "place": {"when": "Quando é um bom momento para comprar ou mudar?",
                  "how": "O mercado imobiliário combina com meu mapa?",
                  "now": "Onde meu mapa me apoia melhor?",
                  "why": "Por que não me sinto em casa onde estou?"},
        "speculation": {"when": "Quando abre minha próxima janela de ganhos não trabalhados?",
                        "how": "É um momento seguro para arriscar ou devo esperar?",
                        "now": "Qual dia desta semana é melhor para mim?",
                        "why": "O que alimenta minha vontade de arriscar?"},
        "spiritual": {"when": "Quando é minha janela espiritual mais forte?",
                      "how": "Como acalmo minha mente este mês?",
                      "now": "Qual prática combina mais comigo agora?",
                      "why": "O que esta fase está me ensinando?"},
        "day": {"now": "Como está amanhã?",
                "when": "Qual é o melhor horário do dia para mim hoje?",
                "how": "O que devo evitar hoje?",
                "wide": "Como está minha semana?"},
        "general": {"when": "Quando abre minha próxima janela forte?",
                    "how": "O que este mês está me pedindo?",
                    "now": "Como está meu dinheiro agora?",
                    "why": "Do que se trata esta fase da minha vida?"},
    },
}

# [love-no-assumed-partner 2026-10-04] the default love questions fit a single reader
# too; the partner versions only when the question itself names a partner.
_Q_PARTNERED = {
    "en": {"how": "What should I watch for with my partner?", "now": "How compatible are we?"},
    "hi": {"how": "Apne partner ke saath mujhe kis cheez ka dhyan rakhna chahiye?",
           "now": "Hum kitne compatible hain?"},
    "es": {"how": "¿Qué debo cuidar con mi pareja?", "now": "¿Qué tan compatibles somos?"},
    "pt": {"how": "O que devo cuidar com meu parceiro?", "now": "Quão compatíveis somos?"},
}
_PARTNER = re.compile(r"(?i)\b(partner|husband|wife|spouse|boyfriend|girlfriend|fianc[eé]e?|married|"
                      r"marriage|we|us|our|pareja|esposo|esposa|novi[oa]|marido|casad[oa]s?|matrimonio|"
                      r"parceir[oa]|namorad[oa]|casamento|pati|patni|biwi|shaadi|gf|bf)\b")


# WhatsApp list titles (24-char cap): name the KIND of next step instead of
# truncating the question ("Which day this week is…"); the full question rides
# as the row's description.
_LANE_TITLE = {
    "en": {"when": "⏳ Timing", "how": "🪔 What helps", "now": "📍 Where I stand",
           "why": "🔍 Go deeper", "wide": "🔭 Bigger picture"},
    "hi": {"when": "⏳ Timing", "how": "🪔 Kya madad karega", "now": "📍 Abhi kahan hoon",
           "why": "🔍 Gehraai se", "wide": "🔭 Badi tasveer"},
    "es": {"when": "⏳ Momento", "how": "🪔 Qué ayuda", "now": "📍 Dónde estoy",
           "why": "🔍 Más a fondo", "wide": "🔭 Panorama"},
    "pt": {"when": "⏳ Momento", "how": "🪔 O que ajuda", "now": "📍 Onde estou",
           "why": "🔍 Mais a fundo", "wide": "🔭 Panorama"},
}
_AREA = {
    "en": {"money": "Money", "career": "Career", "business": "Business", "love": "Love",
           "family": "Family", "health": "Health", "spiritual": "Inner life"},
    "hi": {"money": "Paisa", "career": "Career", "business": "Business", "love": "Pyaar",
           "family": "Parivaar", "health": "Sehat", "spiritual": "Mann"},
    "es": {"money": "Dinero", "career": "Carrera", "business": "Negocio", "love": "Amor",
           "family": "Familia", "health": "Salud", "spiritual": "Vida interior"},
    "pt": {"money": "Dinheiro", "career": "Carreira", "business": "Negócio", "love": "Amor",
           "family": "Família", "health": "Saúde", "spiritual": "Vida interior"},
}
OWN = {
    "en": ("✍️ Ask your own", "Type anything on your mind — I'll read it from your chart."),
    "hi": ("✍️ Apna sawaal", "Jo bhi mann mein hai likhiye — main aapke chart se padhunga."),
    "es": ("✍️ Escribe la tuya", "Escribe lo que tengas en mente — lo leo desde tu carta."),
    "pt": ("✍️ Escreva a sua", "Escreva o que estiver na sua mente — eu leio pelo seu mapa."),
}

# ── lane of the question just asked (EN / ES / PT / Hinglish) ──
_WHY = re.compile(r"(?i)\bwhy\b|\bwhat does (this|it|that) mean\b|\bwhat is (this|it) (all )?about\b"
                  r"|\bpor ?qu[eé]\b|\bpor que\b|\bo que significa\b|\bqu[eé] significa\b|\bky[ou]n\b")
_WHEN = re.compile(r"(?i)\bwhen\b|\bwhich (day|date|month|week)\b|\bhow (long|soon)\b|\buntil\b"
                   r"|\bcu[aá]ndo\b|\bqu[eé] d[ií]a\b|\bhasta cu[aá]ndo\b|\bquando\b|\bqual dia\b"
                   r"|\bat[eé] quando\b|\bkab\b|\bkaun sa din\b|\bkitne din\b")
_HOW = re.compile(r"(?i)\bhow (do|can|should|to|would|could) i\b|\bhow to\b|\bshould i\b"
                  r"|\bwhat (should|can) i do\b|\bwhat do i do\b|\bc[oó]mo (puedo|hago|debo|manejo|protejo|mantengo)\b"
                  r"|\bdebo\b|\bqu[eé] hago\b|\bcomo (posso|fa[cç]o|devo|lido|protejo|mantenho)\b|\bdevo\b"
                  r"|\bo que fa[cç]o\b|\bkaise\b|\bkya karun\b|\bkya mujhe\b")
_NOW = re.compile(r"(?i)\bhow(?:'s| is| are| does)\b|\bwhat(?:'s| is) my\b|\bc[oó]mo (est[aá]|va|se ve)\b"
                  r"|\bcomo (est[aá]|vai)\b|\bkaisa\b|\bkaisi\b")
# distinct-marker count, never everyday words alone ([[whatsapp-language-and-prashna-optin]])
_DISTRESS = re.compile(r"(?i)\b(stuck|anxious|anxiety|worried|worry|scared|afraid|lost|overwhelmed|"
                       r"hopeless|frustrated|exhausted|confused|desperate|atascad[oa]|estancad[oa]|"
                       r"ansios[oa]|preocupad[oa]|miedo|perdid[oa]|agobiad[oa]|travad[oa]|preso|"
                       r"com medo|perdid[oa]|sobrecarregad[oa]|pareshan|tension|ghabra\w*|atka\w*|"
                       r"dar lag\w*)\b")


def asked_lane(question: str):
    q = question or ""
    for lane, rx in (("why", _WHY), ("when", _WHEN), ("how", _HOW), ("now", _NOW)):
        if rx.search(q):
            return lane
    return None


def is_distressed(question: str) -> bool:
    return bool(_DISTRESS.search(question or ""))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _lang(language: str) -> str:
    l = (language or "en").lower()
    # [hi 2026-10-07] the internal "hi" tables are ROMAN-script Hinglish. Devanagari "hi" takes the
    # English pool; Ask's Devanagari guard translates the chips (and drops any it cannot).
    if l in ("hinglish", "hi-latn"):
        return "hi"
    return "en" if l[:2] == "hi" else (l[:2] if l[:2] in _Q else "en")


def pick(bucket: str, question: str, language: str = "en", answered_when: bool = False,
         avoid_words: tuple = (), k: int = 3) -> list:
    """[{q, lane, title}] — the next questions for this answer, best first."""
    lang = _lang(language)
    table = _Q[lang]
    pool = table.get(bucket) or table["general"]
    if bucket == "love" and _PARTNER.search(question or ""):
        pool = {**pool, **_Q_PARTNERED[lang]}
    lane = asked_lane(question)
    order = DISTRESS_ORDER if is_distressed(question) else ORDER[lane]
    covered = {lane} | ({"when"} if answered_when and lane != "when" else set())
    if bucket == "day":
        # today ≠ tomorrow: a day read leads on tomorrow → best hour → the week; the
        # caller's avoid_words drop whichever of those was just asked
        order, covered = DAY_ORDER, set()
    ranked = ([l for l in order if l in pool and l not in covered]
              + [l for l in order if l in pool and l in covered])
    qn = _norm(question)

    def ok(q):
        ql = q.lower()
        return _norm(q) != qn and not any(w in ql for w in avoid_words)

    titles = _LANE_TITLE[lang]
    out = [{"q": pool[l], "lane": l, "title": titles[l]} for l in ranked if ok(pool[l])]
    target = BRIDGE.get(bucket)
    if target and target in table and len(out) >= 2:
        bq = table[target]["now"]
        if ok(bq) and all(_norm(bq) != _norm(o["q"]) for o in out):
            out = out[:2] + [{"q": bq, "lane": "bridge",
                              "title": "↔ " + _AREA[lang].get(target, target.title())}]
    if not out:   # everything filtered — never return nothing
        out = [{"q": pool[l], "lane": l, "title": titles[l]} for l in ranked][:2]
    return out[:k]


# [astrologer-voice 2026-10-10] the follow-ups used to read like an advisor's ("Should I concentrate or
# diversify?", "Which profession fits me best?"). They are now what a client asks an astrologer: the
# period, the timing, what the chart shows, what helps. Chips already sent keep their topic when tapped.
_LEGACY = {
    "choice": [
        "Como protejo meu caixa enquanto decido?",
        "Faisla karte waqt apna cash kaise bachaun?",
        "Har option mein mere liye kaun sa role sahi hai?",
        "How do I protect my cash while I decide?",
        "Que papel combina mais comigo em cada opção?",
        "What role suits me best in each option?",
        "¿Cómo protejo mi efectivo mientras decido?",
        "¿Qué rol me conviene más en cada opción?"
    ],
    "money": [
        "Como está meu fluxo de caixa este mês?",
        "Devo concentrar ou diversificar?",
        "How is my cash flow this month?",
        "Is mahine mera cash flow kaisa hai?",
        "Kya ek jagah focus karun ya diversify karun?",
        "Paise ke saath mera kaun sa pattern baar baar aata hai?",
        "Que padrão se repete com meu dinheiro?",
        "Should I concentrate or diversify?",
        "What pattern keeps repeating with my money?",
        "¿Cómo está mi flujo de caja este mes?",
        "¿Debo concentrarme o diversificar?",
        "¿Qué patrón se repite con mi dinero?"
    ],
    "funding": [
        "Como está meu fluxo de caixa enquanto espero?",
        "De onde meu dinheiro tem mais chance de vir?",
        "How is my cash flow while I wait?",
        "Intezaar ke dauran mera cash flow kaisa hai?",
        "Mera paisa kahan se aane ke zyada chance hain?",
        "Where is my money most likely to come from?",
        "¿Cómo está mi flujo de caja mientras espero?",
        "¿De dónde es más probable que venga mi dinero?"
    ],
    "career": [
        "Is business or a job a better fit for me?",
        "Kaun sa profession mere liye sabse sahi hai?",
        "Mere liye business behtar hai ya job?",
        "Qual profissão combina mais comigo?",
        "Um negócio ou um emprego combina mais comigo?",
        "Which profession fits me best?",
        "¿Me conviene más un negocio o un empleo?",
        "¿Qué profesión encaja mejor conmigo?"
    ],
    "business": [
        "Akele build karun ya partner ke saath?",
        "De onde virão meus primeiros clientes de verdade?",
        "Devo empreender sozinho ou com um sócio?",
        "Main asal mein kis tarah ka founder hoon?",
        "Mere pehle real customers kahan se aayenge?",
        "Que tipo de fundador eu sou, de verdade?",
        "Should I build alone or bring in a partner?",
        "What kind of founder am I, really?",
        "Where will my first real customers come from?",
        "¿De dónde vendrán mis primeros clientes reales?",
        "¿Debo emprender solo o con un socio?",
        "¿Qué tipo de fundador soy, de verdad?"
    ],
    "speculation": [
        "Como mantenho a especulação pequena e segura?",
        "How do I keep speculation small and safe?",
        "Speculation ko chhota aur safe kaise rakhun?",
        "¿Cómo mantengo la especulación pequeña y segura?"
    ]
}


def bucket_of(question: str):
    """The topic of one of OUR suggestions (a tapped chip keeps its thread), else None."""
    qn = _norm(question)
    if not qn:
        return None
    for bucket, old in _LEGACY.items():
        if any(_norm(q) == qn for q in old):
            return bucket
    for table in list(_Q.values()) + [{"love": v} for v in _Q_PARTNERED.values()]:
        for bucket, lanes in table.items():
            # "general" only repeats other topics' questions ("How is my money looking
            # right now?" is a money question), so it never claims one
            if bucket != "general" and any(_norm(q) == qn for q in lanes.values()):
                return bucket
    return None


def own_row(language: str) -> tuple:
    """(title, id, description) for the WhatsApp list's free-text row."""
    t, d = OWN[_lang(language)]
    return (t, "own", d)


_ASK_THIS = {"en": "💬 Ask this", "hi": "💬 Yeh poochiye", "es": "💬 Preguntar esto", "pt": "💬 Perguntar isso"}


def lane_title(question: str, language: str = "en") -> str:
    """A list-row title for a question with no known lane (e.g. welcome starters)."""
    lang = _lang(language)
    lane = asked_lane(question)
    return _LANE_TITLE[lang][lane] if lane else _ASK_THIS[lang]
