#!/usr/bin/env python3
# test_jaimini.py – quick test for Jaimini calculations

from datetime import datetime, timedelta
from antar_engine import chart, jaimini, utils

# Birth details (change as needed)
birth_date = "1972-12-14"
birth_time = "11:30"
latitude = 28.6139   # New Delhi
longitude = 77.2090
tz_offset = 5.5

# Compute chart
chart_data = chart.calculate_chart(birth_date, birth_time, latitude, longitude, tz_offset)

# Compute birth JD
dt_local = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
dt_utc = dt_local - timedelta(hours=tz_offset)
birth_jd = utils.julian_day(dt_utc)

# Compute Jaimini dashas
jai = jaimini.calculate_chara_dasha_from_chart(chart_data, birth_jd)

# Print first 5 mahadashas
print("Jaimini Mahadashas (first 5):")
for md in jai['mahadashas'][:5]:
    print(f"{md['sign']:10s} {md['start_date'][:10]} → {md['end_date'][:10]} ({md['duration_years']:.2f} yrs)")
