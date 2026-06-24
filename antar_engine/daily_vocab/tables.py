"""
antar_engine/daily_vocab/tables.py — deterministic lookup tables for the
Concrete Daily Vocabulary Layer (body / food / mood / romance / direction /
color / timing).

DESIGN DISCIPLINE
  * PURE DATA + tiny normalizers. No LLM. No Swiss Ephemeris. No heavy imports.
    This module must import cleanly in any environment (incl. CI / sandbox
    without pyswisseph) so the vocab layer stays fully unit-testable.
  * Tables are COPIED (not imported) from their canonical homes so this package
    has zero dependency on the swisseph-bearing engine modules. Each block notes
    its canonical source; if a source table changes, mirror it here deliberately.
  * Classical doctrine (kalapurusha body map, day-lord Dik directions, rasa per
    graha) — stable, jargon-free at the OUTPUT layer. Planet/house words live
    ONLY in these internal tables and never reach a user-facing string.

Canonical sources mirrored here:
  SIGN_ELEMENT        <- antar_engine/food_engine.py
  WEEKDAY_TO_LORD     <- classical vara lords
  DAY_LORD_COLOR      <- antar_engine/daily_panchanga.py DAY_LORD_PROPS["color"]
  PLANET_TASTE        <- antar_engine/ayurveda_astrology.py PLANET_DOSHA["taste"]
  HOUSE_BODY          <- antar_engine/deep_read.py HOUSE_BODY
  PLANET_BODY         <- antar_engine/deep_read.py PLANET_BODY
  NAKSHATRA_ENERGY    <- antar_engine/daily_prediction_engine.py NAKSHATRA_PROFILES
  MOON_FRICTION_MAP   <- antar_engine/daily_prediction_engine.py MOON_FRICTION_MAP
"""

from __future__ import annotations

from typing import Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────
# Signs & elements
# ─────────────────────────────────────────────────────────────────────

SIGNS: List[str] = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# <- food_engine.py SIGN_ELEMENT
SIGN_ELEMENT: Dict[str, str] = {
    "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
    "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
    "Gemini": "air", "Libra": "air", "Aquarius": "air",
    "Cancer": "water", "Scorpio": "water", "Pisces": "water",
}

# ─────────────────────────────────────────────────────────────────────
# Vara (weekday) lords + the small graha attribute tables we surface
# ─────────────────────────────────────────────────────────────────────

WEEKDAY_TO_LORD: Dict[str, str] = {
    "Monday": "Moon", "Tuesday": "Mars", "Wednesday": "Mercury",
    "Thursday": "Jupiter", "Friday": "Venus", "Saturday": "Saturn",
    "Sunday": "Sun",
}

# Malefic / benefic temperament — internal only, drives body + event gating.
MALEFICS = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}
BENEFICS = {"Jupiter", "Venus", "Moon", "Mercury"}
# Among malefics: which move fast enough that a tight aspect = a TODAY event
# (Sun ~1°/day, Mars ~0.5°/day) vs slow ones that sit on an aspect for weeks
# (Saturn/Rahu/Ketu) — those only count when genuinely exact.
FAST_MALEFICS = {"Sun", "Mars"}
SLOW_MALEFICS = {"Saturn", "Rahu", "Ketu"}

# One simple wearable color per day-lord (collapsed from DAY_LORD_PROPS color).
DAY_LORD_COLOR: Dict[str, str] = {
    "Sun": "warm gold or orange",
    "Moon": "white or silver",
    "Mars": "red or coral",
    "Mercury": "green",
    "Jupiter": "yellow",
    "Venus": "soft pink or pastel blue",
    "Saturn": "deep blue or charcoal",
}

# Rasa lean per graha, plain-English (collapsed from PLANET_DOSHA["taste"]).
PLANET_TASTE: Dict[str, str] = {
    "Sun": "warming, lightly pungent food",
    "Moon": "soft, comforting food",
    "Mars": "warm, spiced food (go easy on the heat)",
    "Mercury": "light, fresh, easy-to-digest food",
    "Jupiter": "wholesome, mildly sweet food",
    "Venus": "rich, satisfying food",
    "Saturn": "simple, warm, grounding food",
}

# Classical Dik (direction) per graha. Direction words are NOT jargon — safe out.
PLANET_DIRECTION: Dict[str, str] = {
    "Sun": "east", "Venus": "southeast", "Mars": "south", "Rahu": "southwest",
    "Saturn": "west", "Moon": "northwest", "Mercury": "north",
    "Jupiter": "northeast",
}

# Element -> concrete food lean phrasing (the user-facing seed).
ELEMENT_FOOD_LEAN: Dict[str, str] = {
    "fire": "warm, lightly spiced meals sit well — go easy on the very hot stuff",
    "earth": "rich, grounding meals sit well today",
    "air": "light, varied, easy-to-digest food sits best",
    "water": "warm comfort food — simple and soothing — feels right",
}

# ─────────────────────────────────────────────────────────────────────
# Body / health (kalapurusha)  <- deep_read.py
# ─────────────────────────────────────────────────────────────────────

