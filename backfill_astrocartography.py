"""
Backfill astrocartography_data into charts table for charts missing it.
Computes planetary MC/ASC lines via score_cities_for_chart(birth_jd)
and stores the result in charts.astrocartography_data JSONB column.

Run: cd ~/antarai && source venv311/bin/activate && python backfill_astrocartography.py
"""
import os, sys, json
sys.path.insert(0, '.')
from supabase import create_client
from antar_engine.astrocartography import score_cities_for_chart

url = os.environ['SUPABASE_URL']
key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_KEY') or os.environ['SUPABASE_ANON_KEY']
sb = create_client(url, key)

# Get all charts — only need chart_data (for birth_jd) and astrocartography_data (to check if cached)
charts = sb.table("charts").select("id, chart_data, astrocartography_data").execute()
updated = 0
skipped = 0
errors = 0

for chart in charts.data:
    cid = chart["id"]
    try:
        # Skip if already has astrocartography_data
        if chart.get("astrocartography_data"):
            skipped += 1
            continue

        cd = chart.get("chart_data") or {}
        if isinstance(cd, str):
            cd = json.loads(cd)

        birth_jd = cd.get("birth_jd")
        if not birth_jd:
            skipped += 1
            continue

        # Compute planetary lines for this chart
        city_line_data = score_cities_for_chart(float(birth_jd))

        # Store in charts.astrocartography_data
        sb.table("charts").update({
            "astrocartography_data": city_line_data
        }).eq("id", cid).execute()
        updated += 1
        if updated % 5 == 0:
            print(f"Computed {updated} charts...")
    except Exception as e:
        errors += 1
        print(f"Error on {cid}: {e}")

print(f"Done — {updated} charts backfilled, {skipped} skipped, {errors} errors")
