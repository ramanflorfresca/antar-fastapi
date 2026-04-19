"""
Business-Fit Signature v1.0 — Surface B: Life Arc
====================================================
Classifies which business categories structurally align with a chart.
Uses D-1, D-2, D-4, D-7, D-9, D-10, D-60 cross-analysis.

Categories scored:
  1. PLATFORM — SaaS, AI, media, data, educational products
  2. PHYSICAL_OPS — restaurants, hospitality, manufacturing, logistics
  3. REAL_ESTATE — property development, holdings, land
  4. ADVISORY — consulting, legal, financial, medicine, teaching
  5. BROKERING — commissions, matchmaking, M&A, sales
  6. CREATIVE — arts, writing, film, design, brand/persona
  7. SPECULATION — trading, crypto, VC, hedge funds

Outputs ranked category fit with classical reasoning chains.
NO probability percentages. NO dollar amounts.

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any


# ─── METADATA ────────────────────────────────────────────────────────────────

SIGNATURE_METADATA = {
    "name": "business_fit",
    "version": "2.0",
    "event_label": "Business & career structural alignment",
    "confidence": "MEDIUM",
    "positive_sample_size": 2,      # Raman + Andres retrodiction
    "positive_rate": None,
    "false_positive_rate": None,
    "last_validated": "2026-04-19",
    "enabled_in_library": False,    # Enable after N=15+ validation
    "sources": [
        "Retrodiction: Raman (Capricorn rising), Andres (Cancer rising)",
        "Classical Vedic divisional analysis (D-1/D-2/D-4/D-7/D-9/D-10/D-60)",
    ],
    "notes": "v2: Added yogakaraka detection, Mahapurusha stacking, focus-split risk, "
             "SERVICE_MASSES_AUTOMATION and INSTITUTIONAL_AUTHORITY categories. "
             "9 total categories scored. Supersedes wealth_jump business-type analysis.",
}


# ─── DIGNITY TABLES ──────────────────────────────────────────────────────────

SIGN_LORDS = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon",
    4: "Sun", 5: "Mercury", 6: "Venus", 7: "Mars",
    8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter",
}

EXALTATION = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7,
}

DEBILITATION = {
    "Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11,
    "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1,
}

OWN_SIGNS = {
    "Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
    "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
    "Rahu": [10], "Ketu": [7],
}

# Business category labels
CATEGORY_PLATFORM = "PLATFORM"
CATEGORY_PHYSICAL_OPS = "PHYSICAL_OPS"
CATEGORY_REAL_ESTATE = "REAL_ESTATE"
CATEGORY_ADVISORY = "ADVISORY"
CATEGORY_BROKERING = "BROKERING"
CATEGORY_CREATIVE = "CREATIVE"
CATEGORY_SPECULATION = "SPECULATION"
CATEGORY_SERVICE_MASSES = "SERVICE_MASSES_AUTOMATION"
CATEGORY_INSTITUTIONAL = "INSTITUTIONAL_AUTHORITY"

CATEGORY_VEHICLES = {
    CATEGORY_PLATFORM: "AI platforms, SaaS, knowledge products, media platforms, data businesses, educational products",
    CATEGORY_PHYSICAL_OPS: "Restaurants, hospitality, food processing, manufacturing, logistics, retail operations",
    CATEGORY_REAL_ESTATE: "Property development, real estate holdings, land deals, REITs, construction",
    CATEGORY_ADVISORY: "Consulting, legal advisory, financial planning, medicine, teaching, professional services",
    CATEGORY_BROKERING: "Deal-making, M&A advisory, real estate brokerage, partnerships, marketplace, sales",
    CATEGORY_CREATIVE: "Writing, music, film, design, brand/persona businesses, entertainment, art",
    CATEGORY_SPECULATION: "Trading, crypto, VC investing, hedge funds, derivatives, speculative finance",
    CATEGORY_SERVICE_MASSES: "Operational automation, labor augmentation, MSME services, healthcare, debt/dispute resolution, outsourcing, care work platforms",
    CATEGORY_INSTITUTIONAL: "Legal practice at scale, financial institutions, academic authority, regulatory/government roles, large consulting firms, multi-generational family business leadership",
}

# ─── YOGAKARAKA BY LAGNA ─────────────────────────────────────────────────────
# Planet that simultaneously rules a kendra AND a trikona from lagna.
# When well-placed, this single planet produces Raj Yoga.

YOGAKARAKA_BY_LAGNA = {
    0:  None,       # Aries — no single-planet yogakaraka
    1:  "Saturn",   # Taurus — Saturn rules 9H (Capricorn) + 10H (Aquarius)
    2:  None,       # Gemini
    3:  "Mars",     # Cancer — Mars rules 5H (Scorpio) + 10H (Aries)
    4:  "Mars",     # Leo — Mars rules 4H (Scorpio) + 9H (Aries)
    5:  None,       # Virgo
    6:  "Saturn",   # Libra — Saturn rules 4H (Capricorn) + 5H (Aquarius)
    7:  None,       # Scorpio
    8:  None,       # Sagittarius
    9:  "Venus",    # Capricorn — Venus rules 5H (Taurus) + 10H (Libra)
    10: "Venus",    # Aquarius — Venus rules 4H (Taurus) + 9H (Libra)
    11: None,       # Pisces
}

# Secondary yogakaraka-equivalents (double-lordship producing major yoga)
SECONDARY_YOGAKARAKA = {
    9: ["Venus", "Saturn"],   # Capricorn — Saturn (1H+2H) also major yoga-producer
    3: ["Mars"],              # Cancer — Mars is primary, no secondary
    4: ["Mars"],              # Leo — Mars is primary
}

# House-to-business-theme mapping for yogakaraka placement
YOGAKARAKA_HOUSE_THEMES = {
    1: "self-driven enterprise, personal brand, founder identity",
    2: "wealth accumulation, family-business, speech/communication-based wealth",
    3: "self-effort initiative, short-distance networks, writing/media",
    4: "real estate, property, educational institutions, nurturing services",
    5: "creative ventures, entertainment, children-related, speculation/investing",
    6: "service/labor businesses, operational automation, health/medicine, debt/dispute resolution, serving the underserved/masses",
    7: "partnerships, marriage-based business, public-facing enterprise, dealings-based",
    8: "transformation businesses, research, hidden resources, inheritance/occult",
    9: "philosophy/teaching, publishing, long-distance/international, legal/advisory",
    10: "executive authority, institutional leadership, government-adjacent, large-enterprise",
    11: "platform gains, networks, community-scale businesses, large-follower ventures",
    12: "foreign ventures, spiritual/isolation work, research, behind-scenes roles",
}


# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────

def _get_house_lord(house_num: int, lagna_sign_idx: int) -> str:
    """Get the lord of a house (1-indexed) given lagna sign index."""
    sign_idx = (lagna_sign_idx + house_num - 1) % 12
    return SIGN_LORDS[sign_idx]


def _house_from_sign(planet_sign_idx: int, lagna_sign_idx: int) -> int:
    """Calculate house number (1-12) from planet sign and lagna sign."""
    return (planet_sign_idx - lagna_sign_idx + 12) % 12 + 1


def _is_exalted(planet_name: str, sign_idx: int) -> bool:
    """Check if planet is exalted."""
    return sign_idx == EXALTATION.get(planet_name, -99)


def _is_debilitated(planet_name: str, sign_idx: int) -> bool:
    """Check if planet is debilitated."""
    return sign_idx == DEBILITATION.get(planet_name, -99)


def _is_own_sign(planet_name: str, sign_idx: int) -> bool:
    """Check if planet is in own sign."""
    return sign_idx in OWN_SIGNS.get(planet_name, [])


def _is_dignified(planet_name: str, sign_idx: int) -> bool:
    """Check if planet is exalted or in own sign."""
    return _is_exalted(planet_name, sign_idx) or _is_own_sign(planet_name, sign_idx)


def _is_combust(planet_name: str, planets: dict) -> bool:
    """
    Check if planet is combust (too close to Sun).
    Simplified: within same sign as Sun and within ~8 degrees.
    """
    if planet_name in ("Sun", "Rahu", "Ketu"):
        return False
    sun = planets.get("Sun", {})
    planet = planets.get(planet_name, {})
    if not sun or not planet:
        return False
    sun_lon = sun.get("longitude", -999)
    planet_lon = planet.get("longitude", -998)
    if sun_lon < 0 or planet_lon < 0:
        return False
    diff = abs(sun_lon - planet_lon)
    if diff > 180:
        diff = 360 - diff
    # Combustion thresholds vary by planet; using general ~8 degrees
    return diff < 8.0


def _get_planet_house(planet_name: str, planets: dict, lagna_idx: int) -> Optional[int]:
    """Get house number for a planet. Returns None if planet data missing."""
    pdata = planets.get(planet_name, {})
    if not pdata:
        return None
    # Prefer pre-computed house if available
    h = pdata.get("house")
    if h is not None:
        try:
            return int(h)
        except (TypeError, ValueError):
            pass
    # Fall back to computation from sign_index
    sign_idx = pdata.get("sign_index", -1)
    if sign_idx < 0:
        return None
    return _house_from_sign(sign_idx, lagna_idx)


def _get_planet_sign(planet_name: str, planets: dict) -> Optional[int]:
    """Get sign index for a planet. Returns None if data missing."""
    pdata = planets.get(planet_name, {})
    if not pdata:
        return None
    si = pdata.get("sign_index", -1)
    return si if si >= 0 else None


def _rahu_saturn_conjunct_on_lord(planets: dict, lord_name: str) -> bool:
    """Check if Rahu and Saturn are in same sign as a given planet."""
    lord_data = planets.get(lord_name, {})
    rahu_data = planets.get("Rahu", {})
    saturn_data = planets.get("Saturn", {})
    if not lord_data or not rahu_data or not saturn_data:
        return False
    lord_sign = lord_data.get("sign_index", -1)
    rahu_sign = rahu_data.get("sign_index", -2)
    saturn_sign = saturn_data.get("sign_index", -3)
    return rahu_sign == lord_sign and saturn_sign == lord_sign


def _get_d_chart_planets(chart_data: dict, d_key: str) -> dict:
    """Safely get planet data from a divisional chart."""
    div = chart_data.get("divisional_charts", {})
    d_chart = div.get(d_key, {})
    if not isinstance(d_chart, dict):
        return {}
    return d_chart.get("planets", {})


def _get_d_chart(chart_data: dict, d_key: str) -> dict:
    """Safely get a divisional chart dict."""
    div = chart_data.get("divisional_charts", {})
    d_chart = div.get(d_key, {})
    return d_chart if isinstance(d_chart, dict) else {}


def _count_planets_in_houses(planets: dict, lagna_idx: int, target_houses: set) -> int:
    """Count how many planets are placed in any of the target houses."""
    count = 0
    for p_name, pdata in planets.items():
        if not isinstance(pdata, dict):
            continue
        sign_idx = pdata.get("sign_index", -1)
        if sign_idx < 0:
            continue
        h = _house_from_sign(sign_idx, lagna_idx)
        if h in target_houses:
            count += 1
    return count


def _planets_in_house(planets: dict, lagna_idx: int, house_num: int) -> List[str]:
    """Return list of planet names placed in a specific house."""
    result = []
    for p_name, pdata in planets.items():
        if not isinstance(pdata, dict):
            continue
        sign_idx = pdata.get("sign_index", -1)
        if sign_idx < 0:
            continue
        h = _house_from_sign(sign_idx, lagna_idx)
        if h == house_num:
            result.append(p_name)
    return result


# ─── V2 DETECTIONS ───────────────────────────────────────────────────────────

def detect_yogakaraka_activation(chart_data: dict) -> Optional[List[dict]]:
    """
    Detect whether the chart's yogakaraka planet is active and well-placed.
    Yogakaraka in its house of placement determines the primary business theme.

    Returns list of activation dicts, or None if no yogakaraka for this lagna.
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    primary_yk = YOGAKARAKA_BY_LAGNA.get(lagna_idx)
    secondary_yks = SECONDARY_YOGAKARAKA.get(lagna_idx, [])

    all_yks = []
    if primary_yk:
        all_yks.append((primary_yk, "primary"))
    for yk in secondary_yks:
        if yk != primary_yk:
            all_yks.append((yk, "secondary"))

    if not all_yks:
        return None

    activations = []
    for yk_planet, yk_type in all_yks:
        pdata = planets.get(yk_planet, {})
        if not pdata:
            continue

        yk_sign = _get_planet_sign(yk_planet, planets)
        yk_house = _get_planet_house(yk_planet, planets, lagna_idx)
        if yk_house is None:
            continue

        is_own_or_exalted = yk_sign is not None and _is_dignified(yk_planet, yk_sign)
        is_in_kendra_trikona = yk_house in (1, 4, 5, 7, 9, 10)
        is_in_dushthana = yk_house in (6, 8, 12)

        # Strength classification
        if is_own_or_exalted and is_in_kendra_trikona:
            strength = "peak"
            weight = 4.0
        elif is_in_kendra_trikona:
            strength = "strong"
            weight = 3.0
        elif is_in_dushthana:
            # Dushthana placement is "latent" but H6 is special for service businesses
            strength = "latent"
            weight = 1.5 if yk_house == 6 else 1.0
        else:
            strength = "moderate"
            weight = 2.0

        activations.append({
            "planet": yk_planet,
            "type": yk_type,
            "house": yk_house,
            "sign_dignified": is_own_or_exalted,
            "strength": strength,
            "business_theme": YOGAKARAKA_HOUSE_THEMES.get(yk_house, ""),
            "weight": weight,
        })

    return activations if activations else None


