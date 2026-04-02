#!/usr/bin/env python3
"""
audit_table.py — Universal Supabase Schema Auditor
====================================================
Inspects any table: columns, types, sample data, and cross-checks
against what main.py code references.

USAGE:
  python audit_table.py                        # audits all known tables
  python audit_table.py charts                 # audit specific table
  python audit_table.py dasha_periods          # audit specific table
  python audit_table.py charts dasha_periods   # audit multiple tables

OUTPUT:
  - Column list with types
  - Sample row (first record or specific chart)
  - What main.py references for this table
  - ALTER TABLE scripts for any missing columns
"""

import os
import sys
import re
import json

TEST_CHART = "de02bb52-d43a-4b09-be25-b45a07bfbf8a"


def get_supabase():
    """Connect to Supabase."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")

    for env_file in [".env", ".env.local"]:
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("SUPABASE_URL="):
                        url = url or line.split("=", 1)[1].strip().strip('"').strip("'")
                    if "SUPABASE_KEY=" in line or "SUPABASE_SERVICE_KEY=" in line:
                        key = key or line.split("=", 1)[1].strip().strip('"').strip("'")

    if not url or not key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_KEY in .env")
        sys.exit(1)

    from supabase import create_client
    return create_client(url, key)


def get_columns_via_query(supabase, table_name):
    """Get columns by fetching one row and inspecting keys."""
    try:
        result = supabase.table(table_name).select("*").limit(1).execute()
        if result.data and len(result.data) > 0:
            row = result.data[0]
            columns = {}
            for k, v in row.items():
                if v is None:
                    columns[k] = "unknown"
                elif isinstance(v, bool):
                    columns[k] = "boolean"
                elif isinstance(v, int):
                    columns[k] = "integer"
                elif isinstance(v, float):
                    columns[k] = "float"
                elif isinstance(v, dict) or isinstance(v, list):
                    columns[k] = "jsonb"
                elif isinstance(v, str):
                    if "T" in v and ("Z" in v or "+" in v) and len(v) > 18:
                        columns[k] = "timestamptz"
                    elif re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                        columns[k] = "date"
                    elif len(v) == 36 and v.count("-") == 4:
                        columns[k] = "uuid"
                    else:
                        columns[k] = "text"
                else:
                    columns[k] = type(v).__name__
            return columns, row
        else:
            return {}, None
    except Exception as e:
        if "does not exist" in str(e) or "42P01" in str(e):
            return None, None
        return {}, None


def get_sample_for_chart(supabase, table_name, chart_id):
    """Get a sample row for the test chart."""
    try:
        # Try chart_id first
        result = supabase.table(table_name).select("*").eq("chart_id", chart_id).limit(3).execute()
        if result.data:
            return result.data

        # Try id
        result = supabase.table(table_name).select("*").eq("id", chart_id).limit(3).execute()
        if result.data:
            return result.data

        return []
    except:
        return []


def find_code_references(table_name):
    """Scan main.py for references to this table."""
    if not os.path.exists("main.py"):
        return [], []

    with open("main.py") as f:
        content = f.read()

    # Find .select("...") calls for this table
    selects = []
    pattern = re.compile(
        r'table\("' + re.escape(table_name) + r'"\)\s*\\?\s*\.select\("([^"]+)"\)',
        re.MULTILINE
    )
    for m in pattern.finditer(content):
        cols = [c.strip() for c in m.group(1).split(",")]
        selects.extend(cols)

    # Find .insert({...}) calls for this table
    inserts = []
    insert_pattern = re.compile(
        r'table\("' + re.escape(table_name) + r'"\)\.insert\(\{([^}]+)\}',
        re.DOTALL
    )
    for m in insert_pattern.finditer(content):
        block = m.group(1)
        keys = re.findall(r'"(\w+)":', block)
        inserts.extend(keys)

    # Find .eq("col", ...) calls near this table
    eq_cols = []
    eq_pattern = re.compile(
        r'table\("' + re.escape(table_name) + r'"\).*?\.eq\("(\w+)"',
        re.DOTALL
    )
    for m in eq_pattern.finditer(content):
        eq_cols.append(m.group(1))

    return list(set(selects)), list(set(inserts)), list(set(eq_cols))


def suggest_type(col_name):
    """Guess the SQL type for a column name."""
    name = col_name.lower()
    if name in ("id",):
        return "UUID DEFAULT gen_random_uuid() PRIMARY KEY"
    if "chart_id" in name or "_id" in name:
        return "TEXT"
    if name in ("score", "level", "level_int"):
        return "INTEGER"
    if name in ("created_at", "updated_at", "cooldown_until", "start_date", "end_date"):
        return "TIMESTAMPTZ DEFAULT NOW()" if "created" in name else "TIMESTAMPTZ"
    if name in ("breakdown", "prashna_chart", "prashna_data", "chart_data", "jaimini_data", "lal_kitab_data"):
        return "JSONB"
    if "is_" in name or name.startswith("has_"):
        return "BOOLEAN DEFAULT FALSE"
    if name in ("latitude", "longitude", "degree"):
        return "FLOAT"
    return "TEXT"


def audit_table(supabase, table_name):
    """Full audit of one table."""
    print(f"\n{'═' * 60}")
    print(f"  TABLE: {table_name}")
    print(f"{'═' * 60}")

    # Get columns
    columns, sample_row = get_columns_via_query(supabase, table_name)

    if columns is None:
        print(f"  ❌ TABLE DOES NOT EXIST")
        print(f"\n  To create it, you need to define the schema.")
        return

    if not columns:
        print(f"  ⚠️  Table exists but is EMPTY — cannot detect columns from data.")
        print(f"     Run: SELECT column_name, data_type FROM information_schema.columns")
        print(f"     WHERE table_name = '{table_name}' ORDER BY ordinal_position;")
    else:
        print(f"\n  Columns ({len(columns)}):")
        for col, typ in columns.items():
            print(f"    {col:<30} {typ}")

    # Sample data for test chart
    print(f"\n  Sample data (chart {TEST_CHART[:12]}...):")
    samples = get_sample_for_chart(supabase, table_name, TEST_CHART)
    if samples:
        for i, row in enumerate(samples[:2]):
            print(f"\n    Row {i + 1}:")
            for k, v in row.items():
                val_str = str(v)
                if len(val_str) > 80:
                    if isinstance(v, dict):
                        val_str = f"dict({len(v)} keys: {list(v.keys())[:5]})"
                    elif isinstance(v, list):
                        val_str = f"list[{len(v)}]"
                    else:
                        val_str = val_str[:77] + "..."
                print(f"      {k:<28} = {val_str}")
    else:
        print(f"    (no rows for this chart)")

    # Code references
    selects, inserts, eq_cols = find_code_references(table_name)

    if selects or inserts or eq_cols:
        print(f"\n  Code references in main.py:")
        if selects:
            print(f"    SELECT: {selects}")
        if inserts:
            print(f"    INSERT: {inserts}")
        if eq_cols:
            print(f"    .eq():  {eq_cols}")

        # Cross-check: columns referenced in code but missing from table
        all_referenced = set(selects + inserts + eq_cols)
        if columns:
            actual = set(columns.keys())
            missing = all_referenced - actual - {"*"}
            extra = actual - all_referenced - {"id", "created_at", "updated_at"}

            if missing:
                print(f"\n  ❌ MISSING COLUMNS (in code but not in table):")
                for col in sorted(missing):
                    print(f"    - {col}")

                print(f"\n  SQL to fix:")
                for col in sorted(missing):
                    sql_type = suggest_type(col)
                    print(f"    ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col} {sql_type};")

            if extra:
                print(f"\n  ℹ️  Extra columns (in table but not referenced in code):")
                for col in sorted(extra):
                    print(f"    - {col}")

            if not missing:
                print(f"\n  ✅ All referenced columns exist in the table")
        else:
            print(f"\n  ⚠️  Cannot cross-check — table is empty")
            print(f"  Code expects these columns:")
            for col in sorted(all_referenced):
                if col != "*":
                    print(f"    - {col} ({suggest_type(col)})")
    else:
        print(f"\n  ℹ️  No references to '{table_name}' found in main.py")

    # JSONB deep inspection
    if sample_row:
        for col, typ in columns.items():
            if typ == "jsonb" and sample_row.get(col):
                val = sample_row[col]
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except:
                        continue
                if isinstance(val, dict):
                    print(f"\n  JSONB deep inspect: {col}")
                    print(f"    Top-level keys: {list(val.keys())[:15]}")
                    for k, v in list(val.items())[:8]:
                        if isinstance(v, dict):
                            print(f"      {k}: dict({list(v.keys())[:5]})")
                        elif isinstance(v, list):
                            print(f"      {k}: list[{len(v)}]")
                        elif isinstance(v, str) and len(str(v)) > 60:
                            print(f"      {k}: \"{str(v)[:57]}...\"")
                        else:
                            print(f"      {k}: {v}")


def main():
    supabase = get_supabase()
    print("Connected to Supabase ✓")

    # Default tables to audit
    ALL_TABLES = [
        "charts", "dasha_periods", "predictions", "prashna_log",
        "prashna_readings", "practice_log", "practice_schedule_cache",
        "compatibility_sessions", "welcome_signals", "subscriptions",
    ]

    if len(sys.argv) > 1:
        tables = sys.argv[1:]
    else:
        tables = ALL_TABLES

    for table in tables:
        audit_table(supabase, table)

    print(f"\n{'═' * 60}")
    print(f"  Audit complete for: {', '.join(tables)}")
    print(f"{'═' * 60}")


if __name__ == "__main__":
    main()
