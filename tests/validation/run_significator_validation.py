#!/usr/bin/env python3
"""
tests/validation/run_significator_validation.py
Significator VALIDATION harness — d10_career + concern_engines.       2026-09-05

WHY THIS EXISTS
  d10_career (career-field ranking) and concern_engines (funding/relationship/
  separation/health verdicts) are LIVE and deterministic, but their significator
  SETS are v1 — classical defaults never validated against real dated outcomes.
  This harness scores them against a labelled cohort so "untuned" can become
  "measured", the same way tests/hora_rules_prespecified.py did for D-2 wealth.

DISCIPLINE (read tests/significator_rules_prespecified.md FIRST)
  Pre-register the rule + the chance baseline BEFORE looking at charts. The
  charts that GENERATED a significator table cannot also test it. A result that
  only beats chance after you tweaked the mapping to fit the cohort is not a
  result — it is memorisation. Commit the fixtures + the expected direction, then
  run. This repo already has 20+ dead hypotheses; the defence is a timestamp.

WHAT IT SCORES
  career  — is the person's REAL field in the engine's top-1 / top-3? Aggregated
            hit@1 / hit@3 vs a chance baseline (K / #distinct-fields), exact
            one-tailed binomial p.
  concern — does the engine's verdict POLARITY (favorable vs risk/unfavorable)
            match whether the good thing actually happened? vs p=0.5.

FIXTURES
  A JSON list of cases. Each case carries a pre-computed `chart_data` (+ `dashas`
  for concern cases) and the labelled truth. See fixtures.example.json for the
  schema. Populate `chart_data` by dumping it from the live system for people
  whose outcomes are a matter of record (do NOT hand-fabricate charts).

USAGE
  python3 tests/validation/run_significator_validation.py [fixtures.json] [--out report.md]
  (pure-Python; needs no anthropic/supabase/network.)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# Repo root on path so this runs from anywhere (tests/validation/ → repo root).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Pure-Python engines — safe to import without the server deps.
from antar_engine.d10_career import analyze_career, PLANET_CAREERS
from antar_engine.concern_engines import analyze_concern


# ── scoring helpers ────────────────────────────────────────────────────────
def _distinct_fields() -> int:
    """Size of the career-field pool the engine ranks from (chance denominator)."""
    fields = set()
    for careers in PLANET_CAREERS.values():
        for f in (careers or []):
            fields.add(str(f).strip().lower())
    return max(1, len(fields))


def _field_match(true_fields, engine_fields) -> bool:
    """Loose match: any labelled true field overlaps any engine field (either
    direction, case-insensitive). Keep the fixture's true_fields in the engine's
    vocabulary where possible; this fuzz only covers wording, not meaning."""
    for t in (true_fields or []):
        tl = str(t).strip().lower()
        if not tl:
            continue
        for e in (engine_fields or []):
            el = str(e).strip().lower()
            if tl and el and (tl in el or el in tl):
                return True
    return False


def _binom_tail_ge(k: int, n: int, p: float) -> float:
    """Exact one-tailed P(X >= k) for X ~ Binomial(n, p). No scipy."""
    if n <= 0:
        return 1.0
    k = max(0, k)
    return sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))


# The engine verdict describes the SUBJECT's level. For a GAIN concern the
# subject is the good thing ("well supported" = good thing likely). For a RISK
# concern the subject is the BAD thing ("elevated — worth active care" = bad
# thing likely). So we first classify HIGH (subject indicated/elevated) vs LOW
# (not indicated / minor / steady) from the actual verdict vocabulary, THEN map
# to a good-outcome prediction by concern kind. LOW markers are checked first
# because "not strongly indicated" contains "indicated".
_LOW_MARKERS = ("not indicated", "not strongly", "not pressing", "minor theme",
                "a minor", "steady")
_HIGH_MARKERS = ("well supported", "supported", "elevated", "worth watching",
                 "worth active care", "strongly indicated", "likely", "favorable")


def _subject_level(verdict: str) -> str:
    v = (verdict or "").strip().lower()
    if not v:
        return "unknown"
    if any(m in v for m in _LOW_MARKERS):
        return "low"
    if any(m in v for m in _HIGH_MARKERS):
        return "high"
    return "unknown"


def _verdict_polarity(verdict: str, polarity_kind: str) -> str:
    """Predict whether the GOOD outcome happened ('positive'/'negative'/'unknown').
    polarity_kind: 'gain' — subject IS the good thing (high→positive);
    'risk' — subject is the BAD thing (high→negative)."""
    level = _subject_level(verdict)
    if level == "unknown":
        return "unknown"
    if (polarity_kind or "gain") == "risk":
        return "negative" if level == "high" else "positive"
    return "positive" if level == "high" else "negative"


# ── runners ────────────────────────────────────────────────────────────────
def run(fixtures: list) -> dict:
    n_fields = _distinct_fields()
    career = {"n": 0, "unavailable": 0, "hit1": 0, "hit3": 0, "detail": []}
    concern = {"n": 0, "unavailable": 0, "correct": 0, "detail": []}

    for case in fixtures:
        ctype = (case.get("type") or "").lower()
        cid = case.get("id", "?")
        chart_data = case.get("chart_data") or {}

        if ctype == "career":
            res = analyze_career(chart_data)
            if not res.get("available"):
                career["unavailable"] += 1
                career["detail"].append(f"{cid}: UNAVAILABLE (engine had no usable D-1/D-10)")
                continue
            ranked = [c.get("field") for c in (res.get("careers") or [])]
            true_fields = case.get("true_fields") or []
            h1 = _field_match(true_fields, ranked[:1])
            h3 = _field_match(true_fields, ranked[:3])
            career["n"] += 1
            career["hit1"] += int(h1)
            career["hit3"] += int(h3)
            career["detail"].append(
                f"{cid}: true={true_fields} top3={ranked[:3]} hit@1={h1} hit@3={h3}")

        elif ctype == "concern":
            res = analyze_concern(case.get("concern", ""), chart_data,
                                  case.get("dashas") or {}, case.get("intent", "state"))
            if not res.get("available"):
                concern["unavailable"] += 1
                concern["detail"].append(f"{cid}: UNAVAILABLE")
                continue
            kind = case.get("polarity_kind", "gain")  # 'gain' or 'risk'
            pred = _verdict_polarity(res.get("verdict", ""), kind)
            truth = "positive" if case.get("outcome_positive") else "negative"
            ok = (pred == truth)
            concern["n"] += 1
            concern["correct"] += int(ok)
            concern["detail"].append(
                f"{cid}: concern={case.get('concern')} verdict={res.get('verdict')!r} "
                f"pred={pred} truth={truth} correct={ok}")
        else:
            career["detail"].append(f"{cid}: SKIPPED (unknown type {ctype!r})")

    # aggregate stats
    out = {"n_fields": n_fields, "career": career, "concern": concern}
    if career["n"]:
        base1 = min(0.99, 1.0 / n_fields)
        base3 = min(0.99, 3.0 / n_fields)
        out["career_stats"] = {
            "hit1_rate": career["hit1"] / career["n"],
            "hit3_rate": career["hit3"] / career["n"],
            "baseline1": base1, "baseline3": base3,
            "p_hit1": _binom_tail_ge(career["hit1"], career["n"], base1),
            "p_hit3": _binom_tail_ge(career["hit3"], career["n"], base3),
        }
    if concern["n"]:
        out["concern_stats"] = {
            "accuracy": concern["correct"] / concern["n"],
            "baseline": 0.5,
            "p": _binom_tail_ge(concern["correct"], concern["n"], 0.5),
        }
    return out


def _fmt(out: dict) -> str:
    L = ["# Significator validation — results", ""]
    c = out["career"]
    L.append(f"## Career (field pool = {out['n_fields']} distinct fields)")
    L.append(f"scored={c['n']}  unavailable={c['unavailable']}")
    if out.get("career_stats"):
        s = out["career_stats"]
        L.append(f"hit@1 = {c['hit1']}/{c['n']} = {s['hit1_rate']:.2f} "
                 f"(chance {s['baseline1']:.2f}, one-tailed p = {s['p_hit1']:.4f})")
        L.append(f"hit@3 = {c['hit3']}/{c['n']} = {s['hit3_rate']:.2f} "
                 f"(chance {s['baseline3']:.2f}, one-tailed p = {s['p_hit3']:.4f})")
        L.append(f"VERDICT: {'BEATS chance (p<0.05)' if s['p_hit3'] < 0.05 else 'NOT distinguishable from chance'} at hit@3")
    L += ["", *[f"  {d}" for d in c["detail"]], ""]

    cc = out["concern"]
    L.append("## Concern verdicts")
    L.append(f"scored={cc['n']}  unavailable={cc['unavailable']}")
    if out.get("concern_stats"):
        s = out["concern_stats"]
        L.append(f"accuracy = {cc['correct']}/{cc['n']} = {s['accuracy']:.2f} "
                 f"(chance 0.50, one-tailed p = {s['p']:.4f})")
        L.append(f"VERDICT: {'BEATS chance (p<0.05)' if s['p'] < 0.05 else 'NOT distinguishable from chance'}")
    L += ["", *[f"  {d}" for d in cc["detail"]], ""]
    return "\n".join(L)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    fixtures_path = Path(args[0]) if args else Path(__file__).parent / "fixtures.example.json"
    out_path = None
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 < len(argv):
            out_path = Path(argv[i + 1])

    fixtures = json.loads(Path(fixtures_path).read_text())
    if not isinstance(fixtures, list):
        fixtures = fixtures.get("cases", [])
    print(f"[validation] loaded {len(fixtures)} cases from {fixtures_path}")
    report = _fmt(run(fixtures))
    print("\n" + report)
    if out_path:
        out_path.write_text(report)
        print(f"\n[validation] wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
