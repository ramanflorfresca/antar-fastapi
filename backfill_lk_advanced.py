"""
Backfill Lal-Kitab derived fields into charts.lal_kitab_data:
  advanced.{sleeping_planets, rin_debts}  (natal, static)
  enemy_houses                            (natal, static)
  year_lord / year_lord_house             (Varshphal; refreshed by birthday cron)

Field-additive + idempotent: only writes when a field is missing, preserves all
existing keys. Run: cd ~/antarai && source venv311/bin/activate && python backfill_lk_advanced.py
"""
import os, sys, json
sys.path.insert(0, '.')
from supabase import create_client
from antar_engine.lal_kitab_advanced import (
    detect_sleeping_planets, calculate_comprehensive_rin,
    detect_enemy_houses, year_lord_for)

url = os.environ['SUPABASE_URL']
key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_KEY') or os.environ['SUPABASE_ANON_KEY']
sb = create_client(url, key)

charts = sb.table("charts").select("id, chart_data, lal_kitab_data, birth_date").execute()
updated = skipped = errors = 0

for chart in charts.data:
    try:
        lk = chart.get("lal_kitab_data") or {}
        if isinstance(lk, str):
            lk = json.loads(lk)

        cd = chart.get("chart_data") or {}
        if isinstance(cd, str):
            cd = json.loads(cd)
        planets = cd.get("planets", {})
        if not planets:
            skipped += 1
            continue

        changed = False

        adv = lk.get("advanced") or {}
        if not adv.get("sleeping_planets") and not adv.get("rin_debts"):
            lk["advanced"] = {
                "sleeping_planets": detect_sleeping_planets(planets),
                "rin_debts":        calculate_comprehensive_rin(planets),
            }
            changed = True

        if "enemy_houses" not in lk:
            lk["enemy_houses"] = detect_enemy_houses(planets)
            changed = True

        if not lk.get("year_lord") and chart.get("birth_date"):
            _yl = year_lord_for(chart["birth_date"])
            if _yl:
                lk["year_lord"] = _yl
                lk["year_lord_house"] = (planets.get(_yl, {}) or {}).get("house", 0)
                changed = True

        if not changed:
            skipped += 1
            continue

        sb.table("charts").update({"lal_kitab_data": lk}).eq("id", chart["id"]).execute()
        updated += 1
        if updated % 20 == 0:
            print(f"Updated {updated} charts...")
    except Exception as e:
        errors += 1
        print(f"Error on {chart.get('id')}: {e}")

print(f"Done — {updated} charts backfilled, {skipped} skipped, {errors} errors")
