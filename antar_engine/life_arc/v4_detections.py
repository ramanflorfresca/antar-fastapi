"""
v4 Detection Functions — Surface B: Life Arc
===============================================
Four new detection functions derived from N=5 validation analysis
(Musk, Gates, Ambani, Mallya, Shashi).

1. detect_viparita_stack() — Viparita Raj Yoga stacking (rise-through-adversity)
2. detect_identity_overwhelm() — H1 stellium without output-engine (CHARISMA trap)
3. check_moon_md_h2_pressure() — Moon MD emotional-wealth-pressure trap
4. check_d2_hora_business_mismatch() — D-2 hora vs business category mismatch

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any


# ─── HELPERS ────────────────────────────────────────────────────────────────

SIGN_LORDS = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon",
    4: "Sun", 5: "Mercury", 6: "Venus", 7: "Mars",
    8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter",
}


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


def _get_house_lord(house_num: int, lagna_idx: int) -> str:
    sign_idx = (lagna_idx + house_num - 1) % 12
    return SIGN_LORDS[sign_idx]


# ─── DETECTION 1: VIPARITA RAJ YOGA STACKING ────────────────────────────────

def detect_viparita_stack(chart_data: dict) -> dict:
    """
    Counts Viparita Raj Yogas. Stacking is the key signal.
    Triple Viparita = extreme rise-through-adversity architecture.

    Viparita forms when lords of dushthana houses (6, 8, 12) are placed
    in other dushthana houses. Can also be read from chart_data.yogas.
    """
    yogas = chart_data.get("yogas", [])

    # First check pre-computed yogas
    viparitas = [
        y for y in yogas
        if isinstance(y, dict) and "viparita" in y.get("name", "").lower()
    ]

    # If no pre-computed viparitas, detect algorithmically
    if not viparitas:
        planets = chart_data.get("planets", {})
        lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)
        dushthana = {6, 8, 12}
        detected = []

        for house in (6, 8, 12):
            lord = _get_house_lord(house, lagna_idx)
            lord_house = _get_planet_house(lord, planets, lagna_idx)
            if lord_house in dushthana and lord_house != house:
                detected.append({
                    "name": f"Viparita ({house}L in {lord_house}H)",
                    "lord": lord,
                    "from_house": house,
                    "to_house": lord_house,
                })
        viparitas = detected

    count = len(viparitas)

    if count >= 3:
        return {
            "tier": "extreme",
            "weight": 6.0,
            "count": count,
            "names": [v.get("name", "Viparita") for v in viparitas],
            "implication": (
                "Triple Viparita Raj Yoga. Classical texts reserved this for extraordinary "
                "rise-through-adversity patterns. Modern meaning: chart architecture "
                "literally encodes 'the worse it looks, the bigger the outcome.' "
                "Crisis becomes the engine, not the obstacle. Musk-tier founder signature."
            ),
            "modern_context": (
                "Found in disruptive unicorn founders whose biography "
                "shows multiple near-failures transforming into breakthroughs."
            ),
        }
    elif count == 2:
        return {
            "tier": "strong",
            "weight": 4.0,
            "count": 2,
            "names": [v.get("name", "Viparita") for v in viparitas],
            "implication": (
                "Double Viparita Raj Yoga. Strong rise-through-adversity pattern. "
                "Crises tend to convert into growth moments if persistence holds."
            ),
        }
    elif count == 1:
        return {
            "tier": "moderate",
            "weight": 2.0,
            "count": 1,
            "names": [v.get("name", "Viparita") for v in viparitas],
            "implication": (
                "One Viparita Raj Yoga — moderate protection against one "
                "specific crisis domain."
            ),
        }

    return {"tier": "none", "weight": 0, "count": 0}


# ─── DETECTION 2: IDENTITY-OVERWHELM ANTI-PATTERN ───────────────────────────

def detect_identity_overwhelm(chart_data: dict) -> Optional[dict]:
    """
    H1 stellium (3+ non-shadow planets) WITHOUT compensating output-engine
    in H6/H10/H11 = CHARISMA archetype.

    Not a failure pattern — but requires specific business-fit (advisory,
    services, relationship-brokerage) not production/scaling businesses.
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # Count non-shadow planets in H1
    h1_planets = [
        p for p, d in planets.items()
        if isinstance(d, dict)
        and _get_planet_house(p, planets, lagna_idx) == 1
        and p not in ("Rahu", "Ketu")
    ]
    h1_count = len(h1_planets)

    if h1_count < 3:
        return None  # Not enough concentration to trigger

    # Check output-engine activation
    h6_productive = [
        p for p in ("Saturn", "Mars", "Rahu")
        if _get_planet_house(p, planets, lagna_idx) == 6
    ]
    h10_productive = [
        p for p in ("Saturn", "Mars", "Rahu", "Sun")
        if _get_planet_house(p, planets, lagna_idx) == 10
    ]
    h11_productive = [
        p for p, d in planets.items()
        if isinstance(d, dict)
        and _get_planet_house(p, planets, lagna_idx) == 11
        and p != "Ketu"
    ]

    output_activation_count = len(h6_productive) + len(h10_productive) + len(h11_productive)

    if output_activation_count >= 2:
        # Has H1 stellium AND output engine = strong chart, not CHARISMA trap
        return None

    return {
        "flag": "identity_overwhelm",
        "severity": "high" if h1_count >= 4 else "moderate",
        "h1_planets": h1_planets,
        "h1_count": h1_count,
        "output_activation": {
            "h6": h6_productive,
            "h10": h10_productive,
            "h11": h11_productive,
            "total": output_activation_count,
        },
        "implication": (
            f"{h1_count}-planet H1 stellium without compensating output-engine in H6/H10/H11. "
            f"Classical reading scores this as extraordinary Raj Yoga. Modern context reveals "
            f"CHARISMA archetype: presence-dominant, relationship-leveraged, production-light. "
            f"Wealth vehicle MUST match this architecture (advisory, consulting, services, "
            f"brokerage, personal-brand). Production/manufacturing/scaling-ops businesses "
            f"will dissolve capital despite apparent classical-chart strength."
        ),
        "favored_vehicles": [
            "consulting and advisory services",
            "personal-brand businesses",
            "relationship-brokerage (M&A, real-estate commission, matchmaking)",
            "services-sales through personal presence",
            "media/speaking/teaching platforms",
        ],
        "disfavored_vehicles": [
            "physical-operations manufacturing",
            "capital-heavy infrastructure",
            "operational platforms requiring uptime/scale",
            "asset-heavy businesses",
            "pure-tech product build (CTO roles)",
        ],
    }


