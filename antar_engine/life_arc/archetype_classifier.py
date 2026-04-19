"""
v4 Archetype Classifier — Surface B: Life Arc
================================================
Classifies charts into one of five wealth archetypes using v2+v4
detection primitives. The archetype drives business-fit narrative
and honest-scale-read.

Five archetypes:
  1. DISRUPTOR — triple viparita, crisis-as-engine, Musk signature
  2. SYSTEMATIC — Mahapurusha stacking, Saturn structure, institutional scale
  3. MASS_SERVER — H6 workforce + Rahu amplification, serve-millions model
  4. CHARISMA — H1 stellium without output-engine, relationship leverage
  5. INSTITUTIONAL — Jupiter/Saturn in kendras, dharmic authority, legacy

Each archetype has a scoring function. Highest scorer wins.
Ties broken by specificity (more conditions matched = more specific).

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any, Tuple


# ─── ARCHETYPE DEFINITIONS ──────────────────────────────────────────────────

WEALTH_ARCHETYPES = {
    "DISRUPTOR": {
        "label": "Disruptor",
        "description": (
            "Crisis-as-engine architecture. Chart literally encodes "
            "'the worse it looks, the bigger the outcome.' Multiple "
            "dushthana lords exchanging houses create rise-through-adversity "
            "patterns. Found in founders whose biography shows near-failures "
            "transforming into breakthroughs."
        ),
        "signature_markers": [
            "Triple or double Viparita Raj Yoga",
            "Dushthana lords in mutual exchange",
            "Mars/Rahu in H6 or H8 with dignity",
            "Saturn providing structural containment from H10/H11",
        ],
        "favored_vehicles": [
            "Deep-tech platforms",
            "Frontier industries (space, energy, biotech)",
            "Turnaround operations",
            "Venture-scale startups with long timelines",
        ],
        "disfavored_vehicles": [
            "Stable recurring-revenue services",
            "Inherited operations",
            "Advisory/consulting (too low-variance)",
        ],
        "historical_examples": "Musk-tier founder signature",
    },
    "SYSTEMATIC": {
        "label": "Systematic Builder",
        "description": (
            "Mahapurusha-stacked chart with Saturn as structural anchor. "
            "Builds institutions that outlast the founder. Wealth accumulates "
            "slowly then compounds exponentially. Requires patience-compatible "
            "business models."
        ),
        "signature_markers": [
            "2+ Mahapurusha yogas (especially Sasa + one other)",
            "Saturn well-placed in kendra or 11H",
            "Yogakaraka activated and dignified",
            "D-10 showing structured career progression",
        ],
        "favored_vehicles": [
            "Conglomerate / holding company",
            "Infrastructure and real estate",
            "Financial services at scale",
            "Industrial manufacturing",
        ],
        "disfavored_vehicles": [
            "Quick-flip speculation",
            "Personal-brand businesses",
            "Creative/media ventures",
        ],
        "historical_examples": "Gates/Ambani-tier systematic empire builder",
    },
    "MASS_SERVER": {
        "label": "Mass Server",
        "description": (
            "H6 workforce activation combined with Rahu amplification. "
            "Chart architecture serves millions through operational systems. "
            "Wealth comes from volume, not margin. The chart's 6H activation "
            "that classically reads as 'servant' actually means 'serving at scale.'"
        ),
        "signature_markers": [
            "Saturn/Mars in H6 with dignity",
            "Rahu in H10 or H11 amplifying reach",
            "Moon supporting public connection (H4/H7/H10)",
            "D-10 showing service-oriented career",
        ],
        "favored_vehicles": [
            "MSME service platforms",
            "Healthcare / care-work at scale",
            "Labor-augmentation technology",
            "Operational automation",
            "Franchise / multi-location service",
        ],
        "disfavored_vehicles": [
            "Luxury/premium products",
            "Speculative finance",
            "Personal advisory (too small-scale)",
        ],
        "historical_examples": "Founders of mass-service platforms and operational empires",
    },
    "CHARISMA": {
        "label": "Charisma Leverager",
        "description": (
            "H1 stellium (3+ planets) without compensating output-engine "
            "in H6/H10/H11. Enormous personal presence and relationship "
            "capital, but production capacity is thin. Wealth MUST flow "
            "through relationship leverage, not operational scale."
        ),
        "signature_markers": [
            "3+ non-shadow planets in H1",
            "Weak or absent H6/H10/H11 activation",
            "Venus or Jupiter in H1 adding charm/wisdom",
            "Moon well-placed for public connection",
        ],
        "favored_vehicles": [
            "Consulting and advisory services",
            "Personal-brand businesses",
            "Relationship brokerage (M&A, real estate, matchmaking)",
            "Media / speaking / teaching platforms",
            "Services-sales through personal presence",
        ],
        "disfavored_vehicles": [
            "Physical-operations manufacturing",
            "Capital-heavy infrastructure",
            "Operational platforms requiring uptime/scale",
            "Asset-heavy businesses",
            "Pure-tech product build (CTO roles)",
        ],
        "historical_examples": "Shashi Tharoor-tier — brilliant presence, advisory-optimal",
    },
    "INSTITUTIONAL": {
        "label": "Institutional Authority",
        "description": (
            "Jupiter and Saturn anchoring kendras with dharmic dignity. "
            "Chart architecture builds authority within existing systems "
            "rather than disrupting them. Wealth comes from positional "
            "authority, legacy institutions, and long-tenure compounding."
        ),
        "signature_markers": [
            "Jupiter in kendra (especially H1/H10) with dignity",
            "Saturn in kendra providing structural authority",
            "Mahapurusha Hamsa or Sasa yoga",
            "D-9 confirming dharmic purpose alignment",
        ],
        "favored_vehicles": [
            "Legal practice at scale",
            "Financial institutions",
            "Academic / research authority",
            "Government / regulatory roles",
            "Multi-generational family business leadership",
        ],
        "disfavored_vehicles": [
            "Startup-speed ventures",
            "Speculative trading",
            "Personal-brand-dependent businesses",
        ],
        "historical_examples": "Institutional leaders, family business patriarchs",
    },
}


# ─── SIGN / DIGNITY HELPERS (local copies to avoid circular imports) ────────

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

KENDRA_HOUSES = {1, 4, 7, 10}


def _get_planet_house(planet_name: str, planets: dict, lagna_idx: int) -> Optional[int]:
    pdata = planets.get(planet_name, {})
    if not pdata or not isinstance(pdata, dict):
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


def _is_dignified(planet_name: str, sign_index: int) -> bool:
    if EXALTATION.get(planet_name) == sign_index:
        return True
    if sign_index in OWN_SIGNS.get(planet_name, []):
        return True
    return False


# ─── INDIVIDUAL ARCHETYPE SCORERS ───────────────────────────────────────────

def _score_disruptor(
    chart_data: dict,
    viparita_result: Optional[dict] = None,
    dushthana_wealth: Optional[dict] = None,
) -> Tuple[float, List[str]]:
    """Score chart against DISRUPTOR archetype."""
    score = 0.0
    reasons = []
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # Primary signal: Viparita stack count
    if viparita_result:
        tier = viparita_result.get("tier", "none")
        if tier == "extreme":
            score += 6.0
            reasons.append(f"Triple+ Viparita Raj Yoga ({viparita_result.get('count', 3)} stacked)")
        elif tier == "strong":
            score += 4.0
            reasons.append("Double Viparita Raj Yoga")
        elif tier == "moderate":
            score += 1.5
            reasons.append("Single Viparita Raj Yoga")

    # Secondary: dushthana wealth patterns (from v3 layer)
    if dushthana_wealth and dushthana_wealth.get("any_detected"):
        strength = dushthana_wealth.get("total_dushthana_strength", 0)
        if strength >= 6.0:
            score += 3.0
            reasons.append(f"Strong dushthana-wealth activation (strength {strength:.1f})")
        elif strength >= 3.0:
            score += 1.5
            reasons.append(f"Moderate dushthana-wealth activation (strength {strength:.1f})")

    # Mars or Rahu in H6/H8 with dignity = crisis-navigation capacity
    for planet in ("Mars", "Rahu"):
        house = _get_planet_house(planet, planets, lagna_idx)
        if house in (6, 8):
            p_sign = planets.get(planet, {}).get("sign_index", -1)
            if p_sign >= 0 and _is_dignified(planet, p_sign):
                score += 1.5
                reasons.append(f"{planet} in H{house} with dignity — crisis navigation")
            else:
                score += 0.5
                reasons.append(f"{planet} in H{house} — crisis exposure without dignity")

    # Saturn providing containment from H10/H11
    saturn_house = _get_planet_house("Saturn", planets, lagna_idx)
    if saturn_house in (10, 11):
        score += 1.0
        reasons.append(f"Saturn in H{saturn_house} — structural containment for disruption")

    return score, reasons


def _score_systematic(
    chart_data: dict,
    mahapurusha_result: Optional[dict] = None,
    yogakaraka_result: Optional[list] = None,
) -> Tuple[float, List[str]]:
    """Score chart against SYSTEMATIC archetype."""
    score = 0.0
    reasons = []
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # Primary signal: Mahapurusha stacking
    if mahapurusha_result:
        tier = mahapurusha_result.get("tier", "none")
        if tier == "stacked":
            score += 6.0
            names = mahapurusha_result.get("names", [])
            reasons.append(f"Stacked Mahapurusha yogas ({', '.join(names)})")
            # Extra bonus if Sasa (Saturn) is one of them
            if "Sasa" in names:
                score += 1.5
                reasons.append("Sasa yoga anchors systematic structure")
        elif tier == "single":
            score += 3.0
            reasons.append(f"Single Mahapurusha yoga ({mahapurusha_result.get('names', [''])[0]})")

    # Yogakaraka activation = career-success engine
    if yogakaraka_result:
        best = max(yogakaraka_result, key=lambda a: a.get("weight", 0))
        if best.get("strength") == "exalted":
            score += 2.5
            reasons.append(f"Yogakaraka {best['planet']} exalted in H{best.get('house', '?')}")
        elif best.get("strength") == "own_sign":
            score += 2.0
            reasons.append(f"Yogakaraka {best['planet']} in own sign H{best.get('house', '?')}")
        else:
            score += 1.0
            reasons.append(f"Yogakaraka {best['planet']} activated")

    # Saturn in kendra or H11 = structural authority
    saturn_house = _get_planet_house("Saturn", planets, lagna_idx)
    saturn_sign = planets.get("Saturn", {}).get("sign_index", -1)
    if saturn_house in KENDRA_HOUSES:
        if saturn_sign >= 0 and _is_dignified("Saturn", saturn_sign):
            score += 2.0
            reasons.append(f"Saturn dignified in kendra H{saturn_house}")
        else:
            score += 1.0
            reasons.append(f"Saturn in kendra H{saturn_house}")
    elif saturn_house == 11:
        score += 1.0
        reasons.append("Saturn in H11 — gains through patience")

    # D-10 check: Saturn in gains houses (10, 11) in career chart
    d10 = chart_data.get("divisional_charts", {}).get("d10", {})
    if isinstance(d10, dict):
        d10_planets = d10.get("planets", {})
        d10_saturn = d10_planets.get("Saturn", {})
        if isinstance(d10_saturn, dict):
            d10_sat_house = d10_saturn.get("house")
            if d10_sat_house in (10, 11):
                score += 1.0
                reasons.append(f"D-10 Saturn in H{d10_sat_house} — career-level structure")

    return score, reasons


def _score_mass_server(
    chart_data: dict,
    dushthana_wealth: Optional[dict] = None,
) -> Tuple[float, List[str]]:
    """Score chart against MASS_SERVER archetype."""
    score = 0.0
    reasons = []
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # Primary: Saturn or Mars in H6 with dignity = workforce commander
    for planet in ("Saturn", "Mars"):
        house = _get_planet_house(planet, planets, lagna_idx)
        if house == 6:
            p_sign = planets.get(planet, {}).get("sign_index", -1)
            if p_sign >= 0 and _is_dignified(planet, p_sign):
                score += 3.0
                reasons.append(f"{planet} dignified in H6 — serve-at-scale engine")
            else:
                score += 1.5
                reasons.append(f"{planet} in H6 — service orientation")

    # Rahu in H10 or H11 = mass amplification
    rahu_house = _get_planet_house("Rahu", planets, lagna_idx)
    if rahu_house == 10:
        score += 2.5
        reasons.append("Rahu in H10 — mass-reach career amplification")
    elif rahu_house == 11:
        score += 2.0
        reasons.append("Rahu in H11 — large-network gains")
    elif rahu_house == 6:
        score += 1.5
        reasons.append("Rahu in H6 — obsessive service/competition drive")

    # Moon in public-connection houses (4, 7, 10) = emotional rapport with masses
    moon_house = _get_planet_house("Moon", planets, lagna_idx)
    if moon_house in (4, 7, 10):
        score += 1.5
        reasons.append(f"Moon in H{moon_house} — public emotional connection")

    # 6H dushthana-as-wealth pattern from v3 detection
    if dushthana_wealth and dushthana_wealth.get("any_detected"):
        patterns = dushthana_wealth.get("patterns_detected", [])
        for pat in patterns:
            if isinstance(pat, dict) and "6h" in pat.get("pattern", "").lower():
                score += 2.0
                reasons.append("6H entrepreneur pattern detected — service wealth")
                break

    # Multiple planets aspecting H6 = strong service-sector pull
    h6_aspects = 0
    for p_name, pdata in planets.items():
        if not isinstance(pdata, dict) or p_name in ("Rahu", "Ketu"):
            continue
        p_house = _get_planet_house(p_name, planets, lagna_idx)
        # 7th aspect to H6 comes from H12; Jupiter aspects H6 from H2 (5th), H10 (9th)
        if p_house == 12:  # 7th aspect to H6
            h6_aspects += 1
    if h6_aspects >= 2:
        score += 1.0
        reasons.append(f"{h6_aspects} planets aspect H6 — reinforced service pull")

    return score, reasons


def _score_charisma(
    chart_data: dict,
    identity_overwhelm: Optional[dict] = None,
) -> Tuple[float, List[str]]:
    """Score chart against CHARISMA archetype."""
    score = 0.0
    reasons = []
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # Primary: identity overwhelm detection (from v4)
    if identity_overwhelm:
        severity = identity_overwhelm.get("severity", "moderate")
        h1_count = identity_overwhelm.get("h1_count", 3)
        if severity == "high":
            score += 6.0
            reasons.append(f"{h1_count}-planet H1 stellium with no output-engine — strong CHARISMA")
        else:
            score += 4.0
            reasons.append(f"{h1_count}-planet H1 stellium — moderate CHARISMA pattern")
    else:
        # Manual H1 stellium check (lighter version)
        h1_planets = [
            p for p, d in planets.items()
            if isinstance(d, dict)
            and _get_planet_house(p, planets, lagna_idx) == 1
            and p not in ("Rahu", "Ketu")
        ]
        h1_count = len(h1_planets)
        if h1_count >= 3:
            # Check output engine
            output_count = 0
            for p in ("Saturn", "Mars", "Rahu", "Sun"):
                h = _get_planet_house(p, planets, lagna_idx)
                if h in (6, 10, 11):
                    output_count += 1
            if output_count < 2:
                score += 4.0
                reasons.append(f"{h1_count} planets in H1 without output-engine")
            else:
                score += 1.0
                reasons.append(f"{h1_count} planets in H1 but output-engine present — partial CHARISMA")
        elif h1_count == 2:
            score += 0.5
            reasons.append("2 planets in H1 — mild presence emphasis")

    # Venus or Jupiter in H1 adds charm/wisdom
    for planet in ("Venus", "Jupiter"):
        if _get_planet_house(planet, planets, lagna_idx) == 1:
            score += 1.5
            reasons.append(f"{planet} in H1 — {'charm' if planet == 'Venus' else 'wisdom'} amplifier")

    # Moon well-placed for public rapport
    moon_house = _get_planet_house("Moon", planets, lagna_idx)
    if moon_house in (1, 4, 7, 10):
        score += 1.0
        reasons.append(f"Moon in H{moon_house} — public connection capacity")

    # Negative: strong output-engine REDUCES charisma archetype fit
    output_planets = 0
    for p in ("Saturn", "Mars"):
        h = _get_planet_house(p, planets, lagna_idx)
        if h in (6, 10):
            output_planets += 1
    if output_planets >= 2:
        score -= 2.0
        reasons.append("Strong output-engine (Saturn+Mars in H6/H10) — reduces CHARISMA fit")

    return score, reasons


def _score_institutional(
    chart_data: dict,
    mahapurusha_result: Optional[dict] = None,
    yogakaraka_result: Optional[list] = None,
) -> Tuple[float, List[str]]:
    """Score chart against INSTITUTIONAL archetype."""
    score = 0.0
    reasons = []
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)

    # Jupiter in kendra with dignity = dharmic authority
    jupiter_house = _get_planet_house("Jupiter", planets, lagna_idx)
    jupiter_sign = planets.get("Jupiter", {}).get("sign_index", -1)
    if jupiter_house in KENDRA_HOUSES:
        if jupiter_sign >= 0 and _is_dignified("Jupiter", jupiter_sign):
            score += 3.0
            reasons.append(f"Jupiter dignified in kendra H{jupiter_house} — dharmic authority")
        else:
            score += 1.5
            reasons.append(f"Jupiter in kendra H{jupiter_house}")
    elif jupiter_house in (5, 9):  # trikona
        score += 1.0
        reasons.append(f"Jupiter in trikona H{jupiter_house} — dharmic support")

    # Saturn in kendra = structural institutional anchor
    saturn_house = _get_planet_house("Saturn", planets, lagna_idx)
    saturn_sign = planets.get("Saturn", {}).get("sign_index", -1)
    if saturn_house in KENDRA_HOUSES:
        if saturn_sign >= 0 and _is_dignified("Saturn", saturn_sign):
            score += 2.5
            reasons.append(f"Saturn dignified in kendra H{saturn_house} — institutional structure")
        else:
            score += 1.0
            reasons.append(f"Saturn in kendra H{saturn_house}")

    # Mahapurusha: Hamsa or Sasa specifically = institutional marker
    if mahapurusha_result:
        names = mahapurusha_result.get("names", [])
        if "Hamsa" in names:
            score += 2.0
            reasons.append("Hamsa yoga — wisdom/dharmic institutional authority")
        if "Sasa" in names:
            score += 2.0
            reasons.append("Sasa yoga — structural/disciplinary institutional authority")

    # D-9 confirmation: Jupiter or Saturn dignified in navamsha
    d9 = chart_data.get("divisional_charts", {}).get("d9", {})
    if isinstance(d9, dict):
        d9_planets = d9.get("planets", {})
        for planet in ("Jupiter", "Saturn"):
            d9_p = d9_planets.get(planet, {})
            if isinstance(d9_p, dict):
                d9_sign = d9_p.get("sign_index", -1)
                if d9_sign >= 0 and _is_dignified(planet, d9_sign):
                    score += 1.0
                    reasons.append(f"D-9 {planet} dignified — navamsha confirms institutional purpose")

    # Sun in H10 with dignity = positional authority
    sun_house = _get_planet_house("Sun", planets, lagna_idx)
    sun_sign = planets.get("Sun", {}).get("sign_index", -1)
    if sun_house == 10:
        if sun_sign >= 0 and _is_dignified("Sun", sun_sign):
            score += 2.0
            reasons.append("Sun dignified in H10 — career authority")
        else:
            score += 1.0
            reasons.append("Sun in H10 — authority orientation")

    # Negative: Rahu in H1 or H10 = unconventional, opposes institutional
    rahu_house = _get_planet_house("Rahu", planets, lagna_idx)
    if rahu_house in (1, 10):
        score -= 1.5
        reasons.append(f"Rahu in H{rahu_house} — unconventional drive opposes institutional path")

    return score, reasons


# ─── MAIN CLASSIFIER ────────────────────────────────────────────────────────

def classify_wealth_archetype(
    chart_data: dict,
    viparita_result: Optional[dict] = None,
    identity_overwhelm: Optional[dict] = None,
    mahapurusha_result: Optional[dict] = None,
    yogakaraka_result: Optional[list] = None,
    dushthana_wealth: Optional[dict] = None,
) -> dict:
    """
    Classify chart into one of five wealth archetypes.

    Accepts pre-computed detection results to avoid re-computation.
    If not provided, scores with available chart_data only.

    Returns:
        {
            "primary_archetype": str,
            "primary_score": float,
            "primary_description": str,
            "secondary_archetype": str or None,
            "secondary_score": float,
            "all_scores": {archetype: {score, reasons}},
            "archetype_detail": dict (full WEALTH_ARCHETYPES entry),
            "honest_read": str,
        }
    """
    # Score all five archetypes
    scores = {}

    s, r = _score_disruptor(chart_data, viparita_result, dushthana_wealth)
    scores["DISRUPTOR"] = {"score": s, "reasons": r}

    s, r = _score_systematic(chart_data, mahapurusha_result, yogakaraka_result)
    scores["SYSTEMATIC"] = {"score": s, "reasons": r}

    s, r = _score_mass_server(chart_data, dushthana_wealth)
    scores["MASS_SERVER"] = {"score": s, "reasons": r}

    s, r = _score_charisma(chart_data, identity_overwhelm)
    scores["CHARISMA"] = {"score": s, "reasons": r}

    s, r = _score_institutional(chart_data, mahapurusha_result, yogakaraka_result)
    scores["INSTITUTIONAL"] = {"score": s, "reasons": r}

    # Rank: highest score wins, ties broken by number of reasons (specificity)
    ranked = sorted(
        scores.items(),
        key=lambda kv: (kv[1]["score"], len(kv[1]["reasons"])),
        reverse=True,
    )

    primary_name = ranked[0][0]
    primary_data = ranked[0][1]
    primary_archetype = WEALTH_ARCHETYPES[primary_name]

    secondary_name = ranked[1][0] if ranked[1][1]["score"] >= 3.0 else None
    secondary_score = ranked[1][1]["score"] if secondary_name else 0.0

    # Build honest read
    honest_read = _build_honest_read(
        primary_name, primary_data["score"],
        secondary_name, secondary_score,
        primary_archetype,
    )

    return {
        "primary_archetype": primary_name,
        "primary_score": primary_data["score"],
        "primary_label": primary_archetype["label"],
        "primary_description": primary_archetype["description"],
        "primary_reasons": primary_data["reasons"],
        "secondary_archetype": secondary_name,
        "secondary_score": secondary_score,
        "secondary_label": WEALTH_ARCHETYPES[secondary_name]["label"] if secondary_name else None,
        "all_scores": scores,
        "archetype_detail": primary_archetype,
        "favored_vehicles": primary_archetype["favored_vehicles"],
        "disfavored_vehicles": primary_archetype["disfavored_vehicles"],
        "honest_read": honest_read,
    }


def _build_honest_read(
    primary: str,
    primary_score: float,
    secondary: Optional[str],
    secondary_score: float,
    archetype: dict,
) -> str:
    """
    Build the honest-scale-read narrative.
    This is the v4 'no-sugar-coating' output that tells the user
    exactly what their chart architecture supports and what it doesn't.
    """
    parts = []

    # Confidence qualifier based on score magnitude
    if primary_score >= 8.0:
        parts.append(
            f"Strong {archetype['label']} architecture (confidence: high). "
            f"Chart clearly encodes this wealth pattern."
        )
    elif primary_score >= 5.0:
        parts.append(
            f"Moderate {archetype['label']} architecture (confidence: medium). "
            f"Chart leans toward this pattern but isn't locked in."
        )
    elif primary_score >= 3.0:
        parts.append(
            f"Mild {archetype['label']} tendency (confidence: low). "
            f"Chart shows some markers but not a dominant pattern."
        )
    else:
        parts.append(
            f"No dominant wealth archetype detected. "
            f"Chart is balanced across patterns — business-fit should "
            f"rely on category scores rather than archetype."
        )

    # Secondary archetype
    if secondary and secondary_score >= 5.0:
        secondary_label = WEALTH_ARCHETYPES[secondary]["label"]
        parts.append(
            f"Secondary {secondary_label} pattern is also strong "
            f"(score {secondary_score:.1f}) — chart supports hybrid approach."
        )
    elif secondary and secondary_score >= 3.0:
        secondary_label = WEALTH_ARCHETYPES[secondary]["label"]
        parts.append(
            f"Mild secondary {secondary_label} influence present."
        )

    # Honest constraint
    if primary_score >= 3.0:
        disfavored = archetype.get("disfavored_vehicles", [])
        if disfavored:
            parts.append(
                f"Architecture actively opposes: {', '.join(disfavored[:3]).lower()}. "
                f"These venture types will consume capital despite apparent effort."
            )

    return " ".join(parts)
