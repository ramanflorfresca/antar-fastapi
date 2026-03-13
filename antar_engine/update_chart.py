# quick_fix.py
import sys
from supabase import create_client
from antar_engine import chart, vimsottari, jaimini, utils
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

chart_id = '23ad82e9-b04a-4d67-af95-f64f4f11c54c'
birth_date = '1972-08-10'
birth_time = '07:20'
lat = 28.6139
lon = 77.2090
tz = 5.5

chart_data = chart.calculate_chart(birth_date, birth_time, lat, lon, tz)
new_lagna_sign = chart_data['lagna']['sign_index']
new_lagna_deg = chart_data['lagna']['degree']

supabase.table("charts").update({
    "lagna_sign": new_lagna_sign,
    "lagna_degree": new_lagna_deg,
    "chart_data": chart_data
}).eq("id", chart_id).execute()

print("Chart updated. Now delete old dashas and recompute...")