def detect_mahapurusha_stack(chart_data: dict) -> dict:
    """
    Count Mahapurusha yogas (planet exalted or own sign in kendra).
    Checks: Saturn (Sasa), Jupiter (Hamsa), Mercury (Bhadra),
            Venus (Malavya), Mars (Ruchaka).

    Single = notable success capacity. Stacked (2+) = rare institutional-scale.

    Uses chart_data.yogas if available, else computes from planets.
    """
    # Try pre-computed yogas first
    yogas = chart_data.get("yogas", [])
    if yogas:
        mahapurusha = [
            y for y in yogas
            if isinstance(y, dict)
            and y.get("category") == "mahapurusha"
            and y.get("strength") in ("strong", "moderate")
        ]
        if mahapurusha:
            count = len(mahapurusha)
            names = [y.get("name", "") for y in mahapurusha]
            if count >= 2:
                return {
                    "count": count,
                    "weight": 6.0,
                    "tier": "stacked",
                    "names": names,
                    "note": (
                        f"{count} Mahapurusha yogas stacked — rare institutional-scale "
                        "capacity. Classical texts reserve this for founders of "
                        "institutions and major dharmic figures."
                    ),
                }
            else:
                return {
                    "count": 1,
                    "weight": 3.0,
                    "tier": "single",
                    "names": names,
                    "note": f"Mahapurusha yoga ({names[0]}) — notable success capacity in this domain",
                }

    # Fall back: compute from planets
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    mp_names_map = {
        "Saturn": "Sasa",
        "Jupiter": "Hamsa",
        "Mercury": "Bhadra",
        "Venus": "Malavya",
        "Mars": "Ruchaka",
    }
    found = []
    for p_name, yoga_name in mp_names_map.items():
        pdata = planets.get(p_name, {})
        if not pdata:
            continue
        p_sign = pdata.get("sign_index", -1)
        if p_sign < 0:
            continue
        if not _is_dignified(p_name, p_sign):
            continue
        p_house = _get_planet_house(p_name, planets, lagna_idx)
        if p_house in (1, 4, 7, 10):
            found.append(yoga_name)

    count = len(found)
    if count == 0:
        return {"count": 0, "weight": 0, "tier": "none", "names": [], "note": ""}
    elif count == 1:
        return {
            "count": 1,
            "weight": 3.0,
            "tier": "single",
            "names": found,
            "note": f"Mahapurusha yoga ({found[0]}) — notable success capacity",
        }
    else:
        return {
            "count": count,
            "weight": 6.0,
            "tier": "stacked",
            "names": found,
            "note": (
                f"{count} Mahapurusha yogas stacked ({', '.join(found)}) — "
                "rare institutional-scale capacity"
            ),
        }


