"""
antar_engine/child_gender.py
============================
Classical progeny-gender leaning (a "boy or girl" indication).

This is NOT a house-strength question (which is why it does not belong in the
ask channel-role map) and NOT a medical determination. It is the traditional
Jyotish reading: gender is judged by the interplay of MALE / FEMALE / NEUTER
planets and ODD / EVEN signs across the progeny significators —

  • the 5th house (santana bhava) and its lord,
  • Jupiter, the putrakaraka (child-significator),
  • the D7 saptamsha (the divisional chart FOR progeny) — its 5th house,
    5th lord, and occupants.

Odd signs (Aries, Gemini, Leo, Libra, Sagittarius, Aquarius — the 1st, 3rd,
5th … signs, i.e. even sign_index) are male; even signs are female. Male
planets are Sun/Mars/Jupiter; female are Moon/Venus; Mercury and Saturn are
neuter and Rahu/Ketu shadowy (they cast no gender vote). Predominance decides,
and — being probabilistic in the classics — the result is reported as a
LEANING with its factor breakdown, never a certainty.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from antar_engine.antar_ephemeris import SIGNS, SIGN_LORDS

_MALE_PLANETS = {"Sun", "Mars", "Jupiter"}
_FEMALE_PLANETS = {"Moon", "Venus"}
# Mercury, Saturn = neuter; Rahu, Ketu = shadowy → no gender vote.


def _sidx(value) -> Optional[int]:
    """Sign index 0..11 from a sign name or an int."""
    if isinstance(value, int) and 0 <= value <= 11:
        return value
    if isinstance(value, str) and value in SIGNS:
        return SIGNS.index(value)
    return None


def _sign_vote(sign_index: Optional[int]) -> Optional[str]:
    """Odd sign (even index) = male; even sign (odd index) = female."""
    if sign_index is None:
        return None
    return "male" if sign_index % 2 == 0 else "female"


def _planet_vote(planet: str) -> Optional[str]:
    if planet in _MALE_PLANETS:
        return "male"
    if planet in _FEMALE_PLANETS:
        return "female"
    return None  # neuter / shadowy → abstains


def _planet_sign_index(planets: dict, planet: str) -> Optional[int]:
    d = (planets or {}).get(planet)
    if isinstance(d, dict):
        si = d.get("sign_index")
        if isinstance(si, int):
            return si
        return _sidx(d.get("sign"))
    return None


def _occupants(planets: dict, house: int) -> List[str]:
    out = []
    for p, d in (planets or {}).items():
        if isinstance(d, dict) and d.get("house") == house:
            out.append(p)
    return out


def child_gender_signal(chart_data: dict) -> Dict[str, Any]:
    """
    Return a progeny-gender leaning with its factor breakdown:
      {leaning: 'boy'|'girl'|'mixed', male: int, female: int,
       factors: [ {source, detail, vote} ... ]}
    Empty {} if the chart lacks the data to judge.
    """
    if not isinstance(chart_data, dict):
        return {}
    planets = chart_data.get("planets") or {}
    house_lords = chart_data.get("house_lords") or {}
    if not planets or not house_lords:
        return {}

    factors: List[Dict[str, Any]] = []

    def add(source: str, detail: str, vote: Optional[str], weight: int = 1):
        if vote in ("male", "female"):
            factors.append({"source": source, "detail": detail,
                            "vote": vote, "weight": weight})

    # ── D1: 5th house, its lord, occupants, and the karaka Jupiter ──────────
    h5 = house_lords.get("5") or house_lords.get(5) or {}
    fifth_sign = h5.get("sign") if isinstance(h5, dict) else None
    fifth_lord = h5.get("lord") if isinstance(h5, dict) else None

    add("5th house sign", str(fifth_sign),
        _sign_vote(_sidx(fifth_sign)), weight=2)          # santana bhava — primary

    if fifth_lord:
        lsi = _planet_sign_index(planets, fifth_lord)
        lsign = SIGNS[lsi] if isinstance(lsi, int) else "?"
        add("5th-lord's sign", f"{fifth_lord} in {lsign}", _sign_vote(lsi))
        add("5th-lord's nature", fifth_lord, _planet_vote(fifth_lord))

    for pl in _occupants(planets, 5):
        add("planet in the 5th", pl, _planet_vote(pl))

    jsi = _planet_sign_index(planets, "Jupiter")
    jsign = SIGNS[jsi] if isinstance(jsi, int) else "?"
    add("Jupiter (child-significator) sign", f"Jupiter in {jsign}", _sign_vote(jsi))

    # ── D7 saptamsha: THE progeny varga — 5th house, 5th lord, occupants ────
    dc = chart_data.get("divisional_charts") or {}
    d7 = dc.get("d7") or dc.get("D7") or {}
    d7_planets = d7.get("planets") or {}
    d7_lagna_si = _sidx(d7.get("lagna"))
    if d7_lagna_si is not None:
        d7_fifth_si = (d7_lagna_si + 4) % 12
        d7_fifth_sign = SIGNS[d7_fifth_si]
        add("D7 5th-house sign", d7_fifth_sign,
            _sign_vote(d7_fifth_si), weight=2)            # progeny varga — primary
        d7_fifth_lord = SIGN_LORDS.get(d7_fifth_sign)
        if d7_fifth_lord:
            lsi = _planet_sign_index(d7_planets, d7_fifth_lord)
            lsign = SIGNS[lsi] if isinstance(lsi, int) else "?"
            add("D7 5th-lord's sign", f"{d7_fifth_lord} in {lsign}", _sign_vote(lsi))
        for pl in _occupants(d7_planets, 5):
            add("planet in the D7 5th", pl, _planet_vote(pl))

    if not factors:
        return {}

    male = sum(f["weight"] for f in factors if f["vote"] == "male")
    female = sum(f["weight"] for f in factors if f["vote"] == "female")
    if male > female:
        leaning = "boy"
    elif female > male:
        leaning = "girl"
    else:
        leaning = "mixed"
    return {"leaning": leaning, "male": male, "female": female, "factors": factors}
