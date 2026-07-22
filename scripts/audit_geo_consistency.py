"""
scripts/audit_geo_consistency.py
Do a chart's coordinates actually lie in the country it claims?

Read-only. Run:  ./venv311/bin/python scripts/audit_geo_consistency.py

The check: resolve the coordinates to an IANA timezone, and confirm that zone
belongs to the stated birth country. If it does not, the point is not in that
country whatever the city string says.

Written because the lagna audit could not see this class of error. A chart
whose city read "Santiago de Cali" — the official name of CALI, COLOMBIA — was
geocoded to Santiago, CHILE. Internally consistent: the stored lagna matched
those coordinates perfectly. It was simply the wrong continent, and only a
country cross-check catches that.

First run flagged 3 mismatches (all repaired) and 23 charts as UNVERIFIABLE,
which turned out to matter as much: birth_country held a mix of ISO codes, full
names ("INDIA", "UNITED STATES"), "ZZ" and blanks, so there was nothing to
check against. Those were backfilled from the coordinates, along with the IANA
timezone id — only 4 of 220 charts had one, which is why resolving the birth
offset at the birth moment had almost nothing to act on.

State after: 92/92 live charts consistent, 0 unverifiable, and the lagna audit
still reports 220/220 unchanged.
"""
import os, pytz
from dotenv import load_dotenv; load_dotenv("/Users/ramandeepsinghchadha/antarai/.env")
from supabase import create_client
from timezonefinder import TimezoneFinder
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
tf = TimezoneFinder()

# country -> its IANA zones. If the coordinates' zone isn't among the stated
# country's zones, the point is not in the country the user said they were
# born in, whatever the city string claims.
ZONES = {}
for cc in pytz.country_timezones:
    ZONES[cc] = set(pytz.country_timezones[cc])

rows = sb.table("charts").select(
    "id,name,birth_city,birth_country,country_code,latitude,longitude,lagna_sign,user_id"
).is_("deleted_at","null").execute().data
bad, nocc, ok, unk = [], 0, 0, []
for c in rows:
    cc = (c.get("birth_country") or c.get("country_code") or "").strip().upper()
    if len(cc) != 2 or cc not in ZONES:
        nocc += 1
        unk.append((c, f"no usable birth_country (got {cc!r})"))
        continue
    try:
        z = tf.timezone_at(lat=float(c["latitude"]), lng=float(c["longitude"]))
    except Exception:
        z = None
    if not z:
        nocc += 1; unk.append((c,"coords resolve to no timezone")); continue
    if z in ZONES[cc]: ok += 1
    else: bad.append((c, cc, z))

print(f"checked {len(rows)} live charts:  consistent {ok}   unverifiable {nocc}   MISMATCH {len(bad)}\n")
for c, cc, z in bad:
    print(f"  {c['id'][:8]} city={str(c.get('birth_city'))[:22]:24} says {cc} "
          f"but ({c['latitude']},{c['longitude']}) is in {z}   user={'Y' if c.get('user_id') else '-'}")
print("\nUNVERIFIABLE — no country to check the coordinates against:")
for c, why in unk:
    print(f"  {c['id'][:8]} city={str(c.get('birth_city'))[:20]:22} "
          f"lat={c.get('latitude')} user={'Y' if c.get('user_id') else '-'}  {why}")
