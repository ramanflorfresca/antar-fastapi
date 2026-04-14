#!/usr/bin/env python3
"""
patch_phase2c_d9_remaining.py
==============================
Fixes the remaining D9 uppercase references in production code paths.

FINDINGS from grep:
  yoga_engine.py:589       — d_charts.get("D9", {}) — REAL BUG, no fallback
  compatibility_session_engine.py:630 — string literal in list, low risk
  symptom_library.py:639   — already has d9 fallback, safe but clean it up
  d_charts_calculator.py:279 — docstring only, no fix needed

USAGE:
    cd ~/antarai && source venv311/bin/activate
    python patch_phase2c_d9_remaining.py
    python3 -c "import ast; ast.parse(open('antar_engine/yoga_engine.py').read()); print('yoga OK')"
    python3 -c "import ast; ast.parse(open('antar_engine/symptom_library.py').read()); print('symptom OK')"
    python3 -c "import ast; ast.parse(open('antar_engine/compatibility_session_engine.py').read()); print('compat OK')"
    grep -rn '"D9"' main.py antar_engine/ --include='*.py'
    git add -A && git commit -m "fix: all remaining D9 uppercase refs in production code" && git push
"""

import sys
from pathlib import Path

def read(p): return Path(p).read_text(encoding="utf-8")
def write(p, c): Path(p).write_text(c, encoding="utf-8")

def patch(path, patches):
    content = read(path)
    applied = 0
    for desc, old, new in patches:
        if old not in content:
            print(f"  ⚠️  SKIP: {desc}")
            print(f"     Pattern: {old[:80]!r}")
            continue
        content = content.replace(old, new)
        applied += 1
        print(f"  ✅ {desc}")
    if applied:
        write(path, content)
    return applied

def main():
    total = 0

    # --- yoga_engine.py:589 — real bug, no fallback ---
    print("🔧 yoga_engine.py")
    total += patch("antar_engine/yoga_engine.py", [
        (
            "d_charts.get(D9) → d_charts.get(d9)",
            'd9         = d_charts.get("D9", {})',
            'd9         = d_charts.get("d9", d_charts.get("D9", {}))',
        ),
    ])

    # --- symptom_library.py:639 — has fallback but clean it up to canonical ---
    print("🔧 symptom_library.py")
    total += patch("antar_engine/symptom_library.py", [
        (
            'clean up D9/d9 fallback to canonical d9-first',
            'd9=_sj(div.get("D9",div.get("d9",{})))',
            'd9=_sj(div.get("d9",div.get("D9",{})))',
        ),
    ])

    # --- compatibility_session_engine.py:630 — string literal in list ---
    # "D9" and "D10" here are labels/display strings in a missing_data list,
    # not dict key lookups. Change to lowercase for consistency.
    print("🔧 compatibility_session_engine.py")
    total += patch("antar_engine/compatibility_session_engine.py", [
        (
            'missing_data string literals D9/D10 → lowercase',
            '"missing_data":   ["lagna","house_placements","D9","D10","D12"]',
            '"missing_data":   ["lagna","house_placements","d9","d10","d12"]',
        ),
    ])

    print(f"\n{'='*50}")
    print(f"Total changes: {total}")
    if total > 0:
        print("\nVerify:")
        print('  python3 -c "import ast; ast.parse(open(\'antar_engine/yoga_engine.py\').read()); print(\'yoga OK\')"')
        print('  python3 -c "import ast; ast.parse(open(\'antar_engine/symptom_library.py\').read()); print(\'symptom OK\')"')
        print('  python3 -c "import ast; ast.parse(open(\'antar_engine/compatibility_session_engine.py\').read()); print(\'compat OK\')"')
        print('  grep -rn \'"D9"\' main.py antar_engine/ --include=\'*.py\'')
        print("  # Only chart_schema.py and chart_data_validator.py should remain (test fixtures)")
        print("\nCommit:")
        print("  git add -A && git commit -m 'fix: all remaining D9 uppercase refs in production code' && git push")

if __name__ == "__main__":
    main()
