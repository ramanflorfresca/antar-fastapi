#!/usr/bin/env python3
"""
scripts/normalize_existing_charts.py
======================================
One-shot migration: normalize all chart_data rows to canonical schema.

REAL SCHEMA (confirmed Apr 14 2026):
  chart_data has: lagna, planets, divisional_charts, yogas, house_lords, etc.
  NO dashas inside chart_data (separate dasha_periods table)
  NO lal_kitab_data inside chart_data (separate column)
  Divisional charts already use lowercase keys in production.

WHAT THIS SCRIPT DOES:
  - Reads chart_data from every charts row
  - Adds sign_index to lagna, planets, and divisional chart planets
  - Normalizes sign/planet name casing
  - Normalizes any uppercase D9-style keys (safety net)
  - Writes back only rows that actually changed (safe, idempotent)

USAGE:
  python scripts/normalize_existing_charts.py --dry-run   # safe, no writes
  python scripts/normalize_existing_charts.py --wet-run   # writes to Supabase
  python scripts/normalize_existing_charts.py --chart-id <id> --dry-run
"""

import argparse, json, os, sys, time
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from antar_engine.chart_schema import normalize_chart_data
from antar_engine.chart_data_validator import validate_chart_data, split_errors_warnings


def get_supabase():
    try:
        from supabase import create_client
    except ImportError:
        print("pip install supabase"); sys.exit(1)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not (url and key):
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            for line in open(env_path):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not (url and key):
        print("❌ SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required"); sys.exit(1)
    return create_client(url, key)


def _json_equal(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def process_chart(row):
    chart_id = row.get("id", "unknown")
    raw_data = row.get("chart_data") or {}
    normalized = normalize_chart_data(raw_data)
    ok, all_errors = validate_chart_data(normalized)
    hard, warnings = split_errors_warnings(all_errors)
    changed = not _json_equal(raw_data, normalized)

    summary_lines = []
    if changed:
        # Detect sign_index additions
        def count_missing_sign_index(d, depth=0):
            if depth > 4 or not isinstance(d, dict): return 0
            count = sum(1 for k, v in d.items()
                       if k == "sign" and isinstance(v, str) and "sign_index" not in d)
            return count + sum(count_missing_sign_index(v, depth+1) for v in d.values()
                               if isinstance(v, dict))
        missing = count_missing_sign_index(raw_data)
        if missing:
            summary_lines.append(f"sign_index added to {missing} location(s)")

        # Uppercase div keys
        orig_div = raw_data.get("divisional_charts") or {}
        upper = [k for k in orig_div if k != k.lower()]
        if upper:
            summary_lines.append(f"uppercase keys normalized: {upper}")

        if not summary_lines:
            summary_lines.append("data structure normalized")

    return {
        "chart_id": chart_id,
        "changed": changed,
        "valid": ok,
        "hard_errors": hard,
        "warnings": warnings,
        "summary": ", ".join(summary_lines) if summary_lines else "no changes needed",
        "normalized_data": normalized,
    }


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--wet-run", action="store_true")
    parser.add_argument("--chart-id")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if args.wet_run:
        print("⚠️  WET RUN — changes will be written to Supabase")
        print("    Have you taken a Supabase backup? (y/N) ", end="", flush=True)
        if input().strip().lower() != "y":
            print("Aborting."); sys.exit(0)

    print("Connecting to Supabase...")
    supabase = get_supabase()

    if args.chart_id:
        resp = supabase.table("charts").select("id, chart_data").eq("id", args.chart_id).execute()
    else:
        resp = supabase.table("charts").select("id, chart_data").execute()

    rows = resp.data or []
    if args.limit > 0:
        rows = rows[:args.limit]

    total = len(rows)
    print(f"Processing {total} chart(s)...\n")

    results = []
    for i, row in enumerate(rows, 1):
        r = process_chart(row)
        results.append(r)
        status = "CHANGED" if r["changed"] else "OK    "
        mark = "✅" if r["valid"] else "⚠️ "
        print(f"  [{i:4d}/{total}] {mark} {status} {r['chart_id'][:36]}  {r['summary']}")
        for e in r["hard_errors"]:
            print(f"            ERROR: {e}")

    changed = [r for r in results if r["changed"]]
    invalid = [r for r in results if not r["valid"]]

    print(f"\n{'='*60}")
    print(f"TOTAL:   {total}")
    print(f"CHANGED: {len(changed)}")
    print(f"INVALID: {len(invalid)}")
    print(f"{'='*60}")

    if args.dry_run:
        print(f"\n🔍 DRY RUN — no changes written.")
        if changed:
            print(f"   Re-run with --wet-run to apply {len(changed)} change(s).")
        return

    if not changed:
        print("\n✅ Nothing to write — all charts already canonical.")
        return

    print(f"\n✍️  Writing {len(changed)} chart(s)...")
    ok_count = err_count = 0
    for r in changed:
        try:
            supabase.table("charts").update(
                {"chart_data": r["normalized_data"]}
            ).eq("id", r["chart_id"]).execute()
            ok_count += 1
            print(f"  ✅ {r['chart_id']}")
        except Exception as e:
            err_count += 1
            print(f"  ❌ {r['chart_id']}: {e}")
        time.sleep(0.05)

    print(f"\nWrite results: {ok_count} OK, {err_count} errors")
    if err_count == 0:
        print("✅ Migration complete.")


if __name__ == "__main__":
    main()
