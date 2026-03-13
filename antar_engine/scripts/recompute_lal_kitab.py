#!/usr/bin/env python3
"""
ONE-TIME MIGRATION — recompute_lal_kitab_data.py
=================================================
Overwrites charts.lal_kitab_data for every chart row using the correct
120-row Varshphal table (varshaphal_table.py).

Run ONCE after deploying the fixed antar_engine files.

Usage:
    cd antarai
    python scripts/recompute_lal_kitab_data.py

Safe to re-run — each update is idempotent (upsert by chart id).
"""

import os
import sys
from datetime import datetime, date

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# ── resolve imports regardless of where the script lives ────────────────────
# works whether script is in antarai/ OR antarai/antar_engine/scripts/
_here = os.path.dirname(os.path.abspath(__file__))
# walk up until we find the antar_engine package
for _candidate in [_here, os.path.dirname(_here), os.path.dirname(os.path.dirname(_here))]:
    if os.path.isdir(os.path.join(_candidate, 'antar_engine')):
        sys.path.insert(0, _candidate)
        break
from antar_engine.varshaphal_table import get_annual_house

PLANET_PRIORITY = [
    "Sun", "Moon", "Mars", "Saturn", "Jupiter",
    "Rahu", "Ketu", "Venus", "Mercury",
]

_SPECIAL_CYCLES = {
    35: {"significance": "The 35-year karmic reset — major life restructuring indicated"},
    47: {"significance": "Wisdom and teaching phase — share your knowledge"},
    60: {"significance": "Second Saturn return — legacy crystallisation"},
    70: {"significance": "Double 35 — profound spiritual transition"},
}


def age_from_birth_date(birth_date_str: str) -> int:
    today = date.today()
    born  = date.fromisoformat(birth_date_str[:10])
    return today.year - born.year - (
        (today.month, today.day) < (born.month, born.day)
    )


def extract_natal_houses(chart_data: dict) -> dict:
    return {
        planet: pdata.get("house", pdata.get("sign_index", 0) + 1)
        for planet, pdata in chart_data.get("planets", {}).items()
    }


def compute_lk_data(chart_data: dict, birth_date_str: str) -> dict:
    age          = age_from_birth_date(birth_date_str)
    running_year = max(1, min(120, age + 1))
    natal_houses = extract_natal_houses(chart_data)

    placements = {
        planet: get_annual_house(natal_house, age)
        for planet, natal_house in natal_houses.items()
        if 1 <= natal_house <= 12
    }

    special = _SPECIAL_CYCLES.get(age)

    return {
        "age":                age,
        "table_age":          running_year,
        "placements":         placements,
        "is_special_cycle":   special is not None,
        "cycle_significance": special["significance"] if special else None,
        "predictions":        [],   # repopulated by generate_varshphal on next call
        "remedies_summary":   [],   # repopulated by generate_varshphal on next call
    }


def main():
    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    print("Fetching all charts...")
    result = supabase.table("charts").select("id, chart_data, birth_date").execute()
    charts = result.data or []
    print(f"Found {len(charts)} charts to recompute.")

    ok = 0
    skipped = 0
    errors = 0

    for row in charts:
        chart_id   = row["id"]
        chart_data = row.get("chart_data")
        birth_date = row.get("birth_date")

        if not chart_data or not birth_date:
            print(f"  SKIP {chart_id} — missing chart_data or birth_date")
            skipped += 1
            continue

        try:
            lk_data = compute_lk_data(chart_data, birth_date)
            age     = lk_data["age"]
            ry      = lk_data["table_age"]

            supabase.table("charts").update({
                "lal_kitab_data": lk_data,
                "lk_age":         age,
                "lk_computed_at": datetime.utcnow().isoformat(),
            }).eq("id", chart_id).execute()

            print(f"  OK  {chart_id} — Age {age}, running year {ry}, "
                  f"{len(lk_data['placements'])} placements")
            ok += 1

        except Exception as e:
            print(f"  ERR {chart_id} — {e}")
            errors += 1

    print()
    print(f"Done. OK={ok}  SKIPPED={skipped}  ERRORS={errors}")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
