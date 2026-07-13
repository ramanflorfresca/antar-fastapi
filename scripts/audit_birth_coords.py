#!/usr/bin/env python3
"""
scripts/audit_birth_coords.py
=============================
[desh-kaal-patra P2 2026-07-12] Find charts whose BIRTH coords are a country
centroid / capital PLACEHOLDER rather than the real birth city, and (read-only)
show what a recompute would change.

Fixing these properly means geocoding birth_city -> real coords and RECOMPUTING
the natal chart (ascendant + house cusps shift), which changes every downstream
prediction. So this script never writes: it identifies scope and, per chart,
does a dry-run diff (current lagna vs. corrected lagna) so the fix can be applied
deliberately, with eyes open.

USAGE:
  source venv311/bin/activate
  python scripts/audit_birth_coords.py                       # list placeholder charts
  python scripts/audit_birth_coords.py --chart-id <id>       # dry-run recompute diff
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main  # noqa: E402

# The India centroid is NEVER a real birthplace -> always a placeholder.
# The Delhi coords ARE New Delhi's real coords, so they're only a placeholder
# when the birth_city clearly isn't Delhi.
_INDIA_CENTROID = (20.5937, 78.9629)
_DELHI = (28.6139, 77.209)


def _near(lat, lng, pt):
    return (lat is not None and lng is not None
            and abs(float(lat) - pt[0]) < 1e-3 and abs(float(lng) - pt[1]) < 1e-3)


def _is_placeholder(lat, lng, birth_city=""):
    """Return (label, definite:bool) or None."""
    if _near(lat, lng, _INDIA_CENTROID):
        return ("India centroid", True)                 # never a real birthplace
    if _near(lat, lng, _DELHI):
        city = (birth_city or "").strip().lower()
        if not city:
            return ("Delhi coords, city missing", False)   # suspect, can't confirm
        if "delhi" not in city:
            return (f"Delhi coords but city={birth_city!r}", True)  # mismatch = placeholder
    return None


async def diff_one(cid: str):
    sb = main.supabase
    r = sb.table("charts").select(
        "id,first_name,birth_date,birth_time,birth_city,birth_country,"
        "latitude,longitude,timezone_offset,chart_data").eq("id", cid).limit(1).execute()
    if not r.data:
        print("chart not found"); return
    d = r.data[0]
    import json
    cd = d["chart_data"]
    cd = json.loads(cd) if isinstance(cd, str) else (cd or {})
    cur_lagna = (cd.get("lagna") or {})
    cur_lagna_sign = cur_lagna.get("sign") if isinstance(cur_lagna, dict) else cur_lagna
    print(f"chart {cid[:8]} — {d.get('first_name')} | birth {d.get('birth_city')},"
          f"{d.get('birth_country')} {d.get('birth_date')} {d.get('birth_time')}")
    _ph = _is_placeholder(d.get('latitude'), d.get('longitude'), d.get('birth_city'))
    print(f"  stored coords: ({d.get('latitude')}, {d.get('longitude')})  "
          f"[{_ph[0] if _ph else 'looks specific'}]")
    print(f"  current lagna: {cur_lagna_sign}")
    lat, lng, tz_id, src = await main._geocode_city(d.get("birth_city") or "",
                                                    d.get("birth_country") or "")
    print(f"  real {d.get('birth_city')}: ({lat:.4f}, {lng:.4f}) [{src}]")
    from antar_engine.antar_ephemeris import build_chart
    tz = float(d.get("timezone_offset") or 5.5)
    fixed = build_chart(str(d["birth_date"])[:10], str(d.get("birth_time") or "12:00")[:5],
                        float(lat), float(lng), tz)
    new_lagna = (fixed.get("lagna") or {})
    new_lagna_sign = new_lagna.get("sign") if isinstance(new_lagna, dict) else new_lagna
    flip = "  <-- LAGNA SIGN CHANGES" if (new_lagna_sign and new_lagna_sign != cur_lagna_sign) else ""
    print(f"  corrected lagna: {new_lagna_sign}{flip}")
    print("  (read-only — no write. Recompute changes ascendant + houses + all reads.)")


async def list_all():
    sb = main.supabase
    rows = sb.table("charts").select(
        "id,first_name,birth_city,birth_country,latitude,longitude").limit(5000).execute().data or []
    definite, suspect = [], []
    for r in rows:
        ph = _is_placeholder(r.get("latitude"), r.get("longitude"), r.get("birth_city"))
        if ph:
            (definite if ph[1] else suspect).append((r, ph[0]))
    print(f"scanned {len(rows)} charts")
    print(f"  DEFINITE placeholders (real fix needed): {len(definite)}")
    print(f"  suspect (Delhi coords, city missing — can't confirm): {len(suspect)}")
    for r, why in definite[:50]:
        print(f"    {r['id'][:8]} {(r.get('first_name') or '')[:12]:12} "
              f"{(r.get('birth_city') or '')[:16]:16} ({r.get('latitude')},{r.get('longitude')})  [{why}]")
    if len(definite) > 50:
        print(f"    ... +{len(definite)-50} more")
    print("\nFix = geocode birth_city + recompute natal chart (deliberate; changes reads).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--chart-id", default=None)
    a = ap.parse_args()
    asyncio.run(diff_one(a.chart_id) if a.chart_id else list_all())
