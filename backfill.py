#!/usr/bin/env python3
"""
Jaimini v2.0 Backfill Script
==============================
Recomputes jaimini_data for all existing charts using the new K.N. Rao engine.

Run: python3 backfill_jaimini_v2.py

Requires:
  - SUPABASE_URL and SUPABASE_KEY env vars (or set below)
  - antar_engine/jaimini_engine.py and jaimini_integration.py in place

What it does:
  1. Fetches all charts from Supabase
  2. For each chart, extracts planets + D9 from chart_data JSONB
  3. Runs build_and_store_jaimini() which computes karakas, AL, UL, KL,
     full Chara Dasha timeline, and stores to jaimini_data JSONB + dasha rows
  4. Reports success/failure per chart
"""

import os
import sys
import json
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 60)
    print("  Jaimini v2.0 Backfill")
    print("=" * 60)

    # ── Connect to Supabase ──
    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: pip install supabase")
        sys.exit(1)

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not url or not key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_KEY env vars")
        print("  export SUPABASE_URL=https://xxx.supabase.co")
        print("  export SUPABASE_KEY=eyJ...")
        sys.exit(1)

    supabase = create_client(url, key)
    print(f"✓ Connected to Supabase")

    # ── Import engine ──
    try:
        from antar_engine.jaimini_integration import build_and_store_jaimini
        from antar_engine.jaimini_engine import SIGN_NAMES
    except ImportError as e:
        print(f"ERROR: Cannot import Jaimini engine: {e}")
        sys.exit(1)

    print(f"✓ Jaimini engine imported")

    # ── Fetch all charts ──
    result = supabase.table("charts").select(
        "id, birth_date, lagna_sign, chart_data, jaimini_data"
    ).execute()

    charts = result.data or []
    print(f"✓ Found {len(charts)} charts")
    print()

    # ── Process each chart ──
    success = 0
    skipped = 0
    failed = 0
    errors = []

    for i, chart in enumerate(charts):
        chart_id = chart.get("id", "?")
        birth_date = chart.get("birth_date", "")
        lagna_sign_text = chart.get("lagna_sign", "")
        chart_data_raw = chart.get("chart_data", {})

        # Parse chart_data if string
        if isinstance(chart_data_raw, str):
            try:
                chart_data_raw = json.loads(chart_data_raw)
            except (json.JSONDecodeError, TypeError):
                chart_data_raw = {}

        # Skip if no chart_data
        if not chart_data_raw or not birth_date or not lagna_sign_text:
            print(f"  [{i+1}/{len(charts)}] {chart_id[:8]}... SKIP (missing data)")
            skipped += 1
            continue

        # Get lagna index
        try:
            lagna_idx = SIGN_NAMES.index(lagna_sign_text.title())
        except (ValueError, AttributeError):
            # Try from chart_data
            lagna_from_cd = chart_data_raw.get("lagna", "")
            if isinstance(lagna_from_cd, str):
                try:
                    lagna_idx = SIGN_NAMES.index(lagna_from_cd.title())
                except ValueError:
                    print(f"  [{i+1}/{len(charts)}] {chart_id[:8]}... SKIP (bad lagna: {lagna_sign_text})")
                    skipped += 1
                    continue
            elif isinstance(lagna_from_cd, (int, float)):
                lagna_idx = int(lagna_from_cd)
            else:
                print(f"  [{i+1}/{len(charts)}] {chart_id[:8]}... SKIP (no lagna)")
                skipped += 1
                continue

        # Extract planets
        planets_dict = chart_data_raw.get("planets", {})
        if not planets_dict:
            print(f"  [{i+1}/{len(charts)}] {chart_id[:8]}... SKIP (no planets)")
            skipped += 1
            continue

        # Extract D9 planets
        d9_dict = {}
        div_charts = chart_data_raw.get("divisional_charts", {})
        if div_charts and "D9" in div_charts:
            d9_dict = div_charts["D9"].get("planets", {})
        if not d9_dict:
            d9_dict = chart_data_raw.get("d9_planets", {})
        if not d9_dict:
            # Use D1 planets as fallback (karakamsa will use D1 signs)
            d9_dict = planets_dict

        # Normalize birth_date
        bd = str(birth_date)[:10]

        # Run the engine
        try:
            result = build_and_store_jaimini(
                chart_id=chart_id,
                lagna_sign=lagna_idx,
                planets_dict=planets_dict,
                d9_planets_dict=d9_dict,
                birth_date_str=bd,
                supabase_client=supabase,
            )
            success += 1
            # Show key results
            jd = result.get("jaimini_data", {})
            n_karakas = len(jd.get("karakas", []))
            n_preds = len(jd.get("predictions", []))
            al = jd.get("arudha_lagna", {}).get("sign_name", "?")
            md = jd.get("current_md", {})
            md_sign = md.get("sign_name", "?") if md else "?"
            md_years = md.get("years", "?") if md else "?"
            print(f"  [{i+1}/{len(charts)}] {chart_id[:8]}... OK  karakas={n_karakas} AL={al} MD={md_sign}({md_years}yr) preds={n_preds}")

        except Exception as e:
            failed += 1
            err_msg = str(e)[:100]
            errors.append((chart_id, err_msg))
            print(f"  [{i+1}/{len(charts)}] {chart_id[:8]}... FAIL: {err_msg}")

    # ── Summary ──
    print()
    print("=" * 60)
    print(f"  BACKFILL COMPLETE")
    print(f"  Success: {success}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed:  {failed}")
    print(f"  Total:   {len(charts)}")
    print("=" * 60)

    if errors:
        print("\nFailed charts:")
        for cid, err in errors:
            print(f"  {cid}: {err}")


if __name__ == "__main__":
    main()
