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
    # [voice-gate 2026-08-13] "planetary <noun>" ("planetary movements/motion/
    # positions/influence") and the bare word "planet(s)" ("planets align",
    # "the planet is moving") both slipped past — planet_name lists only the
    # specific bodies, and cosmic_timing_filler needed a leading "the". Ban the
    # planet-mechanism vocabulary outright, the same way bare "chart" is banned.
    ("planet_mechanism", re.compile(
        r"\bplanetary\b|\bplanets?\b|\bplaneta\w*\b", re.IGNORECASE)),
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
    # [ask-voice-gate 2026-06-16] English transit jargon ("the slow-moving force
    # transiting through it"). Planet-motion vocabulary, never user-facing.
    ("transit_jargon", re.compile(r"\btransit(?:s|ing|ed)?\b", re.IGNORECASE)),
    # ANY energy construction — energy-voice is retired from prediction
    # surfaces ("growth and wisdom energy", "your X energy", bare "energy").
    ("energy_voice", re.compile(r"\benerg(?:y|ies|\u00eda|ia)\b", re.IGNORECASE)),
    ("coined_period_vocab", re.compile(
        r"\b(?:sub|micro)[-\s]?(?:chapter|phase|period)\b|"
        r"\bchapter lord\b|\bmajor(?:\s+life)?\s+chapter\b|"
        r"\b(?:major|minor|micro)\s+rhythm\b|\blayering\b", re.IGNORECASE)),
    ("dasha_code", re.compile(r"(?<![A-Za-z])(?:MD|AD|PD|SD)(?![A-Za-z])")),
    # [ask-voice-gate 2026-06-16] Energy-trait "<trait> forces" / cosmic-mechanism
    # vocabulary that leaked to the Ask surface. ("<trait> energies" is already
    # caught by energy_voice above.) Flag — never strip — so the caller regenerates.
    ("trait_forces", re.compile(
        r"\b\w+\s+and\s+\w+\s+forces?\b|"
        r"\b(?:slow|fast)[-\s]?moving\s+forces?\b|"
        r"\b(?:cosmic|planetary|celestial|astral|energetic|inner|life|identity|"
        r"desire|spiritual|transiting|moving)\s+forces?\b", re.IGNORECASE)),
    # "interventions" used as a count of chart factors ("three unobstructed
    # interventions"). The word has no place on a plain-language life surface.
    ("intervention_count", re.compile(
        r"\b(?:un)?obstructed\s+interventions?\b|\binterventions?\b", re.IGNORECASE)),
    # Vague cosmic timing filler instead of a concrete window/date.
    ("cosmic_timing_filler", re.compile(
        r"\bthe\s+sky\s+aligns?\b|\bthe\s+stars?\s+align\b|"
        r"\bwhen\s+the\s+(?:structure|stars?|sky|alignment|chart|cosmos|universe)\s+aligns?\b|"
        r"\bcosmos\s+aligns?\b|\buniverse\s+aligns?\b|"
        r"\bthe\s+(?:sky|stars?|planets?|cosmos|universe|heavens?)\s+"
        r"(?:is\s+|are\s+|to\s+|finally\s+|slowly\s+)*"
        r"(?:lin(?:e|es|ing)\s+up|align\w*|com\w+\s+into\s+alignment)\b",
        re.IGNORECASE)),
    # Bare "chart"/"horoscope"/"astrology" — the immutable contract bans "chart"
    # anywhere, but the validator only caught qualified forms (natal/annual/
    # relocated chart). "the deeper partnership chart" leaked to the live Ask read.
    ("chart_or_horoscope_word", re.compile(
        r"\b(?:charts?|horoscopes?|astrolog(?:y|ical|ically|er|ers))\b",
        re.IGNORECASE)),
    # Splice mangles from blind substitution / empty fills.
    ("splice_mangle", re.compile(
        r"\ba\s+of\b|\bthe\s+current\s+your\b|\byour\s+your\b|"
        r"\bthe\s+your\b|\ban?\s+and\b", re.IGNORECASE)),
    # Sentence starting lowercase after terminal punctuation.
    ("lowercase_sentence_start", re.compile(r"[.!?]\s+[a-z]")),
    # [narration-integrity 2026-07-04] internal/system vocabulary the
    # 2026-06 rules missed — these sailed through the live Ask
    # voice-gate ("multiple wealth combinations in your blueprint",
    # "One layer shows some friction", "The annual setup").
    ("internal_vocab", re.compile(
        r"\b(?:blueprint|signal\s+floor|wealth\s+combinations?|"
        r"annual\s+setup|convergence\s+(?:score|met)|natal)\b", re.IGNORECASE)),
    ("bare_layer", re.compile(
        r"\b(?:one|a|an|the|another|this|that|each|every|second|third)\s+layers?\b",
        re.IGNORECASE)),
    ("astrocarto_jargon", re.compile(
        r"\b(?:AC|MC|DC|IC|ASC)\s+lines?\b|\brelocated\s+chart\b|"
        r"\bannual\s+chart\b|\bnatal\s+chart\b", re.IGNORECASE)),
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
