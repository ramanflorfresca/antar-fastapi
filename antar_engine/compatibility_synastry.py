"""
antar_engine/compatibility_synastry.py

Phase-2 synastry computations for the 6-layer compatibility surface.

Net-new STANDARD Parashari astrology (no founder-specific / Lal Kitab rules here
— those live, gated, in lk_cross_conditions.py). Pure functions over the raw
chart dicts. The spine (Compatibility.py) is untouched; the layer mapper
(compatibility_layers.py) reads these to replace the Phase-1 "default 50" stubs:

  - planet_dignity_score      : exaltation / own / friend / neutral / enemy / debilitation
  - house_quality_score       : B's planets in A's house H, scored by dignity
                                (replaces the engine's fixed 70/90/95/85 constants and
                                 extends to houses 10 & 11, which the engine never computed)
  - mercury_cross_compat      : Mercury-to-Mercury harmony (engine only did Venus/Mars)
  - cross_aspect_harmony      : cross-chart graha drishti — Mars 4/7/8, Jupiter 5/7/9,
                                Saturn 3/7/10, all planets 7th — to A's lagna & 7th
"""

from antar_engine.Compatibility import SIGNS, SIGN_RULER, PLANET_FRIENDS

# Standard exaltation / debilitation signs (universally agreed Vedic constants).
EXALTATION = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn", "Mercury": "Virgo",
    "Jupiter": "Cancer", "Venus": "Pisces", "Saturn": "Libra",
}
DEBILITATION = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer", "Mercury": "Pisces",
    "Jupiter": "Capricorn", "Venus": "Virgo", "Saturn": "Aries",
}
BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFICS = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}

_COMPAT_WORD = {"strong": 90, "moderate": 65, "challenging": 40}


def _lagna_idx(chart: dict) -> int:
    lg = chart.get("lagna", {})
    sign = lg.get("sign", "Aries") if isinstance(lg, dict) else "Aries"
    return SIGNS.index(sign) if sign in SIGNS else 0


def planet_dignity_score(planet: str, sign: str) -> float:
    """0-100 dignity of `planet` in `sign` by classical placement."""
    if not sign or sign not in SIGNS:
        return 52.0
    if EXALTATION.get(planet) == sign:
        return 95.0
    if DEBILITATION.get(planet) == sign:
        return 20.0
    ruler = SIGN_RULER.get(sign)
    if ruler == planet:
        return 80.0  # own sign (moolatrikona folded in)
    rel = PLANET_FRIENDS.get(planet, {})
    if ruler in rel.get("friends", []):
        return 65.0
    if ruler in rel.get("enemies", []):
        return 38.0
    return 52.0  # neutral


def _planets_in_house(owner: dict, other: dict, house: int) -> list:
    """Which of `other`'s planets fall in `owner`'s whole-sign house H."""
    owner_lagna = _lagna_idx(owner)
    out = []
    for planet, data in (other.get("planets", {}) or {}).items():
        sign = data.get("sign", "")
        if sign not in SIGNS:
            continue
        h = ((SIGNS.index(sign) - owner_lagna) % 12) + 1
        if h == house:
            out.append((planet, sign))
    return out


def house_quality_score(owner: dict, other: dict, house: int) -> float:
    """
    Quality of `other`'s planet activation in `owner`'s house H, by dignity.
    No activation -> 55 (neutral baseline). Benefics nudge up, malefics down.
    Replaces the engine's fixed constants and works for ANY house (10/11 too).
    """
    occupants = _planets_in_house(owner, other, house)
    if not occupants:
        return 55.0
    total = 0.0
    for planet, sign in occupants:
        d = planet_dignity_score(planet, sign)
        if planet in BENEFICS:
            d += 5
        elif planet in MALEFICS:
            d -= 5
        total += d
    return max(0.0, min(100.0, total / len(occupants)))


def mercury_cross_compat(chart_a: dict, chart_b: dict) -> dict:
    """Mercury-to-Mercury harmony (communication). Mirrors the engine's D9 pattern."""
    ma = (chart_a.get("planets", {}) or {}).get("Mercury", {}).get("sign", "Gemini")
    mb = (chart_b.get("planets", {}) or {}).get("Mercury", {}).get("sign", "Gemini")
    ra = SIGN_RULER.get(ma, "Mercury")
    rb = SIGN_RULER.get(mb, "Mercury")
    if ma == mb or rb in PLANET_FRIENDS.get(ra, {}).get("friends", []):
        word, score = "strong", 90.0
    elif rb in PLANET_FRIENDS.get(ra, {}).get("neutral", []):
        word, score = "moderate", 65.0
    elif rb in PLANET_FRIENDS.get(ra, {}).get("enemies", []):
        word, score = "challenging", 40.0
    else:
        word, score = "moderate", 60.0
    return {"score": score, "label": word, "a_sign": ma, "b_sign": mb}


# Parashari special aspects: house offsets a planet aspects FROM its own position.
_SPECIAL_ASPECTS = {
    "Mars":    [4, 7, 8],
    "Jupiter": [5, 7, 9],
    "Saturn":  [3, 7, 10],
}
_DEFAULT_ASPECTS = [7]


def cross_aspect_harmony(chart_a: dict, chart_b: dict) -> dict:
    """
    Cross-chart graha drishti to A's lagna (house 1) and 7th (partnership).
    Benefic aspects raise harmony, malefic aspects lower it. 0-100, neutral 60.
    Symmetric: also weighs A's planets aspecting B's lagna/7th.
    """
    notable = []

    def aspects_from(owner: dict, other: dict, side: str):
        delta = 0
        owner_lagna = _lagna_idx(owner)
        for planet, data in (other.get("planets", {}) or {}).items():
            sign = data.get("sign", "")
            if sign not in SIGNS:
                continue
            ph = ((SIGNS.index(sign) - owner_lagna) % 12) + 1  # other-planet's house in owner
            offsets = _SPECIAL_ASPECTS.get(planet, _DEFAULT_ASPECTS)
            aspected = {((ph - 1 + (off - 1)) % 12) + 1 for off in offsets}
            for target, label in ((1, "self/identity"), (7, "the partnership")):
                if target in aspected:
                    if planet in BENEFICS:
                        delta += 8
                        notable.append(f"{side}: a supportive influence touches {label}")
                    elif planet in MALEFICS:
                        delta -= 8
                        notable.append(f"{side}: a testing influence touches {label}")
        return delta

    score = 60 + aspects_from(chart_a, chart_b, "their effect on you") \
               + aspects_from(chart_b, chart_a, "your effect on them")
    return {"score": float(max(0, min(100, score))), "notable": notable[:4]}
