"""
antar_engine/dangling_text_guard.py
─────────────────────────────────────
BUG fix from the "kill the generic read" sprint.

Live output contained:
    "Speculation is risky today; wait until to decide"
    "Wait until when the pressure lifts"

These are not template-merge bugs in Python — they are Claude itself
emitting boilerplate sentence frames whose placeholder slot was meant
to be filled with a date or condition but stayed empty. The fix is a
defensive scrub on /predict's final user-facing fields:

  1. Detect dangling patterns (`detect_dangling`)
  2. Repair safely without changing the verdict (`repair_dangling`)
  3. Guard the centralised plain_english output by composing both

The repair never invents a date. It either drops the dangling clause
or rewrites the sentence to be honest about the absence of timing.

Used by:
  - antar_engine/plain_english.py (post-validate, language-aware)
  - main.py /predict post-pass (defense in depth)
"""

from __future__ import annotations
import re
from typing import List, Tuple


# Regexes — case-insensitive, multi-language. Each catches a known
# dangling shape. They MUST NOT match the legitimate "wait until <date>"
# form ("wait until August 2026") or "wait until <verb-phrase>" form
# ("wait until you feel grounded").
_PATTERNS_EN: List[Tuple[re.Pattern, str]] = [
    # "wait until to decide"  /  "wait until to act"
    (re.compile(r"\bwait\s+until\s+to\s+(decide|act|move|commit|choose|begin|start)\b", re.I),
     "hold off"),

    # "Wait until when the pressure lifts"  → drop "when"
    (re.compile(r"\bwait\s+until\s+when\s+", re.I),
     "wait until "),

    # "wait until ___" or "wait until --"
    (re.compile(r"\bwait\s+until\s+(?:_+|-+|\?+)\s*", re.I),
     "hold off "),

    # Trailing "wait until." at end of sentence
    (re.compile(r"\bwait\s+until\.\s*", re.I),
     "hold off. "),

    # "wait until ." or "wait until ," with no object before it
    (re.compile(r"\bwait\s+until\s*([.,;])", re.I),
     r"hold off\1"),

    # "wait until the date" left as a literal placeholder
    (re.compile(r"\bwait\s+until\s+(?:the\s+)?date\b", re.I),
     "hold off"),

    # Empty-bracket placeholder
    (re.compile(r"\bwait\s+until\s+\[\s*\]", re.I),
     "hold off"),

    # Double-space artifacts often left by empty merges
    (re.compile(r"  +"), " "),

    # Orphaned punctuation after empty merges
    (re.compile(r"\s+([.,;!?])"), r"\1"),
]

_PATTERNS_ES: List[Tuple[re.Pattern, str]] = [
    # "espera hasta para decidir"
    (re.compile(r"\bespera\s+hasta\s+para\s+(decidir|actuar|mover|comprometer|elegir|empezar)\b", re.I),
     "espera"),

    # "Espera hasta cuando ..."
    (re.compile(r"\bespera\s+hasta\s+cuando\s+", re.I),
     "espera hasta "),

    # "espera hasta ___"  /  "--"
    (re.compile(r"\bespera\s+hasta\s+(?:_+|-+|\?+)\s*", re.I),
     "espera "),

    (re.compile(r"\bespera\s+hasta\.\s*", re.I),
     "espera. "),

    (re.compile(r"\bespera\s+hasta\s*([.,;])", re.I),
     r"espera\1"),

    (re.compile(r"\bespera\s+hasta\s+\[\s*\]", re.I),
     "espera"),

    (re.compile(r"  +"), " "),
    (re.compile(r"\s+([.,;!?])"), r"\1"),
]


def detect_dangling(text: str, language: str = "en") -> List[str]:
    """Return list of dangling-pattern descriptions present in text."""
    if not text:
        return []
    patterns = _PATTERNS_ES if (language or "en").lower().startswith("es") else _PATTERNS_EN
    hits: List[str] = []
    for pat, _ in patterns:
        if pat.search(text):
            hits.append(pat.pattern)
    return hits


def repair_dangling(text: str, language: str = "en") -> str:
    """Apply all dangling-pattern repairs. Idempotent — safe to call
    multiple times. Never changes verdict or invents dates."""
    if not text or not isinstance(text, str):
        return text
    patterns = _PATTERNS_ES if (language or "en").lower().startswith("es") else _PATTERNS_EN
    repaired = text
    for pat, replacement in patterns:
        repaired = pat.sub(replacement, repaired)
    # Strip leading/trailing whitespace introduced by sub.
    return repaired.strip()


def scrub_fields(data: dict, language: str = "en") -> dict:
    """In-place scrub the standard user-facing string fields on a
    /predict response dict. Returns the same dict for chaining."""
    if not isinstance(data, dict):
        return data
    for field in ("plain_summary", "signal_line", "action_item",
                  "timing_window", "why_this", "bridge_practice_note"):
        v = data.get(field)
        if isinstance(v, str) and v:
            data[field] = repair_dangling(v, language=language)
    return data
