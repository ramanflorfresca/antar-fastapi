"""
timing_engine.py
Enhanced timing engine for Antar.
Provides functions to compute upcoming dashas, transits, their impact weights,
and dasha‑transit confluence scores.
Date: 2026-03-10
"""

import swisseph as swe
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from . import utils
from . import constants

# List of planets to track sign changes (Sun, Moon, Jupiter, Saturn, Rahu, Ketu)
KEY_PLANETS = ['Sun', 'Moon', 'Jupiter', 'Saturn', 'Rahu', 'Ketu']


# ---------- Transit Sign Change Calculation ----------
def next_sign_change(planet, start_jd, direction=1, ayanamsa_mode=1):
    """
    Find the next Julian day when the planet enters a new sign (i.e., crosses a multiple of 30°).
    Returns (ingress_jd, new_sign_index).
    Uses binary search for efficiency.
    """
    swe.set_sid_mode(ayanamsa_mode)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

    # Helper to get planet longitude
    def get_lon(jd):
        if planet == 'Rahu':
            lon, _ = swe.calc_ut(jd, swe.TRUE_NODE, flags=flags)
            return lon[0]
        elif planet == 'Ketu':
            lon_rahu, _ = swe.calc_ut(jd, swe.TRUE_NODE, flags=flags)
            return (lon_rahu[0] + 180) % 360
        else:
            p = getattr(swe, planet.upper())
            lon, _ = swe.calc_ut(jd, p, flags=flags)
            return lon[0]

    # Current longitude
    lon0 = get_lon(start_jd)
    current_sign = int(lon0 / 30)
    next_boundary = (current_sign + 1) * 30

    # Coarse search
    step = 1 if planet == 'Moon' else 10
    jd = start_jd
    max_days = 2 * 365
    found = False
    while (jd - start_jd) < max_days:
        lon = get_lon(jd)
        if lon >= next_boundary:
            found = True
            break
        jd += step
    if not found:
        return None, None

    # Binary search refinement
    low = jd - step
    high = jd
    for _ in range(10):
        mid = (low + high) / 2
        lon = get_lon(mid)
        if lon < next_boundary:
            low = mid
        else:
            high = mid
    ingress_jd = (low + high) / 2
    new_sign = (current_sign + 1) % 12
    return ingress_jd, new_sign


# ---------- Transit Impact Weighting ----------
def get_transit_impact(planet: str, transit_sign: int, natal_planet: str, natal_sign: int, supabase) -> dict:
    """
    Return impact weight and description for a given transit.
    Queries the transit_impact table (or uses hard‑coded rules for key transits).
    Returns dict with 'weight', 'description', 'duration'.
    """
    # Hard‑coded major transits (you can extend by querying a database table)
    if planet == 'Saturn' and natal_planet == 'Moon':
        # Sade Sati: Saturn transiting Moon sign ±1
        natal_moon_sign = natal_sign
        if transit_sign in [(natal_moon_sign - 1) % 12, natal_moon_sign, (natal_moon_sign + 1) % 12]:
            return {'weight': 10.0, 'description': 'Sade Sati – major karmic period', 'duration': '2.5 years per phase'}

    if planet == 'Jupiter' and natal_planet == 'Lagna':
        lagna_sign = natal_sign
        if transit_sign == lagna_sign:
            return {'weight': 8.0, 'description': 'Jupiter over Lagna – expansion and opportunities', 'duration': '~1 year'}

    if planet == 'Saturn' and natal_planet == 'Saturn':
        if transit_sign == natal_sign:
            return {'weight': 9.0, 'description': 'Saturn return – life restructuring', 'duration': '~1 year'}

    if planet == 'Jupiter' and natal_planet == 'Jupiter':
        if transit_sign == natal_sign:
            return {'weight': 7.0, 'description': 'Jupiter return – renewal of faith and growth', 'duration': '~1 year'}

    # For other transits, you could query a database table (transit_impact) here.
    # Example: result = supabase.table("transit_impact").select(...).execute()
    # For now, return neutral.
    return {'weight': 1.0, 'description': '', 'duration': ''}


# ---------- Ashtakavarga (Stub) ----------
def get_ashtakavarga_points(planet: str, sign: int, supabase) -> int:
    """
    Return the number of points (bindus) for a planet in a given sign.
    For full implementation, you would query the ashtakavarga table.
    Stub: returns 4 (average) for now.
    """
    # TODO: implement actual ashtakavarga query
    return 4

def compute_transit_strength(transit_planet: str, transit_sign: int, supabase) -> float:
    """
    Compute strength of a transit based on Ashtakavarga points.
    Returns a multiplier (e.g., 1.0 = neutral, >1 = strong, <1 = weak).
    """
    points = get_ashtakavarga_points(transit_planet, transit_sign, supabase)
    if points >= 5:
        return 1.5
    elif points <= 2:
        return 0.5
    else:
        return 1.0


