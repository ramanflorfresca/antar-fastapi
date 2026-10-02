"""
antar_engine/integrity_gate.py — last check on an answer before a reader sees it.

[integrity-gate 2026-10-02] Live answers shipped broken text that no single step
"wrote": ", Oct 5 is…", "Avoid, Oct 3", "until, then", "Oct 5 () is…". Each
came from a word-deleting filter running AFTER the model wrote a correct
sentence. The gate runs after every filter and checks two things:

  1. FRAGMENTS — orphan/double punctuation, empty brackets, a preposition left
     dangling before punctuation, leftover placeholders, unbalanced brackets.
  2. UNSUPPORTED DATES — every calendar date, month-year and clock time in the
     answer must appear in the grounding (what the engines computed and the
     narrator was given). A date the model invented is a hallucination.

If either fires, ONE small-model rewrite fixes grammar only (and drops an
unsupported date) under a strict contract: same language, same meaning, every
supported date/number kept, nothing added. The rewrite is accepted only if it
passes the same checks plus the caller's validator (jargon voice-gate) and keeps
a similar length. Otherwise a deterministic tidy runs. Never raises: a gate
failure must not cost the reader an answer.
"""
from __future__ import annotations

import json
import re
from typing import Awaitable, Callable, Optional

# ── fragment detection ─────────────────────────────────────────────────────
_DANGLING_WORDS = (
    # EN
    "until", "till", "by", "before", "after", "from", "on", "at", "in", "of",
    "for", "with", "to", "than", "between", "the", "a", "an", "avoid", "during",
    # ES / PT (words that essentially never sit right before a comma/period)
    "hasta", "desde", "del", "para", "con", "el", "los", "las", "durante", "até",
    "com", "pelo", "pela", "evita", "evite",
)
_NEVER_FINAL = ("until", "till", "from", "of", "than", "between", "the", "a", "an",
                "avoid", "hasta", "desde", "del", "para", "con", "el", "los", "las",
                "até", "com", "evita", "evite")
_FRAGMENT_RULES = (
    ("leading_punct", re.compile(r"^\s*[,;:.)\]]")),
    ("empty_brackets", re.compile(r"\(\s*\)|\[\s*\]")),
    ("double_punct", re.compile(r"[,;:]\s*[,;:.!?]")),
    ("space_before_punct", re.compile(r"\w\s+[,;:!?](?=\s|$)")),
    # before a comma/semicolon/colon: any of the dangling words
    ("dangling_word", re.compile(
        r"(?i)\b(" + "|".join(_DANGLING_WORDS) + r")\s*[,;:](?=\s|$)")),
    # before a full stop: only words that can never end a sentence
    # ("move on." / "the day after." are fine)
    ("dangling_word", re.compile(
        r"(?i)\b(" + "|".join(_NEVER_FINAL) + r")\s*[.!?](?=\s|$)")),
    ("placeholder", re.compile(r"\{[a-z_]+\}|\[[A-Z_]{2,}\]|\x00")),
    ("doubled_word", re.compile(r"(?i)\b(the|a|an|to|of|in|on|and|de|la|el|que)\s+\1\b")),
)


def fragment_issues(text: Optional[str]) -> list:
    if not isinstance(text, str) or not text.strip():
        return []
    out = list(dict.fromkeys(name for name, rx in _FRAGMENT_RULES if rx.search(text)))
    if text.count("(") != text.count(")"):
        out.append("unbalanced_brackets")
    return out


