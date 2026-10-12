"""Questions Antar must not answer as a prediction, rerouted to the asker's decision.

[other-person 2026-10-12] Owner positioning (2026-10-10): Antar is decision intelligence.
Every answer is about what the asker faces, the risk, the move and its window. It never
predicts another person's feelings or behaviour, and it never forecasts a health event.

Three question kinds are rewritten into a decision question BEFORE routing:

  reunion       "Will my ex come back?"            -> whether and when to reach out
  feelings      "Does he love me?"                 -> how to handle it and when to talk
  health_event  "Will I have a health scare?"      -> what to protect, and when

The rewritten question goes through the normal Ask path (Yes/No becomes Explore, so there
is no hard yes/no on a third party and no verdict on a body), and the answer carries
`reframed = {kind, original}` so the app can say what it did.

Matching is regex only, EN / ES / PT / Hinglish / Hindi. English-only logic would silently
leave everyone else on the old behaviour. Patterns are deliberately narrow: a question
about a boss, a client or a deal must never be caught.
"""
import re
from typing import Optional

_I = re.IGNORECASE
_HE = r"(?:he(?:\s+or\s+she)?|she|they)"                 # "he or she" is how people type it when unsure
_MYP = r"my\s+(?:husband|wife|spouse|partner|boyfriend|girlfriend|fianc[eé]e?)(?:\s+or\s+(?:husband|wife|boyfriend|girlfriend))?"

# ── a former partner, or a named person coming back ──────────────────────────
_EX_EN = r"my\s+ex(?:[- ]?(?:boyfriend|girlfriend|husband|wife|partner|fianc[eé]e?))?"
_REUNION = [
    # "my ex" only counts when the question asks whether they will act or feel something
    re.compile(r"\b" + _EX_EN + r"\b[^?]{0,40}\b(back|return\w*|text\w*|call\w*|reach\w*|contact\w*|messag\w*|miss\w*|want\w*|love\w*|think\w*|forgiv\w*|apolog\w*)\b", _I),
    re.compile(r"\b(back|return\w*|text\w*|call\w*|reach\w*|contact\w*|messag\w*|miss\w*|want\w*|love\w*|forgiv\w*)\b[^?]{0,30}\b" + _EX_EN + r"\b", _I),
    re.compile(r"\b(get|getting)\s+back\s+together\b|\bback\s+together\s+with\b|\btake\s+me\s+back\b", _I),
    re.compile(r"\b(will|would|does|do|is|are|can)\s+" + _HE + r"\s+(ever\s+|really\s+)?(come|coming|return)\s+back\b", _I),
    re.compile(r"\b(mi|su)\s+ex(pareja|novi[oa])?\b[^?]{0,40}\b(volver|vuelv\w*|llam\w*|escrib\w*|extra[ñn]\w*|quiere|ama|piensa)\b|\bvolver[aá]?\b[^?]{0,20}\b(mi|su)\s+ex\b|\bvolver\s+con\s+(mi\s+ex|[eé]l|ella)\b|\bvolver[aá]\s+conmigo\b|\bvuelva\s+conmigo\b", _I),
    re.compile(r"\b(meu|minha)\s+ex\b[^?]{0,40}\b(voltar\w*|ligar\w*|lig[ao]\w*|escrever\w*|sente\w*|quer|ama|pensa)\b|\bvoltar\s+(comigo|pra\s+mim|para\s+mim)\b|\bvoltar[aá]\s+(comigo|pra\s+mim)\b", _I),
    re.compile(r"\b(mera|meri)\s+ex\b[^?]{0,40}\b(wapas|vapas|call|message|text|yaad|pyaar|baat)\b|\bwapas\s+aa\s*(ayega|ayegi|jayega|jayegi)\b|\bwapas\s+(ayega|ayegi)\b|\bvapas\s+(ayega|ayegi)\b", _I),
    re.compile(r"(मेरा|मेरी)\s*एक्स[^?]{0,30}(वापस|कॉल|मैसेज|प्यार)|वापस\s*(आएगा|आएगी|आ\s*जाएगा|आ\s*जाएगी)"),
]

