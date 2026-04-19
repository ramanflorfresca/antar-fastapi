"""
Context-Aware Remedy Selector — v5 Actionability Layer
=======================================================
Selects appropriate Lal Kitab remedies based on:
  1. Finding category (POSITIVE → activate, NEGATIVE → neutralize/support)
  2. Chart's relationship to target planet (yogakaraka? afflicted? sleeping?)
  3. Current dasha (is this planet's dasha active?)
  4. User context (struggle, goal, preferences, restrictions)

Critical principle: WRONG REMEDY IS WORSE THAN NO REMEDY.
Returns None when uncertain.

Author: Antar Engine · April 2026
"""

from typing import Dict, List, Optional, Any, Tuple
from .lal_kitab_database import (
    LalKitabRemedy,
    ALL_REMEDIES,
    REMEDY_BY_ID,
    get_remedies_for_planet,
)


# ─── FINDING-TO-PLANET MAPPING ─────────────────────────────────────────────

FINDING_PLANET_MAP = {
    # v2 detections
    "yogakaraka_activation": None,        # planet determined at runtime
    "mahapurusha_stack": None,             # multiple planets
    "focus_split_risk": "Rahu",

    # v4 detections
    "viparita_stack": None,               # multiple dushthana lords
    "identity_overwhelm": None,           # H1 stellium
    "moon_md_h2_pressure": "Moon",
    "hora_business_mismatch": None,       # structural, not planet-specific

    # D-60 karmic markers
    "d60_karma": None,                    # planet from finding
}

# Remedy IDs appropriate for each finding type
FINDING_REMEDY_PREFERENCE = {
    "yogakaraka_activation": {
        "Saturn": ["saturn_iron_workplace"],
        "Venus": ["venus_silver_daily"],
        "Mars": ["mars_sweet_to_sisters"],  # activation, not suppression
    },
    "focus_split_risk": ["rahu_silver_wire_scatter"],
    "moon_md_h2_pressure": ["moon_milk_offering"],
    "identity_overwhelm": ["venus_silver_daily"],
    "d60_karma_Mercury": ["mercury_green_cloth_tulsi"],
    "d60_karma_Jupiter": ["jupiter_feed_teachers"],
    "d60_karma_Saturn": ["saturn_flour_water_mustard"],
    "d60_karma_Mars": ["mars_sweet_to_sisters"],
    "d60_karma_Sun": ["sun_water_offering"],
    "d60_karma_Moon": ["moon_milk_offering"],
    "d60_karma_Venus": ["venus_cow_ghee"],
    "d60_karma_Rahu": ["rahu_coconut_water"],
    "d60_karma_Ketu": ["ketu_dog_feeding"],
}


def select_appropriate_remedy(
    finding_type: str,
    finding_category: str,
    target_planet: Optional[str],
    chart_data: dict,
    user_context: Optional[dict] = None,
) -> Optional[LalKitabRemedy]:
    """
    Select the most appropriate remedy for a finding.

    Args:
        finding_type: e.g., "yogakaraka_activation", "focus_split_risk"
        finding_category: "POSITIVE" | "NEGATIVE" | "NEUTRAL"
        target_planet: Planet involved (if known)
        chart_data: Full chart data dict
        user_context: Optional user preferences/restrictions

    Returns:
        LalKitabRemedy or None if no appropriate remedy exists.
    """
    # Step 1: Get candidate remedy IDs from preference map
    candidates = _get_candidate_remedies(finding_type, target_planet)
    if not candidates:
        # Fall back to planet-based selection
        if target_planet:
            candidates = get_remedies_for_planet(target_planet)
        if not candidates:
            return None

    # Step 2: Filter by contraindications
    chart_conditions = _extract_chart_conditions(chart_data, target_planet)
    filtered = _filter_contraindicated(candidates, chart_conditions)
    if not filtered:
        return None

    # Step 3: Filter by category (POSITIVE → activation remedies, NEGATIVE → neutralization)
    category_filtered = _filter_by_category(filtered, finding_category, target_planet, chart_data)
    if not category_filtered:
        # Relax and return best available
        category_filtered = filtered

    # Step 4: Filter by user preferences (allergies, time, cultural context)
    if user_context:
        user_filtered = _filter_by_user_context(category_filtered, user_context)
        if user_filtered:
            category_filtered = user_filtered

    # Step 5: Return highest-confidence remedy
    return _select_highest_confidence(category_filtered)


