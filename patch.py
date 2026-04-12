#!/usr/bin/env python3
"""
patch_save_chat_messages.py

Saves every Ask Antar question + answer to a chat_messages table.
This enables:
1. Registro de Inteligencia to show real user questions to verify
2. Pattern recognition across sessions
3. Oracle context for follow-up questions
4. Practice personalisation based on question domains
5. Precision improvement loop

Run: python patch_save_chat_messages.py

Then run this SQL in Supabase to create the table:
(SQL printed at end of script)
"""

import shutil, re

TARGET = "main.py"
BACKUP = "main.py.bak_save_chat"

with open(TARGET, "r") as f:
    content = f.read()

shutil.copy(TARGET, BACKUP)
print(f"Backup: {BACKUP}")

# ── PATCH 1: Add save_chat_message helper function ────────────────────────

SAVE_FUNCTION = '''
async def save_chat_message(
    supabase,
    chart_id: str,
    question: str,
    response_data: dict,
    language: str = "en"
) -> str:
    """
    Save a chat message (question + answer) to Supabase.
    Returns the message_id.
    
    Extracts:
    - domain from question keywords (finance/career/relationships/health)
    - question_type (timing/blockage/decision/opportunity)
    - key_date from timing_window field
    """
    import re as _re
    from datetime import datetime, timezone

    # ── Extract domain from question ──────────────────────────────
    q_lower = question.lower()
    domain = "general"
    if any(w in q_lower for w in [
        "cash", "money", "finance", "income", "revenue", "invest",
        "wealth", "salary", "profit", "business", "dinero", "plata",
        "riqueza", "ingresos", "negocio", "capital", "flujo"
    ]):
        domain = "finance"
    elif any(w in q_lower for w in [
        "career", "job", "work", "promotion", "boss", "company",
        "client", "project", "carrera", "trabajo", "empleo", "jefe"
    ]):
        domain = "career"
    elif any(w in q_lower for w in [
        "relationship", "partner", "love", "marriage", "dating",
        "relacion", "pareja", "amor", "matrimonio", "novio", "novia"
    ]):
        domain = "relationships"
    elif any(w in q_lower for w in [
        "health", "sick", "doctor", "pain", "energy", "tired",
        "salud", "enfermo", "doctor", "dolor", "energía", "cansado"
    ]):
        domain = "health"
    elif any(w in q_lower for w in [
        "move", "relocate", "travel", "city", "country",
        "mudar", "mover", "ciudad", "país", "viaje"
    ]):
        domain = "location"

    # ── Extract question type ──────────────────────────────────────
    question_type = "general"
    if any(w in q_lower for w in [
        "when", "cuándo", "how long", "cuánto tiempo", "date", "fecha"
    ]):
        question_type = "timing"
    elif any(w in q_lower for w in [
        "why", "por qué", "block", "bloqueo", "stuck", "atascado",
        "problem", "problema", "issue", "dificultad"
    ]):
        question_type = "blockage"
    elif any(w in q_lower for w in [
        "should i", "debo", "debería", "decision", "decisión",
        "choose", "elegir", "better", "mejor"
    ]):
        question_type = "decision"
    elif any(w in q_lower for w in [
        "opportunity", "oportunidad", "chance", "posibilidad",
        "good time", "buen momento", "window", "ventana"
    ]):
        question_type = "opportunity"

    # ── Extract key date from timing_window ───────────────────────
    timing_window = response_data.get("timing_window", "")
    key_date = None
    if timing_window:
        # Extract year-month patterns: "September 2026", "septiembre 2026"
        date_match = _re.search(
            r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|'
            r'septiembre|octubre|noviembre|diciembre|'
            r'january|february|march|april|may|june|july|august|'
            r'september|october|november|december)'
            r'\s+(\d{4})',
            timing_window.lower()
        )
        if date_match:
            key_date = date_match.group(0).title()
        else:
            # Try year only
            year_match = _re.search(r'\b(202[4-9]|203\d)\b', timing_window)
            if year_match:
                key_date = year_match.group(0)

    # ── Build record ──────────────────────────────────────────────
    record = {
        "chart_id": chart_id,
        "question": question,
        "plain_summary": response_data.get("plain_summary", ""),
        "signal_line": response_data.get("signal_line", ""),
        "action_item": response_data.get("action_item", ""),
        "timing_window": timing_window,
        "domain": domain,
        "question_type": question_type,
        "key_date": key_date,
        "confidence": response_data.get("signal_confidence", ""),
        "archetype_name": response_data.get("archetype_name", ""),
        "language": language,
        "why_this": response_data.get("why_this", ""),
        "bridge_practice_note": response_data.get("bridge_practice_note", ""),
        "contradiction_detected": response_data.get("contradiction_detected", False),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        result = supabase.table("chat_messages").insert(record).execute()
        if result.data:
            msg_id = result.data[0].get("id", "")
            return msg_id
    except Exception as e:
        print(f"save_chat_message error: {e}")

    return ""


async def get_recent_questions(
    supabase,
    chart_id: str,
    limit: int = 5,
    domain: str = None
) -> list:
    """
    Get recent Ask Antar questions for this chart.
    Used to build oracle_context for follow-up questions.
    """
    try:
        query = supabase.table("chat_messages").select(
            "question, signal_line, action_item, domain, key_date, created_at"
        ).eq("chart_id", chart_id).order(
            "created_at", desc=True
        ).limit(limit)

        if domain:
            query = query.eq("domain", domain)

        result = query.execute()
        return result.data or []
    except Exception as e:
        print(f"get_recent_questions error: {e}")
        return []


async def get_domain_pattern(supabase, chart_id: str) -> dict:
    """
    Returns a dict of how many times each domain has been asked.
    Used to personalise the dashboard (show finance signals first if
    user mostly asks about money).
    """
    try:
        result = supabase.table("chat_messages").select(
            "domain"
        ).eq("chart_id", chart_id).execute()

        if not result.data:
            return {}

        counts = {}
        for row in result.data:
            d = row.get("domain", "general")
            counts[d] = counts.get(d, 0) + 1

        # Sort by frequency
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
    except Exception as e:
        print(f"get_domain_pattern error: {e}")
        return {}
'''