# ── another person's feelings or private behaviour toward the asker ─────────
_FEELINGS = [
    re.compile(r"\b(does|do|did|is|will|would|can)\s+(" + _HE + r"|my\s+crush|my\s+(boyfriend|girlfriend|husband|wife|partner|ex))\s+"
               r"(really\s+|still\s+|ever\s+|actually\s+|secretly\s+)?(love|like|miss|want|care|think|text|call|message|marry)\b[^?]{0,30}\b(me|us|about\s+me|of\s+me)\b", _I),
    re.compile(r"\b(does|do|will|would|is|did)\s+(" + _HE + r"|my\s+crush|my\s+(boyfriend|girlfriend|husband|wife|partner))\s+"
               r"(ever\s+|really\s+|still\s+)?(propose|cheat|cheating|lying|leave\s+me|loves?\s+me)\b", _I),
    re.compile(r"\b(love|likes?|misses|wants|cares?\s+about)\s+me\b[^?]{0,10}\?", _I),
    re.compile(r"\b(me\s+(ama|quiere|extra[ñn]a|piensa\s+en\s+m[ií])|(est[aá]\s+)?enamorad[oa]\s+de\s+m[ií]|le\s+gusto)\b", _I),
    re.compile(r"\b(me\s+ama|gosta\s+de\s+mim|sente\s+(minha\s+)?falta|est[aá]\s+apaixonad[oa]\s+por\s+mim|pensa\s+em\s+mim)\b", _I),
    re.compile(r"\b(mujhse\s+(pyaar|pyar|mohabbat|prem)|mujhe\s+(pyaar|pyar)\s+kar|mujhse\s+shaadi)\b", _I),
    re.compile(r"मुझसे\s*(प्यार|प्रेम|शादी)|मुझे\s*प्यार\s*कर"),
]

# ── a forecast of illness, accident or death ─────────────────────────────────
_HEALTH = [
    re.compile(r"\b(will|am|could|might|do|shall)\s+i\s+(ever\s+|really\s+|actually\s+)?(have|get|suffer|face|develop|catch|need|go\s+through|end\s+up)\b[^?]{0,40}"
               r"\b(health\s+scare|serious\s+illness|sick|ill|illness|disease|cancer|surgery|operation|accident|heart\s+attack|stroke|hospital|diagnos\w*|injur\w*)\b", _I),
    re.compile(r"\b(when|how)\s+(will|am)\s+i\s+(going\s+to\s+)?die\b|\bwill\s+i\s+die\b|\bhow\s+long\s+(will|am)\s+i\s+(going\s+to\s+)?live\b|\blife\s?span\b|\bwhen\s+is\s+my\s+death\b", _I),
    re.compile(r"\b(tendr[eé]|voy\s+a\s+tener|sufrir[eé])\b[^?]{0,40}\b(c[aá]ncer|enfermedad|operaci[oó]n|cirug[ií]a|accidente|infarto|problema\s+de\s+salud)\b|\bcu[aá]ndo\s+(voy\s+a\s+)?morir[eé]?\b|\bcu[aá]nto\s+(voy\s+a\s+)?vivir[eé]?\b", _I),
    re.compile(r"\b(vou\s+(ter|ficar)|terei|vou\s+sofrer)\b[^?]{0,40}\b(c[aâ]ncer|doen[cç]a|doente|cirurgia|acidente|infarto|problema\s+de\s+sa[uú]de)\b|\bquando\s+(vou\s+)?morrer\b|\bquanto\s+tempo\s+(vou\s+)?viver\b", _I),
    re.compile(r"\b(bimar|bimaar)\s+(padunga|padungi|hounga|hoongi)\b|\bkab\s+(marunga|marungi)\b|\bkitna\s+(jiyunga|jiyungi)\b|\bcancer\s+(hoga|ho\s+jayega)\b|\boperation\s+(hoga|karna\s+padega)\b", _I),
    re.compile(r"कब\s*मरूँ?गा|कब\s*मरूँ?गी|कितना\s*जिऊँ?गा|बीमार\s*(पड़ूँ?गा|पड़ूँ?गी|हो\s*जाऊँ?गा)"),
]


