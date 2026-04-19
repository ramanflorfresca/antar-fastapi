"""
Forbidden Terms Linter — v5.1 Voice Framework
===============================================
Catches jargon leakage in rendered output.

Author: Antar Engine · April 2026
"""

from typing import List, Tuple
import re


# Terms that must NEVER appear in user-facing output
FORBIDDEN_TERMS = [
    # Planet names as subjects (allowed only inside energy_vocabulary references)
    r"\bYour Jupiter\b",
    r"\bYour Saturn\b",
    r"\bYour Mars\b",
    r"\bYour Mercury\b",
    r"\bYour Venus\b",
    r"\bYour Sun\b",
    r"\bYour Moon\b",
    r"\bYour Rahu\b",
    r"\bYour Ketu\b",

    # Jargon phrases
    r"\bLal Kitab prescribes\b",
    r"\bLal Kitab\b",            # framework name itself
    r"\bastrologically\b",
    r"\bpropitiate\b",
    r"\bappease\b",
    r"\bevil eye\b",
    r"\bnegative energy attack\b",
    r"\bplanets are aligned\b",
    r"\bstars say\b",

    # Prescriptive / fatalistic
    r"\bYou must\b",
    r"\bYou should\b",
    r"\bYou need to\b",
    r"\bguaranteed\b",
    r"\bThis will fix\b",
    r"\bThis will cure\b",
    r"\bYour karma demands\b",
    r"\bevil\b",
    r"\bcursed\b",

    # Technical astrology terms
    r"\bH\d+\b",                # H1, H6, H10 etc.
    r"\bdushthana\b",
    r"\bkendra\b",
    r"\btrikona\b",
    r"\byogakaraka\b",
    r"\bMahapurusha\b",
    r"\bViparita\b",
    r"\bnavamsha\b",
    r"\bgochara\b",
    r"\bmaraka\b",
    r"\bdosha\b",
    r"\bgraha\b",
    r"\bhomam\b",
    r"\bnakshatra\b",
    r"\bMahadasha\b",
    r"\bAntardasha\b",
    r"\blagna\b",

    # Medieval vocabulary
    r"\bpropitiation\b",
    r"\bplanetary affliction\b",
    r"\bbad time period\b",
    r"\bgood time period\b",

    # Self-help bloat
    r"\bthe universe has conspired\b",
    r"\byou have the power within\b",
    r"\bI sense that your soul\b",
]

# Compiled patterns for performance
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_TERMS]


def check_forbidden_terms(text: str) -> List[Tuple[str, str]]:
    """
    Check text for forbidden terms.

    Returns:
        List of (matched_text, pattern) tuples. Empty list = clean.
    """
    violations = []
    for pattern, compiled in zip(FORBIDDEN_TERMS, _COMPILED_PATTERNS):
        matches = compiled.findall(text)
        for m in matches:
            violations.append((m, pattern))
    return violations


def is_voice_clean(text: str) -> bool:
    """Quick check — returns True if no forbidden terms found."""
    return len(check_forbidden_terms(text)) == 0


# Recommended replacements for common jargon
JARGON_REPLACEMENTS = {
    "weak planet": "energy running dim",
    "strong planet": "energy running strong",
    "affliction": "this flow is under pressure",
    "dosha": "this pattern is active",
    "Sade Sati": "a 7.5-year structural reshaping phase",
    "karma": "a pattern from before you that you're now navigating",
    "Mahadasha": "your life's current main chapter",
    "Antardasha": "your current sub-chapter",
    "yoga": "a specific pattern in your design",
    "dushthana": "transformation houses",
    "maraka": "a pressure-point",
    "propitiate": "strengthen/support this energy",
    "remedial measure": "a practice",
    "lagna": "your chart's rising-point",
    "navamsha": "your soul-level chart",
    "gochara": "current sky-movements crossing your chart",
}
