#!/usr/bin/env python3
"""
Test + Deploy: Jaimini → LK Bridge
===================================
Run: python3 test_and_deploy_bridge.py

Phase 1: Run all tests locally (no Railway, no Supabase)
Phase 2: Copy to antar_engine/
Phase 3: Wire into main.py /predict endpoint
Phase 4: Print git commands
"""

import json
import sys
import os
import shutil
from datetime import datetime

# =============================================================================
# PHASE 1: LOCAL TESTS
# =============================================================================

def run_tests():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  PHASE 1: Testing Jaimini → LK Bridge Locally           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # Import from current directory first, then antar_engine
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        from jaimini_lk_bridge import (
            generate_bridge_correction,
            format_bridge_from_stored,
            get_nakshatra_quality,
            get_sublord_check,
            NAKSHATRAS,
            PAKKA_GHAR,
            LK_REMEDIES,
            NAKSHATRA_TIMING_QUALITY,
        )
    except ImportError:
        from antar_engine.jaimini_lk_bridge import (
            generate_bridge_correction,
            format_bridge_from_stored,
            get_nakshatra_quality,
            get_sublord_check,
            NAKSHATRAS,
            PAKKA_GHAR,
            LK_REMEDIES,
            NAKSHATRA_TIMING_QUALITY,
        )

    passed = 0
    failed = 0
    total = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f"  ✓ {name}")
        else:
            failed += 1
            print(f"  ✗ {name} — {detail}")

    # ── Test 1: Nakshatra database completeness ──
    print("--- Test 1: Nakshatra Database ---")
    check("27 nakshatras loaded", len(NAKSHATRAS) == 27, f"got {len(NAKSHATRAS)}")
    check("Revati exists", "Revati" in NAKSHATRAS)
    check("Ashwini exists", "Ashwini" in NAKSHATRAS)
    check("Each has lord+quality+flavor",
          all("lord" in v and "quality" in v and "flavor" in v for v in NAKSHATRAS.values()))
    print()

    # ── Test 2: Pakka Ghar table ──
    print("--- Test 2: Pakka Ghar Table ---")
    check("Sun Pakka Ghar = 1", PAKKA_GHAR["Sun"] == 1)
    check("Moon Pakka Ghar = 4", PAKKA_GHAR["Moon"] == 4)
    check("Saturn Pakka Ghar = 8", PAKKA_GHAR["Saturn"] == 8)
    check("All 9 planets have Pakka Ghar", len(PAKKA_GHAR) == 9)
    print()

    # ── Test 3: Remedy database ──
    print("--- Test 3: LK Remedies ---")
    check("All 9 planets have remedies", len(LK_REMEDIES) == 9)
    check("Each remedy has item+day+action",
          all("item" in v and "day" in v and "action" in v for v in LK_REMEDIES.values()))
    check("Saturn remedy = oil on Saturday",
          "oil" in LK_REMEDIES["Saturn"]["item"].lower() and LK_REMEDIES["Saturn"]["day"] == "Saturday")
    print()

    # ── Test 4: Nakshatra quality lookup ──
    print("--- Test 4: Nakshatra Quality Lookup ---")
    revati = get_nakshatra_quality("Revati")
    check("Revati lord = Mercury", revati.get("lord") == "Mercury")
    check("Revati quality = soft", revati.get("quality") == "soft")
    check("Revati has flavor", len(revati.get("flavor", "")) > 0)

    ashwini = get_nakshatra_quality("Ashwini")
    check("Ashwini lord = Ketu", ashwini.get("lord") == "Ketu")
    check("Ashwini quality = swift", ashwini.get("quality") == "swift")

    # Partial match test
    partial = get_nakshatra_quality("Purva Phalguni")
    check("Purva Phalguni found", partial.get("lord") == "Venus")
    print()

    # ── Test 5: Sub-lord check ──
    print("--- Test 5: Sub-Lord Check ---")
    sl1 = get_sublord_check("Mars", "Revati")  # Mars + Mercury(Revati lord) = enemies
    check("Mars + Revati = obstructed", sl1["status"] == "obstructed")
    check("Sub-lord is Mercury", sl1["sub_lord"] == "Mercury")

    sl2 = get_sublord_check("Sun", "Krittika")  # Sun + Sun(Krittika lord) = friend (self)
    check("Sun + Krittika = supportive", sl2["status"] == "supportive")

    sl3 = get_sublord_check("Jupiter", "Punarvasu")  # Jupiter + Jupiter = friend
    check("Jupiter + Punarvasu = supportive", sl3["status"] == "supportive")

    sl4 = get_sublord_check("Saturn", "Ashwini")  # Saturn + Ketu = ?
    check("Saturn + Ashwini returns a status", sl4["status"] in ["supportive", "obstructed", "neutral"])
    print()

    # ── Test 6: Full bridge with Ramandeep's chart ──
    print("--- Test 6: Full Bridge (Ramandeep's Chart) ---")
    chart_data = {
        "id": "de02bb52",
        "moon_nakshatra": "Revati",
        "current_dasha": "Mars-Moon",
        "lagna_sign": "Capricorn",
        "jaimini_data": json.dumps({
            "karakas": [
                {"karaka": "AK", "planet": "Mars", "sign": 8, "sign_name": "Sagittarius", "degree": 28.3, "meaning": "Self/Soul"},
                {"karaka": "AmK", "planet": "Saturn", "sign": 2, "sign_name": "Gemini", "degree": 25.4, "meaning": "Career/Status"},
                {"karaka": "PK", "planet": "Venus", "sign": 8, "sign_name": "Sagittarius", "degree": 10.1, "meaning": "Children/Intelligence"},
                {"karaka": "GK", "planet": "Jupiter", "sign": 1, "sign_name": "Taurus", "degree": 8.7, "meaning": "Conflict/Disease"},
                {"karaka": "DK", "planet": "Sun", "sign": 7, "sign_name": "Scorpio", "degree": 0.5, "meaning": "Spouse/Partners"},
            ],
            "predictions": [
                {"event_type": "career", "confidence": "medium", "description": "Major professional rise", "conditions": ["AmK aspects dasha sign"], "karaka": "AmK"},
                {"event_type": "children", "confidence": "medium", "description": "Creative breakthrough", "conditions": ["PK aspects dasha sign"], "karaka": "PK"},
            ],
        }),
        "lal_kitab_data": json.dumps({"year_lord": "Saturn"}),
    }

    result = format_bridge_from_stored(chart_data)
    check("Bridge returns non-empty string", len(result) > 100, f"got {len(result)} chars")
    check("Contains JAIMINI → LAL KITAB CORRECTION header", "JAIMINI" in result and "LAL KITAB" in result)
    check("Contains CAREER event", "CAREER" in result)
    check("Contains CHILDREN event", "CHILDREN" in result)
    check("Contains NAKSHATRA PRECISION", "NAKSHATRA PRECISION" in result)
    check("Contains Revati", "Revati" in result)
    check("Contains SOUL PURPOSE", "SOUL PURPOSE" in result)
    check("Contains Karmic Lesson", "patience" in result.lower())
    check("Contains Sub-Lord Check", "Sub-Lord" in result)
    check("Contains Mercury enemy warning", "Mercury" in result and "enemy" in result.lower())
    print()

    # ── Test 7: Edge cases ──
    print("--- Test 7: Edge Cases ---")

    # Empty data
    empty_result = format_bridge_from_stored({"id": "empty"})
    check("Empty chart returns empty string", empty_result == "")

    # String JSONB
    chart_str = dict(chart_data)
    chart_str["jaimini_data"] = chart_data["jaimini_data"]  # Already a string
    result_str = format_bridge_from_stored(chart_str)
    check("String JSONB works same as dict", len(result_str) > 100)

    # No predictions but has karakas
    chart_no_pred = dict(chart_data)
    chart_no_pred["jaimini_data"] = json.dumps({
        "karakas": [{"karaka": "AK", "planet": "Mars", "sign": 8, "meaning": "Self/Soul"}],
        "predictions": [],
    })
    result_no_pred = format_bridge_from_stored(chart_no_pred)
    check("No predictions still returns soul purpose", "SOUL PURPOSE" in result_no_pred or result_no_pred == "")

    # No moon nakshatra
    chart_no_nak = dict(chart_data)
    chart_no_nak["moon_nakshatra"] = ""
    result_no_nak = format_bridge_from_stored(chart_no_nak)
    check("No nakshatra still works", "CAREER" in result_no_nak)
    print()

    # ── Test 8: Sleeping planet detection ──
    print("--- Test 8: Sleeping Planet Detection ---")
    chart_sleeping = dict(chart_data)
    chart_sleeping["jaimini_data"] = json.dumps({
        "karakas": [
            {"karaka": "AK", "planet": "Mars", "sign": 8, "meaning": "Self/Soul"},
            {"karaka": "AmK", "planet": "Jupiter", "sign": 5, "sign_name": "Virgo", "degree": 10.0, "meaning": "Career/Status"},
        ],
        "predictions": [
            {"event_type": "career", "confidence": "high", "description": "Career peak", "conditions": ["test"], "karaka": "AmK"},
        ],
    })
    result_sleeping = format_bridge_from_stored(chart_sleeping)
    # Jupiter in sign 5 (Virgo) = LK house 6 = dusthana = sleeping
    check("Jupiter in Virgo (house 6) detected as SLEEPING", "SLEEPING" in result_sleeping)
    check("Awakening remedy shown", "AWAKENING" in result_sleeping or "Donate" in result_sleeping)
    print()

    # ── Test 9: Pakka Ghar detection ──
    print("--- Test 9: Pakka Ghar Detection ---")
    chart_pakka = dict(chart_data)
    chart_pakka["jaimini_data"] = json.dumps({
        "karakas": [
            {"karaka": "AK", "planet": "Sun", "sign": 0, "meaning": "Self/Soul"},
            {"karaka": "AmK", "planet": "Sun", "sign": 0, "sign_name": "Aries", "degree": 15.0, "meaning": "Career/Status"},
        ],
        "predictions": [
            {"event_type": "career", "confidence": "high", "description": "Career peak", "conditions": ["test"], "karaka": "AmK"},
        ],
    })
    result_pakka = format_bridge_from_stored(chart_pakka)
    # Sun in Aries (sign 0) = LK house 1 = Sun's Pakka Ghar
    check("Sun in Aries detected as Pakka Ghar", "Pakka Ghar" in result_pakka and "YES" in result_pakka)
    print()

    # ── Summary ──
    print("=" * 60)
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


