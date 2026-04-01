#!/usr/bin/env python3
"""
patch_prashna.py — Automated patcher for main.py
=================================================
Replaces the old /prashna endpoint with the new Ithasala engine wiring.

WHAT IT DOES:
1. Backs up main.py → main.py.bak_prashna
2. Adds the new import (if not already present)
3. Replaces the ask_prashna function with the new Ithasala-powered version
4. Keeps /prashna/followup and /prashna/session untouched

RUN:
    python patch_prashna.py

VERIFY:
    grep -n "run_prashna_engine" main.py
    grep -n "prashna_log" main.py
    grep -n "check_cooldown" main.py
"""

import os
import re
import shutil
import sys

MAIN_PY = "main.py"
BACKUP = "main.py.bak_prashna"

def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# ═══════════════════════════════════════════════════════════════════
# THE NEW ENDPOINT CODE
# ═══════════════════════════════════════════════════════════════════

NEW_ENDPOINT = '''@app.post("/api/v1/prashna")
async def ask_prashna(request: PrashnaRequest):
    """
    Prashna (Horary) Oracle — real-time YES/NO verdict engine.
    Uses Ithasala (Tajika) + 4-step scoring + Navamsa genuineness + VoC Moon.
    Python calculates ALL facts. Claude only explains in plain English.
    """
    import traceback
    from datetime import datetime, timezone

    try:
        chart_id = request.chart_id
        question = (request.question or "").strip()

        if not question:
            return JSONResponse(status_code=400, content={"error": "Question is required"})

        # ─── 1. Cooldown Check (24h between questions) ───
        try:
            last_prashna = supabase.table("prashna_log") \\
                .select("created_at") \\
                .eq("chart_id", chart_id) \\
                .order("created_at", desc=True) \\
                .limit(1) \\
                .execute()

            last_time = None
            if last_prashna.data and len(last_prashna.data) > 0:
                last_time = last_prashna.data[0].get("created_at")

            cooldown = check_cooldown(last_time, cooldown_hours=PRASHNA_COOLDOWN_HOURS)

            if not cooldown["allowed"]:
                return JSONResponse(status_code=429, content={
                    "error": "cooldown",
                    "message": cooldown.get("message", "Please wait before asking another question."),
                    "cooldown_until": cooldown.get("cooldown_until"),
                    "remaining_seconds": cooldown.get("remaining_seconds", 0),
                })
        except Exception as e:
            logger.warning(f"Cooldown check failed (table may not exist): {e}")

        # ─── 2. Fetch Chart Data ───
        chart_row = supabase.table("charts") \\
            .select("chart_data, jaimini_data, lal_kitab_data, current_dasha, first_name, current_country, lagna_sign, latitude, longitude") \\
            .eq("chart_id", chart_id) \\
            .single() \\
            .execute()

        if not chart_row.data:
            return JSONResponse(status_code=404, content={"error": "Chart not found"})

        chart_data = chart_row.data
        jaimini_data = chart_data.get("jaimini_data")
        natal_dasha = chart_data.get("current_dasha", "unknown")
        first_name = chart_data.get("first_name", "User")
        current_country = chart_data.get("current_country", "US")

        if isinstance(jaimini_data, str):
            try:
                jaimini_data = json.loads(jaimini_data)
            except Exception:
                jaimini_data = None

        # ─── 3. Coordinates: request > chart > default ───
        lat = request.lat
        lng = request.lng
        if not lat or lat == 28.6139:
            lat = chart_data.get("latitude") or 40.8215
        if not lng or lng == 77.2090:
            lng = chart_data.get("longitude") or -73.9876

        # ─── 4. Run Prashna Engine (Ithasala + 4-step scoring) ───
        timestamp = datetime.now(timezone.utc)
        locale = "IN" if current_country and current_country.upper() in ["IN", "INDIA"] else "global"

        engine_result = run_prashna_engine(
            question=question,
            lat=lat,
            lng=lng,
            timestamp=timestamp,
            jaimini_data=jaimini_data,
            natal_dasha=natal_dasha,
            user_name=first_name or "User",
            locale=locale,
        )

        # ─── 5. Call Claude to explain the verdict ───
        explanation = ""
        try:
            result_tuple = await call_llm(
                prompt=question,
                system_override=engine_result["claude_prompt"],
            )
            explanation = result_tuple[0] if isinstance(result_tuple, tuple) else result_tuple
        except Exception as claude_err:
            logger.error(f"Claude call failed for prashna: {claude_err}")
            bd = engine_result["breakdown"]
            explanation = (
                f"{engine_result['verdict']} ({engine_result['score']}%). "
                f"{bd['ithasala'].get('reason', '')}. "
                f"Timing: {engine_result['timing']}."
            )

        # ─── 6. Remedy Card ───
        wp = engine_result.get("weakest_planet", {})
        if locale == "IN":
            _rem_map = {
                "Sun": "Offer water to the Sun at sunrise. Donate wheat on Sundays.",
                "Moon": "Wear white on Mondays. Keep a silver item with you.",
                "Mercury": "Feed green vegetables to a cow. Donate on Wednesdays.",
                "Venus": "Donate white clothes on Fridays. Offer white flowers.",
                "Mars": "Donate red lentils on Tuesdays. Serve with physical effort.",
                "Jupiter": "Donate yellow items on Thursdays. Respect your teachers.",
                "Saturn": "Donate mustard oil on Saturdays. Serve the elderly.",
            }
        else:
            _rem_map = {
                "Sun": "Express confidence in one decision today. Lead from the front.",
                "Moon": "Practice emotional grounding — 5 minutes of stillness before any big call.",
                "Mercury": "Write your intention down. Clarity comes through articulation.",
                "Venus": "Express appreciation to someone who supports you this week.",
                "Mars": "Channel energy into physical action — exercise before the decision.",
                "Jupiter": "Express gratitude to a mentor or teacher this week.",
                "Saturn": "Commit to one disciplined action. Follow through completely.",
            }
        remedy = {
            "planet": wp.get("planet", "Saturn"),
            "practice": _rem_map.get(wp.get("planet", "Saturn"), "Take one deliberate action this week."),
            "why": f"{wp.get('planet', 'Saturn')} needs strengthening — {', '.join(wp.get('reasons', ['general']))}",
        }

        # ─── 7. Log to prashna_log ───
        try:
            supabase.table("prashna_log").insert({
                "chart_id": chart_id,
                "question": question,
                "domain": engine_result.get("domain"),
                "verdict": engine_result["verdict"],
                "score": engine_result["score"],
                "label": engine_result["label"],
                "timing": engine_result["timing"],
                "explanation": explanation,
                "breakdown": json.dumps(engine_result["breakdown"], default=str),
                "prashna_chart": json.dumps(engine_result["prashna_chart"], default=str),
                "weakest_planet": wp.get("planet"),
                "cooldown_until": engine_result["cooldown_until"],
            }).execute()
        except Exception as log_err:
            logger.warning(f"Failed to log prashna (non-blocking): {log_err}")

        # ─── 8. Also save to legacy prashna_readings for backward compat ───
        try:
            supabase.table("prashna_readings").insert({
                "chart_id":      chart_id,
                "question":      question,
                "question_type": engine_result.get("domain", "general"),
                "verdict":       engine_result["verdict"],
                "score":         engine_result["score"],
                "confidence":    engine_result["label"],
                "timing":        engine_result["timing"],
                "narrative":     explanation,
                "prashna_data":  {
                    "prashna_chart":  engine_result["prashna_chart"],
                    "lagna":          engine_result["prashna_chart"].get("lagna_sign"),
                    "moon_nakshatra": engine_result["prashna_chart"].get("moon_nakshatra"),
                    "yes_factors":    [],
                    "no_factors":     [],
                },
            }).execute()
        except Exception:
            pass

        # ─── 9. Return Response ───
        return {
            "verdict":       engine_result["verdict"],
            "score":         engine_result["score"],
            "label":         engine_result["label"],
            "confidence":    engine_result["label"],
            "domain":        engine_result["domain"],
            "timing":        engine_result["timing"],
            "explanation":   explanation,
            "narrative":     explanation,
            "remedy":        remedy,
            "breakdown": {
                "lagna_strength":   engine_result["breakdown"]["lagna_strength"]["score"],
                "lord_connection":  engine_result["breakdown"]["lord_connection"]["score"],
                "ithasala": {
                    "type":   engine_result["breakdown"]["ithasala"]["type"],
                    "score":  engine_result["breakdown"]["ithasala"]["score"],
                    "aspect": engine_result["breakdown"]["ithasala"].get("aspect"),
                },
                "moon_validation":  engine_result["breakdown"]["moon_validation"]["score"],
                "void_of_course":   engine_result["breakdown"].get("void_of_course", {}).get("void_of_course", False),
                "navamsa_genuine":  engine_result["breakdown"].get("navamsa_genuineness", {}).get("genuine", True),
                "mutual_reception": engine_result["breakdown"]["mutual_reception"].get("found", False),
                "edge_yoga":        engine_result["breakdown"]["edge_yoga"]["yoga"] if engine_result["breakdown"].get("edge_yoga") else None,
                "jaimini_locks":    engine_result["breakdown"]["jaimini_locks"],
            },
            "prashna_chart":  engine_result["prashna_chart"],
            "cooldown_until": engine_result["cooldown_until"],
            "natal_context":  engine_result["natal_context"],
            # Legacy fields for backward compatibility
            "question_type":  engine_result.get("domain", "general"),
            "lagna":          engine_result["prashna_chart"].get("lagna_sign"),
            "moon_nakshatra": engine_result["prashna_chart"].get("moon_nakshatra"),
            "yes_factors":    [],
            "no_factors":     [],
            "analysis":       {"explanation": explanation},
        }

    except Exception as e:
        logger.error(f"Prashna engine error: {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={
            "error": "Prashna engine failed",
            "detail": str(e),
        })

'''