# ── suspicion about a partner: cheating, a third person ──────────────────────
_TRUST = [
    re.compile(r"\b(is|are|was|were|will|does|do|did)\s+(?:" + _HE + r"|" + _MYP + r")\s+(?:be\s+|being\s+)?(?:cheat\w*|having\s+an?\s+affair|unfaithful|lying|seeing\s+someone(?:\s+else)?|hiding\s+something)\b", _I),
    re.compile(r"\b" + _MYP + r"\b[^?]{0,25}\b(affair|cheat\w*|unfaithful)\b", _I),
    re.compile(r"\b(?:is\s+there\s+(?:a|another)\s+)?(?:third\s+(?:person|party)|other\s+(?:woman|man|person))\b[^?]{0,30}\b(relationship|marriage|between|us|our)\b", _I),
    re.compile(r"\b(me\s+(?:es\s+infiel|enga[ñn]a|est[aá]\s+enga[ñn]ando)|(?:mi\s+(?:esposo|esposa|pareja|marido))\b[^?]{0,25}\b(infiel|aventura|amante)|tercera\s+persona)\b", _I),
    re.compile(r"\b(me\s+(?:trai|est[aá]\s+traindo|engana)|terceira\s+pessoa|caso\s+extraconjugal)\b", _I),
    re.compile(r"\b(dhokha\s+de\s+(?:raha|rahi)|cheat\s+kar\s+(?:raha|rahi)|teesra\s+(?:insaan|vyakti|shakhs))\b", _I),
]

# ── the asker's own secret relationship / affair ─────────────────────────────
_AFFAIR = [
    re.compile(r"\b(am\s+i\s+having\s+an?\s+affair|(?:will|would|can)\s+my\s+affair|my\s+affair\s+(?:partner|be\s+exposed)|affair\s+partner|secret\s+(?:relationship|affair|lover))\b", _I),
    re.compile(r"\b(tengo\s+una\s+aventura|mi\s+amante|relaci[oó]n\s+secreta)\b|\b(meu\s+amante|relacionamento\s+secreto|caso\s+extraconjugal)\b", _I),
]

# ── when another person will act toward the asker (call, contact, meet) ──────
_CONTACT = [
    re.compile(r"\b(will|when\s+will|when\s+would|does|do|is)\s+(?:" + _HE + r"|" + _MYP + r"|my\s+crush)\s+(?:be\s+)?(?:going\s+to\s+)?(?:call|contact|text|message|reach|ring|write|reply|respond|get\s+in\s+touch)\b[^?]{0,30}", _I),
    re.compile(r"\bwill\s+we\s+(?:meet|talk|speak|see\s+each\s+other|run\s+into\s+each\s+other)(?:\s+up|\s+again)?\s+(?:today|tonight|tomorrow|this\s+(?:week|month)|soon)\s*\?*\s*$", _I),
    re.compile(r"\b(me\s+(?:llamar[aá]|escribir[aá]|buscar[aá])|nos\s+(?:veremos|encontraremos)\b[^?]{0,20}\b(hoy|ma[ñn]ana|este\s+mes))\b", _I),
    re.compile(r"\b(vai\s+me\s+(?:ligar|chamar|procurar|escrever)|vamos\s+nos\s+(?:ver|encontrar)\b[^?]{0,20}\b(hoje|amanh[aã]|este\s+m[eê]s))\b", _I),
    re.compile(r"\b(call|message|contact|text)\s+(?:karega|karegi|karenge)\b|\bmilenge\b[^?]{0,15}\b(aaj|kal|is\s+mahine)\b", _I),
]

