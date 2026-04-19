"""
antar_engine/yoga_detector.py
==============================
Phase 3 — Detect classical yogas formed in the day chart.

These are *transient* yogas that exist TODAY (not natal).
They color the day's flavor for ALL users in that location.

Called by: daily_transit_analyzer.py (Phase 3 integration)
"""
import logging
from typing import Dict, List

logger = logging.getLogger("antar_engine.yoga_detector")

# ─────────────────────────────────────────────────────────────────
# YOGA DEFINITIONS
# ─────────────────────────────────────────────────────────────────

# sign_index distance for kendra relationship: 0 (same), 3, 6, 9
KENDRA_DISTANCES = {0, 3, 6, 9}

# Trikona distances from a reference: 0, 4, 8  (1st, 5th, 9th house)
TRIKONA_DISTANCES = {0, 4, 8}

# Kendra houses from lagna: 1, 4, 7, 10
KENDRA_HOUSES = {1, 4, 7, 10}
TRIKONA_HOUSES = {1, 5, 9}


def _sign_distance(a: int, b: int) -> int:
    """Distance in signs from a to b (0-11)."""
    return (b - a) % 12


def _same_sign(a: int, b: int) -> bool:
    return a == b


# ─────────────────────────────────────────────────────────────────
# INDIVIDUAL YOGA DETECTORS
# ─────────────────────────────────────────────────────────────────

def _detect_gajakesari(planets: dict) -> bool:
    """Jupiter and Moon in kendras (1,4,7,10) from each other."""
    jup = planets.get("Jupiter", {})
    moon = planets.get("Moon", {})
    if not jup or not moon:
        return False
    dist = _sign_distance(moon.get("sign_index", -1), jup.get("sign_index", -1))
    return dist in KENDRA_DISTANCES


def _detect_budhaditya(planets: dict) -> bool:
    """Sun and Mercury in the same sign."""
    sun = planets.get("Sun", {})
    merc = planets.get("Mercury", {})
    if not sun or not merc:
        return False
    return _same_sign(sun.get("sign_index", -1), merc.get("sign_index", -1))


def _detect_chandra_mangala(planets: dict) -> bool:
    """Moon and Mars in the same sign."""
    moon = planets.get("Moon", {})
    mars = planets.get("Mars", {})
    if not moon or not mars:
        return False
    return _same_sign(moon.get("sign_index", -1), mars.get("sign_index", -1))


def _detect_guru_chandala(planets: dict) -> bool:
    """Jupiter and Rahu in the same sign."""
    jup = planets.get("Jupiter", {})
    rahu = planets.get("Rahu", {})
    if not jup or not rahu:
        return False
    return _same_sign(jup.get("sign_index", -1), rahu.get("sign_index", -1))


def _detect_grahana_solar(planets: dict) -> bool:
    """Sun with Rahu or Ketu in same sign (solar eclipse-like)."""
    sun = planets.get("Sun", {})
    rahu = planets.get("Rahu", {})
    ketu = planets.get("Ketu", {})
    if not sun:
        return False
    sun_idx = sun.get("sign_index", -1)
    return (rahu and _same_sign(sun_idx, rahu.get("sign_index", -1))) or \
           (ketu and _same_sign(sun_idx, ketu.get("sign_index", -1)))


def _detect_grahana_lunar(planets: dict) -> bool:
    """Moon with Rahu or Ketu in same sign (lunar eclipse-like)."""
    moon = planets.get("Moon", {})
    rahu = planets.get("Rahu", {})
    ketu = planets.get("Ketu", {})
    if not moon:
        return False
    moon_idx = moon.get("sign_index", -1)
    return (rahu and _same_sign(moon_idx, rahu.get("sign_index", -1))) or \
           (ketu and _same_sign(moon_idx, ketu.get("sign_index", -1)))


def _detect_shubha_kartari(planets: dict) -> bool:
    """
    Benefics (Jupiter, Venus, Mercury) flanking the lagna sign
    (in 12th and 2nd from lagna = house 12 and house 2).
    """
    benefics = {"Jupiter", "Venus", "Mercury"}
    house_12 = [p for p, d in planets.items() if d.get("house") == 12 and p in benefics]
    house_2 = [p for p, d in planets.items() if d.get("house") == 2 and p in benefics]
    return bool(house_12) and bool(house_2)


def _detect_papa_kartari(planets: dict) -> bool:
    """
    Malefics (Saturn, Mars, Rahu, Ketu) flanking the lagna sign
    (in 12th and 2nd from lagna).
    """
    malefics = {"Saturn", "Mars", "Rahu", "Ketu"}
    house_12 = [p for p, d in planets.items() if d.get("house") == 12 and p in malefics]
    house_2 = [p for p, d in planets.items() if d.get("house") == 2 and p in malefics]
    return bool(house_12) and bool(house_2)


