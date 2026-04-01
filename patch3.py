#!/usr/bin/env python3
"""
PATCH v2: Wire 5 — Add jaimini + lal_kitab to GET /dashboard/{chart_id}
=========================================================================
Fixes the v1 patch that broke on `return await _get_dashboard_inner(chart_id)`.

The dashboard endpoint delegates to _get_dashboard_inner(). This patch:
1. Reverts the broken v1 injection (if present)
2. Replaces `return await _get_dashboard_inner(chart_id)` with a wrapper
   that captures the result, injects jaimini + lal_kitab, then returns it.

HOW TO RUN:
  python patch_dashboard_v2.py
  git diff main.py          # review
  git add main.py && git commit -m "Wire 5: jaimini + lal_kitab in /dashboard" && git push

ROLLBACK:
  cp main.py.bak main.py
"""

import shutil
import sys

MAIN_PY = "main.py"

def patch():
    try:
        with open(MAIN_PY, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERROR: {MAIN_PY} not found. Run from project root.")
        sys.exit(1)

    shutil.copy2(MAIN_PY, MAIN_PY + ".bak")
    print(f"✅ Backup: {MAIN_PY}.bak")

    # ── Step 1: Remove broken v1 patch if present ────────────────
    broken_marker = "# ── Wire 5: Inject jaimini + lal_kitab into dashboard response ──"
    if broken_marker in content:
        print("🔧 Removing broken v1 patch...")
        lines = content.split("\n")
        cleaned = []
        skip = False
        for line in lines:
            if broken_marker in line:
                skip = True
                # Remove the blank line before the marker too
                if cleaned and cleaned[-1].strip() == "":
                    cleaned.pop()
                continue
            if skip:
                # Skip all injected lines until we hit the original return
                if line.strip().startswith("return await _get_dashboard_inner"):
                    skip = False
                    cleaned.append(line)
                elif line.strip().startswith("return ") and "_get_dashboard" in line:
                    skip = False
                    cleaned.append(line)
                # Skip injected lines (they all start with _w5_ or are try/except/if blocks)
                continue
            cleaned.append(line)
        content = "\n".join(cleaned)
        print("✅ Broken v1 patch removed")

    # ── Step 2: Find and replace the return line ─────────────────
    # Target:  `        return await _get_dashboard_inner(chart_id)`
    # Replace with wrapper that injects jaimini + lal_kitab

    target = "return await _get_dashboard_inner(chart_id)"

    if target not in content:
        # Try variations
        import re
        match = re.search(r'return\s+await\s+_get_dashboard_inner\s*\(\s*chart_id\s*\)', content)
        if match:
            target = match.group(0)
        else:
            print(f"ERROR: Could not find `{target}` in main.py")
            print("       Searching for _get_dashboard_inner...")
            for i, line in enumerate(content.split("\n")):
                if "_get_dashboard_inner" in line:
                    print(f"  Line {i+1}: {line.rstrip()}")
            sys.exit(1)

    # Check if already patched (v2)
    if "_w5_result" in content and '"jaimini"' in content:
        print("⚠️  Wire 5 v2 appears already applied. Skipping.")
        sys.exit(0)

    # Find the exact line to get the indentation
    lines = content.split("\n")
    target_idx = None
    for i, line in enumerate(lines):
        if target in line:
            target_idx = i
            break

    if target_idx is None:
        print("ERROR: Target line not found after cleanup")
        sys.exit(1)

    indent = lines[target_idx][:len(lines[target_idx]) - len(lines[target_idx].lstrip())]
    print(f"✅ Found target at line {target_idx + 1}, indent='{indent}' ({len(indent)} spaces)")

    # ── Step 3: Build replacement block ──────────────────────────
    replacement = f"""{indent}# ── Wire 5: Inject jaimini + lal_kitab into dashboard response ──
{indent}_w5_result = await _get_dashboard_inner(chart_id)
{indent}if isinstance(_w5_result, dict):
{indent}    try:
{indent}        _w5_chart = supabase.table('charts').select('jaimini_data, lal_kitab_data').eq('id', chart_id).single().execute()
{indent}        _w5_row = _w5_chart.data if _w5_chart and _w5_chart.data else {{}}
{indent}        _w5_result['jaimini'] = _safe_jsonb(_w5_row.get('jaimini_data', {{}}))
{indent}        _w5_result['lal_kitab'] = _safe_jsonb(_w5_row.get('lal_kitab_data', {{}}))
{indent}    except Exception:
{indent}        _w5_result.setdefault('jaimini', {{}})
{indent}        _w5_result.setdefault('lal_kitab', {{}})
{indent}return _w5_result"""

    # Replace the single return line with the block
    lines[target_idx] = replacement
    patched = "\n".join(lines)

    with open(MAIN_PY, "w") as f:
        f.write(patched)

    print(f"\n✅ PATCH v2 APPLIED")
    print(f"")
    print(f"── WHAT CHANGED ──")
    print(f"   Before: return await _get_dashboard_inner(chart_id)")
    print(f"   After:  Calls inner function → injects jaimini + lal_kitab from charts JSONB → returns")
    print(f"")
    print(f"── VERIFY ──")
    print(f"   git diff main.py")
    print(f"   git add main.py && git commit -m 'Wire 5: jaimini + lal_kitab in /dashboard' && git push")
    print(f"   curl https://antar-fastapi-production.up.railway.app/api/v1/dashboard/de02bb52-d43a-4b09-be25-b45a07bfbf8a | python -m json.tool | grep jaimini")
    print(f"")
    print(f"── EXPECTED RESPONSE (new keys) ──")
    print(f'   "jaimini": {{ "karakas": [...], "arudha_lagna": {{...}}, "current_md": {{...}}, ... }}')
    print(f'   "lal_kitab": {{ "varshphal": {{...}}, "sleeping_planets": [...], ... }}')
    print(f"")
    print(f"── ROLLBACK ──")
    print(f"   cp main.py.bak main.py")


if __name__ == "__main__":
    patch()