# ── what a former partner does next (marries, moves on) ──────────────────────
_EX_FUTURE = [
    re.compile(r"\b" + _EX_EN + r"\b[^?]{0,30}\b(marry|married|get\s+married|remarry|move\s+on|dating|date|someone\s+else|new\s+(?:partner|girlfriend|boyfriend|wife|husband))\b", _I),
    re.compile(r"\b(mi|su)\s+ex(?:pareja)?\b[^?]{0,30}\b(casar\w*|rehar\w*\s+su\s+vida|otra\s+persona)\b|\b(meu|minha)\s+ex\b[^?]{0,30}\b(casar\w*|outra\s+pessoa)\b", _I),
]

# ── looks, caste or religion of a future spouse — not a decision, not ours to forecast
_PARTNER_LOOKS = [
    re.compile(r"\bwhat\s+will\s+(?:my\s+)?(?:spouse|husband|wife|partner|future\s+(?:spouse|husband|wife|partner))\s+look\s+like\b", _I),
    re.compile(r"\b(?:my\s+)?(?:spouse|husband|wife|partner|future\s+(?:spouse|husband|wife|partner))\b[^?]{0,35}\b(caste|religion|race|ethnic\w*|colou?r|complexion|skin|height|tall|short|fair|dark|attractive|beautiful|handsome)\b", _I),
    re.compile(r"\bdifferent\s+(?:caste|religion)\b|\b(?:c[oó]mo\s+ser[aá]\s+(?:f[ií]sicamente\s+)?mi\s+(?:esposo|esposa|pareja))\b|\bcomo\s+ser[aá]\s+(?:fisicamente\s+)?(?:meu|minha)\s+(?:marido|esposa|parceir[oa])\b", _I),
]

_KINDS = (("reunion", _REUNION), ("feelings", _FEELINGS), ("health_event", _HEALTH),
          ("affair", _AFFAIR), ("trust", _TRUST), ("contact", _CONTACT),
          ("ex_future", _EX_FUTURE), ("partner_looks", _PARTNER_LOOKS))

