"""
antar_engine/timing_fidelity.py
================================
Narrator hard-binding for /api/v1/ask — launch item (c), 2026-06-05.

The deterministic convergence engine computes the ONLY timing window the
product may voice. The prompts instruct Claude to "NEVER invent dates",
but prompt instructions are not enforcement: live screenshots showed an
invented "June–Aug 2026" contradicting the engine. This module is the
enforcement layer — a post-generation scrub that removes any month/year
token from user-facing narration that does not match the deterministic
window labels.

Same philosophy as antar_engine/output_strips.py: Python is the last gate
before text reaches the frontend, never the model.

Public API:
    scrub_freelance_dates(text, allowed_labels) -> (clean_text, removed_tokens)

allowed_labels — any iterable of strings that may legitimately contain
dates (window_label, next_window_label, the yesno `timing` field). Every
"Mon YYYY – Mon YYYY" label is expanded so months INSIDE the window are
also allowed. With no labels (no window), every date token is scrubbed
and replaced with a neutral building-phase phrase.

No LLM calls. No network. Pure text.
"""

from __future__ import annotations

import re

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    # Spanish / Portuguese full names — narration is generated in EN and
    # localized afterwards, but scrub defensively in case ordering changes.
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
    "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "maio": 5,
    "junho": 6, "julho": 7, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}

# Longest-first so "september" wins over "sep".
_MONTH_ALT = "|".join(sorted(_MONTHS.keys(), key=len, reverse=True))

_PREP_WORDS = {
    "between", "from", "in", "by", "around", "until", "till", "through",
    "during", "before", "after", "hasta", "entre", "en", "desde", "para",
    "até", "ate", "em",
}
_PREP = r"(?:" + "|".join(sorted(_PREP_WORDS, key=len, reverse=True)) + r")"

# "June–Aug 2026", "June 2026 – Mar 2027", "June to August 2026",
# "junio a agosto de 2026", "between May and July 2026"
_RANGE_RE = re.compile(
    rf"(?:\b{_PREP}\s+)?\b({_MONTH_ALT})\.?\s*(?:(?:de\s+|of\s+)?(20\d\d))?"
    rf"(?:\s*[–—-]\s*|\s+(?:to|and|a|y|hasta|até|through|until)\s+)"
    rf"\b({_MONTH_ALT})\.?\s*,?\s*(?:de\s+|of\s+)?(20\d\d)\b",
    re.IGNORECASE,
)

# "August 2026", "Aug. 2026", "agosto de 2026"
_MONTH_YEAR_RE = re.compile(
    rf"(?:\b{_PREP}\s+)?\b({_MONTH_ALT})\.?,?\s+(?:de\s+|of\s+)?(20\d\d)\b",
    re.IGNORECASE,
)

# "Q3 2026"
_QUARTER_RE = re.compile(
    rf"(?:\b{_PREP}\s+)?\bQ[1-4]\s*(?:de\s+|of\s+)?(20\d\d)\b",
    re.IGNORECASE,
)

# "early 2027", "mid-2026", "late 2026", "summer 2026"
_SEASON_YEAR_RE = re.compile(
    rf"(?:\b{_PREP}\s+)?\b(?:early|mid|late|spring|summer|autumn|fall|winter)"
    rf"[\s-]*(20\d\d)\b",
    re.IGNORECASE,
)

# bare "2026" (runs LAST — allowed month-year tokens keep their year)
_BARE_YEAR_RE = re.compile(rf"(?:\b{_PREP}\s+)?\b(20\d\d)\b", re.IGNORECASE)

_NEUTRAL = "the months ahead"


def _allowed_sets(allowed_labels):
    """(month, year) pairs + years permitted to appear in narration.
    A two-date label ("Jun 2026 – Mar 2027") is expanded so every month
    inside the window is allowed — restating a month within the window is
    consistent, not freelancing."""
    pairs, years = set(), set()
    finder = re.compile(
        rf"\b({_MONTH_ALT})\.?,?\s+(?:de\s+|of\s+)?(20\d\d)\b", re.IGNORECASE)
    for label in allowed_labels or []:
        if not label:
            continue
        found = [(_MONTHS[m.lower()], int(y))
                 for m, y in finder.findall(str(label))]
        for m, y in found:
            pairs.add((m, y))
            years.add(y)
        if len(found) == 2:
            (m1, y1), (m2, y2) = found
            cur_y, cur_m, guard = y1, m1, 0
            while (cur_y, cur_m) <= (y2, m2) and guard < 60:
                pairs.add((cur_m, cur_y))
                years.add(cur_y)
                cur_m += 1
                if cur_m > 12:
                    cur_m, cur_y = 1, cur_y + 1
                guard += 1
    return pairs, years


def scrub_freelance_dates(text, allowed_labels=None):
    """Remove month/year tokens not present in (or inside) the allowed
    labels. Returns (clean_text, removed_tokens). Never raises; never
    empties the text — disallowed tokens become a neutral phrase."""
    if not text or not isinstance(text, str):
        return text, []
    try:
        pairs, years = _allowed_sets(allowed_labels)
        removed = []

        def _neutral_for(token):
            removed.append(token.strip())
            first = token.strip().split()[0].lower() if token.strip() else ""
            return ("in " + _NEUTRAL) if first in _PREP_WORDS else _NEUTRAL

        def _range_repl(m):
            m1 = _MONTHS.get((m.group(1) or "").lower())
            y1 = int(m.group(2)) if m.group(2) else int(m.group(4))
            m2 = _MONTHS.get((m.group(3) or "").lower())
            y2 = int(m.group(4))
            if (m1, y1) in pairs and (m2, y2) in pairs:
                return m.group(0)
            return _neutral_for(m.group(0))

        def _month_year_repl(m):
            mm = _MONTHS.get((m.group(1) or "").lower())
            yy = int(m.group(2))
            if (mm, yy) in pairs:
                return m.group(0)
            return _neutral_for(m.group(0))

        def _year_only_repl(m):
            if int(m.group(1)) in years:
                return m.group(0)
            return _neutral_for(m.group(0))

        out = _RANGE_RE.sub(_range_repl, text)
        out = _MONTH_YEAR_RE.sub(_month_year_repl, out)
        out = _QUARTER_RE.sub(_year_only_repl, out)
        out = _SEASON_YEAR_RE.sub(_year_only_repl, out)
        out = _BARE_YEAR_RE.sub(_year_only_repl, out)

        if removed:
            out = re.sub(r"\s{2,}", " ", out)
            out = re.sub(r"\s+([,.;:!?])", r"\1", out)
            out = re.sub(r"\(\s*\)", "", out)
            out = out.replace(f"{_NEUTRAL} {_NEUTRAL}", _NEUTRAL)
            out = out.replace(f"in {_NEUTRAL} in {_NEUTRAL}", f"in {_NEUTRAL}")
            out = out.strip()
        return out, removed
    except Exception:
        # Enforcement must never break the request path.
        return text, []
