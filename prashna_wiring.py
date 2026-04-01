"""
═══════════════════════════════════════════════════════════════════
PRASHNA ENDPOINT WIRING — Paste into main.py
═══════════════════════════════════════════════════════════════════

INSTRUCTIONS:
1. Copy prashna_engine.py into antar_engine/
2. Run the SQL below in Supabase to create prashna_log table
3. Find your existing /prashna endpoint in main.py
4. REPLACE it entirely with the code below
5. Add the import at the top of main.py
6. git push → Railway auto-deploys
7. Test with the curl commands at the bottom

═══════════════════════════════════════════════════════════════════
"""

# ─────────────────────────────────────────────────────────────────
# STEP 1: Add this import at the top of main.py (near other imports)
# ─────────────────────────────────────────────────────────────────

"""
# Add near the top of main.py, with the other antar_engine imports:

from antar_engine.prashna_engine import (
    run_prashna_engine,
    check_cooldown,
    detect_prashna_intent,
    PRASHNA_COOLDOWN_HOURS,
)
"""


# ─────────────────────────────────────────────────────────────────
# STEP 2: Run this SQL in Supabase SQL Editor
# ─────────────────────────────────────────────────────────────────

SUPABASE_SQL = """
-- Prashna Log table — tracks every Oracle question for cooldown + history
CREATE TABLE IF NOT EXISTS prashna_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    chart_id UUID NOT NULL REFERENCES charts(chart_id),
    question TEXT NOT NULL,
    domain TEXT,
    verdict TEXT,
    score INTEGER,
    label TEXT,
    timing TEXT,
    explanation TEXT,
    breakdown JSONB,
    prashna_chart JSONB,
    weakest_planet TEXT,
    cooldown_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for cooldown lookup (fast: chart_id + time)
CREATE INDEX IF NOT EXISTS idx_prashna_log_chart_time 
ON prashna_log (chart_id, created_at DESC);

-- RLS
ALTER TABLE prashna_log ENABLE ROW LEVEL SECURITY;

-- Open policy (same as other tables)
CREATE POLICY "Allow all on prashna_log" ON prashna_log
FOR ALL USING (true) WITH CHECK (true);
"""


# ─────────────────────────────────────────────────────────────────
# STEP 3: Replace the existing /prashna endpoint with this code
# ─────────────────────────────────────────────────────────────────

# Find the existing endpoint — it looks something like:
#   @app.post("/api/v1/prashna")
#   async def prashna_oracle(request: ...):
#       ...
#
# DELETE the entire function and REPLACE with everything below.
# Make sure the Pydantic model is also updated (or add the new one).