def detect_focus_split_risk(chart_data: dict) -> Optional[dict]:
    """
    Charts with Rahu in kama houses (3/7/11) + multi-planet 11H stellium
    are prone to running multiple ventures simultaneously.
    During Rahu MD/AD, this pattern amplifies.

    Returns risk assessment dict or None if no risk detected.
    """
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    rahu_house = _get_planet_house("Rahu", planets, lagna_idx)

    # Count planets in 11H
    h11_all = _planets_in_house(planets, lagna_idx, 11)
    h11_count = len(h11_all)

    risk_factors = []
    severity = "low"

    if rahu_house in (3, 7, 11):
        risk_factors.append(f"Rahu in H{rahu_house} (kama house — desire-amplifier)")
        severity = "moderate"

    if h11_count >= 3:
        risk_factors.append(f"{h11_count}-planet stellium in 11H ({', '.join(h11_all)})")
        severity = "high" if severity == "moderate" else "moderate"

    if rahu_house == 11 and h11_count >= 2:
        risk_factors.append("Rahu joining 11H stellium = amplified gains-seeking")
        severity = "high"

    if not risk_factors:
        return None

    return {
        "flag": "focus_split_risk",
        "severity": severity,
        "factors": risk_factors,
        "implication": (
            "Chart architecture attracts multiple business opportunities simultaneously. "
            "This is a capability — AND a risk. Without conscious focus, ventures compete "
            "for attention and none compound fully."
        ),
        "amplified_during": "Rahu MD, Rahu AD, Rahu PD, Rahu transits to 11H",
        "guidance": (
            "Designate ONE primary vehicle, especially during Rahu MD/AD. Secondary "
            "ventures must be genuinely complementary (feed into primary) or delegated "
            "(partner or team runs them)."
        ),
    }


# ─── CATEGORY SCORERS ────────────────────────────────────────────────────────

def score_platform_fit(chart_data: dict) -> dict:
    """
    PLATFORM / KNOWLEDGE PRODUCT — SaaS, AI, media, educational products
    Uses D-1, D-2, D-9, D-10 cross-analysis.
    """
    score = 0.0
    reasons = []
    warnings = []

    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # ── D-1: Jupiter in wealth houses (2, 5, 9, 11) — wisdom-wealth ──
    jup_house = _get_planet_house("Jupiter", planets, lagna_idx)
    jup_sign = _get_planet_sign("Jupiter", planets)
    if jup_house in (2, 5, 9, 11):
        score += 2.5
        reasons.append(f"Jupiter in {jup_house}H — wisdom-product wealth alignment")
    elif jup_house in (6, 8, 12):
        if jup_sign is not None and not _is_dignified("Jupiter", jup_sign):
            score -= 1.5
            warnings.append(f"Jupiter in dushthana H{jup_house} without dignity — knowledge business faces obstacles")

    # ── D-1: Mercury in kendra/trikona — communication scalability ──
    mer_house = _get_planet_house("Mercury", planets, lagna_idx)
    mer_sign = _get_planet_sign("Mercury", planets)
    if mer_house in (1, 4, 5, 7, 9, 10):
        score += 2.0
        reasons.append(f"Mercury in {mer_house}H — communication scalability")
    if mer_sign is not None and _is_debilitated("Mercury", mer_sign):
        score -= 2.0
        warnings.append("Mercury debilitated — platform communication challenges")
    if _is_combust("Mercury", planets):
        score -= 1.0
        warnings.append("Mercury combust — communication clarity tested by ego")

    # ── D-1: Rahu in 11H or 3H — unconventional platform scale ──
    rahu_house = _get_planet_house("Rahu", planets, lagna_idx)
    rahu_sign = _get_planet_sign("Rahu", planets)
    if rahu_house in (3, 11):
        score += 2.5
        reasons.append(f"Rahu in {rahu_house}H — unconventional platform scale")
        # Rahu in Scorpio (sign 7) in 11H = volatile gains
        if rahu_sign == 7 and rahu_house == 11:
            reasons.append("Rahu in 11H Scorpio — gains through unconventional networks but volatility in accumulation")

    # ── D-2 Hora: Moon hora dominance (venture wealth) ──
    d2 = _get_d_chart(chart_data, "d2")
    moon_hora_planets = d2.get("moon_hora_planets", [])
    sun_hora_planets = d2.get("sun_hora_planets", [])
    if len(moon_hora_planets) >= 5:
        score += 2.0
        reasons.append(f"D-2: {len(moon_hora_planets)} planets in Moon hora — venture-wealth type")
    elif len(moon_hora_planets) >= 4:
        score += 1.0
        reasons.append(f"D-2: {len(moon_hora_planets)} planets in Moon hora — moderate venture-wealth")

    # ── D-9 Navamsa: Jupiter placement (soul-level alignment) ──
    d9_planets = _get_d_chart_planets(chart_data, "d9")
    d9_jup = d9_planets.get("Jupiter", {})
    d9_jup_sign = d9_jup.get("sign_index")
    if d9_jup_sign is not None and _is_dignified("Jupiter", d9_jup_sign):
        score += 1.5
        reasons.append("D-9 Jupiter dignified — soul-level alignment with wisdom business")

    # ── D-10 Dashamsa: Mercury/Jupiter in career chart ──
    d10_planets = _get_d_chart_planets(chart_data, "d10")
    d10_mer = d10_planets.get("Mercury", {})
    d10_mer_sign = d10_mer.get("sign_index")
    d10_mer_house = d10_mer.get("house")
    if d10_mer_house is not None:
        try:
            d10_mer_h = int(d10_mer_house)
            if d10_mer_h in (1, 4, 5, 7, 9, 10, 11):
                score += 1.5
                reasons.append(f"D-10 Mercury in H{d10_mer_h} — career platform fit")
        except (TypeError, ValueError):
            pass
    if d10_mer_sign is not None and _is_debilitated("Mercury", d10_mer_sign):
        score -= 1.5
        warnings.append("D-10 Mercury afflicted — career-level platform challenges")

    d10_jup = d10_planets.get("Jupiter", {})
    d10_jup_house = d10_jup.get("house")
    if d10_jup_house is not None:
        try:
            d10_jup_h = int(d10_jup_house)
            if d10_jup_h in (1, 4, 5, 7, 9, 10):
                score += 1.0
                reasons.append(f"D-10 Jupiter in H{d10_jup_h} kendra/trikona — career wisdom authority")
        except (TypeError, ValueError):
            pass

    return {
        "category": CATEGORY_PLATFORM,
        "score": round(score, 1),
        "reasoning": reasons,
        "warnings": warnings,
        "vehicles": CATEGORY_VEHICLES[CATEGORY_PLATFORM],
    }


