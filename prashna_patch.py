#!/usr/bin/env python3
"""
patch_prashna_v2.py — Fixed patcher for main.py
================================================
v2 fix: inserts import AFTER the jaimini_integration closing ), not inside it.

RUN:   cp main.py.bak_prashna main.py   (restore first if v1 broke it)
THEN:  python patch_prashna_v2.py
UNDO:  cp main.py.bak_prashna main.py
"""
import os, sys, shutil

MAIN_PY = "main.py"
BACKUP  = "main.py.bak_prashna"

# The import to add — indented with 4 spaces because it's inside a try: block
NEW_IMPORT_LINES = [
    "    from antar_engine.prashna_engine import (",
    "        run_prashna_engine,",
    "        check_cooldown,",
    "        detect_prashna_intent,",
    "        PRASHNA_COOLDOWN_HOURS,",
    "    )",
]

NEW_BLOCK = r'''class PrashnaRequest(BaseModel):
    question:        str
    chart_id:        Optional[str] = None
    lat:             Optional[float] = 28.6139
    lng:             Optional[float] = 77.2090
    language:        Optional[str] = "en"
    generate_answer: Optional[bool] = True


@app.post("/api/v1/prashna")
async def ask_prashna(request: PrashnaRequest):
    """
    Prashna (Horary) Oracle — Ithasala + Tajika verdict engine.
    Python calculates ALL facts. Claude only explains.
    """
    import traceback
    from datetime import datetime, timezone

    try:
        chart_id = request.chart_id
        question = (request.question or "").strip()

        if not question:
            return JSONResponse(status_code=400, content={"error": "Question is required"})

        # ─── 1. Cooldown Check ───
        try:
            last_prashna = supabase.table("prashna_log") \
                .select("created_at") \
                .eq("chart_id", chart_id) \
                .order("created_at", desc=True) \
                .limit(1) \
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
            logger.warning(f"Cooldown check failed (table may not exist yet): {e}")

        # ─── 2. Fetch Chart Data ───
        chart_row = None
        jaimini_data = None
        natal_dasha = "unknown"
        first_name = "User"
        current_country = "US"
        db_lat = None
        db_lng = None

        if chart_id:
            try:
                chart_row = supabase.table("charts") \
                    .select("chart_data, jaimini_data, lal_kitab_data, current_dasha, first_name, current_country, lagna_sign, latitude, longitude") \
                    .eq("chart_id", chart_id) \
                    .maybe_single() \
                    .execute()

                if not chart_row or not chart_row.data:
                    chart_row = supabase.table("charts") \
                        .select("chart_data, jaimini_data, lal_kitab_data, current_dasha, first_name, current_country, lagna_sign, latitude, longitude") \
                        .eq("id", chart_id) \
                        .maybe_single() \
                        .execute()
            except Exception as db_err:
                logger.warning(f"Chart fetch error: {db_err}")

            if chart_row and chart_row.data:
                _cd = chart_row.data
                jaimini_data = _cd.get("jaimini_data")
                natal_dasha = _cd.get("current_dasha", "unknown")
                first_name = _cd.get("first_name", "User")
                current_country = _cd.get("current_country", "US")
                db_lat = _cd.get("latitude")
                db_lng = _cd.get("longitude")

                if isinstance(jaimini_data, str):
                    try:
                        jaimini_data = json.loads(jaimini_data)
                    except Exception:
                        jaimini_data = None

        # ─── 3. Coordinates ───
        lat = request.lat
        lng = request.lng
        if not lat or lat == 28.6139:
            lat = db_lat or 40.8215
        if not lng or lng == 77.2090:
            lng = db_lng or -73.9876

        # ─── 4. Run Prashna Engine ───
        timestamp = datetime.now(timezone.utc)
        locale = "IN" if current_country and str(current_country).upper() in ["IN", "INDIA"] else "global"

        engine_result = run_prashna_engine(
            question=question,
            lat=float(lat),
            lng=float(lng),
            timestamp=timestamp,
            jaimini_data=jaimini_data,
            natal_dasha=natal_dasha,
            user_name=first_name or "User",
            locale=locale,
        )

        # ─── 5. Claude explains the verdict ───
        explanation = ""
        if request.generate_answer:
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
            _rmap = {
                "Sun": "Offer water to the Sun at sunrise. Donate wheat on Sundays.",
                "Moon": "Wear white on Mondays. Keep a silver item with you.",
                "Mercury": "Feed green vegetables to a cow. Donate on Wednesdays.",
                "Venus": "Donate white clothes on Fridays. Offer white flowers.",
                "Mars": "Donate red lentils on Tuesdays. Serve with physical effort.",
                "Jupiter": "Donate yellow items on Thursdays. Respect your teachers.",
                "Saturn": "Donate mustard oil on Saturdays. Serve the elderly.",
            }
        else:
            _rmap = {
                "Sun": "Express confidence in one decision today. Lead from the front.",
                "Moon": "Practice emotional grounding — 5 minutes of stillness before any big call.",
                "Mercury": "Write your intention down. Clarity comes through articulation.",
                "Venus": "Express appreciation to someone who supports you this week.",
                "Mars": "Channel energy into physical action — exercise before the decision.",
                "Jupiter": "Express gratitude to a mentor or teacher this week.",
                "Saturn": "Commit to one disciplined action. Follow through completely.",
            }
        remedy = _rmap.get(wp.get("planet", "Saturn"), "Take one deliberate action this week.")

        # ─── 7. Log to prashna_log ───
        try:
            supabase.table("prashna_log").insert({
                "chart_id":       chart_id,
                "question":       question,
                "domain":         engine_result.get("domain"),
                "verdict":        engine_result["verdict"],
                "score":          engine_result["score"],
                "label":          engine_result["label"],
                "timing":         engine_result["timing"],
                "explanation":    explanation,
                "breakdown":      json.dumps(engine_result["breakdown"], default=str),
                "prashna_chart":  json.dumps(engine_result["prashna_chart"], default=str),
                "weakest_planet": wp.get("planet"),
                "cooldown_until": engine_result["cooldown_until"],
            }).execute()
        except Exception as log_err:
            logger.warning(f"prashna_log insert failed (non-blocking): {log_err}")

        # ─── 8. Legacy prashna_readings ───
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

        # ─── 9. Return ───
        return {
            "question":       question,
            "verdict":        engine_result["verdict"],
            "score":          engine_result["score"],
            "label":          engine_result["label"],
            "confidence":     engine_result["label"],
            "domain":         engine_result["domain"],
            "timing":         engine_result["timing"],
            "explanation":    explanation,
            "narrative":      explanation,
            "remedy":         remedy,
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
            "question_type":  engine_result.get("domain", "general"),
            "lagna":          engine_result["prashna_chart"].get("lagna_sign"),
            "moon_nakshatra": engine_result["prashna_chart"].get("moon_nakshatra"),
            "moon_quality":   "strong" if engine_result["breakdown"]["moon_validation"]["score"] > 0 else "neutral",
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


def main():
    if not os.path.exists(MAIN_PY):
        print(f"ERROR: {MAIN_PY} not found."); sys.exit(1)

    with open(MAIN_PY, "r") as f:
        lines = f.readlines()
    print(f"Read {MAIN_PY} ({len(lines)} lines)")

    # Backup (only if no existing backup)
    if not os.path.exists(BACKUP):
        shutil.copy2(MAIN_PY, BACKUP)
        print(f"Backed up -> {BACKUP}")
    else:
        print(f"Backup already exists at {BACKUP}")

    # ═══════════════════════════════════════════════════════════
    # PATCH 1: Add import AFTER the jaimini_integration block
    # ═══════════════════════════════════════════════════════════
    content = "".join(lines)

    if "run_prashna_engine" not in content:
        # Find "jaimini_prashna_check," then find its parent import's closing ")"
        # The structure is:
        #     from antar_engine.jaimini_integration import (
        #         ...
        #         jaimini_prashna_check,
        #     )
        # We need to insert AFTER that "    )" line

        new_lines = []
        found = False
        looking_for_close = False

        for i, line in enumerate(lines):
            new_lines.append(line)

            if not found and "jaimini_prashna_check" in line:
                looking_for_close = True

            if looking_for_close and line.strip() == ")":
                # This is the closing ) of the jaimini_integration import
                for imp_line in NEW_IMPORT_LINES:
                    new_lines.append(imp_line + "\n")
                found = True
                looking_for_close = False
                print(f"PATCH 1: Inserted import after line {i + 1}")

        if not found:
            print("WARNING: Could not find jaimini_prashna_check closing ). Add import manually.")
        
        content = "".join(new_lines)
    else:
        print("PATCH 1: Import already present (skipped)")

    # ═══════════════════════════════════════════════════════════
    # PATCH 2: Replace endpoint
    # ═══════════════════════════════════════════════════════════
    START = "class PrashnaRequest(BaseModel):"
    END   = "class PrashnaFollowupRequest(BaseModel):"

    s = content.find(START)
    e = content.find(END)

    if s == -1 or e == -1:
        print(f"ERROR: Markers not found. s={s}, e={e}"); sys.exit(1)

    content = content[:s] + NEW_BLOCK + content[e:]
    print(f"PATCH 2: Replaced ask_prashna endpoint")

    # ═══════════════════════════════════════════════════════════
    # Write + Verify
    # ═══════════════════════════════════════════════════════════
    with open(MAIN_PY, "w") as f:
        f.write(content)
    print(f"Written {MAIN_PY} ({content.count(chr(10))} lines)")

    print("\nVERIFICATION:")
    for term in ["run_prashna_engine", "check_cooldown", "PRASHNA_COOLDOWN_HOURS",
                  "prashna_log", "void_of_course", "navamsa_genuine", "ithasala",
                  "call_llm", "prashna_readings", "PrashnaFollowupRequest"]:
        print(f"  {'OK' if term in content else 'MISSING'}: {term}")

    print("\nDone. Next: Supabase SQL, git push, curl test.")


if __name__ == "__main__":
    main()
