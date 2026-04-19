"""
Dushthana-as-Wealth Detector — Surface B: Life Arc
=====================================================
Detects when 6H / 8H / 12H placements activate as modern wealth producers.

Classical Parashari treats houses 6, 8, 12 as uniformly negative (enemies,
chronic issues, losses). In modern business contexts, these houses often
produce outsized wealth when activated by specific planet combinations.

Three patterns:
  1. 6H_ENTREPRENEUR — service, automation, operational grit
  2. 8H_TRANSFORMATION_WEALTH — deep research, insurance, fame-through-crisis
  3. 12H_FOREIGN_DIGITAL_WEALTH — global-scale, digital, immigrant-founder

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any


# ─── DIGNITY / HOUSE HELPERS ────────────────────────────────────────────────
# (Duplicated from modern_translation.py to keep modules independent)

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

# Yogakaraka planets by lagna sign_index (same table as business_fit.py)
YOGAKARAKA_BY_LAGNA = {
    0:  None,       # Aries
    1:  "Saturn",   # Taurus — rules 9H + 10H
    2:  None,       # Gemini
    3:  "Mars",     # Cancer — rules 5H + 10H
    4:  "Mars",     # Leo — rules 4H + 9H
    5:  None,       # Virgo
    6:  "Saturn",   # Libra — rules 4H + 5H
    7:  None,       # Scorpio
    8:  None,       # Sagittarius
    9:  "Venus",    # Capricorn — rules 5H + 10H (note: Saturn rules 1H+2H but Venus is yogakaraka)
    10: None,       # Aquarius
    11: None,       # Pisces
}


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


def _is_dignified(planet_name: str, sign_idx: int) -> bool:
    """Planet is exalted or in own sign."""
    if sign_idx == EXALTATION.get(planet_name, -99):
        return True
    if sign_idx in OWN_SIGNS.get(planet_name, []):
        return True
    return False


def _get_planet_sign(planet_name: str, planets: dict) -> int:
    """Get sign_index for a planet, or -1 if unknown."""
    return planets.get(planet_name, {}).get("sign_index", -1)


def _same_sign(p1: str, p2: str, planets: dict) -> bool:
    """Check if two planets are conjunct (same sign)."""
    s1 = _get_planet_sign(p1, planets)
    s2 = _get_planet_sign(p2, planets)
    return s1 >= 0 and s1 == s2


def _get_house_lord(house_num: int, lagna_idx: int) -> str:
    """Return the lord of a given house (1-12)."""
    sign_idx = (lagna_idx + house_num - 1) % 12
    return SIGN_LORDS[sign_idx]


# ─── PATTERN 1: 6H ENTREPRENEUR ────────────────────────────────────────────

def _detect_6h_entrepreneur(planets: dict, lagna_idx: int) -> dict:
    """
    6th house = service, enemies, labor, debt, disease (classically negative).
    Modern: entrepreneurs who build operational/service businesses thrive with
    strong 6H — they outwork competitors, serve the masses, resolve disputes.

    Activation requires: functional malefics in 6H (Saturn, Mars, Rahu)
    that are NOT debilitated, plus supporting factors from 10H/11H.
    """
    h6_planets = _planets_in_house(planets, lagna_idx, 6)

    strength = 0.0
    signals = []
    activators_found = []

    # ── Primary activators: malefics in 6H ──
    if "Saturn" in h6_planets:
        sat_sign = _get_planet_sign("Saturn", planets)
        if _is_dignified("Saturn", sat_sign):
            strength += 4.0
            signals.append("Saturn dignified in 6H — peak service-automation entrepreneur")
        else:
            strength += 2.5
            signals.append("Saturn in 6H — disciplined service builder")
        activators_found.append("Saturn")

        # Check if Saturn is yogakaraka for this lagna
        yk = YOGAKARAKA_BY_LAGNA.get(lagna_idx)
        if yk == "Saturn":
            strength += 2.0
            signals.append("Saturn is yogakaraka — 6H service becomes primary career vehicle")

    if "Mars" in h6_planets:
        mars_sign = _get_planet_sign("Mars", planets)
        if _is_dignified("Mars", mars_sign):
            strength += 3.5
            signals.append("Mars dignified in 6H — competitive warrior-entrepreneur")
        else:
            strength += 2.0
            signals.append("Mars in 6H — aggressive service/ops builder")
        activators_found.append("Mars")

    if "Rahu" in h6_planets:
        strength += 3.0
        signals.append("Rahu in 6H — disruptive service innovator (tech-for-masses pattern)")
        activators_found.append("Rahu")

    # ── Secondary: benefics in 6H weaken the pattern ──
    if "Jupiter" in h6_planets:
        strength += 1.0  # mild positive — service through wisdom
        signals.append("Jupiter in 6H — service through education/health (classically weak, modern moderate)")

    if "Venus" in h6_planets:
        strength += 0.5
        signals.append("Venus in 6H — luxury-service, beauty industry ops")

    # ── Supporting factors ──
    h10_planets = _planets_in_house(planets, lagna_idx, 10)
    h11_planets = _planets_in_house(planets, lagna_idx, 11)

    # 6H lord in 10H or 11H = service becomes career/gains
    h6_lord = _get_house_lord(6, lagna_idx)
    h6_lord_house = _get_planet_house(h6_lord, planets, lagna_idx)
    if h6_lord_house in (10, 11):
        strength += 1.5
        signals.append(f"6H lord ({h6_lord}) in {h6_lord_house}H — service converts to career gains")

    # 10H lord in 6H = career expressed through service
    h10_lord = _get_house_lord(10, lagna_idx)
    h10_lord_house = _get_planet_house(h10_lord, planets, lagna_idx)
    if h10_lord_house == 6:
        strength += 1.5
        signals.append(f"10H lord ({h10_lord}) in 6H — career fundamentally service-oriented")

    # Saturn-Mars conjunction anywhere = disciplined aggression
    if _same_sign("Saturn", "Mars", planets) and "Saturn" not in h6_planets:
        strength += 1.0
        signals.append("Saturn-Mars conjunction — disciplined aggression (ops-heavy founder energy)")

    if not activators_found:
        # No functional malefics in 6H — pattern not active
        return {
            "pattern": "6H_ENTREPRENEUR",
            "detected": False,
            "strength": 0.0,
            "signals": [],
            "business_implication": None,
        }

    # ── Determine business implication ──
    if strength >= 6.0:
        implication = (
            "Strong 6H activation — chart structurally favors operational/service "
            "businesses that serve the masses. Think automation, healthcare, labor "
            "platforms, dispute resolution, outsourcing."
        )
    elif strength >= 3.0:
        implication = (
            "Moderate 6H activation — service-oriented businesses are viable but may "
            "need complementary strengths. Lean into operational discipline and "
            "problem-solving for underserved markets."
        )
    else:
        implication = (
            "Mild 6H activation — some service-business capacity exists but is not "
            "the chart's primary vehicle. Better as supporting energy to another category."
        )

    return {
        "pattern": "6H_ENTREPRENEUR",
        "detected": True,
        "strength": round(strength, 1),
        "signals": signals,
        "business_implication": implication,
    }


# ─── PATTERN 2: 8H TRANSFORMATION WEALTH ────────────────────────────────────

def _detect_8h_transformation_wealth(planets: dict, lagna_idx: int) -> dict:
    """
    8th house = death, chronic issues, hidden things, other people's money
    (classically very negative).
    Modern: transformation-wealth, fame-through-crisis, research breakthroughs,
    insurance/derivatives, deep-tech, biotech, celebrity survival narratives.

    Bachchan pattern: Sun + stellium in 8H = fame through near-death and
    reinvention. Authority tempered by transformation.
    """
    h8_planets = _planets_in_house(planets, lagna_idx, 8)

    strength = 0.0
    signals = []
    activators_found = []

    # ── Stellium detection (3+ planets) ──
    if len(h8_planets) >= 3:
        strength += 3.0
        signals.append(f"8H stellium ({len(h8_planets)} planets) — concentrated transformation energy")

    # ── Primary activators ──
    if "Sun" in h8_planets:
        strength += 2.5
        signals.append("Sun in 8H — fame through survival/crisis narrative (Bachchan pattern)")
        activators_found.append("Sun")

    if "Saturn" in h8_planets:
        sat_sign = _get_planet_sign("Saturn", planets)
        if _is_dignified("Saturn", sat_sign):
            strength += 3.5
            signals.append("Saturn dignified in 8H — long-duration hidden-asset wealth (Buffett pattern)")
        else:
            strength += 2.0
            signals.append("Saturn in 8H — slow research/structural wealth from hidden sources")
        activators_found.append("Saturn")

    if "Rahu" in h8_planets:
        strength += 3.0
        signals.append("Rahu in 8H — transformation-wealth at scale (biotech, crypto, derivatives)")
        activators_found.append("Rahu")

    if "Mars" in h8_planets:
        mars_sign = _get_planet_sign("Mars", planets)
        if _is_dignified("Mars", mars_sign):
            strength += 2.5
            signals.append("Mars dignified in 8H — surgical precision in research/investigation")
        else:
            strength += 1.5
            signals.append("Mars in 8H — aggressive transformation, accident-to-fortune narratives")
        activators_found.append("Mars")

    if "Jupiter" in h8_planets:
        strength += 2.0
        signals.append("Jupiter in 8H — wisdom from deep research, academic-to-commercial pipeline")
        activators_found.append("Jupiter")

    if "Mercury" in h8_planets:
        strength += 1.5
        signals.append("Mercury in 8H — analytical/investigative wealth (forensics, data-mining, research)")
        activators_found.append("Mercury")

    if "Ketu" in h8_planets:
        strength += 1.0
        signals.append("Ketu in 8H — past-life research karma, intuitive breakthroughs")
        activators_found.append("Ketu")

    # ── Supporting factors ──

    # 8H lord in 2H or 11H = hidden wealth becomes manifest gains
    h8_lord = _get_house_lord(8, lagna_idx)
    h8_lord_house = _get_planet_house(h8_lord, planets, lagna_idx)
    if h8_lord_house in (2, 11):
        strength += 1.5
        signals.append(f"8H lord ({h8_lord}) in {h8_lord_house}H — transformation converts to tangible wealth")

    # 2H lord in 8H = wealth through other people's money
    h2_lord = _get_house_lord(2, lagna_idx)
    h2_lord_house = _get_planet_house(h2_lord, planets, lagna_idx)
    if h2_lord_house == 8:
        strength += 1.0
        signals.append(f"2H lord ({h2_lord}) in 8H — wealth via inheritance, insurance, OPM structures")

    # Sun-Saturn conjunction in 8H = authority + endurance through crisis
    if "Sun" in h8_planets and "Saturn" in h8_planets:
        strength += 1.5
        signals.append("Sun-Saturn in 8H — authority forged through endurance and crisis")

    if not activators_found:
        return {
            "pattern": "8H_TRANSFORMATION_WEALTH",
            "detected": False,
            "strength": 0.0,
            "signals": [],
            "business_implication": None,
        }

    if strength >= 6.0:
        implication = (
            "Strong 8H activation — chart structurally favors transformation-wealth: "
            "deep research commercialization, crisis-to-fame narratives, insurance/"
            "derivatives, biotech, or other people's money structures."
        )
    elif strength >= 3.0:
        implication = (
            "Moderate 8H activation — some capacity for transformation-wealth. "
            "Research-heavy or crisis-narrative businesses can work, but pair with "
            "other chart strengths for full activation."
        )
    else:
        implication = (
            "Mild 8H activation — transformation energy exists but is not the "
            "chart's primary wealth vehicle. May manifest as resilience rather "
            "than active business pattern."
        )

    return {
        "pattern": "8H_TRANSFORMATION_WEALTH",
        "detected": True,
        "strength": round(strength, 1),
        "signals": signals,
        "business_implication": implication,
    }


# ─── PATTERN 3: 12H FOREIGN/DIGITAL WEALTH ──────────────────────────────────

def _detect_12h_foreign_digital_wealth(planets: dict, lagna_idx: int) -> dict:
    """
    12th house = losses, isolation, foreign lands, moksha (classically negative).
    Modern: foreign-country success, global-digital scale, remote/distributed
    businesses, immigrant-founder pattern, spiritual-commerce.

    Musk pattern: 12H emphasis + Rahu-11H = foreign-country billionaire.
    """
    h12_planets = _planets_in_house(planets, lagna_idx, 12)

    strength = 0.0
    signals = []
    activators_found = []

    # ── Stellium detection ──
    if len(h12_planets) >= 3:
        strength += 2.5
        signals.append(f"12H stellium ({len(h12_planets)} planets) — concentrated foreign/digital energy")

    # ── Primary activators ──
    if "Rahu" in h12_planets:
        strength += 3.5
        signals.append("Rahu in 12H — massive foreign-country success, global-digital scale, immigrant-founder")
        activators_found.append("Rahu")

    if "Jupiter" in h12_planets:
        jup_sign = _get_planet_sign("Jupiter", planets)
        if _is_dignified("Jupiter", jup_sign):
            strength += 3.0
            signals.append("Jupiter dignified in 12H — wisdom-commerce at global scale, spiritual-publishing")
        else:
            strength += 2.0
            signals.append("Jupiter in 12H — foreign education, international advisory, publishing-for-global-audience")
        activators_found.append("Jupiter")

    if "Venus" in h12_planets:
        ven_sign = _get_planet_sign("Venus", planets)
        if _is_dignified("Venus", ven_sign):
            strength += 3.0
            signals.append("Venus dignified in 12H — luxury-foreign business, hospitality-abroad, art-exports")
        else:
            strength += 1.5
            signals.append("Venus in 12H — creative/luxury businesses with foreign clientele")
        activators_found.append("Venus")

    if "Sun" in h12_planets:
        strength += 1.5
        signals.append("Sun in 12H — behind-scenes founder, not front-facing CEO. Reinvention-wealth.")
        activators_found.append("Sun")

    if "Moon" in h12_planets:
        strength += 1.0
        signals.append("Moon in 12H — emotional connection to foreign markets, intuitive global timing")
        activators_found.append("Moon")

    if "Saturn" in h12_planets:
        strength += 1.5
        signals.append("Saturn in 12H — structured foreign operations, slow-build international presence")
        activators_found.append("Saturn")

    if "Mercury" in h12_planets:
        strength += 1.5
        signals.append("Mercury in 12H — digital/remote business models, foreign communications/media")
        activators_found.append("Mercury")

    if "Ketu" in h12_planets:
        strength += 2.0
        signals.append("Ketu in 12H — natural moksha placement, spiritual-commerce, retreat businesses")
        activators_found.append("Ketu")

    # ── Supporting factors ──

    # Rahu in 11H while 12H active = foreign gains amplified
    rahu_house = _get_planet_house("Rahu", planets, lagna_idx)
    if rahu_house == 11 and activators_found:
        strength += 2.0
        signals.append("Rahu in 11H + 12H activation — foreign-network gains amplify global business")

    # 12H lord in 2H or 11H = foreign activity converts to tangible wealth
    h12_lord = _get_house_lord(12, lagna_idx)
    h12_lord_house = _get_planet_house(h12_lord, planets, lagna_idx)
    if h12_lord_house in (2, 11):
        strength += 1.5
        signals.append(f"12H lord ({h12_lord}) in {h12_lord_house}H — foreign activities convert to domestic wealth")

    # 9H lord in 12H = dharma expressed through foreign lands
    h9_lord = _get_house_lord(9, lagna_idx)
    h9_lord_house = _get_planet_house(h9_lord, planets, lagna_idx)
    if h9_lord_house == 12:
        strength += 1.0
        signals.append(f"9H lord ({h9_lord}) in 12H — purpose/dharma fulfilled through foreign engagement")

    # 4H lord in 12H = home-base is abroad
    h4_lord = _get_house_lord(4, lagna_idx)
    h4_lord_house = _get_planet_house(h4_lord, planets, lagna_idx)
    if h4_lord_house == 12:
        strength += 1.0
        signals.append(f"4H lord ({h4_lord}) in 12H — home-base established abroad, immigrant-founder pattern")

    if not activators_found:
        return {
            "pattern": "12H_FOREIGN_DIGITAL_WEALTH",
            "detected": False,
            "strength": 0.0,
            "signals": [],
            "business_implication": None,
        }

    if strength >= 6.0:
        implication = (
            "Strong 12H activation — chart structurally favors foreign/global/digital "
            "businesses. Immigrant-founder energy, global-platform scale, remote-distributed "
            "models, spiritual-commerce, or export-oriented operations."
        )
    elif strength >= 3.0:
        implication = (
            "Moderate 12H activation — foreign/digital business capacity exists. "
            "International clientele or digital-first models are viable, but pair "
            "with domestic strengths for stability."
        )
    else:
        implication = (
            "Mild 12H activation — some foreign/digital business capacity but not "
            "the chart's primary vehicle. May manifest as occasional international "
            "opportunities rather than core business model."
        )

    return {
        "pattern": "12H_FOREIGN_DIGITAL_WEALTH",
        "detected": True,
        "strength": round(strength, 1),
        "signals": signals,
        "business_implication": implication,
    }


# ─── MAIN FUNCTION ──────────────────────────────────────────────────────────

def detect_modern_dushthana_wealth_pattern(chart_data: dict) -> dict:
    """
    Detects when dushthana placements (6H/8H/12H) activate as modern
    wealth producers.

    Args:
        chart_data: Chart data dict with planets, lagna, etc.

    Returns:
        {
            "patterns_detected": [
                {
                    "pattern": "6H_ENTREPRENEUR" | "8H_TRANSFORMATION_WEALTH" | "12H_FOREIGN_DIGITAL_WEALTH",
                    "detected": bool,
                    "strength": float,
                    "signals": [str],
                    "business_implication": str | None,
                }
            ],
            "any_detected": bool,
            "strongest_pattern": str | None,
            "total_dushthana_strength": float,
            "meta": {
                "note": str,
            }
        }
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    p6 = _detect_6h_entrepreneur(planets, lagna_idx)
    p8 = _detect_8h_transformation_wealth(planets, lagna_idx)
    p12 = _detect_12h_foreign_digital_wealth(planets, lagna_idx)

    patterns = [p6, p8, p12]
    detected = [p for p in patterns if p["detected"]]
    total_strength = sum(p["strength"] for p in detected)

    strongest = None
    if detected:
        strongest = max(detected, key=lambda p: p["strength"])["pattern"]

    return {
        "patterns_detected": patterns,
        "any_detected": len(detected) > 0,
        "strongest_pattern": strongest,
        "total_dushthana_strength": round(total_strength, 1),
        "meta": {
            "note": (
                "Houses 6, 8, and 12 are classically negative (enemies, death, losses). "
                "In modern business contexts, these houses often produce outsized wealth "
                "when activated by specific planet combinations. This detector identifies "
                "charts where dushthana placements are modern wealth producers rather than "
                "classical liabilities."
            ),
        },
    }