def score_physical_ops_fit(chart_data: dict) -> dict:
    """
    PHYSICAL OPERATIONS / HOSPITALITY / FOOD
    Restaurants, hotels, processing, manufacturing, logistics.
    Uses D-1, D-2, D-7, D-10, D-60.
    """
    score = 0.0
    reasons = []
    warnings = []

    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # ── Ketu in 2H = MAJOR disfavor for food/consumption businesses ──
    ketu_house = _get_planet_house("Ketu", planets, lagna_idx)
    if ketu_house == 2:
        score -= 4.0
        warnings.append("Ketu in 2H — food/consumption businesses structurally dissolve")
    elif ketu_house == 6:
        score -= 2.0
        warnings.append("Ketu in 6H — service/operations businesses face karmic dissolution")
    elif ketu_house == 10:
        score -= 2.5
        warnings.append("Ketu in 10H — career in physical operations faces dissolution")

    # ── Rahu in 2H = erratic cash flow in consumption businesses ──
    rahu_house = _get_planet_house("Rahu", planets, lagna_idx)
    rahu_sign = _get_planet_sign("Rahu", planets)
    if rahu_house == 2:
        score -= 3.0
        warnings.append("Rahu in 2H — erratic consumption-business cash flow")

    # ── Rahu in 11H Scorpio = volatile gains (not steady accumulation) ──
    if rahu_house == 11 and rahu_sign == 7:  # Scorpio
        score -= 2.5
        warnings.append("Rahu in 11H Scorpio — gains are volatile, not steady; physical ops need steady cash")

    # ── Mars strength for execution capability ──
    mars_house = _get_planet_house("Mars", planets, lagna_idx)
    mars_sign = _get_planet_sign("Mars", planets)
    if mars_sign is not None and mars_house is not None:
        mars_dignified = _is_dignified("Mars", mars_sign)
        if mars_dignified and mars_house in (1, 3, 6, 10, 11):
            score += 2.0
            reasons.append(f"Mars dignified in H{mars_house} — execution capability")
        elif mars_house in (6, 8, 12) and not mars_dignified:
            score -= 2.0
            warnings.append(f"Mars in dushthana H{mars_house} without dignity — execution fragility")

    # ── Venus in 4H or 2H — hospitality/comfort alignment ──
    ven_house = _get_planet_house("Venus", planets, lagna_idx)
    ven_sign = _get_planet_sign("Venus", planets)
    if ven_house in (2, 4):
        score += 1.5
        reasons.append(f"Venus in H{ven_house} — hospitality/comfort product alignment")
    if ven_sign is not None and _is_combust("Venus", planets):
        score -= 1.0
        warnings.append("Venus combust — hospitality charm overshadowed")
    if ven_sign is not None and _is_debilitated("Venus", ven_sign):
        score -= 1.5
        warnings.append("Venus debilitated — hospitality/comfort businesses structurally weak")

    # ── Moon position (public-facing operations) ──
    moon_house = _get_planet_house("Moon", planets, lagna_idx)
    moon_sign = _get_planet_sign("Moon", planets)
    if moon_house in (1, 4, 7, 10):
        score += 1.0
        reasons.append(f"Moon in kendra H{moon_house} — strong public-facing operations potential")
    elif moon_house in (3, 6):
        score -= 0.5
        warnings.append(f"Moon in H{moon_house} — emotional energy in communication/service, not operations")

    # ── D-2 Sun hora dominance (self-effort/physical wealth) ──
    d2 = _get_d_chart(chart_data, "d2")
    sun_hora_planets = d2.get("sun_hora_planets", [])
    if len(sun_hora_planets) >= 5:
        score += 1.5
        reasons.append(f"D-2: {len(sun_hora_planets)} planets in Sun hora — self-effort/physical wealth type")

    # ── D-10: Venus/Mars in 2H or 4H (operations orientation) ──
    d10_planets = _get_d_chart_planets(chart_data, "d10")
    for p in ("Venus", "Mars"):
        pdata = d10_planets.get(p, {})
        ph = pdata.get("house")
        if ph is not None:
            try:
                ph_int = int(ph)
                if ph_int in (2, 4):
                    score += 1.0
                    reasons.append(f"D-10 {p} in H{ph_int} — career operations fit")
            except (TypeError, ValueError):
                pass

    # ── D-7: Creative output capacity (what you "birth" into the world) ──
    d7_planets = _get_d_chart_planets(chart_data, "d7")
    # If D-7 is weakened, creative/physical output is challenged
    d7_jup = d7_planets.get("Jupiter", {})
    d7_ven = d7_planets.get("Venus", {})
    d7_jup_sign = d7_jup.get("sign_index")
    d7_ven_sign = d7_ven.get("sign_index")
    d7_weak = 0
    if d7_jup_sign is not None and _is_debilitated("Jupiter", d7_jup_sign):
        d7_weak += 1
    if d7_ven_sign is not None and _is_debilitated("Venus", d7_ven_sign):
        d7_weak += 1
    if d7_weak >= 2:
        score -= 1.5
        warnings.append("D-7 Jupiter + Venus debilitated — creative/physical output challenged")

    # ── Mercury debilitated = management/logistics communication fails ──
    mer_sign = _get_planet_sign("Mercury", planets)
    if mer_sign is not None and _is_debilitated("Mercury", mer_sign):
        score -= 1.5
        warnings.append("Mercury debilitated — operations management/logistics communication fails")

    # ── D-60: Karmic markers on operational planets (score penalty, not just warning) ──
    d60 = _get_d_chart(chart_data, "d60")
    planet_analysis = d60.get("planet_analysis", {})
    if isinstance(planet_analysis, dict):
        for p in ("Mars", "Venus"):
            pdata = planet_analysis.get(p, {})
            if isinstance(pdata, dict) and pdata.get("is_challenging"):
                karma = pdata.get("karma_name", "challenging")
                score -= 1.5
                warnings.append(
                    f"D-60 {p} has {karma} karma — operational challenges recur karmically"
                )
        # Mercury D-60 as warning only (already penalized above if debilitated)
        mer_d60 = planet_analysis.get("Mercury", {})
        if isinstance(mer_d60, dict) and mer_d60.get("is_challenging"):
            warnings.append(
                f"D-60 Mercury has {mer_d60.get('karma_name', 'challenging')} karma — "
                f"operational challenges recur karmically"
            )

    return {
        "category": CATEGORY_PHYSICAL_OPS,
        "score": round(score, 1),
        "reasoning": reasons,
        "warnings": warnings,
        "vehicles": CATEGORY_VEHICLES[CATEGORY_PHYSICAL_OPS],
    }


def score_real_estate_fit(chart_data: dict) -> dict:
    """
    REAL ESTATE / PROPERTY / LAND
    Development, holdings, REITs, land deals.
    Uses D-1, D-4, Mars/Saturn/Moon analysis.
    """
    score = 0.0
    reasons = []
    warnings = []

    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # ── 4H lord analysis (house of property) ──
    lord_4 = _get_house_lord(4, lagna_idx)
    lord_4_house = _get_planet_house(lord_4, planets, lagna_idx)
    lord_4_sign = _get_planet_sign(lord_4, planets)

    if lord_4_house in (6, 8, 12):
        score -= 3.0
        warnings.append(
            f"4H lord ({lord_4}) in H{lord_4_house} dushthana — "
            f"property ownership structurally drains"
        )
    elif lord_4_house in (1, 4, 7, 10):
        score += 1.5
        reasons.append(f"4H lord ({lord_4}) in kendra H{lord_4_house} — property foundation solid")

    # ── Saturn in 4H ──
    sat_house = _get_planet_house("Saturn", planets, lagna_idx)
    sat_sign = _get_planet_sign("Saturn", planets)
    if sat_house == 4:
        if sat_sign is not None and _is_dignified("Saturn", sat_sign):
            score += 1.0
            reasons.append("Saturn dignified in 4H — disciplined property accumulation")
        else:
            score -= 1.5
            warnings.append("Saturn in 4H without dignity — property stagnation, delays")

    # ── Rahu-Saturn conjunction affecting 4H lord ──
    if _rahu_saturn_conjunct_on_lord(planets, lord_4):
        score -= 3.0
        warnings.append(f"Rahu-Saturn affecting 4H lord ({lord_4}) — property losses likely")

    # ── Rahu in 11H Scorpio = volatile gains (property needs steady accumulation) ──
    rahu_house = _get_planet_house("Rahu", planets, lagna_idx)
    rahu_sign = _get_planet_sign("Rahu", planets)
    if rahu_house == 11 and rahu_sign == 7:  # Scorpio
        score -= 2.0
        warnings.append("Rahu in 11H Scorpio — volatile gains cycle; long-term property accumulation disfavored")

    # ── Mars in 4H dignified = construction/development capability ──
    mars_house = _get_planet_house("Mars", planets, lagna_idx)
    mars_sign = _get_planet_sign("Mars", planets)
    if mars_house == 4 and mars_sign is not None and _is_dignified("Mars", mars_sign):
        score += 2.5
        reasons.append("Mars dignified in 4H — property development capability")
    elif mars_house == 4 and mars_sign is not None and _is_debilitated("Mars", mars_sign):
        score -= 1.5
        warnings.append("Mars debilitated in 4H — construction/property efforts undercut")

    # ── Benefics aspecting 4H (Jupiter/Venus in 4H or aspecting) ──
    jup_house = _get_planet_house("Jupiter", planets, lagna_idx)
    ven_house = _get_planet_house("Venus", planets, lagna_idx)
    if jup_house == 4:
        score += 1.5
        reasons.append("Jupiter in 4H — property blessing, wise acquisitions")
    if ven_house == 4:
        score += 1.0
        reasons.append("Venus in 4H — property through comfort/luxury")

    # ── Moon strong (nurturing stable assets) ──
    moon_house = _get_planet_house("Moon", planets, lagna_idx)
    moon_sign = _get_planet_sign("Moon", planets)
    if moon_sign is not None and _is_dignified("Moon", moon_sign):
        score += 1.0
        reasons.append("Moon dignified — capacity for nurturing stable asset growth")

    # ── D-4 Chaturthamsa (property chart) ──
    d4 = _get_d_chart(chart_data, "d4")
    d4_planets = d4.get("planets", {}) if isinstance(d4, dict) else {}
    for p in ("Jupiter", "Venus"):
        pdata = d4_planets.get(p, {})
        ph = pdata.get("house")
        if ph is not None:
            try:
                ph_int = int(ph)
                if ph_int in (1, 4, 7, 10):
                    score += 1.0
                    reasons.append(f"D-4 {p} in kendra H{ph_int} — property fortune potential")
            except (TypeError, ValueError):
                pass

    # ── Saturn as yogakaraka in service houses (wealth through service not assets) ──
    # For Capricorn/Aquarius lagna, Saturn may be yogakaraka but placed in 6H
    if sat_house == 6 and lagna_idx in (9, 10):
        score -= 1.0
        warnings.append(f"Saturn (yogakaraka) in 6H — wealth comes through service/knowledge, not holding assets")

    return {
        "category": CATEGORY_REAL_ESTATE,
        "score": round(score, 1),
        "reasoning": reasons,
        "warnings": warnings,
        "vehicles": CATEGORY_VEHICLES[CATEGORY_REAL_ESTATE],
    }