def _get_candidate_remedies(
    finding_type: str, target_planet: Optional[str]
) -> List[LalKitabRemedy]:
    """Get candidate remedies from preference map."""
    # Check specific finding type
    pref = FINDING_REMEDY_PREFERENCE.get(finding_type)
    if pref is None and target_planet:
        # Try planet-specific key (e.g., d60_karma_Mercury)
        pref = FINDING_REMEDY_PREFERENCE.get(f"{finding_type}_{target_planet}")

    if pref is None:
        return []

    # pref can be a list of IDs or a dict keyed by planet
    if isinstance(pref, dict):
        if target_planet and target_planet in pref:
            remedy_ids = pref[target_planet]
        else:
            return []
    else:
        remedy_ids = pref

    remedies = []
    for rid in remedy_ids:
        r = REMEDY_BY_ID.get(rid)
        if r:
            remedies.append(r)
    return remedies


def _extract_chart_conditions(
    chart_data: dict, target_planet: Optional[str]
) -> List[str]:
    """
    Extract active conditions from chart that affect remedy selection.
    Returns list of condition strings matching contraindication tags.
    """
    conditions = []
    planets = chart_data.get("planets", {})
    lagna_idx = chart_data.get("lagna", {}).get("sign_index", 0)
    yogas = chart_data.get("yogas", [])
    current_dasha = chart_data.get("current_dasha", {})

    # Check if target planet is yogakaraka
    from ..signatures.business_fit import YOGAKARAKA_BY_LAGNA
    yk_planet = YOGAKARAKA_BY_LAGNA.get(lagna_idx)
    if target_planet and yk_planet == target_planet:
        conditions.append(f"{target_planet.lower()}_yogakaraka_active")

    # Check Mahapurusha yogas
    mp_yogas = [y for y in yogas if isinstance(y, dict) and y.get("category") == "mahapurusha"]
    for y in mp_yogas:
        yp = y.get("planet", "")
        if yp == "Venus":
            conditions.append("venus_malavya_active")
        elif yp == "Mars":
            conditions.append("mars_ruchaka_active")

    # Check if Rahu is wealth engine
    rahu_data = planets.get("Rahu", {})
    if isinstance(rahu_data, dict):
        rahu_house = rahu_data.get("house")
        if rahu_house in (8, 10, 11):
            conditions.append("rahu_wealth_engine")
            if rahu_house == 11:
                conditions.append("rahu_h11_gains")
            if rahu_house == 10:
                conditions.append("rahu_h10_career")

    # Check current MD
    if isinstance(current_dasha, dict):
        md_lord = current_dasha.get("md_lord", "")
        if md_lord == "Rahu":
            conditions.append("rahu_md_active")
        if md_lord == target_planet:
            conditions.append(f"{target_planet.lower()}_md_active")

    return conditions


def _filter_contraindicated(
    remedies: List[LalKitabRemedy], conditions: List[str]
) -> List[LalKitabRemedy]:
    """Remove remedies whose contraindications match active conditions."""
    result = []
    for r in remedies:
        if not r.contraindications:
            result.append(r)
            continue
        has_contra = any(c in conditions for c in r.contraindications)
        if not has_contra:
            result.append(r)
    return result


