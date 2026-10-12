"""Relationship bands - validation runner. Spec (locked before any data): Antar.world/RELATIONSHIP_BAND_VALIDATION.md

    venv311/bin/python antar_research/validate_relationship_bands.py                 # our own charts (DB); aggregates only
    venv311/bin/python antar_research/validate_relationship_bands.py --csv export.csv   # an Astro-Databank style export

CSV columns:  id, birth_date (YYYY-MM-DD), birth_time (HH:MM), lat, lng, tz_hours, rodden (AA|A|B|C|X|...),
              outcome (married|divorced|separated), marriage_dates (opt, ';'-separated ISO), divorce_dates (opt)
Only AGGREGATES are written (no ids, names or dates of birth). Nothing here changes the product: it reports whether the rules beat chance.
"""
import argparse, csv, datetime, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from antar_engine import validation_stats as vs  # noqa: E402

EVER = ("married", "divorced", "separated")
BROKE = ("divorced", "separated")
ALPHA = 0.05


# ── pure: features + the locked tests ────────────────────────────────────────────
def features(chart: dict) -> dict:
    """Band and components straight from the production engine."""
    from antar_engine.relationship_foundation import analyze_foundation
    a = analyze_foundation(chart)
    if not a.get("available"):
        return {}
    return {"band": a["foundation"]["band"], "score": a["foundation"]["score"],
            "sus_fragile": a["sustenance"]["level"] == "fragile",
            "dk_bad": a["spouse_indicator"]["state"] in ("detached", "burdened"),
            "d9_weak": a["d9"]["level"] == "weak"}


def _table(recs, pred):
    a = sum(1 for r in recs if pred(r) and r["broke"]); b = sum(1 for r in recs if pred(r) and not r["broke"])
    c = sum(1 for r in recs if not pred(r) and r["broke"]); d = sum(1 for r in recs if not pred(r) and not r["broke"])
    return a, b, c, d


def test_exposure(recs, pred, alpha=ALPHA, seed=3):
    a, b, c, d = _table(recs, pred)
    if a + b == 0 or c + d == 0 or a + c == 0 or b + d == 0:
        return {"table": (a, b, c, d), "p": None, "or": None, "ci": None}
    f = vs.fisher_exact(a, b, c, d)
    lo, mid, hi = vs.odds_ratio_ci(a, b, c, d)
    # placebo: the same share exposed, assigned at random - must NOT look significant
    rng = random.Random(seed); n_exp = a + b; idx = list(range(len(recs))); ps = []
    for _ in range(200):
        pick = set(rng.sample(idx, n_exp))
        pa = sum(1 for i in pick if recs[i]["broke"]); pb = n_exp - pa
        pc = sum(1 for i in idx if i not in pick and recs[i]["broke"]); pd = len(recs) - n_exp - pc
        ps.append(vs.fisher_exact(pa, pb, pc, pd)["p_greater"])
    return {"table": (a, b, c, d), "p": f["p_greater"], "or": mid, "ci": (lo, hi),
            "placebo_false_positive_rate": sum(p < alpha for p in ps) / len(ps)}


def evaluate(recs, aa_a_only=False):
    """The locked analysis on a list of {band, score, sus_fragile, dk_bad, d9_weak, rodden, broke}. Returns a dict incl. the verdict."""
    cohort = [r for r in recs if (not aa_a_only) or str(r.get("rodden", "")).upper() in ("AA", "A")]
    n = len(cohort)
    broke = sum(1 for r in cohort if r["broke"])
    out = {"n": n, "broke": broke, "scope": "AA/A only" if aa_a_only else "all"}
    if n < 6 or broke == 0 or broke == n:
        out.update({"verdict": "NOT TESTABLE", "reason": "too few people or no variation in the outcome"})
        return out
    base = max(0.02, min(0.98, (sum(1 for r in cohort if r["broke"] and r["band"] != "fragile") or 0.5) /
                         max(1, sum(1 for r in cohort if r["band"] != "fragile"))))
    share = sum(1 for r in cohort if r["band"] == "fragile") / n
    out["h1"] = test_exposure(cohort, lambda r: r["band"] == "fragile")
    out["h2"] = {k: test_exposure(cohort, lambda r, k=k: bool(r[k])) for k in ("sus_fragile", "dk_bad", "d9_weak")}
    out["h3"] = vs.permutation_p([-r["score"] for r in cohort], [1 if r["broke"] else 0 for r in cohort], n_perm=3000)  # lower score = worse
    share = min(max(share, 0.05), 0.95)
    out["power"] = {"share_fragile": round(share, 2), "base_rate": round(base, 2),
                    "min_detectable_or": vs.min_detectable_or(n, share, base),
                    "n_for_or3": vs.required_n(share, base, 3.0), "n_for_or2": vs.required_n(share, base, 2.0)}
    mdor = out["power"]["min_detectable_or"]
    h1p = out["h1"]["p"]
    if mdor > 4:
        out["verdict"] = "NOT TESTABLE"
        out["reason"] = f"underpowered: only an odds ratio of {mdor if mdor != float('inf') else '50+'} or more could be detected at 80% power"
    elif h1p is not None and h1p < ALPHA and out["h3"]["p"] < ALPHA and out["h1"]["placebo_false_positive_rate"] <= 0.12:
        out["verdict"] = "PASSES"; out["reason"] = "H1 and H3 beat the bar and the placebo stays null"
    else:
        out["verdict"] = "FAILS"; out["reason"] = "adequately powered, and the band does not beat chance"
    return out