def score_advisory_fit(chart_data: dict) -> dict:
    """
    ADVISORY / CONSULTING / PROFESSIONAL SERVICES
    Legal, financial advisory, consulting, medicine, teaching.
    Uses D-1, D-10, D-20.
    """
    score = 0.0
    reasons = []
    warnings = []

    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # ── Jupiter strong and well-placed ──
    jup_house = _get_planet_house("Jupiter", planets, lagna_idx)
    jup_sign = _get_planet_sign("Jupiter", planets)
    if jup_sign is not None and _is_dignified("Jupiter", jup_sign):
        score += 2.5
        reasons.append("Jupiter dignified — wisdom dispensation capability")
    if jup_house in (1, 5, 9, 10):
        score += 2.0
        reasons.append(f"Jupiter in H{jup_house} kendra/trikona — advisory authority")
    elif jup_house in (2, 11):
        score += 1.0
        reasons.append(f"Jupiter in H{jup_house} — wealth through wisdom")
    if _is_combust("Jupiter", planets):
        score -= 1.5
        warnings.append("Jupiter combust — advisory credibility tested by ego dynamics")

    # ── Mercury in communication houses ──
    mer_house = _get_planet_house("Mercury", planets, lagna_idx)
    mer_sign = _get_planet_sign("Mercury", planets)
    if mer_house in (1, 3, 5, 9, 10):
        score += 1.5
        reasons.append(f"Mercury in H{mer_house} — expertise communication")
    # Mercury-Rahu conjunction check
    rahu_sign = _get_planet_sign("Rahu", planets)
    if mer_sign is not None and rahu_sign is not None and mer_sign == rahu_sign:
        if not _is_dignified("Mercury", mer_sign):
            score -= 1.0
            warnings.append("Mercury-Rahu conjunction without Mercury strength — advisory communication may mislead")

    # ── Saturn in 10H well-placed (professional authority) ──
    sat_house = _get_planet_house("Saturn", planets, lagna_idx)
    sat_sign = _get_planet_sign("Saturn", planets)
    if sat_house == 10:
        if sat_sign is not None and _is_dignified("Saturn", sat_sign):
            score += 2.0
            reasons.append("Saturn dignified in 10H — deep professional authority")
        else:
            score += 1.0
            reasons.append("Saturn in 10H — professional discipline (authority builds slowly)")

    # ── 10H lord strength ──
    lord_10 = _get_house_lord(10, lagna_idx)
    lord_10_house = _get_planet_house(lord_10, planets, lagna_idx)
    lord_10_sign = _get_planet_sign(lord_10, planets)
    if lord_10_house in (6, 8, 12) and lord_10_sign is not None and not _is_dignified(lord_10, lord_10_sign):
        score -= 1.5
        warnings.append(f"10H lord ({lord_10}) weak in H{lord_10_house} — professional authority challenged")

    # ── D-10: Jupiter/Mercury in 10H ──
    d10_planets = _get_d_chart_planets(chart_data, "d10")
    d10_h10_benefics = []
    for p in ("Jupiter", "Mercury"):
        pdata = d10_planets.get(p, {})
        ph = pdata.get("house")
        if ph is not None:
            try:
                if int(ph) == 10:
                    d10_h10_benefics.append(p)
            except (TypeError, ValueError):
                pass
    if d10_h10_benefics:
        score += 1.5
        reasons.append(f"D-10: {', '.join(d10_h10_benefics)} in 10H — professional authority confirmed")

    # ── D-10 benefics in kendras ──
    d10_kendra_benefics = 0
    for p in ("Jupiter", "Venus", "Mercury"):
        pdata = d10_planets.get(p, {})
        ph = pdata.get("house")
        if ph is not None:
            try:
                if int(ph) in (1, 4, 7, 10):
                    d10_kendra_benefics += 1
            except (TypeError, ValueError):
                pass
    if d10_kendra_benefics >= 2:
        score += 1.0
        reasons.append(f"D-10: {d10_kendra_benefics} benefics in kendras — career authority reinforced")

    # ── D-20 (spiritual advisory alignment) ──
    d20_planets = _get_d_chart_planets(chart_data, "d20")
    d20_jup = d20_planets.get("Jupiter", {})
    d20_jup_sign = d20_jup.get("sign_index")
    if d20_jup_sign is not None and _is_dignified("Jupiter", d20_jup_sign):
        score += 1.0
        reasons.append("D-20 Jupiter dignified — spiritual/wisdom advisory alignment")

    return {
        "category": CATEGORY_ADVISORY,
        "score": round(score, 1),
        "reasoning": reasons,
        "warnings": warnings,
        "vehicles": CATEGORY_VEHICLES[CATEGORY_ADVISORY],
    }


def score_brokering_fit(chart_data: dict) -> dict:
    """
    BROKERING / COMMISSION / MATCHMAKING
    Deal-making, M&A, partnerships, sales.
    Uses D-1 + archetype analysis.
    """
    score = 0.0
    reasons = []
    warnings = []

    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # ── 11H stellium (gains through networks) ──
    h11_planets = _planets_in_house(planets, lagna_idx, 11)
    if len(h11_planets) >= 3:
        score += 3.0
        reasons.append(f"{len(h11_planets)} planets in 11H ({', '.join(h11_planets)}) — strong gains-through-networks signature")
    elif len(h11_planets) >= 2:
        score += 2.0
        reasons.append(f"{len(h11_planets)} planets in 11H — gains through networks")

    # ── Mercury strength (dealmaking communication) ──
    mer_house = _get_planet_house("Mercury", planets, lagna_idx)
    mer_sign = _get_planet_sign("Mercury", planets)
    if mer_house in (1, 3, 7, 10, 11):
        score += 1.5
        reasons.append(f"Mercury in H{mer_house} — dealmaking communication")
    if mer_sign is not None and _is_debilitated("Mercury", mer_sign):
        score -= 1.5
        warnings.append("Mercury debilitated — dealmaking communication impaired")

    # ── Venus in relationship houses (3, 7, 11) ──
    ven_house = _get_planet_house("Venus", planets, lagna_idx)
    if ven_house in (3, 7, 11):
        score += 1.5
        reasons.append(f"Venus in H{ven_house} — relationship leverage")

    # ── Rahu in 3H or 11H (unconventional networks) ──
    rahu_house = _get_planet_house("Rahu", planets, lagna_idx)
    if rahu_house in (3, 11):
        score += 2.0
        reasons.append(f"Rahu in H{rahu_house} — unconventional network building")

    # ── 7H strength (partnership capacity) ──
    lord_7 = _get_house_lord(7, lagna_idx)
    lord_7_house = _get_planet_house(lord_7, planets, lagna_idx)
    lord_7_sign = _get_planet_sign(lord_7, planets)
    if lord_7_house in (6, 8, 12) and lord_7_sign is not None and not _is_dignified(lord_7, lord_7_sign):
        score -= 1.5
        warnings.append(f"7H lord ({lord_7}) weak in H{lord_7_house} — partnership breakdown risk")

    # ── Ketu in 3H (effort dissolution) ──
    ketu_house = _get_planet_house("Ketu", planets, lagna_idx)
    if ketu_house == 3:
        score -= 1.0
        warnings.append("Ketu in 3H — effort and initiative dissolution in dealmaking")

    # ── Mercury in 6H afflicted ──
    if mer_house == 6 and mer_sign is not None and not _is_dignified("Mercury", mer_sign):
        score -= 1.5
        warnings.append("Mercury in 6H without dignity — deals turn into disputes")

    # ── Jupiter strong (wisdom-based dealmaking / advisory brokering) ──
    jup_house = _get_planet_house("Jupiter", planets, lagna_idx)
    jup_sign = _get_planet_sign("Jupiter", planets)
    if jup_sign is not None and _is_dignified("Jupiter", jup_sign):
        score += 1.5
        reasons.append("Jupiter dignified — wisdom-based dealmaking/advisory brokering")
    if jup_house in (1, 7, 10, 11):
        score += 1.0
        reasons.append(f"Jupiter in H{jup_house} — dealmaking authority")

    # ── Saturn in 11H (network-based gains, structured brokering) ──
    sat_house = _get_planet_house("Saturn", planets, lagna_idx)
    if sat_house == 11:
        score += 1.5
        reasons.append("Saturn in 11H — disciplined network-based gains; structured brokering")

    # ── Archetype check ──
    archetype = chart_data.get("archetype", {})
    if isinstance(archetype, dict):
        arch_name = str(archetype.get("name", "")).upper()
        if "BROKER" in arch_name or "MEDIATOR" in arch_name or "DEALER" in arch_name:
            score += 2.0
            reasons.append(f"Archetype {archetype.get('name', '')} — natural dealmaker")
    elif isinstance(archetype, str):
        if "BROKER" in archetype.upper() or "MEDIATOR" in archetype.upper():
            score += 2.0
            reasons.append(f"Archetype {archetype} — natural dealmaker")

    return {
        "category": CATEGORY_BROKERING,
        "score": round(score, 1),
        "reasoning": reasons,
        "warnings": warnings,
        "vehicles": CATEGORY_VEHICLES[CATEGORY_BROKERING],
    }


