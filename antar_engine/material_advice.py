"""
antar_engine/material_advice.py

Lal-Kitab / classical MATERIAL guidance — which COLOURS, GEMSTONES and METALS
support this chart, and which to AVOID, for things a person buys and wears or
keeps close (a watch, a car, a phone case, clothing, a ring).

The mechanism (owner's blue-dial example): each graha owns a colour, a gemstone
and a metal (the classical attributions in daily_panchanga.DAY_LORD_PROPS). When
a graha is AFFLICTED in the chart — sitting in a debt/loss house (6/8/12),
debilitated, carrying a Lal-Kitab rin, or 'sleeping' — carrying its colour/gem/
metal on you every day AMPLIFIES that affliction. A blue dial (Saturn's colour)
on a chart with Saturn in the 8th feeds the very debt/obstruction Saturn is
causing there. Conversely, the colour/gem/metal of a SUPPORTIVE graha (the
ascendant lord, a yogakaraka, a strong trine lord) strengthens the good it does.

This is REMEDIAL guidance (do / avoid to support the chart), not an event
prediction — so it carries no falsifiable accuracy claim. Gemstones are the most
potent lever and are flagged for care; colours and metals are the gentle
everyday choices.

The narrator never names a planet/house/system — only the plain colour/gem/metal
and a plain reason. LLM narrates; this module decides.
"""
from __future__ import annotations

from typing import Optional

try:
    from antar_engine.daily_panchanga import DAY_LORD_PROPS
except Exception:
    DAY_LORD_PROPS = {}
try:
    from antar_engine.d10_career import SIGNS, SIGN_LORD
except Exception:
    SIGNS, SIGN_LORD = [], {}
try:
    from antar_engine.relationships import _dig, _house_of, _combust
except Exception:
    def _dig(p, s): return 0.0, None
    def _house_of(p, pl): return None
    def _combust(p, pl): return False

_KENDRA = {1, 4, 7, 10}
_TRIKONA = {1, 5, 9}
_DUSTHANA = {6, 8, 12}

# Shadow planets have no weekday entry in DAY_LORD_PROPS — add classical metals.
_SHADOW_MATERIAL = {
    "Rahu": {"color": "Smoky Grey/Deep Blue", "gem": "Hessonite (Gomed)", "metal": "Lead/mixed alloy"},
    "Ketu": {"color": "Brown/Earth/Multicolour", "gem": "Cat's Eye (Lehsunia)", "metal": "Mixed alloy (ashtadhatu)"},
}


def _material(planet: str) -> dict:
    """{color, gem, metal} for a graha — classical attributions."""
    p = (planet or "").strip().title()
    if p in _SHADOW_MATERIAL:
        return dict(_SHADOW_MATERIAL[p])
    d = DAY_LORD_PROPS.get(p) or {}
    return {"color": d.get("color", ""), "gem": d.get("gem", ""), "metal": d.get("metal", "")}


def _house_lords_from_lagna(lagna_sign: str) -> dict:
    """house (1..12) -> ruling graha, whole-sign from the ascendant."""
    if lagna_sign not in SIGNS:
        return {}
    li = SIGNS.index(lagna_sign)
    return {h: SIGN_LORD.get(SIGNS[(li + h - 1) % 12]) for h in range(1, 13)}


# Plain-language reasons (NO planet/house names — the narrator keeps that rule).
_WHY_FAVOR = {
    "lagna_lord": "supports your core vitality and footing",
    "yogakaraka": "a genuinely lucky, success-linked choice for you",
    "trikona":    "strengthens support, fortune and ease",
    "strong":     "reinforces a strength you can lean on",
}
_WHY_AVOID = {
    "h6":  "can amplify conflict, debt and health strain",
    "h8":  "can amplify sudden loss, debt and obstacles",
    "h12": "can amplify leakage, expense and things slipping away",
    "debil": "reinforces a weak spot instead of helping",
    "rin":  "feeds an existing debt/karmic pattern",
    "sleeping": "pours energy into a dormant, unhelpful area",
    "func_malefic": "amplifies a part of your life that already runs hard",
}


