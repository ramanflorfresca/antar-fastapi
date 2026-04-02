#!/usr/bin/env python3
"""
fix_natal_dasha.py — Patches the prashna endpoint to get current dasha
from the dasha_periods table (Vimsottari MD-AD).

Replaces the jaimini_data.current_md lookup with a proper DB query.

RUN: python fix_natal_dasha.py
UNDO: cp main.py.bak_dasha main.py
"""
import os, sys, shutil

MAIN_PY = "main.py"
BACKUP = "main.py.bak_dasha"

# The old code block (reads from jaimini_data which doesn't have Vimsottari dasha)
OLD_BLOCK = '''        # current_dasha not a column — get from jaimini_data.current_md
        _jd_raw = chart_data.get("jaimini_data", {})
        if isinstance(_jd_raw, str):
            try:
                _jd_raw = json.loads(_jd_raw)
            except Exception:
                _jd_raw = {}
        if isinstance(_jd_raw, dict):
            _cur_md = _jd_raw.get("current_md", {})
            natal_dasha = _cur_md.get("lord", "unknown") if isinstance(_cur_md, dict) else "unknown"
        else:
            natal_dasha = "unknown"'''

# The new code block (queries dasha_periods for current Vimsottari MD + AD)
NEW_BLOCK = '''        # Get current dasha from dasha_periods table (Vimsottari MD + AD)
        natal_dasha = "unknown"
        try:
            _dasha_rows = supabase.table("dasha_periods") \\
                .select("planet_or_sign, system, type, level") \\
                .eq("chart_id", chart_id) \\
                .eq("system", "vimsottari") \\
                .lte("start_date", datetime.now(timezone.utc).isoformat()) \\
                .gte("end_date", datetime.now(timezone.utc).isoformat()) \\
                .order("level") \\
                .execute()
            if _dasha_rows.data:
                _md = next((r["planet_or_sign"] for r in _dasha_rows.data if r.get("level") == 1), None)
                _ad = next((r["planet_or_sign"] for r in _dasha_rows.data if r.get("level") == 2), None)
                if _md and _ad:
                    natal_dasha = f"{_md}-{_ad}"
                elif _md:
                    natal_dasha = _md
        except Exception as _de:
            logger.warning(f"Dasha lookup failed (non-blocking): {_de}")'''


def main():
    if not os.path.exists(MAIN_PY):
        print(f"ERROR: {MAIN_PY} not found."); sys.exit(1)

    with open(MAIN_PY, "r") as f:
        content = f.read()

    print(f"Read {MAIN_PY} ({content.count(chr(10))} lines)")

    # Backup
    shutil.copy2(MAIN_PY, BACKUP)
    print(f"Backed up -> {BACKUP}")

    if OLD_BLOCK in content:
        content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)
        print("PATCHED: Replaced jaimini_data dasha lookup with dasha_periods DB query")
    elif "dasha_periods" in content and "vimsottari" in content and "natal_dasha" in content:
        print("Already patched (dasha_periods query found). Skipping.")
    else:
        print("WARNING: Could not find the expected old code block.")
        print("Looking for alternative pattern...")
        
        # Try to find any natal_dasha assignment
        if 'natal_dasha = chart_data.get("current_dasha"' in content:
            content = content.replace(
                'natal_dasha = chart_data.get("current_dasha", "unknown")',
                NEW_BLOCK.lstrip(),
                1
            )
            print("PATCHED: Replaced chart_data.get('current_dasha') with DB query")
        else:
            print("ERROR: Cannot find natal_dasha assignment to replace.")
            print("Check main.py manually around the prashna endpoint.")
            sys.exit(1)

    with open(MAIN_PY, "w") as f:
        f.write(content)
    print(f"Written {MAIN_PY}")

    # Verify
    print("\nVERIFICATION:")
    checks = [
        ("dasha_periods", "Queries dasha_periods table"),
        ("vimsottari", "Filters by vimsottari system"),
        ("planet_or_sign", "Selects planet_or_sign column"),
        ("natal_dasha", "Sets natal_dasha variable"),
        ('f"{_md}-{_ad}"', "Formats as 'Mars-Moon' style"),
    ]
    for term, label in checks:
        found = term in content
        print(f"  {'OK' if found else 'MISSING'}: {label}")

    print("\nDone. Deploy with:")
    print("  git add main.py && git commit -m 'fix: get natal_dasha from dasha_periods table' && git push")
    print("\nExpected result: natal_dasha = 'Mars-Moon' for test chart")


if __name__ == "__main__":
    main()
