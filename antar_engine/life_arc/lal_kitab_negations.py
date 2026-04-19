"""
Lal Kitab Condition-Dependent Negation — Surface B: Life Arc
==============================================================
Warnings-only layer that detects when Lal Kitab conditions (sleeping
planets, rin debts, enemy houses) could negate otherwise-positive
business-fit scores.

This module does NOT modify scores directly. It returns structured
warnings that the integration layer (business_fit.py v3) can attach
to category results. The AI layer can then communicate these as
"conditions that could block this category from activating."

Three detection areas:
  1. Sleeping Yogas — planets in dusthana with no benefic support
  2. Rin Debts — ancestral karmic debts that block specific life areas
  3. Enemy House Conditions — planets in signs ruled by their enemies

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any


# ─── PLANET-CATEGORY MAPPING ────────────────────────────────────────────────
# Maps each planet to the business categories it primarily activates.
# A sleeping planet or rin debt affecting that planet produces a warning
# for the associated categories.

PLANET_CATEGORY_MAP = {
    "Sun": ["PLATFORM", "INSTITUTIONAL_AUTHORITY"],
    "Moon": ["SERVICE_MASSES_AUTOMATION", "CREATIVE"],
    "Mars": ["PHYSICAL_OPS", "SPECULATION"],
    "Mercury": ["PLATFORM", "BROKERING", "ADVISORY"],
    "Jupiter": ["ADVISORY", "INSTITUTIONAL_AUTHORITY", "REAL_ESTATE"],
    "Venus": ["CREATIVE", "REAL_ESTATE", "BROKERING"],
    "Saturn": ["SERVICE_MASSES_AUTOMATION", "PHYSICAL_OPS", "INSTITUTIONAL_AUTHORITY"],
    "Rahu": ["PLATFORM", "SPECULATION", "SERVICE_MASSES_AUTOMATION"],
    "Ketu": ["ADVISORY", "CREATIVE"],
}


# ─── SLEEPING PLANET RULES ──────────────────────────────────────────────────
# From lal_kitab_advanced.py — planets sleeping in dusthana houses

LK_SLEEPING_HOUSES = {
    "Sun":     [6, 8, 12],
    "Moon":    [6, 8, 12],
    "Mars":    [8, 12],
    "Mercury": [8, 12],
    "Jupiter": [3, 6, 8, 12],
    "Venus":   [6, 8, 12],
    "Saturn":  [6, 8, 12],   # Note: Saturn in 6H is modern-positive but LK still flags it
}

# Benefic planets for LK sleeping-planet checks
LK_BENEFICS = {"Jupiter", "Venus", "Moon", "Mercury"}

SLEEPING_IMPACT = {
    "Sun":     "Career authority blocked, leadership capacity dormant",
    "Moon":    "Emotional intelligence suppressed, public-facing work hampered",
    "Mars":    "Execution energy blocked, physical ventures stalled",
    "Mercury": "Communication/deals ineffective, platform building compromised",
    "Jupiter": "Wisdom/expansion blocked, advisory capacity dormant",
    "Venus":   "Creative/luxury capacity dormant, partnerships blocked",
    "Saturn":  "Discipline/structure blocked, service-building capacity dormant",
}


# ─── RIN DEBT RULES ─────────────────────────────────────────────────────────
# Condition-dependent: rin debts that block specific business categories

RIN_CATEGORY_IMPACT = {
    "pitru_rin": {
        "label": "Father's debt (Pitru Rin)",
        "affected_categories": ["INSTITUTIONAL_AUTHORITY", "PLATFORM"],
        "condition": "Sun afflicted by Saturn/Rahu in houses 1/5/9/10",
        "warning": (
            "Pitru Rin active — ancestral male-line debt blocks authority-based "
            "ventures. Leadership roles face unexpected resistance until debt is "
            "addressed. Institutional authority and large-scale platform ambitions "
            "encounter structural friction."
        ),
    },
    "matru_rin": {
        "label": "Mother's debt (Matru Rin)",
        "affected_categories": ["SERVICE_MASSES_AUTOMATION", "REAL_ESTATE"],
        "condition": "Moon afflicted by Rahu/Ketu in houses 4/6",
        "warning": (
            "Matru Rin active — maternal-line karmic debt affects nurturing/service "
            "businesses. Real estate and property ventures face emotional blocks. "
            "Service-to-masses work needs extra grounding."
        ),
    },
    "stri_rin": {
        "label": "Spouse/partner debt (Stri Rin)",
        "affected_categories": ["BROKERING", "CREATIVE"],
        "condition": "Venus afflicted by Rahu or debilitated in houses 2/7",
        "warning": (
            "Stri Rin active — partnership karma blocks deal-making and creative "
            "collaborations. Brokering ventures need extra care around partner "
            "dynamics. Creative output benefits from solo work over collaboration."
        ),
    },
    "putra_rin": {
        "label": "Children's debt (Putra Rin)",
        "affected_categories": ["SPECULATION", "CREATIVE"],
        "condition": "Jupiter afflicted in houses 5/9, or 5H lord debilitated",
        "warning": (
            "Putra Rin active — 5th house blessings blocked. Speculation and "
            "creative risk-taking face karmic friction. Investment timing needs "
            "extra caution. Creative projects stall without structured approach."
        ),
    },
    "bhatru_rin": {
        "label": "Sibling debt (Bhatru Rin)",
        "affected_categories": ["BROKERING", "PHYSICAL_OPS"],
        "condition": "Mars afflicted in houses 3/6, or 3H lord with malefics",
        "warning": (
            "Bhatru Rin active — sibling-line karmic debt affects collaboration "
            "and operational partnerships. Physical operations with partners face "
            "friction. Brokering works better solo than in teams."
        ),
    },
}


# ─── ENEMY HOUSE RULES ──────────────────────────────────────────────────────
# From lal_kitab_advanced.py — planet in sign ruled by its enemy

SIGN_LORDS_BY_NAME = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

PLANET_ENEMIES = {
    "Sun":     ["Saturn", "Venus", "Rahu"],
    "Moon":    ["Rahu", "Ketu"],
    "Mars":    ["Mercury", "Rahu"],
    "Mercury": ["Moon", "Rahu"],
    "Jupiter": ["Mercury", "Venus", "Saturn", "Rahu"],
    "Venus":   ["Sun", "Moon", "Rahu"],
    "Saturn":  ["Sun", "Moon", "Mars"],
    "Rahu":    ["Sun", "Moon", "Mars", "Jupiter"],
    "Ketu":    ["Sun", "Moon", "Mercury", "Jupiter"],
}


# ─── DETECTION FUNCTIONS ────────────────────────────────────────────────────

def _get_planet_house(planet_name: str, planets: dict, lagna_idx: int) -> Optional[int]:
    """Get house number (1-12) for a planet."""
    pdata = planets.get(planet_name, {})
    if not pdata:
        return None
    h = pdata.get("house")
    if h is not None:
        try:
            return int(h)
        except (TypeError, ValueError):
            pass
    si = pdata.get("sign_index", -1)
    if si < 0:
        return None
    return (si - lagna_idx + 12) % 12 + 1


def _planets_in_house(planets: dict, lagna_idx: int, house_num: int) -> List[str]:
    """Return list of planet names occupying a given house."""
    result = []
    for p_name, pdata in planets.items():
        if not isinstance(pdata, dict):
            continue
        h = _get_planet_house(p_name, planets, lagna_idx)
        if h == house_num:
            result.append(p_name)
    return result


def detect_sleeping_planets(planets: dict, lagna_idx: int) -> List[dict]:
    """
    Detect sleeping planets using Lal Kitab rules.
    A planet is sleeping when:
      1. It occupies one of its sleeping houses (dusthana)
      2. No benefic planet is in the same house or aspects it from 7th

    Returns list of sleeping planet warnings with affected categories.
    """
    # Find which houses have benefics
    benefic_houses = set()
    for p_name, pdata in planets.items():
        if not isinstance(pdata, dict):
            continue
        if p_name in LK_BENEFICS:
            h = _get_planet_house(p_name, planets, lagna_idx)
            if h:
                benefic_houses.add(h)

    sleeping = []

    for planet, sleeping_houses in LK_SLEEPING_HOUSES.items():
        pdata = planets.get(planet, {})
        if not isinstance(pdata, dict):
            continue

        house = _get_planet_house(planet, planets, lagna_idx)
        if house is None or house not in sleeping_houses:
            continue

        # Check same-house benefic support
        same_house = _planets_in_house(planets, lagna_idx, house)
        has_benefic_support = any(p in LK_BENEFICS and p != planet for p in same_house)

        # Check 7th-house aspect from benefic
        seventh_from = ((house - 1 + 6) % 12) + 1
        has_7th_aspect = seventh_from in benefic_houses

        if not has_benefic_support and not has_7th_aspect:
            affected = PLANET_CATEGORY_MAP.get(planet, [])
            sleeping.append({
                "planet": planet,
                "house": house,
                "impact": SLEEPING_IMPACT.get(planet, "Significations blocked"),
                "affected_categories": affected,
                "warning": (
                    f"{planet} is sleeping in house {house} — its significations "
                    f"are dormant. Categories affected: {', '.join(affected)}. "
                    f"These business areas face activation resistance until the "
                    f"sleeping condition is resolved."
                ),
                "severity": "high" if planet in ("Sun", "Jupiter", "Saturn") else "medium",
            })

    return sleeping


def detect_rin_debts(planets: dict, lagna_idx: int) -> List[dict]:
    """
    Detect active Rin (karmic debts) from chart placements.
    Uses simplified detection logic matching lk_aspects_rin.py patterns.

    Returns list of active rin debts with affected categories.
    """
    active_rins = []

    # ── Pitru Rin: Sun afflicted by Saturn/Rahu in key houses ──
    sun_house = _get_planet_house("Sun", planets, lagna_idx)
    if sun_house in (1, 5, 9, 10):
        sun_sign = planets.get("Sun", {}).get("sign_index", -1)
        sat_sign = planets.get("Saturn", {}).get("sign_index", -2)
        rahu_sign = planets.get("Rahu", {}).get("sign_index", -3)
        if sun_sign >= 0 and (sun_sign == sat_sign or sun_sign == rahu_sign):
            active_rins.append({
                **RIN_CATEGORY_IMPACT["pitru_rin"],
                "detected": True,
                "severity": "high",
            })

    # ── Matru Rin: Moon afflicted by Rahu/Ketu in houses 4/6 ──
    moon_house = _get_planet_house("Moon", planets, lagna_idx)
    if moon_house in (4, 6):
        moon_sign = planets.get("Moon", {}).get("sign_index", -1)
        rahu_sign = planets.get("Rahu", {}).get("sign_index", -2)
        ketu_sign = planets.get("Ketu", {}).get("sign_index", -3)
        if moon_sign >= 0 and (moon_sign == rahu_sign or moon_sign == ketu_sign):
            active_rins.append({
                **RIN_CATEGORY_IMPACT["matru_rin"],
                "detected": True,
                "severity": "high",
            })

    # ── Stri Rin: Venus afflicted by Rahu or debilitated in houses 2/7 ──
    venus_house = _get_planet_house("Venus", planets, lagna_idx)
    if venus_house in (2, 7):
        venus_sign = planets.get("Venus", {}).get("sign_index", -1)
        rahu_sign = planets.get("Rahu", {}).get("sign_index", -2)
        venus_debilitated = venus_sign == 5  # Virgo
        venus_rahu_conjunct = venus_sign >= 0 and venus_sign == rahu_sign
        if venus_debilitated or venus_rahu_conjunct:
            active_rins.append({
                **RIN_CATEGORY_IMPACT["stri_rin"],
                "detected": True,
                "severity": "high" if venus_debilitated else "medium",
            })

    # ── Putra Rin: Jupiter afflicted in houses 5/9 ──
    jup_house = _get_planet_house("Jupiter", planets, lagna_idx)
    if jup_house in (5, 9):
        jup_sign = planets.get("Jupiter", {}).get("sign_index", -1)
        sat_sign = planets.get("Saturn", {}).get("sign_index", -2)
        rahu_sign = planets.get("Rahu", {}).get("sign_index", -3)
        jup_debilitated = jup_sign == 9  # Capricorn
        jup_afflicted = jup_sign >= 0 and (jup_sign == sat_sign or jup_sign == rahu_sign)
        if jup_debilitated or jup_afflicted:
            active_rins.append({
                **RIN_CATEGORY_IMPACT["putra_rin"],
                "detected": True,
                "severity": "high" if jup_debilitated else "medium",
            })

    # ── Bhatru Rin: Mars afflicted in houses 3/6 ──
    mars_house = _get_planet_house("Mars", planets, lagna_idx)
    if mars_house in (3, 6):
        mars_sign = planets.get("Mars", {}).get("sign_index", -1)
        sat_sign = planets.get("Saturn", {}).get("sign_index", -2)
        rahu_sign = planets.get("Rahu", {}).get("sign_index", -3)
        mars_debilitated = mars_sign == 3  # Cancer
        mars_afflicted = mars_sign >= 0 and (mars_sign == sat_sign or mars_sign == rahu_sign)
        if mars_debilitated or mars_afflicted:
            active_rins.append({
                **RIN_CATEGORY_IMPACT["bhatru_rin"],
                "detected": True,
                "severity": "high" if mars_debilitated else "medium",
            })

    return active_rins


def detect_enemy_house_conditions(planets: dict, lagna_idx: int) -> List[dict]:
    """
    Detect planets in enemy-ruled signs (Lal Kitab enemy house concept).
    A planet in an enemy's sign has its significations actively opposed.

    Returns list of enemy-house warnings with affected categories.
    """
    warnings = []

    for planet in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        pdata = planets.get(planet, {})
        if not isinstance(pdata, dict):
            continue

        sign_idx = pdata.get("sign_index", -1)
        if sign_idx < 0 or sign_idx >= 12:
            continue

        sign_name = SIGN_NAMES[sign_idx]
        sign_lord = SIGN_LORDS_BY_NAME.get(sign_name, "")
        enemies = PLANET_ENEMIES.get(planet, [])

        if sign_lord in enemies:
            affected = PLANET_CATEGORY_MAP.get(planet, [])
            house = _get_planet_house(planet, planets, lagna_idx)
            warnings.append({
                "planet": planet,
                "sign": sign_name,
                "house": house,
                "enemy_lord": sign_lord,
                "affected_categories": affected,
                "warning": (
                    f"{planet} in {sign_name} (ruled by enemy {sign_lord}) — "
                    f"its significations face active opposition. During {planet}'s "
                    f"dasha/antardasha, categories {', '.join(affected)} may "
                    f"underperform expectations."
                ),
                "severity": "medium",
            })

    return warnings


# ─── MAIN FUNCTION ──────────────────────────────────────────────────────────

def check_lal_kitab_negations(chart_data: dict) -> dict:
    """
    Run all Lal Kitab negation checks and return structured warnings.

    This is a warnings-only function — it does NOT modify scores.
    The integration layer in business_fit.py attaches these warnings
    to category results so the AI can communicate blocking conditions.

    Args:
        chart_data: Chart data dict with planets, lagna, etc.

    Returns:
        {
            "sleeping_planets": [...],
            "rin_debts": [...],
            "enemy_houses": [...],
            "has_warnings": bool,
            "categories_with_warnings": {
                "PLATFORM": ["sleeping: Mercury", "rin: Pitru Rin"],
                ...
            },
            "meta": {
                "note": str,
            }
        }
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    sleeping = detect_sleeping_planets(planets, lagna_idx)
    rins = detect_rin_debts(planets, lagna_idx)
    enemies = detect_enemy_house_conditions(planets, lagna_idx)

    # Aggregate warnings by category
    category_warnings: Dict[str, List[str]] = {}

    for sp in sleeping:
        for cat in sp["affected_categories"]:
            category_warnings.setdefault(cat, [])
            category_warnings[cat].append(f"sleeping: {sp['planet']} in H{sp['house']}")

    for rin in rins:
        for cat in rin["affected_categories"]:
            category_warnings.setdefault(cat, [])
            category_warnings[cat].append(f"rin: {rin['label']}")

    for enemy in enemies:
        for cat in enemy["affected_categories"]:
            category_warnings.setdefault(cat, [])
            category_warnings[cat].append(f"enemy: {enemy['planet']} in {enemy['sign']}")

    has_warnings = bool(sleeping or rins or enemies)

    return {
        "sleeping_planets": sleeping,
        "rin_debts": rins,
        "enemy_houses": enemies,
        "has_warnings": has_warnings,
        "categories_with_warnings": category_warnings,
        "meta": {
            "note": (
                "Lal Kitab negation warnings identify conditions that could block "
                "otherwise-positive business-fit categories from activating. These "
                "are not score adjustments — they are conditional flags. A category "
                "with a sleeping planet or rin debt warning may still score well "
                "structurally, but activation depends on addressing the blocking "
                "condition."
            ),
        },
    }
