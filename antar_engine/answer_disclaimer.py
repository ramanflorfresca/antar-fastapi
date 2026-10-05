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
    if l in ("hi", "hinglish") or l.startswith("hi"):
        return "hi"
    b = l.split("_")[0].split("-")[0][:2]
    return b if b in ("es", "pt") else "en"


# Substances / modalities the health answer can name. Kept in sync with the
# _HERBS tuple in main.py's health-remedy guarantee.
_HEALTH_RX = re.compile(
    r"\b(ashwagandha|triphala|brahmi|gotu\s*kola|abhyanga|guduchi|shatavari|"
    r"neem|turmeric|amla|dinacharya|ayurveda|sesame[- ]oil|herbs?|"
    r"supplements?|dosha|vata|pitta|kapha)\b", re.IGNORECASE)

_MONEY_RX = re.compile(
    r"\b(speculat\w+|invest\w+|stocks?|shares?|equit\w+|crypto\w*|trading|"
    r"loan|funding|mutual\s+funds?|portfolio|betting|lottery|casino)\b",
    re.IGNORECASE)

_LEGAL_RX = re.compile(
    r"\b(court|case|lawsuit|litigation|lawyer|counsel|attorney|settlement|"
    r"hearing|tribunal|legal\s+matter|verdict)\b", re.IGNORECASE)

_FERTILITY_RX = re.compile(
    r"\b(conceiv\w+|concept\w+|pregnan\w+|fertilit\w+|ivf|baby|"
    r"trying\s+for\s+a\s+child)\b", re.IGNORECASE)

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


def _domain(concern: Optional[str], blob: str) -> Optional[str]:
    c = (concern or "").strip().lower()
    if c in _CONCERN_MAP:
        return _CONCERN_MAP[c]
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


def disclaimer_for(concern: Optional[str], *texts, language: str = "en") -> Optional[str]:
    """The disclaimer this answer must carry, or None.

    `concern` is the Ask concern label; `texts` are the user-visible answer
    fields (read, next, actions…). Returns one sentence in the answer's own
    language, to be rendered on the answer card — not appended into `read`,
    so the FE can style it as a disclaimer rather than as part of the answer.
    """
    blob = " ".join(str(t) for t in texts if t)
    if not blob.strip() and not concern:
        return None
    dom = _domain(concern, blob)
    if not dom:
        return None
    return _TEXT[dom].get(_lang(language)) or _TEXT[dom]["en"]
