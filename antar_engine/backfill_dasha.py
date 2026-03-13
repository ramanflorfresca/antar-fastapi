"""
backfill_dashas.py - Fixed version using correct DB column names
Run: PYTHONPATH=/Users/ramandeepsinghchadha/antarai python backfill_dashas.py
"""
import os, sys
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
sys.path.insert(0, os.path.dirname(__file__))

from supabase import create_client
from antar_engine import chart as chart_module
from antar_engine import vimsottari, jaimini, ashtottari

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])


def normalise_dashas(raw) -> list:
    if isinstance(raw, list): return raw
    if not isinstance(raw, dict): return []
    flat = []
    for p in raw.get("mahadashas", []):
        flat.append({"planet_or_sign": p.get("lord",""), "start": p.get("start_date","")[:10],
                     "end": p.get("end_date","")[:10], "duration_years": p.get("duration_years",0), "level":"mahadasha"})
    for p in raw.get("antardashas", []):
        flat.append({"planet_or_sign": p.get("lord",""), "start": p.get("start_date","")[:10],
                     "end": p.get("end_date","")[:10], "duration_years": p.get("duration_years",0), "level":"antardasha"})
    return flat


def backfill_chart(ch):
    chart_id   = ch["id"]
    birth_date = ch["birth_date"]
    birth_time = (ch.get("birth_time") or "00:00")[:5]  # strip seconds
    lat        = ch.get("latitude") or 18.1
    lng        = ch.get("longitude") or 78.85
    tz_offset  = ch.get("timezone_offset") or 5.5

    print(f"\n  chart {chart_id[:8]}  {birth_date} {birth_time}  {lat},{lng}  tz={tz_offset}")

    # Recompute to get birth_jd; merge house numbers into stored chart_data
    try:
        fresh = chart_module.calculate_chart(
            birth_date=birth_date, birth_time=birth_time,
            lat=lat, lng=lng, tz_offset=tz_offset, ayanamsa="lahiri",
        )
        birth_jd = fresh.get("birth_jd")
    except Exception as e:
        print(f"  ERROR computing chart: {e}"); return 0

    if not birth_jd:
        print("  ERROR: birth_jd missing"); return 0

    # Use stored chart_data if richer, else fresh
    stored = ch.get("chart_data") or {}
    if stored.get("planets") and stored.get("lagna"):
        chart_data = stored.copy()
        lagna_si = stored["lagna"].get("sign_index", 0)
        for pdata in chart_data["planets"].values():
            if "house" not in pdata:
                pdata["house"] = ((pdata.get("sign_index",0) - lagna_si) % 12) + 1
        chart_data["birth_jd"] = birth_jd
        print(f"  using stored chart_data (lagna={stored['lagna'].get('sign')})")
    else:
        chart_data = fresh
        print(f"  using fresh chart_data")

    vim_dashas = jai_dashas = ash_dashas = []
    try: vim_dashas = normalise_dashas(vimsottari.calculate_vimsottari_from_chart(chart_data, birth_jd)); print(f"  vimsottari: {len(vim_dashas)}")
    except Exception as e: print(f"  vimsottari error: {e}")
    try: jai_dashas = normalise_dashas(jaimini.calculate_chara_dasha_from_chart(chart_data, birth_jd)); print(f"  jaimini: {len(jai_dashas)}")
    except Exception as e: print(f"  jaimini error: {e}")
    try: ash_dashas = normalise_dashas(ashtottari.calculate_ashtottari_from_chart(chart_data, birth_jd)); print(f"  ashtottari: {len(ash_dashas)}")
    except Exception as e: print(f"  ashtottari error: {e}")

    if len(vim_dashas) + len(jai_dashas) + len(ash_dashas) == 0:
        print("  ERROR: all empty"); return 0

    try: sb.table("dasha_periods").delete().eq("chart_id", chart_id).execute()
    except Exception as e: print(f"  delete error: {e}")

    dasha_rows = []
    for system, periods in [("vimsottari",vim_dashas),("jaimini",jai_dashas),("ashtottari",ash_dashas)]:
        for i, p in enumerate(periods):
            dasha_rows.append({
                "chart_id": chart_id, "system": system,
                "type": p.get("level","mahadasha"),
                "level": 1 if p.get("level")=="mahadasha" else 2,
                "planet_or_sign": p.get("planet_or_sign",""),
                "start_date": p.get("start",""), "end_date": p.get("end",""),
                "duration_years": p.get("duration_years",0),
                "sequence": i, "metadata": {},
            })

    try:
        for i in range(0, len(dasha_rows), 100):
            sb.table("dasha_periods").insert(dasha_rows[i:i+100]).execute()
        print(f"  inserted {len(dasha_rows)} rows")
        return len(dasha_rows)
    except Exception as e:
        print(f"  INSERT ERROR: {e}"); return 0


def main():
    charts = sb.table("charts").select("*").execute()
    print(f"Found {len(charts.data)} charts\n")
    needs = []
    for ch in charts.data:
        d = sb.table("dasha_periods").select("id", count="exact").eq("chart_id", ch["id"]).execute()
        print(f"  {'BACKFILL' if d.count < 20 else 'ok'}: {ch['id'][:8]}  {ch['birth_date']}  dashas={d.count}")
        if d.count < 20: needs.append(ch)
    if not needs: print("\nAll complete."); return
    print(f"\nBackfilling {len(needs)} charts...")
    total = sum(backfill_chart(ch) for ch in needs)
    print(f"\nDone. Inserted {total} rows across {len(needs)} charts.")

if __name__ == "__main__":
    main()
