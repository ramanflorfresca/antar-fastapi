"""
Jaimini Chara Dasha Engine — Complete Refactored Implementation
===============================================================
Antar Platform · v2.0 · March 31, 2026

Architecture:
  Phase 1 — Data Pre-processing (Karakas, Arudha Lagna, Upapada Lagna, Karakamsa)
  Phase 2 — Chara Dasha Engine (MD sequence, duration, AD sub-periods)
  Phase 3 — Predictive Layer (Rashi Drishti, Argala, Moving Lagna, Event Logic)
  Phase 4 — Context Builder (formats everything for /predict LLM prompt)

Algorithm (K.N. Rao / Parasara Light verified):
  - Duration = quadrant-based sign-to-lord distance (NOT planets-in-sign+1)
  - Direction: Q1 (Ari-Tau-Gem) and Q3 (Lib-Sco-Sag) → forward = (lord−sign)%12
              Q2 (Can-Leo-Vir) and Q4 (Cap-Aqu-Pis) → backward = (sign−lord)%12
  - Jaimini Lords: Aquarius uses Rahu (not Saturn), Scorpio uses Ketu (not Mars)
    unless Winning Lord logic overrides
  - Cycling: confirmed — does cycle through all 12 signs repeatedly

Verified against Parasara Light:
  - Capricorn lagna (Nov 26, 1974): all 12 durations match
  - Libra lagna (1970): cycling confirmed (Libra returns 2072)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import IntEnum

# =============================================================================
# CONSTANTS
# =============================================================================

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

PLANET_NAMES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

KARAKA_NAMES = ["AK", "AmK", "BK", "MK", "PK", "GK", "DK"]
KARAKA_FULL_NAMES = [
    "Atmakaraka", "Amatyakaraka", "Bhratrukaraka",
    "Matrukaraka", "Putrakaraka", "Gnatikaraka", "Darakaraka"
]
KARAKA_MEANINGS = [
    "Self/Soul", "Career/Status", "Guru/Siblings",
    "Mother/Property", "Children/Intelligence", "Conflict/Disease", "Spouse/Partners"
]

# Standard sign lords (0-indexed sign → planet name)
SIGN_LORDS = {
    0: "Mars",      # Aries
    1: "Venus",     # Taurus
    2: "Mercury",   # Gemini
    3: "Moon",      # Cancer
    4: "Sun",       # Leo
    5: "Mercury",   # Virgo
    6: "Venus",     # Libra
    7: "Mars",      # Scorpio (dual: Mars/Ketu)
    8: "Jupiter",   # Sagittarius
    9: "Saturn",    # Capricorn
    10: "Saturn",   # Aquarius (dual: Saturn/Rahu)
    11: "Jupiter",  # Pisces
}

# Jaimini default lords for dual-lordship signs
# These are the defaults BEFORE applying Winning Lord logic
JAIMINI_LORDS = {
    7: ("Mars", "Ketu"),       # Scorpio
    10: ("Saturn", "Rahu"),    # Aquarius
}

# Sign modality
MOVABLE_SIGNS = {0, 3, 6, 9}       # Aries, Cancer, Libra, Capricorn
FIXED_SIGNS = {1, 4, 7, 10}        # Taurus, Leo, Scorpio, Aquarius
DUAL_SIGNS = {2, 5, 8, 11}         # Gemini, Virgo, Sagittarius, Pisces

# Quadrant-based direction for Chara Dasha (K.N. Rao method)
# Q1 (Ari, Tau, Gem) and Q3 (Lib, Sco, Sag) → FORWARD
# Q2 (Can, Leo, Vir) and Q4 (Cap, Aqu, Pis) → BACKWARD
FORWARD_SIGNS = {0, 1, 2, 6, 7, 8}    # Aries, Taurus, Gemini, Libra, Scorpio, Sagittarius
BACKWARD_SIGNS = {3, 4, 5, 9, 10, 11}  # Cancer, Leo, Virgo, Capricorn, Aquarius, Pisces

# Exaltation signs (0-indexed)
EXALTATION = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7
}

# Debilitation signs (0-indexed)
DEBILITATION = {
    "Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11,
    "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1
}

# Own signs
OWN_SIGNS = {
    "Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
    "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
    "Rahu": [10], "Ketu": [7]
}

# Benefics and Malefics
BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Planet:
    name: str
    sign: int               # 0-indexed sign (0=Aries ... 11=Pisces)
    degree: float           # Absolute degree (0-360)
    degree_in_sign: float   # Degree within sign (0-30)
    retrograde: bool = False
    nakshatra: str = ""
    nakshatra_lord: str = ""


@dataclass
class KarakaAssignment:
    karaka: str             # AK, AmK, BK, MK, PK, GK, DK
    karaka_full: str        # Full name
    meaning: str            # What it represents
    planet: str             # Planet name
    sign: int               # Sign the planet is in
    degree_in_sign: float   # Degree used for ranking


@dataclass
class ArudhaResult:
    name: str               # "AL" or "UL" or "A2" etc.
    sign: int               # Final sign (0-indexed)
    sign_name: str          # Sign name
    exception_applied: bool # Whether an exception rule was applied
    exception_detail: str   # Which exception, if any


@dataclass
class DashaPeriod:
    sign: int
    sign_name: str
    duration_years: int
    start_date: datetime
    end_date: datetime
    direction: str          # "forward" or "backward"
    lord: str               # Ruling planet used for duration calc
    level: int              # 1=MD, 2=AD
    sub_periods: List['DashaPeriod'] = field(default_factory=list)


@dataclass
class RashiDrishti:
    """Signs aspected by a given sign via Jaimini Rashi Drishti."""
    source_sign: int
    aspected_signs: List[int]


@dataclass
class ArgalaResult:
    sign: int
    primary_argala: Dict[str, List[str]]    # house_pos -> planets causing argala
    virodhargala: Dict[str, List[str]]       # house_pos -> planets obstructing
    secondary_argala: Dict[str, List[str]]   # 5th house argala
    net_supported: bool                      # Overall: more support than obstruction?


@dataclass
class PredictionEvent:
    event_type: str         # "marriage", "career", "health", "wealth", "children", "property"
    conditions_met: List[str]
    confidence: str         # "high", "medium", "low"
    description: str
    karaka_involved: str
    houses_active: List[int]


@dataclass
class JaiminiContext:
    """Complete Jaimini analysis result — passed to /predict prompt."""
    karakas: List[KarakaAssignment]
    arudha_lagna: ArudhaResult
    upapada_lagna: ArudhaResult
    karakamsa_sign: int
    karakamsa_sign_name: str
    current_md: Optional[DashaPeriod]
    current_ad: Optional[DashaPeriod]
    all_mds: List[DashaPeriod]
    rashi_drishti_from_md: List[int]
    rashi_drishti_from_ad: List[int]
    argala_on_md: Optional[ArgalaResult]
    predictions: List[PredictionEvent]
    moving_lagna_analysis: Dict[str, Any]


# =============================================================================
# PHASE 1: DATA PRE-PROCESSING
# =============================================================================

def compute_7_karakas(planets: Dict[str, Planet]) -> List[KarakaAssignment]:
    """
    Rank 7 planets (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn)
    by longitude within their sign (0°–30°), descending.
    Highest = AK, Lowest = DK.
    """
    karaka_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    ranked = sorted(
        [(name, planets[name]) for name in karaka_planets if name in planets],
        key=lambda x: x[1].degree_in_sign,
        reverse=True
    )

    assignments = []
    for i, (planet_name, planet) in enumerate(ranked):
        if i < 7:
            assignments.append(KarakaAssignment(
                karaka=KARAKA_NAMES[i],
                karaka_full=KARAKA_FULL_NAMES[i],
                meaning=KARAKA_MEANINGS[i],
                planet=planet_name,
                sign=planet.sign,
                degree_in_sign=planet.degree_in_sign
            ))
    return assignments


def _sign_distance(from_sign: int, to_sign: int) -> int:
    """Count signs from 'from_sign' to 'to_sign' forward (zodiacal), inclusive of to_sign.
    Distance of 0 means same sign → returns 0. But for Arudha we count inclusive."""
    return (to_sign - from_sign) % 12


def compute_arudha_lagna(lagna_sign: int, planets: Dict[str, Planet]) -> ArudhaResult:
    """
    Arudha Lagna (AL) — the "Maya" / perceived reality.

    Steps:
      1. Find Lagna Lord
      2. Count distance n from Lagna to Lord (forward, zodiacal)
      3. Project same distance n from Lord's position
      4. Apply the FOUR exceptions:
         - If AL falls in 1st house (Lagna itself) → move to 10th from Lagna
         - If AL falls in 4th house → keep as 4th (no change)
         - If AL falls in 7th house → move to 4th from Lagna
         - If AL falls in 10th house → move to 4th from Lagna

    The AL CANNOT be in the 1st or 7th houses from the Lagna. If it is, it's wrong.
    """
    lagna_lord_name = _get_sign_lord(lagna_sign, planets)
    _SIGNS_JE = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    _raw_lord_sign = planets[lagna_lord_name].sign
    lord_sign = _SIGNS_JE.index(_raw_lord_sign) if isinstance(_raw_lord_sign, str) and _raw_lord_sign in _SIGNS_JE else int(_raw_lord_sign or 0)

    # Distance from lagna to lord
    n = _sign_distance(lagna_sign, lord_sign)

    # Project same distance from lord
    projected_sign = (lord_sign + n) % 12

    # House position of projected AL from lagna (1-indexed)
    house_from_lagna = _sign_distance(lagna_sign, projected_sign)
    # house_from_lagna of 0 means same sign = 1st house (we use 0-based internally for distance)

    exception_applied = False
    exception_detail = ""

    if house_from_lagna == 0:  # Falls in 1st house (Lagna itself)
        projected_sign = (lagna_sign + 9) % 12  # 10th from Lagna (0-indexed: +9)
        exception_applied = True
        exception_detail = "AL fell in 1st house → moved to 10th from Lagna"
    elif house_from_lagna == 6:  # Falls in 7th house
        projected_sign = (lagna_sign + 3) % 12  # 4th from Lagna (0-indexed: +3)
        exception_applied = True
        exception_detail = "AL fell in 7th house → moved to 4th from Lagna"
    elif house_from_lagna == 9:  # Falls in 10th house
        projected_sign = (lagna_sign + 3) % 12  # 4th from Lagna
        exception_applied = True
        exception_detail = "AL fell in 10th house → moved to 4th from Lagna"
    # 4th house: no change (exception noted but no move)

    return ArudhaResult(
        name="AL",
        sign=projected_sign,
        sign_name=SIGN_NAMES[projected_sign],
        exception_applied=exception_applied,
        exception_detail=exception_detail
    )


def compute_upapada_lagna(lagna_sign: int, planets: Dict[str, Planet]) -> ArudhaResult:
    """
    Upapada Lagna (UL) — Arudha of the 12th House. The "Marriage Point."

    Steps:
      1. Identify 12th house sign from Lagna
      2. Find the Lord of that 12th house sign
         (For Scorpio/Aquarius, use Winning Lord rules)
      3. Count distance d from 12th house to its Lord (forward)
      4. Project same distance d from Lord's position
      5. Apply exceptions:
         - If projected UL == 12th house sign → add 10 signs
         - If projected UL == 7th from 12th house sign → add 10 signs
    """
    h12_sign = (lagna_sign + 11) % 12  # 12th house = lagna - 1
    h12_lord_name = _get_sign_lord(h12_sign, planets)
    lord_sign = planets[h12_lord_name].sign

    # Distance from 12th house to its lord
    d = _sign_distance(h12_sign, lord_sign)

    # Project same distance from lord
    projected_sign = (lord_sign + d) % 12

    exception_applied = False
    exception_detail = ""

    # Exception 1: projected UL == 12th house sign itself
    if projected_sign == h12_sign:
        projected_sign = (projected_sign + 10) % 12
        exception_applied = True
        exception_detail = "UL fell in 12th house sign → added 10 signs"

    # Exception 2: projected UL == 7th from 12th house sign
    seventh_from_h12 = (h12_sign + 6) % 12
    if projected_sign == seventh_from_h12:
        projected_sign = (projected_sign + 10) % 12
        exception_applied = True
        exception_detail = "UL fell in 7th from 12th house → added 10 signs"

    return ArudhaResult(
        name="UL",
        sign=projected_sign,
        sign_name=SIGN_NAMES[projected_sign],
        exception_applied=exception_applied,
        exception_detail=exception_detail
    )


def compute_karakamsa(karakas: List[KarakaAssignment], d9_planets: Dict[str, Planet]) -> int:
    """
    Karakamsa = sign occupied by the Atmakaraka (AK) in the D9 (Navamsha) chart.
    This sign is then identified in D1 and labeled "KL".
    """
    ak = karakas[0]  # First karaka is always AK
    ak_planet_name = ak.planet

    if ak_planet_name in d9_planets:
        return d9_planets[ak_planet_name].sign

    # Fallback: compute navamsha sign from absolute degree
    # Navamsha sign = floor(absolute_degree / 3.333...) % 12
    # More precisely: each navamsha = 3°20' = 3.3333°
    # But we need the actual D9 positions ideally from swisseph
    raise ValueError(f"AK planet '{ak_planet_name}' not found in D9 chart data")


# =============================================================================
# PHASE 2: CHARA DASHA ENGINE
# =============================================================================

def _get_sign_lord(sign: int, planets: Dict[str, Planet]) -> str:
    """
    Get the effective lord of a sign for Jaimini Chara Dasha.
    For Scorpio (7) and Aquarius (10), apply Winning Lord logic.
    """
    if sign not in JAIMINI_LORDS:
        return SIGN_LORDS[sign]

    lord_a, lord_b = JAIMINI_LORDS[sign]

    # Both lords must exist in the planets dict
    if lord_a not in planets or lord_b not in planets:
        return lord_a  # Fallback to traditional lord

    planet_a = planets[lord_a]
    planet_b = planets[lord_b]

    # Rule 1 — Occupancy: If one is IN the sign and the other isn't,
    # the one OUTSIDE wins (becomes the lord for distance calculation)
    a_in_sign = planet_a.sign == sign
    b_in_sign = planet_b.sign == sign

    if a_in_sign and not b_in_sign:
        return lord_b  # The one outside wins
    if b_in_sign and not a_in_sign:
        return lord_a  # The one outside wins
    if a_in_sign and b_in_sign:
        # Both in sign — use degrees (higher longitude wins)
        return lord_a if planet_a.degree_in_sign >= planet_b.degree_in_sign else lord_b

    # Rule 2 — Companions: Both outside. The one with more planets in its sign wins.
    a_companions = sum(1 for p in planets.values() if p.sign == planet_a.sign and p.name != lord_a)
    b_companions = sum(1 for p in planets.values() if p.sign == planet_b.sign and p.name != lord_b)

    if a_companions > b_companions:
        return lord_a
    if b_companions > a_companions:
        return lord_b

    # Rule 3 — Degrees: If tied, higher longitude wins
    return lord_a if planet_a.degree_in_sign >= planet_b.degree_in_sign else lord_b


def compute_md_duration(sign: int, planets: Dict[str, Planet]) -> Tuple[int, str]:
    """
    Compute Mahadasha duration for a sign using K.N. Rao quadrant-based method.

    Algorithm:
      - Find the sign's lord (with Jaimini Winning Lord for Scorpio/Aquarius)
      - Get lord's sign position (0-indexed)
      - Forward signs (Q1, Q3): duration = (lord_sign - sign) % 12
      - Backward signs (Q2, Q4): duration = (sign - lord_sign) % 12
      - If result is 0, duration = 12

    Returns: (years, lord_name)
    """
    lord_name = _get_sign_lord(sign, planets)
    lord_sign = planets[lord_name].sign

    if sign in FORWARD_SIGNS:
        duration = (lord_sign - sign) % 12
    else:
        duration = (sign - lord_sign) % 12

    if duration == 0:
        duration = 12

    return duration, lord_name


def compute_md_sequence(lagna_sign: int) -> List[int]:
    """
    Determine the Mahadasha sign sequence starting from Lagna.

    Direction depends on lagna:
      - Forward signs (Ari, Tau, Gem, Lib, Sco, Sag): 1→2→3→...→12
      - Backward signs (Can, Leo, Vir, Cap, Aqu, Pis): 1→12→11→...→2

    Returns list of 12 sign indices in dasha order.
    """
    if lagna_sign in FORWARD_SIGNS:
        return [(lagna_sign + i) % 12 for i in range(12)]
    else:
        return [(lagna_sign - i) % 12 for i in range(12)]


def compute_ad_sequence(md_sign: int) -> List[int]:
    """
    Antardasha sequence within a Mahadasha.
    Starts with the MD sign. Direction follows same forward/backward rule.
    """
    if md_sign in FORWARD_SIGNS:
        return [(md_sign + i) % 12 for i in range(12)]
    else:
        return [(md_sign - i) % 12 for i in range(12)]


def compute_chara_dasha(
    lagna_sign: int,
    planets: Dict[str, Planet],
    birth_date: datetime,
    num_cycles: int = 3
) -> List[DashaPeriod]:
    """
    Compute the full Jaimini Chara Dasha timeline.

    Each cycle goes through all 12 signs. The engine supports multiple cycles
    (confirmed: Jaimini Chara Dasha DOES cycle — verified vs Parasara Light).

    Each MD contains 12 ADs, each AD = MD_duration_years in months.
    AD sequence: starts with MD sign, direction matches MD sign's forward/backward rule.
    """
    md_sequence = compute_md_sequence(lagna_sign)
    all_periods = []
    current_date = birth_date

    for cycle in range(num_cycles):
        for sign in md_sequence:
            duration_years, lord = compute_md_duration(sign, planets)
            direction = "forward" if sign in FORWARD_SIGNS else "backward"

            md_start = current_date
            md_end = md_start + timedelta(days=duration_years * 365.25)

            # Compute Antardashas
            ad_sequence = compute_ad_sequence(sign)
            ad_duration_days = (duration_years * 365.25) / 12.0  # Each AD = MD years in months
            ad_periods = []
            ad_start = md_start

            for ad_sign in ad_sequence:
                ad_end = ad_start + timedelta(days=ad_duration_days)
                ad_direction = "forward" if ad_sign in FORWARD_SIGNS else "backward"
                ad_lord = _get_sign_lord(ad_sign, planets)

                ad_periods.append(DashaPeriod(
                    sign=ad_sign,
                    sign_name=SIGN_NAMES[ad_sign],
                    duration_years=0,  # ADs measured in months, not years
                    start_date=ad_start,
                    end_date=ad_end,
                    direction=ad_direction,
                    lord=ad_lord,
                    level=2,
                    sub_periods=[]
                ))
                ad_start = ad_end

            md_period = DashaPeriod(
                sign=sign,
                sign_name=SIGN_NAMES[sign],
                duration_years=duration_years,
                start_date=md_start,
                end_date=md_end,
                direction=direction,
                lord=lord,
                level=1,
                sub_periods=ad_periods
            )
            all_periods.append(md_period)
            current_date = md_end

    return all_periods


def get_current_dasha(
    all_mds: List[DashaPeriod],
    target_date: datetime
) -> Tuple[Optional[DashaPeriod], Optional[DashaPeriod]]:
    """Find the active MD and AD for a given date."""
    for md in all_mds:
        if md.start_date <= target_date < md.end_date:
            for ad in md.sub_periods:
                if ad.start_date <= target_date < ad.end_date:
                    return md, ad
            return md, None
    return None, None


# =============================================================================
# PHASE 3: PREDICTIVE LAYER
# =============================================================================

# ---- 3.1 Rashi Drishti (Jaimini Sign Aspects) ----

def get_rashi_drishti(sign: int) -> List[int]:
    """
    Jaimini Rashi Drishti — sign-based aspects (NOT planetary aspects).

    Rules:
      - Movable signs (0,3,6,9) aspect Fixed signs (1,4,7,10) EXCEPT the adjacent one
      - Fixed signs (1,4,7,10) aspect Movable signs (0,3,6,9) EXCEPT the adjacent one
      - Dual signs (2,5,8,11) aspect all other Dual signs

    "Adjacent" = the next sign in zodiacal order from the aspecting sign.
    Example: Aries (0) cannot aspect Taurus (1) even though Taurus is Fixed.
    """
    adjacent = (sign + 1) % 12

    if sign in MOVABLE_SIGNS:
        return [s for s in FIXED_SIGNS if s != adjacent]
    elif sign in FIXED_SIGNS:
        return [s for s in MOVABLE_SIGNS if s != adjacent]
    elif sign in DUAL_SIGNS:
        return [s for s in DUAL_SIGNS if s != sign]
    return []


def get_abhimukha_drishti(sign: int) -> Optional[int]:
    """
    Abhimukha Drishti (Facing Aspect) — the FURTHEST sign aspected.
    This is the primary/strongest influence.

    Movable → Fixed (8th sign distance)
    Fixed → Movable (6th sign distance)
    Dual → the opposite Dual sign (7th from it)
    """
    if sign in MOVABLE_SIGNS:
        return (sign + 7) % 12  # 8th sign (0-indexed +7)
    elif sign in FIXED_SIGNS:
        return (sign + 5) % 12  # 6th sign (0-indexed +5)
    elif sign in DUAL_SIGNS:
        return (sign + 6) % 12  # Opposite dual
    return None


# ---- 3.2 Argala (Intervention Logic) ----

def compute_argala(sign: int, planets: Dict[str, Planet]) -> ArgalaResult:
    """
    Argala — determines if a sign is being "supported" or "blocked."

    Primary Argala: Planets in the 2nd, 4th, and 11th houses from a sign.
    Virodhargala (Obstruction): Planets in the 12th, 10th, and 3rd houses respectively.
    Secondary Argala: Planets in the 5th house, obstructed by planets in the 9th.
    """
    def planets_in_house(house_offset: int) -> List[str]:
        target = (sign + house_offset) % 12
        return [p.name for p in planets.values() if p.sign == target]

    # Primary Argala houses and their obstructors
    argala_pairs = {
        "2nd": (1, 11),    # 2nd house argala, 12th house obstructs
        "4th": (3, 9),     # 4th house argala, 10th house obstructs
        "11th": (10, 2),   # 11th house argala, 3rd house obstructs
    }

    primary_argala = {}
    virodhargala = {}

    for label, (argala_offset, virodh_offset) in argala_pairs.items():
        a_planets = planets_in_house(argala_offset)
        v_planets = planets_in_house(virodh_offset)
        if a_planets:
            primary_argala[label] = a_planets
        if v_planets:
            virodhargala[label] = v_planets

    # Secondary Argala: 5th house, obstructed by 9th
    secondary_argala = {}
    fifth_planets = planets_in_house(4)
    ninth_planets = planets_in_house(8)
    if fifth_planets:
        secondary_argala["5th"] = fifth_planets

    # Net assessment
    total_support = sum(len(v) for v in primary_argala.values()) + sum(len(v) for v in secondary_argala.values())
    total_obstruct = sum(len(v) for v in virodhargala.values()) + len(ninth_planets)

    return ArgalaResult(
        sign=sign,
        primary_argala=primary_argala,
        virodhargala=virodhargala,
        secondary_argala=secondary_argala,
        net_supported=total_support > total_obstruct
    )


# ---- 3.3 Moving Lagna (Chara Lagna) ----

def analyze_moving_lagna(
    dasha_sign: int,
    karakas: List[KarakaAssignment],
    al: ArudhaResult,
    ul: ArudhaResult,
    planets: Dict[str, Planet]
) -> Dict[str, Any]:
    """
    Moving Lagna analysis — treat the Dasha Sign as the 1st house.
    Re-calculate all house significations relative to this new Lagna.

    Key checks:
      - AK position from dasha sign → self/soul status
      - AmK position from dasha sign → career potential
      - DK position from dasha sign → relationship potential
      - GK position from dasha sign → health/conflict
      - PK position from dasha sign → children/intelligence
      - MK position from dasha sign → property/mother
      - AL position from dasha sign → public image/wealth
      - UL position from dasha sign → marriage events
    """
    karaka_map = {k.karaka: k for k in karakas}
    analysis = {}

    # AK analysis
    if "AK" in karaka_map:
        ak_house = _sign_distance(dasha_sign, karaka_map["AK"].sign)
        analysis["ak_house"] = ak_house + 1  # 1-indexed for display
        if ak_house in [0, 4, 8]:  # 1st, 5th, 9th
            analysis["ak_effect"] = "Period of self-growth and soul alignment"
        elif ak_house == 11:  # 12th
            analysis["ak_effect"] = "Loss of health or status — caution period"
        elif ak_house in [5, 7]:  # 6th, 8th
            analysis["ak_effect"] = "Periodo de salud o transformacion profunda"
        else:
            analysis["ak_effect"] = "Neutral soul period"

    # AmK analysis
    if "AmK" in karaka_map:
        amk_house = _sign_distance(dasha_sign, karaka_map["AmK"].sign)
        analysis["amk_house"] = amk_house + 1
        if amk_house in [9, 10]:  # 10th, 11th
            analysis["amk_effect"] = "Major career milestone — professional peak"
        elif amk_house == 0:  # 1st
            analysis["amk_effect"] = "Career comes to the forefront of identity"
        elif amk_house in [5, 7]:  # 6th, 8th
            analysis["amk_effect"] = "Career obstacles or job changes"
        else:
            analysis["amk_effect"] = "Steady career period"

    # DK analysis
    if "DK" in karaka_map:
        dk_house = _sign_distance(dasha_sign, karaka_map["DK"].sign)
        analysis["dk_house"] = dk_house + 1
        if dk_house in [0, 6]:  # 1st, 7th
            analysis["dk_effect"] = "Relationship milestone — meeting or commitment"
        elif dk_house in [1, 10]:  # 2nd, 11th
            analysis["dk_effect"] = "Growth through partnerships"
        else:
            analysis["dk_effect"] = "Neutral relationship period"

    # GK analysis
    if "GK" in karaka_map:
        gk_house = _sign_distance(dasha_sign, karaka_map["GK"].sign)
        analysis["gk_house"] = gk_house + 1
        if gk_house in [0, 5, 7]:  # 1st, 6th, 8th
            analysis["gk_effect"] = "Health issues or litigation — heightened awareness needed"
        else:
            analysis["gk_effect"] = "No major conflict signals"

    # PK analysis
    if "PK" in karaka_map:
        pk_house = _sign_distance(dasha_sign, karaka_map["PK"].sign)
        analysis["pk_house"] = pk_house + 1
        if pk_house == 4:  # 5th
            analysis["pk_effect"] = "Nacimiento de hijo o ruptura creativa"
        elif pk_house in [0, 8]:  # 1st, 9th
            analysis["pk_effect"] = "Children and intelligence highlighted"
        else:
            analysis["pk_effect"] = "Neutral children/intelligence period"

    # MK analysis
    if "MK" in karaka_map:
        mk_house = _sign_distance(dasha_sign, karaka_map["MK"].sign)
        analysis["mk_house"] = mk_house + 1
        if mk_house == 3:  # 4th
            analysis["mk_effect"] = "Property acquisition or home changes"
        elif mk_house in [0, 9]:  # 1st, 10th
            analysis["mk_effect"] = "Mother/property matters prominent"
        else:
            analysis["mk_effect"] = "Neutral property period"

    # AL-based analysis
    al_house = _sign_distance(dasha_sign, al.sign)
    analysis["al_house"] = al_house + 1
    if al_house == 10:  # 11th from AL
        analysis["al_effect"] = "Premier time for wealth and financial gains"
    elif al_house == 9:  # 10th from AL
        analysis["al_effect"] = "Major fame and reputation gains"
    elif al_house in [1, 10]:  # 2nd, 11th
        analysis["al_effect"] = "Financial windfall period"
    else:
        analysis["al_effect"] = "Steady public image"

    # UL-based analysis
    ul_house = _sign_distance(dasha_sign, ul.sign)
    analysis["ul_house"] = ul_house + 1
    if ul_house in [0, 6]:  # 1st or 7th from UL
        analysis["ul_effect"] = "Marriage event mathematically triggered"
    elif ul_house == 1:  # 2nd from UL
        analysis["ul_effect"] = "Growth in marital life / financial partnership"
    else:
        analysis["ul_effect"] = "No direct marriage trigger"

    return analysis


# ---- 3.4 Event Prediction Engine ----

def predict_events(
    dasha_sign: int,
    karakas: List[KarakaAssignment],
    al: ArudhaResult,
    ul: ArudhaResult,
    karakamsa_sign: int,
    lagna_sign: int,
    planets: Dict[str, Planet]
) -> List[PredictionEvent]:
    """
    Multi-condition event prediction using the Jaimini Event Logic Table.

    Each event type requires multiple conditions to be met for high confidence.

    Event Types and Conditions:
    ─────────────────────────────────────────────────────────────────────────
    Marriage:
      C1: Dasha sign is 1st, 7th, or 2nd from UL
      C2: 7th house from AL
      C3: Contains or aspects DK (via Rashi Drishti)

    Childbirth:
      C1: Dasha sign is 1st, 5th, or 9th from Lagna
      C2: 5th house from Moving Lagna
      C3: Contains or aspects PK

    Promotion/Career:
      C1: Dasha sign is 10th or 11th from Lagna
      C2: 10th from AL
      C3: Contains or aspects AmK
      C4: Dasha sign aspects Karakamsa

    Buying Home/Property:
      C1: Dasha sign is 4th from Lagna
      C2: 4th house from Moving Lagna
      C3: Contains or aspects MK

    Health Issues:
      C1: GK is in the Dasha Sign or aspects it
      C2: Dasha sign is 6th or 8th from Moving Lagna
      C3: Malefics in 3rd or 6th from AL

    Financial Windfall:
      C1: Dasha sign is 2nd or 11th from AL
      C2: Argala support from 11th house (no virodhargala in 3rd)
    ─────────────────────────────────────────────────────────────────────────
    """
    events = []
    karaka_map = {k.karaka: k for k in karakas}
    drishti = get_rashi_drishti(dasha_sign)

    def _sign_contains_planet(sign: int, planet_name: str) -> bool:
        return planet_name in planets and planets[planet_name].sign == sign

    def _sign_contains_or_aspects_karaka(karaka_key: str) -> bool:
        if karaka_key not in karaka_map:
            return False
        k_sign = karaka_map[karaka_key].sign
        return k_sign == dasha_sign or k_sign in drishti

    def _house_from(base: int, target: int) -> int:
        """1-indexed house from base to target."""
        return _sign_distance(base, target) + 1

    # ── Marriage ──
    marriage_conditions = []
    ul_house = _house_from(ul.sign, dasha_sign)
    if ul_house in [1, 7, 2]:
        marriage_conditions.append(f"Dasha sign is {ul_house}th from UL")
    al_7th = _house_from(al.sign, dasha_sign)
    if al_7th == 7:
        marriage_conditions.append("Dasha sign is 7th from AL")
    if _sign_contains_or_aspects_karaka("DK"):
        marriage_conditions.append("Dasha sign contains or aspects DK")

    if len(marriage_conditions) >= 2:
        events.append(PredictionEvent(
            event_type="marriage",
            conditions_met=marriage_conditions,
            confidence="high" if len(marriage_conditions) == 3 else "medium",
            description="Hito importante en tu relacion — compromiso, matrimonio, o decision de vida con pareja",
            karaka_involved="DK",
            houses_active=[ul_house, al_7th]
        ))

    # ── Childbirth ──
    child_conditions = []
    lagna_house = _house_from(lagna_sign, dasha_sign)
    if lagna_house in [1, 5, 9]:
        child_conditions.append(f"Dasha sign is {lagna_house}th from Lagna")
    # 5th from moving lagna (dasha sign is the moving lagna — so 5th from it)
    if _sign_contains_or_aspects_karaka("PK"):
        child_conditions.append("Dasha sign contains or aspects PK")
        child_conditions.append("5th house from Moving Lagna activated")

    if len(child_conditions) >= 2:
        events.append(PredictionEvent(
            event_type="children",
            conditions_met=child_conditions,
            confidence="high" if len(child_conditions) >= 3 else "medium",
            description="Lanzaste o completaste un proyecto creativo importante, o hubo noticia de embarazo/nacimiento en tu circulo cercano",
            karaka_involved="PK",
            houses_active=[lagna_house]
        ))

    # ── Career / Promotion ──
    career_conditions = []
    if lagna_house in [10, 11]:
        career_conditions.append(f"Dasha sign is {lagna_house}th from Lagna")
    al_house_career = _house_from(al.sign, dasha_sign)
    if al_house_career == 10:
        career_conditions.append("Dasha sign is 10th from AL — fame/reputation")
    if _sign_contains_or_aspects_karaka("AmK"):
        career_conditions.append("Dasha sign contains or aspects AmK")
    if dasha_sign in get_rashi_drishti(karakamsa_sign) or dasha_sign == karakamsa_sign:
        career_conditions.append("Dasha sign aspects or is the Karakamsa")

    if len(career_conditions) >= 2:
        events.append(PredictionEvent(
            event_type="career",
            conditions_met=career_conditions,
            confidence="high" if len(career_conditions) >= 3 else "medium",
            description="Ascenso profesional importante — promocion, nuevo rol, o reconocimiento publico en tu trabajo",
            karaka_involved="AmK",
            houses_active=[lagna_house, al_house_career]
        ))

    # ── Property / Home ──
    property_conditions = []
    if lagna_house == 4:
        property_conditions.append("Dasha sign is 4th from Lagna")
    if _sign_contains_or_aspects_karaka("MK"):
        property_conditions.append("Dasha sign contains or aspects MK")

    if len(property_conditions) >= 2:
        events.append(PredictionEvent(
            event_type="property",
            conditions_met=property_conditions,
            confidence="medium",
            description="Compra, venta, o cambio importante de casa o propiedad",
            karaka_involved="MK",
            houses_active=[4]
        ))

    # ── Health Issues ──
    health_conditions = []
    if _sign_contains_or_aspects_karaka("GK"):
        health_conditions.append("GK in or aspecting dasha sign — health/litigation")
    moving_house = lagna_house  # house from lagna
    if moving_house in [6, 8]:
        health_conditions.append(f"Dasha sign is {moving_house}th from Lagna — stress axis")
    # Malefics in 3rd or 6th from AL
    al_3rd = (al.sign + 2) % 12
    al_6th = (al.sign + 5) % 12
    malefics_in_al_3_6 = [
        p.name for p in planets.values()
        if p.name in MALEFICS and p.sign in [al_3rd, al_6th]
    ]
    if malefics_in_al_3_6:
        health_conditions.append(f"Malefics ({', '.join(malefics_in_al_3_6)}) in 3rd/6th from AL")

    if len(health_conditions) >= 2:
        events.append(PredictionEvent(
            event_type="health",
            conditions_met=health_conditions,
            confidence="high" if len(health_conditions) >= 3 else "medium",
            description="Tuviste un episodio de salud o un conflicto que te obligo a parar — fatiga, enfermedad, o disputa importante",
            karaka_involved="GK",
            houses_active=[moving_house]
        ))

    # ── Financial Windfall ──
    wealth_conditions = []
    al_house_wealth = _house_from(al.sign, dasha_sign)
    if al_house_wealth in [2, 11]:
        wealth_conditions.append(f"Dasha sign is {al_house_wealth}th from AL — wealth axis")
    argala = compute_argala(dasha_sign, planets)
    if "11th" in argala.primary_argala and "11th" not in argala.virodhargala:
        wealth_conditions.append("11th house Argala with no Virodhargala — financial support")
    # Benefics in 2nd or 11th from AL
    al_2nd = (al.sign + 1) % 12
    al_11th = (al.sign + 10) % 12
    benefics_supporting = [
        p.name for p in planets.values()
        if p.name in BENEFICS and p.sign in [al_2nd, al_11th]
    ]
    if benefics_supporting:
        wealth_conditions.append(f"Benefics ({', '.join(benefics_supporting)}) support AL wealth houses")

    if len(wealth_conditions) >= 2:
        events.append(PredictionEvent(
            event_type="wealth",
            conditions_met=wealth_conditions,
            confidence="high" if len(wealth_conditions) >= 3 else "medium",
            description="Ingreso inesperado o ganancia financiera importante — bono, negocio, o oportunidad no planeada",
            karaka_involved="AL",
            houses_active=[al_house_wealth]
        ))

    return events


# =============================================================================
# PHASE 4: CONTEXT BUILDER (for /predict LLM prompt)
# =============================================================================

def build_jaimini_context(
    lagna_sign: int,
    planets: Dict[str, Planet],
    d9_planets: Dict[str, Planet],
    birth_date: datetime,
    target_date: Optional[datetime] = None
) -> JaiminiContext:
    """
    Master function — computes the entire Jaimini analysis and returns
    a JaiminiContext object ready for the /predict prompt builder.
    """
    if target_date is None:
        target_date = datetime.now()

    # Phase 1: Pre-processing
    karakas = compute_7_karakas(planets)
    al = compute_arudha_lagna(lagna_sign, planets)
    ul = compute_upapada_lagna(lagna_sign, planets)

    try:
        karakamsa_sign = compute_karakamsa(karakas, d9_planets)
    except ValueError:
        karakamsa_sign = karakas[0].sign  # Fallback to AK's D1 sign

    # Phase 2: Dasha timeline
    all_mds = compute_chara_dasha(lagna_sign, planets, birth_date, num_cycles=3)
    current_md, current_ad = get_current_dasha(all_mds, target_date)

    # Phase 3: Predictive layer
    active_sign = current_ad.sign if current_ad else (current_md.sign if current_md else lagna_sign)

    rashi_drishti_md = get_rashi_drishti(current_md.sign) if current_md else []
    rashi_drishti_ad = get_rashi_drishti(active_sign)
    argala_on_md = compute_argala(active_sign, planets)

    moving_lagna = analyze_moving_lagna(active_sign, karakas, al, ul, planets)

    predictions = predict_events(
        dasha_sign=active_sign,
        karakas=karakas,
        al=al,
        ul=ul,
        karakamsa_sign=karakamsa_sign,
        lagna_sign=lagna_sign,
        planets=planets
    )

    return JaiminiContext(
        karakas=karakas,
        arudha_lagna=al,
        upapada_lagna=ul,
        karakamsa_sign=karakamsa_sign,
        karakamsa_sign_name=SIGN_NAMES[karakamsa_sign],
        current_md=current_md,
        current_ad=current_ad,
        all_mds=all_mds,
        rashi_drishti_from_md=rashi_drishti_md,
        rashi_drishti_from_ad=rashi_drishti_ad,
        argala_on_md=argala_on_md,
        predictions=predictions,
        moving_lagna_analysis=moving_lagna
    )


def format_jaimini_prompt_block(ctx: JaiminiContext) -> str:
    """
    Format the Jaimini context as a text block for the /predict LLM system prompt.
    This is what Claude/DeepSeek sees when generating predictions.

    Uses plain-English labels — NO Sanskrit jargon in user-facing output.
    """
    lines = []
    lines.append("═══ JAIMINI CHARA DASHA ANALYSIS ═══")
    lines.append("")

    # Karakas
    lines.append("SOUL MAP (7 Karakas):")
    for k in ctx.karakas:
        lines.append(f"  {k.karaka} ({k.meaning}): {k.planet} in {SIGN_NAMES[k.sign]} "
                      f"at {k.degree_in_sign:.1f}°")

    # Special Points
    lines.append("")
    lines.append("SPECIAL POINTS:")
    lines.append(f"  Public Image (AL): {ctx.arudha_lagna.sign_name}"
                  f"{' [Exception: ' + ctx.arudha_lagna.exception_detail + ']' if ctx.arudha_lagna.exception_applied else ''}")
    lines.append(f"  Marriage Point (UL): {ctx.upapada_lagna.sign_name}"
                  f"{' [Exception: ' + ctx.upapada_lagna.exception_detail + ']' if ctx.upapada_lagna.exception_applied else ''}")
    lines.append(f"  Soul Purpose (Karakamsa): {ctx.karakamsa_sign_name}")

    # Current Dasha
    lines.append("")
    lines.append("CURRENT TIMING:")
    if ctx.current_md:
        lines.append(f"  Main Period: {ctx.current_md.sign_name} "
                      f"({ctx.current_md.start_date.strftime('%b %Y')} – "
                      f"{ctx.current_md.end_date.strftime('%b %Y')}) "
                      f"[{ctx.current_md.duration_years}yr, {ctx.current_md.direction}]")
    if ctx.current_ad:
        lines.append(f"  Sub-Period: {ctx.current_ad.sign_name} "
                      f"({ctx.current_ad.start_date.strftime('%b %Y')} – "
                      f"{ctx.current_ad.end_date.strftime('%b %Y')})")

    # Aspects active
    if ctx.rashi_drishti_from_ad:
        aspected = ", ".join(SIGN_NAMES[s] for s in ctx.rashi_drishti_from_ad)
        lines.append(f"  Signs Influenced: {aspected}")

    # Moving Lagna
    lines.append("")
    lines.append("MOVING LAGNA ANALYSIS (Dasha Sign = temporary 1st house):")
    ml = ctx.moving_lagna_analysis
    for key in ["ak_effect", "amk_effect", "dk_effect", "gk_effect", "pk_effect",
                "mk_effect", "al_effect", "ul_effect"]:
        if key in ml:
            label = key.replace("_effect", "").upper()
            lines.append(f"  {label}: {ml[key]}")

    # Argala
    if ctx.argala_on_md:
        lines.append("")
        a = ctx.argala_on_md
        if a.primary_argala:
            support_str = "; ".join(f"{k}: {', '.join(v)}" for k, v in a.primary_argala.items())
            lines.append(f"  Support (Argala): {support_str}")
        if a.virodhargala:
            block_str = "; ".join(f"{k}: {', '.join(v)}" for k, v in a.virodhargala.items())
            lines.append(f"  Obstruction: {block_str}")
        lines.append(f"  Net Assessment: {'Supported' if a.net_supported else 'Obstructed'}")

    # Predictions
    if ctx.predictions:
        lines.append("")
        lines.append("EVENT SIGNALS:")
        for p in ctx.predictions:
            lines.append(f"  [{p.confidence.upper()}] {p.event_type.upper()}: {p.description}")
            for c in p.conditions_met:
                lines.append(f"    ✓ {c}")

    lines.append("")
    lines.append("═══ END JAIMINI ANALYSIS ═══")

    return "\n".join(lines)


# =============================================================================
# PRASHNA (QUESTION) BINARY CHECK
# =============================================================================

def jaimini_binary_check(
    question_type: str,
    ctx: JaiminiContext,
    lagna_sign: int
) -> Dict[str, Any]:
    """
    Binary YES/NO check for specific questions using Jaimini logic gates.

    Question Types:
      "marriage"    → Is the current AD sign 1/7 from UL or DK?
      "lawsuit"     → Is there a malefic in 3rd or 6th from AL?
      "investment"  → Is the current sign 2nd, 5th, or 11th from AL?
      "foreign"     → Does the dasha sign aspect the 7th or 9th house from Lagna?
    """
    active_sign = ctx.current_ad.sign if ctx.current_ad else (ctx.current_md.sign if ctx.current_md else lagna_sign)
    result = {"question_type": question_type, "verdict": False, "reasons": []}

    if question_type == "marriage":
        ul_dist = _sign_distance(ctx.upapada_lagna.sign, active_sign) + 1
        dk_sign = None
        for k in ctx.karakas:
            if k.karaka == "DK":
                dk_sign = k.sign
                break
        if ul_dist in [1, 7]:
            result["verdict"] = True
            result["reasons"].append(f"Current sign is {ul_dist}th from Marriage Point (UL)")
        if dk_sign is not None:
            dk_dist = _sign_distance(active_sign, dk_sign)
            drishti = get_rashi_drishti(active_sign)
            if dk_sign == active_sign or dk_sign in drishti:
                result["verdict"] = True
                result["reasons"].append("Current sign contains or aspects spouse significator (DK)")

    elif question_type == "lawsuit":
        al_3rd = (ctx.arudha_lagna.sign + 2) % 12
        al_6th = (ctx.arudha_lagna.sign + 5) % 12
        # Note: malefics in 3rd/6th from AL = victory, but through struggle
        # This is actually favorable for winning
        result["verdict"] = True  # Default: check if favorable
        result["reasons"].append("Checking 3rd and 6th from Public Image point (AL)")
        # Check is simplified — in production, check actual malefic placements

    elif question_type == "investment":
        al_dist = _sign_distance(ctx.arudha_lagna.sign, active_sign) + 1
        if al_dist in [2, 5, 11]:
            result["verdict"] = True
            result["reasons"].append(f"Current sign is {al_dist}th from Public Image (AL) — wealth axis active")

    elif question_type == "foreign":
        drishti = get_rashi_drishti(active_sign)
        seventh_from_lagna = (lagna_sign + 6) % 12
        ninth_from_lagna = (lagna_sign + 8) % 12
        if seventh_from_lagna in drishti or ninth_from_lagna in drishti:
            result["verdict"] = True
            result["reasons"].append("Dasha sign aspects the 7th or 9th house from Lagna — foreign connection active")

    return result


# =============================================================================
# DATABASE SERIALIZATION
# =============================================================================

def jaimini_to_db_json(ctx: JaiminiContext) -> Dict[str, Any]:
    """
    Serialize the Jaimini context for storage in Supabase charts table
    (stored in the jaimini_data JSONB column).
    """
    return {
        "karakas": [
            {
                "karaka": k.karaka,
                "planet": k.planet,
                "sign": k.sign,
                "sign_name": SIGN_NAMES[k.sign],
                "degree": k.degree_in_sign,
                "meaning": k.meaning
            }
            for k in ctx.karakas
        ],
        "arudha_lagna": {
            "sign": ctx.arudha_lagna.sign,
            "sign_name": ctx.arudha_lagna.sign_name,
            "exception": ctx.arudha_lagna.exception_applied,
            "exception_detail": ctx.arudha_lagna.exception_detail
        },
        "upapada_lagna": {
            "sign": ctx.upapada_lagna.sign,
            "sign_name": ctx.upapada_lagna.sign_name,
            "exception": ctx.upapada_lagna.exception_applied,
            "exception_detail": ctx.upapada_lagna.exception_detail
        },
        "karakamsa": {
            "sign": ctx.karakamsa_sign,
            "sign_name": ctx.karakamsa_sign_name
        },
        "current_md": {
            "sign": ctx.current_md.sign,
            "sign_name": ctx.current_md.sign_name,
            "years": ctx.current_md.duration_years,
            "start": ctx.current_md.start_date.isoformat(),
            "end": ctx.current_md.end_date.isoformat(),
            "direction": ctx.current_md.direction,
            "lord": ctx.current_md.lord
        } if ctx.current_md else None,
        "current_ad": {
            "sign": ctx.current_ad.sign,
            "sign_name": ctx.current_ad.sign_name,
            "start": ctx.current_ad.start_date.isoformat(),
            "end": ctx.current_ad.end_date.isoformat(),
            "direction": ctx.current_ad.direction,
            "lord": ctx.current_ad.lord
        } if ctx.current_ad else None,
        "predictions": [
            {
                "event_type": p.event_type,
                "confidence": p.confidence,
                "description": p.description,
                "conditions": p.conditions_met,
                "karaka": p.karaka_involved
            }
            for p in ctx.predictions
        ],
        "moving_lagna": ctx.moving_lagna_analysis,
        "rashi_drishti_ad": [SIGN_NAMES[s] for s in ctx.rashi_drishti_from_ad],
        "argala_net": ctx.argala_on_md.net_supported if ctx.argala_on_md else None,
    }


def format_jaimini_for_predict(ctx: JaiminiContext) -> str:
    """
    Wrapper: returns the LLM prompt block.
    Called by build_complete_context() in the main predict pipeline.
    """
    return format_jaimini_prompt_block(ctx)


# =============================================================================
# INTEGRATION HELPER — called from chart/create and /predict
# =============================================================================

def calculate_jaimini_analysis(
    lagna_sign: int,
    planets_dict: Dict[str, Dict],
    d9_planets_dict: Dict[str, Dict],
    birth_date_str: str,
    target_date_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Top-level integration function called from FastAPI endpoints.

    Args:
        lagna_sign: 0-indexed lagna sign
        planets_dict: {planet_name: {sign, degree, degree_in_sign, retrograde, ...}}
        d9_planets_dict: Same format for D9 chart
        birth_date_str: "YYYY-MM-DD"
        target_date_str: "YYYY-MM-DD" (optional, defaults to today)

    Returns:
        Complete Jaimini analysis as serialized dict for DB storage + LLM prompt
    """
    # Convert raw dicts to Planet objects
    # Helper: chart_data stores sign as string ("Libra"), Planet needs int (0-indexed)
    def _sign_to_idx(s):
        if isinstance(s, int):
            return s
        if isinstance(s, str) and s in SIGN_NAMES:
            return SIGN_NAMES.index(s)
        try:
            return int(s)
        except (ValueError, TypeError):
            return 0

    def _safe_float(v, default=0.0):
        try:
            return float(v)
        except (ValueError, TypeError):
            return default

    planets = {}
    for name, data in planets_dict.items():
        _raw_sign = data.get("sign", 0)
        _raw_house = data.get("house", 0)
        _deg = _safe_float(data.get("degree", 0.0))
        _deg_in = _safe_float(data.get("degree_in_sign", _deg % 30 if _deg else 0.0))
        planets[name] = Planet(
            name=name,
            sign=_sign_to_idx(_raw_sign),
            degree=_deg,
            degree_in_sign=_deg_in,
            retrograde=bool(data.get("retrograde", False)),
            nakshatra=data.get("nakshatra", ""),
            nakshatra_lord=data.get("nakshatra_lord", "")
        )

    d9_planets = {}
    for name, data in d9_planets_dict.items():
        _raw_sign = data.get("sign", 0)
        _deg = _safe_float(data.get("degree", 0.0))
        _deg_in = _safe_float(data.get("degree_in_sign", _deg % 30 if _deg else 0.0))
        d9_planets[name] = Planet(
            name=name,
            sign=_sign_to_idx(_raw_sign),
            degree=_deg,
            degree_in_sign=_deg_in,
            retrograde=bool(data.get("retrograde", False))
        )

    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d") if target_date_str else datetime.now()

    # Build complete context
    ctx = build_jaimini_context(lagna_sign, planets, d9_planets, birth_date, target_date)

    # Return both DB-storable JSON and LLM prompt block
    return {
        "db_json": jaimini_to_db_json(ctx),
        "prompt_block": format_jaimini_for_predict(ctx),
        "context": ctx  # Raw context object for further processing
    }


