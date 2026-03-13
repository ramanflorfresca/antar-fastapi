#!/usr/bin/env python3
"""
Test multiple birth charts to verify Vimsottari and Jaimini calculations.
Date: 2026-03-10
"""

from datetime import datetime, timedelta
from . import chart, vimsottari, jaimini, utils

# List of test cases: (birth_date, birth_time, lat, lon, tz_offset, description)
TEST_CASES = [
    ("1974-11-26", "11:59", 28.6139, 77.2090, 5.5, "Original test case"),
    ("1985-08-15", "14:30", 19.0760, 72.8777, 5.5, "Mumbai test"),
    ("1990-03-21", "06:15", 40.7128, -74.0060, -5.0, "New York"),
    # Add more as needed
]

def print_dashas_summary(title, dashas_dict, max_md=5):
    mds = dashas_dict['mahadashas']
    print(f"\n{title} (first {max_md}):")
    for i, md in enumerate(mds[:max_md]):
        lord_or_sign = md.get('lord') or md.get('sign', '?')
        print(f"  {i+1}. {lord_or_sign:12s} {md['start_date'][:10]} → {md['end_date'][:10]} ({md['duration_years']:.2f} yrs)")

def main():
    for idx, (bd, bt, lat, lon, tz, desc) in enumerate(TEST_CASES):
        print(f"\n{'='*60}")
        print(f"Test {idx+1}: {desc}")
        print(f"Birth: {bd} {bt} UTC{'+' if tz>=0 else ''}{tz}, ({lat}, {lon})")

        # Compute chart
        chart_data = chart.calculate_chart(bd, bt, lat, lon, tz)
        dt_local = datetime.strptime(f"{bd} {bt}", "%Y-%m-%d %H:%M")
        dt_utc = dt_local - timedelta(hours=tz)
        birth_jd = utils.julian_day(dt_utc)

        # Vimsottari
        vim = vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)
        print_dashas_summary("Vimsottari", vim)

        # Jaimini
        jai = jaimini.calculate_chara_dasha_from_chart(chart_data, birth_jd)
        print_dashas_summary("Jaimini", jai)

if __name__ == "__main__":
    main()
