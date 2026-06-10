"""
antar_engine/narration_validator.py
===================================
Class-B narration validator (Cowork brief 2026-06-10).

Doctrine: VALIDATE, don't strip. Post-hoc regex substitution on generated
prose is what produced "a of wisdom" / "The current your love and
partnership energy micro-phase". This module only FLAGS violations; the
caller fails to a deterministic, dated, life-noun fallback.

Usage:
    from antar_engine.narration_validator import validate_narration
    violations = validate_narration(text, extra_banned=[archetype_name])
    if violations:
        text = safe_fallback  # caller-owned

Covers: planet names (EN/ES), house references (numeric, ordinal, spelled,
or the bare word), Sanskrit/system names, ANY "energy" construction,
Antar-coined period vocabulary, MD/AD/PD codes, splice mangles, and
lowercase sentence-starts.
"""
from __future__ import annotations

import re
from typing import List, Optional

_RULES = [
    ("planet_name", re.compile(
        r"\b(?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu|"
        r"Sol|Luna|Marte|Mercurio|J[uú]piter|Saturno)\b", re.IGNORECASE)),
    ("sign_name", re.compile(
        r"\b(?:Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|"
        r"Sagittarius|Capricorn|Aquarius|Pisces)\b")),
    # Any house reference — numeric, ordinal, spelled, or the bare word.
    # The verify contract is "no 'house' anywhere in user-facing strings".
    ("house_reference", re.compile(r"\bhouses?\b", re.IGNORECASE)),
    ("sanskrit_or_system", re.compile(
        r"\b(?:dasha|mahadasha|antardasha|pratyantar\w*|nakshatra|"
        r"navamsh?a|lagna|karaka|rashi|graha|sade\s*sati|vimsh?ottari|"
        r"jaimini|chara|varshphal|arudha|atmakaraka|amatyakaraka|"
        r"darakaraka|dharma|gochar)\b", re.IGNORECASE)),
    # ANY energy construction — energy-voice is retired from prediction
    # surfaces ("growth and wisdom energy", "your X energy", bare "energy").
    ("energy_voice", re.compile(r"\benerg(?:y|ies|\u00eda|ia)\b", re.IGNORECASE)),
    ("coined_period_vocab", re.compile(
        r"\b(?:sub|micro)[-\s]?(?:chapter|phase|period)\b|"
        r"\bchapter lord\b|\bmajor(?:\s+life)?\s+chapter\b|"
        r"\b(?:major|minor|micro)\s+rhythm\b|\blayering\b", re.IGNORECASE)),
    ("dasha_code", re.compile(r"(?<![A-Za-z])(?:MD|AD|PD|SD)(?![A-Za-z])")),
    # Splice mangles from blind substitution / empty fills.
    ("splice_mangle", re.compile(
        r"\ba\s+of\b|\bthe\s+current\s+your\b|\byour\s+your\b|"
        r"\bthe\s+your\b|\ban?\s+and\b", re.IGNORECASE)),
    # Sentence starting lowercase after terminal punctuation.
    ("lowercase_sentence_start", re.compile(r"[.!?]\s+[a-z]")),
]


def validate_narration(text: str,
                       extra_banned: Optional[List[str]] = None,
                       language: str = "en") -> List[str]:
    """Return a list of violation descriptions ([] = clean)."""
    if not isinstance(text, str) or not text.strip():
        return ["empty_text"]
    violations: List[str] = []
    for name, rx in _RULES:
        m = rx.search(text)
        if m:
            violations.append(f"{name}: '{m.group(0)}'")
    for label in (extra_banned or []):
        if label and isinstance(label, str) and len(label) >= 4:
            if re.search(re.escape(label), text, re.IGNORECASE):
                violations.append(f"extra_banned: '{label}'")
    return violations


def is_clean(text: str, extra_banned: Optional[List[str]] = None,
             language: str = "en") -> bool:
    return not validate_narration(text, extra_banned, language)
