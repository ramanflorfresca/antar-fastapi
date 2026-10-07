"""Point-of-delivery disclaimers for /ask answers.

[appstore-disclaimer 2026-10-05] Disclaimer copy existed in Terms (`s3c` "No
Professional Substitute"), the WhatsApp legal block, the marketing landing page
and `chartFood.disclaimer` — but the /ask payload carried **none**. So the four
most sensitive domains we answer (health, money, legal, fertility) were
delivered with no qualifier on the card the user actually reads.

Live example that triggered this, verbatim from production on 2026-10-05, for
"I keep getting sick, when will my health improve?":

    "For your health, in Ayurveda: brahmi or gotu kola, neem for the skin, and
     warm sesame-oil self-massage (abhyanga)."

Named substances, to someone reporting recurring illness, with nothing attached.
That is App Store Guideline 1.4.1 exposure and plain product liability, and a
disclaimer buried in Terms does not answer either.

Domain comes from the Ask concern when it is set, and is otherwise sniffed from
the answer text, because the health-remedy guarantee and the speculation policy
can both fire on a question whose concern resolved to something else
(e.g. concern=career, answer carries herbs).
"""

from __future__ import annotations

import re
from typing import Optional

__all__ = ["disclaimer_for", "DOMAINS"]

DOMAINS = ("health", "money", "legal", "fertility")


def _lang(language) -> str:
    """en | es | pt | hi — matches the rest of the engine's 4-language contract.

    Hinglish answers are romanised Hindi, so they take the 'hi' string; an
    English-only lookup here would be the same silent-i18n bug we have hit
    before (es/pt/Hinglish users getting English fallback copy).
    """
    l = str(language or "en").strip().lower()
    # [hi 2026-10-07] "hi" = Devanagari -> the "hindi" copy below; the legacy "hi" key
    # holds the Roman-script Hinglish copy and only Hinglish readers get it.
    if l in ("hinglish", "hi-latn") or l.startswith("hinglish"):
        return "hi"
    if l in ("hi", "hindi") or l.startswith("hi-") or l.startswith("hi_"):
        return "hindi"
    b = l.split("_")[0].split("-")[0][:2]
    return b if b in ("es", "pt") else "en"


# Substances / modalities the health answer can name. Kept in sync with the
# _HERBS tuple in main.py's health-remedy guarantee.
_HEALTH_RX = re.compile(
    r"\b(ashwagandha|triphala|brahmi|gotu\s*kola|abhyanga|guduchi|shatavari|"
    r"neem|turmeric|amla|dinacharya|ayurveda|sesame[- ]oil|herbs?|"
    r"supplements?|dosha|vata|pitta|kapha)\b", re.IGNORECASE)

# [disclaimer-false-positive 2026-10-06] The TEXT sniff below runs on the ANSWER, which is full of
# everyday words. Production put "not legal advice … Your lawyer runs the case" on a raise answer
# because it said "make your case with clear facts"; the same hazard sat in "hearing back",
# "concept", "invest time", "share your results", "portfolio of work", "loan officer".
# So the sniff keeps only phrases that essentially only occur in the sensitive domain; the
# QUESTION (and the Ask concern) is the primary signal, and it is not touched.
_MONEY_RX = re.compile(
    r"\b(speculat\w+|crypto\w*|casino|lottery|betting|gambl\w+|stock\s+market|day\s+trading|"
    r"mutual\s+funds?|outside\s+funding|raising\s+funding|funding\s+round)\b",
    re.IGNORECASE)

_LEGAL_RX = re.compile(
    r"\b(lawsuit|litigation|lawyer|attorney|tribunal|legal\s+(?:matter|case|dispute|action|battle)|"
    r"court\s+(?:case|date|hearing|battle|order)|in\s+court|being\s+sued|restraining\s+order|custody)\b",
    re.IGNORECASE)

_FERTILITY_RX = re.compile(
    r"\b(conceiv\w+|conception|pregnan\w+|fertilit\w+|ivf|miscarr\w+|trying\s+for\s+a\s+(?:child|baby))\b",
    re.IGNORECASE)

# Concern labels the Ask engine sets, mapped to a disclaimer domain.
_CONCERN_MAP = {
    "health": "health",
    "health_self": "health",
    "money": "money",
    "wealth": "money",
    "finance": "money",
    "speculation": "money",
    "legal": "legal",
    "children": "fertility",
    "fertility": "fertility",
    "family": "fertility",
}

