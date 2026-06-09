"""
antar_engine/narration_polish.py
─────────────────────────────────
Two surface fixes that close the Yogi feel-gap (per founder brief
2026-06-09):

  1. CLOCK PROMOTION — when `timing_window` carries a real clock token
     (HH:MM or HH AM/PM, computed from hora boundaries), the favorable-
     window phrase in signal_line / plain_summary MUST be that clock
     token. Relative-time phrases ("late morning", "before midday",
     "soon", "later", "shortly") get replaced with the actual clock.

  2. SENTENCE-BOUNDARY CAPITALIZATION — fix lowercase starts after
     ". " / "— " / "! " / "? " and at string start. Live output had
     "…into a new bet. your financial runway…".

KEPT INTENTIONALLY SEPARATE from banned_labels.py: that module owns
*deletions* (jargon strip). This one owns *promotions* (relative-to-
hard rewrites + casing fixes). Different concern, same call surface
(scrub on a dict of user-facing fields).

Never raises. Idempotent.
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────
# Clock-token detection
# ─────────────────────────────────────────────────────────────────────

# Matches `10:40 AM` / `12:10 PM` / `21:53` / `03:16`. Allows the AM/PM
# suffix to be optional and case-insensitive.
_CLOCK_RE = re.compile(
    r"\b(\d{1,2}:\d{2}(?:\s*[AP]\.?M\.?)?|\d{1,2}\s*[AP]\.?M\.?)\b",
    re.IGNORECASE,
)


def extract_clocks(timing_window: str) -> List[str]:
    """Return ordered list of clock tokens in timing_window, deduped."""
    if not timing_window:
        return []
    seen: List[str] = []
    for m in _CLOCK_RE.finditer(timing_window):
        tok = m.group(1).strip()
        if tok not in seen:
            seen.append(tok)
    return seen


# Relative-time phrases that drift away from a real clock. Map each to
# the preposition the rewrite uses ("before"/"after"/"around"/"by").
# Order matters for prefix matching — longer/more-specific first.
_RELATIVE_PHRASES: List[Tuple[str, str]] = [
    ("before midday",   "before"),
    ("around midday",   "around"),
    ("late morning",    "before"),
    ("early morning",   "around"),
    ("mid-morning",     "around"),
    ("late afternoon",  "before"),
    ("early afternoon", "around"),
    ("late evening",    "by"),
    ("early evening",   "by"),
    ("by midday",       "by"),
    ("by noon",         "by"),
    ("by midnight",     "by"),
    ("midday",          "around"),
    ("midnight",        "by"),
    ("shortly",         "by"),
    ("soon",            "by"),
    ("later today",     "after"),
    ("later",           "after"),
]


def _pick_anchor_clock(clocks: List[str], phrase: str) -> str:
    """When timing_window has multiple clocks, pick the one that best
    fits the relative phrase. `before X` → earliest; `after Y` → latest;
    `around/by` → first."""
    if not clocks:
        return ""
    if len(clocks) == 1:
        return clocks[0]
    if phrase in ("before midday", "late morning", "late afternoon",
                  "late evening"):
        return clocks[0]    # earliest = the closing boundary
    if phrase in ("later today", "later"):
        return clocks[-1]   # latest
    return clocks[0]


def promote_clock(data: dict, language: str = "en") -> dict:
    """Rewrite relative-time phrases to use the actual clock token from
    timing_window. In-place; returns data for chaining.

    Two safety passes after substitution:
      1. Dedup consecutive "<prep> CLOCK <prep> CLOCK" → "<prep> CLOCK"
         (happens when two relative phrases sit adjacent and both get
         replaced to the same boundary).
      2. Strip leftover prepositions stranded next to the new clock
         (`act in before 03:16` → `act before 03:16`).
    """
    if not isinstance(data, dict):
        return data
    tw = data.get("timing_window") or ""
    clocks = extract_clocks(tw)
    if not clocks:
        return data

    for field in ("signal_line", "plain_summary", "action_item"):
        text = data.get(field) or ""
        if not isinstance(text, str) or not text:
            continue

        for phrase, prep in _RELATIVE_PHRASES:
            rx = re.compile(r"\b" + re.escape(phrase) + r"\b", re.I)
            if rx.search(text):
                clock = _pick_anchor_clock(clocks, phrase)
                replacement = f"{prep} {clock}" if clock else ""
                text = rx.sub(replacement, text)

        # Pass 1 — dedup `<prep> CLOCK <prep> CLOCK`. Walks each
        # observed clock token.
        for clock in clocks:
            esc = re.escape(clock)
            dedup_rx = re.compile(
                r"\b(before|after|around|by)\s+" + esc
                + r"(?:\s+(?:before|after|around|by)\s+" + esc + r")+",
                re.I,
            )
            text = dedup_rx.sub(lambda m: f"{m.group(1)} {clock}", text)

        # Pass 2 — strip dangling preposition immediately before the
        # new replacement ("act in before 03:16" → "act before 03:16").
        text = re.sub(
            r"\b(in|on|at|during|by)\s+(before|after|around|by)\b",
            r"\2",
            text,
            flags=re.I,
        )

        # Tidy whitespace / punctuation artefacts.
        text = re.sub(r"  +", " ", text)
        text = re.sub(r"\s+([.,;!?])", r"\1", text)
        data[field] = text.strip()
    return data


# ─────────────────────────────────────────────────────────────────────
# Sentence-boundary capitalization
# ─────────────────────────────────────────────────────────────────────

# Match the lowercase letter that starts a sentence — either at the
# absolute start of the string, or after `. ` / `! ` / `? ` / `— ` /
# `– ` (em/en dash followed by space).
_SENT_START_RE = re.compile(
    r"(?:^|(?<=[.!?]\s)|(?<=[—–]\s))([a-z])",
)


def fix_capitalization(text: str) -> str:
    """Capitalize first letter at string start and after sentence-end
    punctuation. Idempotent."""
    if not text or not isinstance(text, str):
        return text
    return _SENT_START_RE.sub(lambda m: m.group(1).upper(), text)


def scrub_capitalization(data: dict) -> dict:
    """In-place capitalization fix for the standard fields."""
    if not isinstance(data, dict):
        return data
    for field in ("signal_line", "plain_summary", "action_item",
                  "why_this", "timing_window", "bridge_practice_note"):
        v = data.get(field)
        if isinstance(v, str) and v:
            data[field] = fix_capitalization(v)
    return data


# ─────────────────────────────────────────────────────────────────────
# Public entry — call this once after banned_labels scrub.
# ─────────────────────────────────────────────────────────────────────

def polish(data: dict, language: str = "en") -> dict:
    """Run both passes in the canonical order: clock-promotion first
    (it introduces new clock tokens), then capitalization (which
    cleans up sentence starts after replacement)."""
    promote_clock(data, language=language)
    scrub_capitalization(data)
    return data