# ═══════════════════════════════════════════════════════════════════
# THE NEW IMPORT LINE
# ═══════════════════════════════════════════════════════════════════

NEW_IMPORT = """from antar_engine.prashna_engine import (
    run_prashna_engine,
    check_cooldown,
    detect_prashna_intent,
    PRASHNA_COOLDOWN_HOURS,
)"""


def main():
    if not os.path.exists(MAIN_PY):
        print(f"❌ {MAIN_PY} not found. Run this from your project root.")
        sys.exit(1)

    content = read_file(MAIN_PY)
    original_len = len(content)
    lines = content.split("\n")

    print(f"📄 Read {MAIN_PY} ({len(lines)} lines, {original_len} chars)")

    # ─── Backup ───
    shutil.copy2(MAIN_PY, BACKUP)
    print(f"💾 Backed up to {BACKUP}")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 1: Add new import (if not already present)
    # ═══════════════════════════════════════════════════════════════
    if "run_prashna_engine" not in content:
        # Find the line with jaimini_prashna_check import and add after it
        # Or find any "from antar_engine" import block
        insert_idx = None

        for i, line in enumerate(lines):
            if "jaimini_prashna_check" in line:
                insert_idx = i + 1
                break

        if insert_idx is None:
            # Fallback: find last "from antar_engine" import
            for i, line in enumerate(lines):
                if line.strip().startswith("from antar_engine"):
                    insert_idx = i + 1

        if insert_idx is None:
            # Last resort: after all imports (find first blank line after imports)
            for i, line in enumerate(lines):
                if i > 20 and line.strip() == "" and not lines[i-1].strip().startswith(("import", "from")):
                    insert_idx = i
                    break

        if insert_idx:
            lines.insert(insert_idx, NEW_IMPORT)
            print(f"✅ PATCH 1: Added prashna_engine import at line {insert_idx + 1}")
        else:
            print("⚠️  PATCH 1: Could not find import location — add manually:")
            print(f"   {NEW_IMPORT}")
    else:
        print("✅ PATCH 1: Import already present (skipped)")

    # ═══════════════════════════════════════════════════════════════
    # PATCH 2: Replace the ask_prashna function
    # ═══════════════════════════════════════════════════════════════
    content = "\n".join(lines)

    # Find the start: @app.post("/api/v1/prashna")
    # Find the end: the next @app decorator or top-level def/class
    # We need to be careful not to eat /prashna/followup or /prashna/session

    # Strategy: find the decorator + function, then find where it ends
    # The function ends at the next line that starts with @ or "class " or "def " at column 0
    # and is NOT indented (i.e., it's a new top-level definition)

    pattern = re.compile(
        r'(@app\.post\("/api/v1/prashna"\)\n'  # The decorator
        r'async def ask_prashna\(request: PrashnaRequest\):.*?)'  # Function signature
        r'(?=\n@app\.|\nclass |\ndef [a-zA-Z])',  # Lookahead: next top-level item
        re.DOTALL
    )

    match = pattern.search(content)
    if match:
        old_code = match.group(0)
        old_lines = old_code.count("\n")
        content = content[:match.start()] + NEW_ENDPOINT + content[match.end():]
        print(f"✅ PATCH 2: Replaced ask_prashna ({old_lines} lines) with new Ithasala engine ({NEW_ENDPOINT.count(chr(10))} lines)")
    else:
        # Fallback: try a simpler pattern
        print("⚠️  Could not find exact function boundaries with regex. Trying line-by-line approach...")

        lines = content.split("\n")
        start_idx = None
        end_idx = None

        for i, line in enumerate(lines):
            if '@app.post("/api/v1/prashna")' in line and "followup" not in line and "session" not in line:
                start_idx = i
            elif start_idx is not None and end_idx is None:
                # Look for the next top-level decorator or definition
                if i > start_idx + 5:  # Skip at least a few lines
                    stripped = line.strip()
                    if (line.startswith("@app.") or
                        line.startswith("class ") or
                        (line.startswith("def ") and not line.startswith("    def ")) or
                        (stripped.startswith("@app.") and not line.startswith(" "))):
                        end_idx = i
                        break

        if start_idx is not None and end_idx is not None:
            old_block = "\n".join(lines[start_idx:end_idx])
            old_count = end_idx - start_idx
            new_lines = lines[:start_idx] + NEW_ENDPOINT.rstrip().split("\n") + ["", ""] + lines[end_idx:]
            content = "\n".join(new_lines)
            print(f"✅ PATCH 2: Replaced lines {start_idx+1}-{end_idx} ({old_count} lines) with new endpoint")
        else:
            print(f"❌ PATCH 2 FAILED: Could not find /prashna endpoint boundaries")
            print(f"   start_idx={start_idx}, end_idx={end_idx}")
            print(f"   You may need to replace manually.")
            # Still write the file with at least the import patch
            write_file(MAIN_PY, content)
            sys.exit(1)

    # ═══════════════════════════════════════════════════════════════
    # PATCH 3: Remove the old run_prashna import if present
    # ═══════════════════════════════════════════════════════════════
    # The old code has: from antar_engine.prashna_engine import run_prashna
    # inside the function body. Our new code doesn't need it (it's in the top-level import).
    # But since we replaced the whole function, it's already gone.

    # Also check if there's a standalone import of the old function
    old_import_pattern = "from antar_engine.prashna_engine import run_prashna\n"
    if old_import_pattern in content and "run_prashna_engine" in content:
        content = content.replace(old_import_pattern, "")
        print("✅ PATCH 3: Removed old 'import run_prashna' line")

    # ═══════════════════════════════════════════════════════════════
    # WRITE
    # ═══════════════════════════════════════════════════════════════
    write_file(MAIN_PY, content)
    new_lines_count = content.count("\n")
    print(f"\n📝 Written {MAIN_PY} ({new_lines_count} lines)")
    print(f"💾 Backup at {BACKUP}")

    # ═══════════════════════════════════════════════════════════════
    # VERIFY
    # ═══════════════════════════════════════════════════════════════
    print("\n═══ VERIFICATION ═══")
    checks = [
        ("run_prashna_engine", "New engine import"),
        ("check_cooldown", "Cooldown function"),
        ("PRASHNA_COOLDOWN_HOURS", "Cooldown constant"),
        ("prashna_log", "New log table"),
        ("claude_prompt", "Claude prompt from engine"),
        ("void_of_course", "Void of Course Moon"),
        ("navamsa_genuine", "Navamsa genuineness"),
        ("ithasala", "Ithasala verdict"),
        ("call_llm", "LLM call preserved"),
        ("prashna_readings", "Legacy table backward compat"),
    ]

    all_ok = True
    for term, label in checks:
        found = term in content
        status = "✅" if found else "❌"
        print(f"  {status} {label}: '{term}'")
        if not found:
            all_ok = False

    if all_ok:
        print(f"\n🎉 ALL PATCHES APPLIED SUCCESSFULLY")
        print(f"\nNext steps:")
        print(f"  1. Run the Supabase SQL to create prashna_log table")
        print(f"  2. git add . && git commit -m 'Sprint PR: Prashna Ithasala engine' && git push")
        print(f"  3. curl test after Railway deploys")
    else:
        print(f"\n⚠️  Some checks failed — review the output above")
        print(f"  Original backup at: {BACKUP}")


if __name__ == "__main__":
    main()