# ── cohort builders ──────────────────────────────────────────────────────────────
def from_db():
    import main
    rows = main.supabase.table("charts").select("id,marital_status,birth_date,birth_time,chart_data,deleted_at").limit(2000).execute().data
    seen, recs = set(), []
    import json
    for r in rows:
        ms = (r.get("marital_status") or "").lower()
        key = (r.get("birth_date"), r.get("birth_time"))
        if ms not in EVER or r.get("deleted_at") or key in seen:
            continue
        seen.add(key)
        cd = r["chart_data"] if isinstance(r["chart_data"], dict) else (json.loads(r["chart_data"]) if r["chart_data"] else {})
        f = features(cd)
        if f:
            recs.append({**f, "broke": ms in BROKE, "rodden": ""})        # our users carry no birth-time grading
    return recs


def _build(birth_date, birth_time, lat, lng, tz):
    from antar_engine.antar_ephemeris import build_chart, divisional_chart, julian_day
    from antar_engine.vimsottari import calculate_vimsottari_from_chart
    cd = build_chart(birth_date, birth_time, float(lat), float(lng), float(tz))
    lag = cd["lagna"]["sign_index"]
    for _p, _v in cd["planets"].items():
        _v["house"] = ((_v["sign_index"] - lag) % 12) + 1
    d9 = divisional_chart(cd, 9)
    cd.setdefault("divisional_charts", {})["d9"] = {"planets": {p: {"sign": d9[p]["sign"]} for p in d9 if p != "Lagna"}, "lagna": d9["Lagna"]["sign"]}
    d = datetime.datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    vim = calculate_vimsottari_from_chart(cd, julian_day(d.year, d.month, d.day, d.hour + d.minute / 60.0 - float(tz)))
    rows = [{"level": "mahadasha", "lord": m["lord"], "start_date": m["start_date"], "end_date": m["end_date"]} for m in vim.get("mahadashas", [])]
    rows += [{"level": "antardasha", "lord": a["lord"], "start_date": a["start_date"], "end_date": a["end_date"]} for a in vim.get("antardashas", [])]
    return cd, rows


def from_csv(path):
    recs = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("outcome") or "").lower() not in EVER:
                continue
            cd, rows = _build(row["birth_date"], row["birth_time"], row["lat"], row["lng"], row["tz_hours"])
            f = features(cd)
            if not f:
                continue
            ev = lambda k: [x for x in (row.get(k) or "").split(";") if x.strip()]
            recs.append({**f, "broke": row["outcome"].lower() in BROKE, "rodden": row.get("rodden", ""), "chart": cd, "dasha_rows": rows,
                         "marriages": ev("marriage_dates"), "divorces": ev("divorce_dates"), "birth": row["birth_date"]})
    return recs


# ── H4: the season at an event date vs the same person's random adult dates ──────────
def _running_on(rows, on):
    iso, out = on.isoformat(), {}
    for r in rows:
        if str(r["start_date"])[:10] <= iso <= str(r["end_date"])[:10]:
            out["md" if r["level"] == "mahadasha" else "ad"] = r["lord"]
    return out


def season_at(rec, on):
    from antar_engine.relationship_timing import classify_season
    cd = rec["chart"]; run = _running_on(rec["dasha_rows"], on)
    if not run.get("md"):
        return None
    return classify_season(cd["planets"], cd["lagna"]["sign"], run)["season"]