def _detect_amala(planets: dict) -> bool:
    """A natural benefic (Jupiter, Venus, Mercury, Moon) in 10th house."""
    benefics = {"Jupiter", "Venus", "Mercury", "Moon"}
    return any(
        planets.get(p, {}).get("house") == 10
        for p in benefics
    )


def _detect_veshi(planets: dict) -> bool:
    """A planet (not Moon, Rahu, Ketu) in 2nd from Sun."""
    sun_idx = planets.get("Sun", {}).get("sign_index", -1)
    if sun_idx < 0:
        return False
    second_from_sun = (sun_idx + 1) % 12
    exclude = {"Sun", "Moon", "Rahu", "Ketu"}
    return any(
        d.get("sign_index") == second_from_sun
        for p, d in planets.items()
        if p not in exclude
    )


def _detect_voshi(planets: dict) -> bool:
    """A planet (not Moon, Rahu, Ketu) in 12th from Sun."""
    sun_idx = planets.get("Sun", {}).get("sign_index", -1)
    if sun_idx < 0:
        return False
    twelfth_from_sun = (sun_idx - 1) % 12
    exclude = {"Sun", "Moon", "Rahu", "Ketu"}
    return any(
        d.get("sign_index") == twelfth_from_sun
        for p, d in planets.items()
        if p not in exclude
    )


def _detect_ubhayachari(planets: dict) -> bool:
    """Planets on BOTH sides of Sun (both Veshi and Voshi active)."""
    return _detect_veshi(planets) and _detect_voshi(planets)


def _detect_saraswati(planets: dict) -> bool:
    """
    Jupiter, Venus, Mercury all in kendras or trikonas from lagna.
    Simplified: all three in houses 1,4,5,7,9,10.
    """
    good_houses = KENDRA_HOUSES | TRIKONA_HOUSES
    targets = ["Jupiter", "Venus", "Mercury"]
    return all(
        planets.get(p, {}).get("house") in good_houses
        for p in targets
    )


def _detect_malavya(planets: dict) -> bool:
    """Venus in kendra (1,4,7,10) in own sign (Taurus=1, Libra=6) or exaltation (Pisces=11)."""
    venus = planets.get("Venus", {})
    if not venus:
        return False
    if venus.get("house") not in KENDRA_HOUSES:
        return False
    venus_sign = venus.get("sign_index", -1)
    # Venus own: Taurus(1), Libra(6); Exalted: Pisces(11)
    return venus_sign in {1, 6, 11}


def _detect_hamsa(planets: dict) -> bool:
    """Jupiter in kendra in own sign (Sagittarius=8, Pisces=11) or exaltation (Cancer=3)."""
    jup = planets.get("Jupiter", {})
    if not jup:
        return False
    if jup.get("house") not in KENDRA_HOUSES:
        return False
    jup_sign = jup.get("sign_index", -1)
    return jup_sign in {8, 11, 3}


def _detect_ruchaka(planets: dict) -> bool:
    """Mars in kendra in own sign (Aries=0, Scorpio=7) or exaltation (Capricorn=9)."""
    mars = planets.get("Mars", {})
    if not mars:
        return False
    if mars.get("house") not in KENDRA_HOUSES:
        return False
    mars_sign = mars.get("sign_index", -1)
    return mars_sign in {0, 7, 9}


def _detect_bhadra(planets: dict) -> bool:
    """Mercury in kendra in own sign (Gemini=2, Virgo=5) or exaltation (Virgo=5)."""
    merc = planets.get("Mercury", {})
    if not merc:
        return False
    if merc.get("house") not in KENDRA_HOUSES:
        return False
    merc_sign = merc.get("sign_index", -1)
    return merc_sign in {2, 5}


def _detect_sasa(planets: dict) -> bool:
    """Saturn in kendra in own sign (Capricorn=9, Aquarius=10) or exaltation (Libra=6)."""
    sat = planets.get("Saturn", {})
    if not sat:
        return False
    if sat.get("house") not in KENDRA_HOUSES:
        return False
    sat_sign = sat.get("sign_index", -1)
    return sat_sign in {9, 10, 6}


def _detect_kemadruma(planets: dict) -> bool:
    """
    No planet (except Sun, Rahu, Ketu) in 2nd or 12th from Moon.
    Indicates emotional isolation.
    """
    moon_idx = planets.get("Moon", {}).get("sign_index", -1)
    if moon_idx < 0:
        return False
    second = (moon_idx + 1) % 12
    twelfth = (moon_idx - 1) % 12
    exclude = {"Sun", "Moon", "Rahu", "Ketu"}
    has_flanking = any(
        d.get("sign_index") in (second, twelfth)
        for p, d in planets.items()
        if p not in exclude
    )
    return not has_flanking


# ─────────────────────────────────────────────────────────────────
# YOGA REGISTRY
# ─────────────────────────────────────────────────────────────────

