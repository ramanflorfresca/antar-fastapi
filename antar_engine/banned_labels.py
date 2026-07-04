"""
antar_engine/banned_labels.py
─────────────────────────────
WS3 of the "stable deterministic verdict" sprint.

Internal energy-translation labels (the hyphenated `<X>-and-<Y>` form
used INSIDE the prompt to teach Claude not to leak planet names) have
been leaking into user-facing text:

    "Your structure-and-persistence layer (Saturn) sits in your gains area."
    "Your identity-and-authority energy is amplifying ..."
    "Your release-and-dissolution energy is currently moving through ..."

These are documented as BAD examples in main.py's _voice_rules — but
Claude still echoes them sometimes. The fix is a deterministic post-
generation strip + canonicalize pass that runs on every user-facing
field of the /predict response.

Rule: detect known hyphenated energy labels (and the area-suffix forms
like "your gains area"), replace with the canonical single-word noun.

NEVER MUTATES the verdict, the band, the timeframe, or the move —
only the surface vocabulary.

Used by:
  - antar_engine/plain_english.py (post-validate)
  - main.py /predict post-pass (defense in depth)
"""

from __future__ import annotations
import re
from typing import Dict, List, Tuple


# Canonical map: hyphenated energy label → single word (English).
# Spanish: leave the English label removal alone and translate in main
# via existing _strip_instrument_names; we focus on the English forms.
_LABEL_CANONICAL: Dict[str, str] = {
    # Saturn family
    "structure-and-persistence": "discipline",
    "structure-and-discipline":  "discipline",
    "discipline-and-structure":  "discipline",
    "discipline-and-persistence": "discipline",
    "structure-and-stability":   "structure",

    # Sun family
    "identity-and-authority":    "authority",
    "command-and-authority":     "authority",
    "authority-and-identity":    "authority",

    # Ketu family
    "release-and-dissolution":   "release",
    "release-and-letting-go":    "release",
    "dissolution-and-release":   "release",
    "letting-go-and-release":    "release",

    # Jupiter family
    "growth-and-wisdom":         "growth",
    "expansion-and-wisdom":      "growth",
    "wisdom-and-growth":         "growth",
    "growth-and-expansion":      "growth",

    # Mars family
    "action-and-drive":          "drive",
    "drive-and-action":          "drive",
    "courage-and-action":        "drive",

    # Venus family
    "love-and-partnership":      "partnership",
    "partnership-and-love":      "partnership",
    "harmony-and-comfort":       "harmony",
    "beauty-and-harmony":        "harmony",

    # Mercury family
    "communication-and-intellect": "clarity",
    "clarity-and-communication":   "clarity",
    "intellect-and-communication": "clarity",

    # Rahu family
    "ambition-and-amplification": "ambition",
    "desire-and-amplification":   "ambition",
    "amplification-and-ambition": "ambition",

    # Moon family
    "emotional-and-nurturing":   "emotion",
    "emotion-and-intuition":     "intuition",
    "intuition-and-emotion":     "intuition",
}

# Area-suffix labels — "your gains area", "your transformation area", etc.
# Replace with a plain phrase that doesn't sound like an internal label.
_AREA_CANONICAL: Dict[str, str] = {
    "your gains area":            "your income side",
    "your transformation area":   "your shared-resources side",
    "your release area":          "your release side",
    "your identity area":         "yourself",
    "your wealth and voice area": "your savings side",
    "your courage and initiative area": "your initiative",
    "your home and inner peace area":   "your home life",
    "your creativity and children area":"your creative side",
    "your work and health area":  "your work-and-health side",
    "your partnerships area":     "your partnerships",
    "your luck and higher purpose area":"your direction",
    "your career and public role area": "your public role",
    "your gains and community area":    "your network",
    "your release and foreign lands area":"your release side",
}

# Dasha cycle labels Claude sometimes emits ("Ambition cycle",
# "Structure cycle", etc.) — these are internal training-example labels.
_CYCLE_CANONICAL: Dict[str, str] = {
    "ambition cycle":        "this chapter",
    "structure cycle":       "this chapter",
    "growth cycle":          "this chapter",
    "execution cycle":       "this chapter",
    "magnetism cycle":       "this chapter",
    "communication cycle":   "this chapter",
    "authority cycle":       "this chapter",
    "emotional cycle":       "this chapter",
    "extraction cycle":      "this chapter",
}

# Compile a single combined regex per category to make the strip cheap.
def _compile(table: Dict[str, str]) -> List[Tuple[re.Pattern, str]]:
    out: List[Tuple[re.Pattern, str]] = []
    # Longest-first so multi-word labels match before substrings.
    for k in sorted(table.keys(), key=lambda s: -len(s)):
        pat = re.compile(r"\b" + re.escape(k) + r"\b", flags=re.IGNORECASE)
        out.append((pat, table[k]))
    return out


_LABEL_PATTERNS = _compile(_LABEL_CANONICAL)
_AREA_PATTERNS  = _compile(_AREA_CANONICAL)
_CYCLE_PATTERNS = _compile(_CYCLE_CANONICAL)

# Trailing "energy"/"layer"/"vibe" word that often follows a label.
_TRAILING_NOISE = re.compile(
    r"\b(energy|layer|vibe|signal)\b",
    flags=re.IGNORECASE,
)