# House (counted from lagna) -> body region, soft phrasing.
HOUSE_BODY: Dict[int, str] = {
    1: "your head and overall energy",
    2: "your face, eyes, and throat",
    3: "your arms, shoulders, and hands",
    4: "your chest and heart",
    5: "your stomach and upper belly",
    6: "your gut and digestion",
    7: "your lower back and kidneys",
    8: "your core and recovery",
    9: "your hips and thighs",
    10: "your knees and joints",
    11: "your calves and ankles",
    12: "your feet and sleep",
}

# Graha -> body system it tends to stress (internal driver).
PLANET_BODY: Dict[str, str] = {
    "Sun": "your heart and eyes",
    "Moon": "your fluids and stomach",
    "Mars": "your muscles and blood",
    "Mercury": "your skin and nerves",
    "Jupiter": "your liver and weight",
    "Venus": "your kidneys and reproductive system",
    "Saturn": "your bones, teeth, and joints",
    "Rahu": "your nervous system",
    "Ketu": "your nervous system and digestion",
}

# Soft, NON-medical "gentle attention" advice per graha contact.
# Never diagnostic, never a warning — just a nudge to be unhurried with the body.
PLANET_BODY_ADVICE: Dict[str, str] = {
    "Sun": "pace your energy and rest your eyes from screens",
    "Moon": "keep meals regular and drink enough water",
    "Mars": "warm up before any hard effort — no rushed lifting or sudden strain",
    "Mercury": "give your hands and your busy mind a few real breaks",
    "Jupiter": "keep meals on the lighter side",
    "Venus": "warmth and rest help — don't push through tiredness",
    "Saturn": "go gentle on joints and posture — stretch, don't strain",
    "Rahu": "wind down early; a calm evening settles a busy nervous system",
    "Ketu": "keep things simple and let digestion settle",
}

# ─────────────────────────────────────────────────────────────────────
# Mood / nakshatra energy  <- daily_prediction_engine.py NAKSHATRA_PROFILES
# (energy + aligned + friction only — the fields the mood read needs)
# ─────────────────────────────────────────────────────────────────────

NAKSHATRA_ENERGY: Dict[str, Dict[str, object]] = {
    "Ashwini": {"energy": "swift and ready to start things", "aligned": ["starting something", "quick decisions"], "friction": ["slow negotiations", "long planning"]},
    "Bharani": {"energy": "intense and ready to finish things", "aligned": ["closing a chapter", "a hard conversation"], "friction": ["brand-new beginnings", "light socializing"]},
    "Krittika": {"energy": "sharp and decisive", "aligned": ["cutting a loss", "editing and clarity"], "friction": ["diplomacy", "compromise"]},
    "Rohini": {"energy": "creative and warm", "aligned": ["creative work", "time with people you love"], "friction": ["confrontation", "endings"]},
    "Mrigashira": {"energy": "curious and searching", "aligned": ["research", "meeting new people"], "friction": ["finalizing", "big commitments"]},
    "Ardra": {"energy": "stormy and restless", "aligned": ["solving a stubborn problem", "focused technical work"], "friction": ["partnerships", "being on show"]},
    "Punarvasu": {"energy": "easygoing and restoring", "aligned": ["recovery", "restarting something stalled"], "friction": ["intense focus", "confrontation"]},
    "Pushya": {"energy": "steady and nourishing", "aligned": ["long-term planning", "looking after your people"], "friction": ["risky bets", "speculation"]},
    "Ashlesha": {"energy": "quiet and strategic", "aligned": ["reading a situation", "careful negotiation"], "friction": ["being fully open", "trusting too fast"]},
    "Magha": {"energy": "dignified and sure of itself", "aligned": ["leading", "presenting your work"], "friction": ["blending in", "deferring"]},
    "Purva Phalguni": {"energy": "warm and pleasure-loving", "aligned": ["time with a partner", "something creative"], "friction": ["solo grind", "tight budgeting"]},
    "Uttara Phalguni": {"energy": "steady and reliable", "aligned": ["agreements", "long-term arrangements"], "friction": ["fast pivots", "speculation"]},
    "Hasta": {"energy": "skilled and precise", "aligned": ["detailed handiwork", "fixing things"], "friction": ["big-picture strategy", "delegating"]},
    "Chitra": {"energy": "bright and design-minded", "aligned": ["design", "a pitch or a polish"], "friction": ["dull routine", "slow processes"]},
    "Swati": {"energy": "independent and adaptable", "aligned": ["networking", "staying flexible"], "friction": ["being pinned down", "confrontation"]},
    "Vishakha": {"energy": "driven and goal-focused", "aligned": ["going after a target", "a competitive push"], "friction": ["resting", "casual socializing"]},
    "Anuradha": {"energy": "devoted and steady", "aligned": ["teamwork", "friendship", "structured work"], "friction": ["isolation", "self-promotion"]},
    "Jyeshtha": {"energy": "protective and in-command", "aligned": ["handling a crisis", "taking charge"], "friction": ["softness", "building partnerships"]},
    "Mula": {"energy": "digging and getting to the root", "aligned": ["root-cause work", "clearing things out"], "friction": ["new launches", "keeping things stable"]},
    "Purva Ashadha": {"energy": "buoyant and persuasive", "aligned": ["persuading someone", "travel"], "friction": ["slowing down", "accepting a no"]},
    "Uttara Ashadha": {"energy": "principled and built to last", "aligned": ["finalizing a win", "an honest decision"], "friction": ["grey areas", "compromise"]},
    "Shravana": {"energy": "tuned-in and listening", "aligned": ["learning", "advice and mentorship"], "friction": ["talking over people", "acting on impulse"]},
    "Dhanishta": {"energy": "abundant and bold", "aligned": ["a money move", "leading a group"], "friction": ["isolation", "fiddly detail work"]},
    "Shatabhisha": {"energy": "private and healing", "aligned": ["solo work", "an unconventional fix"], "friction": ["public-facing work", "partnerships"]},
    "Purva Bhadrapada": {"energy": "intense and all-in", "aligned": ["a high-stakes decision", "deep focus"], "friction": ["patience", "slow work"]},
    "Uttara Bhadrapada": {"energy": "calm and wise", "aligned": ["teaching", "settling a matter"], "friction": ["fast pivots", "speculation"]},
    "Revati": {"energy": "gentle and wrapping things up", "aligned": ["closing a cycle", "kind, generous acts"], "friction": ["new ventures", "competitive pressure"]},
}

