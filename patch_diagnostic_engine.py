"""
patch_diagnostic_engine.py — Sprint 1.2: Diagnostic Middleware + Verification Endpoint

Patches main.py to:
1. Import symptom_library and verification_engine
2. Inject diagnostic pre-scan into /predict endpoint (before Claude call)
3. Pass chart_data to plain_english for doctor-mode prompt injection
4. Add GET /api/v1/verification/{chart_id} endpoint
5. Add GET /api/v1/dashboard-status/{chart_id} endpoint (live sensor data)

Run: python patch_diagnostic_engine.py
Backs up to: main.py.bak_diagnostic
"""

import os
import re
import shutil

TARGET = "main.py"
BACKUP = TARGET + ".bak_diagnostic"


def patch():
    if not os.path.exists(TARGET):
        print(f"ERROR: {TARGET} not found. Run from project root.")
        return False

    shutil.copy2(TARGET, BACKUP)
    print(f"✓ Backed up to {BACKUP}")

    with open(TARGET, "r") as f:
        content = f.read()

    # ═══════════════════════════════════════════════════════════════
    # PATCH 1: Add imports
    # ═══════════════════════════════════════════════════════════════

    new_imports = [
        "from antar_engine.symptom_library import scan_chart_symptoms, get_domain_status, build_diagnostic_prompt_block, get_primary_symptom, get_domain_vocabulary",
        "from antar_engine.verification_engine import generate_verification_queue, calculate_precision_score, get_verification_data",
    ]

    for imp in new_imports:
        module_name = imp.split("import")[0].strip().split("from ")[-1].strip()
        if module_name not in content:
            # Find last import and add after
            import_matches = list(re.finditer(r"^(?:from|import)\s+.+$", content, re.MULTILINE))
            if import_matches:
                pos = import_matches[-1].end()
                content = content[:pos] + "\n" + imp + content[pos:]
                print(f"✓ Added import: {module_name}")
            else:
                content = imp + "\n" + content
                print(f"✓ Added import (at top): {module_name}")
        else:
            print(f"⊘ Import already exists: {module_name}")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 2: Inject diagnostic pre-scan into /predict endpoint
    # Find the spot where chart_data is available but before Claude call
    # ═══════════════════════════════════════════════════════════════

    diagnostic_marker = "# --- DIAGNOSTIC PRE-SCAN (Sprint 1.2) ---"
    
    if diagnostic_marker not in content:
        # Look for where the Claude call happens in /predict
        # Usually: response = await call_llm( or similar
        # We need to inject BEFORE this, AFTER chart_data is loaded
        
        # Strategy: find "extra_blocks" or "prompt_blocks" or similar list
        # that gets passed to Claude, and append diagnostic block to it
        
        # Look for the pattern where extra context blocks are assembled
        extra_blocks_pattern = r"(extra_blocks\s*=\s*\[\]|prompt_extra\s*=\s*\[\]|extra_context\s*=\s*\[\])"
        eb_match = re.search(extra_blocks_pattern, content)
        
        if eb_match:
            insert_pos = eb_match.end()
            
            diagnostic_code = f"""
    {diagnostic_marker}
    diagnostic_block = ""
    active_symptoms = []
    try:
        # chart_data should already be loaded at this point
        if chart_data and isinstance(chart_data, dict) and chart_data.get("planets"):
            diagnostic_block = build_diagnostic_prompt_block(
                chart_data,
                request.question if hasattr(request, 'question') else "",
                request.concern if hasattr(request, 'concern') else None
            )
            active_symptoms = scan_chart_symptoms(chart_data)
            if diagnostic_block:
                extra_blocks.append(diagnostic_block)
                logger.info(f"Diagnostic pre-scan: {{len(active_symptoms)}} symptoms detected")
    except Exception as e:
        logger.warning(f"Diagnostic pre-scan failed (non-critical): {{e}}")
        diagnostic_block = ""
    # --- END DIAGNOSTIC PRE-SCAN ---
"""
            content = content[:insert_pos] + diagnostic_code + content[insert_pos:]
            print("✓ Injected diagnostic pre-scan into /predict")
        else:
            # Alternative: look for where dkp_block or lk_block is added
            alt_pattern = r"(dkp_block\s*=|lk_block\s*=)"
            alt_match = re.search(alt_pattern, content)
            if alt_match:
                # Find the end of this block's section
                next_newline = content.find("\n\n", alt_match.end())
                if next_newline > 0:
                    diagnostic_code_alt = f"""

    {diagnostic_marker}
    diagnostic_block = ""
    try:
        if chart_data and isinstance(chart_data, dict):
            diagnostic_block = build_diagnostic_prompt_block(
                chart_data,
                request.question if hasattr(request, 'question') else "",
                concern if 'concern' in dir() else None
            )
            if diagnostic_block:
                # Will be injected into prompt via extra context
                pass
    except Exception as e:
        logger.warning(f"Diagnostic pre-scan failed: {{e}}")
        diagnostic_block = ""
    # --- END DIAGNOSTIC PRE-SCAN ---
"""
                    content = content[:next_newline] + diagnostic_code_alt + content[next_newline:]
                    print("✓ Injected diagnostic pre-scan (alternative location)")
            else:
                print("⚠ Could not find injection point for diagnostic pre-scan")
                print("  MANUAL: Add diagnostic_block = build_diagnostic_prompt_block(chart_data, question, concern)")
                print("  AFTER chart_data is loaded, BEFORE Claude call")
    else:
        print("⊘ Diagnostic pre-scan already exists")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 3: Pass chart_data into plain_english call
    # ═══════════════════════════════════════════════════════════════

    pe_call_marker = "generate_plain_english"
    
    if pe_call_marker in content and "'chart_data'" not in content.split(pe_call_marker)[1][:500]:
        # Find the chart_context dict that's passed to generate_plain_english
        chart_context_pattern = r"(chart_context\s*=\s*\{[^}]+\})"
        cc_match = re.search(chart_context_pattern, content)
        
        if cc_match:
            old_context = cc_match.group(0)
            if "'chart_data'" not in old_context and '"chart_data"' not in old_context:
                # Add chart_data to the context dict
                new_context = old_context.rstrip("}")
                if new_context.rstrip().endswith(","):
                    new_context += "\n        'chart_data': chart_data,\n    }"
                else:
                    new_context += ",\n        'chart_data': chart_data,\n    }"
                content = content.replace(old_context, new_context, 1)
                print("✓ Added chart_data to plain_english chart_context")
            else:
                print("⊘ chart_data already in chart_context")
        else:
            print("⚠ Could not find chart_context dict — add manually")
    else:
        print("⊘ chart_data reference already near generate_plain_english")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 4: Add GET /api/v1/verification/{chart_id} endpoint
    # ═══════════════════════════════════════════════════════════════

    verification_endpoint_marker = "/api/v1/verification/"
    
    if verification_endpoint_marker not in content:
        verification_endpoint = '''

# ═══════════════════════════════════════════════════════════════
# VERIFICATION QUEUE — Sprint 1.4
# Generates binary verification questions from dasha history
# Powers the Precision Score gamification loop
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/verification/{chart_id}")
async def get_verification(chart_id: str):
    """
    Returns verification queue + precision score.
    Frontend uses this for the interactive Level Ring / SYSTEM AUDIT drawer.
    """
    try:
        data = await get_verification_data(chart_id, supabase)
        return data
    except Exception as e:
        logger.error(f"Verification endpoint failed: {e}")
        return {
            "verification_queue": [],
            "precision_score": {"level": 1, "level_display": "1", "total_rated": 0, "accuracy_pct": 0, "next_level_in": 2, "max_level": 10},
            "has_pending": False,
            "message": "Verification data unavailable.",
        }

'''
        # Find the last endpoint definition and add after
        endpoint_pattern = r'(@app\.(get|post|put|delete)\s*\([^)]+\))'
        ep_matches = list(re.finditer(endpoint_pattern, content))
        
        if ep_matches:
            # Find the end of the last endpoint's function body
            last_ep = ep_matches[-1]
            # Find the next @app. or end of file
            next_ep = re.search(r'\n@app\.', content[last_ep.end():])
            if next_ep:
                insert_pos = last_ep.end() + next_ep.start()
            else:
                insert_pos = len(content)
            
            content = content[:insert_pos] + verification_endpoint + content[insert_pos:]
            print("✓ Added GET /api/v1/verification/{chart_id} endpoint")
        else:
            content += verification_endpoint
            print("✓ Added verification endpoint (at end of file)")
    else:
        print("⊘ Verification endpoint already exists")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 5: Add GET /api/v1/dashboard-status/{chart_id} endpoint
    # Dashboard live sensor data with active symptoms
    # ═══════════════════════════════════════════════════════════════

    dashboard_status_marker = "/api/v1/dashboard-status/"
    
    if dashboard_status_marker not in content:
        dashboard_endpoint = '''

# ═══════════════════════════════════════════════════════════════
# DASHBOARD STATUS — Sprint 1.2
# Returns live sensor data with active symptoms for each domain
# Powers the "Flight Deck" dashboard view
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/dashboard-status/{chart_id}")
async def get_dashboard_status(chart_id: str):
    """
    Returns the diagnostic status for all 4 domains + precision score.
    Used by the frontend Status tab to show AUTHORITY ENGINE: HIGH FRICTION etc.
    """
    try:
        # Load chart data
        chart_result = supabase.table("charts").select("chart_data").eq("id", chart_id).single().execute()
        if not chart_result.data:
            return {"error": "Chart not found"}, 404
        
        chart_data = chart_result.data.get("chart_data", {})
        
        # Get domain status from symptom library
        domain_status = get_domain_status(chart_data)
        
        # Get precision score
        precision = await calculate_precision_score(chart_id, supabase)
        
        # Get all active symptoms
        all_symptoms = scan_chart_symptoms(chart_data)
        
        return {
            "domains": {
                "career": {
                    "label": "AUTHORITY ENGINE",
                    **domain_status.get("career", {}),
                },
                "wealth": {
                    "label": "CAPITAL RUNWAY",
                    **domain_status.get("wealth", {}),
                },
                "relationship": {
                    "label": "ALLIANCE SYNC",
                    **domain_status.get("relationship", {}),
                },
                "health": {
                    "label": "SYSTEM VITALS",
                    **domain_status.get("health", {}),
                },
            },
            "precision_score": precision,
            "total_active_symptoms": len(all_symptoms),
            "critical_symptoms": [s for s in all_symptoms if s["verdict"] in ("HIBERNATE", "RETREAT AND RESET", "PLUG THE LEAK", "RECOVERY MODE")],
        }
    except Exception as e:
        logger.error(f"Dashboard status failed: {e}")
        return {
            "domains": {},
            "precision_score": {"level": 1, "total_rated": 0},
            "total_active_symptoms": 0,
            "critical_symptoms": [],
        }

'''
        # Insert after the verification endpoint we just added
        ver_ep_idx = content.find(verification_endpoint_marker)
        if ver_ep_idx > 0:
            # Find the end of the verification endpoint function
            next_at = content.find("\n@app.", ver_ep_idx + 10)
            if next_at > 0:
                content = content[:next_at] + dashboard_endpoint + content[next_at:]
            else:
                content += dashboard_endpoint
        else:
            content += dashboard_endpoint
        
        print("✓ Added GET /api/v1/dashboard-status/{chart_id} endpoint")
    else:
        print("⊘ Dashboard status endpoint already exists")

    # ═══════════════════════════════════════════════════════════════
    # WRITE
    # ═══════════════════════════════════════════════════════════════

    with open(TARGET, "w") as f:
        f.write(content)

    print(f"\n✓ Patched {TARGET}")
    print(f"  Backup: {BACKUP}")
    print(f"\n  DEPLOYMENT:")
    print(f"  1. Copy symptom_library.py to antar_engine/symptom_library.py")
    print(f"  2. Copy verification_engine.py to antar_engine/verification_engine.py")
    print(f"  3. Run: python patch_doctor_mode.py (patches plain_english.py)")
    print(f"  4. Run: python patch_diagnostic_engine.py (patches main.py)")
    print(f"  5. Test: curl https://antar-fastapi-production.up.railway.app/api/v1/verification/de02bb52-d43a-4b09-be25-b45a07bfbf8a")
    print(f"  6. Test: curl https://antar-fastapi-production.up.railway.app/api/v1/dashboard-status/de02bb52-d43a-4b09-be25-b45a07bfbf8a")
    print(f"  7. Test: ask a career question — response should start with ✦ VERDICT:")
    print(f"  8. Deploy: git add -A && git commit -m 'feat: diagnostic engine + verification queue + doctor mode' && git push")
    
    return True


if __name__ == "__main__":
    patch()
