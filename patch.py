#!/usr/bin/env python3
"""
patch_phase2_chart_data_bugs.py
================================
Phase 2 of the JSON-first /predict refactor sprint.

Fixes three pre-existing bugs discovered during the Apr 14 KV caching sprint:

  BUG 1 — D9 case inconsistency
    chart data stores divisional_charts.d9 (lowercase)
    but 5 code paths read divisional_charts.D9 (uppercase)
    → every Jaimini computation silently fell back to D1 as Navamsa
    → wrong Karakamsa, wrong predictions for every user

  BUG 2 — build_and_store_jaimini dead import
    main.py:4513 references a function that no longer exists in jaimini_engine.py
    try/except swallows the error
    → every new chart silently fails to store Jaimini data

  BUG 3 — computed_at timestamp in jaimini_to_db_json
    datetime.now().isoformat() inside jaimini_to_db_json poisons KV cache
    → cache_hit stays at 0 even after all other drift was eliminated

AFFECTED FILES:
  main.py                                      — bugs 1 (×3 locations), 2, 3
  antar_engine/yoga_engine.py                  — bug 1 (×1 location)
  antar_engine/d_charts_calculator.py          — bug 1 (×1 location, docstring)
  antar_engine/compatibility_session_engine.py — bug 1 (×1 location)
  antar_engine/jaimini_engine.py               — bug 3 (computed_at removal)

USAGE:
  cd ~/antarai && source venv311/bin/activate
  python patch_phase2_chart_data_bugs.py
  python3 -c "import ast; ast.parse(open('main.py').read()); print('main.py OK')"
  python3 -c "import ast; ast.parse(open('antar_engine/jaimini_engine.py').read()); print('jaimini_engine.py OK')"
  python3 -c "import ast; ast.parse(open('antar_engine/yoga_engine.py').read()); print('yoga_engine.py OK')"
  python3 -c "import ast; ast.parse(open('antar_engine/compatibility_session_engine.py').read()); print('compatibility OK')"
  git add -A && git commit -m "fix: D9 case bug, dead jaimini import, computed_at cache drift" && git push
"""

import re
import sys
import shutil
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def write(path: str, content: str) -> None:
    Path(path).write_text(content, encoding="utf-8")

