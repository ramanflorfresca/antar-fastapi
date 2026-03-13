"""
Ashtottari Dasha calculation module.
Date: 2026-03-10
Based on 8‑lord cycle: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu.
Nakshatra lords are assigned in a repeating cycle starting from Ashvini.
"""

import pyswisseph as swe
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from . import utils
from . import constants

# Ashtottari sequence and years (in order)
ASHTOTTARI_SEQUENCE = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu']
ASHTOTTARI_YEARS = {
    'Sun': 6,
    'Moon': 15,
    'Mars': 8,
    'Mercury': 17,
    'Jupiter': 19,
    'Venus': 21,
    'Saturn': 24,
    'Rahu': 12
}

# Nakshatra lords for Ashtottari (27 nakshatras, cycle of 8 lords starting from Ashvini)
# This mapping is commonly used: Ashvini → Sun, Bharani → Moon, Krittika → Mars, etc.
ASHTOTTARI_NAKSHATRA_LORDS = []
for i in range(27):
    ASHTOTTARI_NAKSHATRA_LORDS.append(ASHTOTTARI_SEQUENCE[i % 8])

def compute_ashtottari_mahadashas(moon_nakshatra_idx, birth_jd):
    """
    Compute Ashtottari mahadashas starting from birth.
    Returns list of dicts with keys: lord, start_jd, end_jd, duration_years.
    """
    start_lord = ASHTOTTARI_NAKSHATRA_LORDS[moon_nakshatra_idx]
    start_idx = ASHTOTTARI_SEQUENCE.index(start_lord)

    dashas = []
    current_jd = birth_jd
    total_years = 0
    cycle_idx = start_idx
    while total_years < 122:  # approximate total (sum of years)
        lord = ASHTOTTARI_SEQUENCE[cycle_idx % 8]
        duration = ASHTOTTARI_YEARS[lord]
        dasha = {
            'lord': lord,
            'start_jd': current_jd,
            'duration_years': duration
        }
        dasha['end_jd'] = current_jd + duration * 365.25
        dashas.append(dasha)
        current_jd = dasha['end_jd']
        total_years += duration
        cycle_idx += 1
    return dashas

def compute_antardashas(mahadasha_lord, mahadasha_start_jd, mahadasha_duration):
    """
    Compute antardashas (sub‑periods) within a given mahadasha.
    For Ashtottari, the antardasha sequence is the same as the mahadasha sequence,
    and the duration is proportional to the lord's years over total cycle.
    """
    total_years = mahadasha_duration
    start_idx = ASHTOTTARI_SEQUENCE.index(mahadasha_lord)
    antardashas = []
    current_jd = mahadasha_start_jd
    for i in range(8):
        lord = ASHTOTTARI_SEQUENCE[(start_idx + i) % 8]
        lord_years = ASHTOTTARI_YEARS[lord]
        ad_years = (lord_years / sum(ASHTOTTARI_YEARS.values())) * total_years
        end_jd = current_jd + ad_years * 365.25
        antardashas.append({
            'lord': lord,
            'start_jd': current_jd,
            'end_jd': end_jd,
            'duration_years': ad_years
        })
        current_jd = end_jd
    return antardashas

def calculate_ashtottari_from_chart(chart_data, birth_jd):
    """
    Compute full Ashtottari mahadashas and antardashas from chart data.
    Returns dict with 'mahadashas' and 'antardashas'.
    """
    moon_data = chart_data['planets']['Moon']
    moon_nakshatra_idx = moon_data.get('nakshatra_index')
    if moon_nakshatra_idx is None:
        moon_long = moon_data['longitude']
        nakshatra_deg = 360 / 27
        moon_nakshatra_idx = int(moon_long / nakshatra_deg)
        if moon_nakshatra_idx >= 27:
            moon_nakshatra_idx = 26
        portion_elapsed = (moon_long - moon_nakshatra_idx * nakshatra_deg) / nakshatra_deg
    else:
        portion_elapsed = moon_data.get('nakshatra_portion', 0.5)

    # Compute full mahadashas (unadjusted)
    mahadashas = compute_ashtottari_mahadashas(moon_nakshatra_idx, birth_jd)

    # Adjust first mahadasha balance
    first_duration = mahadashas[0]['duration_years'] * (1 - portion_elapsed)
    mahadashas[0]['duration_years'] = first_duration
    mahadashas[0]['end_jd'] = mahadashas[0]['start_jd'] + first_duration * 365.25

    # Recalculate subsequent start/end
    for i in range(1, len(mahadashas)):
        mahadashas[i]['start_jd'] = mahadashas[i-1]['end_jd']
        mahadashas[i]['end_jd'] = mahadashas[i]['start_jd'] + mahadashas[i]['duration_years'] * 365.25

    # Convert to exact datetimes
    birth_dt = utils.datetime_from_jd(birth_jd)
    mahadashas_exact = []
    current_dt = birth_dt
    for md in mahadashas:
        years = md['duration_years']
        years_int = int(years)
        frac = years - years_int
        end_dt = current_dt + relativedelta(years=years_int) + timedelta(days=frac * 365.25)
        md_exact = {
            'lord': md['lord'],
            'start_datetime': current_dt,
            'end_datetime': end_dt,
            'duration_years': years
        }
        mahadashas_exact.append(md_exact)
        current_dt = end_dt

    # Compute antardashas
    all_antardashas = []
    for md in mahadashas_exact:
        total_seconds = (md['end_datetime'] - md['start_datetime']).total_seconds()
        start_dt = md['start_datetime']
        for i, lord in enumerate(ASHTOTTARI_SEQUENCE):
            lord_years = ASHTOTTARI_YEARS[lord]
            ad_years = (lord_years / sum(ASHTOTTARI_YEARS.values())) * md['duration_years']
            ad_seconds = total_seconds * (ad_years / md['duration_years'])
            ad_end = start_dt + timedelta(seconds=ad_seconds)
            ad = {
                'lord': lord,
                'start_datetime': start_dt,
                'end_datetime': ad_end,
                'duration_years': ad_years,
                'parent_lord': md['lord']
            }
            all_antardashas.append(ad)
            start_dt = ad_end

    # Convert to strings
    for md in mahadashas_exact:
        md['start_date'] = md['start_datetime'].isoformat()
        md['end_date'] = md['end_datetime'].isoformat()
    for ad in all_antardashas:
        ad['start_date'] = ad['start_datetime'].isoformat()
        ad['end_date'] = ad['end_datetime'].isoformat()

    return {
        'mahadashas': mahadashas_exact,
        'antardashas': all_antardashas
    }

calculate = calculate_ashtottari_from_chart