# Insert before the first route
marker = "@app.get(\"/health\")"
alt_markers = ["@app.post(\"/api", "@app.get(\"/api"]

inserted = False
for m in [marker] + alt_markers:
    if m in content:
        content = content.replace(m, SAVE_FUNCTION + "\n\n" + m, 1)
        print(f"✅ Inserted save_chat_message() before '{m}'")
        inserted = True
        break

if not inserted:
    content += "\n\n" + SAVE_FUNCTION
    print("✅ Appended save_chat_message() to end of file")

# ── PATCH 2: Call save_chat_message in the /predict endpoint ─────────────

# Find the predict endpoint return statement and add save call before it
OLD_PREDICT_RETURN = '''        return {
            "prediction": prediction_text,'''

NEW_PREDICT_RETURN = '''        # ── Save question + answer to chat_messages ──────────────
        try:
            response_payload = {
                "plain_summary": plain_summary,
                "signal_line": signal_line,
                "action_item": action_item,
                "timing_window": timing_window,
                "signal_confidence": signal_confidence,
                "archetype_name": archetype_name,
                "why_this": why_this,
                "bridge_practice_note": bridge_practice_note,
                "contradiction_detected": contradiction_detected,
            }
            saved_id = await save_chat_message(
                supabase=supabase,
                chart_id=chart_id,
                question=question,
                response_data=response_payload,
                language=language
            )
            if saved_id:
                print(f"✓ Saved chat message: {saved_id}")
        except Exception as save_err:
            print(f"Chat message save error (non-fatal): {save_err}")
        # ── End save ──────────────────────────────────────────────

        return {
            "prediction": prediction_text,'''

if OLD_PREDICT_RETURN in content:
    content = content.replace(OLD_PREDICT_RETURN, NEW_PREDICT_RETURN, 1)
    print("✅ Added save_chat_message call in /predict endpoint")
else:
    print("⚠️  Could not auto-patch predict return")
    print("    Manually add save_chat_message() call before the return in POST /predict")

# ── PATCH 3: Add recent questions to oracle_context ──────────────────────

# Find where oracle_context is built and add recent questions
OLD_ORACLE = '"oracle_context": oracle_context,'
NEW_ORACLE = '''"oracle_context": oracle_context,
            "recent_questions": await get_recent_questions(
                supabase=supabase,
                chart_id=chart_id,
                limit=3
            ),'''

if OLD_ORACLE in content:
    content = content.replace(OLD_ORACLE, NEW_ORACLE, 1)
    print("✅ Added recent_questions to predict response")

# ── Write file ────────────────────────────────────────────────────────────
with open(TARGET, "w") as f:
    f.write(content)

print("\n✅ Patch complete")
print()
print("=" * 60)
print("RUN THIS SQL IN SUPABASE FIRST:")
print("=" * 60)
print("""
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chart_id UUID REFERENCES charts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- The question
    question TEXT NOT NULL,
    
    -- Structured answer fields (what frontend shows)
    plain_summary TEXT,
    signal_line TEXT,
    action_item TEXT,
    timing_window TEXT,
    key_date TEXT,
    
    -- Classification (extracted from question + answer)
    domain TEXT DEFAULT 'general',
    -- finance / career / relationships / health / location / general
    
    question_type TEXT DEFAULT 'general',
    -- timing / blockage / decision / opportunity / general
    
    -- Metadata
    confidence TEXT,
    archetype_name TEXT,
    language TEXT DEFAULT 'en',
    why_this TEXT,
    bridge_practice_note TEXT,
    contradiction_detected BOOLEAN DEFAULT FALSE,
    
    -- Verification (user confirms if prediction was accurate)
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    accuracy_rating TEXT,
    -- 'confirmed' / 'not_quite' / NULL (not yet verified)
    
    -- Indexes
    CONSTRAINT chat_messages_chart_id_fkey
        FOREIGN KEY (chart_id) REFERENCES charts(id)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_chat_messages_chart_id 
    ON chat_messages(chart_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at 
    ON chat_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_domain 
    ON chat_messages(chart_id, domain);
CREATE INDEX IF NOT EXISTS idx_chat_messages_unverified 
    ON chat_messages(chart_id, verified) 
    WHERE verified = FALSE AND plain_summary IS NOT NULL;

-- RLS policy (users can only see their own messages)
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
""")
print("=" * 60)
print()
print("Then verify syntax:")
print("python3 -c \"import ast; ast.parse(open('main.py').read()); print('OK')\"")
print()
print("Then deploy:")
print("git add -A && git commit -m 'feat: save chat messages to DB (intel loop)' && git push")
print()
print("Verify after deploy:")
print("# Ask a question in Ask Antar, then run:")
print("curl -s https://antar-fastapi-production.up.railway.app/api/v1/predict \\")
print("  -X POST -H 'Content-Type: application/json' \\")
print("  -d '{\"chart_id\":\"de02bb52-d43a-4b09-be25-b45a07bfbf8a\",\"question\":\"test save\",\"language\":\"en\"}'")
print("# Then check Supabase chat_messages table for the new row")