DAY_YOGAS = {
    "Gajakesari": {
        "detect": _detect_gajakesari,
        "effect": "Wisdom and success amplified — intellectual work especially favored today",
        "quality": "very_auspicious",
    },
    "Budhaditya": {
        "detect": _detect_budhaditya,
        "effect": "Mental clarity and communication power — sharp thinking, good for writing and speaking",
        "quality": "auspicious",
    },
    "Chandra-Mangala": {
        "detect": _detect_chandra_mangala,
        "effect": "Emotional fire and action energy — powerful drive but watch for impulsiveness",
        "quality": "mixed",
    },
    "Guru-Chandala": {
        "detect": _detect_guru_chandala,
        "effect": "Wisdom interference — be cautious with advisors and major philosophical decisions",
        "quality": "inauspicious",
    },
    "Grahana (Solar)": {
        "detect": _detect_grahana_solar,
        "effect": "Eclipse-like confusion on authority and identity — avoid big commitments",
        "quality": "inauspicious",
    },
    "Grahana (Lunar)": {
        "detect": _detect_grahana_lunar,
        "effect": "Eclipse-like emotional fog — confusion in feelings, avoid emotional decisions",
        "quality": "inauspicious",
    },
    "Shubha Kartari": {
        "detect": _detect_shubha_kartari,
        "effect": "Benefics protect the day's rising energy — auspicious umbrella over activities",
        "quality": "very_auspicious",
    },
    "Papa Kartari": {
        "detect": _detect_papa_kartari,
        "effect": "Malefics squeeze the day's rising energy — feel hemmed in, limited options",
        "quality": "inauspicious",
    },
    "Amala": {
        "detect": _detect_amala,
        "effect": "Benefic in the public-action house — good day for professional visibility",
        "quality": "auspicious",
    },
    "Ubhayachari": {
        "detect": _detect_ubhayachari,
        "effect": "Planets flanking the Sun — amplified solar power, strong authority day",
        "quality": "very_auspicious",
    },
    "Saraswati": {
        "detect": _detect_saraswati,
        "effect": "Jupiter-Venus-Mercury aligned in power positions — peak day for learning and creativity",
        "quality": "very_auspicious",
    },
    "Malavya (Pancha Mahapurusha)": {
        "detect": _detect_malavya,
        "effect": "Venus empowered — luxury, beauty, relationships, and creative arts all favored",
        "quality": "very_auspicious",
    },
    "Hamsa (Pancha Mahapurusha)": {
        "detect": _detect_hamsa,
        "effect": "Jupiter empowered — wisdom, ethics, expansion, and teaching all amplified",
        "quality": "very_auspicious",
    },
    "Ruchaka (Pancha Mahapurusha)": {
        "detect": _detect_ruchaka,
        "effect": "Mars empowered — courage, competition, leadership, and physical vitality boosted",
        "quality": "auspicious",
    },
    "Bhadra (Pancha Mahapurusha)": {
        "detect": _detect_bhadra,
        "effect": "Mercury empowered — commerce, communication, analysis, and negotiation excel",
        "quality": "very_auspicious",
    },
    "Sasa (Pancha Mahapurusha)": {
        "detect": _detect_sasa,
        "effect": "Saturn empowered — discipline, structure, long-term building, and authority solidified",
        "quality": "auspicious",
    },
    "Kemadruma": {
        "detect": _detect_kemadruma,
        "effect": "Moon isolated — emotional solitude, low social energy, best for solo work",
        "quality": "inauspicious",
    },
}


# ─────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────

def detect_day_yogas(day_chart: dict) -> List[dict]:
    """
    Detect all active yogas in the given day chart.

    Args:
        day_chart: output of cast_day_chart()

    Returns:
        List of {name, effect, quality} for each active yoga.
    """
    if not day_chart or not day_chart.get("planets"):
        return []

    planets = day_chart["planets"]
    active = []

    for yoga_name, meta in DAY_YOGAS.items():
        try:
            if meta["detect"](planets):
                active.append({
                    "name": yoga_name,
                    "effect": meta["effect"],
                    "quality": meta["quality"],
                })
        except Exception as e:
            logger.warning(f"[yoga-detector] {yoga_name} check failed: {e}")

    return active


def format_day_yogas_for_prompt(yogas: list) -> str:
    """
    Format detected yogas into a text block for LLM prompt injection.
    """
    if not yogas:
        return "YOGAS ACTIVE TODAY: None detected — neutral yoga influence."

    lines = ["YOGAS ACTIVE TODAY:"]
    for y in yogas:
        quality_tag = {
            "very_auspicious": "[VERY AUSPICIOUS]",
            "auspicious": "[AUSPICIOUS]",
            "mixed": "[MIXED]",
            "inauspicious": "[INAUSPICIOUS]",
        }.get(y["quality"], "")
        lines.append(f"  {y['name']} {quality_tag}: {y['effect']}")

    return "\n".join(lines)