def _affliction_and_support(planet, chart_data, lk_data, house_lords):
    """Return (favor_score, avoid_score, favor_reason, avoid_reason)."""
    pl = (chart_data.get("planets") or {})
    v = pl.get(planet) or {}
    sign = v.get("sign")
    house = _house_of(planet, pl)
    lords = [h for h, L in house_lords.items() if L == planet]
    lagna_lord = house_lords.get(1)

    fav, avo = 0.0, 0.0
    fr = av = ""

    # ── SUPPORT ────────────────────────────────────────────────
    if planet == lagna_lord:
        fav += 2.0; fr = fr or _WHY_FAVOR["lagna_lord"]
    is_yk = bool(set(lords) & (_KENDRA - {1})) and bool(set(lords) & (_TRIKONA - {1}))
    if is_yk:
        fav += 2.0; fr = _WHY_FAVOR["yogakaraka"]
    if set(lords) & {5, 9}:
        fav += 1.0; fr = fr or _WHY_FAVOR["trikona"]
    _dg = _dig(planet, sign)[1]
    if _dg == "exalted":
        fav += 1.0; fr = fr or _WHY_FAVOR["strong"]
    elif _dg == "own sign":
        fav += 0.5; fr = fr or _WHY_FAVOR["strong"]
    if house in (_KENDRA | _TRIKONA):
        fav += 0.5

    # ── AFFLICTION ─────────────────────────────────────────────
    if house in _DUSTHANA:
        avo += 2.0
        av = _WHY_AVOID[{6: "h6", 8: "h8", 12: "h12"}[house]]
    if _dg == "debilitated":
        avo += 1.5; av = av or _WHY_AVOID["debil"]
    if _combust(planet, pl):
        avo += 0.5
    # functional malefic: lords a dusthana and no trine
    if (set(lords) & _DUSTHANA) and not (set(lords) & _TRIKONA):
        avo += 1.0; av = av or _WHY_AVOID["func_malefic"]
    # ── Lal-Kitab overlays (rin / sleeping) ────────────────────
    try:
        from antar_engine.lal_kitab_advanced import _has_active_rin
        if lk_data and _has_active_rin(planet, lk_data)[0]:
            avo += 1.5; av = av or _WHY_AVOID["rin"]
    except Exception:
        pass
    try:
        from antar_engine.lal_kitab_advanced import detect_sleeping_planets
        if planet in (detect_sleeping_planets(pl) or []):
            avo += 1.0; av = av or _WHY_AVOID["sleeping"]
    except Exception:
        pass

    return fav, avo, fr, av


def material_guidance(chart_data: dict, lk_data: Optional[dict] = None) -> dict:
    """
    {available, favorable[], avoid[], note}.
      favorable/avoid entries: {color, gem, metal, why}  (no planet names)
    Colours/metals are everyday choices; gemstones are potent → carry a caution.
    """
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        if not (cd.get("planets") and lagna):
            return {"available": False}
        house_lords = _house_lords_from_lagna(lagna)
        lagna_lord = house_lords.get(1)

        favorable, avoid = [], []
        for planet in ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                       "Venus", "Saturn", "Rahu", "Ketu"):
            fav, avo, fr, av = _affliction_and_support(planet, cd, lk_data, house_lords)
            mat = _material(planet)
            if not mat.get("color"):
                continue
            entry = {"color": mat["color"], "gem": mat["gem"],
                     "metal": mat["metal"]}
            # AVOID wins on a real affliction — but never tell someone to avoid
            # their ascendant lord's colour unless it is heavily afflicted.
            _hard_avoid = avo >= 2.0 and avo >= fav
            if planet == lagna_lord and avo < 3.0:
                _hard_avoid = False
            if _hard_avoid:
                avoid.append({**entry, "why": av or "can reinforce a strained area for you"})
            elif fav >= 2.0 and fav > avo:
                favorable.append({**entry, "why": fr or "supports you"})

        note = ("Colours and metals are the gentle, everyday levers — safe to act on. "
                "A gemstone is far more potent: get the stone, weight, metal and timing "
                "right with a qualified jeweller-astrologer before wearing one, and never "
                "wear a stone you were told to avoid.")
        return {"available": True, "favorable": favorable[:4],
                "avoid": avoid[:4], "note": note}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


# ── Reverse lookup: assess a SPECIFIC colour the user names ("a blue watch") ──
_COLOR_PLANET = {
    "blue": "Saturn", "navy": "Saturn", "dark blue": "Saturn", "black": "Saturn",
    "purple": "Saturn", "charcoal": "Saturn", "grey": "Saturn", "gray": "Saturn",
    "sky blue": "Venus", "pink": "Venus", "cream": "Venus",
    "red": "Mars", "coral": "Mars", "maroon": "Mars", "crimson": "Mars",
    "green": "Mercury", "emerald": "Mercury", "sage": "Mercury",
    "yellow": "Jupiter", "gold": "Jupiter", "golden": "Jupiter",
    "white": "Moon", "silver": "Moon", "pearl": "Moon",
    "orange": "Sun", "saffron": "Sun", "amber": "Sun",
    "brown": "Ketu", "earth": "Ketu", "smoky": "Rahu",
}


def assess_color(color_word: str, chart_data: dict, lk_data: Optional[dict] = None) -> dict:
    """For a named colour: {available, verdict: favor|avoid|neutral, why, color}."""
    try:
        cw = (color_word or "").strip().lower()
        planet = None
        for k in sorted(_COLOR_PLANET, key=len, reverse=True):  # longest match first
            if k in cw:
                planet = _COLOR_PLANET[k]; break
        if not planet:
            return {"available": False}
        cd = chart_data if isinstance(chart_data, dict) else {}
        lagna = ((cd.get("lagna") or {}).get("sign"))
        if not (cd.get("planets") and lagna):
            return {"available": False}
        house_lords = _house_lords_from_lagna(lagna)
        fav, avo, fr, av = _affliction_and_support(planet, cd, lk_data, house_lords)
        _hard_avoid = avo >= 2.0 and avo >= fav
        if planet == house_lords.get(1) and avo < 3.0:
            _hard_avoid = False
        if _hard_avoid:
            return {"available": True, "verdict": "avoid", "color": color_word,
                    "why": av or "can reinforce a strained area for you"}
        if fav >= 2.0 and fav > avo:
            return {"available": True, "verdict": "favor", "color": color_word,
                    "why": fr or "supports you"}
        return {"available": True, "verdict": "neutral", "color": color_word,
                "why": "neither a strong help nor a real risk for you — fine to choose on taste"}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
