# Generate Pratyantardasha for all charts
# Backfills dasha_periods table with level=3 rows
#!/usr/bin/env python3
"""
scripts/generate_pds.py
========================
Generate Pratyantardasha (PD, level 3) for all charts and store in dasha_periods.

Vimsottari PD calculation:
  PD duration = AD duration × (PD planet years / 120)
  PD sequence starts from the AD planet

USAGE:
  cd ~/antarai && source venv311/bin/activate
  
  # Dry run first — see what would be inserted
  python scripts/generate_pds.py --dry-run
  
  # Single chart
  python scripts/generate_pds.py --chart-id de02bb52-d43a-4b09-be25-b45a07bfbf8a
  
  # All charts
  python scripts/generate_pds.py --all

VERIFY:
  python3 -c "
  import os
  from dotenv import load_dotenv
  from supabase import create_client
  load_dotenv()
  sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
  r = sb.table('dasha_periods').select('id', count='exact').eq('level', 3).execute()
  print('PD rows:', r.count)
  "
"""

import os, sys, argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase import create_client

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

# Vimsottari planet years
VIM_YEARS = {
    "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16,
    "Saturn": 19, "Mercury": 17, "Ketu": 7, "Venus": 20
}

SEQUENCE = ["Sun", "Moon", "Mars", "Rahu", "Jupiter",
            "Saturn", "Mercury", "Ketu", "Venus"]


def calculate_pds(md_planet: str, ad_planet: str,
                  ad_start: datetime, ad_end: datetime) -> list:
    """Calculate all PDs within a given AD window."""
    ad_duration_days = (ad_end - ad_start).days
    if ad_duration_days <= 0:
        return []

    ad_idx = SEQUENCE.index(ad_planet)
    pd_order = SEQUENCE[ad_idx:] + SEQUENCE[:ad_idx]

    pds = []
    current = ad_start
    for pd_planet in pd_order:
        pd_days = ad_duration_days * VIM_YEARS[pd_planet] / 120.0
        pd_end = current + timedelta(days=pd_days)
        pds.append({
            "md":    md_planet,
            "ad":    ad_planet,
            "pd":    pd_planet,
            "start": current,
            "end":   pd_end,
        })
        current = pd_end
    return pds


def parse_date(date_str: str) -> datetime:
    """Parse date string from Supabase."""
    if not date_str:
        return None
    ds = str(date_str)[:10]
    return datetime.strptime(ds, "%Y-%m-%d")


def generate_pds_for_chart(chart_id: str, dry_run: bool = False) -> int:
    """
    Generate and store all PDs for a chart.
    Returns number of PD rows inserted.
    """
    # Fetch existing vimsottari periods
    res = sb.table("dasha_periods") \
        .select("id,planet_or_sign,start_date,end_date,level,type,metadata,sequence") \
        .eq("chart_id", chart_id) \
        .eq("system", "vimsottari") \
        .order("start_date") \
        .execute()

    rows = res.data

    # Check if PDs already exist
    existing_pds = [r for r in rows if r.get("level") == 3 or
                    str(r.get("type","")).lower() in ("pratyantardasha","pd","3")]
    if existing_pds:
        print(f"  {chart_id[:8]}: {len(existing_pds)} PDs already exist — skipping")
        return 0

    # Get MDs and ADs
    mds = {r["planet_or_sign"]: r for r in rows
           if r.get("level") == 1 or str(r.get("type","")).lower() in ("mahadasha","md","1")}
    ads = [r for r in rows
           if r.get("level") == 2 or str(r.get("type","")).lower() in ("antardasha","ad","2")]

    if not ads:
        print(f"  {chart_id[:8]}: No ADs found — skipping")
        return 0

    # Generate PDs for each AD
    pd_rows = []
    seq = 1000  # start sequence after existing rows

    for ad in ads:
        ad_planet = ad["planet_or_sign"]
        ad_start  = parse_date(ad["start_date"])
        ad_end    = parse_date(ad["end_date"])
        md_planet = (ad.get("metadata") or {}).get("parent_lord", "")

        if not ad_start or not ad_end or not md_planet:
            continue

        pds = calculate_pds(md_planet, ad_planet, ad_start, ad_end)

        for pd in pds:
            pd_rows.append({
                "chart_id":       chart_id,
                "system":         "vimsottari",
                "type":           "pratyantardasha",
                "level":          3,
                "sequence":       seq,
                "planet_or_sign": pd["pd"],
                "start_date":     pd["start"].strftime("%Y-%m-%d"),
                "end_date":       pd["end"].strftime("%Y-%m-%d"),
                "duration_years": round((pd["end"] - pd["start"]).days / 365.25, 4),
                "metadata": {
                    "parent_lord":    md_planet,
                    "parent_ad":      ad_planet,
                    "type":           "pratyantardasha",
                },
            })
            seq += 1

    if not pd_rows:
        print(f"  {chart_id[:8]}: No PDs generated")
        return 0

    if dry_run:
        print(f"  {chart_id[:8]}: Would insert {len(pd_rows)} PD rows")
        # Show sample
        for row in pd_rows[:3]:
            print(f"    {row['metadata']['parent_lord']}-{row['metadata']['parent_ad']}-{row['planet_or_sign']:10s} "
                  f"{row['start_date']} -> {row['end_date']}")
        print(f"    ... and {len(pd_rows)-3} more")
        return len(pd_rows)

    # Insert in batches of 100
    inserted = 0
    batch_size = 100
    for i in range(0, len(pd_rows), batch_size):
        batch = pd_rows[i:i+batch_size]
        sb.table("dasha_periods").insert(batch).execute()
        inserted += len(batch)

    print(f"  {chart_id[:8]}: Inserted {inserted} PD rows")
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Generate Pratyantardasha for charts")
    parser.add_argument("--chart-id", help="Single chart ID")
    parser.add_argument("--all", action="store_true", help="All charts")
    parser.add_argument("--dry-run", action="store_true", help="Preview without inserting")
    args = parser.parse_args()

    if not args.chart_id and not args.all:
        parser.print_help()
        sys.exit(1)

    if args.dry_run:
        print("DRY RUN — no data will be inserted\n")

    if args.chart_id:
        chart_ids = [args.chart_id]
    else:
        # Get all chart IDs
        res = sb.table("charts").select("id,name,first_name").execute()
        chart_ids = [r["id"] for r in res.data]
        print(f"Found {len(chart_ids)} charts\n")

    total = 0
    for cid in chart_ids:
        count = generate_pds_for_chart(cid, dry_run=args.dry_run)
        total += count

    print(f"\nTotal PD rows {'would be inserted' if args.dry_run else 'inserted'}: {total}")
    print(f"Average per chart: {total // max(len(chart_ids), 1)}")
    print()
    print("Each chart has ~90 ADs × 9 PDs = ~810 PD rows")
    print("This enables month-level timing precision vs current year-level")


if __name__ == "__main__":
    main()
