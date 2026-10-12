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

# ── a former partner, or a named person coming back ──────────────────────────
_EX_EN = r"my\s+ex(?:[- ]?(?:boyfriend|girlfriend|husband|wife|partner|fianc[eé]e?))?"
_REUNION = [
    # "my ex" only counts when the question asks whether they will act or feel something
    re.compile(r"\b" + _EX_EN + r"\b[^?]{0,40}\b(back|return\w*|text\w*|call\w*|reach\w*|contact\w*|messag\w*|miss\w*|want\w*|love\w*|think\w*|forgiv\w*|apolog\w*)\b", _I),
    re.compile(r"\b(back|return\w*|text\w*|call\w*|reach\w*|contact\w*|messag\w*|miss\w*|want\w*|love\w*|forgiv\w*)\b[^?]{0,30}\b" + _EX_EN + r"\b", _I),
    re.compile(r"\b(get|getting)\s+back\s+together\b|\bback\s+together\s+with\b|\btake\s+me\s+back\b", _I),
    re.compile(r"\b(will|would|does|do|is|are|can)\s+(he|she|they)\s+(ever\s+|really\s+)?(come|coming|return)\s+back\b", _I),
    re.compile(r"\b(mi|su)\s+ex(pareja|novi[oa])?\b[^?]{0,40}\b(volver|vuelv\w*|llam\w*|escrib\w*|extra[ñn]\w*|quiere|ama|piensa)\b|\bvolver[aá]?\b[^?]{0,20}\b(mi|su)\s+ex\b|\bvolver\s+con\s+(mi\s+ex|[eé]l|ella)\b|\bvolver[aá]\s+conmigo\b|\bvuelva\s+conmigo\b", _I),
    re.compile(r"\b(meu|minha)\s+ex\b[^?]{0,40}\b(voltar\w*|ligar\w*|lig[ao]\w*|escrever\w*|sente\w*|quer|ama|pensa)\b|\bvoltar\s+(comigo|pra\s+mim|para\s+mim)\b|\bvoltar[aá]\s+(comigo|pra\s+mim)\b", _I),
    re.compile(r"\b(mera|meri)\s+ex\b[^?]{0,40}\b(wapas|vapas|call|message|text|yaad|pyaar|baat)\b|\bwapas\s+aa\s*(ayega|ayegi|jayega|jayegi)\b|\bwapas\s+(ayega|ayegi)\b|\bvapas\s+(ayega|ayegi)\b", _I),
    re.compile(r"(मेरा|मेरी)\s*एक्स[^?]{0,30}(वापस|कॉल|मैसेज|प्यार)|वापस\s*(आएगा|आएगी|आ\s*जाएगा|आ\s*जाएगी)"),
]

# ── another person's feelings or private behaviour toward the asker ─────────
_FEELINGS = [
    re.compile(r"\b(does|do|did|is|will|would|can)\s+(he|she|they|my\s+crush|my\s+(boyfriend|girlfriend|husband|wife|partner|ex))\s+"
               r"(really\s+|still\s+|ever\s+|actually\s+|secretly\s+)?(love|like|miss|want|care|think|text|call|message|marry)\b[^?]{0,30}\b(me|us|about\s+me|of\s+me)\b", _I),
    re.compile(r"\b(does|do|will|would|is|did)\s+(he|she|they|my\s+crush|my\s+(boyfriend|girlfriend|husband|wife|partner))\s+"
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

_KINDS = (("reunion", _REUNION), ("feelings", _FEELINGS), ("health_event", _HEALTH))

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
    "health_event": {
        "en": "How is my health this year, and what should I protect and when?",
        "es": "¿Cómo está mi salud este año, y qué debo cuidar y cuándo?",
        "pt": "Como está minha saúde este ano, e o que devo proteger e quando?",
        "hinglish": "Is saal meri health kaisi hai, aur mujhe kya aur kab dhyan mein rakhna chahiye?",
        "hi": "इस साल मेरी सेहत कैसी है, और मुझे क्या और कब ध्यान में रखना चाहिए?",
    },
}


def classify(question: str) -> Optional[str]:
    """'reunion' | 'feelings' | 'health_event' | None."""
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
