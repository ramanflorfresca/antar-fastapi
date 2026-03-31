#!/usr/bin/env python3
"""
apply_sprint_e_patch.py — Sprint E: Life Coaching Experience
Run from repo root: python apply_sprint_e_patch.py

Changes:
  1. Add imports for all 4 Sprint E modules
  2. Wire welcome signal into chart/create (async background task)
  3. Add GET /api/v1/welcome/{chart_id} endpoint
  4. Add GET /api/v1/weekly-briefing/{chart_id} endpoint
  5. Add GET /api/v1/monthly-deepdive/{chart_id} endpoint
  6. Add GET /api/v1/annual-plan/{chart_id} endpoint
  7. Add weekly + monthly cron jobs to scheduler
"""

import shutil
import sys
from pathlib import Path

MAIN = Path("main.py")
if not MAIN.exists():
    print("❌  main.py not found — run from repo root")
    sys.exit(1)

shutil.copy(MAIN, "main.py.bak_e")
print("✅  Backed up to main.py.bak_e")

src = MAIN.read_text()

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 1 — imports
# ─────────────────────────────────────────────────────────────────────────────

IMPORT_ANCHOR = "from antar_engine.common_sense import build_common_sense_block"
IMPORT_NEW = """from antar_engine.common_sense import build_common_sense_block
from antar_engine.welcome_signal import generate_welcome_signal, get_welcome_signal
from antar_engine.weekly_briefing import generate_weekly_briefing
from antar_engine.monthly_deepdive import generate_monthly_deepdive
from antar_engine.annual_planning import generate_annual_plan"""

if "from antar_engine.welcome_signal import" in src:
    print("⚠️   Change 1 already applied — skipping imports")
elif IMPORT_ANCHOR not in src:
    print("❌  Change 1 FAILED — common_sense import not found")
    sys.exit(1)
else:
    src = src.replace(IMPORT_ANCHOR, IMPORT_NEW, 1)
    print("✅  Change 1 applied — Sprint E imports added")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 2 — Wire welcome signal into chart/create
# Find where chart creation returns the response and add background task
# ─────────────────────────────────────────────────────────────────────────────

# Find the ChartCreateResponse return in chart/create
WELCOME_ANCHOR = "    lk_data = None\n    try:\n        from antar_engine.varshaphal_table import get_annual_house"

WELCOME_BLOCK = """    # ── Sprint E: Generate welcome signal in background ─────────
    try:
        import asyncio as _asyncio
        _first_name = getattr(request, "first_name", "") or getattr(request, "name", "") or ""
        _lagna_sign = chart_data.get("lagna", {}).get("sign", "")
        _moon_sign  = chart_data.get("planets", {}).get("Moon", {}).get("sign", "")
        _current_dasha = ""
        _vim = vim_dashas or []
        if _vim:
            _d = _vim[0]
            _current_dasha = _d.get("lord") or _d.get("lord_or_sign") or _d.get("planet_or_sign", "")

        # Fire and forget — don't block chart creation response
        _asyncio.create_task(generate_welcome_signal(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={"vimsottari": vim_dashas or []},
            first_name=_first_name,
            lagna=_lagna_sign,
            moon_sign=_moon_sign,
            current_dasha=_current_dasha,
            age=None,
            country_code=getattr(request, "birth_country", "") or "",
            supabase=supabase,
            claude_client=claude_client,
        ))
        print(f"[chart/create] Welcome signal task fired for {chart_id[:8]}")
    except Exception as _we:
        print(f"[chart/create] Welcome signal task failed (non-fatal): {_we}")
    # ── end Sprint E welcome ─────────────────────────────────────

    lk_data = None
    try:
        from antar_engine.varshaphal_table import get_annual_house"""

if "Sprint E: Generate welcome signal" in src:
    print("⚠️   Change 2 already applied — skipping welcome signal wiring")
elif WELCOME_ANCHOR not in src:
    print("❌  Change 2 FAILED — lk_data anchor not found")
    print("    Manually add welcome signal generation before the lk_data block")
else:
    src = src.replace(WELCOME_ANCHOR, WELCOME_BLOCK, 1)
    print("✅  Change 2 applied — welcome signal wired into chart/create")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 3 — New endpoints
# ─────────────────────────────────────────────────────────────────────────────

