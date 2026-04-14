#!/usr/bin/env python3
"""
scripts/normalize_existing_charts.py
======================================
One-shot migration: normalize all existing chart rows in Supabase
to the canonical schema defined in antar_engine/chart_schema.py.

WHAT IT DOES:
  - Reads every row from the `charts` table (chart_data JSONB column)
  - Runs normalize_chart_data() on each
  - Validates the result with validate_chart_data()
  - Writes back only rows that actually changed
  - Prints a full report

SAFETY FEATURES:
  --dry-run   (default) — shows what would change, writes nothing
  --wet-run   — actually writes to Supabase (requires confirmation)
  --chart-id  — process a single chart only (for spot-checking)
  --limit N   — process only the first N charts

USAGE:
  cd ~/antarai && source venv311/bin/activate

  # 1. Dry run first (safe, always do this first)
  python scripts/normalize_existing_charts.py --dry-run

  # 2. Spot-check one chart
  python scripts/normalize_existing_charts.py --chart-id de02bb52-d43a-4b09-be25-b45a07bfbf8a --dry-run

  # 3. Wet run (take a Supabase point-in-time backup FIRST)
  python scripts/normalize_existing_charts.py --wet-run

BEFORE RUNNING WET RUN:
  1. Go to Supabase dashboard → Settings → Backups
  2. Create a manual backup or note the current point-in-time
  3. Then run --wet-run

VERIFICATION AFTER WET RUN:
  # Spot-check a chart
  python scripts/normalize_existing_charts.py --chart-id <id> --dry-run
  # Should show: "No changes needed" for all normalized charts
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from antar_engine.chart_schema import normalize_chart_data
from antar_engine.chart_data_validator import validate_chart_data, split_errors_warnings


# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------

def get_supabase():
    try:
        from supabase import create_client
    except ImportError:
        print("❌ supabase-py not installed. Run: pip install supabase")
        sys.exit(1)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

    if not url or not key:
        # Try loading from .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            for line in open(env_path):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("❌ SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        print("   Either export them or put them in a .env file at the project root")
        sys.exit(1)

    return create_client(url, key)


# ---------------------------------------------------------------------------
# Deep equality check (compare JSON blobs)
# ---------------------------------------------------------------------------

def _json_equal(a: Any, b: Any) -> bool:
    """Compare two objects as JSON (sort_keys for consistency)."""
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# ---------------------------------------------------------------------------
# Per-chart processing
# ---------------------------------------------------------------------------

def process_chart(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process one chart row.
    Returns a result dict with keys: chart_id, changed, errors, warnings, summary
    """
    chart_id = row.get("id", "unknown")
    raw_data = row.get("chart_data") or {}

    # Normalize
    normalized = normalize_chart_data(raw_data)

    # Validate
    ok, all_errors = validate_chart_data(normalized)
    hard_errors, warnings = split_errors_warnings(all_errors)

    # Check if anything changed
    changed = not _json_equal(raw_data, normalized)

    # Build change summary
    summary_lines = []
    if changed:
        # Detect D9 case fix
        orig_div = raw_data.get("divisional_charts") or {}
        norm_div = normalized.get("divisional_charts") or {}
        if "D9" in orig_div and "d9" in norm_div:
            summary_lines.append("D9→d9 key normalized")
        if "D10" in orig_div and "d10" in norm_div:
            summary_lines.append("D10→d10 key normalized")

        # Detect sign index coercions
        def count_string_signs(d: Any, depth=0) -> int:
            if depth > 5 or not isinstance(d, dict):
                return 0
            count = 0
            for k, v in d.items():
                if k == "sign" and isinstance(v, str):
                    count += 1
                count += count_string_signs(v, depth + 1)
            return count

        string_signs = count_string_signs(raw_data)
        if string_signs:
            summary_lines.append(f"{string_signs} string sign(s) coerced to int")

        # Detect kala.age fix
        orig_age = ((raw_data.get("dkp_context") or {}).get("kala") or {}).get("age")
        norm_age = ((normalized.get("dkp_context") or {}).get("kala") or {}).get("age")
        if orig_age is not None and not isinstance(orig_age, int) and isinstance(norm_age, int):
            summary_lines.append(f"kala.age {orig_age!r}→{norm_age}")

        if not summary_lines:
            summary_lines.append("data structure normalized")

    return {
        "chart_id": chart_id,
        "changed": changed,
        "valid": ok,
        "hard_errors": hard_errors,
        "warnings": warnings,
        "summary": ", ".join(summary_lines) if summary_lines else "no changes needed",
        "normalized_data": normalized,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Normalize existing Antar chart data to canonical schema"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                      help="Show what would change, write nothing (SAFE)")
    mode.add_argument("--wet-run", action="store_true",
                      help="Actually write changes to Supabase")
    parser.add_argument("--chart-id", help="Process only this chart ID")
    parser.add_argument("--limit", type=int, default=0,
                        help="Process only first N charts (0 = all)")
    args = parser.parse_args()

    if args.wet_run:
        print("⚠️  WET RUN MODE — changes will be written to Supabase")
        print("    Have you taken a Supabase backup? (y/N) ", end="", flush=True)
        ans = input().strip().lower()
        if ans != "y":
            print("Aborting. Run with --dry-run first, then take a backup.")
            sys.exit(0)
        print()

    print("Connecting to Supabase…")
    supabase = get_supabase()

    # Fetch charts
    print("Fetching charts…")
    if args.chart_id:
        resp = supabase.table("charts").select("id, chart_data").eq("id", args.chart_id).execute()
    else:
        resp = supabase.table("charts").select("id, chart_data").execute()

    rows = resp.data or []
    if args.limit > 0:
        rows = rows[:args.limit]

    total = len(rows)
    print(f"Processing {total} chart(s)…\n")

    # Process
    results = []
    for i, row in enumerate(rows, 1):
        result = process_chart(row)
        results.append(result)

        status = "CHANGED" if result["changed"] else "OK    "
        valid_mark = "✅" if result["valid"] else "⚠️ "
        print(f"  [{i:4d}/{total}] {valid_mark} {status} {result['chart_id'][:36]}  {result['summary']}")

        if result["hard_errors"]:
            for e in result["hard_errors"]:
                print(f"            ERROR: {e}")

    # Summary stats
    changed = [r for r in results if r["changed"]]
    invalid = [r for r in results if not r["valid"]]
    warned  = [r for r in results if r["warnings"]]

    print(f"\n{'=' * 60}")
    print(f"TOTAL:   {total}")
    print(f"CHANGED: {len(changed)}")
    print(f"INVALID: {len(invalid)}  (schema hard errors)")
    print(f"WARNED:  {len(warned)}   (missing optional data)")
    print(f"{'=' * 60}")

    if invalid:
        print(f"\n⚠️  Charts with hard errors ({len(invalid)}):")
        for r in invalid:
            print(f"   {r['chart_id']}")
            for e in r["hard_errors"][:3]:
                print(f"     {e}")

    # Write
    if args.dry_run:
        print(f"\n🔍 DRY RUN — no changes written.")
        if changed:
            print(f"   Re-run with --wet-run to apply {len(changed)} change(s).")
        return

    if not changed:
        print("\n✅ Nothing to write — all charts already canonical.")
        return

    print(f"\n✍️  Writing {len(changed)} updated chart(s) to Supabase…")
    write_ok = 0
    write_err = 0
    for r in changed:
        try:
            supabase.table("charts").update(
                {"chart_data": r["normalized_data"]}
            ).eq("id", r["chart_id"]).execute()
            write_ok += 1
            print(f"  ✅ {r['chart_id']}")
        except Exception as e:
            write_err += 1
            print(f"  ❌ {r['chart_id']}: {e}")
        time.sleep(0.05)   # gentle rate limit

    print(f"\nWrite results: {write_ok} OK, {write_err} errors")
    if write_err == 0:
        print("✅ Migration complete.")
    else:
        print("⚠️  Some writes failed — check the errors above.")


if __name__ == "__main__":
    main()
