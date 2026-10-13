"""
Score the rules engines against dated life events of notable people (B.V. Raman, "Notable Horoscopes",
extracted to DATA_notable_horoscopes_part{1,2}_*.json).

PRE-REGISTERED DESIGN (fixed before any result was looked at):
  People   : birth date + birth time + printed planetary positions + lagna sign present, and the book does NOT
             call the time rectified, speculative or uncertain. Strict sensitivity set: only "book states time is
             reliable". Positions are the book's own (its ayanamsa), not recomputed.
  Events   : career_start / career_rise / fame -> career; marriage -> marriage; money_gain -> money;
             education -> education; children -> children; exile_or_downfall -> caution. travel_abroad, other: not tested.
             Only events inside the person's age 18-70 window. Date precision sets the event interval
             (day / calendar month / calendar year).
  Hit      : some dasha sub-period overlapping the event interval satisfies the test.
  Baseline : for each event, the chance that a random interval of the SAME width placed uniformly inside the
             age 18-70 window overlaps a firing sub-period (weekly grid, exact). Expected hits = sum of those
             chances; p-value is the exact one-sided Poisson-binomial tail; lift = observed / expected.
  Tests    : Chara (AD sign rules, product thresholds: 2 rules, marriage 3), Mandook (only people passing Rao's
             kendra gate), Parashari/Vimshottari (AD grade 'strong'; the D-10 parts and transits are off because the
             book prints no lagna degree). Per family and per individual rule id. Benjamini-Hochberg across all
             tests is reported next to the raw p.
  Not tested: D-10 layer, Jupiter/Saturn double transit, rules needing the lagna degree (MAR.navamsa_lagna_or_its_7th).
Caveats printed with the report: the book's authors fitted dashas to known events (so a high hit rate can reflect
how the examples were chosen), times are sometimes rounded, and a hit rate is only meaningful against the baseline.
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from antar_engine import jaimini_rao_events as jre
from antar_engine import parashari_events as pe
from antar_engine.jaimini_engine import Planet, compute_chara_dasha
from antar_engine.mandook_dasha import compute_mandook_dasha
from antar_engine import constants

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius",
         "Capricorn", "Aquarius", "Pisces"]
EVENT_FAMILY = {"career_start": "career", "career_rise": "career", "fame": "career", "marriage": "marriage",
                "money_gain": "money", "education": "education", "children": "children",
                "exile_or_downfall": "caution"}
PAR_FAMILY = {"career": "career", "marriage": "marriage", "money": "money", "education": "study"}
EXCLUDE_WORDS = ("rectified", "speculative", "uncertain")
STRICT_WORD = "book states time is reliable"
DROPPED_RULES = {"MAR.navamsa_lagna_or_its_7th"}          # needs the lagna degree the book does not print
AGE_LO, AGE_HI = 18, 70


# ---------- data ----------
def parse_pos(txt):
    """'Scorpio 19d54m' -> absolute longitude in degrees."""
    sign, rest = txt.split(None, 1)
    d, m = rest.replace("d", " ").replace("m", " ").split()[:2]
    return SIGNS.index(sign) * 30 + int(d) + int(m) / 60.0


def load_people(paths, strict=False):
    people = []
    for p in paths:
        d = json.load(open(p))
        rows = d if isinstance(d, list) else d.get("people", [])
        people += rows
    out = []
    for r in people:
        rel = (r.get("birth_data_reliable") or "").lower()
        if not (r.get("birth_date") and r.get("birth_time") and r.get("planets_per_book") and r.get("lagna_per_book")):
            continue
        if any(w in rel for w in EXCLUDE_WORDS):
            continue
        if strict and STRICT_WORD not in rel:
            continue
        if r["lagna_per_book"].split()[0] not in SIGNS or int(r["birth_date"][:4]) < 1000:
            continue
        pl = r["planets_per_book"]
        if not all(k in pl for k in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu")):
            continue
        out.append(r)
    return out


def event_interval(ev):
    s = ev["date"]
    try:
        if len(s) == 4:
            return date(int(s), 1, 1), date(int(s), 12, 31)
        if len(s) == 7:
            y, m = int(s[:4]), int(s[5:7])
            nxt = date(y + (m == 12), m % 12 + 1, 1)
            return date(y, m, 1), nxt - timedelta(days=1)
        return date.fromisoformat(s[:10]), date.fromisoformat(s[:10])
    except Exception:
        return None


def build_chart(p):
    lon = {k: parse_pos(v) for k, v in p["planets_per_book"].items() if k != "Ketu"}
    lon["Ketu"] = (lon["Rahu"] + 180) % 360
    planets = {n: Planet(name=n, sign=int(l // 30) % 12, degree=l, degree_in_sign=l % 30) for n, l in lon.items()}
    lagna = SIGNS.index(p["lagna_per_book"].split()[0])
    return lagna, planets, lon


# ---------- stats ----------
def poisson_binomial_tail(ps, k):
    """P(X >= k) for independent Bernoulli(ps)."""
    dist = [1.0]
    for p in ps:
        new = [0.0] * (len(dist) + 1)
        for i, q in enumerate(dist):
            new[i] += q * (1 - p)
            new[i + 1] += q * p
        dist = new
    return float(sum(dist[k:])) if k < len(dist) else 0.0


def bh_adjust(pvals):
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    adj = [0.0] * n
    prev = 1.0
    for rank in range(n, 0, -1):
        i = order[rank - 1]
        prev = min(prev, pvals[i] * n / rank)
        adj[i] = prev
    return adj


def weekly_series(windows, a0, n_weeks):
    """windows: [(start_date, end_date)] -> list[bool] over weekly grid from a0."""
    s = [False] * n_weeks
    for ws, we in windows:
        k0 = max(0, (ws - a0).days // 7)
        k1 = min(n_weeks - 1, (we - a0).days // 7)
        for k in range(k0, k1 + 1):
            s[k] = True
    return s


def hit_and_baseline(series, a0, interval):
    """(hit, p_baseline) for an event interval on a weekly boolean grid, None if outside the grid."""
    n = len(series)
    ka = (interval[0] - a0).days // 7
    kb = (interval[1] - a0).days // 7
    if ka < 0 or kb >= n:
        return None
    width = kb - ka + 1
    hit = any(series[ka:kb + 1])
    pref = [0]
    for v in series:
        pref.append(pref[-1] + (1 if v else 0))
    starts = n - width + 1
    if starts <= 0:
        return None
    p = sum(1 for s in range(starts) if pref[s + width] - pref[s] > 0) / starts
    return hit, p


# ---------- per-person windows ----------
def person_windows(p):
    lagna, planets, lon = build_chart(p)
    birth = datetime.fromisoformat(p["birth_date"] + "T" + p["birth_time"] + ":00")
    c = jre.Chart(lagna, lagna * 30 + 15.0, planets)
    rules = {s: jre.rules_for_sign(c, s) for s in range(12)}
    for s in rules.values():
        for fam in s:
            s[fam] = [r for r in s[fam] if r not in DROPPED_RULES]
    chara = []
    for md in compute_chara_dasha(lagna, planets, birth, num_cycles=2):
        for ad in md.sub_periods:
            chara.append((ad.start_date.date(), ad.end_date.date(), rules[ad.sign]))
    signs = {n: pl.sign for n, pl in planets.items()}
    mand = None
    mp = compute_mandook_dasha(lagna, signs, birth, num_cycles=3)
    if mp is not None:
        mand = []
        for per in mp:
            for sub in per.subs:
                r = {k: list(v) for k, v in rules[sub.sign].items()}
                if per.sign == (lagna + 6) % 12:
                    r["marriage"].append("MAR.mdk_major_is_7th_from_lagna")
                mand.append((sub.start.date(), sub.end.date(), r))
    # Parashari: book Moon longitude -> Vimshottari
    seq, yrs = constants.VIMSOTTARI_SEQUENCE, constants.VIMSOTTARI_YEARS
    nk = int(lon["Moon"] // (360 / 27))
    frac = (lon["Moon"] % (360 / 27)) / (360 / 27)
    lords = constants.NAKSHATRA_LORDS
    start_i = seq.index(lords[nk])
    first_len = yrs[seq[start_i]] * (1 - frac)
    cur = birth - timedelta(days=(yrs[seq[start_i]] - first_len) * 365.25)
    rows = []
    for i in range(18):
        lord = seq[(start_i + i) % 9]
        end = cur + timedelta(days=yrs[lord] * 365.25)
        rows.append({"planet": lord, "level": "mahadasha", "start_date": cur, "end_date": end})
        t = cur
        for j in range(9):
            al = seq[(seq.index(lord) + j) % 9]
            ad_end = t + timedelta(days=yrs[lord] * yrs[al] / 120 * 365.25)
            rows.append({"planet": al, "level": "antardasha", "start_date": t, "end_date": ad_end})
            t = ad_end
        cur = end
    return birth, chara, mand, rows, lagna, planets


def parashari_fire(p, lagna, planets, rows, a0, a1):
    orig_d10, orig_dt = pe.d10_chart, pe._double_transit
    pe.d10_chart = lambda lon, pl: {"lagna": 0, "house_sign": lambda h: -1, "lord": lambda h: None, "occ": {}, "pos": {}}
    pe._double_transit = lambda *a, **k: None
    try:
        ws = pe.parashari_windows(lagna, lagna * 30 + 15.0, planets, rows,
                                  datetime(a0.year, a0.month, a0.day), datetime(a1.year, a1.month, a1.day))
    finally:
        pe.d10_chart, pe._double_transit = orig_d10, orig_dt
    out = {}
    for w in ws:
        for e in w["events"]:
            if e["grade"] == "strong":
                out.setdefault(e["event"], []).append((w["start"].date(), w["end"].date()))
    return out


# ---------- main scoring ----------
def score(paths, strict=False):
    people = load_people(paths, strict)
    tests = {}          # key -> {"hits": int, "ps": [], "n_events": int}
    dropped = 0
    per_event = []
    for p in people:
        birth, chara, mand, rows, lagna, planets = person_windows(p)
        a0 = (birth + timedelta(days=AGE_LO * 365.25)).date()
        a1 = (birth + timedelta(days=AGE_HI * 365.25)).date()
        n_weeks = (a1 - a0).days // 7 + 1
        events = []
        for ev in p.get("events", []):
            fam = EVENT_FAMILY.get(ev["event"])
            iv = event_interval(ev)
            if not fam or iv is None:
                continue
            if iv[0] < a0 or iv[1] > a1:
                dropped += 1
                continue
            events.append((fam, iv, ev))
        if not events:
            continue
        par = parashari_fire(p, lagna, planets, rows, a0, a1)
        need = lambda fam: 3 if fam == "marriage" else 2
        for fam, iv, ev in events:
            def record(key, wins):
                ser = weekly_series(wins, a0, n_weeks)
                r = hit_and_baseline(ser, a0, iv)
                if r is None:
                    return
                t = tests.setdefault(key, {"hits": 0, "ps": []})
                t["hits"] += 1 if r[0] else 0
                t["ps"].append(r[1])
            fams = ["marriage", "career", "money", "education", "children", "caution"]
            # Chara and Mandook: family test and each rule id of this family
            for sysname, wins_all in (("chara", chara), ("mandook", mand)):
                if wins_all is None:
                    continue
                record((sysname, fam, "FAMILY"), [(s, e) for s, e, r in wins_all if len(r[fam]) >= need(fam)])
                ids = sorted({x for s, e, r in wins_all for x in r[fam]})
                for rid in ids:
                    record((sysname, fam, rid), [(s, e) for s, e, r in wins_all if rid in r[fam]])
            pf = PAR_FAMILY.get(fam)
            if pf:
                record(("parashari", fam, "STRONG_GRADE"), par.get(pf, []))
            per_event.append({"person": p["name"], "family": fam, "interval": [str(iv[0]), str(iv[1])]})
    rows_out = []
    for (sysn, fam, rid), t in tests.items():
        n = len(t["ps"])
        exp = sum(t["ps"])
        pval = poisson_binomial_tail(t["ps"], t["hits"])
        rows_out.append({"system": sysn, "family": fam, "rule": rid, "n_events": n, "hits": t["hits"],
                         "expected": round(exp, 2), "lift": round(t["hits"] / exp, 2) if exp > 0 else None,
                         "p": pval})
    adj = bh_adjust([r["p"] for r in rows_out]) if rows_out else []
    for r, a in zip(rows_out, adj):
        r["p_bh"] = a
    return {"n_people": len(people), "dropped_outside_age_window": dropped, "n_events": len(per_event),
            "results": sorted(rows_out, key=lambda r: (r["system"], r["family"], r["rule"] != "FAMILY", r["p"]))}


def write_report(res_main, res_strict, path):
    def table(rows, min_n=5, only_family=False):
        lines = ["| system | event family | rule | events | hits | expected by chance | lift | p | p (BH) |",
                 "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            if r["n_events"] < min_n:
                continue
            if only_family and r["rule"] not in ("FAMILY", "STRONG_GRADE"):
                continue
            lines.append(f"| {r['system']} | {r['family']} | {r['rule']} | {r['n_events']} | {r['hits']} | "
                         f"{r['expected']} | {r['lift']} | {r['p']:.3f} | {r['p_bh']:.3f} |")
        return "\n".join(lines)

    out = ["# Scoring against Notable Horoscopes — run " + date.today().isoformat(), "",
           "Design is pre-registered in `scripts/score_notable_charts.py` (docstring). Read the caveats before the numbers.", "",
           "## Caveats",
           "- The book's author fitted dashas to known events, and chose which charts to publish. A hit rate against a "
           "random baseline tests how well the rules *fit known lives*, not how well they predict.",
           "- Birth times printed to the minute; some are 'about'. Rectified, speculative and uncertain times are excluded.",
           "- Positions are the book's own (its ayanamsa). No lagna degree, so the D-10 layer and the double transit are not tested.",
           "- Many tests are run (every rule id). Use the BH-adjusted p, and read small-n rows as exploratory.", "",
           f"## Main set: {res_main['n_people']} people, {res_main['n_events']} scored events "
           f"({res_main['dropped_outside_age_window']} events outside ages {AGE_LO}-{AGE_HI} dropped)", "",
           "### Family-level results", table(res_main["results"], min_n=1, only_family=True), "",
           "### Individual rules (events >= 8)", table([r for r in res_main["results"] if r["rule"] not in ("FAMILY", "STRONG_GRADE")], min_n=8), "",
           f"## Strict set (time stated reliable): {res_strict['n_people']} people, {res_strict['n_events']} scored events", "",
           table(res_strict["results"], min_n=1, only_family=True), ""]
    open(path, "w").write("\n".join(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.expanduser("~/antarai/Antar.world"))
    ap.add_argument("--out", default=os.path.expanduser("~/antarai/Antar.world/SCORING_notable_charts_2026-10-13.md"))
    a = ap.parse_args()
    paths = [os.path.join(a.data_dir, f"DATA_notable_horoscopes_part{i}_2026-10-13.json") for i in (1, 2)]
    main = score(paths, strict=False)
    strict = score(paths, strict=True)
    write_report(main, strict, a.out)
    json.dump({"main": main, "strict": strict}, open(a.out.replace(".md", ".json"), "w"), indent=1, default=str)
    print("people:", main["n_people"], "events:", main["n_events"], "strict people:", strict["n_people"])
