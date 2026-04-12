#!/usr/bin/env python3
"""
backfill_null.py
----------------
Targets the 60 charts with NULL character_archetype using raw SQL filter.

RUN:
  export SUPABASE_URL=https://xxxx.supabase.co
  export SUPABASE_KEY=your-service-role-key
  python backfill_null.py
"""

import os, sys, time, requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
API_BASE     = "https://antar-fastapi-production.up.railway.app"
DELAY_SEC    = 0.3

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_KEY")
        sys.exit(1)

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Use raw postgrest filter instead of .is_()
    result = sb.table("charts").select("id").filter(
        "character_archetype", "is", "null"
    ).execute()

    chart_ids = [row["id"] for row in result.data]
    print(f"Found {len(chart_ids)} NULL charts")

    if not chart_ids:
        # Fallback — fetch all and filter client-side
        print("Trying client-side filter...")
        result = sb.table("charts").select("id, character_archetype").execute()
        chart_ids = [
            row["id"] for row in result.data
            if row.get("character_archetype") is None
        ]
        print(f"Found {len(chart_ids)} NULL charts (client-side)")

    if not chart_ids:
        print("No NULL charts found.")
        return

    success, failed = 0, []
    for i, chart_id in enumerate(chart_ids, 1):
        url = f"{API_BASE}/api/v1/chart/{chart_id}/signature"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                name = data.get("character_archetype", {}).get("name", "UNKNOWN")
                print(f"[{i}/{len(chart_ids)}] ✓ {chart_id[:8]}... → {name}")
                success += 1
            else:
                print(f"[{i}/{len(chart_ids)}] ✗ {chart_id[:8]}... → HTTP {r.status_code}")
                failed.append(chart_id)
        except Exception as e:
            print(f"[{i}/{len(chart_ids)}] ✗ {chart_id[:8]}... → {e}")
            failed.append(chart_id)
        time.sleep(DELAY_SEC)

    print(f"\nDONE — {success}/{len(chart_ids)} backfilled")
    if failed:
        print(f"Failed: {len(failed)}")

if __name__ == "__main__":
    main()
