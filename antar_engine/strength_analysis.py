"""
strength_analysis.py
Computes planetary strength, neecha bhanga, and identifies yogas.
Uses data from Supabase tables.
"""

from typing import Dict, Any, List, Tuple, Optional
from supabase import Client

def get_planet_strength(planet: str, chart_data: Dict[str, Any], supabase: Client) -> Tuple[float, List[str]]:
    """
    Compute strength factor for a planet based on sign placement, exaltation, etc.
    Returns (score, list_of_factors).
    """
    score = 1.0
    factors = []

    # Get planet position
    planet_data = chart_data['planets'].get(planet)
    if not planet_data:
        return 0.0, ["Planet not found"]

    sign = planet_data['sign_index']
    degree = planet_data['degree']

    # Fetch rules
    rules = supabase.table("planet_strength_rules").select("*").eq("planet", planet).execute()
    if not rules.data:
        return 1.0, ["No strength rules found"]

    rule = rules.data[0]

    # Check own sign
    if sign in rule.get('own_signs', []):
        score *= 1.0
        factors.append(f"{planet} is in own sign")
    else:
        # Check friend/enemy via planet_friends table
        friends = supabase.table("planet_friends").select("friend_planet, relationship").eq("planet", planet).execute()
        # Need to get lord of the sign to determine friendship? Actually friend/enemy is between planets, not signs.
        # We'll need the sign lord first.
        lord_of_sign = get_sign_lord(sign)  # you need a function that returns planet name for a sign
        # Then lookup relationship between planet and that lord
        # For simplicity, we'll skip friend/enemy for now; you can expand later.
        pass

    # Exaltation
    if rule.get('exaltation_sign') == sign:
        # Exaltation degree may be exact or within orb (±5°?)
        ex_deg = rule.get('exaltation_degree')
        if ex_deg is not None and abs(degree - ex_deg) <= 5:  # orb 5°
            score *= 1.5
            factors.append(f"{planet} is exalted (within 5° of exact degree)")
        else:
            # Still in exaltation sign but not exact
            score *= 1.2
            factors.append(f"{planet} is in exaltation sign")

    # Debilitation
    if rule.get('debilitation_sign') == sign:
        deb_deg = rule.get('debilitation_degree')
        if deb_deg is not None and abs(degree - deb_deg) <= 5:
            score *= 0.5
            factors.append(f"{planet} is debilitated")
        else:
            score *= 0.8
            factors.append(f"{planet} is in debilitation sign (not exact)")

    # Combustion (within 8° of Sun)
    sun_data = chart_data['planets'].get('Sun')
    if sun_data and planet != 'Sun':
        sun_long = sun_data['longitude']
        planet_long = planet_data['longitude']
        diff = abs(planet_long - sun_long) % 360
        if diff < 8 or diff > 352:
            score *= 0.4
            factors.append(f"{planet} is combust (within 8° of Sun)")

    # Retrograde
    # Swiss Ephemeris provides retrograde flag; we don't have it in chart_data currently.
    # For now, skip.

    return score, factors

def check_neecha_bhanga(planet: str, chart_data: Dict[str, Any], supabase: Client) -> Tuple[bool, str]:
    """
    Determine if a debilitated planet has cancellation.
    Returns (bool, explanation).
    """
    # Get planet position
    planet_data = chart_data['planets'].get(planet)
    if not planet_data:
        return False, ""

    sign = planet_data['sign_index']
    degree = planet_data['degree']

    # Fetch rules
    rules = supabase.table("planet_strength_rules").select("*").eq("planet", planet).execute()
    if not rules.data:
        return False, ""
    rule = rules.data[0]

    # Check if planet is debilitated (exact or in sign)
    if rule.get('debilitation_sign') != sign:
        return False, f"{planet} is not debilitated."

    # Get debilitation degree
    deb_deg = rule.get('debilitation_degree')
    if deb_deg is not None and abs(degree - deb_deg) > 5:
        # Not exact, but still in sign; Neecha Bhanga can still apply.
        pass

    # Cancellation conditions:

    # 1. Dispositor of debilitated planet is in Kendra (1,4,7,10) from Lagna or Moon
    lagna = chart_data['lagna']['sign_index']
    moon_sign = chart_data['planets']['Moon']['sign_index']
    dispositor = get_sign_lord(sign)  # planet ruling the sign
    if dispositor:
        disp_pos = chart_data['planets'].get(dispositor)
        if disp_pos:
            disp_sign = disp_pos['sign_index']
            # Check if dispositor's sign is in Kendra from Lagna
            from_lagna = (disp_sign - lagna) % 12
            if from_lagna in [0,3,6,9]:  # 1st,4th,7th,10th houses (0-indexed)
                return True, f"Neecha Bhanga: Dispositor {dispositor} is in Kendra from Lagna."
            # Check from Moon
            from_moon = (disp_sign - moon_sign) % 12
            if from_moon in [0,3,6,9]:
                return True, f"Neecha Bhanga: Dispositor {dispositor} is in Kendra from Moon."

    # 2. Planet that would be exalted in this sign is in Kendra
    # For the sign of debilitation, which planet gets exalted there?
    # We need a table of exaltation by sign. Could query planet_strength_rules where exaltation_sign = sign.
    exalt_planet_result = supabase.table("planet_strength_rules").select("planet").eq("exaltation_sign", sign).execute()
    if exalt_planet_result.data:
        exalt_planet = exalt_planet_result.data[0]['planet']
        exalt_data = chart_data['planets'].get(exalt_planet)
        if exalt_data:
            exalt_sign = exalt_data['sign_index']
            from_lagna = (exalt_sign - lagna) % 12
            if from_lagna in [0,3,6,9]:
                return True, f"Neecha Bhanga: {exalt_planet} (exalted in this sign) is in Kendra from Lagna."
            from_moon = (exalt_sign - moon_sign) % 12
            if from_moon in [0,3,6,9]:
                return True, f"Neecha Bhanga: {exalt_planet} (exalted in this sign) is in Kendra from Moon."

    # 3. Debilitated planet is retrograde
    # If we have retrograde info, check; for now skip.

    return False, "No Neecha Bhanga found."

