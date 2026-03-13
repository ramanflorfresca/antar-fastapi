#!/usr/bin/env python3
"""
Quick test script for Vimsottari and Jaimini dasha calculations.
Run as: python -m antar_engine.test_dashas
Date: 2026-03-10
"""

from datetime import datetime, timedelta
from . import chart, vimsottari, jaimini, utils

# ---------- Test birth data ----------
BIRTH_DATE = "1974-11-26"
BIRTH_TIME = "11:59"
LAT = 28.6139
LON = 77.2090
TZ_OFFSET = 5.5

def print_dashas(title, dashas_dict, max_md=5, max_ad=3):
    """Pretty print mahadashas and first few antardashas."""
    print(f"\n=== {title} ===")
    mds = dashas_dict['mahadashas']
    ads = dashas_dict['antardashas']

    print("\nMahadashas (first {}):".format(max_md))
    for i, md in enumerate(mds[:max_md]):
        lord_or_sign = md.get('lord') or md.get('sign', '?')
        print(f"  {i+1:2d}. {lord_or_sign:12s} "
              f"{md['start_date'][:10]} → {md['end_date'][:10]} "
              f"({md['duration_years']:.2f} yrs)")

    print("\nAntardashas (first few for first mahadasha):")
    if ads:
        parent_key = 'parent_lord' if 'parent_lord' in ads[0] else 'parent_sign'
        parent_value = mds[0].get('lord') or mds[0].get('sign')
        count = 0
        for ad in ads:
            if ad.get(parent_key) == parent_value:
                lord_or_sign = ad.get('lord') or ad.get('sign', '?')
                print(f"    {lord_or_sign:12s} "
                      f"{ad['start_date'][:10]} → {ad['end_date'][:10]} "
                      f"({ad['duration_years']:.2f} yrs)")
                count += 1
                if count >= max_ad:
                    break
    else:
        print("  (none)")

def main():
    print("Computing chart for birth data:")
    print(f"  {BIRTH_DATE} {BIRTH_TIME} UTC{'+' if TZ_OFFSET>=0 else ''}{TZ_OFFSET}")
    print(f"  Location: ({LAT}, {LON})")

    # Compute chart
    chart_data = chart.calculate_chart(BIRTH_DATE, BIRTH_TIME, LAT, LON, TZ_OFFSET)

    # Compute birth Julian day
    dt_local = datetime.strptime(f"{BIRTH_DATE} {BIRTH_TIME}", "%Y-%m-%d %H:%M")
    dt_utc = dt_local - timedelta(hours=TZ_OFFSET)
    birth_jd = utils.julian_day(dt_utc)

    # Vimsottari
    vim_result = vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)
    print(f"\nType of vim_result: {type(vim_result)}")
    if isinstance(vim_result, dict):
        print("Keys:", vim_result.keys())
    print_dashas("Vimsottari Dasha", vim_result)

    # Jaimini
    jai_result = jaimini.calculate_chara_dasha_from_chart(chart_data, birth_jd)
    print_dashas("Jaimini Chara Dasha", jai_result)

if __name__ == "__main__":
    main()
