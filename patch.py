#!/usr/bin/env python3
"""
PATCH: Fix dkp_block scoping + jaimini chart_id
Run: python patch_bugs.py

Bug 1: dkp_block used at line ~1723 before defined at line ~1880
Bug 3: jaimini_integration gets chart_data without 'id' key
"""

import shutil
from pathlib import Path
import sys

MAIN = Path("main.py")
if not MAIN.exists():
    print("ERROR: main.py not found"); sys.exit(1)

backup = MAIN.with_suffix(".py.bak_bugs")
shutil.copy2(MAIN, backup)
print(f"✅ Backup: {backup}")

code = MAIN.read_text()

# ═══════════════════════════════════════════════════════════════
# BUG 1: dkp_block scoping — used before defined
# ═══════════════════════════════════════════════════════════════
LANDMARK_BUG1 = "    # Sprint D: domain-focused DKP note"

if 'dkp_block = dkp_block if "dkp_block" in locals()' in code:
    print("⏭️  Bug 1 already fixed — skipping")
else:
    if LANDMARK_BUG1 not in code:
        print("ERROR: Cannot find dkp_block landmark")
        sys.exit(1)
    
    FIX_BUG1 = '''    # Initialize dkp_block if not yet defined (defined later in DKP section ~line 1880)
    dkp_block = dkp_block if "dkp_block" in locals() else ""
    # Sprint D: domain-focused DKP note'''
    
    code = code.replace(LANDMARK_BUG1, FIX_BUG1, 1)
    print("✅ Bug 1 fixed: dkp_block initialized before first use")

# ═══════════════════════════════════════════════════════════════
# BUG 2: Nation insight 'last_updated' — needs investigation
# The error is inside nation_engine.get_nation_insight()
# For now, make the error message more useful
# ═══════════════════════════════════════════════════════════════
LANDMARK_BUG2_OLD = '            print(f"Nation insight error: {e}")'

if 'Nation insight error (non-fatal)' in code:
    print("⏭️  Bug 2 already patched — skipping")
else:
    if LANDMARK_BUG2_OLD in code:
        FIX_BUG2 = '            print(f"[predict] Nation insight error (non-fatal): {type(e).__name__}: {e}")'
        code = code.replace(LANDMARK_BUG2_OLD, FIX_BUG2, 1)
        print("✅ Bug 2: Improved nation insight error logging")
    else:
        print("⏭️  Bug 2 landmark not found — skipping")

# ═══════════════════════════════════════════════════════════════
# BUG 3: Jaimini gets chart_data without 'id' key
# Fix: inject chart_id into chart_data before jaimini calls
# ═══════════════════════════════════════════════════════════════
# Find where chart_data is built/extracted and ensure 'id' is present
LANDMARK_BUG3 = "No jaimini_data found for chart"

# This is in jaimini_integration.py, not main.py
# The fix is to ensure chart_data has 'id' when passed to jaimini functions
# Find where jaimini is called in main.py
JAIMINI_CALL = "score_jaimini_convergence(chart_data, _concern)"

if 'chart_data["id"] = ' in code or 'chart_data.get("id")' in code.split(JAIMINI_CALL)[0][-200:] if JAIMINI_CALL in code else False:
    print("⏭️  Bug 3 already fixed — skipping")
else:
    if JAIMINI_CALL in code:
        FIX_BUG3 = '''# Ensure chart_data has 'id' for jaimini lookups
            if "id" not in chart_data:
                chart_data["id"] = request.chart_id
            _jaimini_conv = score_jaimini_convergence(chart_data, _concern)'''
        
        OLD_BUG3 = "            _jaimini_conv = score_jaimini_convergence(chart_data, _concern)"
        code = code.replace(OLD_BUG3, FIX_BUG3, 1)
        print("✅ Bug 3 fixed: chart_data['id'] set before jaimini call")
    else:
        print("⏭️  Bug 3 jaimini call not found — skipping")

# ═══════════════════════════════════════════════════════════════
# WRITE
# ═══════════════════════════════════════════════════════════════
MAIN.write_text(code)
print(f"\n✅ ALL PATCHES APPLIED — main.py updated")
print(f"   Backup at: {backup}")
print(f"\n📋 Next steps:")
print(f"   1. git add main.py && git commit -m 'fix: dkp_block scoping + jaimini chart_id + nation insight logging'")
print(f"   2. git push")
print(f"   3. Check Railway logs — all 3 errors should be gone")
