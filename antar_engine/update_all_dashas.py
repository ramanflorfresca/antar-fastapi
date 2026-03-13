#!/usr/bin/env python3
"""
update_all_dashas.py
Iterates over all charts in the database and recomputes/updates their dashas
using the current vimsottari.py, jaimini.py, and ashtottari.py.
Date: 2026-03-10
"""

import sys
from supabase import create_client
from antar_engine import chart, vimsottari, jaimini, ashtottari, utils
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

def update_chart_dashas(chart_id):
    """Recompute and store dashas for a single chart."""
    # fetch chart record
    res = supabase.table("charts").select("*").eq("id", chart_id).execute()
    if not res.data:
        print(f"Chart {chart_id} not found.")
        return
    rec = res.data[0]
    birth_date = rec['birth_date']
    birth_time = rec['birth_time'][:5]  # truncate seconds if present
    lat = rec['latitude']
    lon = rec['longitude']
    tz = rec['timezone_offset']
    chart_data = rec['chart_data']

    dt_local = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    dt_utc = dt_local - timedelta(hours=tz)
    birth_jd = utils.julian_day(dt_utc)

    # delete existing dashas for this chart
    supabase.table("dasha_periods").delete().eq("chart_id", chart_id).execute()
    print(f"Deleted old dashas for chart {chart_id}")

    # store new Vimsottari
    vim = vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)
    for seq, md in enumerate(vim['mahadashas']):
        supabase.table("dasha_periods").insert({
            "chart_id": chart_id,
            "system": "vimsottari",
            "type": "mahadasha",
            "level": 1,
            "sequence": seq,
            "planet_or_sign": md['lord'],
            "start_date": md['start_date'],
            "end_date": md['end_date'],
            "duration_years": md['duration_years'],
            "metadata": {},
            "parent_id": None
        }).execute()
    print(f"  Stored {len(vim['mahadashas'])} Vimsottari dashas")

    # store new Jaimini
    jai = jaimini.calculate_chara_dasha_from_chart(chart_data, birth_jd)
    for seq, md in enumerate(jai['mahadashas']):
        supabase.table("dasha_periods").insert({
            "chart_id": chart_id,
            "system": "jaimini",
            "type": "mahadasha",
            "level": 1,
            "sequence": seq,
            "planet_or_sign": md['sign'],
            "start_date": md['start_date'],
            "end_date": md['end_date'],
            "duration_years": md['duration_years'],
            "metadata": {},
            "parent_id": None
        }).execute()
    print(f"  Stored {len(jai['mahadashas'])} Jaimini dashas")

    # store new Ashtottari
    ast = ashtottari.calculate_ashtottari_from_chart(chart_data, birth_jd)
    for seq, md in enumerate(ast['mahadashas']):
        supabase.table("dasha_periods").insert({
            "chart_id": chart_id,
            "system": "ashtottari",
            "type": "mahadasha",
            "level": 1,
            "sequence": seq,
            "planet_or_sign": md['lord'],
            "start_date": md['start_date'],
            "end_date": md['end_date'],
            "duration_years": md['duration_years'],
            "metadata": {},
            "parent_id": None
        }).execute()
    print(f"  Stored {len(ast['mahadashas'])} Ashtottari dashas")

def main():
    # Fetch all chart IDs
    result = supabase.table("charts").select("id").execute()
    if not result.data:
        print("No charts found in database.")
        return

    chart_ids = [row['id'] for row in result.data]
    print(f"Found {len(chart_ids)} charts to update.")

    for idx, cid in enumerate(chart_ids):
        print(f"\n[{idx+1}/{len(chart_ids)}] Processing chart {cid}")
        try:
            update_chart_dashas(cid)
        except Exception as e:
            print(f"ERROR on chart {cid}: {e}")
            # optionally continue or break

    print("\nAll charts processed.")

if __name__ == "__main__":
    main()
