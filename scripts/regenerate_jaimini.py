"""
scripts/regenerate_jaimini.py
Regenerate Jaimini Chara Dasha rows for 9 validated charts
using the corrected schema (system/type/level/sequence/planet_or_sign/metadata).
"""
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client
from dotenv import load_dotenv
from antar_engine.jaimini_integration import build_and_store_jaimini

load_dotenv()

sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

PREFIXES = {
    "AA":      "7c38b6b7",
    "Vikram":  "a4d32fc8",
    "Raman":   "de02bb52",
    "Andres":  "6ec6311c",
    "Gayatri": "d725ce95",
    "Leena":   "e3a3dac7",
    "Jonatan": "0cd4d01a",
    "AT":      "ee0e5dab",
    "JS":      "6b7ab7b0",
}

SIGN_INDEX = {
    "Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3,
    "Leo": 4, "Virgo": 5, "Libra": 6, "Scorpio": 7,
    "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11,
}

print("Fetching all charts...")
all_charts = sb.table("charts").select("id, birth_date, chart_data").execute()
print(f"  {len(all_charts.data)} charts in DB\n")

success = 0
skipped = 0
failed = 0

for label, prefix in PREFIXES.items():
    chart = next((c for c in all_charts.data if c["id"].startswith(prefix)), None)
    if not chart:
        print(f"SKIP {label} (prefix={prefix}): not found in DB")
        skipped += 1
        continue

    cd = chart["chart_data"]
    if isinstance(cd, str):
        import json
        cd = json.loads(cd)

    lagna_raw = cd.get("lagna")
    # lagna can be a plain string "Capricorn" or a dict {"sign": "Capricorn", ...}
    if isinstance(lagna_raw, dict):
        lagna_str = lagna_raw.get("sign") or lagna_raw.get("name") or lagna_raw.get("sign_name")
    else:
        lagna_str = lagna_raw
    if not lagna_str or lagna_str not in SIGN_INDEX:
        print(f"SKIP {label} ({chart['id'][:8]}): bad lagna={lagna_raw!r}")
        skipped += 1
        continue

    planets = cd.get("planets", {})
    d9_data = cd.get("divisional_charts", {}).get("d9", {})
    d9_planets = d9_data.get("planets", {})

    print(f"{label} ({chart['id'][:8]}, lagna={lagna_str}): regenerating...")
    try:
        result = build_and_store_jaimini(
            chart_id=chart["id"],
            lagna_sign=SIGN_INDEX[lagna_str],
            planets_dict=planets,
            d9_planets_dict=d9_planets,
            birth_date_str=chart["birth_date"],
            supabase_client=sb,
        )
        row_count = len(result.get("dasha_rows", []))
        print(f"  OK — {row_count} rows stored")
        success += 1
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        failed += 1

print(f"\n=== Summary: {success} OK / {skipped} skipped / {failed} failed ===")
if failed:
    sys.exit(1)