def backup(path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{path}.bak_phase2_{ts}"
    shutil.copy2(path, dst)
    return dst

def apply(path: str, patches: list[tuple[str, str, str]]) -> int:
    """
    Apply a list of (description, old, new) patches to a file.
    Returns count of patches applied.
    """
    content = read(path)
    applied = 0
    for description, old, new in patches:
        if old not in content:
            print(f"  ⚠️  SKIP ({path}): pattern not found — {description}")
            print(f"     First 80 chars of pattern: {old[:80]!r}")
            continue
        count = content.count(old)
        if count > 1:
            print(f"  ⚠️  SKIP ({path}): pattern matches {count} times — {description}")
            continue
        content = content.replace(old, new)
        applied += 1
        print(f"  ✅ Applied: {description}")
    write(path, content)
    return applied

# ---------------------------------------------------------------------------
# BUG 1a — main.py: D9 uppercase reads
#
# The sprint doc identified these line ranges (use landmark strings):
#   main.py:4510  — chart creation backfill flow
#   main.py:6810  — /api/v1/backfill-jaimini/{chart_id} endpoint
#   main.py (3rd occurrence) — somewhere in predict/context build path
#
# Strategy: grep for ALL occurrences of .get("D9" and replace with .get("d9"
# but ONLY inside the get() call (not in comments or string literals that
# are user-facing). We replace the dict .get("D9") pattern specifically.
# ---------------------------------------------------------------------------

def fix_d9_in_file(path: str) -> int:
    content = read(path)
    original = content

    # Pattern 1: .get("D9") → .get("d9")
    new_content = content.replace('.get("D9")', '.get("d9")')
    count1 = content.count('.get("D9")')

    # Pattern 2: ["D9"] → ["d9"]  (direct dict access)
    new_content2 = new_content.replace('["D9"]', '["d9"]')
    count2 = new_content.count('["D9"]')

    # Pattern 3: 'D9' inside get() with single quotes
    new_content3 = new_content2.replace(".get('D9')", ".get('d9')")
    count3 = new_content2.count(".get('D9')")

    # Pattern 4: ['D9'] direct access single quotes
    new_content4 = new_content3.replace("['D9']", "['d9']")
    count4 = new_content3.count("['D9']")

    total = count1 + count2 + count3 + count4
    if total > 0:
        write(path, new_content4)
        print(f"  ✅ {path}: replaced {total} D9 uppercase reference(s)")
        print(f"     (.get: {count1+count3}, direct[]: {count2+count4})")
    else:
        print(f"  ℹ️  {path}: no D9 uppercase references found")
    return total

# ---------------------------------------------------------------------------
# BUG 2 — main.py: build_and_store_jaimini dead import
#
# The dead call at chart creation (around main.py:4513) looks like:
#
#   try:
#       build_and_store_jaimini(chart_id, chart_data)
#   except Exception as e:
#       logger.error(f"Jaimini storage failed: {e}")
#
# Replace with the correct pattern (same as backfill_jaimini_local.py):
#
#   try:
#       from antar_engine.jaimini_engine import (
#           calculate_jaimini_analysis, jaimini_to_db_json
#       )
#       jaimini_result = calculate_jaimini_analysis(chart_data)
#       jaimini_db = jaimini_to_db_json(jaimini_result)
#       supabase.table("charts").update(
#           {"jaimini_data": jaimini_db}
#       ).eq("id", chart_id).execute()
#       logger.info(f"Jaimini data stored for chart {chart_id}")
#   except Exception as e:
#       logger.error(f"Jaimini storage failed for {chart_id}: {e}", exc_info=True)
#
# NOTE: We use landmark search (the try: + build_and_store_jaimini line)
# because line numbers shift with edits. If the exact pattern isn't found,
# the patch prints a clear skip message so you can locate it manually.
# ---------------------------------------------------------------------------

DEAD_IMPORT_PATTERNS = [
    # Variant A — most common form
    (
        "fix: replace dead build_and_store_jaimini import (variant A)",
        """        try:
            build_and_store_jaimini(chart_id, chart_data)
        except Exception as e:
            logger.error(f"Jaimini storage failed: {e}")""",
        """        try:
            from antar_engine.jaimini_engine import (
                calculate_jaimini_analysis, jaimini_to_db_json
            )
            jaimini_result = calculate_jaimini_analysis(chart_data)
            jaimini_db = jaimini_to_db_json(jaimini_result)
            supabase.table("charts").update(
                {"jaimini_data": jaimini_db}
            ).eq("id", chart_id).execute()
            logger.info(f"Jaimini data stored for chart {chart_id}")
        except Exception as e:
            logger.error(
                f"Jaimini storage failed for {chart_id}: {e}", exc_info=True
            )""",
    ),
    # Variant B — different indentation (top-level route handler)
    (
        "fix: replace dead build_and_store_jaimini import (variant B, 4-space indent)",
        """    try:
        build_and_store_jaimini(chart_id, chart_data)
    except Exception as e:
        logger.error(f"Jaimini storage failed: {e}")""",
        """    try:
        from antar_engine.jaimini_engine import (
            calculate_jaimini_analysis, jaimini_to_db_json
        )
        jaimini_result = calculate_jaimini_analysis(chart_data)
        jaimini_db = jaimini_to_db_json(jaimini_result)
        supabase.table("charts").update(
            {"jaimini_data": jaimini_db}
        ).eq("id", chart_id).execute()
        logger.info(f"Jaimini data stored for chart {chart_id}")
    except Exception as e:
        logger.error(
            f"Jaimini storage failed for {chart_id}: {e}", exc_info=True
        )""",
    ),
]

# Also fix the /backfill-jaimini endpoint which has the same dead import
# (sprint doc line 6789 — different endpoint, same bug)
BACKFILL_ENDPOINT_PATTERNS = [
    (
        "fix: backfill-jaimini endpoint — replace dead import (variant A)",
        """            build_and_store_jaimini(chart_id, existing_chart_data)""",
        """            from antar_engine.jaimini_engine import (
                calculate_jaimini_analysis, jaimini_to_db_json
            )
            jaimini_result = calculate_jaimini_analysis(existing_chart_data)
            jaimini_db = jaimini_to_db_json(jaimini_result)
            supabase.table("charts").update(
                {"jaimini_data": jaimini_db}
            ).eq("id", chart_id).execute()
            logger.info(f"Backfill Jaimini stored for chart {chart_id}")""",
    ),
]

# ---------------------------------------------------------------------------
# BUG 3 — jaimini_engine.py: remove computed_at from jaimini_to_db_json
#
# The function includes:
#   "computed_at": datetime.now().isoformat()
#
# This makes the JSONB value different on every call → poisons KV cache.
# Remove this line entirely. If an admin "last computed" marker is needed,
# it should live in a separate Supabase column, not inside the JSONB payload.
# ---------------------------------------------------------------------------

COMPUTED_AT_PATTERNS = [
    (
        'remove computed_at datetime.now() from jaimini_to_db_json (comma after)',
        '        "computed_at": datetime.now().isoformat(),\n',
        '',
    ),
    (
        'remove computed_at datetime.now() from jaimini_to_db_json (no trailing comma)',
        '        "computed_at": datetime.now().isoformat()\n',
        '',
    ),
    # Variant with different spacing
    (
        'remove computed_at (single-space indent variant)',
        '    "computed_at": datetime.now().isoformat(),\n',
        '',
    ),
    (
        'remove computed_at (single-space indent, no comma)',
        '    "computed_at": datetime.now().isoformat()\n',
        '',
    ),
]

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Phase 2: Chart Data Bug Fixes")
    print("=" * 60)

    files_to_check = [
        "main.py",
        "antar_engine/yoga_engine.py",
        "antar_engine/d_charts_calculator.py",
        "antar_engine/compatibility_session_engine.py",
        "antar_engine/jaimini_engine.py",
    ]

    # Verify all files exist before touching anything
    missing = [f for f in files_to_check if not Path(f).exists()]
    if missing:
        print(f"\n❌ ABORT: Files not found: {missing}")
        print("   Run this script from ~/antarai/")
        sys.exit(1)

    # Backup
    print("\n📦 Creating backups…")
    for f in files_to_check:
        dst = backup(f)
        print(f"  {f} → {dst}")

    total_changes = 0

    # ------------------------------------------------------------------
    # BUG 1: D9 uppercase → lowercase in all affected files
    # ------------------------------------------------------------------
    print("\n🔧 BUG 1: D9 case inconsistency")
    for path in [
        "main.py",
        "antar_engine/yoga_engine.py",
        "antar_engine/d_charts_calculator.py",
        "antar_engine/compatibility_session_engine.py",
    ]:
        n = fix_d9_in_file(path)
        total_changes += n

    # ------------------------------------------------------------------
    # BUG 2: Dead build_and_store_jaimini import in main.py
    # ------------------------------------------------------------------
    print("\n🔧 BUG 2: Dead build_and_store_jaimini import")

    # First check if the dead function is even referenced
    main_content = read("main.py")
    if "build_and_store_jaimini" not in main_content:
        print("  ℹ️  build_and_store_jaimini not found in main.py — may already be fixed")
    else:
        # Count occurrences
        count = main_content.count("build_and_store_jaimini")
        print(f"  Found {count} reference(s) to build_and_store_jaimini")

        n = apply("main.py", DEAD_IMPORT_PATTERNS)
        total_changes += n

        if n == 0:
            # Pattern didn't match exactly — print context for manual fix
            print("\n  ⚠️  Could not auto-patch. Manual fix needed.")
            print("  Search main.py for: build_and_store_jaimini")
            print("  Replace the entire try/except block with:")
            print("""
        try:
            from antar_engine.jaimini_engine import (
                calculate_jaimini_analysis, jaimini_to_db_json
            )
            jaimini_result = calculate_jaimini_analysis(chart_data)
            jaimini_db = jaimini_to_db_json(jaimini_result)
            supabase.table("charts").update(
                {"jaimini_data": jaimini_db}
            ).eq("id", chart_id).execute()
            logger.info(f"Jaimini data stored for chart {chart_id}")
        except Exception as e:
            logger.error(
                f"Jaimini storage failed for {chart_id}: {e}", exc_info=True
            )
""")

        # Also fix the backfill endpoint
        n2 = apply("main.py", BACKFILL_ENDPOINT_PATTERNS)
        total_changes += n2

    # ------------------------------------------------------------------
    # BUG 3: computed_at in jaimini_engine.py
    # ------------------------------------------------------------------
    print("\n🔧 BUG 3: computed_at timestamp (cache drift)")

    jaimini_content = read("antar_engine/jaimini_engine.py")
    if "computed_at" not in jaimini_content:
        print("  ℹ️  computed_at not found in jaimini_engine.py — may already be fixed")
    else:
        n = apply("antar_engine/jaimini_engine.py", COMPUTED_AT_PATTERNS)
        total_changes += n
        if n == 0:
            # Try a broader regex match as fallback
            import re
            pattern = r'\s*["\']computed_at["\']\s*:\s*datetime\.now\(\)[^,\n]*[,]?\n'
            new_content = re.sub(pattern, '', jaimini_content)
            if new_content != jaimini_content:
                write("antar_engine/jaimini_engine.py", new_content)
                total_changes += 1
                print("  ✅ Removed computed_at via regex fallback")
            else:
                print("  ⚠️  Could not auto-remove computed_at. Manual fix needed.")
                print("  Find and delete this line in jaimini_to_db_json:")
                print('       "computed_at": datetime.now().isoformat(),')

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'=' * 60}")
    print(f"Total changes applied: {total_changes}")
    print(f"{'=' * 60}")

    if total_changes == 0:
        print("\n⚠️  No changes applied — patterns may have changed.")
        print("   Check each file manually using the descriptions above.")
    else:
        print("\n📋 Next steps:")
        print("  1. Verify syntax:")
        print("     python3 -c \"import ast; ast.parse(open('main.py').read()); print('main.py OK')\"")
        print("     python3 -c \"import ast; ast.parse(open('antar_engine/jaimini_engine.py').read()); print('jaimini OK')\"")
        print("     python3 -c \"import ast; ast.parse(open('antar_engine/yoga_engine.py').read()); print('yoga OK')\"")
        print("     python3 -c \"import ast; ast.parse(open('antar_engine/compatibility_session_engine.py').read()); print('compat OK')\"")
        print("  2. Verify no D9 uppercase remains:")
        print("     grep -rn '\"D9\"\\|\\[.D9.\\]' main.py antar_engine/ --include='*.py'")
        print("  3. Verify computed_at removed:")
        print("     grep -n 'computed_at' antar_engine/jaimini_engine.py")
        print("  4. Verify dead import gone:")
        print("     grep -n 'build_and_store_jaimini' main.py")
        print("  5. Commit:")
        print("     git add -A && git commit -m 'fix: D9 case bug, dead jaimini import, computed_at cache drift' && git push")


if __name__ == "__main__":
    main()
