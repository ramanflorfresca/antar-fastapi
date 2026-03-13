#!/usr/bin/env python3
"""
Load test birth data from a CSV file, compute charts and dashas,
and store them in Supabase.
Date: 2026-03-10
"""

import csv
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

# Import antar_engine modules
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from antar_engine import chart, vimsottari, jaimini, utils

load_dotenv()

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Optional test user ID
TEST_USER_ID = None

def store_chart_and_dashas(row):
    """Process one birth record and store in DB."""
    birth_date = row['birth_date']
    birth_time = row['birth_time']
    lat = float(row['latitude'])
    lon = float(row['longitude'])
    tz_offset = float(row['timezone_offset'])
    description = row.get('description', '')

    # Compute chart
    chart_data = chart.calculate_chart(birth_date, birth_time, lat, lon, tz_offset)

    # Compute birth Julian day
    dt_local = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    dt_utc = dt_local - timedelta(hours=tz_offset)
    birth_jd = utils.julian_day(dt_utc)

    # Insert chart
    chart_insert = {
        "user_id": TEST_USER_ID,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "latitude": lat,
        "longitude": lon,
        "timezone_offset": tz_offset,
        "lagna_sign": chart_data["lagna"]["sign_index"],
        "lagna_degree": chart_data["lagna"]["degree"],
        "chart_data": chart_data,
    }
    result = supabase.table("charts").insert(chart_insert).execute()
    chart_id = result.data[0]["id"]
    print(f"Inserted chart {chart_id} for {birth_date} {birth_time} ({description})")

    # Compute Vimsottari dashas
    vim_result = vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)
    store_mahadashas(chart_id, "vimsottari", vim_result['mahadashas'])

    # Compute Jaimini dashas
    jai_result = jaimini.calculate_chara_dasha_from_chart(chart_data, birth_jd)
    store_mahadashas(chart_id, "jaimini", jai_result['mahadashas'])

    print(f"  -> Stored dashas")

def store_mahadashas(chart_id, system, mahadashas):
    """Insert mahadashas into dasha_periods table."""
    records = []
    for seq, md in enumerate(mahadashas):
        record = {
            "chart_id": chart_id,
            "system": system,
            "type": "mahadasha",
            "level": 1,
            "sequence": seq,
            "planet_or_sign": md.get('lord') or md.get('sign'),
            "start_date": md['start_date'],
            "end_date": md['end_date'],
            "duration_years": md['duration_years'],
            "metadata": {},
            "parent_id": None
        }
        records.append(record)
    if records:
        supabase.table("dasha_periods").insert(records).execute()

def main():
    # Path to your CSV file (adjust if needed)
    csv_file = "antar_engine/test_births.csv"
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            store_chart_and_dashas(row)

if __name__ == "__main__":
    main()
