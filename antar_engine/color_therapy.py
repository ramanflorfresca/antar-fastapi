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

# [graha-reason 2026-07-20] A colour instruction with no mechanism is a
# horoscope column. "Wear red, avoid green" tells the user nothing and reads as
# superstition; "go easy on green — Mercury is agitated, words land sharper
# than you mean" is a claim they can actually test against their own day.
#
# Each graha therefore carries what it DOES in ordinary life, phrased as
# behaviour rather than mythology. `enhances` is what wearing its colour is
# meant to support; `risk` is what over-amplifying it looks like when the graha
# is already agitated — that is the line used when we tell someone to soften a
# colour. Kept to one short clause each: long explanations get skipped.
_GRAHA_EFFECT = {
    "Sun":     {"enhances": "authority and being seen clearly",
                "risk": "ego hardening into a stand-off with someone senior"},
    "Moon":    {"enhances": "emotional steadiness and reading people well",
                "risk": "moods swinging faster than the situation warrants"},
    "Mars":    {"enhances": "decisiveness and physical drive",
                "risk": "speed turning into conflict you cannot walk back"},
    "Mercury": {"enhances": "clear speech and quick analysis",
                "risk": "words landing sharper than you meant them"},
    "Jupiter": {"enhances": "judgement, generosity and the long view",
                "risk": "over-promising, or expanding past what you can hold"},
    "Venus":   {"enhances": "rapport, taste and easy negotiation",
                "risk": "smoothing over a hard truth that needed saying"},
    "Saturn":  {"enhances": "patience, structure and staying power",
                "risk": "heaviness hardening into delay or isolation"},
    "Rahu":    {"enhances": "unconventional moves and visibility",
                "risk": "overreach, or a shortcut that costs more later"},
    "Ketu":    {"enhances": "focus and depth of research",
                "risk": "withdrawing so far you miss a signal that mattered"},
}


def graha_effect(planet: str) -> Dict[str, str]:
    """What this graha actually does, in behavioural terms. {} when unknown."""
    return _GRAHA_EFFECT.get((planet or "").strip().title(), {})


# [activates 2026-07-20] A colour is only meaningful once the user knows what it
# touches in THEIR chart. The same Saturn colour activates a different area of
# life depending on the lagna, because Saturn rules different houses from
# different ascendants.
#
# House numbers never appear in output. "Activates your 10th house" is jargon
# that means nothing to someone who did not ask for an astrology lesson —
# "activates career and visibility; work matters should move more easily today"
# is the same fact in language they can act on. The number stays internal.
_SIGNS_ORDER = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

_SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# Plain-language life area per house, and what a smooth day there feels like.
_HOUSE_AREA = {
    1:  ("presence and health",          "you should come across the way you intend today"),
    2:  ("money and family",             "money and family matters should sit easier today"),
    3:  ("communication and initiative", "speaking up and reaching out should land well today"),
    4:  ("home and peace of mind",       "home and headspace should feel settled today"),
    5:  ("creativity and children",      "creative work and matters with children go smoothly"),
    6:  ("competition and routine",      "you should hold your ground in anything contested"),
    7:  ("partners and clients",         "one-to-one dealings should go smoothly today"),
    8:  ("shared money and change",      "shared money and anything mid-transition move your way"),
    9:  ("luck, mentors and travel",     "advice and openings should come more easily today"),
    10: ("career and visibility",        "work matters should move smoothly today"),
    11: ("income and networks",          "income and the people around you work in your favour"),
    12: ("rest and letting go",          "stepping back should cost you less than usual"),
}

# The chhaya grahas rule no sign of their own, but they are NOT inert: classically
# Rahu and Ketu act through their DISPOSITOR — the lord of the sign they occupy —
# and take on the colouring of any graha they sit with. Rahu in Libra behaves as
# Venus; Rahu conjunct Saturn takes Saturn's flavour.
#
# Returning "no activation" for them (the first version of this) was wrong, and
# it mattered: Rahu and Ketu rule six of the twenty-seven nakshatras between
# them (Ardra, Swati, Shatabhisha / Ashwini, Magha, Mula), so roughly a fifth of
# all days were losing their activation line.
_NO_RULERSHIP = ("Rahu", "Ketu")


def effective_graha(planet: str, chart_data: Optional[dict] = None) -> str:
    """The graha whose qualities actually apply.

    For Rahu/Ketu this resolves to a conjunct planet if there is one (strongest
    colouring), else the dispositor of the sign they occupy. Everything else
    returns itself. Falls back to the node itself when the chart is unavailable.
    """
    p = (planet or "").strip().title()
    if p not in _NO_RULERSHIP or not isinstance(chart_data, dict):
        return p
    planets = chart_data.get("planets") or {}
    own_sign = (planets.get(p) or {}).get("sign")
    if not own_sign:
        return p
    # 1. conjunction wins — a node with a graha takes that graha's nature.
    #    With MORE than one graha in the sign, pick the closest by degree: dict
    #    order is insertion order and has no astrological meaning, so choosing
    #    "the first one found" would silently pick different planets for
    #    identical charts.
    own_deg = (planets.get(p) or {}).get("degree")
    conj = [(other, (d or {}).get("degree"))
            for other, d in planets.items()
            if other not in (p, "Rahu", "Ketu") and (d or {}).get("sign") == own_sign]
    if conj:
        if own_deg is not None and all(dg is not None for _, dg in conj):
            conj.sort(key=lambda t: abs(float(t[1]) - float(own_deg)))
        else:
            conj.sort(key=lambda t: t[0])   # stable, not arbitrary
        return conj[0][0]
    # 2. otherwise the dispositor of the occupied sign
    return _SIGN_LORD.get(own_sign, p)


