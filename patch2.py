#!/usr/bin/env python3
"""
apply_c2_patch.py — Sprint C2 patch for main.py
Run from your repo root: python apply_c2_patch.py

What it does:
  1. Adds desh_kal_patra import
  2. Replaces the existing country_context + nation_insight block
     with the full DKP context (richer, cached, real-time economic data)
  3. Adds DKP to the weekly cron scheduler
"""

import shutil
import sys
from pathlib import Path

MAIN = Path("main.py")
if not MAIN.exists():
    print("❌  main.py not found — run from repo root")
    sys.exit(1)

shutil.copy(MAIN, "main.py.bak_c2")
print("✅  Backed up to main.py.bak_c2")

src = MAIN.read_text()

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 1 — import
# ─────────────────────────────────────────────────────────────────────────────

IMPORT_ANCHOR = "from antar_engine.plain_english import generate_plain_english"
IMPORT_NEW    = (
    "from antar_engine.plain_english import generate_plain_english\n"
    "from antar_engine.desh_kal_patra import get_dkp_context"
)

if "from antar_engine.desh_kal_patra import get_dkp_context" in src:
    print("⚠️   Change 1 already applied — skipping import")
elif IMPORT_ANCHOR not in src:
    print("❌  Change 1 FAILED — plain_english import not found")
    sys.exit(1)
else:
    src = src.replace(IMPORT_ANCHOR, IMPORT_NEW, 1)
    print("✅  Change 1 applied — desh_kal_patra import added")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 2 — replace country_context + nation_insight block with DKP
# ─────────────────────────────────────────────────────────────────────────────

OLD_BLOCK = """    # Country context
    country_code = chart_record.get("country_code")
    country_context = get_country_context(country_code) if country_code else ""

    # Timing
    timing_text = timing_engine.timing_insights(chart_data, dashas_response)

    # Nation insight
    nation_insight = ""
    if country_code:
        try:
            nation_insight = nation_engine.get_nation_insight(
                country_code, supabase, deepseek_client, language
            )
        except Exception as e:
            print(f"Nation insight error: {e}")"""

NEW_BLOCK = """    # Country context — static cultural layer (always available)
    country_code = chart_record.get("country_code")
    country_context = get_country_context(country_code) if country_code else ""

    # Timing
    timing_text = timing_engine.timing_insights(chart_data, dashas_response)

    # ── C2: Desh Kal Patra — real-world economic context ──────────
    dkp_context  = ""
    nation_insight = ""
    if country_code:
        try:
            from antar_engine.country_context import COUNTRY_CONTEXT
            _country_name = COUNTRY_CONTEXT.get(country_code, {}).get("name", country_code)
            dkp_context = await get_dkp_context(
                country_code=country_code,
                country_name=_country_name,
                supabase=supabase,
                deepseek_client=deepseek_client,
            )
            print(f"[predict] DKP loaded for {country_code} ({len(dkp_context)} chars)")
        except Exception as e:
            print(f"[predict] DKP failed (non-fatal): {e}")

        # Nation astrological insight (existing — keep as fallback)
        try:
            nation_insight = nation_engine.get_nation_insight(
                country_code, supabase, deepseek_client, language
            )
        except Exception as e:
            print(f"Nation insight error: {e}")
    # ── end C2 ───────────────────────────────────────────────────"""

if "dkp_context = await get_dkp_context" in src:
    print("⚠️   Change 2 already applied — skipping DKP block")
elif OLD_BLOCK not in src:
    print("❌  Change 2 FAILED — country_context block not found")
    print("    Check that main.py still has the original country_context block")
    sys.exit(1)
else:
    src = src.replace(OLD_BLOCK, NEW_BLOCK, 1)
    print("✅  Change 2 applied — DKP block wired in")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 3 — wire dkp_context into the prompt builder
# Find where country_context is passed to build_predict_prompt and add dkp_context
# ─────────────────────────────────────────────────────────────────────────────

OLD_PROMPT = "            country_context=country_context,"
NEW_PROMPT = (
    "            country_context=country_context,\n"
    "            dkp_context=dkp_context,"
)

if "dkp_context=dkp_context" in src:
    print("⚠️   Change 3 already applied — skipping prompt builder update")
elif OLD_PROMPT not in src:
    print("⚠️   Change 3 — country_context prompt line not found")
    print("    Manually add `dkp_context=dkp_context` next to country_context in build_predict_prompt()")
else:
    src = src.replace(OLD_PROMPT, NEW_PROMPT, 1)
    print("✅  Change 3 applied — dkp_context added to prompt builder")

# ─────────────────────────────────────────────────────────────────────────────
# CHANGE 4 — add DKP weekly refresh to cron scheduler
# Find the scheduler setup and add a weekly DKP refresh job
# ─────────────────────────────────────────────────────────────────────────────

CRON_ANCHOR = "scheduler.add_job(ping_cron"
CRON_NEW = """scheduler.add_job(
        lambda: __import__('asyncio').create_task(
            __import__('antar_engine.desh_kal_patra', fromlist=['refresh_all_country_contexts'])
            .refresh_all_country_contexts(supabase, deepseek_client)
        ),
        "cron",
        day_of_week="mon",
        hour=5,
        minute=0,
        id="dkp_weekly_refresh",
        replace_existing=True,
    )
    scheduler.add_job(ping_cron"""

if "dkp_weekly_refresh" in src:
    print("⚠️   Change 4 already applied — skipping cron job")
elif CRON_ANCHOR not in src:
    print("⚠️   Change 4 — scheduler not found, skipping (add DKP cron manually if needed)")
else:
    src = src.replace(CRON_ANCHOR, CRON_NEW, 1)
    print("✅  Change 4 applied — DKP weekly refresh cron added")

# ─────────────────────────────────────────────────────────────────────────────
# Write
# ─────────────────────────────────────────────────────────────────────────────

MAIN.write_text(src)
print(f"\n✅  main.py updated. Backup at main.py.bak_c2")
print("    Next steps:")
print("    1. Copy desh_kal_patra.py → antar_engine/desh_kal_patra.py")
print("    2. Run c2_migration.sql in Supabase SQL editor")
print("    3. Check if build_predict_prompt() accepts dkp_context param")
print("       (run: grep -n 'def build_predict_prompt' antar_engine/*.py)")
print("    4. git add antar_engine/desh_kal_patra.py main.py && git commit -m 'feat(C2): desh kal patra' && git push")