# [disclaimer-honest-register 2026-10-05] The first cut wrote these in the
# DENIAL register — "Antar reads timing, not your body", "not a prediction of
# any outcome" — and every one of them contradicted the answer printed directly
# above it. Antar DOES read health from the chart (constitution, care, remedies)
# and DOES return a yes/no with a dated window on a legal question. A disclaimer
# that denies a shipped feature is worse than none: the reader sees the
# contradiction, and it is the same "we are not what we are" posture that the
# App Store metadata was just rewritten to drop.
#
# The honest boundary is not "we don't predict". It is:
#   this is a CHART reading, not professional advice, and not a guarantee.
# Own the prediction; bound the authority; name who to go to.
# [disclaimer-honest-register 2026-10-05] Two rewrites, both worth recording.
#
# 1. The first cut used the DENIAL register — "Antar reads timing, not your
#    body", "not a prediction of any outcome" — and each line contradicted the
#    answer printed directly above it. Antar DOES read health from the chart
#    (constitution, care, remedies) and DOES return a yes/no with a dated
#    window on a legal question. A disclaimer that denies a shipped feature is
#    worse than none.
# 2. The second cut said "a chart reading" — but "reading" is precisely the
#    horoscope-register word stripped out of answer bodies the same day
#    (_ASK_CHART_FIX). Naming the mechanic as computation instead of divination
#    is both more accurate and consistent with the store positioning
#    ("computed, not generated").
#
# Settled form: name the method (planetary positions + timing), bound the
# authority (not professional advice, not a guarantee), name who to go to.
# Own the prediction. Never deny the feature.
_TEXT = {
    "health": {
        "en": "An analysis of your planetary positions and timing — not a diagnosis, and not a "
              "guarantee. See a doctor about symptoms, and before you start or stop anything.",
        "es": "Un análisis de tus posiciones planetarias y su momento — no es un diagnóstico ni una "
              "garantía. Consulta a un médico ante cualquier síntoma, y antes de empezar o dejar algo.",
        "pt": "Uma análise das suas posições planetárias e do momento — não é diagnóstico nem "
              "garantia. Procure um médico diante de sintomas, e antes de começar ou parar algo.",
        "hi": "Yeh aapke grahon ki sthiti aur timing ka vishleshan hai — diagnosis nahi, aur guarantee "
              "bhi nahi. Takleef ho to doctor se milein, aur kuch shuru ya band karne se pehle bhi.",
    },
    "money": {
        "en": "An analysis of your planetary positions and timing — not financial advice, and not a "
              "guarantee of returns. Never risk money you can't afford to lose.",
        "es": "Un análisis de tus posiciones planetarias y su momento — no es asesoramiento financiero "
              "ni una garantía de rendimiento. Nunca arriesgues dinero que no puedas perder.",
        "pt": "Uma análise das suas posições planetárias e do momento — não é consultoria financeira "
              "nem garantia de retorno. Nunca arrisque dinheiro que você não pode perder.",
        "hi": "Yeh aapke grahon ki sthiti aur timing ka vishleshan hai — financial advice nahi, aur "
              "munafe ki guarantee bhi nahi. Utna paisa kabhi na lagayein jo aap kho nahi sakte.",
    },
    "legal": {
        "en": "An analysis of your planetary positions and timing — not legal advice, and not a "
              "guarantee of any result. Your lawyer runs the case.",
        "es": "Un análisis de tus posiciones planetarias y su momento — no es asesoramiento legal ni "
              "una garantía de resultado. Tu abogado lleva el caso.",
        "pt": "Uma análise das suas posições planetárias e do momento — não é orientação jurídica nem "
              "garantia de resultado. Quem conduz o caso é o seu advogado.",
        "hi": "Yeh aapke grahon ki sthiti aur timing ka vishleshan hai — legal advice nahi, aur kisi "
              "nateeje ki guarantee bhi nahi. Case aapke vakeel ka hai.",
    },
    "fertility": {
        "en": "An analysis of your planetary positions and timing — not a diagnosis, and not a "
              "guarantee. Only a doctor can give you a clinical answer about conceiving.",
        "es": "Un análisis de tus posiciones planetarias y su momento — no es un diagnóstico ni una "
              "garantía. Solo un médico puede darte una respuesta clínica sobre la concepción.",
        "pt": "Uma análise das suas posições planetárias e do momento — não é diagnóstico nem "
              "garantia. Só um médico pode dar uma resposta clínica sobre concepção.",
        "hi": "Yeh aapke grahon ki sthiti aur timing ka vishleshan hai — diagnosis nahi, aur guarantee "
              "bhi nahi. Garbhdharan ka clinical jawab sirf doctor hi de sakta hai.",
    },
}


# [hi 2026-10-07] Devanagari Hindi copy (same four domains, same stance as the English).
_TEXT["health"]["hindi"] = ("यह आपके ग्रहों की स्थिति और समय का विश्लेषण है — निदान नहीं, और कोई गारंटी भी नहीं। "
                           "कोई तकलीफ़ हो तो डॉक्टर से मिलिए, और कुछ भी शुरू या बंद करने से पहले भी।")
