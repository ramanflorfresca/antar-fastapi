"""
[profession-naming 2026-08-05] Extract the field/profession the user named in a
"when will my X rise" question, so the answer names THAT ("Your music is
well-supported" / "Tu música está bien apoyada") instead of a generic verdict
noun or a mis-routed "your business".

Doctrine (owner rule): we do NOT infer profession — people tell us. A question
like "when will my music rise" IS the disclosure: the field is music. This
module only fires on the explicit "my <field> <rise-verb>" pattern, so it never
guesses; a miss falls back to the existing generic behaviour (safe).

Public API:
    extract_rise_subject(question, language) -> Optional[str]   # the raw field noun
    to_possessive(noun, language)            -> str             # "tu música" / "your music"
"""
import re
from typing import Optional

# Rise / advancement verbs — the signal that "my X" is a thing the user wants
# to see grow (career/vocation-timing), not a decision they're weighing.
_RISE_EN = (
    r"(?:rise|rises|rising|risen|go(?:es|ing)? up|went up|take[s]? off|"
    r"taking off|took off|grow[s]?|growing|grew|pick[s]? up|picking up|"
    r"blow[s]? up|blowing up|break[s]? through|breaking through|broke through|"
    r"improve[s]?|improving|lift[s]? off|soar[s]?|soaring|climb[s]?|climbing|"
    r"expand[s]?|expanding|get[s]? big(?:ger)?|take off)"
)

# Spanish rise verbs (indicative + subjunctive stems). Order in Spanish is
# often verb-first ("cuando suba mi música"), so we match both orders.
_RISE_ES = (
    r"(?:sub[ae]n?|subir[aá]?|despeg(?:a|ue|ar)n?|crezc[ao]n?|crece[nr]?|"
    r"mejor[ae]n?|mejorar|arranc[ae]n?|arrancar|repunt[ae]n?|explot[ae]n?|"
    r"despunt[ae]n?|prosper[ae]n?|asciend[ae]n?|elev[ae]n?|creci[eó])"
)

_TRAIL_STOP_EN = {
    "is", "are", "will", "gonna", "going", "to", "up", "really", "finally",
    "ever", "now", "soon", "again", "a", "the", "my",
}
_TRAIL_STOP_ES = {
    "va", "van", "a", "ya", "por", "fin", "de", "verdad", "ahora", "pronto",
    "otra", "vez", "el", "la", "mi", "en", "este", "esta",
}


def _clean_noun(raw: str, es: bool) -> Optional[str]:
    x = re.sub(r"[^\w\sáéíóúñüÁÉÍÓÚÑÜ]", " ", raw or "", flags=re.UNICODE)
    x = re.sub(r"\s+", " ", x).strip()
    if not x:
        return None
    words = x.split()
    stop = _TRAIL_STOP_ES if es else _TRAIL_STOP_EN
    while words and words[-1].lower() in stop:
        words.pop()
    while words and words[0].lower() in stop:
        words.pop(0)
    n = " ".join(words).strip()
    # Keep it a tight noun phrase: 1–3 words, reasonable length.
    if not n or len(n) > 30 or len(n.split()) > 3:
        return None
    return n


def extract_rise_subject(question: str, language: str = "en") -> Optional[str]:
    """Return the field noun from a "my X <rise-verb>" question, else None.

    Examples:
        "when will my music rise"      -> "music"
        "cuando suba mi música"        -> "música"
        "is my restaurant taking off"  -> "restaurant"
        "when should I have this talk" -> None  (no rise verb / no "my X")
    """
    ql = (question or "").strip().lower()
    if not ql:
        return None
    es = (language or "en").lower().startswith("es")

    if es:
        # verb-first: "... suba mi música ..."
        m = re.search(_RISE_ES + r"\s+mi\s+([a-záéíóúñü][\w\sáéíóúñü]{0,28}?)"
                      r"(?:\?|\.|,|;|$|\s+(?:cuando|en|este|esta|el|la|para|otra)\b)", ql)
        if m:
            n = _clean_noun(m.group(1), True)
            if n:
                return n
        # noun-first: "... mi música suba ..."
        m = re.search(r"\bmi\s+([a-záéíóúñü][\w\sáéíóúñü]{0,28}?)\s+" + _RISE_ES, ql)
        if m:
            n = _clean_noun(m.group(1), True)
            if n:
                return n
        return None

    # English: "my X <rise-verb>" (allow filler between: to / will / is going to)
    m = re.search(r"\bmy\s+([a-z][\w\s]{0,28}?)\s+"
                  r"(?:to\s+|will\s+|is\s+going\s+to\s+|gonna\s+)?" + _RISE_EN, ql)
    if m:
        n = _clean_noun(m.group(1), False)
        if n:
            return n
    return None


def to_possessive(noun: str, language: str = "en") -> str:
    """'music' -> 'your music' / 'música' -> 'tu música'."""
    n = (noun or "").strip()
    if not n:
        return n
    es = (language or "en").lower().startswith("es")
    return f"tu {n}" if es else f"your {n}"
