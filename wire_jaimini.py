#!/usr/bin/env python3
"""
Wire 4 + 5: Prashna triple-lock + Dashboard jaimini key
Run: python3 wire_4_5.py
"""

with open("main.py", "r") as f:
    lines = f.readlines()

content = "".join(lines)
changes = 0

# ═══════════════════════════════════════
# WIRE 4: PRASHNA — find line 3822 area
# Insert before the return that has "verdict"
# ═══════════════════════════════════════

if "Jaimini Triple-Lock" not in content:
    # Find @app.post("/api/v1/prashna") 
    prashna_line = None
    for i, line in enumerate(lines):
        if "/api/v1/prashna" in line and "app.post" in line:
            prashna_line = i
            break

    if prashna_line:
        # Find the return { that contains "verdict" after the prashna endpoint
        return_line = None
        for i in range(prashna_line, min(prashna_line + 200, len(lines))):
            if "return {" in lines[i] or "return{" in lines[i]:
                # Check if "verdict" appears in the next few lines
                snippet = "".join(lines[i:i+15])
                if "verdict" in snippet:
                    return_line = i
                    break

        if return_line:
            indent = "        "  # Match the indentation
            block = [
                f"\n",
                f"{indent}# --- Jaimini Triple-Lock ---\n",
                f"{indent}try:\n",
                f'{indent}    _q_map = {{"marriage":"marriage","love":"marriage","relationship":"marriage",\n',
                f'{indent}              "investment":"investment","wealth":"investment","money":"investment",\n',
                f'{indent}              "lawsuit":"lawsuit","legal":"lawsuit","court":"lawsuit",\n',
                f'{indent}              "abroad":"foreign","travel":"foreign","visa":"foreign"}}\n',
                f'{indent}    _q_text = str(getattr(request, "question", "")).lower()\n',
                f"{indent}    _q_type = next((v for k,v in _q_map.items() if k in _q_text), None)\n",
                f"{indent}    if _q_type:\n",
                f"{indent}        _jc = jaimini_prashna_check(chart_data, _q_type, 0)\n",
                f'{indent}        if _jc.get("jaimini_verdict"):\n',
                f'{indent}            result["jaimini_confirms"] = True\n',
                f'{indent}            result["jaimini_reasons"] = _jc.get("reasons", [])\n',
                f"{indent}except Exception:\n",
                f"{indent}    pass\n",
                f"\n",
            ]
            for k, b in enumerate(block):
                lines.insert(return_line + k, b)
            changes += 1
            print(f"✓ WIRE 4: Prashna triple-lock added before line {return_line + 1}")
        else:
            print("✗ WIRE 4: Could not find return block with verdict after /prashna")
    else:
        print("✗ WIRE 4: Could not find /api/v1/prashna endpoint")
else:
    print("⚠ WIRE 4: Already wired")

# Rebuild content after wire 4
content = "".join(lines)

# ═══════════════════════════════════════
# WIRE 5: DASHBOARD — find line 4919 area
# Add jaimini key after lal_kitab in response
# ═══════════════════════════════════════

if '"jaimini"' not in content[content.index("async def get_dashboard"):] if "async def get_dashboard" in content else True:
    # Find the dashboard endpoint
    dash_line = None
    for i, line in enumerate(lines):
        if "async def get_dashboard" in line:
            dash_line = i
            break

    if dash_line:
        # Find "return response_dict" or the response builder in the dashboard
        insert_line = None
        for i in range(dash_line, min(dash_line + 300, len(lines))):
            if "return response_dict" in lines[i]:
                insert_line = i
                break

        if not insert_line:
            # Try finding where response_dict is returned differently
            for i in range(dash_line, min(dash_line + 300, len(lines))):
                if 'response_dict["lal_kitab"]' in lines[i] or "lal_kitab_data" in lines[i]:
                    insert_line = i + 1
                    break

        if insert_line:
            indent = "    "
            block = [
                f"\n",
                f"{indent}# --- Jaimini v2 for frontend ---\n",
                f"{indent}try:\n",
                f"{indent}    import json as _json\n",
                f'{indent}    _jd = r.get("jaimini_data") or {{}}\n',
                f"{indent}    if isinstance(_jd, str):\n",
                f"{indent}        _jd = _json.loads(_jd) if _jd else {{}}\n",
                f'{indent}    response_dict["jaimini"] = {{\n',
                f'{indent}        "karakas": _jd.get("karakas", []),\n',
                f'{indent}        "arudha_lagna": _jd.get("arudha_lagna", {{}}),\n',
                f'{indent}        "upapada_lagna": _jd.get("upapada_lagna", {{}}),\n',
                f'{indent}        "karakamsa": _jd.get("karakamsa", {{}}),\n',
                f'{indent}        "current_md": _jd.get("current_md"),\n',
                f'{indent}        "current_ad": _jd.get("current_ad"),\n',
                f'{indent}        "predictions": _jd.get("predictions", []),\n',
                f"{indent}    }}\n",
                f"{indent}except Exception:\n",
                f'{indent}    response_dict["jaimini"] = {{}}\n',
                f"\n",
            ]
            for k, b in enumerate(block):
                lines.insert(insert_line + k, b)
            changes += 1
            print(f"✓ WIRE 5: Dashboard jaimini key added at line {insert_line + 1}")
        else:
            print("✗ WIRE 5: Could not find insertion point in dashboard")
    else:
        print("✗ WIRE 5: Could not find get_dashboard function")
else:
    print("⚠ WIRE 5: Already wired")

# Save
if changes > 0:
    with open("main.py", "w") as f:
        f.writelines(lines)
    print(f"\n✅ {changes}/2 wired. Now run:")
    print("  git add main.py && git commit -m 'wire: prashna + dashboard Jaimini' && git push")
else:
    print("\nNo changes made.")
