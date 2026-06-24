"""
antar_engine/profession/profession_signature.py  —  PRIMARY SIGNATURE

Standing-chart vocational read. NOT KP, no horary, no number. Pure longitude
math off the stored chart_data (no Swiss Ephemeris needed at call time).

THREE SOURCES THAT SHOULD CONVERGE
  1. D10 (Dasamsa) — what the work IS:
        D10 lagna lord, planets in/aspecting the D10 10th, strongest D10 planet.
  2. Amatyakaraka + its D1 HOUSE connection (the heart of it):
        AmK -> 10th = mainstream career / status
        AmK -> 5th  = creative / speculative / education / performance
        AmK -> 8th  = research / transformation / OPM / occult / crisis work
        AmK -> 3rd  = communication / media / self-effort / entrepreneurship
        AmK -> 7th  = business / partnership / public-facing
  3. Karakamsa + 10th-from-Karakamsa — the soul's vocation.

STRENGTH GATE
  A signature becomes a recommendation only if its driving planet is dignified
  (exalted or own) in D1 OR D10 OR D9 — D10 counts DOUBLE (it is the career
  chart). Conviction points: D1=1, D9=1, D10=2.

This module returns the structural read + dignity/convergence bookkeeping. The
archetype + modern arenas are built in profession_archetype.py; the gate +
jargon-free surface live in profession_service.py.
"""

from __future__ import annotations

from ..d_charts_calculator import (
    SIGNS, SIGN_INDEX, SIGN_LORDS,
    get_d_chart, get_d1_from_chart_data, get_house_sign, get_planets_in_house,
    _planet_strength,
)
from ..karakas import get_all_karakas

CLASSICAL = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
# fixed tie-break order (natural karaka seniority for work / authority)
_TIEBREAK = {"Sun": 0, "Saturn": 1, "Jupiter": 2, "Mars": 3,
             "Mercury": 4, "Venus": 5, "Moon": 6, "Rahu": 7, "Ketu": 8}

# Amatyakaraka D1-house -> arena family (the 5 canonical ones are verbatim from
# the doctrine; the rest are sensible completions so no house is a dead end).
AMK_HOUSE_FAMILY = {
    10: ("mainstream", "mainstream career, status and institutional rank"),
    5:  ("creative", "creative, speculative, education and performance work"),
    8:  ("research", "research, transformation, other-people's-money and depth work"),
    3:  ("communication", "communication, media, self-effort and entrepreneurship"),
    7:  ("partnership", "business, partnership and public-facing work"),
    1:  ("self", "self-driven, independent practice and personal craft"),
    2:  ("resources", "wealth-building, finance and a trusted voice"),
    4:  ("foundations", "property, land, a home base and tangible assets"),
    6:  ("service", "service, problem-solving, health and daily systems"),
    9:  ("dharma", "teaching, law, publishing and belief systems"),
    11: ("gains", "networks, large gains and scaled distribution"),
    12: ("retreat", "behind-the-scenes, foreign, research-seclusion or contemplative work"),
}

# Whole-sign aspects (counting houses, 1-indexed from the aspecting planet's sign)
_ASPECTS = {
    "Sun": [7], "Moon": [7], "Mercury": [7], "Venus": [7],
    "Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10],
    "Rahu": [5, 7, 9], "Ketu": [5, 7, 9],
}

_DIGNITY_RANK = {"exalted": 3, "own": 2, "neutral": 1, "debilitated": 0}


def _house_of(sign_index: int, lagna_index: int) -> int:
    return ((sign_index - lagna_index) % 12) + 1


def _is_dignified(strength: str) -> bool:
    return strength in ("exalted", "own")


def _strongest_planet(d_chart: dict, prefer_house_idx=None, lagna_idx=None) -> str:
    """Strongest classical planet in a D-chart by dignity, with house + tie-break."""
    best, best_key = None, None
    for p in CLASSICAL:
        pos = d_chart.get(p, {})
        rank = _DIGNITY_RANK.get(pos.get("strength", "neutral"), 1)
        in_focus = 0
        if prefer_house_idx is not None and lagna_idx is not None:
            if pos.get("sign_index") == prefer_house_idx:
                in_focus = 1
        # higher dignity, then in-focus-house, then seniority (lower tie-break)
        key = (rank, in_focus, -_TIEBREAK.get(p, 9))
        if best_key is None or key > best_key:
            best_key, best = key, p
    return best