ENDPOINT_CODE = '''
# ═══════════════════════════════════════════════════════════════════
# /prashna — YES/NO Oracle (Prashna Horary Engine)
# ═══════════════════════════════════════════════════════════════════

class PrashnaRequest(BaseModel):
    question: str
    chart_id: str
    lat: Optional[float] = None
    lng: Optional[float] = None

@app.post("/api/v1/prashna")
async def prashna_oracle(request: PrashnaRequest):
    """
    Prashna (Horary) Oracle — real-time YES/NO verdict engine.
    
    Flow:
    1. Check cooldown (24h between questions)
    2. Fetch chart data from Supabase (for jaimini + dasha context)
    3. Run prashna_engine → cast Moment Chart + 4-step scoring + Ithasala
    4. Call Claude Sonnet to explain the pre-calculated verdict in plain English
    5. Log to prashna_log table
    6. Return verdict + score + explanation + breakdown
    """
    import traceback
    from datetime import datetime, timezone
    
    try:
        chart_id = request.chart_id
        question = request.question.strip()
        
        if not question:
            return JSONResponse(status_code=400, content={"error": "Question is required"})
        
        # ─── 1. Cooldown Check ───
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
            # If prashna_log table doesn't exist yet, skip cooldown
            logger.warning(f"Cooldown check failed (table may not exist): {e}")
        
        # ─── 2. Fetch Chart Data ───
        chart_row = supabase.table("charts") \\
            .select("chart_data, jaimini_data, lal_kitab_data, current_dasha, first_name, current_country, lagna_sign") \\
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
        
        # Parse jaimini_data if it's a string
        if isinstance(jaimini_data, str):
            try:
                jaimini_data = json.loads(jaimini_data)
            except:
                jaimini_data = None
        
        # ─── 3. Default coordinates (Cliffside Park, NJ) if not provided ───
        lat = request.lat or 40.8215
        lng = request.lng or -73.9876
        
        # ─── 4. Run Prashna Engine ───
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
        remedy_text = ""
        
        try:
            import anthropic
            client = anthropic.Anthropic()
            
            claude_response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                system=engine_result["claude_prompt"],
                messages=[{"role": "user", "content": question}],
            )
            
            explanation = claude_response.content[0].text if claude_response.content else ""
            
        except Exception as claude_err:
            logger.error(f"Claude call failed for prashna: {claude_err}")
            # Fallback: use the breakdown reason as explanation
            bd = engine_result["breakdown"]
            explanation = (
                f"{engine_result['verdict']} ({engine_result['score']}%). "
                f"{bd['ithasala'].get('reason', '')}. "
                f"Timing: {engine_result['timing']}."
            )
        
        # ─── 6. Build Remedy Card ───
        wp = engine_result.get("weakest_planet", {})
        if locale == "IN":
            remedy_practices = {
                "Sun": "Offer water to the Sun at sunrise. Donate wheat on Sundays.",
                "Moon": "Wear white on Mondays. Keep a silver item with you.",
                "Mercury": "Feed green vegetables to a cow. Donate on Wednesdays.",
                "Venus": "Donate white clothes on Fridays. Offer white flowers.",
                "Mars": "Donate red lentils on Tuesdays. Serve with physical effort.",
                "Jupiter": "Donate yellow items on Thursdays. Respect your teachers.",
                "Saturn": "Donate mustard oil on Saturdays. Serve the elderly.",
            }
        else:
            remedy_practices = {
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
            "practice": remedy_practices.get(wp.get("planet", "Saturn"), "Take one deliberate action this week."),
            "why": f"{wp.get('planet', 'Saturn')} needs strengthening in this moment — {', '.join(wp.get('reasons', ['general']))}",
        }
        
        # ─── 7. Log to Supabase ───
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
        
        # ─── 8. Return Response ───
        return {
            "verdict": engine_result["verdict"],
            "score": engine_result["score"],
            "label": engine_result["label"],
            "domain": engine_result["domain"],
            "timing": engine_result["timing"],
            "explanation": explanation,
            "remedy": remedy,
            "breakdown": {
                "lagna_strength": engine_result["breakdown"]["lagna_strength"]["score"],
                "lord_connection": engine_result["breakdown"]["lord_connection"]["score"],
                "ithasala": {
                    "type": engine_result["breakdown"]["ithasala"]["type"],
                    "score": engine_result["breakdown"]["ithasala"]["score"],
                    "aspect": engine_result["breakdown"]["ithasala"].get("aspect"),
                },
                "moon_validation": engine_result["breakdown"]["moon_validation"]["score"],
                "void_of_course": engine_result["breakdown"].get("void_of_course", {}).get("void_of_course", False),
                "navamsa_genuine": engine_result["breakdown"].get("navamsa_genuineness", {}).get("genuine", True),
                "mutual_reception": engine_result["breakdown"]["mutual_reception"].get("found", False),
                "edge_yoga": engine_result["breakdown"]["edge_yoga"]["yoga"] if engine_result["breakdown"].get("edge_yoga") else None,
                "jaimini_locks": engine_result["breakdown"]["jaimini_locks"],
            },
            "prashna_chart": engine_result["prashna_chart"],
            "cooldown_until": engine_result["cooldown_until"],
            "natal_context": engine_result["natal_context"],
        }
    
    except Exception as e:
        logger.error(f"Prashna engine error: {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={
            "error": "Prashna engine failed",
            "detail": str(e),
        })
'''


# ─────────────────────────────────────────────────────────────────
# STEP 4: Curl test commands
# ─────────────────────────────────────────────────────────────────