def detect_energy_labels(text: str) -> List[str]:
    """Return every banned label currently in text. Empty list = clean."""
    if not text:
        return []
    hits: List[str] = []
    for pat, _ in _LABEL_PATTERNS + _AREA_PATTERNS + _CYCLE_PATTERNS:
        if pat.search(text):
            hits.append(pat.pattern)
    return hits


def strip_energy_labels(text: str, language: str = "en") -> str:
    """Replace every banned label with its canonical single-word form,
    then tidy any orphan 'energy'/'layer'/'vibe' suffix left dangling
    immediately after the replacement. Idempotent."""
    if not text or not isinstance(text, str):
        return text

    out = text
    for pat, replacement in _LABEL_PATTERNS:
        out = pat.sub(replacement, out)
    for pat, replacement in _AREA_PATTERNS:
        out = pat.sub(replacement, out)
    for pat, replacement in _CYCLE_PATTERNS:
        out = pat.sub(replacement, out)

    # Tidy the typical leftover: "<noun> energy/layer/vibe sits ..." →
    # drop the "energy/layer/vibe" right after a single-word replacement.
    # [predclean 2026-06-09] widened the trailing noun set to match the
    # main rephrase-strip below — `influence` was paraphrased through.
    out = re.sub(
        r"\b(discipline|authority|release|growth|drive|partnership|"
        r"harmony|clarity|ambition|emotion|intuition|structure)\s+"
        r"(energy|layer|vibe|signal|influence)\b",
        r"\1",
        out,
        flags=re.IGNORECASE,
    )

    # Standalone "energy"/"layer" suffix after a chart-area phrase loses
    # its anchor when we strip — kill obvious leftovers.
    out = re.sub(r"\s+(energy|layer|vibe|influence)\.", ".", out, flags=re.IGNORECASE)
    out = re.sub(r"\s+(energy|layer|vibe|influence),", ",", out, flags=re.IGNORECASE)

    # [narration-polish] general-energy + metaphor + house-jargon
    # Defect 1 (founder brief 2026-06-09): catch ANY '<word> energy'
    # or '<word>-and-<word> energy' the canonical map missed, ban
    # metaphor verbs, and translate stock house jargon.
    #
    # The general regex matches forms like:
    #   'structure-and-persistence energy' (escaped the canonical map)
    #   'persistence energy', 'discipline-and-structure energy'
    #   'persistence and structure energy'
    # Replacement: empty (drop the construction; the surrounding
    # clause re-reads as plain English).
    # [predclean 2026-06-09] widened: catch `<x>-and-<y> energy`
    # AND the model's rephrase variants `<x>-and-<y> influence`,
    # `<x>-and-<y> layer`, `<x>-and-<y> signal`, `<x>-and-<y> vibe`.
    # Same leak class — the model was paraphrasing past the
    # `energy`-only regex.
    # [narration-integrity 2026-07-04] NEVER delete these constructions
    # word-by-word — in-place deletion is what produced "no strong
    # confirms" on the live Ask surface. Any sentence still carrying a
    # '<x> energy/layer/influence/signal/vibe' construction after the
    # canonical swaps above is dropped WHOLE. If every sentence is
    # dropped, return "" — callers treat empty as flag -> fallback.
    _generic_energy = re.compile(
        r"\b[\w-]+(?:\s+and\s+[\w-]+)?\s+(?:energy|layer|influence|signal|vibe)\b",
        flags=re.IGNORECASE,
    )
    if _generic_energy.search(out):
        _sents = re.split(r"(?<=[.!?])\s+", out)
        _kept = [_s for _s in _sents if not _generic_energy.search(_s)]
        out = " ".join(_kept).strip()
    # Metaphor verbs: 'pressing through' / 'flowing through' /
    # 'moving through' / 'coursing through' — drop the verb phrase.
    out = re.sub(
        r"\b(?:pressing|flowing|moving|coursing)\s+through\b",
        "into",
        out,
        flags=re.IGNORECASE,
    )
    # House jargon → plain-language equivalents.
    _HOUSE_JARGON = {
        "hidden gains":     "back-channel income",
        "hidden income":    "back-channel income",
        "hidden losses":    "back-channel costs",
        "hidden expenses":  "back-channel costs",
        "hidden wealth":    "reserves",
        "shared resources": "joint funds",
    }
    for _src, _dst in _HOUSE_JARGON.items():
        out = re.sub(r"\b" + re.escape(_src) + r"\b",
                     _dst, out, flags=re.IGNORECASE)
    # Tidy residual artefacts from the energy-strip
    # (e.g. 'your   savings' or ' . ').
    out = re.sub(r"\s+([.,;!?])", r"\1", out)
    out = re.sub(r"  +", " ", out).strip()
    # Collapse double spaces created by replacements.
    return out


def scrub_fields(data: dict, language: str = "en") -> dict:
    """In-place scrub of standard user-facing fields. Returns data."""
    if not isinstance(data, dict):
        return data
    for field in ("plain_summary", "signal_line", "action_item",
                  "timing_window", "why_this", "bridge_practice_note"):
        v = data.get(field)
        if isinstance(v, str) and v:
            data[field] = strip_energy_labels(v, language=language)
    return data