# ---------- Upcoming Windows ----------
def upcoming_dasha_windows(dashas_list, current_dt):
    """
    Given a list of mahadashas (from database response), return those starting after current_dt.
    Each dasha dict should have keys: 'lord_or_sign', 'start', 'end', 'duration'.
    """
    _now = current_dt.replace(tzinfo=None) if current_dt.tzinfo else current_dt
    windows = []
    for md in dashas_list:
        try:
            start = datetime.fromisoformat(str(md['start'])[:10])
        except Exception:
            continue
        if start > _now:
            windows.append({
                'type': 'mahadasha',
                'sign': md['lord_or_sign'],
                'start': md['start'],
                'end': md['end'],
                'duration': md.get('duration_years', md.get('duration', ''))
            })
    return windows[:5]

def upcoming_transit_windows(chart_data, current_dt=None, look_ahead_years=2):
    """
    Identify sign changes of key planets in the next `look_ahead_years`.
    Returns a list of windows (each with description, start date, end date).
    """
    if current_dt is None:
        current_dt = datetime.now(timezone.utc)
    jd_now = utils.julian_day(current_dt)
    windows = []

    for planet in KEY_PLANETS:
        ingress_jd, new_sign = next_sign_change(planet, jd_now)
        if ingress_jd is None:
            continue
        ingress_dt = utils.datetime_from_jd(ingress_jd)
        if ingress_dt - current_dt <= timedelta(days=look_ahead_years*365):
            sign_name = constants.SIGNS[new_sign]
            windows.append({
                'type': 'transit',
                'description': f"{planet} enters {sign_name}",
                'start': ingress_dt.isoformat()[:10],
                'end': ingress_dt.isoformat()[:10]  # same day
            })
    windows.sort(key=lambda x: x['start'])
    return windows[:5]


# ---------- Confluence Scoring ----------
def compute_confluence_score(dashas: dict, transits: list, supabase) -> (float, list):
    """
    Compute a confluence score based on current dashas and active transits.
    Higher score = more powerful alignment.
    Returns (score, list_of_factors).
    """
    score = 1.0
    factors = []

    # Get current mahadasha lord (from dashas_response)
    vim = dashas.get('vimsottari', [])
    if not vim:
        return score, factors
    current_md_lord = vim[0].get('lord_or_sign')  # assuming first is current

    # For each transit, check if it involves the same planet or has high weight
    for t in transits:
        planet = t['planet']
        # If transit planet is the same as mahadasha lord, amplify
        if planet == current_md_lord:
            score += 2.0
            factors.append(f"{planet} transit aligns with your {planet} Mahadasha – powerful period")

        # Check specific high‑impact transits using get_transit_impact
        # For simplicity, we'll just use the description we may have added elsewhere.
        # Alternatively, we could compute impact here.
        # For now, we'll check for Sade Sati based on transit data.
        if planet == 'Saturn' and 'Sade Sati' in t.get('description', ''):
            score += 5.0
            factors.append("Sade Sati active – major karmic focus")
        if planet == 'Jupiter' and t.get('transit_house') == 1:  # Jupiter over Lagna
            score += 3.0
            factors.append("Jupiter over Lagna – expansion peak")

        # Ashtakavarga strength
        strength = compute_transit_strength(planet, t.get('sign_index', 0), supabase)
        if strength > 1.2:
            score += 0.5
            factors.append(f"{planet} transit is strong (Ashtakavarga {strength:.1f}x)")
        elif strength < 0.8:
            score -= 0.5
            factors.append(f"{planet} transit is weak – need extra effort")

    # Clamp score to reasonable range
    if score < 0.1:
        score = 0.1
    if score > 10:
        score = 10
    return score, factors


# ---------- Main Insights ----------
def timing_insights(chart_data, dashas_dict, current_dt=None, supabase=None):
    """
    Generate a summary of upcoming astrological events for the prompt.
    Optionally include confluence factors if supabase client is provided.
    """
    if current_dt is None:
        current_dt = datetime.now(timezone.utc)

    # Use Vimsottari dashas for upcoming periods
    vim_dashas = dashas_dict.get('vimsottari', [])
    dasha_windows = upcoming_dasha_windows(vim_dashas, current_dt)

    transit_windows = upcoming_transit_windows(chart_data, current_dt)

    lines = []
    if dasha_windows:
        lines.append("Upcoming Mahadashas:")
        for w in dasha_windows[:3]:
            lines.append(f"  - {w['sign']} from {w['start'][:10]} to {w['end'][:10]} ({w['duration']} years)")

    if transit_windows:
        lines.append("Notable planetary sign changes:")
        for t in transit_windows:
            lines.append(f"  - {t['description']} on {t['start']}")

    # If supabase client provided, compute confluence and add factors
    if supabase:
        conf_score, conf_factors = compute_confluence_score(dashas_dict, transit_windows, supabase)
        if conf_factors:
            lines.append("Current transit‑dasha confluence:")
            for f in conf_factors[:3]:
                lines.append(f"  - {f}")
        # You could also return the score separately if needed

    return "\n".join(lines)
