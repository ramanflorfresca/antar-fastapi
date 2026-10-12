"""
antar_engine/window_guard.py

ONE window per answer, and never a window that starts in the past.

Two bugs, one module:
  • FORWARD-ONLY. A window that began months ago and is still open must read "now through <end>", never "late 2024 through late 2027".
    The data itself carried the past start ("The strongest partnership window opens around 2024-11") and the prompt only ASKED the model
    to clip it; the model sometimes didn't. clip_forward() makes it deterministic, at the source and again on the finished text.
  • SHARED WINDOW. An answer was assembling up to four different windows for one question (the old marriage-timing convergence window, the
    sub-period stretch, the event engine's window, a divorced two-window block). The event engine's window is the headline: the
    relationship facts are reconciled to it before the model sees them, and a sentence that still announces a conflicting "window" is
    dropped from the finished answer.

Pure; never raises; works on plain text (en). Day-level dates ("Oct 18–23", "Dec 19 through Feb 1") are never touched - they are calm days
and inner periods, a different thing from the headline window.
"""
from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, timedelta
from typing import Optional

_MON = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
        "november": 11, "december": 12}
_MONTH_NAMES = "Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
# one date token: "Nov 2026" | "late 2027" | "mid-2027" | "2027" | "2026-11"
_TOKEN = (r"(?:(?P<mon>" + _MONTH_NAMES + r")\.?,?\s+(?P<my>20\d\d)|"
          r"(?P<part>early|mid|late|end\s+of)[\s-]+(?:(?:the\s+)?year\s+)?(?P<py>20\d\d)|"
          r"(?P<iso>20\d\d)-(?P<im>0[1-9]|1[0-2])\b|"
          r"(?P<y>20\d\d))")
_T = re.compile(_TOKEN, re.I)
_CONN = r"(?:\s*[–—-]\s*|\s+(?:to|through|until|till|and)\s+)"
_RANGE = re.compile(r"(?:(?P<lead>from|between)\s+)?(?P<a>" + _TOKEN.replace("?P<", "?P<a_") + r")" + _CONN + r"(?P<b>"
                    + _TOKEN.replace("?P<", "?P<b_") + r")", re.I)
_SENT = re.compile(r"(?<=[.!?])\s+")
_PAST_MARK = re.compile(r"(?i)\b(since|was|were|had|last|ago|previous\w*|used\s+to|in\s+the\s+past|back\s+in|began|started|already\s+ended|ended)\b")
_FUTURE_MARK = re.compile(r"(?i)\b(opens?|window|will|upcoming|ahead|next|coming|expect\w*|arrives?|begins?\s+in|starts?\s+in)\b")


def _span(m, pre: str = "") -> tuple:
    """(start_date, end_date) a matched date token covers."""
    g = (lambda k: m.groupdict().get(pre + k))
    if g("mon"):
        mo, y = _MON[g("mon").lower().rstrip(".")], int(g("my"))
        return date(y, mo, 1), date(y, mo, monthrange(y, mo)[1])
    if g("part"):
        y, p = int(g("py")), g("part").lower()
        if p.startswith("early"):
            return date(y, 1, 1), date(y, 4, 30)
        if p == "mid":
            return date(y, 5, 1), date(y, 8, 31)
        return date(y, 9, 1), date(y, 12, 31)
    if g("iso"):
        y, mo = int(g("iso")), int(g("im"))
        return date(y, mo, 1), date(y, mo, monthrange(y, mo)[1])
    y = int(g("y"))
    return date(y, 1, 1), date(y, 12, 31)


def parse_label(label: str) -> Optional[tuple]:
    """'Nov 2026 – Apr 2027' -> (2026-11-01, 2027-04-30); a single token covers itself. None when it has no year-level date."""
    try:
        m = _RANGE.search(label or "")
        if m:
            return _span(m, "a_")[0], _span(m, "b_")[1]
        t = _T.search(label or "")
        return _span(t) if t else None
    except Exception:
        return None


def _now_range(m) -> str:
    """The text a range collapses to when its start has already passed: 'now through <end>'."""
    lead = (m.group("lead") or "").lower()
    end = m.group("b")
    if lead == "between":
        return f"between now and {end}"
    return f"from now through {end}" if lead == "from" else f"now through {end}"


