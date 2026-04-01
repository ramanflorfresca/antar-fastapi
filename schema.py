#!/usr/bin/env python3
"""
validate_prashna_schema.py
==========================
Connects to your Supabase, inspects the actual table schemas,
and validates that the prashna endpoint code uses correct column names.

RUN: python validate_prashna_schema.py

Requires: pip install supabase
Uses env vars: SUPABASE_URL, SUPABASE_KEY (or reads from .env / main.py)
"""

import os
import sys
import re
import json

# ─── 1. Get Supabase credentials ───
def get_supabase_creds():
    """Try multiple sources for Supabase URL and key."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")

    # Try .env file
    if not url or not key:
        for env_file in [".env", ".env.local"]:
            if os.path.exists(env_file):
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("SUPABASE_URL="):
                            url = url or line.split("=", 1)[1].strip().strip('"').strip("'")
                        if "SUPABASE_KEY=" in line or "SUPABASE_SERVICE_KEY=" in line:
                            key = key or line.split("=", 1)[1].strip().strip('"').strip("'")

    # Try reading from main.py
    if (not url or not key) and os.path.exists("main.py"):
        with open("main.py") as f:
            content = f.read()
        url_match = re.search(r'SUPABASE_URL["\s:=]+["\']?(https://[^"\'\s]+)', content)
        key_match = re.search(r'SUPABASE_(?:SERVICE_)?KEY["\s:=]+["\']?(eyJ[^"\'\s]+)', content)
        if url_match: url = url or url_match.group(1)
        if key_match: key = key or key_match.group(1)

    return url, key


def get_table_columns(supabase, table_name):
    """Get column names for a table by doing a LIMIT 0 query and checking metadata,
    or by querying information_schema."""
    try:
        # Method 1: Query information_schema via RPC or direct
        result = supabase.rpc("", {}).execute()  # won't work, fallback below
    except:
        pass

    try:
        # Method 2: Select * limit 1 and check keys
        result = supabase.table(table_name).select("*").limit(1).execute()
        if result.data and len(result.data) > 0:
            return list(result.data[0].keys())
        else:
            # Table exists but empty — try to get columns from an insert error
            return []
    except Exception as e:
        err = str(e)
        if "does not exist" in err or "42P01" in err:
            return None  # Table doesn't exist
        return []


def main():
    print("═══ PRASHNA SCHEMA VALIDATOR ═══\n")

    url, key = get_supabase_creds()
    if not url or not key:
        print("ERROR: Cannot find SUPABASE_URL and SUPABASE_KEY.")
        print("Set them as env vars or ensure .env file exists.")
        sys.exit(1)

    print(f"Supabase URL: {url[:40]}...")

    try:
        from supabase import create_client
        supabase = create_client(url, key)
        print("Connected to Supabase ✓\n")
    except ImportError:
        print("ERROR: pip install supabase")
        sys.exit(1)

    passed = 0
    failed = 0
    warnings = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name} — {detail}")

    def warn(msg):
        nonlocal warnings
        warnings += 1
        print(f"  ⚠️  {msg}")

    # ═══════════════════════════════════════════════════════════
    # TABLE 1: charts
    # ═══════════════════════════════════════════════════════════
    print("─── TABLE: charts ───")
    charts_cols = get_table_columns(supabase, "charts")

    if charts_cols is None:
        check("charts table exists", False, "Table not found")
    else:
        check("charts table exists", True)

        # What the prashna endpoint SELECT needs:
        needed = ["chart_data", "jaimini_data", "lal_kitab_data", "first_name",
                   "current_country", "lagna_sign", "latitude", "longitude"]

        for col in needed:
            check(f"charts.{col}", col in charts_cols, f"Column missing. Available: {charts_cols[:10]}...")

        # Check what the endpoint uses for lookup
        check("charts.id (for .eq lookup)", "id" in charts_cols, "Missing 'id' column")

        # Check if chart_id exists (it shouldn't based on schema)
        if "chart_id" in charts_cols:
            print(f"  ℹ️  charts.chart_id also exists — endpoint should try both")
        else:
            print(f"  ℹ️  charts.chart_id does NOT exist — use .eq('id', ...) only")

        # Check if current_dasha is a column
        if "current_dasha" in charts_cols:
            print(f"  ℹ️  charts.current_dasha EXISTS as a column")
        else:
            print(f"  ℹ️  charts.current_dasha NOT a column — must read from chart_data JSONB")

    # Get a sample chart to check chart_data structure
    print("\n─── SAMPLE CHART DATA ───")
    try:
        sample = supabase.table("charts").select("id, chart_data, jaimini_data").eq(
            "id", "de02bb52-d43a-4b09-be25-b45a07bfbf8a"
        ).single().execute()

        if sample.data:
            chart_id_val = sample.data.get("id")
            check("Test chart found", True)
            print(f"  Chart ID: {chart_id_val}")

            cd = sample.data.get("chart_data", {})
            if isinstance(cd, str):
                try: cd = json.loads(cd)
                except: cd = {}

            if cd:
                cd_keys = list(cd.keys())[:15]
                print(f"  chart_data keys: {cd_keys}")

                # Look for dasha info
                dasha_keys = [k for k in cd.keys() if "dasha" in k.lower()]
                if dasha_keys:
                    print(f"  Dasha keys found: {dasha_keys}")
                    for dk in dasha_keys:
                        val = cd[dk]
                        if isinstance(val, str):
                            print(f"    {dk} = {val}")
                        elif isinstance(val, dict):
                            print(f"    {dk} = dict with keys: {list(val.keys())[:5]}")
                        elif isinstance(val, list) and len(val) > 0:
                            print(f"    {dk} = list[{len(val)}], first: {val[0] if isinstance(val[0], str) else type(val[0]).__name__}")
                else:
                    print(f"  ⚠️  No dasha keys in chart_data. Full keys: {list(cd.keys())}")
            else:
                warn("chart_data is empty or not a dict")

            jd = sample.data.get("jaimini_data")
            if isinstance(jd, str):
                try: jd = json.loads(jd)
                except: jd = None
            if jd:
                jd_keys = list(jd.keys())[:10]
                print(f"  jaimini_data keys: {jd_keys}")
                check("jaimini_data has content", len(jd_keys) > 0)
            else:
                warn("jaimini_data is empty/null")
        else:
            warn("Test chart not found")
    except Exception as e:
        warn(f"Could not fetch sample chart: {e}")

    # ═══════════════════════════════════════════════════════════
    # TABLE 2: prashna_log
    # ═══════════════════════════════════════════════════════════
    print("\n─── TABLE: prashna_log ───")
    pl_cols = get_table_columns(supabase, "prashna_log")

    if pl_cols is None:
        check("prashna_log table exists", False, "Table not found — run CREATE TABLE SQL")
    else:
        check("prashna_log table exists", True)

        needed_pl = ["chart_id", "question", "domain", "verdict", "score", "label",
                      "timing", "explanation", "breakdown", "prashna_chart",
                      "weakest_planet", "cooldown_until", "created_at"]

        for col in needed_pl:
            check(f"prashna_log.{col}", col in pl_cols, f"Missing. Available: {pl_cols}")

    # ═══════════════════════════════════════════════════════════
    # TABLE 3: prashna_readings (legacy)
    # ═══════════════════════════════════════════════════════════
    print("\n─── TABLE: prashna_readings (legacy) ───")
    pr_cols = get_table_columns(supabase, "prashna_readings")

    if pr_cols is None:
        warn("prashna_readings table not found — legacy inserts will fail silently (non-blocking)")
    else:
        check("prashna_readings table exists", True)
        needed_pr = ["chart_id", "question", "question_type", "verdict", "score",
                      "confidence", "timing", "narrative", "prashna_data"]
        for col in needed_pr:
            if col in pr_cols:
                check(f"prashna_readings.{col}", True)
            else:
                warn(f"prashna_readings.{col} missing — legacy insert may fail (non-blocking)")

    # ═══════════════════════════════════════════════════════════
    # CHECK main.py CODE
    # ═══════════════════════════════════════════════════════════
    print("\n─── CODE ANALYSIS: main.py ───")
    if os.path.exists("main.py"):
        with open("main.py") as f:
            code = f.read()

        # Check what columns the SELECT uses
        select_match = re.search(r'ask_prashna.*?\.select\("([^"]+)"\)', code, re.DOTALL)
        if select_match:
            select_cols = [c.strip() for c in select_match.group(1).split(",")]
            print(f"  SELECT columns in code: {select_cols}")

            if charts_cols:
                for col in select_cols:
                    if col not in charts_cols:
                        check(f"SELECT column '{col}' exists in charts", False,
                              f"Column does not exist! Remove from SELECT.")
                    else:
                        check(f"SELECT column '{col}' exists in charts", True)

        # Check .eq() usage
        eq_matches = re.findall(r'\.eq\("(\w+)",\s*chart_id\)', code[code.find("ask_prashna"):code.find("ask_prashna")+5000])
        for eq_col in eq_matches:
            actual_exists = charts_cols and eq_col in charts_cols
            check(f".eq('{eq_col}', chart_id) — column exists", actual_exists,
                  f"'{eq_col}' not in charts table")

        # Check if current_dasha is referenced as a direct column
        if 'current_dasha' in code[code.find("ask_prashna"):code.find("ask_prashna")+5000]:
            if charts_cols and "current_dasha" not in charts_cols:
                warn("Code references 'current_dasha' but it's NOT a column — must read from chart_data JSONB")
    else:
        warn("main.py not found")

    # ═══════════════════════════════════════════════════════════
    # RESULTS
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'═' * 50}")
    print(f"  RESULTS: {passed} passed, {failed} failed, {warnings} warnings")
    print(f"{'═' * 50}")

    if failed > 0:
        print("\n  ❌ FIX THE FAILURES ABOVE BEFORE DEPLOYING")
        sys.exit(1)
    elif warnings > 0:
        print("\n  ⚠️  Warnings exist but won't block deployment")
    else:
        print("\n  🎉 ALL CHECKS PASSED — safe to deploy")


if __name__ == "__main__":
    main()
