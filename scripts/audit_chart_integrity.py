import sys; sys.path.insert(0,"/Users/ramandeepsinghchadha/antarai")
import os, json
from dotenv import load_dotenv; load_dotenv("/Users/ramandeepsinghchadha/antarai/.env")
from supabase import create_client
from collections import Counter
from timezonefinder import TimezoneFinder
from antar_engine.chart import calculate_chart, _tz_name_to_offset

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
tf = TimezoneFinder()
rows, page = [], 0
while True:
    d = (sb.table("charts").select(
        "id,name,birth_date,birth_time,latitude,longitude,timezone,timezone_offset,"
        "lagna_sign,birth_country,birth_city").range(page*1000, page*1000+999).execute().data) or []
    rows += d
    if len(d) < 1000: break
    page += 1

moved, same, skipped = [], 0, 0
for c in rows:
    try:
        lat, lng = float(c["latitude"]), float(c["longitude"])
        bd, bt = c["birth_date"], (c.get("birth_time") or "12:00")[:5]
        stored = (c.get("lagna_sign") or "").strip()
        if not stored: skipped += 1; continue
        tzid = c.get("timezone") if "/" in str(c.get("timezone") or "") else tf.timezone_at(lat=lat, lng=lng)
        if not tzid: skipped += 1; continue
        off = _tz_name_to_offset(tzid, bd, bt)
        new = calculate_chart(bd, bt, lat, lng, tz_offset=off)["lagna"]["sign"]
        if new.strip().lower() != stored.lower():
            moved.append((c.get("name") or "?", c.get("birth_country"), bd, bt, stored, new,
                          c.get("timezone_offset"), off, c["id"]))
        else: same += 1
    except Exception:
        skipped += 1

print(f"charts        : {len(rows)}")
print(f"lagna MATCHES : {same}")
print(f"lagna MOVES   : {len(moved)}")
print(f"skipped       : {skipped}")
print("\nby country:", Counter(m[1] for m in moved).most_common(10))
print("\n%-18s %-3s %-11s %-6s %-11s -> %-11s  stored_off -> correct" % ("name","cc","date","time","stored","correct"))
for m in moved[:25]:
    print(f"{str(m[0])[:17]:18} {str(m[1]):3} {m[2]:11} {m[3]:6} {m[4]:11} -> {m[5]:11}  {m[6]} -> {m[7]}")
json.dump([{"id":m[8],"name":m[0],"stored":m[4],"correct":m[5],"off":m[7]} for m in moved],
          open("/tmp/lagna_moved.json","w"), indent=1)
print(f"\nwrote /tmp/lagna_moved.json ({len(moved)})")
