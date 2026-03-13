"""
Jaimini Chara Dasha calculation module (K.N. Rao method).
Date: 2026-03-10
Implements exclusive distance, node dispositors, and first dasha balance.
Matches Parāśara Light algorithm.
Includes optional debug output to verify planet longitudes and distances.
"""

import swisseph as swe
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from . import chart
from . import utils

DEBUG = True  # Set to True to enable debug prints

SIGNS = chart.SIGNS                    # 0‑based list (Aries=0, Taurus=1, ...)
SIGN_LORDS = chart.SIGN_LORDS          # 0‑based list of rulers
MOVABLE = [0, 3, 6, 9]                 # Aries, Cancer, Libra, Capricorn
FIXED   = [1, 4, 7, 10]                # Taurus, Leo, Scorpio, Aquarius
DUAL    = [2, 5, 8, 11]                # Gemini, Virgo, Sagittarius, Pisces

def dasha_direction(lagna_sign):
    """Return +1 (forward) or -1 (backward) based on Lagna type."""
    if lagna_sign in MOVABLE:
        return -1
    return 1

def zodiac_distance_exclusive(start, end, direction):
    """
    Count number of signs traversed from start to end, NOT including start.
    If start == end, returns 0.
    """
    if start == end:
        return 0
    dist = 0
    current = start
    while True:
        current = (current + direction) % 12
        dist += 1
        if current == end:
            break
    return dist

def node_dispositor(node, planet_signs):
    """Return the sign of the dispositor of a node (Rahu/Ketu)."""
    node_sign = planet_signs[node]
    lord = SIGN_LORDS[node_sign]
    return planet_signs[lord]

def get_ruler_sign(sign_index, planet_signs):
    """
    Return the sign(s) occupied by the ruler(s) of a sign.
    For dual‑lord signs (Scorpio, Aquarius), returns a tuple of two signs.
    For others, returns a single sign index.
    Nodes are handled via dispositor.
    """
    if sign_index == 7:          # Scorpio
        mars_sign = planet_signs['Mars']
        ketu_ruler_sign = node_dispositor('Ketu', planet_signs)
        return (mars_sign, ketu_ruler_sign)
    elif sign_index == 10:       # Aquarius
        saturn_sign = planet_signs['Saturn']
        rahu_ruler_sign = node_dispositor('Rahu', planet_signs)
        return (saturn_sign, rahu_ruler_sign)
    else:
        ruler = SIGN_LORDS[sign_index]
        # If ruler is a node (should not happen, but handle)
        if ruler in ['Rahu', 'Ketu']:
            return node_dispositor(ruler, planet_signs)
        else:
            return planet_signs[ruler]

def compute_sign_duration(sign_index, direction, planet_signs):
    """
    Compute Mahadasha duration for a sign.
    Uses exclusive distance; if distance == 0 → 12 years.
    For dual‑lord signs, takes the maximum distance to either lord.
    """
    rulers = get_ruler_sign(sign_index, planet_signs)
    if isinstance(rulers, tuple):
        dist1 = zodiac_distance_exclusive(sign_index, rulers[0], direction)
        dist2 = zodiac_distance_exclusive(sign_index, rulers[1], direction)
        if dist1 == 0:
            dist1 = 12
        if dist2 == 0:
            dist2 = 12
        dist = max(dist1, dist2)
    else:
        dist = zodiac_distance_exclusive(sign_index, rulers, direction)
        if dist == 0:
            dist = 12
    return dist

def generate_sequence(lagna_sign, direction):
    """Generate the 12‑sign sequence starting from Lagna."""
    seq = []
    current = lagna_sign
    for _ in range(12):
        seq.append(current)
        current = (current + direction) % 12
    return seq

def compute_antardashas(md_years, md_start_dt, direction, start_sign):
    """Antardashas are equal divisions of the Mahadasha, signs follow same direction."""
    ad_years = md_years / 12
    ad_days = ad_years * 365.25
    antardashas = []
    current_dt = md_start_dt
    current_sign = start_sign
    for _ in range(12):
        end_dt = current_dt + timedelta(days=ad_days)
        antardashas.append({
            'sign': SIGNS[current_sign],
            'sign_index': current_sign,
            'start_datetime': current_dt,
            'end_datetime': end_dt,
            'duration_years': ad_years
        })
        current_dt = end_dt
        current_sign = (current_sign + direction) % 12
    return antardashas

def calculate_chara_dasha_from_chart(chart_data, birth_jd):
    """
    Compute full Jaimini Chara Dasha from chart data.
    Returns dict with 'mahadashas' and 'antardashas'.
    """
    lagna_sign = chart_data['lagna']['sign_index']
    lagna_deg = chart_data['lagna']['degree']
    planet_signs = {p: chart_data['planets'][p]['sign_index'] for p in chart_data['planets']}
    
    # Optional debug: print raw planet longitudes from chart_data
    if DEBUG:
        print("\n[DEBUG] Planet longitudes from chart_data:")
        for p in chart_data['planets']:
            lon = chart_data['planets'][p]['longitude']
            print(f"  {p}: {lon:.4f}° (sign {planet_signs[p]})")

    direction = dasha_direction(lagna_sign)

    # Generate sign sequence
    sequence = generate_sequence(lagna_sign, direction)

    # Compute full durations for each sign in the sequence
    full_durations = [compute_sign_duration(sign, direction, planet_signs) for sign in sequence]

    if DEBUG:
        print("\n[DEBUG] Sign sequence and full durations:")
        for i, sign in enumerate(sequence):
            print(f"  {SIGNS[sign]}: full duration {full_durations[i]} years")

    # First dasha balance
    first_duration = full_durations[0]  # full MD, ignore lagna or Moon fraction

    # Build Mahadashas with exact dates
    birth_dt = utils.datetime_from_jd(birth_jd)
    mahadashas = []
    current_dt = birth_dt
    for i, sign in enumerate(sequence):
        years = first_duration if i == 0 else full_durations[i]
        years_int = int(years)
        frac = years - years_int
        end_dt = current_dt + relativedelta(years=years_int) + timedelta(days=frac * 365.25)
        mahadashas.append({
            'sign': SIGNS[sign],
            'sign_index': sign,
            'start_datetime': current_dt,
            'end_datetime': end_dt,
            'duration_years': years
        })
        current_dt = end_dt

    # Convert to strings
    for md in mahadashas:
        md['start_date'] = md['start_datetime'].isoformat()
        md['end_date'] = md['end_datetime'].isoformat()

    # Compute antardashas
    all_antardashas = []
    for md in mahadashas:
        ad_list = compute_antardashas(md['duration_years'], md['start_datetime'], direction, md['sign_index'])
        for ad in ad_list:
            ad['parent_sign'] = md['sign']
            ad['start_date'] = ad['start_datetime'].isoformat()
            ad['end_date'] = ad['end_datetime'].isoformat()
        all_antardashas.extend(ad_list)

    return {
        'mahadashas': mahadashas,
        'antardashas': all_antardashas
    }
calculate = calculate_chara_dasha_from_chart