def h4(recs, n_random=20, seed=5, perms=5000):
    rng = random.Random(seed)
    res = {}
    for label, key, want in (("divorce -> ending/friction", "divorces", ("ending", "friction")), ("marriage -> opening", "marriages", ("opening",))):
        diffs = []
        for r in recs:
            ev = [datetime.date.fromisoformat(x[:10]) for x in r.get(key, [])]
            if not ev:
                continue
            born = datetime.date.fromisoformat(r["birth"][:10]); lo = born + datetime.timedelta(days=365 * 20)
            hi = min(datetime.date.today(), born + datetime.timedelta(days=365 * 70))
            if hi <= lo:
                continue
            at_ev = [season_at(r, e) for e in ev]; at_ev = [s for s in at_ev if s]
            rand = [season_at(r, lo + datetime.timedelta(days=rng.randint(0, (hi - lo).days))) for _ in range(n_random)]; rand = [s for s in rand if s]
            if at_ev and rand:
                diffs.append(sum(s in want for s in at_ev) / len(at_ev) - sum(s in want for s in rand) / len(rand))
        if len(diffs) < 5:
            res[label] = {"n": len(diffs), "p": None, "mean_diff": None}
            continue
        obs = sum(diffs) / len(diffs); hit = 0
        for _ in range(perms):
            if sum(d * rng.choice((-1, 1)) for d in diffs) / len(diffs) >= obs - 1e-12:
                hit += 1
        res[label] = {"n": len(diffs), "mean_diff": round(obs, 3), "p": (hit + 1) / (perms + 1)}
    return res


# ── report ───────────────────────────────────────────────────────────────────────
def _fmt_or(x):
    return "50+" if x == float("inf") else str(x)


def report(results, source):
    L = [f"# Relationship band validation - {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')}Z", "",
         f"Source: {source}. Spec: `Antar.world/RELATIONSHIP_BAND_VALIDATION.md` (locked before analysis). Aggregates only.", ""]
    for scope, r in results:
        L += [f"## {scope}: n={r['n']} ever-married, {r['broke']} divorced/separated", "", f"**Verdict: {r['verdict']}** - {r.get('reason', '')}", ""]
        if "h1" in r:
            a, b, c, d = r["h1"]["table"]
            L += ["| | divorced/separated | still married |", "|---|---|---|", f"| fragile band | {a} | {b} |", f"| not fragile | {c} | {d} |", ""]
            if r["h1"]["p"] is not None:
                lo, hi = r["h1"]["ci"]
                L.append(f"- H1 one-sided Fisher p = {r['h1']['p']:.3f}; odds ratio {r['h1']['or']:.2f} (95% CI {lo:.2f} - {hi:.1f}); placebo false-positive rate {r['h1']['placebo_false_positive_rate']:.2f}")
            for k, v in r["h2"].items():
                if v["p"] is not None:
                    L.append(f"- H2 {k}: p = {v['p']:.3f} (bar {ALPHA / 3:.3f}), OR {v['or']:.2f}")
            L.append(f"- H3 score AUC = {r['h3']['auc']:.2f}, permutation p = {r['h3']['p']:.3f}")
            pw = r["power"]
            L += [f"- Power: fragile share {pw['share_fragile']}, base rate {pw['base_rate']}: smallest odds ratio detectable at 80% power = **{_fmt_or(pw['min_detectable_or'])}**; "
                  f"people needed for OR 3 = {pw['n_for_or3']}, for OR 2 = {pw['n_for_or2']}", ""]
    return "\n".join(L)


def main_cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    a = ap.parse_args()
    recs = from_csv(a.csv) if a.csv else from_db()
    results = [("All charts", evaluate(recs))]
    if any(str(r.get("rodden", "")).upper() in ("AA", "A") for r in recs):
        results.append(("Rodden AA/A only", evaluate(recs, aa_a_only=True)))
    md = report(results, a.csv or "Antar users (stored charts)")
    if a.csv and any(r.get("divorces") or r.get("marriages") for r in recs):
        md += "\n\n## H4 (season at the event date vs the same person's random adult dates)\n\n" + "\n".join(
            f"- {k}: n={v['n']}, mean difference {v['mean_diff']}, permutation p = {v['p']}" for k, v in h4(recs).items())
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Antar.world", "answer_audit")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"validation_{datetime.datetime.utcnow().strftime('%Y-%m-%dT%H%M')}.md")
    open(path, "w").write(md)
    print(md); print(f"-> {path}")


if __name__ == "__main__":
    main_cli()
