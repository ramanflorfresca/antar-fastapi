"""
Vimsottari Dasha calculation module.
Date: 2026-03-10
Includes mahadasha and antardasha (sub‑period) computation using exact calendar arithmetic.
"""

import swisseph as swe
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import math
from . import utils
from . import constants

DASHA_SEQUENCE = constants.VIMSOTTARI_SEQUENCE
DASHA_LENGTHS = constants.VIMSOTTARI_YEARS
NAKSHATRA_LORDS = constants.NAKSHATRA_LORDS


# ---------- Core Computation Functions ----------
def compute_vimsottari_mahadashas(moon_nakshatra_idx, birth_jd):
    start_lord = NAKSHATRA_LORDS[moon_nakshatra_idx]
    start_idx = DASHA_SEQUENCE.index(start_lord)

    dashas = []
    current_jd = birth_jd
    total_years = 0
    cycle_idx = start_idx
    while total_years < 120:
        lord = DASHA_SEQUENCE[cycle_idx % 9]
        duration = DASHA_LENGTHS[lord]
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
    total_years = mahadasha_duration
    start_idx = DASHA_SEQUENCE.index(mahadasha_lord)
    antardashas = []
    current_jd = mahadasha_start_jd
    for i in range(9):
        lord = DASHA_SEQUENCE[(start_idx + i) % 9]
        lord_years = DASHA_LENGTHS[lord]
        ad_years = (lord_years / 120) * total_years
        end_jd = current_jd + ad_years * 365.25
        antardashas.append({
            'lord': lord,
            'start_jd': current_jd,
            'end_jd': end_jd,
            'duration_years': ad_years
        })
        current_jd = end_jd
    return antardashas


# ---------- Chart-Based Wrapper ----------
def calculate_vimsottari_from_chart(chart_data, birth_jd):
    """
    Compute full Vimsottari mahadashas and antardashas from chart data.
    Returns dict with mahadashas and antardashas, each containing datetime fields.
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
    mahadashas = compute_vimsottari_mahadashas(moon_nakshatra_idx, birth_jd)

    # Adjust first mahadasha balance
    first_duration = mahadashas[0]['duration_years'] * (1 - portion_elapsed)
    mahadashas[0]['duration_years'] = first_duration
    mahadashas[0]['end_jd'] = mahadashas[0]['start_jd'] + first_duration * 365.25

    # Recalculate subsequent start/end
    for i in range(1, len(mahadashas)):
        mahadashas[i]['start_jd'] = mahadashas[i-1]['end_jd']
        mahadashas[i]['end_jd'] = mahadashas[i]['start_jd'] + mahadashas[i]['duration_years'] * 365.25

    # Convert birth_jd to datetime for exact timeline
    birth_dt = utils.datetime_from_jd(birth_jd)
    current_dt = birth_dt
    mahadashas_exact = []

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
    # Rule: antardasha sequence within a mahadasha STARTS from the mahadasha lord
    all_antardashas = []
    for md in mahadashas_exact:
        total_seconds = (md['end_datetime'] - md['start_datetime']).total_seconds()
        start_dt = md['start_datetime']
        # Find starting index for this mahadasha lord
        md_start_idx = DASHA_SEQUENCE.index(md['lord'])
        for i in range(9):
            lord = DASHA_SEQUENCE[(md_start_idx + i) % 9]
            lord_years = DASHA_LENGTHS[lord]
            ad_years = (lord_years / 120) * md['duration_years']
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

    # Convert to ISO strings for JSON
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

calculate = calculate_vimsottari_from_chart   # alias for main.py