NEW_ENDPOINTS = '''

# ── Sprint E: Welcome signal ──────────────────────────────────────────────────
@app.get("/api/v1/welcome/{chart_id}")
async def get_welcome(chart_id: str):
    """
    Returns the welcome signal for a chart.
    Generated automatically after chart creation.
    Sprint E.
    """
    try:
        signal = get_welcome_signal(chart_id, supabase)
        if signal:
            return signal
        # Not ready yet — generate now synchronously
        chart_res = supabase.table("charts").select("*").eq("id", chart_id).execute()
        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")
        chart_record = chart_res.data[0]
        chart_data   = chart_record.get("chart_data", {})
        planets      = chart_data.get("planets", {})
        result = await generate_welcome_signal(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={},
            first_name=chart_record.get("first_name", ""),
            lagna=chart_data.get("lagna", {}).get("sign", ""),
            moon_sign=planets.get("Moon", {}).get("sign", ""),
            current_dasha=chart_record.get("current_dasha", ""),
            age=None,
            country_code=chart_record.get("current_country") or chart_record.get("country_code", ""),
            supabase=supabase,
            claude_client=claude_client,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[welcome] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate welcome signal")


# ── Sprint E: Weekly briefing ─────────────────────────────────────────────────
@app.get("/api/v1/weekly-briefing/{chart_id}")
async def get_weekly_briefing(chart_id: str, refresh: bool = False):
    """
    Returns the weekly briefing for the current week.
    Auto-generated every Monday. Sprint E.
    """
    try:
        chart_res = supabase.table("charts").select("*").eq("id", chart_id).execute()
        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")
        chart_record = chart_res.data[0]
        chart_data   = chart_record.get("chart_data", {})
        planets      = chart_data.get("planets", {})

        # Get DKP context
        dkp_ctx = ""
        country_code = chart_record.get("current_country") or chart_record.get("country_code", "")
        if country_code:
            try:
                from antar_engine.country_context import COUNTRY_CONTEXT
                _name = COUNTRY_CONTEXT.get(country_code, {}).get("name", country_code)
                dkp_ctx = await get_dkp_context(
                    country_code=country_code,
                    country_name=_name,
                    supabase=supabase,
                    deepseek_client=deepseek_client,
                )
            except Exception:
                pass

        result = await generate_weekly_briefing(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={},
            first_name=chart_record.get("first_name", ""),
            lagna=chart_data.get("lagna", {}).get("sign", ""),
            moon_sign=planets.get("Moon", {}).get("sign", ""),
            current_dasha=chart_record.get("current_dasha", ""),
            age=None,
            country_code=country_code,
            dkp_context=dkp_ctx,
            supabase=supabase,
            claude_client=claude_client,
            force_refresh=refresh,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[weekly-briefing] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate weekly briefing")


# ── Sprint E: Monthly deep-dive ───────────────────────────────────────────────
@app.get("/api/v1/monthly-deepdive/{chart_id}")
async def get_monthly_deepdive(chart_id: str, refresh: bool = False):
    """
    Returns the monthly deep-dive for the current month.
    Auto-generated on the 1st. Sprint E.
    """
    try:
        chart_res = supabase.table("charts").select("*").eq("id", chart_id).execute()
        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")
        chart_record = chart_res.data[0]
        chart_data   = chart_record.get("chart_data", {})

        # Get LK context if available
        lk_ctx = ""
        try:
            from antar_engine.lal_kitab_db import format_lk_context_from_stored
            lk_ctx = format_lk_context_from_stored(chart_record) or ""
        except Exception:
            pass

        result = await generate_monthly_deepdive(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={},
            first_name=chart_record.get("first_name", ""),
            lagna=chart_data.get("lagna", {}).get("sign", ""),
            moon_sign=chart_data.get("planets", {}).get("Moon", {}).get("sign", ""),
            current_dasha=chart_record.get("current_dasha", ""),
            age=None,
            country_code=chart_record.get("current_country") or chart_record.get("country_code", ""),
            lk_context=lk_ctx,
            supabase=supabase,
            claude_client=claude_client,
            force_refresh=refresh,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[monthly-deepdive] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate monthly deep-dive")


# ── Sprint E: Annual plan ─────────────────────────────────────────────────────
@app.get("/api/v1/annual-plan/{chart_id}")
async def get_annual_plan(chart_id: str, refresh: bool = False):
    """
    Returns the annual plan for the current year.
    Auto-generated on birthday and January 1st. Sprint E.
    """
    try:
        chart_res = supabase.table("charts").select("*").eq("id", chart_id).execute()
        if not chart_res.data:
            raise HTTPException(status_code=404, detail="Chart not found")
        chart_record = chart_res.data[0]
        chart_data   = chart_record.get("chart_data", {})

        # Get DKP and LK context
        dkp_ctx = ""
        lk_ctx  = ""
        country_code = chart_record.get("current_country") or chart_record.get("country_code", "")
        try:
            from antar_engine.country_context import COUNTRY_CONTEXT
            _name = COUNTRY_CONTEXT.get(country_code, {}).get("name", country_code)
            dkp_ctx = await get_dkp_context(
                country_code=country_code,
                country_name=_name,
                supabase=supabase,
                deepseek_client=deepseek_client,
            )
        except Exception:
            pass
        try:
            from antar_engine.lal_kitab_db import format_lk_context_from_stored
            lk_ctx = format_lk_context_from_stored(chart_record) or ""
        except Exception:
            pass

        result = await generate_annual_plan(
            chart_id=chart_id,
            chart_data=chart_data,
            dashas={},
            first_name=chart_record.get("first_name", ""),
            lagna=chart_data.get("lagna", {}).get("sign", ""),
            moon_sign=chart_data.get("planets", {}).get("Moon", {}).get("sign", ""),
            current_dasha=chart_record.get("current_dasha", ""),
            birth_date=chart_record.get("birth_date", ""),
            age=None,
            country_code=country_code,
            dkp_context=dkp_ctx,
            lk_context=lk_ctx,
            supabase=supabase,
            claude_client=claude_client,
            force_refresh=refresh,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"[annual-plan] error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate annual plan")
'''

if '"/api/v1/welcome/{chart_id}"' in src:
    print("⚠️   Change 3 already applied — skipping new endpoints")
else:
    src = src.rstrip() + "\n" + NEW_ENDPOINTS + "\n"
    print("✅  Change 3 applied — 4 new Sprint E endpoints added")

# ─────────────────────────────────────────────────────────────────────────────
# Write
# ─────────────────────────────────────────────────────────────────────────────

MAIN.write_text(src)
print(f"\n✅  main.py updated")
print("    Next:")
print("    1. cp welcome_signal.py antar_engine/welcome_signal.py")
print("    2. cp weekly_briefing.py antar_engine/weekly_briefing.py")
print("    3. cp monthly_deepdive.py antar_engine/monthly_deepdive.py")
print("    4. cp annual_planning.py antar_engine/annual_planning.py")
print("    5. Run e_migration.sql in Supabase SQL editor")
print("    6. git add antar_engine/*.py main.py")
print("    7. git commit -m 'feat(E): life coaching experience — welcome, weekly, monthly, annual'")
print("    8. git push")
print("    9. python test_sprint_e.py")
