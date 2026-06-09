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
# [ask-spec 2026-06-09] Internal-metric + planet-trait + relative-time
# strippers. Run AFTER promote_clock so a real computed clock survives.
# Defensive: even when the prompt bans these, models leak. These are
# the last gate before the user sees the text.
# ─────────────────────────────────────────────────────────────────────

# Matches '51%', '51 %', '39%'. Used to strip whole clauses that
# include any percentage figure (we never expose raw scores).
_PCT_RE = re.compile(r"\b\d{1,3}\s?%")

# Match a sentence (or fragment between commas / em-dashes) that
# contains a banned internal-metric token. We strip the entire
# fragment because partial paraphrase from a regex is worse than
# silent deletion.
_INTERNAL_TOKENS = [
    r"\d{1,3}\s?%",
    r"\blive\s+signal\b",
    r"\bblueprint(?:\s+floor)?\b",
    r"\bsignal\s+floor\b",
    r"\binternal\s+score\b",
    r"\bconfidence\s+(?:score|number)\b",
]
_INTERNAL_ANY = re.compile("|".join(_INTERNAL_TOKENS), re.IGNORECASE)

# Splits text into fragments at sentence breaks AND em/en dashes.
# Em-dash often joins a "leak" subordinate clause to the main sentence;
# we want to amputate just that limb if it carries an internal metric.
_FRAG_SPLIT = re.compile(r"(\.\s+|;\s+|\s+—\s+|\s+–\s+)")


def strip_internal_metrics(text: str) -> str:
    """Strip any sentence-fragment containing a percentage figure or
    the words 'live signal', 'blueprint', 'signal floor'. Idempotent.

    Founder rule 2026-06-09: internal scores never appear in `/ask`
    read/next/actions. They live in reasoning_technical only.
    """
    if not text or not isinstance(text, str):
        return text
    if not _INTERNAL_ANY.search(text):
        return text

    parts = _FRAG_SPLIT.split(text)
    keep: list = []
    for i, frag in enumerate(parts):
        # _FRAG_SPLIT keeps separators as odd-indexed entries.
        if i % 2 == 1:
            # Only keep separator if BOTH neighbours survive (else
            # we'd leave a dangling '— ' at end).
            if keep and (i + 1) < len(parts) and not _INTERNAL_ANY.search(parts[i + 1] or ""):
                keep.append(frag)
            continue
        if _INTERNAL_ANY.search(frag or ""):
            continue  # drop the fragment entirely
        keep.append(frag)

    out = "".join(keep).strip()
    # If we annihilated the whole text, return a single neutral
    # connector so downstream code never sees an empty string.
    if not out:
        return ""
    # Tidy: collapse multiple spaces, drop leading/trailing
    # punctuation orphans.
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"^\s*[,;—–]\s*", "", out)
    out = re.sub(r"\s*[,;]\s*$", ".", out)
    # Ensure the result still ends with terminal punctuation.
    if out and out[-1] not in ".!?":
        out += "."
    return out


# Planet-trait single words used as if they were the cause itself.
# Saturn → "discipline", Mars → "drive", Venus → "harmony", etc.
# We restate them as the PLAIN constraint so the read reads as
# everyday English, never as a vedic gloss.
_TRAIT_TRANSLATIONS: list = [
    # 'discipline blocking X' / 'discipline holds X' → 'caution holds X'
    (re.compile(r"\bdiscipline\s+(blocking|holding|restraining|gating|keeping)\b",
                re.IGNORECASE),
     r"caution \1"),
    # 'your discipline' as subject → 'your caution'
    (re.compile(r"\byour\s+discipline\b", re.IGNORECASE),
     "your caution"),
    # 'authority pulling X' → 'a senior call pulling X'
    (re.compile(r"\bauthority\s+(pulling|pressing|driving)\b",
                re.IGNORECASE),
     r"a senior call \1"),
    # 'drive pushing X' → 'momentum pushing X'
    (re.compile(r"\bdrive\s+(pushing|pressing|forcing)\b",
                re.IGNORECASE),
     r"momentum \1"),
]


def strip_planet_traits(text: str) -> str:
    """Replace planet-trait single-word leaks with plain-English
    constraints. Idempotent."""
    if not text or not isinstance(text, str):
        return text
    out = text
    for rx, repl in _TRAIT_TRANSLATIONS:
        out = rx.sub(repl, out)
    return out


# Soft-time tokens that drift away from a real clock. When NO hard
# clock has been promoted (i.e. timing_window did not supply one),
# we still ban the soft fallback — the read must either name a
# real clock OR omit timing entirely. The user's brief: "Ban
# relative-time phrases in the `read`: late morning, early/early
# afternoon, after midday, soon, later, shortly."
_RELATIVE_BAN = re.compile(
    r"\b(late\s+morning|early\s+morning|early\s+afternoon|"
    r"late\s+afternoon|after\s+midday|after\s+noon|"
    r"shortly|later\s+today|soon|later)\b",
    re.IGNORECASE,
)


def ban_relative_time(text: str, has_hard_clock: bool = False) -> str:
    """If no hard clock was promoted into `text`, strip any leftover
    soft-time phrases that survived promote_clock. Idempotent."""
    if not text or not isinstance(text, str):
        return text
    if has_hard_clock:
        # If a real clock token already lives in the text, leave
        # relative tokens around it alone — they may be legitimate
        # textures ('late morning, around 11:20').
        return text
    out = _RELATIVE_BAN.sub("", text)
    # Tidy connectors stranded by the removal.
    out = re.sub(r"\s*,\s*,", ",", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([.,;!?])", r"\1", out)
    return out.strip()


def has_clock_token(text: str) -> bool:
    """True if text already carries a HH:MM or H AM/PM clock token."""
    if not text or not isinstance(text, str):
        return False
    return bool(_CLOCK_RE.search(text))

# ─────────────────────────────────────────────────────────────────────
# Public entry — call this once after banned_labels scrub.
# ─────────────────────────────────────────────────────────────────────

def polish(data: dict, language: str = "en") -> dict:
    """Run passes in canonical order: clock-promotion first,
    then capitalization, then the [ask-spec 2026-06-09] strippers
    (internal metrics → planet-trait translation → soft-time ban).
    The relative-time ban respects whether a hard clock survives."""
    promote_clock(data, language=language)
    scrub_capitalization(data)
    # [ask-spec 2026-06-09] Defensive strippers.
    for _field in ("signal_line", "plain_summary", "action_item",
                   "why_this", "bridge_practice_note"):
        _v = data.get(_field)
        if isinstance(_v, str) and _v:
            _v = strip_internal_metrics(_v)
            _v = strip_planet_traits(_v)
            _v = ban_relative_time(_v, has_hard_clock=has_clock_token(_v))
            data[_field] = _v
    return data
