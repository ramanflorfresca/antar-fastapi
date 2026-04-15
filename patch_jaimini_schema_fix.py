"""
patch_jaimini_schema_fix.py
Aligns jaimini_engine.py row builder with real dasha_periods schema
and removes the silent try/except pass in jaimini_integration.py.
Idempotent: checks whether patch already applied before modifying.
"""
import re
import shutil
from pathlib import Path

ENGINE_PATH = Path("antar_engine/jaimini_engine.py")
INTEGRATION_PATH = Path("antar_engine/jaimini_integration.py")

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8")

def backup(p: Path) -> None:
    bak = p.with_suffix(".py.bak_jaimini_schema")
    shutil.copy2(p, bak)
    print(f"  backed up → {bak}")

# ===========================================================================
# PATCH A+B — jaimini_engine.py: fix MD + AD row builders
# ===========================================================================

ENGINE_OLD = '''\
    for md in all_mds:
        # Level 1 (Mahadasha)
        rows.append({
            "chart_id": chart_id,
            "dasha_system": "jaimini_chara",
            "sign": md.sign,
            "sign_name": md.sign_name,
            "level": "MD",
            "level_int": 1,
            "start_date": md.start_date.isoformat(),
            "end_date": md.end_date.isoformat(),
            "duration_years": md.duration_years,
            "lord": md.lord,
            "direction": md.direction,
            "parent_sign": None
        })

        # Level 2 (Antardasha)
        for ad in md.sub_periods:
            rows.append({
                "chart_id": chart_id,
                "dasha_system": "jaimini_chara",
                "sign": ad.sign,
                "sign_name": ad.sign_name,
                "level": "AD",
                "level_int": 2,
                "start_date": ad.start_date.isoformat(),
                "end_date": ad.end_date.isoformat(),
                "duration_years": 0,
                "lord": ad.lord,
                "direction": ad.direction,
                "parent_sign": md.sign
            })'''

ENGINE_NEW = '''\
    for md_idx, md in enumerate(all_mds):
        # Level 1 (Mahadasha)
        rows.append({
            "chart_id": chart_id,
            "system": "jaimini",
            "type": "mahadasha",
            "level": 1,
            "sequence": md_idx,
            "planet_or_sign": md.sign_name,
            "start_date": md.start_date.isoformat(),
            "end_date": md.end_date.isoformat(),
            "duration_years": md.duration_years,
            "metadata": {
                "lord": md.lord,
                "direction": md.direction,
                "sign_index": md.sign,
            },
            "parent_id": None,
        })

        # Level 2 (Antardasha)
        for ad_idx, ad in enumerate(md.sub_periods):
            rows.append({
                "chart_id": chart_id,
                "system": "jaimini",
                "type": "antardasha",
                "level": 2,
                "sequence": (md_idx * 12) + ad_idx,
                "planet_or_sign": ad.sign_name,
                "start_date": ad.start_date.isoformat(),
                "end_date": ad.end_date.isoformat(),
                "duration_years": 0,
                "metadata": {
                    "lord": ad.lord,
                    "direction": ad.direction,
                    "sign_index": ad.sign,
                    "parent_md_sign": md.sign_name,
                },
                "parent_id": None,
            })'''

print("=== Patching jaimini_engine.py ===")
engine_text = read(ENGINE_PATH)

if '"system": "jaimini"' in engine_text:
    print("  SKIP: patch already applied (system=jaimini found)")
else:
    if ENGINE_OLD not in engine_text:
        print("  ERROR: landmark block not found in jaimini_engine.py — aborting")
        print("  Searching for partial landmark...")
        if "dasha_system" in engine_text:
            print("  Found 'dasha_system' in file — inspect manually")
        raise SystemExit(1)
    backup(ENGINE_PATH)
    engine_text = engine_text.replace(ENGINE_OLD, ENGINE_NEW, 1)
    write(ENGINE_PATH, engine_text)
    print("  OK: MD+AD row builders patched")

# ===========================================================================
# PATCH C — jaimini_integration.py: remove silent try/except pass
# ===========================================================================

# We look for the inner try block that silently swallows insert errors.
# Landmark: the comment immediately above the inner try.
INTEGRATION_OLD = '''\
            # Skip dasha row insertion if table doesn't have dasha_system column
            # The jaimini_data JSONB has all timing data — dasha rows are optional
            try:
                supabase_client.table("dasha_periods").delete().eq(
                    "chart_id", chart_id
                ).eq("dasha_system", "jaimini_chara").execute()
                if dasha_rows:
                    supabase_client.table("dasha_periods").insert(dasha_rows).execute()
                    logger.info(f"Inserted {len(dasha_rows)} Jaimini dasha rows for chart {chart_id}")
            except Exception as _de:
                pass  # dasha_periods table may not have dasha_system column yet'''

INTEGRATION_NEW = '''\
            # Wipe existing Jaimini rows for this chart, then re-insert
            supabase_client.table("dasha_periods").delete().eq(
                "chart_id", chart_id
            ).eq("system", "jaimini").execute()
            if dasha_rows:
                supabase_client.table("dasha_periods").insert(dasha_rows).execute()
                logger.info(f"Inserted {len(dasha_rows)} Jaimini dasha rows for chart {chart_id}")'''

print("\n=== Patching jaimini_integration.py ===")
integ_text = read(INTEGRATION_PATH)

if '.eq("system", "jaimini")' in integ_text:
    print("  SKIP: patch already applied (.eq('system','jaimini') found)")
else:
    if INTEGRATION_OLD not in integ_text:
        print("  ERROR: landmark block not found in jaimini_integration.py — aborting")
        print("  Checking for partial markers...")
        for marker in ["dasha_system column yet", "may not have dasha_system", "_de"]:
            if marker in integ_text:
                print(f"    Found marker: {marker!r}")
        raise SystemExit(1)
    backup(INTEGRATION_PATH)
    integ_text = integ_text.replace(INTEGRATION_OLD, INTEGRATION_NEW, 1)
    write(INTEGRATION_PATH, integ_text)
    print("  OK: silent try/except pass removed, filter changed to system=jaimini")

print("\n=== All patches applied successfully ===")
