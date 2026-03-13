# update_chart_lagna.py
import sys
from supabase import create_client
from antar_engine import chart, vimsottari, jaimini, utils
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

def update_chart_and_dashas(chart_id):
    # fetch chart record
    res = supabase.table("charts").select("*").eq("id", chart_id).execute()
    if not res.data:
        print("Chart not found")
        return
    rec = res.data[0]
    birth_date = rec['birth_date']
    birth_time = rec['birth_time'][:5]
    lat = rec['latitude']
    lon = rec['longitude']
    tz = rec['timezone_offset']

    # recompute chart with current chart.py
    chart_data = chart.calculate_chart(birth_date, birth_time, lat, lon, tz)
    new_lagna_sign = chart_data['lagna']['sign_index']
    new_lagna_deg = chart_data['lagna']['degree']

    # update the chart record
    supabase.table("charts").update({
        "lagna_sign": new_lagna_sign,
        "lagna_degree": new_lagna_deg,
        "chart_data": chart_data
    }).eq("id", chart_id).execute()
    print(f"Updated chart {chart_id} with Lagna {chart.SIGNS[new_lagna_sign]} at {new_lagna_deg:.2f}°")

    # delete old dashas
    supabase.table("dasha_periods").delete().eq("chart_id", chart_id).execute()
    print("Deleted old dashas")

    # compute birth JD
    dt_local = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    dt_utc = dt_local - timedelta(hours=tz)
    birth_jd = utils.julian_day(dt_utc)

    # store Vimsottari
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
    print(f"Stored {len(vim['mahadashas'])} Vimsottari dashas")

    # store Jaimini (using the correct Leo base table - you need to provide it)
    # For now, we'll use the placeholder; replace with correct table later
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
    print(f"Stored {len(jai['mahadashas'])} Jaimini dashas")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        update_chart_and_dashas(sys.argv[1])
    else:
        print("Usage: python update_chart_lagna.py <chart_id>")
