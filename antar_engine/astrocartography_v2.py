"""
antar_engine/astrocartography_v2.py
====================================
Relocation-primary astrocartography scoring (June 2026).

Replaces line-proximity-only ranking with a weighted composite that puts
the relocated whole-sign house ring at the center — the only term that
actually varies city-to-city when birth time stays fixed.

Composite weights (0-100 score):
  40%  relocated house of intent-house LORDS (with modern + LK rescue)
  25%  significator angularity (degree-proximity to relocated ASC/MC/DC/IC)
  15%  relocated occupancy of intent houses
  15%  dasha live-now placement (active MD/AD lord's relocated house)
   5%  age-chapter REWEIGHT (push priority houses, not flat bonus)

Birth UTC stays fixed. Only lat/lng of the target city enter the relocated
ascendant computation. Lahiri sidereal + whole-sign ring rotation.

Timezone is NOT an input. The relocated ASC depends only on the fixed UTC
instant + the target's geographic lat/lng via local sidereal time.

Narration contract: every user-facing string passes through _scrub() — zero
planet names, zero house numbers, zero Sanskrit (except bija mantras, none
here). Internal trace stays under keys prefixed with "_debug".
"""

from __future__ import annotations
import math
import re
import hashlib
from typing import Any, Dict, List, Optional, Tuple

try:
    import swisseph as swe
    _SWE_AVAILABLE = True
except ImportError:
    _SWE_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Intent → houses + significators
# ─────────────────────────────────────────────────────────────────────────────
INTENT_HOUSES = {
    "money":        {"houses": [2, 11], "sig": ["Jupiter", "Venus", "Mercury"]},
    "career":       {"houses": [10, 6, 11], "sig": ["Sun", "Saturn", "Mars", "Mercury"]},
    "love":         {"houses": [7, 5], "sig": ["Venus", "Moon", "Jupiter"]},
    "marriage":     {"houses": [7, 2, 4], "sig": ["Venus", "Jupiter", "Moon"]},
    "home":         {"houses": [4, 2, 12], "sig": ["Moon", "Mars", "Venus"]},
    "growth":       {"houses": [9, 5, 11], "sig": ["Jupiter", "Sun"]},
    "happiness":    {"houses": [4, 5, 9], "sig": ["Jupiter", "Moon", "Venus"]},
    "health":       {"houses": [1, 6], "sig": ["Sun", "Moon", "Mars"]},
    "education":    {"houses": [5, 9, 2], "sig": ["Jupiter", "Mercury"]},
    "spirituality": {"houses": [12, 9, 8], "sig": ["Jupiter", "Saturn", "Ketu"]},
    "depth":        {"houses": [12, 8, 4], "sig": ["Saturn", "Ketu", "Moon"]},
    "general":      {"houses": [10, 11, 2, 5], "sig": ["Jupiter", "Venus", "Sun"]},
}

SUPPORTIVE_HOUSES = {1, 2, 4, 5, 7, 9, 10, 11}
DUSTHANA_HOUSES = {6, 8, 12}

# Sign lords (0=Aries .. 11=Pisces)
SIGN_LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
              "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

_PLANET_IDS = {
    "Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3, "Mars": 4,
    "Jupiter": 5, "Saturn": 6, "Rahu": 11,  # Ketu = Rahu + 180
}

# Modern Layer + Lal Kitab: dusthana ≠ auto-negative.
# Rahu in 11th is the unicorn marker, Saturn in 10th is the master craftsman,
# Mars in 6th wins fights, etc.
MODERN_DUSTHANA_BOOST = {
    ("Rahu", 6): 0.6, ("Rahu", 8): 0.5, ("Rahu", 11): 0.85, ("Rahu", 12): 0.4,
    ("Saturn", 6): 0.55, ("Saturn", 8): 0.3, ("Saturn", 10): 0.75, ("Saturn", 11): 0.55,
    ("Mars", 6): 0.55, ("Mars", 3): 0.55, ("Mars", 10): 0.5,
    ("Ketu", 12): 0.55, ("Ketu", 8): 0.4, ("Ketu", 9): 0.5,
    ("Sun", 10): 0.7,
    ("Jupiter", 9): 0.8, ("Jupiter", 5): 0.75, ("Jupiter", 11): 0.7,
    ("Venus", 7): 0.75, ("Venus", 4): 0.65,
    ("Mercury", 10): 0.6, ("Mercury", 3): 0.55,
    ("Moon", 4): 0.65,
}


