"""
tests/capital_wiring_casecontrol.py

Case-control harness for antar_engine.capital_wiring. RULES BELOW ARE FIXED
BEFORE ANY COHORT IS SCORED: do not add, remove or edit a rule after a cohort
file has been passed in. (Same discipline as success_rules_prespecified.py;
eleven wealth/fame hypotheses have already died in this repo.)

Two modes:

  python tests/capital_wiring_casecontrol.py --baseline [N]
      How often does each rule fire in N RANDOM charts? A wire that fires in
      most random charts cannot separate anyone. No cohort needed.

  python tests/capital_wiring_casecontrol.py --cohort manifest.json
      manifest = {"A": ["chart1.json", ...], "B": [...],
                  "A_label": "raised", "B_label": "controls"}
      Group A is the hypothesised-positive group (e.g. founders who raised).
      Chart files are engine-format chart_data, or the flat b_*_v3.json format.
      Exact permutation test when feasible, otherwise 200,000 samples at
      seed 20260723. Bonferroni over every rule.

Direction: +1 means the rule is predicted HIGHER in group A, -1 means LOWER
(drain-type rules). One-sided p, direction as specified.
"""
import json
import math
import os
import random
import sys
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from antar_engine.capital_wiring import SIGNS, analyze_capital_wiring  # noqa: E402


def _w(r, a, b):
    return any(w["houses"] in ((a, b), (b, a)) for w in r["wires"])


def _w_strict(r, a, b):
    return any(w["houses"] in ((a, b), (b, a)) and w["strict"] for w in r["wires"])


# (name, direction, fn(result)->number). FIXED.
RULES = [
    ("W1 independent golden links, strict",  +1, lambda r: r["independent_count_strict"]),
    ("W2 independent golden links, inclusive", +1, lambda r: r["independent_count"]),
    ("W3 8th-11th linked, inclusive",        +1, lambda r: int(_w(r, 8, 11))),
    ("W4 8th-11th linked, strict",           +1, lambda r: int(any(
        w["houses"] == (8, 11) and w["kinds"] and any(
            k in ("conjunction", "exchange", "mutual_aspect") for k in w["kinds"])
        for w in r["wires"]))),
    ("W5 hard drain present",                -1, lambda r: int(r["has_hard_drain"])),
    ("W6 drain flags (hard+caution) count",  -1, lambda r: len(r["drains"])),
    ("W7 blowup-audit flags count",          -1, lambda r: len(r["audit"])),
    ("W8 custodian archetype",               -1, lambda r: int("custodian" in r["archetypes"])),
]


def _flat_to_engine(d):
    """b_*_v3.json flat format -> engine chart_data."""
    planets = {}
    for k in ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"):
        if isinstance(d.get(k), dict):
            planets[k.title()] = dict(d[k])
    return {"planets": planets, "lagna": {"sign": d.get("lagna_sign")}}


def load_chart(path):
    d = json.load(open(path))
    return d if "planets" in d else _flat_to_engine(d)


def random_chart(rng):
    li = rng.randrange(12)
    sun = rng.uniform(0, 360)
    lon = {"Sun": sun,
           "Mercury": (sun + rng.uniform(-28, 28)) % 360,
           "Venus": (sun + rng.uniform(-48, 48)) % 360,
           "Moon": rng.uniform(0, 360), "Mars": rng.uniform(0, 360),
           "Jupiter": rng.uniform(0, 360), "Saturn": rng.uniform(0, 360)}
    rahu = rng.uniform(0, 360)
    lon["Rahu"], lon["Ketu"] = rahu, (rahu + 180) % 360
    return {"lagna": {"sign": SIGNS[li], "sign_index": li},
            "planets": {p: {"longitude": l, "sign_index": int(l // 30) % 12}
                        for p, l in lon.items()}}


def score(chart):
    r = analyze_capital_wiring(chart)
    return None if not r.get("available") else {n: f(r) for n, _, f in RULES}


def perm_p(a, b, direction, rng, max_exact=200_000, samples=200_000):
    vals = a + b
    na = len(a)
    obs = (sum(a) / na) - (sum(b) / len(b))
    obs *= direction
    total = math.comb(len(vals), na)
    ge = n = 0
    if total <= max_exact:
        idx = range(len(vals))
        for comb in combinations(idx, na):
            s = set(comb)
            ma = sum(vals[i] for i in comb) / na
            mb = sum(vals[i] for i in idx if i not in s) / (len(vals) - na)
            ge += ((ma - mb) * direction) >= obs - 1e-12
            n += 1
    else:
        for _ in range(samples):
            rng.shuffle(vals)
            ma = sum(vals[:na]) / na
            mb = sum(vals[na:]) / (len(vals) - na)
            ge += ((ma - mb) * direction) >= obs - 1e-12
            n += 1
    return ge / n, obs * direction


def run_baseline(n):
    rng = random.Random(20260723)
    rows = [s for s in (score(random_chart(rng)) for _ in range(n)) if s]
    print(f"{len(rows)} random charts (uniform lagna, free planet signs,"
          " Mercury/Venus kept near the Sun)\n")
    print(f"{'rule':44s} {'mean':>7s} {'fires>0':>9s}")
    for name, _, _ in RULES:
        v = [r[name] for r in rows]
        print(f"{name:44s} {sum(v)/len(v):7.2f} {100*sum(x > 0 for x in v)/len(v):8.1f}%")
    print("\nA rule that fires in most random charts cannot discriminate between people.")


def run_cohort(manifest_path):
    m = json.load(open(manifest_path))
    base = os.path.dirname(os.path.abspath(manifest_path))
    groups = {}
    for g in ("A", "B"):
        rows = []
        for f in m[g]:
            s = score(load_chart(f if os.path.isabs(f) else os.path.join(base, f)))
            if s is None:
                print(f"SKIPPED (unusable chart): {f}")
            else:
                rows.append(s)
        groups[g] = rows
    na, nb = len(groups["A"]), len(groups["B"])
    if na < 2 or nb < 2:
        sys.exit("need at least 2 usable charts per group")
    thr = 0.05 / len(RULES)
    la, lb = m.get("A_label", "A"), m.get("B_label", "B")
    print(f"{la}: {na}   {lb}: {nb}   Bonferroni threshold: p < {thr:.4f}\n")
    print(f"{'rule':44s} {'dir':>3s} {la[:8]:>8s} {lb[:8]:>8s} {'gap':>7s} {'p':>8s}")
    rng = random.Random(20260723)
    for name, d, _ in RULES:
        a = [r[name] for r in groups["A"]]
        b = [r[name] for r in groups["B"]]
        p, gap = perm_p(a, b, d, rng)
        flag = "  <-- passes" if p < thr else ""
        print(f"{name:44s} {d:+3d} {sum(a)/na:8.2f} {sum(b)/nb:8.2f} {gap:+7.2f} {p:8.4f}{flag}")
    print("\nEvery rule is reported, including failures. No rule may be edited after this run.")


if __name__ == "__main__":
    if "--baseline" in sys.argv:
        i = sys.argv.index("--baseline")
        n = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 and sys.argv[i + 1].isdigit() else 5000
        run_baseline(n)
    elif "--cohort" in sys.argv:
        run_cohort(sys.argv[sys.argv.index("--cohort") + 1])
    else:
        print(__doc__)