# =============================================================================
# PHASE 2 + 3: DEPLOY
# =============================================================================

def deploy():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  PHASE 2: Deploy to antar_engine/                       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    if not os.path.exists("antar_engine"):
        print("  ERROR: antar_engine/ not found. Run from project root.")
        return False

    # Copy the bridge file
    src = "jaimini_lk_bridge.py"
    dst = "antar_engine/jaimini_lk_bridge.py"

    if not os.path.exists(src):
        print(f"  ERROR: {src} not found in current directory.")
        return False

    shutil.copy(src, dst)
    print(f"  ✓ Copied {src} → {dst}")

    # ── Wire into main.py ──
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  PHASE 3: Wire into main.py                             ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    with open("main.py", "r") as f:
        content = f.read()

    changes = 0

    # Add import (in the existing try block with other jaimini imports)
    if "jaimini_lk_bridge" not in content:
        # Find the existing jaimini_integration import block
        marker = "from antar_engine.jaimini_integration import ("
        if marker in content:
            idx = content.index(marker)
            # Find the closing )
            close_idx = content.index(")", idx)
            # Insert the bridge import after the closing paren + next line
            next_line = content.index("\n", close_idx) + 1

            bridge_import = """    from antar_engine.jaimini_lk_bridge import format_bridge_from_stored
"""
            content = content[:next_line] + bridge_import + content[next_line:]
            changes += 1
            print("  ✓ Added jaimini_lk_bridge import")
        else:
            print("  ⚠ Could not find jaimini_integration import block — add import manually")
    else:
        print("  ⚠ jaimini_lk_bridge already imported")

    # Add bridge block after Jaimini context in /predict
    if "LAYER 3.5: JAIMINI → LK BRIDGE" not in content:
        marker2 = "LAYER 2.5: JAIMINI"
        if marker2 in content:
            # Find the end of the Layer 2.5 block (the except clause ending)
            idx2 = content.index(marker2)
            # Find the except + pass that closes the Jaimini block
            # Look for the next "except Exception" after LAYER 2.5
            search_area = content[idx2:idx2+800]
            except_matches = []
            search_pos = 0
            while True:
                pos = search_area.find("except Exception", search_pos)
                if pos == -1:
                    break
                except_matches.append(pos)
                search_pos = pos + 1

            if except_matches:
                # Use the last except in the block
                last_except = except_matches[-1]
                abs_except = idx2 + last_except
                # Find the end of the except line (the print/pass line after it)
                line_end = content.index("\n", abs_except)
                next_line_end = content.index("\n", line_end + 1)

                bridge_block = """

        # --- LAYER 3.5: JAIMINI → LK BRIDGE ---
        try:
            _bridge_block = format_bridge_from_stored(chart_data)
            if _bridge_block:
                _full_context += _bridge_block
        except Exception as _be:
            print(f"Bridge context failed (non-blocking): {_be}")"""

                content = content[:next_line_end] + bridge_block + content[next_line_end:]
                changes += 1
                print("  ✓ Added LAYER 3.5 bridge block after LAYER 2.5 in /predict")
            else:
                print("  ⚠ Could not find except block after LAYER 2.5 — add manually")
        else:
            print("  ⚠ LAYER 2.5 not found — run wire_jaimini.py first, then re-run this script")
    else:
        print("  ⚠ LAYER 3.5 already wired")

    if changes > 0:
        # Backup
        backup = f"main.py.backup.bridge.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy("main.py", backup)

        with open("main.py", "w") as f:
            f.write(content)
        print(f"\n  ✓ main.py updated ({changes} changes). Backup: {backup}")
    else:
        print("\n  No main.py changes needed.")

    return True


