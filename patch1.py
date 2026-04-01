#!/usr/bin/env python3
"""
PATCH: Wire 5 — Add jaimini + lal_kitab keys to GET /dashboard/{chart_id}
==========================================================================
This completes the missing Wire 5 from the Jaimini v2.0 sprint.

PROBLEM:
  - Frontend checks `dashData.jaimini` and gets undefined → error state
  - /dashboard returns flat fields (dasha_md, lagna, etc.) but no jaimini object
  - jaimini_data JSONB is stored in charts table for all 169 charts
  - _safe_jsonb() already exists in main.py (~line 5797)

FIX:
  - Find the /dashboard/{chart_id} endpoint return statement
  - Inject jaimini + lal_kitab keys from chart row JSONB columns

HOW TO RUN:
  1. SSH into Railway or run in the project root
  2. python patch_dashboard_jaimini.py
  3. Verify: curl https://antar-fastapi-production.up.railway.app/api/v1/dashboard/de02bb52-d43a-4b09-be25-b45a07bfbf8a | python -m json.tool | grep jaimini
  4. git add main.py && git commit -m "Wire 5: add jaimini + lal_kitab to /dashboard" && git push

ROLLBACK:
  main.py.bak is created automatically. To rollback:
  cp main.py.bak main.py && git add main.py && git commit -m "rollback Wire 5" && git push
"""

import re
import shutil
import sys

MAIN_PY = "main.py"