CURL_TESTS = """
# ═══════════════════════════════════════════════════════════════════
# CURL TEST COMMANDS — Run after deploying to Railway
# ═══════════════════════════════════════════════════════════════════

BASE="https://antar-fastapi-production.up.railway.app"
CHART="de02bb52-d43a-4b09-be25-b45a07bfbf8a"

# ─── Test 1: Career question ───
curl -s -X POST "$BASE/api/v1/prashna" \\
  -H "Content-Type: application/json" \\
  -d '{
    "question": "Should I accept this job offer?",
    "chart_id": "'$CHART'",
    "lat": 40.8215,
    "lng": -73.9876
  }' | python3 -m json.tool

# ─── Test 2: Relationship question ───
curl -s -X POST "$BASE/api/v1/prashna" \\
  -H "Content-Type: application/json" \\
  -d '{
    "question": "Will I find a partner this year?",
    "chart_id": "'$CHART'",
    "lat": 40.8215,
    "lng": -73.9876
  }' | python3 -m json.tool

# ─── Test 3: Cooldown test (should return 429 if run within 24h of Test 1) ───
curl -s -X POST "$BASE/api/v1/prashna" \\
  -H "Content-Type: application/json" \\
  -d '{
    "question": "Should I invest in crypto?",
    "chart_id": "'$CHART'",
    "lat": 40.8215,
    "lng": -73.9876
  }' | python3 -m json.tool

# ─── Test 4: No coordinates (should use default NJ location) ───
curl -s -X POST "$BASE/api/v1/prashna" \\
  -H "Content-Type: application/json" \\
  -d '{
    "question": "Is this a good time to buy property?",
    "chart_id": "'$CHART'"
  }' | python3 -m json.tool

# ─── Test 5: Check prashna_log table ───
# Run in Supabase SQL editor:
# SELECT chart_id, question, verdict, score, label, timing, created_at 
# FROM prashna_log ORDER BY created_at DESC LIMIT 5;

# ═══════════════════════════════════════════════════════════════════
# WHAT TO VERIFY IN THE RESPONSE:
# ═══════════════════════════════════════════════════════════════════
# 1. "verdict" is one of: STRONG YES, YES, CAUTIOUS YES, UNLIKELY, NO, STRONG NO
# 2. "score" is 0-100
# 3. "explanation" is plain English, zero jargon, under 150 words
# 4. "breakdown" has all 4 steps with scores
# 5. "breakdown.ithasala.type" is "ithasala", "ishrafa", or "neutral"
# 6. "breakdown.void_of_course" is true/false
# 7. "breakdown.navamsa_genuine" is true/false
# 8. "prashna_chart" has lagna_sign, moon_nakshatra, significators
# 9. "remedy" has planet + practice + why
# 10. "cooldown_until" is ~24h from now
# 11. Second request within 24h returns 429 with cooldown message
"""


# ─────────────────────────────────────────────────────────────────
# STEP 5: Deployment checklist
# ─────────────────────────────────────────────────────────────────

DEPLOYMENT_CHECKLIST = """
═══════════════════════════════════════════════════════════════════
DEPLOYMENT CHECKLIST — Sprint PR: Prashna Engine
═══════════════════════════════════════════════════════════════════

□ 1. Copy prashna_engine.py → antar_engine/prashna_engine.py
□ 2. Run locally: python test_prashna.py && python test_prashna_validation.py
      → Both must pass (96/96 + 41/41)
□ 3. Run Supabase SQL: CREATE TABLE prashna_log (see above)
□ 4. Add import to top of main.py:
      from antar_engine.prashna_engine import (
          run_prashna_engine, check_cooldown, 
          detect_prashna_intent, PRASHNA_COOLDOWN_HOURS,
      )
□ 5. Replace existing /prashna endpoint in main.py with the code above
□ 6. git add . && git commit -m "Sprint PR: Prashna Ithasala engine" && git push
□ 7. Wait for Railway deploy (~60s)
□ 8. Run curl Test 1 (career question)
□ 9. Verify response has: verdict, score, explanation, breakdown, prashna_chart
□ 10. Run curl Test 3 (cooldown) — should return 429
□ 11. Check Supabase: SELECT * FROM prashna_log LIMIT 1
□ 12. If all pass: Prashna backend is LIVE ✅
"""


if __name__ == "__main__":
    print("═══ PRASHNA WIRING GUIDE ═══")
    print()
    print("This file contains everything needed to wire prashna_engine.py into main.py.")
    print()
    print("FILES TO DEPLOY:")
    print("  1. antar_engine/prashna_engine.py  (the engine)")
    print("  2. main.py                          (replace /prashna endpoint)")
    print("  3. Supabase SQL                     (create prashna_log table)")
    print()
    print("See DEPLOYMENT_CHECKLIST at the bottom of this file.")
    print()
    print("─── SUPABASE SQL ───")
    print(SUPABASE_SQL)
    print()
    print("─── CURL TESTS ───")
    print(CURL_TESTS)
    print()
    print("─── CHECKLIST ───")
    print(DEPLOYMENT_CHECKLIST)
