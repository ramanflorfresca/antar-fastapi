"""
tests/ak_d10_shadow_run.py — run the frozen AK x D-10 shadow experiment on OGDB.

    python tests/ak_d10_shadow_run.py <path/to/ogdb-all.csv> [out.md]

Needs pyswisseph (pinned in requirements.txt). Cohort: OGDB rows WITH a birth
time and a UT timestamp. The design is frozen in
antar_engine/profession/ak_d10_shadow.py (see prereg_hash in the output).
Reports EVERY test, including failures. No test is added or re-thresholded
after the data is seen.
"""
import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import swisseph as swe  # noqa: E402

from antar_engine.profession import ak_d10_shadow as S  # noqa: E402

_BODIES = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
           "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
           "Venus": swe.VENUS, "Saturn": swe.SATURN}


def sidereal_longitudes(ut: datetime) -> dict:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = swe.julday(ut.year, ut.month, ut.day, ut.hour + ut.minute / 60.0)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    out = {}
    for name, body in _BODIES.items():
        pos, _ = swe.calc_ut(jd, body, flags)
        out[name] = pos[0] % 360.0
    return out


def load(path):
    rows = []
    for r in csv.DictReader(open(path, encoding="utf-8"), delimiter=";"):
        if len(r["DATE"]) <= 10 or not r["DATE-UT"] or len(r["DATE-UT"]) <= 10:
            continue  # untimed
        try:
            ut = datetime.strptime(r["DATE-UT"], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        gs = S.groups_for_slugs(r["OCCU"])
        rows.append((r["OGID"], ut, gs))
    return rows


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    rows = load(src)
    feats = []
    ak_disagree = 0
    for ogid, ut, gs in rows:
        try:
            lon = sidereal_longitudes(ut)
        except Exception:
            continue
        f = S.ak_d10_features(lon)
        if S.atmakaraka_absolute_longitude(lon) != f["ak"]:
            ak_disagree += 1
        feats.append((f, gs))
    n = len(feats)
    L = []
    L.append("# AK x D-10 shadow experiment — result\n")
    L.append(f"prereg_hash `{S.prereg_hash()}` · cohort n={n} timed OGDB rows "
             f"· primary Bonferroni p < {S.BONFERRONI:.5f} (one-sided, higher)\n")
    L.append(f"AK distribution: {dict(Counter(f['ak'] for f, _ in feats))}\n")
    L.append(f"**karakas.py diagnostic:** sorting by absolute longitude picks a "
             f"different AK than highest-in-sign-degree in {ak_disagree}/{n} "
             f"charts ({100*ak_disagree/max(n,1):.1f}%).\n")
    L.append("| test | group | feature=Y (in G / n) | feature=N (in G / n) "
             "| rate Y | rate N | lift | p (1-sided) | family? | verdict |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    t0_pass = {}
    for g, spec in S.GROUPS.items():
        K = set(spec["karaka"])
        # T0 baseline
        a = sum(1 for f, gs in feats if f["ak"] in K and g in gs)
        b = sum(1 for f, gs in feats if f["ak"] in K and g not in gs)
        c = sum(1 for f, gs in feats if f["ak"] not in K and g in gs)
        d = sum(1 for f, gs in feats if f["ak"] not in K and g not in gs)
        p = S.fisher_one_sided(a, b, c, d)
        r1, r2, lf = S.lift(a, b, c, d)
        t0_pass[g] = p < 0.05
        L.append(f"| T0 | {g} | {a}/{a+b} | {c}/{c+d} | {r1:.3f} | {r2:.3f} | "
                 f"{lf:.2f} | {p:.4f} | context | "
                 f"{'ALIVE' if p < 0.05 else 'dead'} |")
        # T1: within AK in K, AK dignified in D-10
        sub = [(f, gs) for f, gs in feats if f["ak"] in K]
        a = sum(1 for f, gs in sub if f["ak_d10_dignified"] and g in gs)
        b = sum(1 for f, gs in sub if f["ak_d10_dignified"] and g not in gs)
        c = sum(1 for f, gs in sub if not f["ak_d10_dignified"] and g in gs)
        d = sum(1 for f, gs in sub if not f["ak_d10_dignified"] and g not in gs)
        p = S.fisher_one_sided(a, b, c, d)
        r1, r2, lf = S.lift(a, b, c, d)
        L.append(f"| T1 | {g} | {a}/{a+b} | {c}/{c+d} | {r1:.3f} | {r2:.3f} | "
                 f"{lf:.2f} | {p:.4f} | yes | "
                 f"{'SURVIVES' if p < S.BONFERRONI else 'dead'} |")
        # T2: D-10 dispositor of AK in K (whole cohort)
        a = sum(1 for f, gs in feats if f["ak_d10_dispositor"] in K and g in gs)
        b = sum(1 for f, gs in feats if f["ak_d10_dispositor"] in K and g not in gs)
        c = sum(1 for f, gs in feats if f["ak_d10_dispositor"] not in K and g in gs)
        d = sum(1 for f, gs in feats if f["ak_d10_dispositor"] not in K and g not in gs)
        p = S.fisher_one_sided(a, b, c, d)
        r1, r2, lf = S.lift(a, b, c, d)
        L.append(f"| T2 | {g} | {a}/{a+b} | {c}/{c+d} | {r1:.3f} | {r2:.3f} | "
                 f"{lf:.2f} | {p:.4f} | yes | "
                 f"{'SURVIVES' if p < S.BONFERRONI else 'dead'} |")
    L.append("")
    L.append("**Gate:** " + ("T0 alive for: " + ", ".join(g for g, v in t0_pass.items() if v)
                             if any(t0_pass.values()) else
                             "T0 dead for every group — the AK->work table is itself unsupported; "
                             "T1/T2 cannot rescue it."))
    L.append("\nCaveats: eminent-person selection (Gauquelin), French birth times "
             "rounded to the hour pre-1920 (no lagna/D-10-house feature was used for "
             "that reason), groups overlap (military-personnel can also be politician), "
             "occupation = career-defining field, not income or satisfaction.")
    text = "\n".join(L)
    print(text)
    if out:
        Path(out).write_text(text + "\n")


if __name__ == "__main__":
    main()