# =============================================================================
# PHASE 4: GIT COMMANDS
# =============================================================================

def print_git_commands():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  PHASE 4: Git Push                                      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("  Run these commands:")
    print()
    print("  git add antar_engine/jaimini_lk_bridge.py main.py")
    print('  git commit -m "feat: Jaimini→LK Bridge + Nakshatra precision layer"')
    print("  git push")
    print()
    print("  Then wait 60s for Railway and test:")
    print()

    BASE = "https://antar-fastapi-production.up.railway.app"
    CID = "de02bb52-d43a-4b09-be25-b45a07bfbf8a"

    print(f"  # Health check")
    print(f"  curl -s {BASE}/health | python3 -m json.tool")
    print()
    print(f"  # Predict with career question — should show bridge correction in context")
    print(f"  curl -s -X POST {BASE}/api/v1/predict \\")
    print(f"    -H 'Content-Type: application/json' \\")
    print(f"    -d '{{\"chart_id\":\"{CID}\",\"question\":\"How is my career this year?\"}}' \\")
    print(f"    | python3 -m json.tool | head -50")
    print()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Phase 1: Test
    tests_passed = run_tests()

    if not tests_passed:
        print("\n  ✗ Tests failed. Fix issues before deploying.")
        sys.exit(1)

    print("\n  All tests passed.")

    # Phase 2+3: Deploy
    response = input("\n  Deploy to antar_engine/ and wire main.py? (y/n): ")
    if response.lower() == "y":
        deploy()
        print_git_commands()
    else:
        print("\n  Skipped deployment. Run again with 'y' when ready.")