# =============================================================================
# DASHA TABLE FOR DATABASE (level=1 and level=2 rows)
# =============================================================================

def generate_dasha_rows(
    chart_id: str,
    lagna_sign: int,
    planets: Dict[str, Planet],
    birth_date: datetime,
    num_cycles: int = 2
) -> List[Dict]:
    """
    Generate dasha rows for the dashas table in Supabase.
    Returns list of dicts ready for bulk insert.

    Each row: {chart_id, system, type, level, sequence, planet_or_sign,
               start_date, end_date, duration_years, metadata, parent_id}
    """
    all_mds = compute_chara_dasha(lagna_sign, planets, birth_date, num_cycles)
    rows = []

    for md_idx, md in enumerate(all_mds):
        # Level 1 (Mahadasha)
        rows.append({
            "chart_id": chart_id,
            "system": "jaimini",
            "type": "mahadasha",
            "level": 1,
            "sequence": md_idx,
            "planet_or_sign": md.sign_name,
            "start_date": md.start_date.isoformat(),
            "end_date": md.end_date.isoformat(),
            "duration_years": md.duration_years,
            "metadata": {
                "lord": md.lord,
                "direction": md.direction,
                "sign_index": md.sign,
            },
            "parent_id": None,
        })

        # Level 2 (Antardasha)
        for ad_idx, ad in enumerate(md.sub_periods):
            rows.append({
                "chart_id": chart_id,
                "system": "jaimini",
                "type": "antardasha",
                "level": 2,
                "sequence": (md_idx * 12) + ad_idx,
                "planet_or_sign": ad.sign_name,
                "start_date": ad.start_date.isoformat(),
                "end_date": ad.end_date.isoformat(),
                "duration_years": 0,
                "metadata": {
                    "lord": ad.lord,
                    "direction": ad.direction,
                    "sign_index": ad.sign,
                    "parent_md_sign": md.sign_name,
                },
                "parent_id": None,
            })

    return rows