def compute_profession_signature(chart_data: dict) -> dict:
    """
    Returns the raw structural vocational read + dignity/convergence bookkeeping.
    No narration here.
    """
    d1 = get_d1_from_chart_data(chart_data)
    d9 = get_d_chart(chart_data, 9)
    d10 = get_d_chart(chart_data, 10)

    # ── Source 1: D10 (what the work IS) ─────────────────────────────
    d10_lagna_sign = d10["Lagna"]["sign"]
    d10_lagna_idx = SIGN_INDEX[d10_lagna_sign]
    d10_lagna_lord = SIGN_LORDS[d10_lagna_sign]
    d10_tenth_sign = get_house_sign(d10_lagna_sign, 10)
    d10_tenth_idx = SIGN_INDEX[d10_tenth_sign]
    d10_tenth_lord = SIGN_LORDS[d10_tenth_sign]
    d10_tenth_occupants = get_planets_in_house(d10, d10_lagna_sign, 10)

    # planets aspecting the D10 10th house
    d10_tenth_aspectors = []
    for p in CLASSICAL + ["Rahu", "Ketu"]:
        pos = d10.get(p)
        if not pos:
            continue
        psign = pos.get("sign_index")
        if psign is None:
            continue
        for h in _ASPECTS.get(p, [7]):
            if (psign + h - 1) % 12 == d10_tenth_idx:
                d10_tenth_aspectors.append(p)
                break

    d10_strongest = _strongest_planet(d10, prefer_house_idx=d10_tenth_idx,
                                      lagna_idx=d10_lagna_idx)

    # ── Source 2: Amatyakaraka + its D1 house ────────────────────────
    karakas = get_all_karakas(chart_data)  # rank1=AK ... rank2=AmK
    ak_planet = karakas[0]["planet"] if karakas else "Sun"
    amk_planet = karakas[1]["planet"] if len(karakas) > 1 else "Jupiter"

    d1_lagna_sign = chart_data["lagna"]["sign"]
    d1_lagna_idx = SIGN_INDEX[d1_lagna_sign]
    amk_sign = d1.get(amk_planet, {}).get("sign", "")
    amk_sign_idx = SIGN_INDEX.get(amk_sign, 0)
    amk_house = _house_of(amk_sign_idx, d1_lagna_idx)
    amk_family, amk_family_text = AMK_HOUSE_FAMILY.get(
        amk_house, ("mainstream", "mainstream career and status"))

    # ── Source 3: Karakamsa + 10th-from ──────────────────────────────
    kk_sign = d9.get(ak_planet, {}).get("sign", "")
    kk_sign_idx = SIGN_INDEX.get(kk_sign, 0)
    kk_lord = SIGN_LORDS.get(kk_sign, "")
    tenth_from_kk_idx = (kk_sign_idx + 9) % 12
    tenth_from_kk_sign = SIGNS[tenth_from_kk_idx]
    tenth_from_kk_lord = SIGN_LORDS[tenth_from_kk_sign]
    # planets sitting in the 10th-from-Karakamsa, read in the rasi (D1)
    tenth_from_kk_occupants = [
        p for p in CLASSICAL + ["Rahu", "Ketu"]
        if d1.get(p, {}).get("sign_index") == tenth_from_kk_idx
    ]

    # ── Career-weight aggregation across the three sources ───────────
    weights: dict[str, float] = {}
    sources: dict[str, set] = {}

    def add(planet, w, source):
        if not planet:
            return
        weights[planet] = weights.get(planet, 0.0) + w
        sources.setdefault(planet, set()).add(source)

    add(d10_lagna_lord, 3.0, "D10")
    add(d10_tenth_lord, 3.0, "D10")
    for p in d10_tenth_occupants:
        add(p, 2.0, "D10")
    for p in d10_tenth_aspectors:
        add(p, 1.0, "D10")
    add(d10_strongest, 2.0, "D10")
    add(amk_planet, 2.5, "AmK")
    add(kk_lord, 2.0, "Karakamsa")
    add(tenth_from_kk_lord, 1.5, "Karakamsa")
    for p in tenth_from_kk_occupants:
        add(p, 1.5, "Karakamsa")

    # dominant driving planet (skip nodes for the archetype — they have no
    # ownerships/dignity in the classical sense; they remain in arenas/evidence)
    ranked = sorted(
        weights.items(),
        key=lambda kv: (kv[1], len(sources.get(kv[0], set())),
                        -_TIEBREAK.get(kv[0], 9)),
        reverse=True,
    )
    dominant = None
    for p, _w in ranked:
        if p in CLASSICAL:
            dominant = p
            break
    if dominant is None and ranked:
        dominant = ranked[0][0]

    # ── Strength gate / conviction (D10 double) ──────────────────────
    def dignity_points(planet):
        pts, where = 0, []
        if _is_dignified(d1.get(planet, {}).get("strength", "neutral")):
            pts += 1; where.append("D1")
        if _is_dignified(d9.get(planet, {}).get("strength", "neutral")):
            pts += 1; where.append("D9")
        if _is_dignified(d10.get(planet, {}).get("strength", "neutral")):
            pts += 2; where.append("D10x2")
        return pts, where

    dom_points, dom_where = dignity_points(dominant) if dominant else (0, [])
    if dom_points >= 3:
        conviction = "strong"
    elif dom_points >= 1:
        conviction = "supported"
    else:
        conviction = "exploratory"

    # convergence: how many of the 3 source-groups name the dominant planet
    dom_sources = sources.get(dominant, set())
    convergence_count = len(dom_sources & {"D10", "AmK", "Karakamsa"})
    converged = convergence_count >= 2

    return {
        "dominant_planet": dominant,
        "conviction": conviction,
        "converged": converged,
        "convergence_count": convergence_count,
        "dominant_sources": sorted(dom_sources),
        "strength_gate_passed": dom_points >= 1,
        "dignity_points": dom_points,
        "dignity_where": dom_where,
        "d10": {
            "lagna_sign": d10_lagna_sign,
            "lagna_lord": d10_lagna_lord,
            "tenth_sign": d10_tenth_sign,
            "tenth_lord": d10_tenth_lord,
            "tenth_occupants": d10_tenth_occupants,
            "tenth_aspectors": d10_tenth_aspectors,
            "strongest_planet": d10_strongest,
        },
        "amk": {
            "planet": amk_planet,
            "d1_sign": amk_sign,
            "d1_house": amk_house,
            "family": amk_family,
            "family_text": amk_family_text,
        },
        "karakamsa": {
            "atmakaraka": ak_planet,
            "sign": kk_sign,
            "lord": kk_lord,
            "tenth_from_sign": tenth_from_kk_sign,
            "tenth_from_lord": tenth_from_kk_lord,
            "tenth_from_occupants": tenth_from_kk_occupants,
        },
        "career_weights": dict(sorted(weights.items(), key=lambda kv: kv[1],
                                      reverse=True)),
        "planet_sources": {p: sorted(s) for p, s in sources.items()},
    }