# <- daily_prediction_engine.py MOON_FRICTION_MAP (natal moon sign -> clashing signs)
MOON_FRICTION_MAP: Dict[str, List[str]] = {
    "Aries": ["Cancer", "Capricorn"],
    "Taurus": ["Leo", "Aquarius"],
    "Gemini": ["Virgo", "Pisces"],
    "Cancer": ["Aries", "Libra"],
    "Leo": ["Taurus", "Scorpio"],
    "Virgo": ["Gemini", "Sagittarius"],
    "Libra": ["Cancer", "Capricorn"],
    "Scorpio": ["Leo", "Aquarius"],
    "Sagittarius": ["Virgo", "Pisces"],
    "Capricorn": ["Aries", "Libra"],
    "Aquarius": ["Taurus", "Scorpio"],
    "Pisces": ["Gemini", "Sagittarius"],
}

# Nakshatras that read as warm/relational — a soft romance signal.
WARM_NAKSHATRAS = {
    "Rohini", "Purva Phalguni", "Uttara Phalguni", "Anuradha", "Revati",
    "Pushya", "Chitra",
}

# Houses (from lagna) that map to soft, namable life-domains for event_watch.
EVENT_DOMAIN_BY_HOUSE: Dict[int, str] = {
    2: "money moves", 3: "short trips and driving", 5: "speculation and risk",
    6: "health and workload", 8: "anything high-stakes", 12: "spending and travel",
}

# ─────────────────────────────────────────────────────────────────────
# Normalizers — make lookups tolerant of spelling drift across engines
# ─────────────────────────────────────────────────────────────────────

# Common nakshatra spelling variants seen across the codebase / panchanga libs.
_NAK_ALIASES: Dict[str, str] = {
    "ashvini": "Ashwini", "aswini": "Ashwini",
    "mrigasira": "Mrigashira", "mrigashirsha": "Mrigashira", "mrigshira": "Mrigashira",
    "aslesha": "Ashlesha", "ashlesa": "Ashlesha",
    "purvaphalguni": "Purva Phalguni", "purva phalguni": "Purva Phalguni", "pubba": "Purva Phalguni",
    "uttaraphalguni": "Uttara Phalguni", "uttara phalguni": "Uttara Phalguni",
    "purvashada": "Purva Ashadha", "purva ashada": "Purva Ashadha", "purvaashadha": "Purva Ashadha",
    "uttarashada": "Uttara Ashadha", "uttara ashada": "Uttara Ashadha", "uttaraashadha": "Uttara Ashadha",
    "purvabhadrapada": "Purva Bhadrapada", "purva bhadra": "Purva Bhadrapada",
    "uttarabhadrapada": "Uttara Bhadrapada", "uttara bhadra": "Uttara Bhadrapada",
    "sravana": "Shravana", "dhanistha": "Dhanishta", "satabhisha": "Shatabhisha",
    "shatabhishak": "Shatabhisha", "jyestha": "Jyeshtha", "vishakha": "Vishakha",
    "visakha": "Vishakha", "kritika": "Krittika",
}


def norm_sign(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    t = name.strip().title()
    return t if t in SIGN_ELEMENT else None


def norm_nakshatra(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    raw = " ".join(name.strip().split())
    if raw in NAKSHATRA_ENERGY:
        return raw
    key = raw.lower().replace("-", " ")
    key1 = key.replace(" ", "")
    if key in _NAK_ALIASES:
        return _NAK_ALIASES[key]
    if key1 in _NAK_ALIASES:
        return _NAK_ALIASES[key1]
    # last resort: title-case match
    t = raw.title()
    return t if t in NAKSHATRA_ENERGY else None


def day_lord_for(weekday: Optional[str]) -> Optional[str]:
    if not weekday:
        return None
    return WEEKDAY_TO_LORD.get(weekday.strip().title())