def _filter_by_category(
    remedies: List[LalKitabRemedy],
    category: str,
    target_planet: Optional[str],
    chart_data: dict,
) -> List[LalKitabRemedy]:
    """
    For POSITIVE findings: prefer activation remedies.
    For NEGATIVE findings: prefer neutralization/support remedies.
    """
    if category == "POSITIVE":
        # Prefer remedies with "activation" or "support" in condition
        activation_keywords = ["activation", "support", "strengthen"]
        preferred = [
            r for r in remedies
            if any(kw in r.target_condition.lower() for kw in activation_keywords)
        ]
        return preferred if preferred else remedies
    elif category == "NEGATIVE":
        # Prefer remedies with "affliction" or "neutralization" in condition
        neutralize_keywords = ["affliction", "neutraliz", "clearing", "stabiliz", "pressure"]
        preferred = [
            r for r in remedies
            if any(kw in r.target_condition.lower() for kw in neutralize_keywords)
        ]
        return preferred if preferred else remedies
    return remedies


def _filter_by_user_context(
    remedies: List[LalKitabRemedy], user_context: dict
) -> List[LalKitabRemedy]:
    """Filter remedies by user preferences and restrictions."""
    result = list(remedies)

    # Filter by allergies/restrictions
    restrictions = user_context.get("remedy_preferences", {}).get("allergies_or_restrictions", [])
    if restrictions:
        result = [
            r for r in result
            if not any(
                restr.lower() in mat.lower()
                for restr in restrictions
                for mat in r.materials
            )
        ]

    # Filter by time availability
    time_avail = user_context.get("remedy_preferences", {}).get("time_available_daily", "")
    if time_avail == "5_min":
        # Prefer weekly or continuous remedies over daily rituals
        simple = [r for r in result if r.frequency in ("Weekly", "Continuous", "Once")]
        if simple:
            result = simple

    # Filter by cultural context
    cultural = user_context.get("remedy_preferences", {}).get("cultural_context", "")
    if cultural == "secular":
        # Prefer non-temple remedies (feeding animals, donations, workplace items)
        secular = [
            r for r in result
            if "temple" not in r.action.lower() and "shiva" not in r.action.lower()
        ]
        if secular:
            result = secular

    return result


def _select_highest_confidence(remedies: List[LalKitabRemedy]) -> Optional[LalKitabRemedy]:
    """Select the highest-confidence remedy from candidates."""
    if not remedies:
        return None

    confidence_order = {"high": 3, "moderate": 2, "experimental": 1}
    remedies.sort(key=lambda r: confidence_order.get(r.confidence, 0), reverse=True)
    return remedies[0]


def select_deactivation_remedy(
    finding_type: str,
    target_planet: Optional[str],
    chart_data: dict,
) -> Optional[Dict[str, str]]:
    """
    Select a deactivation recommendation (what to stop doing / remove).
    Returns a dict with 'action' and 'reason', or None.

    Deactivations are more contextual and less formulaic than activations,
    so this returns guidance rather than a LalKitabRemedy object.
    """
    deactivations = {
        "focus_split_risk": {
            "action": "Stop networking events and opportunity conversations not directly related to your primary vehicle for 6 months.",
            "reason": "Each new connection feeds the scatter-impulse. Focus protocol requires active reduction of input streams.",
        },
        "identity_overwhelm": {
            "action": "Divest from physical-asset businesses. Stop attending events where manufacturing/operations peers reinforce 'you should be building.'",
            "reason": "Continuing to own wrong-fit businesses drains capital AND identity — your design amplifies whatever you identify with.",
        },
        "moon_md_h2_pressure": {
            "action": "Stop consuming content showing wealthier peers' lifestyles. Remove aspirational-wealth content consumption during this period.",
            "reason": "Emotional-responsive energy in the wealth house is triggered by comparison. Reducing the trigger reduces the impulse.",
        },
        "hora_business_mismatch": {
            "action": "Do not add capital to ventures that oppose your wealth-type architecture. Even at apparent opportunity, the structural mismatch will consume rather than compound.",
            "reason": "Your wealth-type design favors a specific channel. Operating against it historically produces capital drain.",
        },
    }

    return deactivations.get(finding_type)