_TEXT["money"]["hindi"] = ("यह आपके ग्रहों की स्थिति और समय का विश्लेषण है — वित्तीय सलाह नहीं, और मुनाफ़े की गारंटी भी नहीं। "
                          "इतना पैसा कभी न लगाइए जिसे खोना आप सह न सकें।")
_TEXT["legal"]["hindi"] = ("यह आपके ग्रहों की स्थिति और समय का विश्लेषण है — कानूनी सलाह नहीं, और किसी नतीजे की गारंटी भी नहीं। "
                          "मुक़दमा आपके वकील का है।")
_TEXT["fertility"]["hindi"] = ("यह आपके ग्रहों की स्थिति और समय का विश्लेषण है — निदान नहीं, और कोई गारंटी भी नहीं। "
                              "गर्भधारण के बारे में चिकित्सकीय उत्तर केवल डॉक्टर ही दे सकता है।")


# [yesno-disclaimer 2026-10-05] What the person ASKED is the strongest domain signal.
# A Yes/No answer is a short timing line ("the timing is not aligned yet…") with
# no herb or court words in it, and its concern label is generic — so the text
# sniff below found nothing and "Will my health improve this year?" shipped with
# no disclaimer at all. Mirrors main.py's _is_health_q / _is_legal_q lists.
_Q_HEALTH = re.compile(
    r"(?i)my health|health issue|illness|\bsick\b|disease|my body|diagnos|surgery|hospital|"
    r"medical|recover|chronic|\bpain\b|\bache\b|immun|always tired|fatigue|wellness|"
    r"be healthy|\bheal|ailment|(an|my|the) operation\b|blood pressure|diabetes|anxiety|depress|cancer|"
    r"salud|enferm|dolor|saúde|doen[cç]a|sehat|bimar")
_Q_FERTILITY = re.compile(
    r"(?i)conceiv|pregnan|fertil|\bivf\b|miscarr|trying (for|to have) (a )?(baby|child)|"
    r"(have|having) a (baby|child)|embarazo|embarazada|gravidez|gr[aá]vida|garbh")
_Q_LEGAL = re.compile(
    r"(?i)lawsuit|\bcourt\b|\b(win|lose|winning|losing)\b[^.?!]{0,12}\bcase\b|"
    r"my (court|legal|lawsuit) case|being sued|\bsuing\b|\bsue\b|"
    r"litigation|(the|my|a) trial\b|court hearing|hearing date|legal settlement|"
    r"settlement (offer|talks|agreement|negotiation)|the judge|custody|restraining order|arbitration|"
    r"legal (case|matter|dispute|battle|trouble|action|fight)|demanda|juicio|processo|tribunal|"
    r"adalat|mukadma")
# [disclaimer-false-positive 2026-10-06] bare "my case" / "hearing" / "settlement" matched
# "make my case to my manager"; a funding / mortgage / debt question had no financial signal.
_Q_MONEY = re.compile(
    r"(?i)invest|\bstocks?\b|share market|shares in|crypto|bitcoin|forex|trading|lottery|lotto|"
    r"gambl|casino|poker|betting|\bbet\b|wager|mutual fund|\bloan\b|\bfunding\b|fundrais\w+|"
    r"raise (money|capital|funds)|venture capital|mortgage|borrow\w*|\bdebt\b|"
    r"inversi|invertir|investir|apuesta|aposta|loter")


def _domain(concern: Optional[str], blob: str, question: Optional[str] = None) -> Optional[str]:
    c = (concern or "").strip().lower()
    if c in _CONCERN_MAP:
        return _CONCERN_MAP[c]
    q = question or ""
    if q:
        # same precedence as the text sniff: health is the sharpest risk
        for dom, rx in (("health", _Q_HEALTH), ("fertility", _Q_FERTILITY),
                        ("legal", _Q_LEGAL), ("money", _Q_MONEY)):
            if rx.search(q):
                return dom
    # Content sniff — order matters: health substances are the sharpest risk,
    # and a money/legal word can appear incidentally in a health answer.
    if _HEALTH_RX.search(blob):
        return "health"
    if _FERTILITY_RX.search(blob):
        return "fertility"
    if _LEGAL_RX.search(blob):
        return "legal"
    if _MONEY_RX.search(blob):
        return "money"
    return None


def disclaimer_for(concern: Optional[str], *texts, language: str = "en",
                    question: Optional[str] = None) -> Optional[str]:
    """The disclaimer this answer must carry, or None.

    `concern` is the Ask concern label; `texts` are the user-visible answer
    fields (read, next, actions…). Returns one sentence in the answer's own
    language, to be rendered on the answer card — not appended into `read`,
    so the FE can style it as a disclaimer rather than as part of the answer.
    """
    blob = " ".join(str(t) for t in texts if t)
    if not blob.strip() and not concern and not question:
        return None
    dom = _domain(concern, blob, question)
    if not dom:
        return None
    return _TEXT[dom].get(_lang(language)) or _TEXT[dom]["en"]