def houses_ruled(planet: str, lagna_sign: str) -> list:
    """Which houses this graha rules from the given lagna. [] when unknown."""
    p = (planet or "").strip().title()
    lag = (lagna_sign or "").strip().title()
    if p in _NO_RULERSHIP or lag not in _SIGNS_ORDER:
        return []
    li = _SIGNS_ORDER.index(lag)
    return [((_SIGNS_ORDER.index(sign) - li) % 12) + 1
            for sign, lord in _SIGN_LORD.items() if lord == p]


def activation_for(planet: str, lagna_sign: str,
                   chart_data: Optional[dict] = None) -> Dict[str, Any]:
    """What wearing this graha's colour actually activates, in plain words.

    Returns {} when the lagna is unknown or the graha rules nothing — the
    surface then shows the colour without an activation line rather than
    guessing at someone's life.
    """
    # Rahu/Ketu resolve to whatever graha actually carries them.
    acting = effective_graha(planet, chart_data)
    houses = houses_ruled(acting, lagna_sign)
    if not houses:
        return {}
    # Where a graha rules two houses, lead with the more publicly consequential
    # one. 10 and 11 outrank 1; the 12th is the least actionable, so it trails.
    _rank = {10: 0, 11: 1, 7: 2, 2: 3, 9: 4, 5: 5, 4: 6, 3: 7, 1: 8, 6: 9, 8: 10, 12: 11}
    houses = sorted(houses, key=lambda h: _rank.get(h, 99))
    # A graha can rule two houses. Name only the leading one: joining both with
    # "and" produced "money and family and how you come across", which is worse
    # than saying less. The second house still informs the ranking above.
    primary = houses[0]
    area, outcome = _HOUSE_AREA[primary]
    return {
        "areas":   area,
        "outcome": outcome,
        "houses":  houses,          # internal only — never render this
    }


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


def _wear_reason(planet: str, lagna_sign: Optional[str] = None,
                 chart_data: Optional[dict] = None) -> str:
    """One clause explaining the colour.

    Prefers the CHART-SPECIFIC activation when the lagna is known — that is the
    version the user can act on, because it names their own life areas. Falls
    back to the generic behavioural effect otherwise. No house numbers, ever.
    """
    act = activation_for(planet, lagna_sign, chart_data) if lagna_sign else {}
    if act:
        return f"activates {act['areas']} &mdash; {act['outcome']}".replace("&mdash;", "\u2014")
    e = graha_effect(effective_graha(planet, chart_data))
    return f"supports {e['enhances']}" if e.get("enhances") else ""


def _soften_reason(planet: str) -> str:
    """One clause: why NOT to amplify this graha today. This is the line that
    turns 'avoid green' from superstition into something testable."""
    e = graha_effect(planet)
    return e.get("risk", "")


def resolve_day_graha(nakshatra: Optional[str],
                      weekday_index: int,
                      tara_quality: Optional[str] = None) -> Dict[str, Any]:
    """Which graha the day's remedial advice should follow, and how.

    [day-graha 2026-07-20] Shared by colour AND food so the day card gives ONE
    coherent instruction ("wear saffron, eat warm golden foods") instead of two
    unrelated ones derived from different planets.

    Returns:
      planet   - the graha to work with
      mode     - 'strengthen' on a workable tara, 'balance' on an adverse one.
                 Adverse tara must NOT amplify the nakshatra lord; classical
                 remedy pacifies instead, and food has a direct analogue
                 (balance_with / cooling foods vs strengthen_with).
      source   - 'both' | 'nakshatra' | 'vara', for explaining the choice
      soften   - the graha to go easy on, when we deliberately stepped away
                 from the nakshatra lord
    """
    vara = weekday_lord(weekday_index)
    nak_lord = nakshatra_lord(nakshatra)
    adverse = str(tara_quality or "").strip().lower() in _ADVERSE_TARA

    if nak_lord and nak_lord == vara:
        return {"planet": nak_lord, "mode": "balance" if adverse else "strengthen",
                "source": "both", "soften": None, "vara": vara, "nakshatra_lord": nak_lord}
    if adverse:
        # lean on the steadier weekday frame, pacify rather than amplify
        return {"planet": vara, "mode": "balance", "source": "vara",
                "soften": nak_lord, "vara": vara, "nakshatra_lord": nak_lord}
    if nak_lord:
        return {"planet": nak_lord, "mode": "strengthen", "source": "nakshatra",
                "soften": None, "vara": vara, "nakshatra_lord": nak_lord}
    return {"planet": vara, "mode": "strengthen", "source": "vara",
            "soften": None, "vara": vara, "nakshatra_lord": None}


def color_for_day(nakshatra: Optional[str],
                  weekday_index: int,
                  tara_quality: Optional[str] = None,
                  lagna_sign: Optional[str] = None,
                  chart_data: Optional[dict] = None) -> Optional[Dict[str, Any]]:
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
            "why_wear": _wear_reason(nak_lord, lagna_sign, chart_data),
            "soften": None,
            "why_soften": None,
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
            "why_wear": _wear_reason(vara, lagna_sign, chart_data),
            "soften": (f"Go easy on {nak_color}" if nak_color else None),
            "why_soften": _soften_reason(nak_lord),
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
            "why_wear": _wear_reason(nak_lord, lagna_sign, chart_data),
            "soften": None,
            "why_soften": None,
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
        "why_wear":      _wear_reason(vara, lagna_sign, chart_data),
        "soften":        None,
        "why_soften":    None,
    }
