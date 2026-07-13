#!/usr/bin/env python3
"""
scripts/backfill_current_location.py
====================================
[desh-kaal-patra P0 2026-07-12] Geocode every chart's `current_city` -> precise
current coords + IANA timezone, and persist to the new columns
(current_latitude / current_longitude / current_timezone / current_geocode_city).

Prereq: run Antar.world/sql_current_location_columns.sql first (adds the columns).
The runtime already does this lazily on the first daily-signal per chart; this
just does everyone up front. Cities in the built-in 60-city table resolve with
no API; the rest need GOOGLE_MAPS_API_KEY (same key the app uses).

USAGE:
  source venv311/bin/activate
  python scripts/backfill_current_location.py --dry-run              # no writes
  python scripts/backfill_current_location.py --wet-run              # persist
  python scripts/backfill_current_location.py --chart-id <id> --dry-run
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# main.py owns the geocoder (_geocode_city: local 60-city table -> Google) and
# the Supabase client. Importing it initialises those (no server is started).
import main  # noqa: E402


async def _resolve(city: str, country: str):
    try:
        lat, lng, tz_id, src = await main._geocode_city(city, country or "")
        return float(lat), float(lng), tz_id, src
    except Exception as e:
        return None, None, None, f"FAILED: {str(e)[:80]}"


async def run(dry_run: bool, only_id: str | None):
    sb = main.supabase
    q = sb.table("charts").select(
        "id,current_city,current_country,current_latitude,current_geocode_city")
    if only_id:
        q = q.eq("id", only_id)
    else:
        q = q.not_.is_("current_city", "null")
    rows = q.limit(5000).execute().data or []

    scanned = skipped = fixed = failed = 0
    for r in rows:
        scanned += 1
        cid = r["id"]
        city = (r.get("current_city") or "").strip()
        country = (r.get("current_country") or "").strip()
        if not city:
            continue
        # already resolved for this exact city?
        if (r.get("current_latitude") is not None
                and (r.get("current_geocode_city") or "").strip().lower() == city.lower()):
            skipped += 1
            continue
        lat, lng, tz_id, src = await _resolve(city, country)
        if lat is None:
            failed += 1
            print(f"  [miss] {cid[:8]} {city!r},{country!r} -> {src}")
            continue
        fixed += 1
        print(f"  [{'plan' if dry_run else 'set '}] {cid[:8]} {city!r},{country!r} "
              f"-> ({lat:.4f},{lng:.4f}) {tz_id} [{src}]")
        if not dry_run:
            try:
                sb.table("charts").update({
                    "current_latitude": lat, "current_longitude": lng,
                    "current_timezone": tz_id, "current_geocode_city": city,
                }).eq("id", cid).execute()
            except Exception as e:
                print(f"    !! write failed (did you run the migration?): {str(e)[:100]}")

    mode = "DRY-RUN" if dry_run else "WET-RUN"
    print(f"\n{mode}: scanned={scanned} already-set={skipped} "
          f"{'would-fix' if dry_run else 'fixed'}={fixed} failed={failed}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wet-run", action="store_true", help="persist (default is dry-run)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--chart-id", default=None)
    a = ap.parse_args()
    asyncio.run(run(dry_run=not a.wet_run, only_id=a.chart_id))