# ─────────────────────────────────────────────────────────────────────────────
# Relocation core
# ─────────────────────────────────────────────────────────────────────────────

def relocate_chart(natal_utc_jd: float, target_lat: float, target_lng: float) -> Dict:
    """
    Recompute the relocated ascendant + rotated whole-sign houses for the
    natal birth moment (fixed in UTC) as if observed from (target_lat, target_lng).

    Returns:
      {
        "asc_lon": float, "asc_sign": int,
        "mc_lon": float,  "mc_sign": int,
        "desc_lon": float, "ic_lon": float,
        "planet_signs":  {planet: int},      # natal signs — location-invariant
        "planet_houses": {planet: int},      # 1-12 from the relocated rising sign
        "planet_lons":   {planet: float},
      }

    Whole-sign relocation: house = ((planet_sign - asc_sign) % 12) + 1.
    """
    if not _SWE_AVAILABLE:
        return {}

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED

    planet_lons = {}
    for name, pid in _PLANET_IDS.items():
        try:
            r = swe.calc_ut(natal_utc_jd, pid, flags)
            planet_lons[name] = float(r[0][0]) % 360.0
        except Exception:
            pass
    if "Rahu" in planet_lons:
        planet_lons["Ketu"] = (planet_lons["Rahu"] + 180.0) % 360.0

    try:
        cusps, ascmc = swe.houses_ex(
            natal_utc_jd, target_lat, target_lng, b"W", swe.FLG_SIDEREAL
        )
        asc_lon = float(ascmc[0]) % 360.0
        mc_lon  = float(ascmc[1]) % 360.0
    except Exception:
        return {}

    asc_sign = int(asc_lon // 30)
    mc_sign  = int(mc_lon // 30)
    desc_lon = (asc_lon + 180.0) % 360.0
    ic_lon   = (mc_lon + 180.0) % 360.0

    planet_signs = {p: int(lon // 30) for p, lon in planet_lons.items()}
    planet_houses = {p: ((sign - asc_sign) % 12) + 1 for p, sign in planet_signs.items()}

    return {
        "asc_lon": asc_lon, "asc_sign": asc_sign,
        "mc_lon":  mc_lon,  "mc_sign":  mc_sign,
        "desc_lon": desc_lon, "ic_lon": ic_lon,
        "planet_signs": planet_signs,
        "planet_houses": planet_houses,
        "planet_lons": planet_lons,
    }


def _angular_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


# ─────────────────────────────────────────────────────────────────────────────
# 40/25/15/15/5 composite scorer
# ─────────────────────────────────────────────────────────────────────────────

def _house_lord_term(reloc: Dict, intent_houses: List[int], asc_sign: int) -> Tuple[float, List[Dict]]:
    """
    Relocated house of the LORDS of the intent houses. This is the dominant
    term — modern/LK layer rescues dusthana for the right planet.
    """
    notes = []
    if not intent_houses:
        return 0.0, notes
    total = 0.0
    n = 0
    for ih in intent_houses:
        h_sign = (asc_sign + ih - 1) % 12
        lord = SIGN_LORDS[h_sign]
        lord_house = reloc.get("planet_houses", {}).get(lord)
        if lord_house is None:
            continue
        n += 1
        if lord_house in SUPPORTIVE_HOUSES:
            s = 0.85 if lord_house in (1, 2, 4, 5, 9, 10, 11) else 0.6
        else:
            base = 0.20
            boost = MODERN_DUSTHANA_BOOST.get((lord, lord_house), 0.0)
            s = min(1.0, base + boost)
        total += s
        notes.append({
            "intent_house": ih, "lord": lord, "lord_house": lord_house,
            "classical_supportive": lord_house in SUPPORTIVE_HOUSES,
            "modern_rescue": (lord_house in DUSTHANA_HOUSES and
                              MODERN_DUSTHANA_BOOST.get((lord, lord_house), 0.0) > 0),
        })
    return (total / n if n else 0.0), notes


def _angularity_term(reloc: Dict, sig_planets: List[str]) -> Tuple[float, List[Dict]]:
    """
    Degree-proximity of intent significators to relocated ASC/MC/DC/IC.
    THIS is what separates two cities that share the same rising sign.
    """
    if not sig_planets:
        return 0.0, []
    asc, mc = reloc.get("asc_lon"), reloc.get("mc_lon")
    desc, ic = reloc.get("desc_lon"), reloc.get("ic_lon")
    if asc is None:
        return 0.0, []
    ORB = 5.0  # tightened twice — within-band discrimination requires sharp falloff
    notes = []
    best = 0.0
    for p in sig_planets:
        plon = reloc.get("planet_lons", {}).get(p)
        if plon is None:
            continue
        for angle_name, angle_lon in (("ASC", asc), ("MC", mc), ("DC", desc), ("IC", ic)):
            d = _angular_diff(plon, angle_lon)
            if d <= ORB:
                s = max(0.0, 1.0 - (d / ORB))
                if s > best:
                    best = s
                notes.append({
                    "planet": p, "angle": angle_name,
                    "orb": round(d, 2), "strength": round(s, 3),
                })
    notes.sort(key=lambda x: -x["strength"])
    return best, notes[:3]


def _occupancy_term(reloc: Dict, intent_houses: List[int]) -> Tuple[float, List[Dict]]:
    """Which natal planets sit in the relocated intent houses."""
    if not intent_houses:
        return 0.0, []
    benefics = {"Jupiter", "Venus", "Mercury", "Moon"}
    notes = []
    score = 0.0
    for planet, h in reloc.get("planet_houses", {}).items():
        if h in intent_houses:
            score += 0.40 if planet in benefics else 0.20
            notes.append({"planet": planet, "house": h})
    return min(1.0, score), notes


def _dasha_term(reloc: Dict, dasha: Dict, intent_houses: List[int]) -> Tuple[float, List[Dict]]:
    """
    Active MD/AD lord IS fixed across cities. What varies is whether *this*
    city places that lord on a relocated angle or relocated intent house.
    """
    notes = []
    score = 0.0
    md = dasha.get("md") if isinstance(dasha, dict) else None
    ad = dasha.get("ad") if isinstance(dasha, dict) else None
    asc_lon = reloc.get("asc_lon")
    mc_lon  = reloc.get("mc_lon")

    for label, planet, weight in (("MD", md, 1.0), ("AD", ad, 0.55)):
        if not planet:
            continue
        ph = reloc.get("planet_houses", {}).get(planet)
        if ph is None:
            continue
        s = 0.0
        if ph in intent_houses:
            s = 0.80
            notes.append({"period": label, "planet": planet, "house": ph, "in_intent_house": True})
        elif ph in {1, 10}:
            s = 0.60
            notes.append({"period": label, "planet": planet, "house": ph, "on_angle": True})
        plon = reloc.get("planet_lons", {}).get(planet)
        if plon is not None and asc_lon is not None and mc_lon is not None:
            d_min = min(_angular_diff(plon, asc_lon), _angular_diff(plon, mc_lon))
            if d_min < 6.0:
                s = max(s, 0.85)
        score += s * weight
    return min(1.0, score), notes


def _age_chapter_weights(age: Optional[int]) -> Dict[str, float]:
    """
    Reweights the composite by life chapter — does NOT add a flat per-city
    bonus. Older → push 10/legacy harder; younger → identity/growth.

    Tune (2026-06-09): angularity bumped to ~0.30 because within-band spread
    on career/home was clustering — angularity is the only term that
    discriminates among cities sharing a relocated rising sign.
    """
    if not age:
        return {"house_lord": 0.35, "angularity": 0.30,
                "occupancy": 0.15,  "dasha":      0.15, "age_houses": 0.05}
    if age < 28:
        return {"house_lord": 0.33, "angularity": 0.32,
                "occupancy": 0.17,  "dasha":      0.13, "age_houses": 0.05}
    if age < 42:
        return {"house_lord": 0.37, "angularity": 0.30,
                "occupancy": 0.15,  "dasha":      0.13, "age_houses": 0.05}
    if age < 56:
        return {"house_lord": 0.37, "angularity": 0.28,
                "occupancy": 0.15,  "dasha":      0.15, "age_houses": 0.05}
    return {"house_lord": 0.35, "angularity": 0.25,
            "occupancy": 0.15,  "dasha":      0.15, "age_houses": 0.10}


def _age_house_priority(age: Optional[int]) -> List[int]:
    if not age:    return [10]
    if age < 28:   return [1, 5, 9]
    if age < 42:   return [10, 2, 11]
    if age < 56:   return [10, 11]
    return [9, 12]


def score_city_for_intent(
    natal_utc_jd: float,
    city_lat: float,
    city_lng: float,
    intent: str,
    dasha: Dict,
    age: Optional[int] = None,
    reloc_cache: Optional[Dict] = None,
) -> Tuple[float, Dict]:
    """40/25/15/15/5 composite scorer. Returns (score 0-100, debug_dict)."""
    spec = INTENT_HOUSES.get(intent, INTENT_HOUSES["general"])
    intent_houses = spec["houses"]
    sig_planets   = spec["sig"]

    reloc = reloc_cache or relocate_chart(natal_utc_jd, city_lat, city_lng)
    if not reloc:
        return 0.0, {"error": "relocation failed"}

    asc_sign = reloc["asc_sign"]
    weights  = _age_chapter_weights(age)
    age_h    = _age_house_priority(age)

    s_house, n_house = _house_lord_term(reloc, intent_houses, asc_sign)
    s_ang,   n_ang   = _angularity_term(reloc, sig_planets)
    s_occ,   n_occ   = _occupancy_term(reloc, intent_houses)
    s_dash,  n_dash  = _dasha_term(reloc, dasha or {}, intent_houses)

    s_age = 0.6 if any(h in age_h for h in intent_houses) else 0.0

    final = (
        weights["house_lord"]  * s_house * 100 +
        weights["angularity"]  * s_ang   * 100 +
        weights["occupancy"]   * s_occ   * 100 +
        weights["dasha"]       * s_dash  * 100 +
        weights["age_houses"]  * s_age   * 100
    )
    final = round(final, 2)

    return final, {
        "reloc_asc_sign": SIGNS[asc_sign],
        "house_lord":  {"score": round(s_house, 3), "notes": n_house},
        "angularity":  {"score": round(s_ang,   3), "notes": n_ang},
        "occupancy":   {"score": round(s_occ,   3), "notes": n_occ},
        "dasha":       {"score": round(s_dash,  3), "notes": n_dash},
        "age_chapter": {"score": round(s_age,   3), "houses": age_h},
        "weights": weights,
    }


# ─────────────────────────────────────────────────────────────────────────────
# chart_context — location-invariant, computed ONCE
# ─────────────────────────────────────────────────────────────────────────────

_PLANET_ENERGY_NOUN = {
    "Sun":     "authority and recognition",
    "Moon":    "public belonging",
    "Mars":    "drive and action",
    "Mercury": "commerce and networks",
    "Jupiter": "expansion and growth",
    "Venus":   "partnership and attraction",
    "Saturn":  "discipline and mastery",
    "Rahu":    "ambition and acceleration",
    "Ketu":    "depth and release",
}


def build_chart_context(
    chart_data: Dict, dasha: Dict, age: Optional[int], intent: str
) -> Dict:
    """
    'WHY THESE PLACES · YOUR CHART RIGHT NOW' — dignity/dasha/age facts that
    are identical across every city. Renders ONCE above the city cards.
    """
    spec = INTENT_HOUSES.get(intent, INTENT_HOUSES["general"])
    planets = chart_data.get("planets", {}) or {}

    strongest = None
    hardest   = None
    for p in spec["sig"]:
        info = planets.get(p) or {}
        dignity = str(
            info.get("dignity") or info.get("strength") or ""
        ).lower()
        if dignity in ("exalted", "own sign", "own", "swakshetra", "moolatrikona"):
            strongest = strongest or p
        if dignity in ("debilitated", "neecha", "combust"):
            hardest = hardest or p

    md = dasha.get("md") if isinstance(dasha, dict) else None
    md_end = (dasha.get("md_end_date") or "")[:7] if isinstance(dasha, dict) else ""

    return {
        "intent": intent,
        "chapter": _chapter_for_age(age),
        "dasha_chapter": _dasha_chapter_phrase(md, md_end),
        "strongest_support": _support_phrase(strongest, intent) if strongest else None,
        "hardest_support":   _strain_phrase(hardest, intent)    if hardest   else None,
        "note": (
            "These facts describe your chart — not any one city. Each city card "
            "below shows where the same energy shifts when you stand on that ground."
        ),
    }


def _chapter_for_age(age: Optional[int]) -> str:
    if not age:   return "An open chapter"
    if age < 28:  return "An identity-building chapter — first scaffolds going up"
    if age < 42:  return "A building chapter — what you put down now compounds for decades"
    if age < 56:  return "A culmination chapter — what you've built starts paying out"
    return "A legacy chapter — what you finish here becomes the record"


def _dasha_chapter_phrase(md: Optional[str], md_end: Optional[str]) -> Optional[str]:
    if not md:
        return None
    energy = _PLANET_ENERGY_NOUN.get(md, "a sustained")
    if md_end:
        return f"You're inside an {energy} period, open through {md_end}."
    return f"You're inside an {energy} period."


def _support_phrase(p: str, intent: str) -> str:
    e = _PLANET_ENERGY_NOUN.get(p, "supportive")
    return f"Your {e} signal is unusually strong for {intent}."


def _strain_phrase(p: str, intent: str) -> str:
    e = _PLANET_ENERGY_NOUN.get(p, "supportive")
    return f"Your {e} signal runs tight — expect a steeper climb for {intent}."


# ─────────────────────────────────────────────────────────────────────────────
# Per-city cards — reference ONLY relocated shifts (no dignity/dasha/age)
# ─────────────────────────────────────────────────────────────────────────────

_HOUSE_NOUN = {
    1:  "how you show up — presence and first impression",
    2:  "money in hand and what you can hold",
    3:  "short-range hustle, sibling-energy, day-to-day momentum",
    4:  "home, roots, and what feels like ground",
    5:  "creative output, romance, and play",
    6:  "daily routine, service, and the work that grinds",
    7:  "partnerships and the people across the table",
    8:  "shared resources and what you'd rather not look at",
    9:  "long-range vision, teachers, and luck",
    10: "public role, authority, and how the world sees you",
    11: "income from networks, friends, and the wins that arrive",
    12: "solitude, exit, and the costs you can't see",
}


def _shift_lines(intent_houses: List[int], reloc: Dict, asc_sign: int) -> List[str]:
    """1–3 jargon-clean lines describing relocated shifts."""
    out = []
    for ih in intent_houses[:3]:
        h_sign = (asc_sign + ih - 1) % 12
        lord = SIGN_LORDS[h_sign]
        lord_house = reloc.get("planet_houses", {}).get(lord)
        if lord_house is None:
            continue
        intent_noun  = _HOUSE_NOUN[ih]
        landing_noun = _HOUSE_NOUN[lord_house]
        if lord_house in SUPPORTIVE_HOUSES:
            out.append(
                f"What runs your {intent_noun} lands inside your {landing_noun} here "
                f"— they pull on the same rope."
            )
        else:
            out.append(
                f"What runs your {intent_noun} lands inside your {landing_noun} here "
                f"— work pays out underground before it shows up on paper."
            )
    return out


_HEADLINE_TEMPLATES = {
    "supportive": [
        "Where {n} starts to compound",
        "{n} catches a tailwind here",
        "A city that lifts {n}",
        "{n} runs with you, not against you",
        "Where {n} keeps paying out long after you arrive",
        "{n} finds easier ground here",
        "A clear runway for {n}",
        "Where the math on {n} flips your way",
    ],
    "mixed": [
        "{n} costs more here — but pays differently",
        "Where {n} asks for steadier hands",
        "A city that bends {n} into a different shape",
        "{n} arrives slower — and bigger",
        "Where {n} trades speed for permanence",
        "A city that reshapes {n} before it pays out",
    ],
    "strained": [
        "{n} runs harder here than it should",
        "Where {n} demands more before it gives",
        "A city that asks {n} to prove itself first",
        "{n} pays late, if at all",
        "Where {n} fights the current",
    ],
}

_INTENT_NOUN_FOR_HEADLINE = {
    "money":        "what you can hold",
    "career":       "your public role",
    "love":         "partnership",
    "marriage":     "the partnership track",
    "home":         "your sense of ground",
    "growth":       "the long-range arc",
    "happiness":    "what feels light",
    "health":       "your daily rhythm",
    "education":    "what you learn",
    "spirituality": "the inner door",
    "depth":        "what you sit with",
    "general":      "what you build",
}

_ANGLE_NOUN = {
    "ASC": "you, head-on",
    "MC":  "your public face",
    "DC":  "the people across the table",
    "IC":  "your private ground",
}


def build_per_city_card(
    city_name: str,
    intent: str,
    score: float,
    debug: Dict,
    reloc: Dict,
) -> Dict:
    """
    Per-city card. References ONLY relocated shifts. No dignity/dasha/age
    facts here — those live in chart_context.
    """
    spec = INTENT_HOUSES.get(intent, INTENT_HOUSES["general"])
    intent_houses = spec["houses"]
    intent_noun   = _INTENT_NOUN_FOR_HEADLINE.get(intent, "what you build")

    house_score = debug.get("house_lord", {}).get("score", 0.0)
    if house_score >= 0.65:
        bucket = "supportive"
    elif house_score >= 0.40:
        bucket = "mixed"
    else:
        bucket = "strained"

    # Signature-driven headline: same astrological signature → same headline.
    # md5(city_name) only tiebreaks WITHIN identical signatures (±1 variant).
    pool = _HEADLINE_TEMPLATES[bucket]
    house_notes = debug.get("house_lord", {}).get("notes", []) or []
    sig_landings = tuple(
        sorted(
            (n.get("intent_house"), n.get("lord_house"))
            for n in house_notes[:3]
        )
    )
    top_ang = (debug.get("angularity", {}).get("notes") or [{}])[0]
    sig_angle = (top_ang.get("angle"), int(top_ang.get("orb") or 99))
    dash_notes = debug.get("dasha", {}).get("notes") or []
    sig_dasha = tuple(sorted(n.get("house") for n in dash_notes[:2] if n.get("house")))
    signature = (bucket, reloc["asc_sign"], sig_landings, sig_angle, sig_dasha)
    sig_hash = int(hashlib.md5(repr(signature).encode("utf-8")).hexdigest(), 16)
    base_idx = sig_hash % len(pool)
    # within-signature tiebreak: ±1 variant keyed by city name
    city_offset = int(hashlib.md5(city_name.encode("utf-8")).hexdigest(), 16) % 2
    raw_headline = pool[(base_idx + city_offset) % len(pool)].format(n=intent_noun)
    headline = _sanitize_headline(raw_headline)

    asc_sign = reloc["asc_sign"]
    shift_lines = _shift_lines(intent_houses, reloc, asc_sign)

    angularity_line = None
    ang_notes = debug.get("angularity", {}).get("notes", [])
    if ang_notes:
        top = ang_notes[0]
        a_noun = _ANGLE_NOUN.get(top["angle"], "a structural angle")
        angularity_line = f"A core driver of {intent_noun} sits right on {a_noun} here."

    dasha_line = None
    dash_notes = debug.get("dasha", {}).get("notes", [])
    if dash_notes:
        d = dash_notes[0]
        if d.get("in_intent_house"):
            dasha_line = (
                f"This city lands your current life-chapter directly inside {intent_noun}."
            )
        elif d.get("on_angle"):
            dasha_line = (
                f"This city places your current life-chapter on your public face."
            )

    relocated_shift = list(shift_lines)
    if angularity_line:
        relocated_shift.append(angularity_line)
    if dasha_line:
        relocated_shift.append(dasha_line)

    return {
        "city": city_name,
        "score": score,
        "headline": headline,
        "verdict": _verdict_for_score(score),
        "relocated_shift": relocated_shift[:3] or [
            f"This city leaves your {intent_noun} where it already is — "
            f"no large relocated shift either way."
        ],
        "your_move": _your_move(bucket, intent_noun),
        "_debug": debug,
    }


def _verdict_for_score(score: float) -> str:
    if score >= 65:  return "Worth the move — this city sits with you."
    if score >= 50:  return "Solid fit — your wins land cleaner here."
    if score >= 38:  return "Mixed — some lifts, some new costs."
    return "Not a fit for what you came here for."


def _your_move(bucket: str, intent_noun: str) -> str:
    if bucket == "supportive":
        return (
            f"Pick one concrete proof-of-life for {intent_noun} you'd be willing "
            f"to start within 30 days of arriving."
        )
    if bucket == "mixed":
        return (
            f"Visit 4–7 days before committing — feel whether the cost on "
            f"{intent_noun} is one you can carry."
        )
    return f"Don't relocate for {intent_noun} alone. Anchor a different reason first."


# ─────────────────────────────────────────────────────────────────────────────
# Top-level orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def astrocartography_v2(
    chart_data: Dict,
    dasha: Dict,
    birth_jd: float,
    intent: str = "career",
    age: Optional[int] = None,
    limit: int = 5,
    cities: Optional[List[Tuple[str, float, float, str]]] = None,
) -> Dict:
    """
    Main entry. Returns:
      {
        "intent": str,
        "chart_context":  {...},     # location-invariant — render ONCE
        "top_cities":     [card,..], # each card references only relocated shifts
        "stats":          {"score_spread", "n_scored"}
      }
    """
    if cities is None:
        try:
            from antar_engine.astrocarto_cities import ASTROCARTO_CITIES
            cities = ASTROCARTO_CITIES
        except ImportError:
            cities = []

    intent = (intent or "career").lower()

    scored = []
    for city_name, lat, lng, _region in cities:
        try:
            reloc = relocate_chart(birth_jd, lat, lng)
            if not reloc:
                continue
            score, debug = score_city_for_intent(
                birth_jd, lat, lng, intent, dasha, age, reloc_cache=reloc,
            )
            if score <= 0:
                continue
            card = build_per_city_card(city_name, intent, score, debug, reloc)
            scored.append(card)
        except Exception:
            continue

    scored.sort(key=lambda c: -c["score"])
    top = scored[:max(1, int(limit or 5))]

    if len(top) >= 2:
        spread = round(top[0]["score"] - top[-1]["score"], 2)
    else:
        spread = 0.0

    chart_context = build_chart_context(chart_data, dasha, age, intent)

    chart_context = _scrub(chart_context)
    top = [_scrub(c) for c in top]

    return {
        "intent": intent,
        "chart_context": chart_context,
        "top_cities": top,
        "stats": {"score_spread": spread, "n_scored": len(scored)},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Narration-contract scrub — last line of defense
# ─────────────────────────────────────────────────────────────────────────────

_PLANET_NAME_RE = re.compile(
    r"\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu|"
    r"Sol|Luna|Marte|Mercurio|J\u00fapiter|Jupiter|Saturno)\b",
    re.IGNORECASE,
)
_HOUSE_REF_RE = re.compile(
    r"\b(\d+(?:st|nd|rd|th)?\s+(?:house|lord|cusp)|house\s+\d+|lord\s+of\s+\d+|"
    r"\d+(?:st|nd|rd|th)\s+\w+\s+lord)\b",
    re.IGNORECASE,
)
_SANSKRIT_RE = re.compile(
    r"\b(nakshatra|atmakaraka|amatyakaraka|bhratrukaraka|dasha|mahadasha|"
    r"antardasha|antara|antar[-\s]?dasha|lagna|rashi|graha|yoga|paran|jaimini|"
    r"vimsottari|chara|naisargika|navamsa|navamsha|gandanta|sade[-\s]?sati|"
    r"kendra|trikona|dusthana|upachaya|moksha|karaka)\b",
    re.IGNORECASE,
)


def _scrub(obj):
    """Walk and scrub. Skips keys starting with '_debug' (internal trace)."""
    if isinstance(obj, dict):
        return {
            k: (v if str(k).startswith("_debug") else _scrub(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, str):
        s = _PLANET_NAME_RE.sub("the energy", obj)
        s = _HOUSE_REF_RE.sub("that area of life", s)
        s = _SANSKRIT_RE.sub("the cycle", s)
        return s
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# Intent alias map — accepts legacy /recommend vocabulary
# ─────────────────────────────────────────────────────────────────────────────

INTENT_ALIASES = {
    "startup":       "money",
    "wealth":        "money",
    "billionaire":   "career",
    "relationships": "love",
    "partner":       "love",
    "marriage":      "marriage",
    "general":       "general",
    # passthrough — already canonical
    "money":         "money",
    "career":        "career",
    "love":          "love",
    "home":          "home",
    "growth":        "growth",
    "happiness":     "happiness",
    "health":        "health",
    "education":     "education",
    "spirituality":  "spirituality",
    "depth":         "depth",
}


def resolve_intent(intent: str) -> str:
    """Collapse legacy intent vocabulary into the canonical INTENT_HOUSES key."""
    if not intent:
        return "career"
    return INTENT_ALIASES.get(str(intent).lower(), "career")


def score_single_city(
    chart_data: Dict,
    dasha: Dict,
    birth_jd: float,
    intent: str,
    city_name: str,
    city_lat: float,
    city_lng: float,
    age: Optional[int] = None,
) -> Dict:
    """
    One-city scoring path. Used by the single-city search endpoint.
    Returns {chart_context, card, intent}.
    """
    intent = resolve_intent(intent)
    reloc = relocate_chart(birth_jd, city_lat, city_lng)
    if not reloc:
        return {
            "intent": intent,
            "chart_context": build_chart_context(chart_data, dasha, age, intent),
            "card": None,
            "error": "relocation_failed",
        }
    score, debug = score_city_for_intent(
        birth_jd, city_lat, city_lng, intent, dasha, age, reloc_cache=reloc,
    )
    card = build_per_city_card(city_name, intent, score, debug, reloc)
    return _scrub({
        "intent": intent,
        "chart_context": build_chart_context(chart_data, dasha, age, intent),
        "card": card,
    })


def _sanitize_headline(s: str) -> str:
    """
    Kill double-"your" leaks that arise when an intent noun already begins
    with "your" and the template prepends "your" too.

    Examples killed:
      "to your your sense of ground" → "to your sense of ground"
      "lifts your your public role"  → "lifts your public role"
    Capitalisation preserved at start.
    """
    if not s:
        return s
    out = s
    out = re.sub(r"\byour\s+your\b", "your", out, flags=re.IGNORECASE)
    out = re.sub(r"\bYour\s+your\b", "Your", out)
    # also any incidental " the the "
    out = re.sub(r"\bthe\s+the\b", "the", out, flags=re.IGNORECASE)
    return out