def score_creative_fit(chart_data: dict) -> dict:
    """
    CREATIVE / ARTS / ENTERTAINMENT
    Writing, music, film, design, brand/persona businesses.
    Uses D-1, D-7.
    """
    score = 0.0
    reasons = []
    warnings = []

    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # ── Venus strong and well-placed ──
    ven_house = _get_planet_house("Venus", planets, lagna_idx)
    ven_sign = _get_planet_sign("Venus", planets)
    if ven_sign is not None and _is_dignified("Venus", ven_sign):
        score += 2.5
        reasons.append("Venus dignified — strong creative/artistic capacity")
    if ven_house in (1, 2, 4, 5, 7, 10):
        score += 1.5
        reasons.append(f"Venus in H{ven_house} — creative prominence")
    if ven_sign is not None and _is_debilitated("Venus", ven_sign):
        score -= 2.0
        warnings.append("Venus debilitated — creative/artistic expression structurally weak")

    # ── 5H strong (creative house) ──
    h5_planets = _planets_in_house(planets, lagna_idx, 5)
    lord_5 = _get_house_lord(5, lagna_idx)
    lord_5_house = _get_planet_house(lord_5, planets, lagna_idx)
    lord_5_sign = _get_planet_sign(lord_5, planets)
    if len(h5_planets) >= 2:
        score += 2.0
        reasons.append(f"5H occupied by {', '.join(h5_planets)} — creative house activated")
    if lord_5_sign is not None and _is_dignified(lord_5, lord_5_sign):
        score += 1.0
        reasons.append(f"5H lord ({lord_5}) dignified — creative potential strong")

    # ── Moon aspecting or in 5H ──
    moon_house = _get_planet_house("Moon", planets, lagna_idx)
    if moon_house == 5:
        score += 1.5
        reasons.append("Moon in 5H — emotional depth fuels creativity")

    # ── Saturn heavy on 5H without Jupiter aspect ──
    sat_house = _get_planet_house("Saturn", planets, lagna_idx)
    jup_house = _get_planet_house("Jupiter", planets, lagna_idx)
    if sat_house == 5:
        # Check if Jupiter aspects 5H (Jupiter from 1, 9, or 11 aspects 5H)
        jup_aspects_5 = False
        if jup_house is not None:
            # Jupiter aspects houses 5th, 7th, 9th from itself
            jup_aspects = {
                (jup_house + 4) % 12 or 12,
                (jup_house + 6) % 12 or 12,
                (jup_house + 8) % 12 or 12,
            }
            jup_aspects_5 = 5 in jup_aspects
        if not jup_aspects_5:
            score -= 2.0
            warnings.append("Saturn in 5H without Jupiter aspect — creative expression blocked/delayed")

    # ── D-7 Saptamsa (creative progeny) ──
    d7 = _get_d_chart(chart_data, "d7")
    d7_planets = d7.get("planets", {}) if isinstance(d7, dict) else {}
    d7_ven = d7_planets.get("Venus", {})
    d7_ven_sign = d7_ven.get("sign_index")
    if d7_ven_sign is not None and _is_dignified("Venus", d7_ven_sign):
        score += 1.5
        reasons.append("D-7 Venus dignified — creative progeny/output strong")
    elif d7_ven_sign is not None and _is_debilitated("Venus", d7_ven_sign):
        score -= 1.5
        warnings.append("D-7 Venus debilitated — creative output challenged")

    d7_jup = d7_planets.get("Jupiter", {})
    d7_jup_sign = d7_jup.get("sign_index")
    if d7_jup_sign is not None and _is_dignified("Jupiter", d7_jup_sign):
        score += 1.0
        reasons.append("D-7 Jupiter dignified — creative abundance")

    return {
        "category": CATEGORY_CREATIVE,
        "score": round(score, 1),
        "reasoning": reasons,
        "warnings": warnings,
        "vehicles": CATEGORY_VEHICLES[CATEGORY_CREATIVE],
    }


def score_speculation_fit(chart_data: dict) -> dict:
    """
    SPECULATION / TRADING / FINANCIAL MARKETS
    Trading, crypto, VC investing, hedge funds.
    Uses D-1, D-2.
    """
    score = 0.0
    reasons = []
    warnings = []

    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # ── Rahu in 5H or 11H (speculation gains) ──
    rahu_house = _get_planet_house("Rahu", planets, lagna_idx)
    if rahu_house == 5:
        score += 2.5
        reasons.append("Rahu in 5H — speculation/risk-taking amplified")
    elif rahu_house == 11:
        score += 2.0
        reasons.append("Rahu in 11H — gains through unconventional/speculative channels")

    # ── Strong 11H ──
    h11_planets = _planets_in_house(planets, lagna_idx, 11)
    lord_11 = _get_house_lord(11, lagna_idx)
    lord_11_sign = _get_planet_sign(lord_11, planets)
    if len(h11_planets) >= 2:
        score += 1.5
        reasons.append(f"11H with {len(h11_planets)} planets — gains house strong")
    if lord_11_sign is not None and _is_dignified(lord_11, lord_11_sign):
        score += 1.0
        reasons.append(f"11H lord ({lord_11}) dignified — gains potential strong")

    # ── Jupiter-Rahu well-aspected (risk-managed ambition) ──
    jup_house = _get_planet_house("Jupiter", planets, lagna_idx)
    jup_sign = _get_planet_sign("Jupiter", planets)
    rahu_sign = _get_planet_sign("Rahu", planets)
    # If both in kendra/trikona and not conjunct (which can be too chaotic)
    if jup_house in (1, 4, 5, 7, 9, 10) and rahu_house in (3, 5, 11):
        if jup_sign != rahu_sign:  # not conjunct
            score += 1.5
            reasons.append("Jupiter + Rahu in supportive positions — risk-managed ambition")

    # ── Mercury + Mars + Jupiter combo (analysis + execution + wisdom) ──
    mer_house = _get_planet_house("Mercury", planets, lagna_idx)
    mars_house = _get_planet_house("Mars", planets, lagna_idx)
    strong_count = 0
    for p, h in [("Mercury", mer_house), ("Mars", mars_house), ("Jupiter", jup_house)]:
        if h in (1, 4, 5, 7, 9, 10, 11):
            strong_count += 1
    if strong_count >= 3:
        score += 1.5
        reasons.append("Mercury + Mars + Jupiter all well-placed — analysis + execution + wisdom combo")

    # ── Saturn in 5H heavy (blocks speculation gains) ──
    sat_house = _get_planet_house("Saturn", planets, lagna_idx)
    if sat_house == 5:
        score -= 2.5
        warnings.append("Saturn in 5H — speculation gains blocked/heavily delayed")

    # ── Weak 2H (no reserve capital for speculation) ──
    lord_2 = _get_house_lord(2, lagna_idx)
    lord_2_house = _get_planet_house(lord_2, planets, lagna_idx)
    lord_2_sign = _get_planet_sign(lord_2, planets)
    if lord_2_house in (6, 8, 12) and lord_2_sign is not None and not _is_dignified(lord_2, lord_2_sign):
        score -= 1.5
        warnings.append(f"2H lord ({lord_2}) weak in H{lord_2_house} — reserve capital insufficient for speculation")

    # ── D-2: Sun hora dominant = physical wealth type (not speculative) ──
    d2 = _get_d_chart(chart_data, "d2")
    sun_hora_planets = d2.get("sun_hora_planets", [])
    if len(sun_hora_planets) >= 5:
        score -= 1.0
        warnings.append(f"D-2 strong Sun hora ({len(sun_hora_planets)} planets) — wealth is physical/self-effort type, not speculative")

    return {
        "category": CATEGORY_SPECULATION,
        "score": round(score, 1),
        "reasoning": reasons,
        "warnings": warnings,
        "vehicles": CATEGORY_VEHICLES[CATEGORY_SPECULATION],
    }


# ─── V2 CATEGORY SCORERS ─────────────────────────────────────────────────────