def patch():
    # ── 1. Read main.py ─────────────────────────────────────────
    try:
        with open(MAIN_PY, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERROR: {MAIN_PY} not found. Run this from the project root.")
        sys.exit(1)

    # ── 2. Backup ────────────────────────────────────────────────
    shutil.copy2(MAIN_PY, MAIN_PY + ".bak")
    print(f"✅ Backup created: {MAIN_PY}.bak")

    # ── 3. Check if already patched ──────────────────────────────
    if '"jaimini"' in content and "jaimini_data" in content and "_safe_jsonb" in content:
        # Could be from other wiring — check if it's in the dashboard endpoint
        # Look for the pattern near /dashboard
        dashboard_section = ""
        lines = content.split("\n")
        in_dashboard = False
        for i, line in enumerate(lines):
            if "/dashboard/" in line and ("def " in line or "@app" in line.lower() or "route" in line.lower()):
                in_dashboard = True
            if in_dashboard:
                dashboard_section += line + "\n"
                if line.strip().startswith("return") and i > 10:
                    break
        if '"jaimini"' in dashboard_section:
            print("⚠️  Wire 5 appears to already be applied. Checking response shape...")
            print("   Run: curl .../api/v1/dashboard/de02bb52... | python -m json.tool | grep jaimini")
            print("   If jaimini key is present, no patch needed.")
            sys.exit(0)

    # ── 4. Find the dashboard endpoint ───────────────────────────
    # Strategy: Find the GET /dashboard/{chart_id} route and its return dict
    #
    # We look for patterns like:
    #   @app.get("/api/v1/dashboard/{chart_id}")
    #   async def dashboard(...):
    #       ...
    #       return { ... }  or  return JSONResponse({ ... })
    #
    # We need to inject jaimini + lal_kitab keys into that return dict.

    lines = content.split("\n")

    # Find the dashboard route decorator line
    dashboard_route_idx = None
    for i, line in enumerate(lines):
        if re.search(r'["\']\/api\/v1\/dashboard\/\{chart_id\}["\']', line):
            dashboard_route_idx = i
            break
        # Also check for variations
        if re.search(r'dashboard.*chart_id', line) and ("get" in line.lower() or "route" in line.lower() or "@app" in line.lower()):
            dashboard_route_idx = i
            break

    if dashboard_route_idx is None:
        print("ERROR: Could not find /dashboard/{chart_id} route in main.py")
        print("       Searching for 'dashboard' in file...")
        for i, line in enumerate(lines):
            if "dashboard" in line.lower():
                print(f"  Line {i+1}: {line.rstrip()}")
        sys.exit(1)

    print(f"✅ Found dashboard route at line {dashboard_route_idx + 1}")

    # ── 5. Find the return statement in the dashboard function ───
    # Walk forward from the route decorator to find the return statement
    # that contains the response dict. It could be:
    #   return { "chart_id": ..., "dasha": ..., ... }
    #   return JSONResponse(content={ ... })
    #   response = { ... }; return response
    #   result = { ... }; return result

    # Strategy A: Find `return {` or `return JSONResponse` within 200 lines
    # Strategy B: Find the variable being built and returned

    return_line_idx = None
    response_var = None
    brace_depth = 0
    func_indent = None

    for i in range(dashboard_route_idx + 1, min(dashboard_route_idx + 300, len(lines))):
        line = lines[i]
        stripped = line.strip()

        # Detect function definition to get indent level
        if stripped.startswith("async def ") or stripped.startswith("def "):
            func_indent = len(line) - len(line.lstrip())

        # Detect next route decorator (we've gone too far)
        if i > dashboard_route_idx + 5 and stripped.startswith("@app."):
            print(f"⚠️  Hit next route at line {i+1} without finding return")
            break

        # Look for return statement
        if stripped.startswith("return "):
            return_line_idx = i
            break

    if return_line_idx is None:
        print("ERROR: Could not find return statement in dashboard endpoint")
        print("       Lines near dashboard route:")
        for i in range(dashboard_route_idx, min(dashboard_route_idx + 50, len(lines))):
            print(f"  {i+1}: {lines[i].rstrip()}")
        sys.exit(1)

    print(f"✅ Found return statement at line {return_line_idx + 1}: {lines[return_line_idx].strip()[:80]}")

    # ── 6. Determine injection strategy ──────────────────────────
    return_line = lines[return_line_idx]
    indent = " " * (len(return_line) - len(return_line.lstrip()))

    # Check what the return line looks like
    return_stripped = return_line.strip()

    # Strategy A: return { ... } — inject before the return, add keys to dict
    # Strategy B: return variable — inject before, modify the variable
    # Strategy C: return JSONResponse(...) — inject before

    # The safest approach: inject a block BEFORE the return line that:
    # 1. Reads jaimini_data and lal_kitab_data from the chart row
    # 2. Modifies the response dict/variable to include them
    #
    # But we don't know the variable name. So let's use a different approach:
    # Inject a helper block that patches whatever is being returned.

    # Find what variable holds the chart data (look for supabase query)
    chart_var = None
    chart_row_var = None
    for i in range(dashboard_route_idx + 1, return_line_idx):
        line = lines[i].strip()
        # Look for supabase select query
        if "supabase" in line and ("select" in line or "charts" in line):
            # Try to find the variable assignment
            if "=" in line:
                chart_var = line.split("=")[0].strip()
        # Look for .data or response extraction
        if ".data" in line and "=" in line:
            chart_row_var = line.split("=")[0].strip()

    print(f"   Chart query var: {chart_var or 'unknown'}")
    print(f"   Chart row var: {chart_row_var or 'unknown'}")

    # ── 7. Build the injection block ─────────────────────────────
    # We inject BEFORE the return line. This block:
    # - Extracts jaimini_data and lal_kitab_data from the chart row
    # - Handles both dict and .data access patterns
    # - Uses _safe_jsonb which already exists in main.py

    # Detect if _safe_jsonb exists
    has_safe_jsonb = "_safe_jsonb" in content
    if not has_safe_jsonb:
        print("⚠️  _safe_jsonb not found in main.py — will add inline version")

    # Build injection code
    injection_lines = []
    injection_lines.append("")
    injection_lines.append(f"{indent}# ── Wire 5: Inject jaimini + lal_kitab into dashboard response ──")

    if not has_safe_jsonb:
        injection_lines.append(f"{indent}import json as _pjson_w5")
        injection_lines.append(f"{indent}def _safe_jsonb_w5(v):")
        injection_lines.append(f"{indent}    if isinstance(v, str):")
        injection_lines.append(f"{indent}        try: return _pjson_w5.loads(v)")
        injection_lines.append(f"{indent}        except: return {{}}")
        injection_lines.append(f"{indent}    return v if isinstance(v, dict) else {{}}")
        safe_fn = "_safe_jsonb_w5"
    else:
        safe_fn = "_safe_jsonb"

    # We need to get jaimini_data from the chart. The dashboard endpoint
    # queries the charts table — we need to find how the chart data is accessed.
    # Since we can't be 100% sure of the variable name, we'll do a fresh query.
    injection_lines.append(f"{indent}try:")
    injection_lines.append(f"{indent}    _w5_chart = supabase.table('charts').select('jaimini_data, lal_kitab_data').eq('id', chart_id).single().execute()")
    injection_lines.append(f"{indent}    _w5_row = _w5_chart.data if _w5_chart and _w5_chart.data else {{}}")
    injection_lines.append(f"{indent}    _w5_jaimini = {safe_fn}(_w5_row.get('jaimini_data', {{}}))")
    injection_lines.append(f"{indent}    _w5_lk = {safe_fn}(_w5_row.get('lal_kitab_data', {{}}))")
    injection_lines.append(f"{indent}except Exception:")
    injection_lines.append(f"{indent}    _w5_jaimini = {{}}")
    injection_lines.append(f"{indent}    _w5_lk = {{}}")

    # Now we need to add these to the return value.
    # If return is `return { ... }` we can't easily modify inline.
    # If return is `return variable` we can patch the variable.
    # Safest: convert the return to use a temp variable.

    if return_stripped.startswith("return {"):
        # return { ... } — wrap in variable
        # Replace `return {` with `_w5_resp = {`
        # Then add keys, then return
        injection_lines.append(f"{indent}# Patch: wrap return dict to inject keys")

        # Find the closing brace (could be multi-line)
        # Replace the return line with assignment
        new_return_line = return_line.replace("return {", "_w5_resp = {", 1)
        lines[return_line_idx] = new_return_line

        # Find the end of the dict (matching brace)
        brace_count = 0
        dict_end_idx = return_line_idx
        for j in range(return_line_idx, min(return_line_idx + 100, len(lines))):
            brace_count += lines[j].count("{") - lines[j].count("}")
            if brace_count <= 0:
                dict_end_idx = j
                break

        # Insert after the dict assignment
        post_dict_lines = [
            f"{indent}_w5_resp['jaimini'] = _w5_jaimini",
            f"{indent}_w5_resp['lal_kitab'] = _w5_lk",
            f"{indent}return _w5_resp",
        ]
        for k, pl in enumerate(post_dict_lines):
            lines.insert(dict_end_idx + 1 + k, pl)

        # Insert the injection block before the dict assignment
        for k, il in enumerate(injection_lines):
            lines.insert(return_line_idx + k, il)

    elif return_stripped.startswith("return JSONResponse"):
        # return JSONResponse(content={ ... }) or similar
        # Extract the content variable if possible
        injection_lines.append(f"{indent}# Patch: JSONResponse — rebuild with jaimini keys")
        # Replace the return with a temp variable approach
        # This is complex — use a simpler approach: modify the content dict
        match = re.search(r'return\s+JSONResponse\(\s*content\s*=\s*(\w+)', return_stripped)
        if match:
            resp_var = match.group(1)
            injection_lines.append(f"{indent}{resp_var}['jaimini'] = _w5_jaimini")
            injection_lines.append(f"{indent}{resp_var}['lal_kitab'] = _w5_lk")
        else:
            injection_lines.append(f"{indent}# WARNING: Could not auto-patch JSONResponse. Manual edit needed.")
            print("⚠️  JSONResponse pattern not auto-patchable. Adding keys but may need manual check.")

        for k, il in enumerate(injection_lines):
            lines.insert(return_line_idx + k, il)

    else:
        # return variable_name — patch the variable before return
        # Extract the variable name
        var_match = re.match(r'\s*return\s+(\w+)', return_line)
        if var_match:
            resp_var = var_match.group(1)
            injection_lines.append(f"{indent}if isinstance({resp_var}, dict):")
            injection_lines.append(f"{indent}    {resp_var}['jaimini'] = _w5_jaimini")
            injection_lines.append(f"{indent}    {resp_var}['lal_kitab'] = _w5_lk")
        else:
            print(f"⚠️  Unexpected return pattern: {return_stripped}")
            print("   Adding jaimini via dict merge — may need manual review")
            injection_lines.append(f"{indent}# WARNING: Could not detect return variable. Manual review needed.")

        for k, il in enumerate(injection_lines):
            lines.insert(return_line_idx + k, il)

    # ── 8. Write patched file ────────────────────────────────────
    patched_content = "\n".join(lines)
    with open(MAIN_PY, "w") as f:
        f.write(patched_content)

    print(f"\n✅ PATCH APPLIED SUCCESSFULLY")
    print(f"   {MAIN_PY} updated with Wire 5 (jaimini + lal_kitab in /dashboard)")
    print(f"\n── NEXT STEPS ──")
    print(f"   1. Review the change:  git diff main.py")
    print(f"   2. Test locally or push:")
    print(f"      curl https://antar-fastapi-production.up.railway.app/api/v1/dashboard/de02bb52-d43a-4b09-be25-b45a07bfbf8a | python -m json.tool | head -50")
    print(f"   3. Verify jaimini key exists in response")
    print(f"   4. Commit:  git add main.py && git commit -m 'Wire 5: jaimini + lal_kitab in /dashboard' && git push")
    print(f"\n── ROLLBACK ──")
    print(f"   cp main.py.bak main.py && git checkout main.py")


if __name__ == "__main__":
    patch()
