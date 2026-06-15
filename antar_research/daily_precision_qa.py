"""
antar_research/daily_precision_qa.py — read-only QA for daily precision (steps 1-3).

Proves the chart-relative layer without the LLM: for two charts with different
natal Moon nakshatras, compute tara + moon-house + blended score for the next 3
days and assert the brief's acceptance criteria.

Usage:
    source venv311/bin/activate
    python -m antar_research.daily_precision_qa
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

from antar_engine.daily_prediction_engine import get_moon_data_for_date, _score_day
from antar_engine.daily_precision import compute_daily_precision, apply_precision_to_score

BASE = "https://antar-fastapi-production.up.railway.app"
CHARTS = {
    "Musk":   "761626dc-2c66-402d-aa3a-9b731df75078",
    "Andres": "6ec6311c-d46e-4e97-a46c-859882071971",
}


def _live_moon_series(cid):
    """date -> {'nakshatra','sign'} from the live endpoint (universal ephemeris).
    Used when local swisseph isn't available (e.g. CI/sandbox)."""
    try:
        req = urllib.request.Request(f"{BASE}/api/v1/daily-week/{cid}?tz_offset=0&language=en")
        d = json.load(urllib.request.urlopen(req, timeout=40))
        return {day["date"]: {"nakshatra": day.get("moon_nakshatra"),
                              "sign": day.get("moon_sign")}
                for day in d.get("days", [])}
    except Exception:
        return {}


def _moon_for(date_obj, live_series):
    md = get_moon_data_for_date(date_obj, tz_offset=0)
    if md.get("nakshatra") and md["nakshatra"] != "Unknown":
        return md
    return live_series.get(date_obj.strftime("%Y-%m-%d"), {"nakshatra": None, "sign": None})


def _env():
    env = {}
    for line in open(os.path.join(os.path.dirname(__file__), "..", ".env")):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v.strip().strip('"')
    return env


def _natal(env, cid):
    url = env["SUPABASE_URL"]
    key = (env.get("SUPABASE_SERVICE_ROLE_KEY")
           or env.get("SUPABASE_KEY") or env.get("SUPABASE_ANON_KEY"))
    req = urllib.request.Request(
        f"{url}/rest/v1/charts?id=eq.{cid}&select=chart_data,lagna_sign",
        headers={"apikey": key, "Authorization": "Bearer " + key})
    row = json.load(urllib.request.urlopen(req, timeout=25))[0]
    cd = row["chart_data"]
    if isinstance(cd, str):
        cd = json.loads(cd)
    moon = (cd.get("planets", {}) or {}).get("Moon", {})
    lagna = (cd.get("lagna", {}) or {}).get("sign") or row.get("lagna_sign")
    return moon.get("nakshatra"), moon.get("sign"), lagna


def main():
    env = _env()
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    data = {}

    live_series = _live_moon_series(CHARTS["Musk"])   # universal ephemeris, any chart

    for nm, cid in CHARTS.items():
        nmn, nms, lagna = _natal(env, cid)
        print(f"### {nm}  natal Moon {nms}/{nmn}, lagna {lagna}")
        rows = []
        for i in range(3):
            d = start + timedelta(days=i)
            md = _moon_for(d, live_series)
            base, _ = _score_day(md["sign"], nms, md["nakshatra"], d.strftime("%A"))
            prec = compute_daily_precision(nmn, lagna, md["nakshatra"], md["sign"])
            blended, friction = apply_precision_to_score(base, prec)
            rows.append({"date": d.strftime("%Y-%m-%d"), "wd": d.strftime("%A"),
                         "nak": md["nakshatra"], "tara": prec["tara"],
                         "q": prec["tara_quality"], "house": prec["moon_house_from_lagna"],
                         "domain": prec["lit_domain"], "base": base, "score": blended,
                         "src": prec["source"]})
            print(f"   {rows[-1]['date']} {rows[-1]['wd']:9} nak={md['nakshatra']:14} "
                  f"tara={prec['tara']}/{prec['tara_quality']} "
                  f"house={prec['moon_house_from_lagna']}({prec['lit_domain']}) "
                  f"base={base} -> score={blended}")
        data[nm] = rows

    print("\n" + "=" * 60 + "\nACCEPTANCE\n" + "=" * 60)
    passed = True

    def check(label, cond):
        nonlocal passed
        passed = passed and cond
        print(f"  [{'PASS' if cond else 'FAIL'}] {label}")

    # 1. Same chart, consecutive days differ on tara/house/score
    for nm, rows in data.items():
        taras = {r["tara"] for r in rows}
        houses = {r["house"] for r in rows}
        scores = {r["score"] for r in rows}
        check(f"{nm}: days 0-2 vary on tara OR house OR score "
              f"(taras={taras}, houses={houses}, scores={scores})",
              len(taras) > 1 or len(houses) > 1 or len(scores) > 1)

    # 2. Two charts, same date (day 0), different tara/quality
    m0, a0 = data["Musk"][0], data["Andres"][0]
    check(f"Two charts day-0 differ on tara ({m0['tara']}/{m0['q']} vs "
          f"{a0['tara']}/{a0['q']})",
          (m0["tara"], m0["q"]) != (a0["tara"], a0["q"]) or m0["house"] != a0["house"])

    # 3. Score actually moved off the generic base for at least one row
    moved = any(r["score"] != r["base"] for rows in data.values() for r in rows)
    check("Blended score differs from generic base on >=1 day", moved)

    # 4. Every row carries a source
    check("Every row carries a non-empty source",
          all(r["src"] for rows in data.values() for r in rows))

    print("\n" + ("ALL CHECKS PASSED" if passed else "SOME CHECKS FAILED"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