def score_service_masses_fit(chart_data: dict) -> dict:
    """
    SERVICE TO MASSES / OPERATIONAL AUTOMATION
    MSME services, labor augmentation, healthcare, debt resolution,
    outsourcing, care work platforms.

    Key marker: yogakaraka in H6 = peak fit.
    Uses D-1, D-10, yogakaraka activation.
    """
    score = 0.0
    reasons = []
    warnings = []

    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # ── Yogakaraka in H6 = peak fit for this category ──
    yk_activations = detect_yogakaraka_activation(chart_data) or []
    for act in yk_activations:
        if act["house"] == 6:
            score += act["weight"] + 2.0  # bonus for exact category match
            reasons.append(
                f"{act['planet']} yogakaraka in H6 ({act['strength']}) — "
                f"classical 'wealth through serving masses' placement"
            )
        elif act["house"] in (10, 11):
            # Yogakaraka in career/gains houses also supports service-at-scale
            score += 1.0
            reasons.append(
                f"{act['planet']} yogakaraka in H{act['house']} — "
                f"supports service-business scaling"
            )

    # ── 6L well-placed ──
    lord_6 = _get_house_lord(6, lagna_idx)
    lord_6_house = _get_planet_house(lord_6, planets, lagna_idx)
    lord_6_sign = _get_planet_sign(lord_6, planets)
    if lord_6_house in (1, 2, 5, 6, 9, 10, 11):
        score += 1.5
        reasons.append(f"6L ({lord_6}) in H{lord_6_house} — service-business lord well-placed")

    # ── Mars or Saturn in 6H = execution capacity for service work ──
    for p in ("Mars", "Saturn"):
        p_house = _get_planet_house(p, planets, lagna_idx)
        if p_house == 6:
            score += 1.5
            reasons.append(f"{p} in H6 — discipline/execution capacity for service work")

    # ── Mercury in 6H or 10H = systematic process capability ──
    mer_house = _get_planet_house("Mercury", planets, lagna_idx)
    if mer_house in (6, 10):
        score += 1.0
        reasons.append(f"Mercury in H{mer_house} — systematic-process capability")

    # ── Rahu in 6H = unconventional service to underserved ──
    rahu_house = _get_planet_house("Rahu", planets, lagna_idx)
    if rahu_house == 6:
        score += 1.5
        reasons.append("Rahu in H6 — unconventional service to underserved populations")

    # ── D-10 career chart: planets in 6H of D-10 ──
    d10_planets = _get_d_chart_planets(chart_data, "d10")
    for p in ("Jupiter", "Mercury", "Saturn"):
        pdata = d10_planets.get(p, {})
        ph = pdata.get("house")
        if ph is not None:
            try:
                if int(ph) == 6:
                    score += 0.5
                    reasons.append(f"D-10: {p} in H6 — career-path aligns with service work")
            except (TypeError, ValueError):
                pass

    # ── D-60 karmic markers on service planets ──
    d60 = _get_d_chart(chart_data, "d60")
    planet_analysis = d60.get("planet_analysis", {})
    if isinstance(planet_analysis, dict):
        sat_d60 = planet_analysis.get("Saturn", {})
        if isinstance(sat_d60, dict) and sat_d60.get("is_challenging"):
            warnings.append(
                f"D-60 Saturn has {sat_d60.get('karma_name', 'challenging')} karma — "
                f"service-to-masses work carries karmic tests around authority/discipline"
            )

    return {
        "category": CATEGORY_SERVICE_MASSES,
        "score": round(score, 1),
        "reasoning": reasons,
        "warnings": warnings,
        "vehicles": CATEGORY_VEHICLES[CATEGORY_SERVICE_MASSES],
    }


def score_institutional_authority_fit(chart_data: dict) -> dict:
    """
    INSTITUTIONAL AUTHORITY — large-institution leadership, long-structure
    authority, government/regulatory/academic/legal/financial-institution work.

    Distinct from ADVISORY (which can be solo practitioner).
    INSTITUTIONAL = systems that persist across decades, hierarchy-based.

    Key markers: Mahapurusha stacking, Saturn in kendra own-sign,
    Jupiter in kendra.
    """
    score = 0.0
    reasons = []
    warnings = []

    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # ── Mahapurusha detection ──
    mp_stack = detect_mahapurusha_stack(chart_data)
    if mp_stack["tier"] == "stacked":
        score += mp_stack["weight"]
        reasons.append(
            f"{mp_stack['count']} Mahapurusha yogas stacked "
            f"({', '.join(mp_stack['names'])}) — institutional-scale capacity"
        )
    elif mp_stack["tier"] == "single":
        score += mp_stack["weight"]
        reasons.append(
            f"Mahapurusha yoga ({mp_stack['names'][0]}) — authority capacity"
        )

    # ── Saturn in kendra = institutional structure capability ──
    sat_house = _get_planet_house("Saturn", planets, lagna_idx)
    sat_sign = _get_planet_sign("Saturn", planets)
    if sat_house in (1, 4, 7, 10):
        score += 2.0
        reasons.append(f"Saturn in H{sat_house} kendra — structural/institutional placement")
        if sat_sign is not None and sat_sign in (9, 10):  # Capricorn or Aquarius
            score += 1.5
            reasons.append("Saturn in own sign — institutional authority is native")

    # ── Jupiter in kendra = wisdom-authority ──
    jup_house = _get_planet_house("Jupiter", planets, lagna_idx)
    jup_sign = _get_planet_sign("Jupiter", planets)
    if jup_house in (1, 4, 7, 10):
        score += 2.0
        reasons.append(f"Jupiter in H{jup_house} kendra — wisdom-authority fit")
        if jup_sign is not None and _is_dignified("Jupiter", jup_sign):
            score += 1.0
            reasons.append("Jupiter dignified in kendra — peak wisdom-authority")

    # ── 10H strength: benefics in 10H ──
    for p in ("Jupiter", "Mercury", "Venus", "Sun", "Saturn"):
        p_house = _get_planet_house(p, planets, lagna_idx)
        if p_house == 10:
            score += 0.5
            reasons.append(f"{p} in H10 — career authority")

    # ── D-10 institutional markers ──
    d10_planets = _get_d_chart_planets(chart_data, "d10")
    sat_d10 = d10_planets.get("Saturn", {})
    sat_d10_house = sat_d10.get("house")
    if sat_d10_house is not None:
        try:
            sh = int(sat_d10_house)
            if sh in (10, 11):
                score += 1.5
                reasons.append(f"D-10: Saturn in H{sh} — long-structure career authority")
        except (TypeError, ValueError):
            pass

    jup_d10 = d10_planets.get("Jupiter", {})
    jup_d10_house = jup_d10.get("house")
    if jup_d10_house is not None:
        try:
            jh = int(jup_d10_house)
            if jh == 1:
                score += 2.0
                reasons.append("D-10: Jupiter in H1 — career itself is wisdom/dharma")
            elif jh in (4, 7, 10):
                score += 1.0
                reasons.append(f"D-10: Jupiter in kendra H{jh} — career wisdom support")
        except (TypeError, ValueError):
            pass

    # ── Yogakaraka in H10 or H7 = institutional authority alignment ──
    yk_activations = detect_yogakaraka_activation(chart_data) or []
    for act in yk_activations:
        if act["house"] in (7, 10):
            score += act["weight"]
            reasons.append(
                f"{act['planet']} yogakaraka in H{act['house']} ({act['strength']}) — "
                f"institutional authority alignment"
            )

    return {
        "category": CATEGORY_INSTITUTIONAL,
        "score": round(score, 1),
        "reasoning": reasons,
        "warnings": warnings,
        "vehicles": CATEGORY_VEHICLES[CATEGORY_INSTITUTIONAL],
    }


# ─── D-60 KARMIC WARNINGS ────────────────────────────────────────────────────

def _extract_d60_warnings(chart_data: dict) -> List[str]:
    """
    Pull D-60 Bhrashta/Rakshasa/Cruura karma markers and translate
    to business-domain karmic risks.
    """
    d60 = _get_d_chart(chart_data, "d60")
    planet_analysis = d60.get("planet_analysis", {})
    if not isinstance(planet_analysis, dict):
        return []

    # Map planets to business domains
    planet_domains = {
        "Mercury": "communication/knowledge businesses",
        "Jupiter": "wisdom/teaching/advisory businesses",
        "Venus": "luxury/creative/hospitality businesses",
        "Mars": "physical operations/construction/execution-dependent businesses",
        "Saturn": "structural/institutional/long-term businesses",
        "Sun": "authority/leadership/personal-brand businesses",
        "Moon": "public-facing/nurturing/food businesses",
    }

    warnings = []
    for planet, domain in planet_domains.items():
        pdata = planet_analysis.get(planet, {})
        if not isinstance(pdata, dict):
            continue
        if pdata.get("is_challenging"):
            karma_name = pdata.get("karma_name", "challenging")
            karma_desc = pdata.get("karma_desc", "")
            # Translate to actionable, non-fatalistic warning
            warnings.append(
                f"{planet} has {karma_name} karma ({karma_desc}) — "
                f"{domain} will test integrity in this area. "
                f"This is a karmic repair opportunity, not a block."
            )

    return warnings


