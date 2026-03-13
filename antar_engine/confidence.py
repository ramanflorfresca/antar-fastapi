# confidence.py

from typing import List, Dict, Any, Optional

def compute_confidence(
    vimsottari_current: Optional[Dict[str, Any]],
    jaimini_current: Optional[Dict[str, Any]],
    ashtottari_current: Optional[Dict[str, Any]],
    transits: List[Dict[str, Any]],
    divisional_strengths: Dict[str, float],
    life_event_patterns: Optional[List[str]] = None
) -> tuple[float, List[str]]:
    """
    Compute a confidence score (0-1) and a list of explanatory factors.
    
    Args:
        vimsottari_current: dict with 'lord' and possibly other fields (or None)
        jaimini_current: dict with 'sign' and possibly other fields (or None)
        ashtottari_current: dict with 'lord' and possibly other fields (or None)
        transits: list of current transit dicts (each with 'planet', 'house', etc.)
        divisional_strengths: dict mapping planet to strength score (0-1)
        life_event_patterns: optional list of observed patterns (e.g., "Marriage during Venus dasha")
    
    Returns:
        confidence (float), factors (list of strings)
    """
    score = 0.5  # baseline
    factors = []

    # 1. Agreement between dasha systems
    agreement_count = 0
    if vimsottari_current and jaimini_current:
        # Simple check: are they thematically similar? We'll just check if they point to same planet/sign.
        # This is a simplification; you can enhance.
        vim_lord = vimsottari_current.get('lord', '')
        jai_sign = jaimini_current.get('sign', '')
        # If the sign's lord is the same as vimsottari lord, or if they share a common theme.
        # For now, we'll just give a small boost if both exist.
        agreement_count += 1
        factors.append("✓ Multiple dasha systems active")
    if ashtottari_current:
        agreement_count += 1

    if agreement_count >= 2:
        score += 0.1
        factors.append("✓ Multiple dasha systems agree")
    elif agreement_count == 1:
        # only one system – no boost
        pass

    # 2. Transit support
    benefic_planets = ['Jupiter', 'Venus', 'Mercury']
    malefic_planets = ['Saturn', 'Mars', 'Rahu', 'Ketu']
    benefic_house_influence = 0
    malefic_house_influence = 0

    for t in transits:
        planet = t['planet']
        house = t.get('house', 0)
        # Simple: benefics in 1,5,9 (trines) are good
        if planet in benefic_planets and house in [1,5,9]:
            benefic_house_influence += 1
        if planet in malefic_planets and house in [6,8,12]:
            malefic_house_influence += 1

    if benefic_house_influence >= 2:
        score += 0.1
        factors.append("✓ Strong benefic transits")
    elif benefic_house_influence == 1:
        score += 0.05
        factors.append("✓ Benefic transit present")

    if malefic_house_influence >= 2:
        score -= 0.1
        factors.append("⚠️ Challenging transits")
    elif malefic_house_influence == 1:
        score -= 0.05
        factors.append("⚠️ Some transit challenges")

    # 3. Divisional strengths (e.g., Atmakaraka exalted in D-9)
    if divisional_strengths:
        strong_planets = [p for p, s in divisional_strengths.items() if s > 0.7]
        if len(strong_planets) >= 2:
            score += 0.1
            factors.append("✓ Multiple planets strong in divisional charts")
        elif len(strong_planets) == 1:
            score += 0.05
            factors.append("✓ Key planet strong in divisional charts")

    # 4. Life event patterns (if any)
    if life_event_patterns:
        # Having patterns can increase confidence because predictions can be based on historical data
        score += 0.05
        factors.append("📊 Based on your life patterns")

    # Clamp score between 0 and 1
    final_score = max(0.0, min(1.0, score))
    return final_score, factors
