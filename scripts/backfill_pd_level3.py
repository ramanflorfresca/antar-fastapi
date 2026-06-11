#!/usr/bin/env python3
"""
scripts/backfill_pd_level3.py
=============================
Event Engine Rebuild — work item 1 (Cowork brief 2026-06-10).

`dasha_periods` has no level-3 (pratyantardasha) rows anywhere —
`vimsottari_from_db.current_pd.start = null, source=live_compute` confirmed.
This backfills PD rows for ALL charts from their existing level-2 ADs using
the deterministic Vimsottari proportional formula
(dasha_event_mapper._compute_pds_for_ad). Live compute stays as fallback only.

Idempotent: charts that already have level-3 vimsottari rows are skipped.
Stdlib-only HTTP (urllib) — runs anywhere with the repo .env.

Run:  python scripts/backfill_pd_level3.py            # all charts
      python scripts/backfill_pd_level3.py <chart_id> # one chart
      python scripts/backfill_pd_level3.py --dry-run  # count only
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from antar_engine.dasha_event_mapper import _compute_pds_for_ad  # noqa: E402

BATCH = 500


def _env():
    env = {}
    with open(os.path.join(ROOT, ".env")) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k] = v.strip().strip('"').strip("'")
    return env


def _req(url, key, method="GET", body=None, prefer=None):
    headers = {"apikey": key, "Authorization": f"Bearer {key}",
               "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def backfill_chart(base, key, chart_id, dry_run=False):
    rows = _req(
        f"{base}/rest/v1/dasha_periods?select=planet_or_sign,start_date,"
        f"end_date,level,metadata&chart_id=eq.{chart_id}"
        f"&system=eq.vimsottari&order=start_date", key)
    ads = [r for r in rows if r.get("level") == 2]
    has_pd = any(r.get("level") == 3 for r in rows)
    if has_pd:
        return ("skip_has_pd", 0)
    if not ads:
        return ("skip_no_ads", 0)

    new_rows = []
    for ad in ads:
        ad_lord = ad.get("planet_or_sign") or ""
        s = str(ad.get("start_date") or "")[:10]
        e = str(ad.get("end_date") or "")[:10]
        md_lord = ""
        meta = ad.get("metadata")
        if isinstance(meta, dict):
            md_lord = meta.get("parent_lord") or ""
        pds = _compute_pds_for_ad(ad_lord, s, e)
        for seq, pd in enumerate(pds, start=1):
            try:
                from datetime import date
                dur = (date.fromisoformat(pd["end"])
                       - date.fromisoformat(pd["start"])).days / 365.25
            except Exception:
                dur = 0.0
            new_rows.append({
                "chart_id": chart_id,
                "system": "vimsottari",
                "type": "pratyantardasha",
                "level": 3,
                "sequence": seq,
                "planet_or_sign": pd["lord"],
                "start_date": pd["start"],
                "end_date": pd["end"],
                "duration_years": round(dur, 6),
                "metadata": {"type": "pratyantardasha",
                             "parent_lord": ad_lord,
                             "parent_md": md_lord},
            })
    if dry_run:
        return ("would_insert", len(new_rows))
    for i in range(0, len(new_rows), BATCH):
        _req(f"{base}/rest/v1/dasha_periods", key, method="POST",
             body=new_rows[i:i + BATCH], prefer="return=minimal")
    return ("inserted", len(new_rows))


def main():
    env = _env()
    base = env["SUPABASE_URL"].rstrip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY") or env["SUPABASE_KEY"]
    dry = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        chart_ids = args
    else:
        charts = _req(f"{base}/rest/v1/charts?select=id&order=created_at",
                      key)
        chart_ids = [c["id"] for c in charts]

    totals = {"inserted": 0, "charts_done": 0, "skip_has_pd": 0,
              "skip_no_ads": 0, "errors": 0}
    for i, cid in enumerate(chart_ids):
        try:
            status, n = backfill_chart(base, key, cid, dry_run=dry)
        except Exception as e:
            totals["errors"] += 1
            print(f"  [{i+1}/{len(chart_ids)}] {cid[:8]} ERROR: {e}")
            continue
        if status in ("inserted", "would_insert"):
            totals["inserted"] += n
            totals["charts_done"] += 1
        else:
            totals[status] += 1
        if (i + 1) % 25 == 0 or status in ("inserted", "would_insert"):
            print(f"  [{i+1}/{len(chart_ids)}] {cid[:8]} {status} ({n})")
    print(f"\nDONE {'(dry-run) ' if dry else ''}— charts with PDs added: "
          f"{totals['charts_done']}, rows: {totals['inserted']}, "
          f"already-had-PD: {totals['skip_has_pd']}, "
          f"no-ADs: {totals['skip_no_ads']}, errors: {totals['errors']}")


if __name__ == "__main__":
    main()
