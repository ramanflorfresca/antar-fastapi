"""
antar_engine/relationship_pattern.py

LAYER 1 of the relationship reading — the PROMISE: what kind of love life does this person have?

  • Which house the bond RUNS ON. The 5th governs falling in love; the 7th governs staying. A 5th-heavy chart
    with a thin 7th produces intense romances that dissolve at the threshold of commitment; a 7th-led chart is slower
    to fall and steadier once in. For "will he come back" the first diagnostic is which house the CURRENT period is
    running on: a 5th-lord period rekindling an old flame is a different thing from a 7th-lord period doing so.
  • Venus — the capacity for love and what love feels like. Retrograde Venus = renegotiation, old partners and old
    patterns coming back. Framed as THE READER's pattern, never as a verdict on an ex.
  • The Moon — emotional need and attachment style. A strong 7th with the reader convinced of being unloved is
    usually this attachment pattern, not proof of absent feeling in the other person.

Pure + fail-open. Reuses relationships.py's dignity / aspect helpers. The facts are plain life-language (no planet,
house or sign names reach the narrator as vocabulary to repeat). v1, classical defaults, UNVALIDATED against dated
outcomes - a principled first pass. Retrograde is not stored on saved charts, so it is computed from birth_jd.
"""
from __future__ import annotations

from typing import Optional

from antar_engine.d10_career import SIGNS, SIGN_LORD, _sign_n_from
from antar_engine.relationships import (
    _benefics_on, _combust, _conj_malefics, _dig, _house_of, _malefics_on)

_GOOD_PLACES = {1, 4, 5, 7, 9, 10, 11}
_ELEMENT = {
    "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
    "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
    "Gemini": "air", "Libra": "air", "Aquarius": "air",
    "Cancer": "water", "Scorpio": "water", "Pisces": "water",
}
_MOON_NEED = {
    "water": "needs emotional security and closeness first — feels everything deeply and bonds through feeling safe",
    "earth": "needs steadiness and proof through consistency — trusts what shows up reliably over time",
    "fire": "needs warmth, appreciation and room to act — bonds through energy and being admired for who they are",
    "air": "needs conversation and mental connection — bonds through talking, and can pull back when overwhelmed",
}


# ── retrograde: not stored on saved charts, so derive it from the birth moment ──
def is_retrograde(chart_data: dict, planet: str) -> Optional[bool]:
    """True/False from the planet's motion at birth; None when it cannot be computed."""
    try:
        v = (chart_data.get("planets") or {}).get(planet) or {}
        if isinstance(v.get("is_retrograde"), bool):
            return v["is_retrograde"]
        jd = chart_data.get("birth_jd") or chart_data.get("birth_jd_ut")
        if jd is None or v.get("longitude") is None:
            return None
        from antar_engine.antar_ephemeris import planet_longitude, lahiri_ayanamsa
        from antar_engine.vedic_enrichment import compute_retrograde
        jd = float(jd)
        t1 = (planet_longitude(planet, jd + 1) - lahiri_ayanamsa(jd + 1)) % 360
        return bool(compute_retrograde(planet, float(v["longitude"]), t1))
    except Exception:
        return None


# ── 5th vs 7th ──────────────────────────────────────────────────────────────────
def _house_strength(planets: dict, lagna: str, h: int) -> dict:
    sign = _sign_n_from(lagna, h)
    lord = SIGN_LORD.get(sign)
    lv = planets.get(lord) or {}
    score, why = 0.0, []
    d, lab = _dig(lord, lv.get("sign"))
    if d > 0:
        score += 1.0 if d < 2 else 1.5; why.append(f"its lord is {lab}")
    elif d < 0:
        score -= 1.5; why.append("its lord is debilitated")
    lh = lv.get("house")
    if lh in (6, 8, 12):
        score -= 1.2; why.append("its lord sits in a house of loss or strain")
    elif lh in _GOOD_PLACES:
        score += 0.5
    ben = _benefics_on(planets, h)
    score += 0.8 * len([b for b in ben if b in ("Jupiter", "Venus")]) + 0.3 * len([b for b in ben if b in ("Mercury", "Moon")])
    if any(b in ("Jupiter", "Venus") for b in ben):
        why.append("a benefic supports it")
    for m in _malefics_on(planets, h):
        score -= {"Saturn": 0.9, "Rahu": 0.8, "Ketu": 0.8, "Mars": 0.7, "Sun": 0.4}.get(m, 0.5)
        why.append(f"{m} presses on it")
    return {"score": round(score, 2), "lord": lord, "why": why}


