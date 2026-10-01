"""
Validation matrix for the Domain-Fit engine (antar_engine/domain_fit.py).

Runs {charts} x {domain phrasings} and ASSERTS coherence + the known-truth
regression set, instead of eyeballing one question at a time. Re-runnable:
    python -m antar_engine.testing.domain_fit_matrix
Needs SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in env (reads real charts).

The engine is a GUARDRAIL (shape / approach-fit / timing / speculation-caution),
never a vertical-success oracle — the assertions encode exactly that.
"""
import os
import json
import urllib.request

from antar_engine.domain_fit import assess_domain_fit
from antar_engine.concern_engines import _vim_active_lords

_URL = os.environ.get("SUPABASE_URL")
_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

CHARTS = {
    "Andres": "6ec6311c-d46e-4e97-a46c-859882071971",   # Libra, Guru-Chandala now, Saturn-4th
    "Raman":  "a4c9d57b-fb9c-4890-8fe7-4a9904f515ed",   # Capricorn, Rahu-11th MD, Ketu-5th
    "Shashi": "9dff84f7-6171-4372-bdb6-1f266696816d",   # Libra, 2nd-lord-12th leak, Rahu-5th
}

GRID = [
    ("property+raise", "Should I raise capital or find an investor to close my real estate deal?", "funding"),
    ("property+hold",  "Should I buy and hold a property long term?", "wealth"),
    ("tech",           "Should I build and raise funding for my tech platform?", "funding"),
    ("speculation",    "Should I put money into crypto day trading?", "speculation"),
    ("hospitality",    "Should I open a restaurant business?", "business"),
    ("partnership",    "Should I take on a co-founder partner?", "business"),
]


def _q(path):
    req = urllib.request.Request(_URL + "/rest/v1/" + path,
                                 headers={"apikey": _KEY, "Authorization": "Bearer " + _KEY})
    return json.load(urllib.request.urlopen(req))


def _load():
    data = {}
    for name, cid in CHARTS.items():
        cd = _q(f"charts?id=eq.{cid}&select=chart_data")[0]["chart_data"]
        cd = cd if isinstance(cd, dict) else json.loads(cd)
        dp = _q(f"dasha_periods?chart_id=eq.{cid}&system=eq.vimsottari"
                "&select=level,planet_or_sign,start_date,end_date&order=start_date&limit=5000")
        run = {str(x).title() for x in _vim_active_lords({"vimsottari": dp})}
        data[name] = (cd, run)
    return data


def run():
    data = _load()
    results = {}
    print("=== DOMAIN-FIT MATRIX ===")
    for name, (cd, run) in data.items():
        print(f"\n{name} (running: {sorted(run)})")
        results[name] = {}
        for label, qst, conc in GRID:
            r = assess_domain_fit(cd, None, qst, conc, running_lords=run)
            results[name][label] = r
            print(f"  {label:16} {r['domain'] or '-':11} "
                  f"align={r['alignment']:18} period={r['period_fit']:9} "
                  f"shape={r['shape'][:34]}")

    # ---- assertions (coherence + known truths) ----
    checks = []

    def ck(name, cond):
        checks.append((name, bool(cond)))

    # GUARDRAIL coherence — hold for EVERY chart:
    for n in CHARTS:
        R = results[n]
        ck(f"[{n}] speculation is never green-lit (caution)",
           R["speculation"]["alignment"] == "caution")
        ck(f"[{n}] raising/flipping a property is misaligned_approach",
           R["property+raise"]["alignment"] == "misaligned_approach")
        ck(f"[{n}] buy-and-hold property is NOT misaligned_approach",
           R["property+hold"]["alignment"] != "misaligned_approach")
        ck(f"[{n}] no domain is ever labelled a success-y 'aligned'",
           all(R[g[0]]["alignment"] != "aligned" for g in GRID))

    # KNOWN-TRUTH regression:
    A = results["Andres"]
    ck("[Andres] real-estate raise flagged + Guru-Chandala season caution",
       A["property+raise"]["alignment"] == "misaligned_approach"
       and A["property+raise"]["period_fit"] == "caution")
    ck("[Andres] tech is supported (his Mercury-10th lane)",
       A["tech"]["alignment"] == "supported")
    R = results["Raman"]
    ck("[Raman] tech supported + favorable season",
       R["tech"]["alignment"] == "supported" and R["tech"]["period_fit"] == "favorable")
    ck("[Raman] speculation caution (Ketu-5th leak)",
       R["speculation"]["alignment"] == "caution")

    print("\n=== ASSERTIONS ===")
    passed = 0
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
        passed += ok
    print(f"\n{passed}/{len(checks)} passed")
    return passed == len(checks)


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
