"""
Modern Translation Layer — Surface B: Life Arc
=================================================
Corrects classical Parashari scores for modern business outcomes.

Classical rules calibrated for agrarian/dharmic-society outcomes.
Many placements labeled "amazing" classically produce moderate modern
results; many "bad" placements (dushthana, Rahu, Ketu) produce
fame/wealth in modern contexts.

This module:
  1. Provides a rescaling table (classical → modern business score)
  2. Detects specific placement patterns and returns modern adjustments
  3. Never says "classical astrology is wrong" — says "classical is right
     for its time; modern interpretation requires translation"

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Tuple, Any


# ─── HELPER: house calculation ────────────────────────────────────────────────

SIGN_LORDS = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon",
    4: "Sun", 5: "Mercury", 6: "Venus", 7: "Mars",
    8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter",
}

EXALTATION = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7,
}

OWN_SIGNS = {
    "Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
    "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
    "Rahu": [10], "Ketu": [7],
}

YOGAKARAKA_LAGNAS_FOR_SATURN = {1, 6, 9}  # Taurus, Libra, Capricorn


def _get_planet_house(planet_name: str, planets: dict, lagna_idx: int) -> Optional[int]:
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
    result = []
    for p_name, pdata in planets.items():
        if not isinstance(pdata, dict):
            continue
        h = _get_planet_house(p_name, planets, lagna_idx)
        if h == house_num:
            result.append(p_name)
    return result


def _is_dignified(planet_name: str, sign_idx: int) -> bool:
    if sign_idx == EXALTATION.get(planet_name, -99):
        return True
    if sign_idx in OWN_SIGNS.get(planet_name, []):
        return True
    return False


# ─── CLASSICAL-TO-MODERN RESCALING TABLE ──────────────────────────────────────
# Each entry: placement_key -> {classical, modern, notes, detect_fn}
# detect_fn takes (planets, lagna_idx) -> bool

def _detect_jupiter_10h(planets, lagna_idx):
    return _get_planet_house("Jupiter", planets, lagna_idx) == 10

def _detect_jupiter_2h(planets, lagna_idx):
    return _get_planet_house("Jupiter", planets, lagna_idx) == 2

def _detect_jupiter_5h(planets, lagna_idx):
    return _get_planet_house("Jupiter", planets, lagna_idx) == 5

def _detect_jupiter_9h(planets, lagna_idx):
    return _get_planet_house("Jupiter", planets, lagna_idx) == 9

def _detect_jupiter_6h(planets, lagna_idx):
    return _get_planet_house("Jupiter", planets, lagna_idx) == 6

def _detect_jupiter_8h(planets, lagna_idx):
    return _get_planet_house("Jupiter", planets, lagna_idx) == 8

def _detect_jupiter_12h(planets, lagna_idx):
    return _get_planet_house("Jupiter", planets, lagna_idx) == 12

def _detect_saturn_6h(planets, lagna_idx):
    return _get_planet_house("Saturn", planets, lagna_idx) == 6

def _detect_mars_6h(planets, lagna_idx):
    return _get_planet_house("Mars", planets, lagna_idx) == 6

def _detect_rahu_6h(planets, lagna_idx):
    return _get_planet_house("Rahu", planets, lagna_idx) == 6

def _detect_sun_8h(planets, lagna_idx):
    return _get_planet_house("Sun", planets, lagna_idx) == 8

def _detect_saturn_8h(planets, lagna_idx):
    return _get_planet_house("Saturn", planets, lagna_idx) == 8

def _detect_rahu_8h(planets, lagna_idx):
    return _get_planet_house("Rahu", planets, lagna_idx) == 8

def _detect_rahu_12h(planets, lagna_idx):
    return _get_planet_house("Rahu", planets, lagna_idx) == 12

def _detect_sun_12h(planets, lagna_idx):
    return _get_planet_house("Sun", planets, lagna_idx) == 12

def _detect_rahu_11h(planets, lagna_idx):
    return _get_planet_house("Rahu", planets, lagna_idx) == 11

def _detect_rahu_10h(planets, lagna_idx):
    return _get_planet_house("Rahu", planets, lagna_idx) == 10

def _detect_rahu_2h(planets, lagna_idx):
    return _get_planet_house("Rahu", planets, lagna_idx) == 2

def _detect_rahu_venus_conjunction(planets, lagna_idx):
    r_sign = planets.get("Rahu", {}).get("sign_index", -1)
    v_sign = planets.get("Venus", {}).get("sign_index", -2)
    return r_sign >= 0 and r_sign == v_sign

def _detect_mars_saturn_conjunction(planets, lagna_idx):
    m_sign = planets.get("Mars", {}).get("sign_index", -1)
    s_sign = planets.get("Saturn", {}).get("sign_index", -2)
    return m_sign >= 0 and m_sign == s_sign

def _detect_kemadruma(planets, lagna_idx):
    """Moon without planets in 2nd or 12th from Moon sign."""
    moon_sign = planets.get("Moon", {}).get("sign_index", -1)
    if moon_sign < 0:
        return False
    sign_before = (moon_sign - 1) % 12
    sign_after = (moon_sign + 1) % 12
    for p_name, pdata in planets.items():
        if p_name in ("Moon", "Rahu", "Ketu"):
            continue
        if not isinstance(pdata, dict):
            continue
        p_sign = pdata.get("sign_index", -1)
        if p_sign in (sign_before, sign_after):
            return False  # flanking planet found — not Kemadruma
    return True

def _detect_10h_stellium_sun_mer_jup(planets, lagna_idx):
    h10 = _planets_in_house(planets, lagna_idx, 10)
    return all(p in h10 for p in ("Sun", "Mercury", "Jupiter"))


# The rescaling table
RESCALING_RULES = [
    # ── JUPITER PLACEMENTS ──
    {
        "key": "jupiter_10h",
        "detect": _detect_jupiter_10h,
        "classical": 3.0,
        "modern": 1.0,
        "notes": (
            "Classical: respected-advisor career. Modern: professor/priest/mentor roles. "
            "Moderate income, low equity accumulation. NOT a founder-scale marker."
        ),
    },
    {
        "key": "jupiter_2h",
        "detect": _detect_jupiter_2h,
        "classical": 3.0,
        "modern": 3.0,
        "notes": (
            "Classical Dhana Yoga: wisdom-wealth. Modern: knowledge-product founders, "
            "publishing, SaaS-education, intellectual property wealth. Translates well."
        ),
    },
    {
        "key": "jupiter_5h",
        "detect": _detect_jupiter_5h,
        "classical": 3.5,
        "modern": 2.5,
        "notes": (
            "Classical: children, creativity, speculation. Modern: good for creative "
            "founders, investing/VC, but not operational-scale founder."
        ),
    },
    {
        "key": "jupiter_9h",
        "detect": _detect_jupiter_9h,
        "classical": 4.0,
        "modern": 2.5,
        "notes": (
            "Classical: peak dharma, guru-placement. Modern: international business, "
            "publishing, philosophy-brands. Wisdom often comes at cost of aggressive "
            "wealth-capture."
        ),
    },
    {
        "key": "jupiter_6h",
        "detect": _detect_jupiter_6h,
        "classical": -1.5,
        "modern": 1.5,
        "notes": (
            "Jupiter in 6H = classical negative (guru in servant house). Modern: works "
            "for founders in health/medicine/education/advisory service businesses."
        ),
    },
    {
        "key": "jupiter_8h",
        "detect": _detect_jupiter_8h,
        "classical": -1.0,
        "modern": 1.5,
        "notes": (
            "Jupiter in 8H = research/occult wisdom. Modern: deep-research founders, "
            "academic-to-commercial pipelines, insurance/inheritance structures."
        ),
    },
    {
        "key": "jupiter_12h",
        "detect": _detect_jupiter_12h,
        "classical": -1.0,
        "modern": 2.0,
        "notes": (
            "Jupiter in 12H = moksha wisdom. Modern: foreign-education wealth, "
            "spiritual-commerce, publishing-for-global-audience."
        ),
    },

    # ── 6H ENTREPRENEUR PLACEMENTS ──
    {
        "key": "saturn_6h",
        "detect": _detect_saturn_6h,
        "classical": -1.0,
        "modern": 3.5,
        "notes": (
            "Saturn in 6H = peak placement for service/automation/operational businesses. "
            "Discipline + service + masses + slow-structure-building = entrepreneur's ideal."
        ),
    },
    {
        "key": "mars_6h",
        "detect": _detect_mars_6h,
        "classical": 2.5,
        "modern": 3.5,
        "notes": (
            "Mars in 6H = classical 'victory over enemies.' Modern: competitive/combat "
            "entrepreneur, sales warrior, ops-heavy founder."
        ),
    },
    {
        "key": "rahu_6h",
        "detect": _detect_rahu_6h,
        "classical": 3.0,
        "modern": 4.0,
        "notes": (
            "Rahu in 6H = disruptive service, exactly the tech-for-masses pattern. "
            "Uber, DoorDash, TezopsAI-pattern founders often have Rahu-6H energy."
        ),
    },

    # ── 8H TRANSFORMATION-FAME ──
    {
        "key": "sun_8h",
        "detect": _detect_sun_8h,
        "classical": -2.5,
        "modern": 2.0,
        "notes": (
            "Sun in 8H = classical 'ego trauma.' Modern: authority tempered by "
            "transformation. Fame through survival narrative (Bachchan pattern)."
        ),
    },
    {
        "key": "saturn_8h",
        "detect": _detect_saturn_8h,
        "classical": -2.0,
        "modern": 3.0,
        "notes": (
            "Saturn in 8H = classical 'chronic issues.' Modern: long-duration wealth "
            "through research/insurance/structural-hidden assets. Buffett-style."
        ),
    },
    {
        "key": "rahu_8h",
        "detect": _detect_rahu_8h,
        "classical": -2.0,
        "modern": 3.5,
        "notes": (
            "Rahu in 8H = classical 'sudden losses.' Modern: transformation-wealth at "
            "scale. Biotech, psychedelics/wellness, crypto/derivatives, hedge funds."
        ),
    },

    # ── 12H FOREIGN/DIGITAL ──
    {
        "key": "rahu_12h",
        "detect": _detect_rahu_12h,
        "classical": -2.0,
        "modern": 3.5,
        "notes": (
            "Rahu in 12H = classical 'foreign obsession.' Modern: massive foreign-country "
            "success, global-digital scale, crypto/web3, immigrant-founder pattern."
        ),
    },
    {
        "key": "sun_12h",
        "detect": _detect_sun_12h,
        "classical": -2.5,
        "modern": 1.0,
        "notes": (
            "Sun in 12H = classical 'ego-dissolution.' Modern: behind-scenes founder "
            "genius, not front-facing CEO. Redemption-wealth through reinvention."
        ),
    },

    # ── RAHU PLACEMENTS ──
    {
        "key": "rahu_11h",
        "detect": _detect_rahu_11h,
        "classical": 3.5,
        "modern": 5.0,
        "notes": (
            "Rahu in 11H = CLASSICAL BILLIONAIRE MARKER for modern tech/disruption. "
            "Unconventional network gains, exponential scale, foreign-networks."
        ),
    },
    {
        "key": "rahu_10h",
        "detect": _detect_rahu_10h,
        "classical": 3.0,
        "modern": 4.5,
        "notes": (
            "Rahu in 10H = unconventional career, disruptive leadership, media-genius. "
            "Modern: platform CEOs, celebrity founders, disruption-industry leaders."
        ),
    },
    {
        "key": "rahu_2h",
        "detect": _detect_rahu_2h,
        "classical": -1.5,
        "modern": 2.5,
        "notes": (
            "Rahu in 2H = classical 'erratic wealth.' Modern: unconventional wealth "
            "sources (crypto, digital, foreign). Risky but upside exists."
        ),
    },

    # ── CONJUNCTIONS ──
    {
        "key": "rahu_venus_conjunction",
        "detect": _detect_rahu_venus_conjunction,
        "classical": 0.5,
        "modern": 3.0,
        "notes": (
            "Rahu-Venus = classical 'unconventional relationships.' Modern: brand/"
            "influencer/luxury-disruption wealth. Fashion, beauty-tech, celebrity."
        ),
    },
    {
        "key": "mars_saturn_conjunction",
        "detect": _detect_mars_saturn_conjunction,
        "classical": -2.5,
        "modern": 1.5,
        "notes": (
            "Mars-Saturn = classical 'destruction and delay.' Modern: disciplined "
            "ambition, slow-aggressive building, hard-startup grinding. Musk-style."
        ),
    },

    # ── KEMADRUMA ──
    {
        "key": "kemadruma",
        "detect": _detect_kemadruma,
        "classical": -3.0,
        "modern": -0.5,
        "notes": (
            "Kemadruma = Moon unsupported. Classical: emotional isolation. Modern: "
            "self-reliant founders who build alone. Musk has this. Mildly negative "
            "(loneliness is real) but not catastrophic for modern wealth."
        ),
    },

    # ── SPECIAL STELLIUMS ──
    {
        "key": "sun_mercury_jupiter_10h_stellium",
        "detect": _detect_10h_stellium_sun_mer_jup,
        "classical": 4.5,
        "modern": 2.0,
        "notes": (
            "Classical: brilliant Raj Yoga. Modern: ethical executive with strong "
            "public reputation but LOW wealth-capture. Professor/judge/ethical-CEO "
            "types, not wealth-maximizers."
        ),
    },
]


# ─── MAIN FUNCTION ───────────────────────────────────────────────────────────

def compute_modern_corrections(chart_data: dict) -> dict:
    """
    Scan chart for placements that have significant classical-to-modern
    score divergence. Returns corrections list and net adjustment.

    Returns:
        {
            "corrections": [
                {
                    "key": "saturn_6h",
                    "classical_score": -1.0,
                    "modern_score": 3.5,
                    "adjustment": +4.5,
                    "notes": "...",
                }
            ],
            "net_adjustment": float,
            "classical_vs_modern_meta": {
                "note": str,
                "total_classical_if_used": float,
                "total_modern_actual": float,
            }
        }
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    corrections = []
    total_classical = 0.0
    total_modern = 0.0

    for rule in RESCALING_RULES:
        if rule["detect"](planets, lagna_idx):
            classical = rule["classical"]
            modern = rule["modern"]
            adjustment = modern - classical

            corrections.append({
                "key": rule["key"],
                "classical_score": classical,
                "modern_score": modern,
                "adjustment": round(adjustment, 1),
                "notes": rule["notes"],
            })

            total_classical += classical
            total_modern += modern

    net_adjustment = round(total_modern - total_classical, 1)

    return {
        "corrections": corrections,
        "net_adjustment": net_adjustment,
        "classical_vs_modern_meta": {
            "note": (
                "Many classical placements are scored differently in modern business "
                "contexts. Antar applies a modern interpretation layer calibrated for "
                "business/wealth/fame outcomes — not king-pleasing/land-holding outcomes "
                "classical texts addressed. Classical astrology is right for its time; "
                "modern interpretation requires translation."
            ),
            "total_classical_contribution": round(total_classical, 1),
            "total_modern_contribution": round(total_modern, 1),
            "difference": net_adjustment,
        },
    }


def get_modern_placement_note(placement_key: str) -> Optional[str]:
    """
    Get the modern interpretation note for a specific placement.
    Used by category scorers to add context to their reasoning.
    """
    for rule in RESCALING_RULES:
        if rule["key"] == placement_key:
            return rule["notes"]
    return None