def _love_style(s5: float, s7: float) -> str:
    # thresholds sit at the quartiles of the score spread over 205 stored charts (median about -0.2, p75 0.6, p25 -1.2)
    if s5 >= 0.6 and s7 >= 0.6:
        return "balanced_strong"
    if s5 <= -1.2 and s7 <= -1.2:
        return "thin_both"
    if s5 - s7 >= 1.5 and s5 >= -0.2:
        return "falls_in_easily"
    if s7 - s5 >= 1.5 and s7 >= -0.2:
        return "slow_then_steady"
    return "balanced"


def _period_running_on(planets: dict, lagna: str, dashas: dict) -> dict:
    """Which of the two houses the CURRENT period (main, sub, inner) is wired to: rules it or sits in it."""
    try:
        from antar_engine.people_pointer import _running
        run = _running(dashas or {})
    except Exception:
        run = {}
    if not run:
        return {"on": None, "running": {}}
    l5, l7 = SIGN_LORD.get(_sign_n_from(lagna, 5)), SIGN_LORD.get(_sign_n_from(lagna, 7))
    w5 = w7 = 0.0
    for key, wt in (("md", 2.0), ("ad", 2.0), ("pd", 1.0)):
        p = run.get(key)
        if not p:
            continue
        h = _house_of(p, planets)
        if p == l5 or h == 5:
            w5 += wt
        if p == l7 or h == 7:
            w7 += wt
    on = ("both" if w5 >= 2 and w7 >= 2 else "5th" if w5 > w7 and w5 >= 2 else "7th" if w7 > w5 and w7 >= 2
          else "neither")
    return {"on": on, "w5": w5, "w7": w7, "running": run}


# ── Venus ───────────────────────────────────────────────────────────────────────
def _venus(chart_data: dict) -> dict:
    planets = chart_data.get("planets") or {}
    v = planets.get("Venus") or {}
    if not v:
        return {"state": "unknown", "retrograde": None, "flags": [], "relief": []}
    score, flags, relief = 0.0, [], []
    d, lab = _dig("Venus", v.get("sign"))
    if d > 0:
        score += 1.5 if d >= 2 else 1.0; relief.append(f"Venus is {lab}")
    elif d < 0:
        score -= 1.5; flags.append("Venus is debilitated")
    h = v.get("house")
    if h in (6, 8, 12):
        score -= 1.0; flags.append("Venus sits in a house of strain or loss")
    elif h in (1, 4, 5, 7, 9, 10, 11):
        score += 0.6; relief.append("Venus is well placed")
    if _combust("Venus", planets):
        score -= 0.8; flags.append("Venus is combust")
    conj = _conj_malefics("Venus", planets)
    if conj:
        score -= 0.7 * len(conj); flags.append(f"Venus sits with {'/'.join(conj)}")
    retro = is_retrograde(chart_data, "Venus")
    state = "warm" if score >= 1.2 else "strained" if score <= -1.0 else "mixed"
    return {"state": state, "score": round(score, 2), "retrograde": retro, "flags": flags, "relief": relief}


# ── the Moon ────────────────────────────────────────────────────────────────────
def _moon(chart_data: dict) -> dict:
    planets = chart_data.get("planets") or {}
    m = planets.get("Moon") or {}
    if not m:
        return {"element": None, "need": None, "pattern": None}
    el = _ELEMENT.get(m.get("sign"))
    h = m.get("house")
    mates = [p for p, v in planets.items() if isinstance(v, dict) and p != "Moon" and v.get("house") == h]
    pattern = None
    if "Saturn" in mates:
        pattern = "guarded"          # slow to trust, holds back
    elif "Rahu" in mates:
        pattern = "intense_anxious"  # intense, can swing between craving and doubt
    elif "Ketu" in mates:
        pattern = "withdrawing"      # feels private, can detach
    elif "Mars" in mates:
        pattern = "reactive"
    elif "Sun" in mates:
        pattern = "proud"
    return {"element": el, "need": _MOON_NEED.get(el), "pattern": pattern, "house": h}


