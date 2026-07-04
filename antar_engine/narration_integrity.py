"""
antar_engine/narration_integrity.py
===================================
Flag -> fallback narration guard (Cowork brief 2026-07-04).

Doctrine: NEVER delete a word out of a finished sentence. The three legal
moves are (1) a safe, grammar-preserving swap, (2) dropping a whole
sentence, (3) falling back to a caller-supplied line. In-place token
deletion is what produced "no strong confirms" and "a of wisdom" on live
surfaces.

Public API:
    guard_field(text, fallback, extra_banned=None) -> str
    clean_text(text, extra_banned=None) -> (str, list[str])
    has_broken_grammar(text) -> bool
    sentence_case(text) -> str
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from antar_engine.narration_validator import validate_narration

# -- Safe swaps: translation-only, grammar shape preserved -----------------
_SAFE_SWAPS = [
    (re.compile(r"\bin\s+your\s+blueprint\b", re.I), "in your makeup"),
    (re.compile(r"\byour\s+blueprint\b", re.I), "your makeup"),
    (re.compile(r"\bblueprint\b", re.I), "makeup"),
    (re.compile(r"\bwealth\s+combinations?\b", re.I), "income patterns"),
    (re.compile(r"\bthe\s+annual\s+setup\b", re.I), "this year's setup"),
    (re.compile(r"\bannual\s+setup\b", re.I), "this year's setup"),
    (re.compile(r"\b(one|a|an|the|another|this|that|each|every)\s+layer\b", re.I),
     lambda m: m.group(1) + " part of the picture"),
    (re.compile(r"\bnatal\s+chart\b", re.I), "birth details"),
    (re.compile(r"\bannual\s+chart\b", re.I), "yearly view"),
    (re.compile(r"\byour\s+relocated\s+chart\b", re.I), "your read for this place"),
    (re.compile(r"\brelocated\s+chart\b", re.I), "read for this place"),
    (re.compile(r"\bcurrent\s+dasha\b", re.I), "current chapter"),
    (re.compile(r"\bvarshphal\b", re.I), "yearly view"),
    (re.compile(r"\btransit\s+alerts?\b", re.I), "timing alerts"),
    (re.compile(r"\bsignal\s+floor\b", re.I), "baseline"),
]

# -- Internal vocabulary that survives swaps -> sentence must be dropped ---
_HARD_INTERNAL = re.compile(
    r"\b[\w-]+(?:\s+and\s+[\w-]+)?\s+(?:energy|layer|influence|signal|vibe)\b|"
    r"\b(?:blueprint|dasha|varshphal|lagna|natal)\b|"
    r"\b(?:AC|MC|DC|IC|ASC)\s+lines?\b|"
    r"\b\d{1,3}\s+out\s+of\s+\d{1,3}\b|\b\d{1,3}\s*/\s*56\b|"
    r"\b\d{1,3}\s?%",
    re.IGNORECASE,
)

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# -- Sentence-integrity patterns -------------------------------------------
# Determiner + bare modifier + finite verb: the missing-noun shape left by
# in-place deletion ("no strong confirms", "a steady holds").
_MISSING_NOUN = re.compile(
    r"\b(no|a|an|the|your|one|this|that|some|any)\s+"
    r"(strong|steady|clear|quiet|big|small|major|minor|new|real|good|deep|"
    r"slow|fast|hard|soft|firm|light)\s+"
    r"(confirms?|shows?|holds?|opens?|lands?|builds?|moves?|arrives?|"
    r"stands?|remains?|suggests?|points?|tests?|shifts?|gathers?|closes?)\b",
    re.IGNORECASE,
)

# Splice mangles from blind substitution.
_SPLICE = re.compile(
    r"\ba\s+of\b|\bthe\s+current\s+your\b|\byour\s+your\b|"
    r"\bthe\s+your\b|\ban\s+and\b|\s,\s*,|—\s*[.,]",
    re.IGNORECASE,
)

# A text may not END on these words — unambiguous danglers only (ending on
# a conjunction / article / possessive is broken in every register; common
# legit tails like "let others in." / "what it's for." are NOT listed).
_DANGLING_TAIL = re.compile(
    r"\b(and|but|or|nor|the|a|an|your|my|our|their|than|if|because|"
    r"while|whereas)\s*[.!?…]?\s*$",
    re.IGNORECASE,
)

# Truncated headline shape: no terminal punctuation AND ends on
# preposition+pronoun ("The tightest stretch of this").
_TRUNCATED_PRONOUN_TAIL = re.compile(
    r"\b(?:of|in|to|for|with|at|on|from|by|toward|towards)\s+"
    r"(?:this|that|these|those|it)\s*$",
    re.IGNORECASE,
)

_HAS_TERMINAL = re.compile(r"[.!?…]['\")\]]*\s*$")


def has_broken_grammar(text: str) -> bool:
    """True when the text shows amputation damage. Cheap heuristics only —
    no parser dependency. Empty/whitespace counts as broken."""
    if not isinstance(text, str) or not text.strip():
        return True
    t = text.strip()
    if _MISSING_NOUN.search(t):
        return True
    if _SPLICE.search(t):
        return True
    if "  " in t:
        return True
    if _DANGLING_TAIL.search(t):
        return True
    if not _HAS_TERMINAL.search(t) and _TRUNCATED_PRONOUN_TAIL.search(t):
        return True
    return False


def sentence_case(text: str) -> str:
    """Capitalize the first alphabetic character of each sentence. Leaves
    everything else untouched (never lowercases acronyms etc.)."""
    if not isinstance(text, str) or not text:
        return text

    _openers = "\"'‘’“”(¡¿—–-"

    def _cap(seg):
        for i, ch in enumerate(seg):
            if ch.isalpha():
                return seg[:i] + ch.upper() + seg[i + 1:]
            if not (ch.isspace() or ch in _openers):
                break
        return seg

    parts = _SENT_SPLIT.split(text)
    seps = _SENT_SPLIT.findall(text)
    out = []
    for i, p in enumerate(parts):
        out.append(_cap(p))
        if i < len(seps):
            out.append(seps[i])
    return "".join(out)


def clean_text(text: str,
               extra_banned: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    """Safe swaps -> per-sentence validate -> drop dirty sentences ->
    sentence-case. Returns (cleaned, flags). cleaned == "" means nothing
    survived; caller MUST fall back."""
    if not isinstance(text, str) or not text.strip():
        return "", ["empty"]
    flags: List[str] = []
    out = text
    for pat, repl in _SAFE_SWAPS:
        if pat.search(out):
            flags.append("swap:" + pat.pattern[:32])
            out = pat.sub(repl, out)

    kept = []
    for sent in _SENT_SPLIT.split(out):
        if not sent.strip():
            continue
        dirty = bool(_HARD_INTERNAL.search(sent))
        if dirty:
            flags.append("hard_internal")
        else:
            v = validate_narration(sent, extra_banned=extra_banned)
            # lowercase starts are FIXED by sentence_case, never dropped.
            v = [x for x in v if not x.startswith("lowercase_sentence_start")]
            if v:
                dirty = True
                flags.extend(v[:3])
        if not dirty:
            kept.append(sent.strip())
    cleaned = " ".join(kept).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = sentence_case(cleaned)
    return cleaned, flags


def guard_field(text: str, fallback: str,
                extra_banned: Optional[List[str]] = None) -> str:
    """Flag -> fallback. Returns cleaned text when it survives both the
    jargon pass and the integrity gate; otherwise the caller's fallback.
    NEVER returns a half-sentence."""
    if not isinstance(text, str) or not text.strip():
        return fallback
    cleaned, _flags = clean_text(text, extra_banned=extra_banned)
    if not cleaned or has_broken_grammar(cleaned):
        return fallback
    return cleaned
