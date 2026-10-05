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

_TEXT = {
    "health": {
        "en": "Not medical advice. Antar reads timing, not your body — talk to a "
              "doctor before starting or stopping anything, especially if symptoms persist.",
        "es": "No es consejo médico. Antar lee el momento, no tu cuerpo — consulta a un "
              "médico antes de empezar o dejar cualquier cosa, sobre todo si los síntomas continúan.",
        "pt": "Não é orientação médica. O Antar lê o momento, não o seu corpo — fale com um "
              "médico antes de começar ou parar qualquer coisa, principalmente se os sintomas persistirem.",
        "hi": "Yeh medical advice nahi hai. Antar timing padhta hai, aapka shareer nahi — kuch bhi "
              "shuru ya band karne se pehle doctor se baat karein, khaas kar agar takleef bani hui hai.",
    },
    "money": {
        "en": "Not financial advice. This is timing, not a forecast of returns — never "
              "commit money you cannot afford to lose, and take professional advice before you do.",
        "es": "No es asesoramiento financiero. Esto es momento, no una previsión de rendimientos — "
              "nunca comprometas dinero que no puedas permitirte perder, y consulta a un profesional antes.",
        "pt": "Não é consultoria financeira. Isto é momento, não previsão de retorno — nunca "
              "comprometa dinheiro que você não pode perder, e busque orientação profissional antes.",
        "hi": "Yeh financial advice nahi hai. Yeh timing hai, return ka anumaan nahi — utna paisa "
              "kabhi na lagayein jo aap kho nahi sakte, aur pehle kisi professional se salah lein.",
    },
    "legal": {
        "en": "Not legal advice, and not a prediction of any outcome. Antar reads timing only — "
              "your lawyer decides strategy.",
        "es": "No es asesoramiento legal ni una predicción del resultado. Antar solo lee el momento — "
              "la estrategia la decide tu abogado.",
        "pt": "Não é orientação jurídica nem previsão de resultado. O Antar lê apenas o momento — "
              "a estratégia é do seu advogado.",
        "hi": "Yeh legal advice nahi hai, aur na hi kisi nateeje ki bhavishyavani. Antar sirf timing "
              "padhta hai — strategy aapke vakeel ki hai.",
    },
    "fertility": {
        "en": "Not medical advice. Antar reads timing, not fertility — a doctor is the only "
              "place to get an answer about conceiving.",
        "es": "No es consejo médico. Antar lee el momento, no la fertilidad — solo un médico "
              "puede responder sobre la concepción.",
        "pt": "Não é orientação médica. O Antar lê o momento, não a fertilidade — só um médico "
              "pode responder sobre concepção.",
        "hi": "Yeh medical advice nahi hai. Antar timing padhta hai, fertility nahi — garbhdharan "
              "ke baare mein jawab sirf doctor hi de sakta hai.",
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