_PATTERN_TXT = {
    "guarded": "slow to trust and quick to hold back — it can look like coolness when it is really caution",
    "intense_anxious": "intense in attachment, and can swing between craving closeness and doubting it",
    "withdrawing": "private about feelings, and inclined to pull away when closeness gets heavy",
    "reactive": "quick to react when hurt, then quick to cool",
    "proud": "needs to feel respected as well as loved, and finds it hard to ask",
}
_STYLE_TXT = {
    "balanced_strong": "Both the 'falling in love' side and the 'staying' side of this chart are well supported — love tends to start and to last.",
    "thin_both": "Neither the 'falling in love' side nor the 'staying' side is strongly supported — love here asks for deliberate effort at both stages.",
    "falls_in_easily": "This chart falls in love more easily than it commits: romance and attraction are the strong side, staying power is the weaker one — intense starts that can dissolve at the threshold of commitment.",
    "slow_then_steady": "This chart is slower to fall in love but steadier once in: commitment is the strong side, romance takes longer to ignite.",
    "balanced": "The 'falling in love' side and the 'staying' side of this chart are about even.",
}
_RUNNING_TXT = {
    "5th": "THE PERIOD NOW RUNS ON ROMANCE AND ATTRACTION. A spark, or an old flame, can feel strong in this stretch — but that is the 'falling in' side, not proof of staying power. Say this plainly.",
    "7th": "THE PERIOD NOW RUNS ON COMMITMENT AND PARTNERSHIP. What starts or restarts now is more likely to be a conversation about something lasting, not just a spark.",
    "both": "THE PERIOD NOW TOUCHES BOTH ROMANCE AND COMMITMENT. Attraction and a serious conversation can both be live; the second is the one to act on.",
    "neither": "THE PERIOD NOW IS NOT BUILT AROUND ROMANCE OR COMMITMENT. Love is not the main thing this stretch is about — do not read a spark or a silence as more than that.",
}


def analyze_pattern(chart_data: dict, dashas: Optional[dict] = None) -> dict:
    """{available, love_style, s5, s7, running_on, venus{}, moon{}, facts[]}. Never raises."""
    try:
        cd = chart_data if isinstance(chart_data, dict) else {}
        planets = cd.get("planets") or {}
        lagna = (cd.get("lagna") or {}).get("sign")
        if not planets or lagna not in SIGNS:
            return {"available": False}
        h5, h7 = _house_strength(planets, lagna, 5), _house_strength(planets, lagna, 7)
        style = _love_style(h5["score"], h7["score"])
        run = _period_running_on(planets, lagna, dashas or {})
        venus, moon = _venus(cd), _moon(cd)
        facts = ["HOW THIS PERSON LOVES (their own pattern, from their side): " + _STYLE_TXT[style]]
        if run.get("on"):
            facts.append(_RUNNING_TXT[run["on"]])
        if venus["state"] != "unknown":
            line = {"warm": "Love comes warmly to this person and they know what they want in it.",
                    "mixed": "Love comes to this person with some push and pull between wanting and getting.",
                    "strained": "Love tends to come with strain for this person: high standards, delays, or choosing hard."}[venus["state"]]
            if venus["retrograde"]:
                line += (" They tend to REVISIT and renegotiate love: old partners and old patterns can come back. "
                         "This is THEIR pattern, never a verdict on what any ex will do.")
            facts.append(line)
        if moon.get("need"):
            line = f"Emotionally this person {moon['need']}."
            if moon.get("pattern"):
                line += f" They tend to be {_PATTERN_TXT[moon['pattern']]}."
                if moon["pattern"] in ("guarded", "intense_anxious", "withdrawing"):
                    line += (" Feeling unloved while the bond is actually strong is usually this attachment pattern, "
                             "not proof that the other person's feeling is missing.")
            facts.append(line)
        facts.append("EPISTEMICS: this is the reader's own pattern and the shape of the current stretch. It never says what another "
                     "person feels or will do.")
        return {"available": True, "love_style": style, "s5": h5["score"], "s7": h7["score"], "house5": h5, "house7": h7,
                "running_on": run.get("on"), "running": run.get("running"), "venus": venus, "moon": moon, "facts": facts}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