# ─── DETECTION 3: MOON MD H2 EMOTIONAL-WEALTH-PRESSURE TRAP ─────────────────

INTENSE_NAKSHATRAS = {"Jyeshtha", "Ashlesha", "Mula", "Ardra", "Vishakha"}


def check_moon_md_h2_pressure(chart_data: dict, current_md: Optional[str] = None) -> Optional[dict]:
    """
    Moon MD activating H2 (wealth house) creates emotional-wealth-pressure.
    Combined with intense nakshatras, pushes toward ambitious capital-heavy
    pivots that oppose chart-fit.
    """
    if current_md != "Moon":
        return None

    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)
    moon = planets.get("Moon", {})
    if not isinstance(moon, dict):
        return None

    moon_house = _get_planet_house("Moon", planets, lagna_idx)
    moon_sign = moon.get("sign", "")
    moon_nakshatra = moon.get("nakshatra", "")

    # Moon activates H2 directly or aspects H2 from H8
    activates_h2 = moon_house == 2
    aspects_h2 = moon_house == 8

    in_intense_nakshatra = moon_nakshatra in INTENSE_NAKSHATRAS

    if activates_h2 or (aspects_h2 and in_intense_nakshatra):
        severity = "high" if in_intense_nakshatra else "moderate"

        return {
            "flag": "moon_md_h2_pressure",
            "severity": severity,
            "moon_placement": f"{moon_sign} H{moon_house} {moon_nakshatra}",
            "implication": (
                f"Moon MD activates H2 (wealth house) with Moon in "
                f"{'intense ' + moon_nakshatra if in_intense_nakshatra else moon_nakshatra} "
                f"nakshatra. Classical reading: wealth-focus period. Modern context: "
                f"emotional pressure around status, family-wealth, legacy. Risk: pivoting "
                f"from working business to larger/more-visible venture driven by emotional "
                f"wealth-anxiety rather than chart-fit analysis. "
                f"Typical trap: adding capital-intensive 'status business' on top of or "
                f"instead of working chart-fit business."
            ),
            "guidance": (
                "Before any major pivot during this dasha: verify new venture matches "
                "chart-fit architecture. Check D-2 hora consistency. Do NOT trust "
                "emotional conviction during this period — decision-quality is impaired "
                "by wealth-anxiety."
            ),
        }

    return None


