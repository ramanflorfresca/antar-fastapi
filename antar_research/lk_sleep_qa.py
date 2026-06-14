"""
antar_research/lk_sleep_qa.py — read-only QA for Phase 2 Rule 1 (sleeping planets).

Runs the dual-sleep + maturity-gate engine on the three audit charts and asserts
the acceptance criteria from the brief. Reads chart_data straight from Supabase
(REST, .env creds). Makes NO writes and touches NO production code path.

Usage:
    source venv311/bin/activate
    python -m antar_research.lk_sleep_qa
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import date

from antar_engine.varshphal_chart import build_varshphal_chart
from antar_engine.lk_rules.sleeping import evaluate_sleeping_planets
from antar_engine.lk_rules.maturity import LK_MATURITY_AGE

CHARTS = {
    "Musk":   "761626dc-2c66-402d-aa3a-9b731df75078",
    "Raman":  "de0c6265-96cc-41ba-a39c-e55868fa5806",
    "Andres": "6ec6311c-d46e-4e97-a46c-859882071971",
}


def _env():
    env = {}
    for line in open(os.path.join(os.path.dirname(__file__), "..", ".env")):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v.strip().strip('"')
    return env


def _fetch_chart(env, cid):
    url = env.get("SUPABASE_URL")
    key = (env.get("SUPABASE_SERVICE_ROLE_KEY")
           or env.get("SUPABASE_KEY") or env.get("SUPABASE_ANON_KEY"))
    req = urllib.request.Request(
        f"{url}/rest/v1/charts?id=eq.{cid}"
        f"&select=chart_data,birth_date,lagna_sign,needs_reconfirm",
        headers={"apikey": key, "Authorization": "Bearer " + key})
    row = json.load(urllib.request.urlopen(req, timeout=25))[0]
    cd = row["chart_data"]
    if isinstance(cd, str):
        cd = json.loads(cd)
    return cd, row["birth_date"], row.get("needs_reconfirm", False)


def main():
    env = _env()
    results = {}
    print("=" * 72)
    print("Phase 2 Rule 1 — sleeping-planet engine QA")
    print("=" * 72)

    for nm, cid in CHARTS.items():
        cd, bd, needs_reconfirm = _fetch_chart(env, cid)
        vc = build_varshphal_chart(cd, bd, on_date=date.today(),
                                   lagna_verified=not bool(needs_reconfirm))
        res = evaluate_sleeping_planets(vc, cd)
        results[nm] = (vc, res)

        print(f"\n### {nm}  (age {vc['age']}, year {vc['year_key']}, "
              f"low_conf={vc['low_confidence']})")
        print(f"    {'planet':8} {'natal':6} {'annual':7} {'aH':3} "
              f"{'mature':7} outcome")
        for p in res["per_planet"]:
            print(f"    {p['planet']:8} "
                  f"{str(p['natal_sleep']):6} {str(p['annual_sleep']):7} "
                  f"{p['annual_house']:<3} {str(p['matured']):7} "
                  f"{p['outcome']}"
                  f"{'  [PROVISIONAL]' if p['provisional'] else ''}")
        firing = [p["planet"] for p in res["firing"]]
        print(f"    FIRING (ranked): {firing or '—'}")

    # ── Acceptance checks ────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("ACCEPTANCE CHECKS")
    print("=" * 72)
    passed = True

    def check(label, cond):
        nonlocal passed
        passed = passed and cond
        print(f"  [{'PASS' if cond else 'FAIL'}] {label}")

    # 1. Maturity boundary on Andres (34): Mercury(34) mature; Sat/Rahu/Ketu suppressed-if-annual-sleep
    a_vc, a_res = results["Andres"]
    a_by = {p["planet"]: p for p in a_res["per_planet"]}
    check("Andres age 34 == Mercury maturity boundary (Mercury matured)",
          a_by.get("Mercury", {}).get("matured") is True)
    for late in ("Saturn", "Rahu", "Ketu"):
        p = a_by.get(late)
        if p is None:
            continue
        # immature late planets must never fire; if annual-sleeping must be SUPPRESSED
        ok = (p["matured"] is False) and (p["remedy_fires"] is False)
        check(f"Andres {late} immature -> remedy_fires False", ok)
    # Musk & Raman: all 9 mature
    for older in ("Musk", "Raman"):
        _, r = results[older]
        all_mat = all(p["matured"] for p in r["per_planet"])
        check(f"{older}: all evaluated planets mature", all_mat)

    # 2. Three-chart divergence of firing sets
    firing_sets = {nm: frozenset(p["planet"] for p in r["firing"])
                   for nm, (_, r) in results.items()}
    distinct = len(set(firing_sets.values())) == len(firing_sets)
    check(f"Three-chart firing sets all distinct {dict(firing_sets)}", distinct)

    # 3. Dual-sleep distinctness: some planet on some chart has natal != annual
    dual_distinct = any(
        p["natal_sleep"] != p["annual_sleep"]
        for _, r in results.values() for p in r["per_planet"])
    check("At least one planet shows natal_sleep != annual_sleep "
          "(annual computed vs Varshphal, not echoing natal)", dual_distinct)

    # 4. Every firing planet carries a non-empty source
    all_sourced = all(
        bool(p.get("source")) for _, r in results.values() for p in r["firing"])
    check("Every firing planet has non-empty source", all_sourced)

    # 5. Synthetic: maturity gate must ACTIVELY suppress an immature planet that
    #    IS annual-sleeping (live charts don't happen to exercise this path).
    #    Force Saturn into annual house 9 (a Saturn sleeping_in house) at age 30
    #    (< Saturn maturity 36) with no benefic support.
    synth_natal = {"planets": {"Saturn": {"house": 9, "sign": "Aries"}}}
    synth_vc = {"age": 30, "low_confidence": False,
                "annual_houses": {"Saturn": 9}}
    synth = evaluate_sleeping_planets(synth_vc, synth_natal)
    sp = next((p for p in synth["per_planet"] if p["planet"] == "Saturn"), {})
    check("Synthetic: Saturn age30 annual-sleeping(H9) -> "
          f"annual_sleep={sp.get('annual_sleep')} matured={sp.get('matured')} "
          f"outcome={sp.get('outcome')} fires={sp.get('remedy_fires')}",
          sp.get("annual_sleep") is True and sp.get("matured") is False
          and sp.get("outcome") == "SUPPRESSED_IMMATURE"
          and sp.get("remedy_fires") is False)

    print("\n" + ("ALL CHECKS PASSED" if passed else "SOME CHECKS FAILED"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
