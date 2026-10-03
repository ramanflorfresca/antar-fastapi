"""
antar_engine/question_forms.py — HOW a question is asked, in EN / ES / PT /
Hinglish, for every phase of life. One shared lexicon instead of word lists
scattered across the code.

[question-forms 2026-10-03] Owner: "add different verbs for all phases of life on
when, how, what, will, should, could, would — and the equivalents in ES/PT and
Hinglish". The understanding layer (understand.py) reads meaning with a model;
this module is the deterministic layer underneath it — the WhatsApp yes/no
detector, the fallback when the model is slow/unavailable, and the
"is this a question?" check used before a statement may update a profile.

Forms:
  when    timing                      kab / cuándo / quando
  how     how something goes          kaise / cómo / como
  what    what to do / what is        kya karun / qué / o que
  will    future yes/no               …hoga, …milega / voy a / vou
  should  advice / decision           …chahiye / debo, me conviene / devo, vale a pena
  could   possibility / ability       …sakta / podría, es posible / poderia, é possível
  would   hypothetical                …hota / sería, qué pasaría / seria, o que aconteceria
  why · which · where · who
Yes/no-shaped forms: will, should, could, would (+ "is/am/are/do/does…" openers).
"""
from __future__ import annotations

import re
from typing import Optional

_F = {
    "when": [
        r"\bwhen\b", r"\bwhat time\b", r"\bhow soon\b", r"\bhow long (until|till|before|will)\b",
        r"\bby when\b", r"\bwhich (day|week|month|year|date)\b", r"\bbest time\b",
        r"\bcu[aá]ndo\b", r"\bpara cu[aá]ndo\b", r"\bqu[eé] d[ií]a\b", r"\ben qu[eé] (momento|mes|a[nñ]o|fecha)\b",
        r"\bcu[aá]nto (falta|tiempo)\b",
        r"\bquando\b", r"\bque dia\b", r"\bem que (momento|m[eê]s|ano|data)\b", r"\bat[eé] quando\b",
        r"\bquanto tempo\b",
        r"\bkab\b", r"\bkab tak\b", r"\bkis (din|mahine|saal|samay)\b", r"\bkitne din\b", r"\bkitna (time|samay)\b",
    ],
    "how": [
        r"\bhow (is|are|was|will|would|can|could|do|does|should|did|much|to)\b", r"\bhow'?s\b",
        r"\bcómo\b", r"^\s*¿?\s*como\b", r"\bqu[eé] tal\b",
        r"\bkaise\b", r"\bkaisa\b", r"\bkaisi\b", r"\bkis tarah\b",
    ],
    "what": [
        r"\bwhat\b(?! time)", r"\bwhat'?s\b",
        # Spanish "que" / PT "como" are everyday conjunctions — only the accented or
        # sentence-initial forms count as question words
        r"\bqu[eé]\b(?! d[ií]a| tal)(?<=é)|^\s*¿?\s*que\b", r"\bcu[aá]l es\b",
        r"\bo que\b", r"\bqual [eé]\b",
        r"\bkya karu+n?\b", r"\bkya karna\b", r"\bkya hai\b", r"\bkya hoga\b",
    ],
    "will": [
        r"^\s*¿?\s*will\b", r"\b(is it|am i|are we|are they|is (he|she)) going to\b", r"\bwill i\b",
        r"^\s*¿?\s*(voy|vas|va|vamos|van) a\b", r"\b(ser[aá]|habr[aá]|tendr[eé]|conseguir[eé]|lograr[eé]|"
        r"encontrar[eé]|ganar[eé]|llegar[aá]|vendr[aá])\b",
        r"^\s*(vou|vai|vamos|v[aã]o)\b", r"\b(ser[aá]|haver[aá]|terei|conseguirei|irei|ganharei|encontrarei|vir[aá])\b",
        r"\b(hoga|hogi|honge|milega|milegi|milenge|aayega|aayegi|ayega|ayegi|jayega|jayegi|banega|banegi|"
        r"chalega|chalegi|karega|karegi|rahega|rahegi|ho jayega|ho jayegi|lagega|lagegi)\b",
    ],
    "should": [
        r"^\s*¿?\s*(should|shall|ought)\b", r"\bshould (i|we)\b", r"\bis it (a good idea|wise|better|worth|right)\b",
        r"\bdo i (need|have) to\b",
        r"\b(debo|deber[ií]a|deber[ií]amos|tengo que|me conviene|nos conviene|vale la pena|es (buena idea|mejor|"
        r"recomendable))\b",
        r"\b(devo|deveria|dever[ií]amos|tenho que|vale a pena|[eé] (boa ideia|melhor|recomend[aá]vel))\b",
        r"\b(chahiye|karna chahiye|karu kya|karoon kya|sahi rahega|theek rahega|thik rahega|accha rahega)\b",
    ],
    "could": [
        r"^\s*¿?\s*(could|can|may|might)\b", r"\b(is it possible|is there a chance|any chance)\b",
        r"\b(puedo|podr[ií]a|podr[eé]|podemos|es posible|se puede|hay (alguna )?posibilidad)\b",
        r"\b(posso|poderia|poderei|podemos|[eé] poss[ií]vel|d[aá] (para|pra)|h[aá] (alguma )?chance)\b",
        r"\b(sakta|sakti|sakte|ho sakta|ho sakti|mumkin|sambhav)\b",
    ],
    "would": [
        r"^\s*¿?\s*would\b", r"\bwhat would\b", r"\bwould (it|i|we|that)\b", r"\bwhat if\b",
        r"\b(ser[ií]a|habr[ií]a|qu[eé] pasar[ií]a|y si)\b",
        r"\b(seria|teria|o que aconteceria|e se)\b",
        r"\b(hota|hoti|hote|agar)\b",
    ],
    "why": [r"\bwhy\b", r"\bhow come\b", r"\bpor qu[eé]\b", r"\bpor que\b", r"\bpor qu[eê]\b",
            r"\bkyun\b", r"\bkyon\b", r"\bkyu\b", r"\bkis wajah\b"],
    "which": [r"\bwhich\b(?! (day|week|month|year|date))", r"\bcu[aá]l(es)?\b", r"\b(qual|quais)\b",
              r"\bkaunsa\b", r"\bkaunsi\b", r"\bkaun sa\b", r"\bkaun si\b"],
    "where": [r"\bwhere\b", r"\b(a)?d[oó]nde\b", r"\b(a)?onde\b", r"\bkahan\b", r"\bkidhar\b", r"\bkahaan\b"],
    "who": [r"\bwho\b", r"\bqui[eé]n(es)?\b", r"\bquem\b", r"\bkaun\b(?! ?(sa|si)\b)"],
}
FORMS = tuple(_F)
_RX = {k: re.compile("(?i)" + "|".join(v)) for k, v in _F.items()}