def clip_forward(text: str, today: Optional[date] = None, keep_min: int = 2) -> str:
    """Forward-only. 'late 2024 through late 2027' -> 'now through late 2027' (the start has passed, the window is still open). A sentence
    that offers a window wholly in the past as something to come is dropped, never below keep_min sentences."""
    if not isinstance(text, str) or not text.strip():
        return text
    today = today or date.today()
    try:
        sents = [s for s in _SENT.split(text.strip()) if s.strip()]
        fixed, drops = [], []
        for s in sents:
            def _fix(m):
                a0, _a1 = _span(m, "a_")
                _b0, b1 = _span(m, "b_")
                return _now_range(m) if (a0 < today <= b1) else m.group(0)
            ns = _RANGE.sub(_fix, s)
            wholly_past = any(_span(m, "b_")[1] < today for m in _RANGE.finditer(ns))
            toks = list(_T.finditer(ns))
            single_past = (not _RANGE.search(ns)) and bool(toks) and all(_span(t)[1] < today for t in toks)
            fixed.append(ns)
            drops.append(bool((wholly_past or single_past) and _FUTURE_MARK.search(ns) and not _PAST_MARK.search(ns)))
        keep = [ns for ns, d in zip(fixed, drops) if not d]
        use = keep if (any(drops) and len(keep) >= keep_min) else fixed
        if use == sents:                       # nothing rewritten, nothing dropped: hand back the ORIGINAL text (line breaks and all)
            return text
        return " ".join(use)
    except Exception:
        return text


def drop_conflicting_window_sentences(text: str, canon_label: Optional[str], today: Optional[date] = None, slack_days: int = 92,
                                      keep_min: int = 2) -> str:
    """A sentence that announces a 'window' as a month/year range which does not sit with the headline window is dropped (two sentences
    must remain). Day-level dates and sentences without the word 'window' are left alone."""
    if not isinstance(text, str) or not text.strip() or not canon_label:
        return text
    today = today or date.today()
    try:
        cw = parse_label(canon_label)
        if not cw:
            return text
        lo, hi = cw[0] - timedelta(days=slack_days), cw[1] + timedelta(days=slack_days)
        sents = [s for s in _SENT.split(text.strip()) if s.strip()]
        keep = []
        for s in sents:
            bad = False
            if re.search(r"(?i)\bwindow\b", s):
                for m in _RANGE.finditer(s):
                    a0, b1 = _span(m, "a_")[0], _span(m, "b_")[1]
                    a0 = max(a0, today) if a0 < today <= b1 else a0
                    if a0 < lo or b1 > hi or b1 < lo or a0 > hi:
                        bad = True
            # "from now through September 2027" is a range with 'now'
            for m in re.finditer(r"(?i)\b(?:from\s+)?now\s+(?:through|to|until|till)\s+(?P<e>" + _TOKEN.replace("?P<", "?P<e_") + ")", s):
                if re.search(r"(?i)\bwindow\b", s):
                    _, e1 = _span(m, "e_")
                    if e1 > hi or e1 < lo:
                        bad = True
            if not bad:
                keep.append(s)
        if len(keep) == len(sents) or len(keep) < keep_min:
            return text
        return " ".join(keep)
    except Exception:
        return text


_TIMING_LINE = re.compile(r"(?m)^TIMING \(multiple methods converge\):.*$")
_STRETCH_LINE = re.compile(r"(?m)^(The next sub-period genuinely tied to partnership runs )")


def reconcile_relationship_block(block: str, canon_label: Optional[str]) -> str:
    """Before the model sees it: one headline window. The old convergence line is replaced by the headline; the sub-period stretch is
    marked as wider context; a rule forbids announcing a second 'window'."""
    if not isinstance(block, str) or not block.strip() or not canon_label or not parse_label(canon_label):
        return block
    out = _TIMING_LINE.sub(f"TIMING: the ONE headline window is {canon_label}. Name this window and no other.", block)
    out = _STRETCH_LINE.sub(r"(WIDER CONTEXT, not the headline window) \1", out)
    return (out.rstrip() + f"\nONE WINDOW: the headline window is {canon_label}. Do not announce any other date range as 'a window'. A longer "
            "sub-period may be called 'the wider stretch'; day-level dates are 'calm days' or 'the inner period'. Never name a start earlier "
            "than today: a window already under way is 'now through <end>'.")
