#!/usr/bin/env python3
"""
scripts/event_convergence_harness.py
====================================
Blind precision harness for the convergence engine (Cowork brief 2026-06-10).

Acceptance gate (precision-only — recall is not measurable without complete
life lists):
  - of surfaced predictions, >=60% confirmed-correct
    (event date inside window +/- tolerance; "within ~3 months of any real
    instance" for recurring events),
  - ZERO confirmed-wrong on painful events,
  - "unknown" (no ground truth for that event type) held aside, not scored.

Ground truth below is founder-provided (sessions 2026-06-08..11).
Harleen/Shashi confirmed dates PENDING — placeholders marked TODO; the
harness skips charts whose ground truth is empty.

Needs swisseph (run on the Mac venv or Railway):
  cd ~/antarai && source venv311/bin/activate
  python scripts/event_convergence_harness.py
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

# tolerance: 92d for dated events, 215d when ground truth is year-only
T_DATE = 92
T_YEAR = 215

# (event_type, 'YYYY-MM-DD', tolerance_days). Recurring events list every
# known instance — a surfaced window matching ANY instance is a hit.
GROUND_TRUTH = {
    "a4c9d57b-fb9c-4890-8fe7-4a9904f515ed": {  # Raman — Capricorn, 1974-11-26
        "label": "Raman",
        "events": [
            ("serious_partnership_began", "1998-01-15", T_DATE),
            ("serious_partnership_ended", "2014-09-15", T_DATE),
            ("family_expansion_first",    "2001-11-15", T_DATE),
            ("family_expansion_second",   "2003-10-15", T_DATE),
            ("major_relocation",          "1992-05-15", T_DATE),   # USA
            ("major_relocation",          "2002-12-15", T_DATE),   # Florida
            ("major_relocation",          "2018-06-15", T_YEAR),   # Colombia
            ("major_acquisition",         "1998-06-15", T_YEAR),   # residence
            ("major_acquisition",         "2003-06-15", T_YEAR),   # residence
            ("business_start",            "2015-06-15", T_YEAR),   # solo startup
        ],
    },
    "a2b1178f-17e5-4321-b5c2-2eb7c684385d": {  # Rishipal — Aquarius, 1976-09-01
        "label": "Rishipal",
        "events": [
            ("serious_partnership_began", "2004-07-25", T_DATE),   # 1st marriage
            ("serious_partnership_began", "2012-02-15", T_DATE),   # 2nd marriage
            ("serious_partnership_ended", "2005-12-15", T_YEAR),   # divorce 2005-06
            ("family_expansion_first",    "2016-02-15", T_DATE),
            ("family_expansion_second",   "2020-06-19", T_DATE),
        ],
    },
    "4e68bd94-8eb6-47f1-a2cc-592ce923a32c": {  # Harleen — Taurus, 1974-11-26
        "label": "Harleen",
        "events": [
            # TODO founder: confirmed dates (marriage, relocations, children…)
        ],
    },
    "9dff84f7-6171-4372-bdb6-1f266696816d": {  # Shashi — Libra, 1970-11-02
        "label": "Shashi",
        "events": [
            # TODO founder: confirmed dates (marriage, migration, children…)
        ],
    },
}

PAINFUL = {"serious_partnership_ended", "professional_setback",
           "legal_entanglement", "financial_disruption",
           "loss_of_father", "loss_of_mother"}


def _env():
    env = {}
    with open(os.path.join(ROOT, ".env")) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k] = v.strip().strip('"').strip("'")
    return env


def _q(base, key, path):
    r = urllib.request.Request(f"{base}/rest/v1/{path}",
                               headers={"apikey": key,
                                        "Authorization": f"Bearer {key}"})
    return json.load(urllib.request.urlopen(r, timeout=30))


def run_chart(base, key, chart_id, gt, explain=False, position_fn=None):
    from antar_engine.event_convergence import converge_events
    rec = _q(base, key, f"charts?select=*&id=eq.{chart_id}")
    if not rec:
        return None, f"chart {chart_id[:8]} not found"
    rec = rec[0]
    chart = rec.get("chart_data")
    if isinstance(chart, str):
        chart = json.loads(chart)
    rows = _q(base, key,
              f"dasha_periods?select=planet_or_sign,start_date,end_date,"
              f"level,type,metadata&chart_id=eq.{chart_id}"
              f"&system=eq.vimsottari&order=start_date&limit=3000")
    birth = str(rec.get("birth_date"))[:10]
    today = datetime.now().strftime("%Y-%m-%d")
    res = converge_events(chart, rec, rows, birth, today,
                          include_debug=False, explain=explain,
                          position_fn=position_fn)
    return res, None


def print_explain(label, res, events):
    """For each ground-truth event: every candidate within ±30 months of
    the true date, with its lock breakdown — the WHY behind hit/miss."""
    tables = res.get("explain") or {}
    print(f"\n════ EXPLAIN {label} ════")
    for et, d, tol in events:
        try:
            dd = datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            continue
        cands = tables.get(et)
        if cands is None:
            print(f"\n  {et} (true {d}): NO CANDIDATE TABLE "
                  f"(skipped: {res.get('skipped', {}).get(et)})")
            continue
        near = []
        for c in cands:
            try:
                ws = datetime.strptime(c["window"][0], "%Y-%m-%d")
                we = datetime.strptime(c["window"][1], "%Y-%m-%d")
            except ValueError:
                continue
            mid = ws + (we - ws) / 2
            dist = abs((mid - dd).days)
            if dist <= 915:
                near.append((dist, c))
        near.sort(key=lambda x: x[0])
        print(f"\n  {et} — true {d} "
              f"({len(cands)} candidates total, {len(near)} within ±30mo):")
        if not near:
            print("    << no candidate near the true date — Stage-2 never "
                  "flagged this period; check significator set >>")
        for dist, c in near[:8]:
            mark = "*" if (c["window"][0] <= d <= c["window"][1]) else " "
            print(f"   {mark} {c['window'][0]}→{c['window'][1]} "
                  f"({c['granularity']}) locks={c['locks']} "
                  f"[J={'Y' if c['jaimini'] else 'n'} "
                  f"T={'Y' if c['transit'] else 'n'}] "
                  f"chain={'/'.join(str(x) for x in c['chain'])} "
                  f"af={c['age_factor']} rank={c['rank']} "
                  f"(mid {dist}d from truth)")


def score(label, res, events):
    surfaced = [p for p in res["predictions"]]
    truth_by_type = {}
    for et, d, tol in events:
        truth_by_type.setdefault(et, []).append((d, tol))

    hits, wrongs, unknowns = [], [], []
    painful_wrong = []
    for p in surfaced:
        et = p["event_type"]
        if et not in truth_by_type:
            unknowns.append(p)
            continue
        ok = False
        for d, tol in truth_by_type[et]:
            try:
                dd = datetime.strptime(d, "%Y-%m-%d")
                ws = datetime.strptime(p["window_start"], "%Y-%m-%d") \
                    - timedelta(days=tol)
                we = datetime.strptime(p["window_end"], "%Y-%m-%d") \
                    + timedelta(days=tol)
                if ws <= dd <= we:
                    ok = True
                    break
            except ValueError:
                continue
        (hits if ok else wrongs).append(p)
        if not ok and et in PAINFUL:
            painful_wrong.append(p)

    scorable = len(hits) + len(wrongs)
    precision = (len(hits) / scorable * 100) if scorable else 0.0
    print(f"\n──── {label} ────  chronology={res['meta'].get('chronology')}")
    for p in surfaced:
        et = p["event_type"]
        tag = ("HIT " if p in hits else "MISS" if p in wrongs else "unkn")
        print(f"  [{tag}] {et:28s} {p['window_start']}→{p['window_end']} "
              f"locks={p['confidence']}")
    for et, v in res.get("skipped", {}).items():
        if et in truth_by_type:
            print(f"  [silent on real event] {et}: {v}")
    print(f"  precision: {len(hits)}/{scorable} = {precision:.0f}% "
          f"(unknown held aside: {len(unknowns)}) "
          f"painful-wrong: {len(painful_wrong)}")
    return {"scorable": scorable, "hits": len(hits),
            "painful_wrong": len(painful_wrong)}


def main():
    env = _env()
    base = env["SUPABASE_URL"].rstrip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY") or env["SUPABASE_KEY"]
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    explain = "--explain" in sys.argv

    # Sandbox support: REAL chronology dumped by scripts/dump_real_chronology.py
    # turns into a position_fn so calibration can run without swisseph.
    position_fn = None
    chrono_path = os.path.join(ROOT, "Antar.world",
                               "real_chronology_1960_2036.json")
    try:
        import swisseph as _swe  # noqa: F401
        _swe.calc_ut  # probe
    except Exception:
        # transit_engine imports swisseph at module top — inject a minimal
        # stub (real julday, calc_ut raises) so the module loads and the
        # dumped REAL chronology drives positions via position_fn.
        import types as _types
        _stub = _types.ModuleType("swisseph")
        for _n, _v in dict(SUN=0, MOON=1, MARS=4, MERCURY=2, JUPITER=5,
                           VENUS=3, SATURN=6, MEAN_NODE=10,
                           FLG_SIDEREAL=65536, FLG_SPEED=256,
                           SIDM_LAHIRI=1).items():
            setattr(_stub, _n, _v)
        _stub.set_sid_mode = lambda *a, **k: None

        def _stub_julday(y, m, d, h=0.0):
            a = (14 - m) // 12
            yy = y + 4800 - a
            mm = m + 12 * a - 3
            jdn = (d + (153 * mm + 2) // 5 + 365 * yy + yy // 4
                   - yy // 100 + yy // 400 - 32045)
            return jdn + (h - 12) / 24.0
        _stub.julday = _stub_julday
        _stub.calc_ut = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("no ephemeris — use dumped chronology"))
        sys.modules.setdefault("swisseph", _stub)
        if os.path.exists(chrono_path):
            with open(chrono_path) as f:
                _chrono = json.load(f)

            def position_fn(jd, planet, _c=_chrono):
                # step-function longitude from real sign segments
                from datetime import date, timedelta as _td
                d = (date(2000, 1, 1)
                     + _td(days=jd - 2451545.0)).isoformat()
                for seg in _c.get(planet, []):
                    if seg["start"] <= d <= seg["end"]:
                        return seg["sign_index"] * 30.0 + 15.0
                return 0.0
            print(f"[harness] swisseph unavailable — using dumped REAL "
                  f"chronology {os.path.basename(chrono_path)}")

    tot = {"scorable": 0, "hits": 0, "painful_wrong": 0}
    for cid, gt in GROUND_TRUTH.items():
        if only and cid not in only and gt["label"].lower() not in \
                [o.lower() for o in only]:
            continue
        if not gt["events"]:
            print(f"\n──── {gt['label']} ──── SKIPPED (ground truth pending)")
            continue
        res, err = run_chart(base, key, cid, gt, explain=explain,
                             position_fn=position_fn)
        if err:
            print(err)
            continue
        s = score(gt["label"], res, gt["events"])
        if explain:
            print_explain(gt["label"], res, gt["events"])
        for k in tot:
            tot[k] += s[k]

    if tot["scorable"]:
        pct = tot["hits"] / tot["scorable"] * 100
        print(f"\n════ OVERALL: {tot['hits']}/{tot['scorable']} = {pct:.0f}% "
              f"precision | painful-wrong: {tot['painful_wrong']} ════")
        print(f"GATE (>=60% precision, 0 painful-wrong): "
              f"{'PASS' if pct >= 60 and tot['painful_wrong'] == 0 else 'FAIL'}")
    else:
        print("\nno scorable predictions")


if __name__ == "__main__":
    main()