# ─── DETECTION 4: D-2 HORA BUSINESS-TYPE MISMATCH ───────────────────────────

HORA_BUSINESS_AFFINITY = {
    # SUN HORA (self-made/operational businesses)
    "PHYSICAL_OPS": "sun",
    "MANUFACTURING": "sun",
    "LOGISTICS_PLATFORM": "sun",
    "PRODUCTION_BUSINESS": "sun",
    "INFRASTRUCTURE": "sun",
    "BIOTECH": "sun",

    # MOON HORA (relationship/public/inherited businesses)
    "ADVISORY": "moon",
    "CONSULTING": "moon",
    "SERVICES_PROFESSIONAL": "moon",
    "BROKERING": "moon",
    "MATCHMAKING": "moon",
    "INHERITED_BUSINESS": "moon",
    "REAL_ESTATE_DEVELOPMENT_INHERITED": "moon",
    "PUBLIC_FACING_BRAND": "moon",
    "MEDIA_PERSONA": "moon",
    "INSTITUTIONAL_AUTHORITY": "moon",
    "CREATIVE": "moon",

    # MIXED / CONTEXT-DEPENDENT
    "PLATFORM": "mixed",
    "SERVICE_MASSES_AUTOMATION": "mixed",
    "KNOWLEDGE_PLATFORM": "mixed",
    "FINANCIAL_TRADING": "mixed",
    "SPECULATION": "mixed",
    "REAL_ESTATE": "mixed",
    "RETAIL": "mixed",
}


def check_d2_hora_business_mismatch(
    chart_data: dict, business_category: str
) -> Optional[dict]:
    """
    Warn when business category opposes D-2 hora dominance.
    Sun-hora dominant = self-made/operational wealth.
    Moon-hora dominant = relationship/advisory/inherited wealth.
    """
    d2 = chart_data.get("divisional_charts", {}).get("d2", {})
    if not isinstance(d2, dict):
        return None

    sun_hora = d2.get("sun_hora_planets", [])
    moon_hora = d2.get("moon_hora_planets", [])

    sun_count = len(sun_hora)
    moon_count = len(moon_hora)

    if abs(sun_count - moon_count) < 2:
        return None  # Balanced — either channel works

    if sun_count > moon_count:
        dominant = "sun"
        dominant_channel = "self-made/operational/production"
    else:
        dominant = "moon"
        dominant_channel = "relationship/inherited/public-facing"

    business_hora = HORA_BUSINESS_AFFINITY.get(business_category)

    if business_hora and business_hora != "mixed" and business_hora != dominant:
        return {
            "flag": "hora_business_mismatch",
            "severity": "high",
            "d2_dominant": dominant,
            "d2_channel": dominant_channel,
            "d2_sun_count": sun_count,
            "d2_moon_count": moon_count,
            "business_category": business_category,
            "business_hora_type": business_hora,
            "implication": (
                f"Your D-2 Hora shows {dominant_channel} wealth type "
                f"({dominant}-hora dominant: {sun_count} vs {moon_count}). "
                f"The {business_category} category is a {business_hora}-hora business. "
                f"Chart architecture opposes this venture type. Historical pattern: people "
                f"with your hora dominance succeed in {dominant_channel} vehicles and "
                f"lose capital in {business_hora}-hora ventures."
            ),
            "recommendation": (
                f"Consider pivoting the venture concept toward {dominant_channel} expression: "
                f"e.g., instead of operating the business yourself, advise/broker/consult to "
                f"that industry. Play the chart-fit channel on a larger field."
            ),
        }

    return None
