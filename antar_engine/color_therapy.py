"""
Daily colour guidance — which colour activates today's live planetary energy.

[color-therapy 2026-07-20]

Two classical signals decide the colour, and they are not the same thing:

  1. VARA (weekday) lord — the day's standing frame. Sunday is the Sun's day
     whoever you are; it does not change with the chart or the hour.
  2. NAKSHATRA lord — the lord of the constellation the Moon actually occupies
     right now. This is the live, moving signal: it changes roughly every 24
     hours and is what makes one Monday different from the next.

Both are real. The nakshatra lord is the more *specific* of the two, so it
leads; the vara lord supports. When both resolve to the same graha the day
carries a single, undiluted colour and we say so — that is a genuinely
stronger recommendation, not a rendering accident.

The third input is TARA BALA, which the daily engine already computes: the
count from the user's birth nakshatra to today's, telling us whether this
Moon is friendly to THIS person. Colour advice ignores it at its peril. When
the tara is adverse, amplifying the nakshatra lord means pouring energy into
the very graha giving trouble; classical remedial practice does the opposite
and leans on the steadier vara frame instead. So on a difficult tara we lead
with the weekday colour and explicitly soften the nakshatra colour.

Colours come from daily_panchanga.DAY_LORD_PROPS, which is already the
codebase's classical source for planet colour/gem/metal/deity. Only Rahu and
Ketu are added here — they never rule a weekday, so DAY_LORD_PROPS has no
entry for them, but they DO rule nakshatras (Ardra, Swati, Shatabhisha for
Rahu; Ashwini, Magha, Mula for Ketu) and so must be covered.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from antar_engine.daily_panchanga import DAY_LORD_PROPS
except Exception:  # pragma: no cover - defensive
    DAY_LORD_PROPS = {}

try:
    from antar_engine.antar_ephemeris import NAKSHATRA_LORDS
except Exception:  # pragma: no cover
    NAKSHATRA_LORDS = []

# The 27 nakshatras in order — index aligns with NAKSHATRA_LORDS.
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

# Weekday index (Mon=0, matching datetime.weekday()) -> ruling graha.
_WEEKDAY_LORD = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]

# Rahu and Ketu rule nakshatras but never a weekday, so DAY_LORD_PROPS omits
# them. Colours follow the standard chhaya-graha attributions: Rahu smoky and
# variegated, Ketu earthen and flag-coloured.
_SHADOW_COLORS = {
    "Rahu": {"color": "Smoky Grey/Deep Blue", "gem": "Hessonite"},
    "Ketu": {"color": "Brown/Earth/Multicolour", "gem": "Cat's Eye"},
}

# Wearable, non-mystical phrasing. The user should not need to know what a
# nakshatra is to act on this.
_WEAR_HINT = {
    "Sun":     "something warm — saffron, amber, or gold",
    "Moon":    "white or silver — soft, calm tones",
    "Mars":    "red or coral — but keep it to an accent",
    "Mercury": "green — anything from sage to emerald",
    "Jupiter": "yellow or gold — the day rewards it",
    "Venus":   "white, pink, or pale blue",
    "Saturn":  "dark blue, charcoal, or black",
    "Rahu":    "smoky grey or deep blue",
    "Ketu":    "brown or earth tones",
}

# Adverse tara values as emitted by the daily engine.
_ADVERSE_TARA = {"caution", "unfavorable", "unfavourable", "adverse", "difficult"}


def _color_of(planet: str) -> Optional[str]:
    p = (planet or "").strip().title()
    if p in _SHADOW_COLORS:
        return _SHADOW_COLORS[p]["color"]
    entry = DAY_LORD_PROPS.get(p) or {}
    return entry.get("color")


def _gem_of(planet: str) -> Optional[str]:
    p = (planet or "").strip().title()
    if p in _SHADOW_COLORS:
        return _SHADOW_COLORS[p]["gem"]
    return (DAY_LORD_PROPS.get(p) or {}).get("gem")


def nakshatra_lord(nakshatra: str) -> Optional[str]:
    """Lord of a nakshatra by name. None when the name isn't recognised —
    never guess, a wrong lord means a wrong colour."""
    if not nakshatra:
        return None
    n = str(nakshatra).strip().lower()
    for i, name in enumerate(NAKSHATRAS):
        if name.lower() == n:
            return NAKSHATRA_LORDS[i] if i < len(NAKSHATRA_LORDS) else None
    # tolerate spelling variants ("Uttara Bhadrapada" / "Uttarabhadrapada")
    squash = n.replace(" ", "").replace("-", "")
    for i, name in enumerate(NAKSHATRAS):
        if name.lower().replace(" ", "") == squash:
            return NAKSHATRA_LORDS[i] if i < len(NAKSHATRA_LORDS) else None
    return None


def weekday_lord(weekday_index: int) -> str:
    """weekday_index is datetime.weekday() — Monday=0."""
    try:
        return _WEEKDAY_LORD[int(weekday_index) % 7]
    except (TypeError, ValueError):
        return "Sun"


def color_for_day(nakshatra: Optional[str],
                  weekday_index: int,
                  tara_quality: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return today's colour guidance, or None when the inputs are unusable.

    None means "we don't know" and the caller must show nothing — a fabricated
    colour is worse than an absent one, and the whole engine is built on not
    inventing.
    """
    vara = weekday_lord(weekday_index)
    nak_lord = nakshatra_lord(nakshatra)

    vara_color = _color_of(vara)
    nak_color = _color_of(nak_lord) if nak_lord else None
    if not vara_color and not nak_color:
        return None

    adverse = str(tara_quality or "").strip().lower() in _ADVERSE_TARA

    if nak_lord and nak_lord == vara:
        # Both signals agree — one colour, and it is genuinely amplified.
        return {
            "primary":       nak_color,
            "primary_from":  nak_lord,
            "wear":          _WEAR_HINT.get(nak_lord, ""),
            "support":       None,
            "support_from":  None,
            "gem":           _gem_of(nak_lord),
            "why": (f"Both the day and the Moon's nakshatra answer to "
                    f"{nak_lord} today — a single, undiluted colour."),
            "soften": None,
        }

    if adverse and vara_color:
        # Difficult tara: do NOT amplify the nakshatra lord. Lean on the
        # steadier weekday frame and say plainly what to go easy on.
        return {
            "primary":       vara_color,
            "primary_from":  vara,
            "wear":          _WEAR_HINT.get(vara, ""),
            "support":       None,
            "support_from":  None,
            "gem":           _gem_of(vara),
            "why": (f"The Moon sits in a nakshatra that runs against you today, "
                    f"so lean on {vara}'s steadier frame rather than amplifying it."),
            "soften": (f"Go easy on {nak_color}" if nak_color else None),
        }

    # Normal case: the live nakshatra lord leads, the weekday supports.
    if nak_color:
        return {
            "primary":       nak_color,
            "primary_from":  nak_lord,
            "wear":          _WEAR_HINT.get(nak_lord, ""),
            "support":       vara_color,
            "support_from":  vara,
            "gem":           _gem_of(nak_lord),
            "why": (f"The Moon is in {nakshatra}, ruled by {nak_lord} — that is "
                    f"the energy actually live today."),
            "soften": None,
        }

    # No usable nakshatra — fall back to the weekday, which is always true.
    return {
        "primary":       vara_color,
        "primary_from":  vara,
        "wear":          _WEAR_HINT.get(vara, ""),
        "support":       None,
        "support_from":  None,
        "gem":           _gem_of(vara),
        "why":           f"{vara} rules today.",
        "soften":        None,
    }