# ── date grounding ─────────────────────────────────────────────────────────
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    "ene": 1, "enero": 1, "febrero": 2, "fev": 2, "fevereiro": 2, "marzo": 3,
    "março": 3, "marco": 3, "abr": 4, "abril": 4, "mayo": 5, "maio": 5,
    "junio": 6, "junho": 6, "julio": 7, "julho": 7, "ago": 8, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "set": 9, "setembro": 9, "octubre": 10,
    "out": 10, "outubro": 10, "noviembre": 11, "novembro": 11, "dic": 12,
    "diciembre": 12, "dez": 12, "dezembro": 12,
}
_MON = "|".join(sorted((re.escape(m) for m in _MONTHS), key=len, reverse=True))
_RX_MON_DAY = re.compile(rf"(?i)\b({_MON})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?!\s*,?\s*\d{{4}}\b(?!\d))")
_RX_DAY_MON = re.compile(rf"(?i)\b(\d{{1,2}})(?:\s+de)?\s+({_MON})\b")
_RX_MON_YEAR = re.compile(rf"(?i)\b({_MON})\.?\s+(?:de\s+)?(\d{{4}})\b")
_RX_MON_DAY_YEAR = re.compile(rf"(?i)\b({_MON})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b")
_RX_RANGE = re.compile(rf"(?i)\b({_MON})\.?\s+(\d{{4}})\s*[–—-]\s*({_MON})\.?\s+(\d{{4}})\b")
_RX_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_RX_TIME = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")


def _date_tokens(text: str) -> set:
    """Normalised date facts: 'md:10-05', 'ym:2026-11', 't:22:47'."""
    out: set = set()
    if not isinstance(text, str) or not text:
        return out
    for mo in _RX_MON_DAY_YEAR.finditer(text):
        m = _MONTHS[mo.group(1).lower()]
        out.add(f"md:{m:02d}-{int(mo.group(2)):02d}")
        out.add(f"ym:{mo.group(3)}-{m:02d}")
    for mo in _RX_MON_DAY.finditer(text):
        d = int(mo.group(2))
        if 1 <= d <= 31:
            out.add(f"md:{_MONTHS[mo.group(1).lower()]:02d}-{d:02d}")
    for mo in _RX_DAY_MON.finditer(text):
        d = int(mo.group(1))
        if 1 <= d <= 31:
            out.add(f"md:{_MONTHS[mo.group(2).lower()]:02d}-{d:02d}")
    for mo in _RX_MON_YEAR.finditer(text):
        out.add(f"ym:{mo.group(2)}-{_MONTHS[mo.group(1).lower()]:02d}")
    for mo in _RX_ISO.finditer(text):
        out.add(f"md:{mo.group(2)}-{mo.group(3)}")
        out.add(f"ym:{mo.group(1)}-{mo.group(2)}")
    for mo in _RX_TIME.finditer(text):
        out.add(f"t:{int(mo.group(1)):02d}:{mo.group(2)}")
    return out


def unsupported_dates(text: str, grounding: str) -> list:
    """Date facts in `text` that the grounding never mentions. A month-day is
    supported if the grounding has that day, or (for a range like 'Nov 2026 –
    Jan 2027') if it falls inside a grounded month."""
    if not isinstance(text, str) or not text:
        return []
    have = _date_tokens(grounding)
    # Only a stated month WINDOW ("Nov 2026 – Jan 2027") covers any day inside it;
    # a specific date (2026-10-05) must not bless every other day that month.
    have_mm = {f"{_MONTHS[mo.group(1).lower()]:02d}"
               for mo in _RX_MON_YEAR.finditer(grounding or "")}
    # a stated range "Nov 2026 – Jan 2027" also covers the months in between
    for mo in _RX_RANGE.finditer(grounding or ""):
        a = int(mo.group(2)) * 12 + _MONTHS[mo.group(1).lower()] - 1
        b = int(mo.group(4)) * 12 + _MONTHS[mo.group(3).lower()] - 1
        for i in range(a, min(b, a + 24) + 1):
            have_mm.add(f"{i % 12 + 1:02d}")
    missing = []
    for tok in sorted(_date_tokens(text)):
        if tok in have:
            continue
        if tok.startswith("md:") and tok[3:5] in have_mm:
            continue          # a day inside a grounded month window
        missing.append(tok)
    return missing


