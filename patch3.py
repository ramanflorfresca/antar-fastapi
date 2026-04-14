#!/usr/bin/env python3
"""
patch_phase2b_d9_main.py
=========================
Fixes the two remaining D9 uppercase references in main.py that the
first patch missed (different pattern: .get("D9", {}) not .get("D9")).

Also fixes the same pattern in the backfill endpoint.

USAGE:
    cd ~/antarai && source venv311/bin/activate
    python patch_phase2b_d9_main.py
    python3 -c "import ast; ast.parse(open('main.py').read()); print('OK')"
    grep -n '"D9"' main.py
    git add -A && git commit -m "fix: remaining D9 uppercase refs in main.py" && git push
"""

import sys
from pathlib import Path

def read(path): return Path(path).read_text(encoding="utf-8")
def write(path, content): Path(path).write_text(content, encoding="utf-8")

def main():
    path = "main.py"
    if not Path(path).exists():
        print("❌ main.py not found — run from ~/antarai/")
        sys.exit(1)

    content = read(path)
    original = content
    changes = 0

    # --- FIX 1: chart creation call site (line ~4510) ---
    # _d9_data = chart_data.get("divisional_charts", {}).get("D9", {}).get("planets", {})
    old1 = '_d9_data = chart_data.get("divisional_charts", {}).get("D9", {}).get("planets", {})'
    new1 = '_d9_data = chart_data.get("divisional_charts", {}).get("d9", {}).get("planets", {})'

    if old1 in content:
        count = content.count(old1)
        content = content.replace(old1, new1)
        changes += count
        print(f"✅ Fixed {count}x: chart creation D9→d9 (.get with default)")
    else:
        print(f"⚠️  SKIP: chart creation pattern not found")
        print(f"   Expected: {old1}")

    # --- FIX 2: backfill endpoint (line ~6814) ---
    # _d9 = cd.get("divisional_charts", {}).get("D9", {}).get("planets", {})
    old2 = '_d9 = cd.get("divisional_charts", {}).get("D9", {}).get("planets", {})'
    new2 = '_d9 = cd.get("divisional_charts", {}).get("d9", {}).get("planets", {})'

    if old2 in content:
        count = content.count(old2)
        content = content.replace(old2, new2)
        changes += count
        print(f"✅ Fixed {count}x: backfill endpoint D9→d9 (.get with default)")
    else:
        print(f"⚠️  SKIP: backfill endpoint pattern not found")
        print(f"   Expected: {old2}")

    # --- SAFETY: catch any remaining "D9" in dict access patterns ---
    # Broad check — don't auto-replace, just report
    remaining = []
    for i, line in enumerate(content.splitlines(), 1):
        if '"D9"' in line or "['D9']" in line or '["D9"]' in line:
            # Skip comments and docstrings (crude but good enough)
            stripped = line.strip()
            if not stripped.startswith("#") and not stripped.startswith('"""') and not stripped.startswith("'D9'"):
                remaining.append((i, line.rstrip()))

    if content != original:
        write(path, content)
        print(f"\n✅ {changes} change(s) written to main.py")
    else:
        print(f"\nℹ️  No changes written")

    if remaining:
        print(f"\n⚠️  {len(remaining)} remaining 'D9' reference(s) in main.py (review manually):")
        for lineno, line in remaining:
            print(f"   {lineno:6d}: {line[:100]}")
    else:
        print("✅ No remaining D9 uppercase references in main.py")

    print("\nNext:")
    print('  python3 -c "import ast; ast.parse(open(\'main.py\').read()); print(\'OK\')"')
    print('  grep -rn \'"D9"\' main.py antar_engine/ --include=\'*.py\'')
    print("  git add -A && git commit -m 'fix: remaining D9 uppercase refs in main.py' && git push")

if __name__ == "__main__":
    main()
