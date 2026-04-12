#!/usr/bin/env python3
"""
force_recompute_signatures.py
------------------------------
Clears character_archetype + planet_signatures for all NAVIGATOR charts
in Supabase, then re-hits the signature endpoint to recompute them.

This is needed because ensure_signatures() skips charts that already
have a value stored — even if that value is the NAVIGATOR fallback.

RUN:
  export SUPABASE_URL=https://xxxx.supabase.co
  export SUPABASE_KEY=your-service-role-key
  python force_recompute_signatures.py
"""

import os, sys, time, requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
API_BASE     = "https://antar-fastapi-production.up.railway.app"
DELAY_SEC    = 0.3

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_KEY env vars")
        sys.exit(1)

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Step 1 — find all NAVIGATOR chart IDs
    print("Finding NAVIGATOR charts...")
    result = sb.table("charts").select("id").eq(
        "character_archetype->>name", "THE NAVIGATOR"
    ).execute()
    chart_ids = [row["id"] for row in result.data]
    print(f"Found {len(chart_ids)} NAVIGATOR charts")

    if not chart_ids:
        print("None found — already clean.")
        return

    # Step 2 — clear the cached values so ensure_signatures recomputes
    print("Clearing cached archetypes...")
    for cid in chart_ids:
        sb.table("charts").update({
            "character_archetype": None,
            "planet_signatures": None
        }).eq("id", cid).execute()
    print(f"Cleared {len(chart_ids)} charts")

    # Step 3 — re-hit signature endpoint for each
    print("Recomputing...")
    success, failed = 0, []

    for i, chart_id in enumerate(chart_ids, 1):
        url = f"{API_BASE}/api/v1/chart/{chart_id}/signature"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                archetype = data.get("character_archetype", {}).get("name", "UNKNOWN")
                print(f"[{i}/{len(chart_ids)}] ✓ {chart_id[:8]}... → {archetype}")
                success += 1
            else:
                print(f"[{i}/{len(chart_ids)}] ✗ {chart_id[:8]}... → HTTP {r.status_code}")
                failed.append(chart_id)
        except Exception as e:
            print(f"[{i}/{len(chart_ids)}] ✗ {chart_id[:8]}... → {e}")
            failed.append(chart_id)
        time.sleep(DELAY_SEC)

    print(f"\n{'─'*50}")
    print(f"DONE — {success}/{len(chart_ids)} recomputed")
    if failed:
        print(f"Failed: {len(failed)} charts — check Railway logs")
    print(f"\nNow run Query 1 in Supabase to confirm NAVIGATOR = 0")

if __name__ == "__main__":
    main()