# "is/am/are/do/does/has…" openers are yes/no in English; ES/PT "es/está/hay/é/tem"
_YN_OPENERS = re.compile(
    r"(?i)^\s*¿?\s*(is|are|am|do|does|did|has|have|was|were|"
    r"es|est[aá]|hay|tengo|tiene|ser[aá]|"
    r"[eé]|est[aá]|tem|h[aá]|tenho|"
    r"kya)\b")
YES_NO_FORMS = frozenset({"will", "should", "could", "would"})
OPEN_FORMS = frozenset({"when", "how", "what", "why", "which", "where", "who"})


def detect(text: str) -> list:
    """Every form present, in FORMS order."""
    t = text or ""
    return [f for f in FORMS if _RX[f].search(t)]


def primary(text: str) -> Optional[str]:
    """The form that decides what kind of answer is wanted. An open word wins
    over a yes/no verb ('when will I…' is a WHEN question)."""
    found = detect(text)
    for f in ("why", "when", "where", "who", "which", "how", "what"):
        if f in found:
            return f
    for f in ("should", "will", "could", "would"):
        if f in found:
            return f
    return "will" if _YN_OPENERS.search(text or "") else None


def is_question(sentence: str) -> bool:
    """A question (or a request for one) rather than a statement."""
    s = (sentence or "").strip()
    if not s:
        return False
    if s.endswith("?") or s.startswith("¿"):
        return True
    p = primary(s)
    return p is not None and (p in OPEN_FORMS and _starts_with_form(s) or p in YES_NO_FORMS
                              and (_starts_with_form(s) or re.search(
                                  r"(?i)\b(hoga|hogi|milega|milegi|chahiye|sakta|sakti)\s*$", s)))


def _starts_with_form(s: str) -> bool:
    first = re.sub(r"^\s*¿?\s*", "", s).split(" ", 2)
    head = " ".join(first[:2]).lower()
    return any(_RX[f].match(head) for f in FORMS) or bool(_YN_OPENERS.match(s))


def intent(text: str) -> Optional[str]:
    """Fallback intent (understand.INTENTS vocabulary) when the model reading is
    unavailable: 'when' → when, 'how' → how, 'what' + should/do → what_to_do,
    'why' → why, 'which' → which, 'where'/'who' → where_who, yes/no forms → yes_no."""
    p = primary(text)
    if p is None:
        return None
    if p in YES_NO_FORMS and re.search(r"(?i)\b(or|ou|ya|either)\b|¿[^?]*\bo\b", text or ""):
        return "which"                       # "…alone or with a partner?" is a choice
    if p == "what":
        return "what_to_do" if re.search(r"(?i)\b(should|do|can|must|debo|deber[ií]a|hago|devo|fa[cç]o|karu|karun|karna)\b",
                                         text or "") else "open"
    return {"when": "when", "how": "how", "why": "why", "which": "which", "where": "where_who",
            "who": "where_who"}.get(p, "yes_no")


# Phases of life the forms are tested across (tests/test_question_forms.py).
LIFE_PHASES = ("studies", "first_job", "career", "business", "money", "debt", "love", "marriage",
               "separation", "children", "parents", "home", "relocation", "health", "legal",
               "purpose", "retirement", "later_life")