# ─── ARCHETYPE BUSINESS FIT ──────────────────────────────────────────────────

def _business_fit_from_archetype(chart_data: dict) -> str:
    """
    Generate archetype-based business fit summary.
    Returns a concise string describing the archetype's natural business orientation.
    """
    archetype = chart_data.get("archetype", {})
    arch_name = ""
    if isinstance(archetype, dict):
        arch_name = archetype.get("name", "")
    elif isinstance(archetype, str):
        arch_name = archetype

    if not arch_name:
        return "No archetype data available for business fit assessment"

    # Map common archetypes to business orientation
    arch_upper = arch_name.upper()

    if "BROKER" in arch_upper or "MEDIATOR" in arch_upper:
        return (
            f"Archetype: {arch_name} — natural dealmaker. "
            "Thrives in platform, brokering, and network-leveraged businesses. "
            "NOT suited for physical operations management."
        )
    elif "ACCUMULATOR" in arch_upper or "BUILDER" in arch_upper:
        return (
            f"Archetype: {arch_name} — systematic wealth builder. "
            "Favors long-term value creation through platforms, advisory, or property. "
            "Needs patience-compatible business models."
        )
    elif "WARRIOR" in arch_upper or "COMMANDER" in arch_upper:
        return (
            f"Archetype: {arch_name} — execution-driven leader. "
            "Can handle physical operations IF Mars is well-placed. "
            "Best in competitive, action-oriented ventures."
        )
    elif "TEACHER" in arch_upper or "SAGE" in arch_upper or "GURU" in arch_upper:
        return (
            f"Archetype: {arch_name} — wisdom transmitter. "
            "Advisory, teaching, and knowledge platforms are natural fit. "
            "Avoid pure speculation or operations."
        )
    elif "CREATOR" in arch_upper or "ARTIST" in arch_upper:
        return (
            f"Archetype: {arch_name} — creative force. "
            "Creative, brand/persona, and design-driven businesses align. "
            "Physical operations and speculation are poor fits."
        )
    elif "HEALER" in arch_upper:
        return (
            f"Archetype: {arch_name} — service-oriented healer. "
            "Advisory, health/wellness platforms, and service businesses fit. "
            "Avoid pure speculation."
        )
    else:
        return (
            f"Archetype: {arch_name} — "
            "see category scores for specific business alignment."
        )


# ─── CONFORMANCE LAYER: check_signature INTERFACE ────────────────────────────
# business_fit is a different type of signature — it doesn't fire on
# dasha/transit windows like event signatures. It provides a static
# chart-level analysis. However, we implement the standard interface
# so it integrates with the signature registry.

def check_natal_conditions(chart_data: dict) -> dict:
    """
    For business_fit, the natal check IS the full analysis.
    Returns the complete business fit analysis.
    """
    result = analyze_business_fit(chart_data)
    favored = result.get("favored_categories", [])
    has_strong_fit = len(favored) > 0 and any(c["score"] >= 5.0 for c in favored)

    detail = []
    for cat in favored:
        detail.append(f"FAVORED: {cat['category']} (score {cat['score']})")
    for cat in result.get("disfavored_categories", []):
        detail.append(f"DISFAVORED: {cat['category']} (score {cat['score']})")

    return {
        "fires": has_strong_fit,
        "score": max((c["score"] for c in favored), default=0),
        "max_score": 15.0,
        "detail": detail,
        "downfall_marker": False,
        "business_fit_result": result,  # full analysis attached
    }


def check_dasha_conditions(chart_data: dict, md_lord: str, ad_lord: str) -> dict:
    """
    Business fit is chart-level, not dasha-dependent.
    Always fires (category fit doesn't change with dasha).
    """
    return {
        "fires": True,
        "detail": ["Business-fit is chart-level (not dasha-dependent)"],
    }


def check_transit_conditions(chart_data: dict, transit_positions: dict) -> dict:
    """
    Business fit is chart-level, not transit-dependent.
    Always fires (category fit doesn't change with transits).
    """
    return {
        "fires": True,
        "detail": ["Business-fit is chart-level (not transit-dependent)"],
    }


def check_signature(
    chart_data: dict,
    md_lord: str,
    ad_lord: str,
    transit_positions: dict,
) -> dict:
    """
    Full business_fit signature check.
    Since business_fit is chart-level, this primarily delegates to natal analysis.
    """
    natal = check_natal_conditions(chart_data)
    dasha = check_dasha_conditions(chart_data, md_lord, ad_lord)
    transit = check_transit_conditions(chart_data, transit_positions)

    conditions_met = sum([natal["fires"], dasha["fires"], transit["fires"]])

    return {
        "fires": conditions_met == 3,
        "partial": conditions_met == 2,
        "conditions_met": conditions_met,
        "natal_match": natal["detail"],
        "dasha_match": dasha["detail"],
        "transit_match": transit["detail"],
        "missing": [],
        "natal_fires": natal["fires"],
        "dasha_fires": dasha["fires"],
        "transit_fires": transit["fires"],
        "downfall_marker": False,
        # Extra: full business fit result
        "business_fit_result": natal.get("business_fit_result", {}),
    }


# ─── MAIN ANALYSIS FUNCTION ──────────────────────────────────────────────────

def analyze_business_fit(chart_data: dict) -> dict:
    """
    Main entry point — computes all category scores and ranks them.

    Returns:
        {
            "favored_categories": [...],     # score >= 3.0
            "disfavored_categories": [...],  # score <= -2.0
            "neutral_categories": [...],     # in between
            "karmic_warnings": [...],        # D-60 warnings
            "archetype_business_fit": "...", # archetype summary
        }
    """
    # ── V2: Run new detections ──
    yogakaraka = detect_yogakaraka_activation(chart_data)
    mahapurusha_stack = detect_mahapurusha_stack(chart_data)
    focus_split = detect_focus_split_risk(chart_data)

    # ── Score all categories (v1 + v2) ──
    categories = [
        score_platform_fit(chart_data),
        score_physical_ops_fit(chart_data),
        score_real_estate_fit(chart_data),
        score_advisory_fit(chart_data),
        score_brokering_fit(chart_data),
        score_creative_fit(chart_data),
        score_speculation_fit(chart_data),
        score_service_masses_fit(chart_data),
        score_institutional_authority_fit(chart_data),
    ]

    # Sort: high positive score = favored, low/negative = disfavored
    categories.sort(key=lambda c: c["score"], reverse=True)

    favored = [c for c in categories if c["score"] >= 3.0]
    disfavored = [c for c in categories if c["score"] <= -2.0]
    neutral = [c for c in categories if -2.0 < c["score"] < 3.0]

    # Extract karmic warnings (D-60)
    karmic_warnings = _extract_d60_warnings(chart_data)

    # Archetype-based business fit summary
    archetype_summary = _business_fit_from_archetype(chart_data)

    # ── Build primary activation summary from yogakaraka ──
    primary_activation = None
    if yogakaraka:
        # Pick the strongest activation
        best = max(yogakaraka, key=lambda a: a["weight"])
        primary_activation = {
            "yogakaraka_planet": best["planet"],
            "yogakaraka_house": best["house"],
            "yogakaraka_strength": best["strength"],
            "yogakaraka_type": best["type"],
            "business_theme": best["business_theme"],
            "note": "This is the single most important career-success marker in the chart.",
        }

    return {
        "primary_activation": primary_activation,
        "mahapurusha_stack": mahapurusha_stack,
        "focus_split_risk": focus_split,
        "favored_categories": favored,
        "disfavored_categories": disfavored,
        "neutral_categories": neutral,
        "karmic_warnings": karmic_warnings,
        "archetype_business_fit": archetype_summary,
        "signature_version": SIGNATURE_METADATA["version"],
        "confidence": SIGNATURE_METADATA["confidence"],
        "sample_size": SIGNATURE_METADATA["positive_sample_size"],
        "honesty_note": (
            "This analysis describes structural alignment based on classical "
            "Vedic divisional analysis, not outcome guarantees. A structurally "
            "aligned business can still fail if execution, capital, or market "
            "timing is off. The chart identifies the right vehicle type — you drive it."
        ),
    }