def get_sign_lord(sign_index: int) -> str:
    """Return planet name ruling a given sign (0-11)."""
    lords = ['Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury',
             'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter']
    return lords[sign_index]

def identify_yogas(chart_data: Dict[str, Any], supabase: Client) -> List[Dict[str, Any]]:
    """
    Identify which yogas are present in the chart.
    Returns list of yoga dicts with name, description, strength.
    """
    present_yogas = []
    lagna = chart_data['lagna']['sign_index']

    # Fetch all yoga rules
    yogas = supabase.table("yoga_rules").select("*").execute()
    for yoga in yogas.data:
        name = yoga['name']
        houses = yoga.get('houses_involved', [])
        planets = yoga.get('planets_involved', [])
        category = yoga.get('category')

        # Check each yoga condition (simplified)
        if name == 'Dhana Yoga':
            # Lords of 2 and 11 conjunct or aspect
            lord2 = get_sign_lord((lagna + 1) % 12)  # 2nd house sign
            lord11 = get_sign_lord((lagna + 10) % 12)  # 11th house sign
            pos2 = chart_data['planets'].get(lord2, {}).get('sign_index')
            pos11 = chart_data['planets'].get(lord11, {}).get('sign_index')
            if pos2 is not None and pos11 is not None:
                # Check conjunction: same sign
                if pos2 == pos11:
                    present_yogas.append({
                        'name': name,
                        'description': yoga['description'],
                        'strength': 1.0,
                        'category': category
                    })
                # Check mutual aspect (opposition or square etc.) – simplified: if signs are opposite (6 houses apart)
                elif (pos2 - pos11) % 12 == 6:
                    present_yogas.append({
                        'name': name,
                        'description': yoga['description'] + ' (mutual aspect)',
                        'strength': 0.8,
                        'category': category
                    })

        elif name in ['Hamsa Yoga', 'Malavya Yoga', 'Sasa Yoga', 'Ruchaka Yoga', 'Bhadra Yoga']:
            # Planet in own/exaltation in Kendra
            planet = yoga['planets_involved'][0]
            planet_data = chart_data['planets'].get(planet)
            if not planet_data:
                continue
            sign = planet_data['sign_index']
            # Check if sign is own or exalted
            rules = supabase.table("planet_strength_rules").select("*").eq("planet", planet).execute()
            if not rules.data:
                continue
            rule = rules.data[0]
            own = rule.get('own_signs', [])
            exalt_sign = rule.get('exaltation_sign')
            # Check if in Kendra
            from_lagna = (sign - lagna) % 12
            if from_lagna in [0,3,6,9]:  # 1,4,7,10
                if sign in own:
                    present_yogas.append({
                        'name': name,
                        'description': f"{planet} in own sign in Kendra",
                        'strength': 1.0,
                        'category': category
                    })
                elif sign == exalt_sign:
                    present_yogas.append({
                        'name': name,
                        'description': f"{planet} in exaltation in Kendra",
                        'strength': 1.2,
                        'category': category
                    })

        # Add more yoga checks as needed (Raja, Lakshmi, Kubera, etc.)

    return present_yogas
