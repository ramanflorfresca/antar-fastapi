#!/usr/bin/env python3
"""
Verify a stored chart by recomputing dashas and divisional charts.
Date: 2026-03-10
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

from antar_engine import chart, vimsottari, jaimini, utils

# Import divisional directly
try:
    from antar_engine.divisional import calculate_divisional_chart
    HAS_DIVISIONAL = True
except ImportError as e:
    HAS_DIVISIONAL = False
    print(f"Note: divisional module not found ({e}). Skipping D-9/D-10 charts.")

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_chart(chart_id):
    result = supabase.table("charts").select("*").eq("id", chart_id).execute()
    if not result.data:
        print(f"Chart {chart_id} not found.")
        return None
    return result.data[0]

def fetch_dashas(chart_id):
    result = supabase.table("dasha_periods").select("*").eq("chart_id", chart_id).order("sequence").execute()
    return result.data

def print_divisional_chart(title, div_chart):
    """Print full divisional chart with all planets."""
    print(f"\n{title}")
    print(f"Lagna: {div_chart['lagna']['sign']} at {div_chart['lagna']['degree']:.2f}°")
    for planet, data in div_chart['planets'].items():
        print(f"  {planet}: {data['sign']} {data['degree']:.2f}°")

def main():
    chart_id = input("Enter chart ID: ").strip()
    chart_record = fetch_chart(chart_id)
    if not chart_record:
        return

    print(f"\n--- Stored Chart ---")
    print(f"Birth: {chart_record['birth_date']} {chart_record['birth_time']}")
    stored_lagna_sign = chart_record['lagna_sign']
    stored_lagna_deg = chart_record['lagna_degree']
    print(f"Stored Lagna: {chart.SIGNS[stored_lagna_sign]} at {stored_lagna_deg:.2f}° (sign index {stored_lagna_sign})")
    print(f"Stored Latitude: {chart_record['latitude']}, Longitude: {chart_record['longitude']}")

    # Parse birth time (may include seconds)
    birth_date = chart_record['birth_date']
    birth_time = chart_record['birth_time']
    if len(birth_time) > 5:
        birth_time = birth_time[:5]
    lat = chart_record['latitude']
    lon = chart_record['longitude']
    tz_offset = chart_record['timezone_offset']

    # Recompute chart using current chart.py
    print(f"\n--- Recomputing with current chart.py ---")
    recomputed_chart = chart.calculate_chart(birth_date, birth_time, lat, lon, tz_offset)
    recomputed_lagna_sign = recomputed_chart['lagna']['sign_index']
    recomputed_lagna_deg = recomputed_chart['lagna']['degree']
    print(f"Recomputed Lagna: {recomputed_chart['lagna']['sign']} at {recomputed_lagna_deg:.2f}° (sign index {recomputed_lagna_sign})")

    # Print full D-1 chart with nakshatras
    print("\n--- D-1 Chart (recomputed) ---")
    print(f"Lagna: {recomputed_chart['lagna']['sign']} at {recomputed_chart['lagna']['degree']:.2f}°")
    for planet, data in recomputed_chart['planets'].items():
        print(f"  {planet}: {data['sign']} {data['degree']:.2f}° (nakshatra {data['nakshatra']} - {data['nakshatra_lord']})")

    # Compute birth JD
    dt_local = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    dt_utc = dt_local - timedelta(hours=tz_offset)
    birth_jd = utils.julian_day(dt_utc)

    # Vimsottari (recomputed)
    vim = vimsottari.calculate_vimsottari_from_chart(recomputed_chart, birth_jd)
    print("\n--- Vimsottari Mahadashas (recomputed) ---")
    for md in vim['mahadashas'][:5]:
        print(f"{md['lord']:10s} {md['start_date'][:10]} → {md['end_date'][:10]} ({md['duration_years']:.2f} yrs)")

    # Jaimini (recomputed)
    jai = jaimini.calculate_chara_dasha_from_chart(recomputed_chart, birth_jd)
    print("\n--- Jaimini Mahadashas (recomputed) ---")
    for md in jai['mahadashas'][:5]:
        print(f"{md['sign']:10s} {md['start_date'][:10]} → {md['end_date'][:10]} ({md['duration_years']:.2f} yrs)")

    # Divisional charts
    if HAS_DIVISIONAL:
        try:
            d9 = calculate_divisional_chart(recomputed_chart, 9)
            print_divisional_chart("--- D-9 Navamsa (recomputed) ---", d9)
        except Exception as e:
            print(f"Error computing D-9: {e}")

        try:
            d10 = calculate_divisional_chart(recomputed_chart, 10)
            print_divisional_chart("--- D-10 Dasamsa (recomputed) ---", d10)
        except Exception as e:
            print(f"Error computing D-10: {e}")
    else:
        print("\nSkipping divisional charts (module not available).")

    # Fetch stored dashas for comparison
    stored = fetch_dashas(chart_id)
    print("\n--- Stored Dashas (from DB) ---")
    for sd in stored[:5]:
        print(f"{sd['planet_or_sign']:10s} {sd['start_date'][:10]} → {sd['end_date'][:10]} ({sd['duration_years']:.2f} yrs)")

    if stored and stored[1]['planet_or_sign'] == 'Leo' and stored[1]['duration_years'] == 7:
        print("\n✅ Stored dashas match recomputed values.")
    else:
        print("\n⚠️ Stored dashas may still be outdated. Run the update script if needed.")

    print("\nNote: Jaimini dashas for Leo Lagna are using placeholder base durations.")
    print("If the durations are incorrect (e.g., Gemini should be 2 years), please provide the correct 12-sign duration sequence for Leo Lagna (index 4) in order: Leo, Cancer, Gemini, Taurus, Aries, Pisces, Aquarius, Capricorn, Sagittarius, Scorpio, Libra, Virgo.")

if __name__ == "__main__":
    main()