# The decision the asker can actually act on. One sentence, so the normal Ask path reads it
# as an ordinary decision-and-timing question.
_REFRAME = {
    "reunion": {
        "en": "Is now a good time for me to reach out to a former partner, and how should I approach it?",
        "es": "¿Es buen momento para que yo contacte a una expareja, y cómo debería abordarlo?",
        "pt": "É um bom momento para eu procurar um ex-parceiro, e como devo abordar isso?",
        "hinglish": "Kya abhi apne purane partner se contact karne ka sahi time hai, aur mujhe ise kaise sambhalna chahiye?",
        "hi": "क्या अभी अपने पुराने साथी से संपर्क करने का सही समय है, और मुझे इसे कैसे संभालना चाहिए?",
    },
    "feelings": {
        "en": "How should I handle this relationship, and when is the right time to talk directly about where we stand?",
        "es": "¿Cómo debo manejar esta relación, y cuándo es el momento adecuado para hablar directamente de dónde estamos?",
        "pt": "Como devo lidar com esta relação, e quando é o momento certo para conversar diretamente sobre onde estamos?",
        "hinglish": "Mujhe is rishte ko kaise sambhalna chahiye, aur seedhi baat karne ka sahi time kab hai?",
        "hi": "मुझे इस रिश्ते को कैसे संभालना चाहिए, और सीधे बात करने का सही समय कब है?",
    },
    "trust": {
        "en": "How should I handle my doubts about trust in this relationship, and when is the right time to talk about it directly?",
        "es": "¿Cómo debo manejar mis dudas de confianza en esta relación, y cuándo es el momento adecuado para hablarlo directamente?",
        "pt": "Como devo lidar com minhas dúvidas de confiança nesta relação, e quando é o momento certo para falar disso diretamente?",
        "hinglish": "Is rishte mein bharose ke apne shak ko mujhe kaise sambhalna chahiye, aur seedhi baat karne ka sahi time kab hai?",
        "hi": "इस रिश्ते में भरोसे के अपने संदेह को मुझे कैसे संभालना चाहिए, और सीधे बात करने का सही समय कब है?",
    },
    "affair": {
        "en": "What decision am I facing about commitment and honesty in my relationships, and when is the right time to act on it?",
        "es": "¿Qué decisión enfrento sobre el compromiso y la honestidad en mis relaciones, y cuándo es el momento adecuado para actuar?",
        "pt": "Que decisão estou enfrentando sobre compromisso e honestidade nas minhas relações, e quando é o momento certo para agir?",
        "hinglish": "Apne rishton mein commitment aur imaandaari ko lekar mujhe kaunsa faisla lena hai, aur kab?",
        "hi": "अपने रिश्तों में प्रतिबद्धता और ईमानदारी को लेकर मुझे कौन सा फ़ैसला लेना है, और कब?",
    },
    "contact": {
        "en": "Should I be the one to reach out in this relationship, and when is the right time to do it?",
        "es": "¿Debería ser yo quien dé el primer paso en esta relación, y cuándo es el momento adecuado para hacerlo?",
        "pt": "Devo ser eu a dar o primeiro passo nesta relação, e quando é o momento certo para isso?",
        "hinglish": "Kya mujhe is rishte mein khud pehle contact karna chahiye, aur uska sahi time kab hai?",
        "hi": "क्या मुझे इस रिश्ते में खुद पहल करनी चाहिए, और उसका सही समय कब है?",
    },
    "ex_future": {
        "en": "How do I move forward from a former relationship, and what should I focus on now?",
        "es": "¿Cómo sigo adelante tras una relación pasada, y en qué debo enfocarme ahora?",
        "pt": "Como sigo em frente depois de um relacionamento passado, e no que devo me concentrar agora?",
        "hinglish": "Purane rishte se aage kaise badhun, aur ab mujhe kis par dhyan dena chahiye?",
        "hi": "पिछले रिश्ते से आगे कैसे बढ़ूँ, और अब मुझे किस पर ध्यान देना चाहिए?",
    },
    "partner_looks": {
        "en": "What kind of partner am I drawn to, and what do I need in a relationship for it to last?",
        "es": "¿Qué tipo de pareja me atrae, y qué necesito en una relación para que dure?",
        "pt": "Que tipo de parceiro me atrai, e o que preciso numa relação para que ela dure?",
        "hinglish": "Mujhe kis tarah ka partner pasand aata hai, aur rishta tikne ke liye mujhe kya chahiye?",
        "hi": "मुझे किस तरह का साथी पसंद आता है, और रिश्ता टिकने के लिए मुझे क्या चाहिए?",
    },
    "health_event": {
        "en": "How is my health this year, and what should I protect and when?",
        "es": "¿Cómo está mi salud este año, y qué debo cuidar y cuándo?",
        "pt": "Como está minha saúde este ano, e o que devo proteger e quando?",
        "hinglish": "Is saal meri health kaisi hai, aur mujhe kya aur kab dhyan mein rakhna chahiye?",
        "hi": "इस साल मेरी सेहत कैसी है, और मुझे क्या और कब ध्यान में रखना चाहिए?",
    },
}


def classify(question: str) -> Optional[str]:
    """'reunion' | 'feelings' | 'health_event' | 'trust' | 'affair' | 'contact' | 'ex_future' | 'partner_looks' | None."""
    q = (question or "").strip()
    if not q:
        return None
    for kind, rules in _KINDS:
        if any(rx.search(q) for rx in rules):
            return kind
    return None


def reframe(kind: str, language: str = "en") -> str:
    """The asker-decision version of a question of this kind, in `language`."""
    table = _REFRAME.get(kind) or {}
    return table.get(language) or table.get("en") or ""
