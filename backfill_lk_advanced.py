"""
Backfill sleeping planets + Rin into lal_kitab_data.advanced for all charts.
Run: cd ~/antarai && source venv311/bin/activate && python backfill_lk_advanced.py
"""
import os, sys, json
sys.path.insert(0, '.')
from supabase import create_client
from antar_engine.lal_kitab_advanced import detect_sleeping_planets, calculate_comprehensive_rin

url = os.environ['SUPABASE_URL']
key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_KEY') or os.environ['SUPABASE_ANON_KEY']
sb = create_client(url, key)

# Get all charts
charts = sb.table("charts").select("id, chart_data, lal_kitab_data").execute()
updated = 0
skipped = 0
errors = 0

for chart in charts.data:
    try:
        lk = chart.get("lal_kitab_data") or {}
        if isinstance(lk, str):
            lk = json.loads(lk)

        # Skip if already has advanced data with content
        adv = lk.get("advanced") or {}
        if adv.get("sleeping_planets") or adv.get("rin_debts"):
            skipped += 1
            continue

        cd = chart.get("chart_data") or {}
        if isinstance(cd, str):
            cd = json.loads(cd)

        planets = cd.get("planets", {})
        if not planets:
            skipped += 1
            continue

        sleeping = detect_sleeping_planets(planets)
        rin = calculate_comprehensive_rin(planets)

        lk["advanced"] = {"sleeping_planets": sleeping, "rin_debts": rin}
        sb.table("charts").update({"lal_kitab_data": lk}).eq("id", chart["id"]).execute()
        updated += 1
        if updated % 10 == 0:
            print(f"Updated {updated} charts...")
    except Exception as e:
        errors += 1
        print(f"Error on {chart['id']}: {e}")

print(f"Done — {updated} charts backfilled, {skipped} skipped, {errors} errors")
