#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
ANTAR Sprint P — ONE-SHOT DEPLOY SCRIPT
═══════════════════════════════════════════════════════════════

Run from your repo root:
    python sprint_p_deploy.py

What it does (in order):
  1. Writes antar_engine/practice_engine.py (the engine)
  2. Scans main.py to find variable names + insertion points
  3. Patches main.py: adds 3 endpoints + /predict wiring
  4. Prints the Supabase SQL to run manually
  5. Asks if you want to git commit + push

❆ ANTAR · antar.world · Sprint P · March 31, 2026
"""

import os
import re
import sys
import textwrap

REPO_ROOT = os.getcwd()
MAIN_PY = os.path.join(REPO_ROOT, "main.py")
ENGINE_DIR = os.path.join(REPO_ROOT, "antar_engine")
ENGINE_FILE = os.path.join(ENGINE_DIR, "practice_engine.py")

# ════════════════════════════════════════════
# COLOR HELPERS
# ════════════════════════════════════════════
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def ok(msg): print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg): print(f"  {RED}❌ {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠️  {msg}{RESET}")
def info(msg): print(f"  {CYAN}→ {msg}{RESET}")


# ════════════════════════════════════════════
# STEP 0: PREFLIGHT CHECKS
# ════════════════════════════════════════════
def preflight():
    print(f"\n{BOLD}═══ ANTAR Sprint P — Preflight ═══{RESET}\n")

    if not os.path.exists(MAIN_PY):
        fail(f"main.py not found at {MAIN_PY}")
        fail("Run this script from your repo root (where main.py lives)")
        sys.exit(1)
    ok("main.py found")

    if not os.path.isdir(ENGINE_DIR):
        fail(f"antar_engine/ directory not found at {ENGINE_DIR}")
        sys.exit(1)
    ok("antar_engine/ directory found")

    # Check if already patched
    with open(MAIN_PY, "r") as f:
        content = f.read()
    if "SPRINT P" in content and "practices" in content and "practice_schedule" in content:
        warn("main.py appears to already have Sprint P endpoints")
        resp = input("  Continue anyway? (y/n): ").strip().lower()
        if resp != "y":
            print("  Aborted.")
            sys.exit(0)

    return content


# ════════════════════════════════════════════
# STEP 1: WRITE practice_engine.py
# ════════════════════════════════════════════
def write_practice_engine():
    print(f"\n{BOLD}═══ Step 1: Writing practice_engine.py ═══{RESET}\n")

    if os.path.exists(ENGINE_FILE):
        warn(f"practice_engine.py already exists at {ENGINE_FILE}")
        resp = input("  Overwrite? (y/n): ").strip().lower()
        if resp != "y":
            ok("Keeping existing practice_engine.py")
            return

    # The engine file was already output earlier in this chat session.
    # Check if user has it in outputs or needs us to reference it.
    info("practice_engine.py should already be in your project from the earlier step.")
    info("If you haven't copied it yet, copy it from the chat outputs to:")
    info(f"  {ENGINE_FILE}")

    if not os.path.exists(ENGINE_FILE):
        fail(f"practice_engine.py not found at {ENGINE_FILE}")
        fail("Copy practice_engine.py from chat outputs to antar_engine/ first, then re-run.")
        sys.exit(1)

    ok(f"practice_engine.py exists at {ENGINE_FILE}")

    # Verify it imports
    try:
        sys.path.insert(0, REPO_ROOT)
        import importlib
        spec = importlib.util.spec_from_file_location("practice_engine", ENGINE_FILE)
        mod = importlib.util.module_from_spec(spec)
        # Don't actually execute — just verify syntax
        import ast
        with open(ENGINE_FILE) as f:
            ast.parse(f.read())
        ok("practice_engine.py syntax OK")
    except SyntaxError as e:
        fail(f"practice_engine.py has syntax error: {e}")
        sys.exit(1)


# ════════════════════════════════════════════
# STEP 2: SCAN main.py FOR VARIABLE NAMES
# ════════════════════════════════════════════
def scan_main_py(content):
    print(f"\n{BOLD}═══ Step 2: Scanning main.py ═══{RESET}\n")

    lines = content.split("\n")
    total_lines = len(lines)
    info(f"main.py has {total_lines} lines")

    # Find the `app = FastAPI(...)` line
    app_var = "app"
    for line in lines:
        m = re.match(r'^(\w+)\s*=\s*FastAPI\(', line)
        if m:
            app_var = m.group(1)
            break
    info(f"FastAPI app variable: {app_var}")

    # Find `supabase` variable
    supabase_var = "supabase"
    for line in lines:
        if "create_client" in line and "=" in line:
            m = re.match(r'^(\w+)\s*=\s*create_client', line.strip())
            if m:
                supabase_var = m.group(1)
                break
        if "supabase:" in line.lower() or "supabase =" in line.lower():
            pass  # default is fine
    info(f"Supabase client variable: {supabase_var}")

    # Find /predict endpoint
    predict_line = None
    predict_decorator_line = None
    for i, line in enumerate(lines):
        if "/predict" in line and ("@" in line or "def " in line):
            if "@" in line and "post" in line.lower():
                predict_decorator_line = i
            if "def " in line and "predict" in line.lower():
                predict_line = i
                break
        # Also catch the case where decorator is one line before def
        if predict_decorator_line and "def " in line:
            predict_line = i
            break

    if predict_line:
        info(f"/predict endpoint found at line {predict_line + 1}")
    else:
        warn("/predict endpoint not found by pattern — will skip /predict wiring")

    # Find where LK context is built inside /predict
    lk_context_var = None
    lk_context_line = None
    if predict_line:
        # Search within 200 lines after /predict def
        search_end = min(predict_line + 300, total_lines)
        for i in range(predict_line, search_end):
            line = lines[i]
            # Look for lk_block, lk_context, format_lk_context
            if "format_lk_context" in line or "lk_block" in line or "lk_context" in line:
                m = re.match(r'\s*(\w+)\s*=.*(?:format_lk_context|lk_block|lk_context)', line)
                if m:
                    lk_context_var = m.group(1)
                    lk_context_line = i
                    break
            # Also check for build_lk_advanced
            if "build_lk_advanced" in line:
                m = re.match(r'\s*(\w+)\s*=.*build_lk_advanced', line)
                if m:
                    lk_context_var = m.group(1)
                    lk_context_line = i

    if lk_context_var:
        info(f"LK context variable: '{lk_context_var}' at line {lk_context_line + 1}")
    else:
        warn("Could not find LK context variable — will search for Claude call instead")

    # Find chart data variables inside /predict
    chart_data_var = "chart_data"
    jaimini_data_var = "jaimini_data"
    lk_data_var = "lal_kitab_data"
    country_var = "current_country"
    birth_date_var = "birth_date"

    if predict_line:
        search_end = min(predict_line + 300, total_lines)
        for i in range(predict_line, search_end):
            line = lines[i].strip()
            # chart_data: look for 'chart_data = ...' exactly
            m = re.match(r'(chart_data)\s*=', line)
            if m:
                chart_data_var = "chart_data"
            elif "chart_data" in line and ".get(" in line:
                m2 = re.match(r'(\w+)\s*=.*\.get\(["\']chart_data', line)
                if m2:
                    chart_data_var = m2.group(1)

            # jaimini_data: look for exact match
            m = re.match(r'(jaimini_data)\s*=', line)
            if m:
                jaimini_data_var = "jaimini_data"
            elif "jaimini_data" in line and ".get(" in line:
                m2 = re.match(r'(\w+)\s*=.*\.get\(["\']jaimini_data', line)
                if m2:
                    jaimini_data_var = m2.group(1)

            # lal_kitab_data: exact match
            m = re.match(r'(lal_kitab_data)\s*=', line)
            if m and "format" not in line:
                lk_data_var = "lal_kitab_data"
            elif "lal_kitab_data" in line and ".get(" in line and "format" not in line:
                m2 = re.match(r'(\w+)\s*=.*\.get\(["\']lal_kitab_data', line)
                if m2:
                    lk_data_var = m2.group(1)

            # country
            m = re.match(r'(current_country)\s*=', line)
            if m:
                country_var = "current_country"

            # birth_date
            m = re.match(r'(birth_date)\s*=', line)
            if m and "format" not in line:
                birth_date_var = "birth_date"

    info(f"Detected vars: chart_data={chart_data_var}, jaimini={jaimini_data_var}, lk={lk_data_var}")
    info(f"               country={country_var}, birth_date={birth_date_var}")

    # Find the Claude API call line (to insert practice context before it)
    claude_call_line = None
    if predict_line:
        search_end = min(predict_line + 300, total_lines)
        for i in range(predict_line, search_end):
            line = lines[i]
            if any(kw in line for kw in ["anthropic", "messages.create", "client.messages", "claude", "sonnet"]):
                if "=" in line and ("create" in line or "messages" in line):
                    claude_call_line = i
                    break
    if claude_call_line:
        info(f"Claude API call found at line {claude_call_line + 1}")

    # Find where full_context / system prompt is built
    context_build_line = None
    context_var = None
    _skip_context_vars = {"response", "result", "data", "chart", "resp", "_chart", "_c"}
    if predict_line:
        search_end = min(predict_line + 300, total_lines)
        for i in range(predict_line, search_end):
            line = lines[i]
            for pat in [r'(system_prompt)\s*=', r'(full_context)\s*=',
                       r'(context)\s*\+=.*lk', r'(context)\s*=\s*f["\'].*NATAL',
                       r'(context_parts)\s*[=\[]', r'(\w*context\w*)\s*\+=',
                       r'(\w*prompt\w*)\s*\+=']:
                m2 = re.search(pat, line, re.IGNORECASE)
                if m2:
                    _candidate = m2.group(1)
                    if _candidate.lower() not in _skip_context_vars:
                        context_var = _candidate
                        context_build_line = i

    if context_var:
        info(f"System prompt variable: '{context_var}' near line {context_build_line + 1}")

    # Find `if __name__` line
    main_guard_line = None
    for i in range(total_lines - 1, max(total_lines - 50, 0), -1):
        if '__name__' in lines[i] and '__main__' in lines[i]:
            main_guard_line = i
            break
    if main_guard_line:
        info(f"if __name__ guard at line {main_guard_line + 1}")
    else:
        main_guard_line = total_lines  # append at end
        warn("No if __name__ guard found — will append at end of file")

    return {
        "app_var": app_var,
        "supabase_var": supabase_var,
        "predict_line": predict_line,
        "lk_context_var": lk_context_var,
        "lk_context_line": lk_context_line,
        "chart_data_var": chart_data_var,
        "jaimini_data_var": jaimini_data_var,
        "lk_data_var": lk_data_var,
        "country_var": country_var,
        "birth_date_var": birth_date_var,
        "claude_call_line": claude_call_line,
        "context_var": context_var,
        "context_build_line": context_build_line,
        "main_guard_line": main_guard_line,
        "total_lines": total_lines,
    }


# ════════════════════════════════════════════
# STEP 3: PATCH main.py
# ════════════════════════════════════════════
def patch_main_py(content, scan):
    print(f"\n{BOLD}═══ Step 3: Patching main.py ═══{RESET}\n")

    lines = content.split("\n")
    app = scan["app_var"]
    sb = scan["supabase_var"]

    # ── 3A: Build the endpoints block ──
    endpoints_block = f'''

# ═══════════════════════════════════════════════════════════════
# SPRINT P — PRACTICE ENGINE ENDPOINTS (auto-patched {__import__("datetime").date.today()})
# ═══════════════════════════════════════════════════════════════

from antar_engine.practice_engine import generate_practice_schedule, format_practice_for_predict_prompt
from pydantic import BaseModel as _PracticeBaseModel

class _PracticeCompleteReq(_PracticeBaseModel):
    practice_id: str
    user_note: str = None

@{app}.get("/api/v1/practices/{{chart_id}}/schedule")
async def get_practice_schedule_endpoint(chart_id: str, refresh: bool = False):
    try:
        from datetime import date as _d, timedelta as _td
        _today = _d.today()
        _week_of = _today - _td(days=_today.weekday())
        if not refresh:
            _cache = {sb}.table("practice_schedule_cache").select("schedule_data").eq("chart_id", chart_id).eq("week_of", _week_of.isoformat()).execute()
            if _cache.data and len(_cache.data) > 0:
                _sched = _cache.data[0]["schedule_data"]
                _streak = await _practice_get_streak(chart_id)
                _sched["streak_data"] = _streak
                return {{"status": "ok", "source": "cache", "schedule": _sched}}
        _chart = {sb}.table("charts").select("chart_data, jaimini_data, lal_kitab_data, current_country, birth_date").eq("id", chart_id).single().execute()
        if not _chart.data:
            return {{"status": "error", "message": "Chart not found"}}
        _c = _chart.data
        _streak = await _practice_get_streak(chart_id)
        _sched = generate_practice_schedule(
            chart_data=_c.get("chart_data") or {{}},
            jaimini_data=_c.get("jaimini_data") or {{}},
            lal_kitab_data=_c.get("lal_kitab_data") or {{}},
            current_country=_c.get("current_country", "US"),
            birth_date=_c.get("birth_date"),
            streak_data=_streak,
        )
        try:
            {sb}.table("practice_schedule_cache").upsert({{"chart_id": chart_id, "week_of": _week_of.isoformat(), "cache_key": _sched.get("cache_key", ""), "schedule_data": _sched}}, on_conflict="chart_id,week_of").execute()
        except Exception:
            pass
        return {{"status": "ok", "source": "generated", "schedule": _sched}}
    except Exception as e:
        print(f"[PRACTICE] Schedule error: {{e}}")
        return {{"status": "error", "message": str(e)}}

@{app}.post("/api/v1/practices/{{chart_id}}/complete")
async def complete_practice_endpoint(chart_id: str, req: _PracticeCompleteReq):
    try:
        from datetime import datetime as _dt, date as _d, timedelta as _td
        _now = _dt.utcnow()
        _streak = await _practice_calc_streak(chart_id, _d.today())
        _planet = "Unknown"
        _ptype = "remedy"
        _planets = ["sun","moon","mars","mercury","jupiter","venus","saturn","rahu","ketu"]
        _types = ["convergence","awakening","remedy","rin_clearing","mantra"]
        for _p in req.practice_id.lower().split("_"):
            if _p in _planets: _planet = _p.capitalize()
            if _p in _types: _ptype = _p
        {sb}.table("practice_log").insert({{"chart_id": chart_id, "practice_id": req.practice_id, "planet": _planet, "practice_type": _ptype, "completed_at": _now.isoformat(), "streak_count": _streak + 1, "user_note": req.user_note}}).execute()
        _new = _streak + 1
        if _new == 7: _msg = "7-day streak unlocked! You earned a free Deep Dive Location Audit."
        elif _new == 21: _msg = "21-day cycle complete. Your energy pattern has shifted."
        elif _new >= 3: _msg = f"{{_new}}-day streak! Consistency is building momentum."
        else: _msg = "Practice logged. Every day counts."
        return {{"status": "ok", "streak_count": _new, "message": _msg}}
    except Exception as e:
        print(f"[PRACTICE] Complete error: {{e}}")
        return {{"status": "error", "message": str(e)}}

@{app}.get("/api/v1/practices/{{chart_id}}/streak")
async def get_practice_streak_endpoint(chart_id: str):
    try:
        from datetime import date as _d, timedelta as _td
        _today = _d.today()
        _30ago = _today - _td(days=30)
        _log = {sb}.table("practice_log").select("practice_id, practice_type, completed_at, streak_count, user_note, energy_label").eq("chart_id", chart_id).gte("created_at", _30ago.isoformat()).order("completed_at", desc=True).execute()
        _completions = _log.data or []
        _current = await _practice_calc_streak(chart_id, _today)
        _longest = max([c.get("streak_count", 0) for c in _completions], default=0)
        _longest = max(_longest, _current)
        _total = len([c for c in _completions if c.get("completed_at")])
        _cal = {{}}
        for c in _completions:
            if c.get("completed_at"):
                _cal[c["completed_at"][:10]] = {{"practice_id": c.get("practice_id"), "practice_type": c.get("practice_type"), "note": c.get("user_note")}}
        return {{"status": "ok", "chart_id": chart_id, "current_streak": _current, "longest_streak": _longest, "total_completed": _total, "completion_rate": round(_total / 30 * 100) if _total else 0, "calendar": _cal, "history": _completions[:20]}}
    except Exception as e:
        print(f"[PRACTICE] Streak error: {{e}}")
        return {{"status": "error", "message": str(e)}}

async def _practice_calc_streak(chart_id: str, today) -> int:
    try:
        from datetime import timedelta as _td
        _60ago = today - _td(days=60)
        _log = {sb}.table("practice_log").select("completed_at").eq("chart_id", chart_id).not_.is_("completed_at", "null").gte("completed_at", _60ago.isoformat()).order("completed_at", desc=True).execute()
        if not _log.data: return 0
        _dates = set()
        for r in _log.data:
            if r.get("completed_at"): _dates.add(r["completed_at"][:10])
        _streak = 0
        _check = today
        if _check.isoformat() not in _dates:
            _check = today - _td(days=1)
            if _check.isoformat() not in _dates: return 0
        while _check.isoformat() in _dates:
            _streak += 1
            _check -= _td(days=1)
        return _streak
    except Exception:
        return 0

async def _practice_get_streak(chart_id: str) -> dict:
    from datetime import date as _d
    _current = await _practice_calc_streak(chart_id, _d.today())
    try:
        _max = {sb}.table("practice_log").select("streak_count").eq("chart_id", chart_id).order("streak_count", desc=True).limit(1).execute()
        _longest = _max.data[0]["streak_count"] if _max.data else 0
    except Exception:
        _longest = 0
    try:
        _cnt = {sb}.table("practice_log").select("id", count="exact").eq("chart_id", chart_id).not_.is_("completed_at", "null").execute()
        _total = _cnt.count or 0
    except Exception:
        _total = 0
    return {{"current": max(_current, 0), "longest": max(_longest, _current), "total_completed": _total}}

# ═══ END SPRINT P ENDPOINTS ═══
'''

    # ── 3B: Build the /predict wiring block ──
    cd = scan["chart_data_var"]
    jd = scan["jaimini_data_var"]
    ld = scan["lk_data_var"]
    cc = scan["country_var"]
    bd = scan["birth_date_var"]

    predict_wire = f'''
        # --- Sprint P: Practice context for /predict (auto-patched) ---
        _practice_block = ""
        try:
            from antar_engine.practice_engine import generate_practice_schedule as _gen_ps, format_practice_for_predict_prompt as _fmt_pp
            _ps = _gen_ps(chart_data={cd} if isinstance({cd}, dict) else {{}}, jaimini_data={jd} if isinstance({jd}, dict) else {{}}, lal_kitab_data={ld} if isinstance({ld}, dict) else {{}}, current_country={cc} if isinstance({cc}, str) else "US", birth_date=str({bd}) if {bd} else None)
            _practice_block = _fmt_pp(_ps)
        except Exception as _pe:
            print(f"[PRACTICE] predict context failed: {{_pe}}")
            _practice_block = ""
        # --- End Sprint P practice context ---
'''

    # ── 3C: Insert into main.py ──

    # Insert endpoints before if __name__ guard
    guard_line = scan["main_guard_line"]
    info(f"Inserting 3 endpoints before line {guard_line + 1}")
    lines.insert(guard_line, endpoints_block)

    # Re-find lines after insertion (offsets shifted)
    # The predict wiring needs to go inside /predict, after LK context
    if scan["lk_context_line"] is not None:
        # Account for the endpoints block we just inserted
        insert_after = scan["lk_context_line"] + 1
        # But only if it's before the guard line (i.e. inside /predict)
        if insert_after < guard_line:
            info(f"Inserting /predict practice wire after line {insert_after + 1} (LK context)")
            lines.insert(insert_after + 1, predict_wire)

            # Also wire the practice block into the context string
            # Search for where context is assembled
            cv = scan["context_var"]
            if cv:
                for i in range(insert_after + 2, min(insert_after + 100, len(lines))):
                    # Find a line that concatenates context
                    if cv in lines[i] and ("+=" in lines[i] or "+" in lines[i] or "f'" in lines[i] or 'f"' in lines[i]):
                        # Insert after this line
                        indent = len(lines[i]) - len(lines[i].lstrip())
                        pad = " " * indent
                        inject = f'{pad}if _practice_block: {cv} += "\\n\\n" + _practice_block  # Sprint P'
                        lines.insert(i + 1, inject)
                        info(f"Injected practice block into '{cv}' at line {i + 2}")
                        break
        else:
            warn("LK context line is after __name__ guard — skipping /predict wire")
            warn("You'll need to manually paste the /predict wire (see below)")
    elif scan["claude_call_line"] is not None:
        # Fallback: insert before the Claude call
        insert_before = scan["claude_call_line"]
        if insert_before < guard_line:
            info(f"Inserting /predict practice wire before Claude call at line {insert_before + 1}")
            lines.insert(insert_before, predict_wire)
    else:
        warn("Could not find insertion point for /predict wiring")
        warn("You'll need to manually add the practice context block inside /predict")
        print(f"\n{YELLOW}Manual /predict wire block:{RESET}")
        print(predict_wire)

    new_content = "\n".join(lines)

    # ── 3D: Write patched main.py ──
    # Backup first
    backup_path = MAIN_PY + ".pre_sprint_p.bak"
    with open(backup_path, "w") as f:
        f.write(content)
    ok(f"Backup saved to {backup_path}")

    with open(MAIN_PY, "w") as f:
        f.write(new_content)
    ok(f"main.py patched ({len(new_content)} chars)")

    return new_content


# ════════════════════════════════════════════
# STEP 4: PRINT SUPABASE SQL
# ════════════════════════════════════════════
def print_sql():
    print(f"\n{BOLD}═══ Step 4: Supabase SQL Migration ═══{RESET}\n")
    print(f"{YELLOW}Run this in Supabase Dashboard → SQL Editor → New Query:{RESET}\n")

    sql = textwrap.dedent("""
    -- ANTAR Sprint P — Practice Engine Tables
    -- Run in Supabase SQL Editor

    CREATE TABLE IF NOT EXISTS practice_log (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        chart_id        UUID NOT NULL REFERENCES charts(id) ON DELETE CASCADE,
        practice_id     TEXT NOT NULL,
        planet          TEXT,
        practice_type   TEXT NOT NULL DEFAULT 'remedy',
        energy_label    TEXT,
        domain          TEXT,
        prescribed_at   TIMESTAMPTZ DEFAULT now(),
        completed_at    TIMESTAMPTZ,
        streak_count    INT DEFAULT 0,
        user_note       TEXT,
        created_at      TIMESTAMPTZ DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS practice_schedule_cache (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        chart_id        UUID NOT NULL REFERENCES charts(id) ON DELETE CASCADE,
        cache_key       TEXT NOT NULL,
        schedule_data   JSONB NOT NULL,
        week_of         DATE NOT NULL,
        created_at      TIMESTAMPTZ DEFAULT now(),
        UNIQUE(chart_id, week_of)
    );

    CREATE INDEX IF NOT EXISTS idx_practice_log_chart_id ON practice_log(chart_id);
    CREATE INDEX IF NOT EXISTS idx_practice_log_chart_completed ON practice_log(chart_id, completed_at DESC NULLS LAST);
    CREATE INDEX IF NOT EXISTS idx_practice_log_chart_date ON practice_log(chart_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_practice_schedule_cache_chart_week ON practice_schedule_cache(chart_id, week_of DESC);

    ALTER TABLE practice_log ENABLE ROW LEVEL SECURITY;
    ALTER TABLE practice_schedule_cache ENABLE ROW LEVEL SECURITY;

    DO $$ BEGIN
        CREATE POLICY "Allow all on practice_log" ON practice_log FOR ALL USING (true) WITH CHECK (true);
    EXCEPTION WHEN duplicate_object THEN NULL;
    END $$;

    DO $$ BEGIN
        CREATE POLICY "Allow all on practice_schedule_cache" ON practice_schedule_cache FOR ALL USING (true) WITH CHECK (true);
    EXCEPTION WHEN duplicate_object THEN NULL;
    END $$;

    SELECT 'practice_log' AS tbl, count(*) AS rows FROM practice_log
    UNION ALL
    SELECT 'practice_schedule_cache', count(*) FROM practice_schedule_cache;
    """).strip()

    print(sql)
    print()

    # Also write to file
    sql_file = os.path.join(REPO_ROOT, "sprint_p_migration.sql")
    with open(sql_file, "w") as f:
        f.write(sql + "\n")
    ok(f"SQL also saved to {sql_file}")


# ════════════════════════════════════════════
# STEP 5: VERIFY + DEPLOY
# ════════════════════════════════════════════
def verify_and_deploy():
    print(f"\n{BOLD}═══ Step 5: Verify & Deploy ═══{RESET}\n")

    # Syntax check patched main.py
    info("Checking main.py syntax...")
    import subprocess
    result = subprocess.run([sys.executable, "-c", f"import ast; ast.parse(open('{MAIN_PY}').read()); print('OK')"],
                         capture_output=True, text=True)
    if "OK" in result.stdout:
        ok("main.py syntax valid")
    else:
        fail(f"main.py syntax ERROR: {result.stderr}")
        fail("Restoring backup...")
        backup = MAIN_PY + ".pre_sprint_p.bak"
        if os.path.exists(backup):
            import shutil
            shutil.copy2(backup, MAIN_PY)
            ok("Backup restored. Fix the issue and re-run.")
        sys.exit(1)

    # Print verification commands
    print(f"\n{BOLD}Verification curls (run after deploy):{RESET}\n")
    base = "https://antar-fastapi-production.up.railway.app"
    chart = "de02bb52-d43a-4b09-be25-b45a07bfbf8a"

    print(f"  # 1. Schedule")
    print(f"  curl {base}/api/v1/practices/{chart}/schedule | python -m json.tool\n")
    print(f"  # 2. Complete a practice")
    print(f'  curl -X POST {base}/api/v1/practices/{chart}/complete \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{{"practice_id":"saturn_convergence_saturday"}}\' | python -m json.tool\n')
    print(f"  # 3. Check streak")
    print(f"  curl {base}/api/v1/practices/{chart}/streak | python -m json.tool\n")

    # Ask to deploy
    print(f"\n{BOLD}Ready to commit and push?{RESET}")
    print(f"  Files changed:")
    print(f"    - antar_engine/practice_engine.py (new)")
    print(f"    - main.py (patched — 3 endpoints + /predict wire)")
    print(f"    - sprint_p_migration.sql (for reference)\n")

    resp = input(f"  {CYAN}git add + commit + push? (y/n): {RESET}").strip().lower()
    if resp == "y":
        import subprocess
        subprocess.run(["git", "add", "antar_engine/practice_engine.py", "main.py", "sprint_p_migration.sql"], cwd=REPO_ROOT)
        subprocess.run(["git", "commit", "-m", "feat: Sprint P — practice engine, 3 endpoints, /predict wiring"], cwd=REPO_ROOT)
        result = subprocess.run(["git", "push"], cwd=REPO_ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            ok("Pushed! Railway will auto-deploy in ~60 seconds.")
            print(f"\n  {YELLOW}Don't forget: Run the SQL migration in Supabase FIRST!{RESET}")
        else:
            fail(f"Push failed: {result.stderr}")
    else:
        info("Skipped deploy. Run manually:")
        print(f"    git add antar_engine/practice_engine.py main.py sprint_p_migration.sql")
        print(f"    git commit -m 'feat: Sprint P — practice engine'")
        print(f"    git push")


# ════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════
def main():
    print(f"\n{BOLD}{CYAN}❆ ANTAR Sprint P — One-Shot Deploy{RESET}\n")

    content = preflight()
    write_practice_engine()
    scan = scan_main_py(content)
    patch_main_py(content, scan)
    print_sql()
    verify_and_deploy()

    print(f"\n{BOLD}{GREEN}❆ Sprint P deployment complete.{RESET}\n")


if __name__ == "__main__":
    main()