# ── deterministic tidy (last resort) ───────────────────────────────────────
def tidy(text: Optional[str]) -> Optional[str]:
    if not isinstance(text, str):
        return text
    t = re.sub(r"\(\s*\)|\[\s*\]", "", text)
    t = re.sub(r"^\s*[,;:.)\]]+\s*", "", t)
    t = re.sub(r"([,;:])\s*[,;:]+", r"\1", t)
    t = re.sub(r"\s+([,;:.!?])", r"\1", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    if t[:1].islower():
        t = t[:1].upper() + t[1:]
    return t


# ── the gate ───────────────────────────────────────────────────────────────
_REWRITE_SYSTEM = (
    "You fix the final text of an answer before a reader sees it. You receive "
    "JSON fields. Return the SAME JSON keys with corrected text.\n"
    "RULES:\n"
    "1. Fix grammar and broken fragments only (stray commas, empty brackets, a "
    "word cut off before punctuation, half-finished phrases). Rejoin the "
    "sentence naturally.\n"
    "2. Keep the meaning, tone, language and roughly the length. Do NOT add any "
    "new facts, advice, dates, numbers or names.\n"
    "3. Keep every date, time and number that appears in ALLOWED_DATES exactly. "
    "If a date does NOT appear in ALLOWED_DATES, remove it and rephrase so the "
    "sentence still reads well (e.g. 'this week' instead of an invented day).\n"
    "4. Never mention planets, signs, houses, charts or astrology terms.\n"
    "5. Output JSON only."
)

RewriteFn = Callable[[str, str], Awaitable[Optional[str]]]


def _issues(fields: dict, grounding: str) -> dict:
    out = {}
    for k, v in fields.items():
        iss = fragment_issues(v) + [f"date:{d}" for d in unsupported_dates(v, grounding)]
        if iss:
            out[k] = iss
    return out


async def run_gate(fields: dict, grounding: str, language: str,
                   rewrite: Optional[RewriteFn] = None,
                   validator: Optional[Callable[..., list]] = None) -> tuple:
    """(fields, report). `fields` = {name: text}; None/empty values pass through.
    `rewrite(system, user) -> raw model text`; `validator(*texts) -> violations`."""
    fields = {k: v for k, v in (fields or {}).items()}
    report = {"issues": {}, "action": "clean"}
    try:
        live = {k: v for k, v in fields.items() if isinstance(v, str) and v.strip()}
        issues = _issues(live, grounding)
        report["issues"] = issues
        if not issues:
            return fields, report
        allowed = sorted(_date_tokens(grounding))
        if rewrite is not None:
            try:
                user = json.dumps({"language": language, "ALLOWED_DATES": allowed,
                                   "problems": issues, "fields": live}, ensure_ascii=False)
                raw = await rewrite(_REWRITE_SYSTEM, user)
                if raw and "{" in raw:
                    got = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
                    got = got.get("fields", got) if isinstance(got, dict) else {}
                    cand = {k: (got.get(k) if isinstance(got.get(k), str) else v)
                            for k, v in live.items()}
                    ok = not _issues(cand, grounding)
                    for k, v in live.items():
                        n = len(cand[k] or "")
                        if not (0.6 * len(v) <= n <= 1.4 * len(v) + 20):
                            ok = False
                        # every SUPPORTED date in the original must survive
                        keep = _date_tokens(v) - set(unsupported_dates(v, grounding))
                        if not keep <= _date_tokens(cand[k] or ""):
                            ok = False
                    if ok and validator is not None and validator(*cand.values()):
                        ok = False
                    if ok:
                        fields.update(cand)
                        report["action"] = "rewritten"
                        return fields, report
            except Exception as e:
                report["rewrite_error"] = str(e)[:200]
        for k in issues:
            fields[k] = tidy(fields[k])
        report["action"] = "tidied"
        report["after"] = _issues({k: fields[k] for k in issues}, grounding)
    except Exception as e:
        report["error"] = str(e)[:200]
    return fields, report
