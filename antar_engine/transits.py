"""
Transit calculation module.
Date: 2026-03-10
Computes current planetary positions and aspects to natal chart.
Uses the same ayanamsa as the chart (Lahiri default).
"""

import swisseph as swe
from datetime import datetime, timedelta
from . import utils
from . import constants

# Planet list (including nodes)
PLANETS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']

def get_current_positions(jd_utc, ayanamsa_mode=1):
    """
    Get sidereal positions of all planets at a given Julian day.
    Returns dict {planet: {'longitude': lon, 'sign_index': si, 'degree': deg, 'nakshatra': nak, 'nakshatra_lord': lord}}
    """
    swe.set_sid_mode(ayanamsa_mode)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    positions = {}
    for planet in PLANETS:
        if planet == 'Rahu':
            lon, _ = swe.calc_ut(jd_utc, swe.TRUE_NODE, flags=flags)
            lon_deg = lon[0]
        elif planet == 'Ketu':
            lon_rahu, _ = swe.calc_ut(jd_utc, swe.TRUE_NODE, flags=flags)
            lon_deg = (lon_rahu[0] + 180) % 360
        else:
            p = getattr(swe, planet.upper())
            lon, _ = swe.calc_ut(jd_utc, p, flags=flags)
            lon_deg = lon[0]
        sign_idx = int(lon_deg / 30)
        deg_in_sign = lon_deg - sign_idx * 30
        # Nakshatra
        nak_deg = 360 / 27
        nak_idx = int(lon_deg / nak_deg)
        if nak_idx >= 27:
            nak_idx = 26
        nak_lord = constants.NAKSHATRA_LORDS[nak_idx]
        positions[planet] = {
            'longitude': lon_deg,
            'sign_index': sign_idx,
            'degree': deg_in_sign,
            'nakshatra': constants.NAKSHATRAS[nak_idx],
            'nakshatra_lord': nak_lord
        }
    return positions

def calculate_transits(natal_chart, target_date=None, ayanamsa_mode=1):
    """
    Compare current planetary positions to natal positions.
    Returns a list of transit events, each with planet, transit_house, aspects, etc.
    """
    if target_date is None:
        target_date = datetime.utcnow()
    jd_target = utils.julian_day(target_date)

    current = get_current_positions(jd_target, ayanamsa_mode)

    # Natal data
    natal_lagna = natal_chart['lagna']['sign_index']
    natal_planets = natal_chart['planets']

    transits = []
    for planet, cur in current.items():
        if planet not in natal_planets:
            continue
        natal = natal_planets[planet]
        # House of transit relative to natal Lagna
        transit_house = (cur['sign_index'] - natal_lagna + 12) % 12 + 1
        # Whether planet is transiting over its natal position (within 1° orb)
        orb = 1.0
        lon_diff = abs(cur['longitude'] - natal['longitude'])
        if lon_diff > 180:
            lon_diff = 360 - lon_diff
        is_conjunct_natal = lon_diff <= orb
        # Major aspects (simplified)
        aspects = []
        # Check opposition (180° ± orb)
        opp = (natal['longitude'] + 180) % 360
        if abs(cur['longitude'] - opp) <= orb or abs(cur['longitude'] - opp - 360) <= orb:
            aspects.append('opposition')
        # Check square (90° ± orb)
        sq1 = (natal['longitude'] + 90) % 360
        sq2 = (natal['longitude'] + 270) % 360
        if abs(cur['longitude'] - sq1) <= orb or abs(cur['longitude'] - sq1 - 360) <= orb or \
           abs(cur['longitude'] - sq2) <= orb or abs(cur['longitude'] - sq2 - 360) <= orb:
            aspects.append('square')
        # Check trine (120° ± orb)
        tri1 = (natal['longitude'] + 120) % 360
        tri2 = (natal['longitude'] + 240) % 360
        if abs(cur['longitude'] - tri1) <= orb or abs(cur['longitude'] - tri1 - 360) <= orb or \
           abs(cur['longitude'] - tri2) <= orb or abs(cur['longitude'] - tri2 - 360) <= orb:
            aspects.append('trine')
        # Check sextile (60° ± orb)
        sex1 = (natal['longitude'] + 60) % 360
        sex2 = (natal['longitude'] + 300) % 360
        if abs(cur['longitude'] - sex1) <= orb or abs(cur['longitude'] - sex1 - 360) <= orb or \
           abs(cur['longitude'] - sex2) <= orb or abs(cur['longitude'] - sex2 - 360) <= orb:
            aspects.append('sextile')

        transits.append({
            'planet': planet,
            'transit_sign': constants.SIGNS[cur['sign_index']],
            'transit_degree': cur['degree'],
            'transit_house': transit_house,
            'natal_sign': natal['sign'],
            'natal_degree': natal['degree'],
            'conjunct_natal': is_conjunct_natal,
            'aspects': aspects
        })
    return transits

def summarize_transits(transits, max_planets=5):
    """Return a short textual summary of key transits."""
    lines = []
    for t in transits[:max_planets]:
        aspects = ', '.join(t['aspects']) if t['aspects'] else 'no major aspects'
        conj = " (conjunct natal)" if t['conjunct_natal'] else ""
        lines.append(f"{t['planet']} in {t['transit_sign']} house {t['transit_house']}{conj} – {aspects}.")
    return "\n".join(lines)
