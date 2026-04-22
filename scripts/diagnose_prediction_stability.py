#!/usr/bin/env python3
"""
diagnose_prediction_stability.py
================================
Diagnostic — how stable are monthly / annual LLM predictions for the same chart?

Runs each endpoint N times (default 3) with force_refresh=true, diffs the
outputs field-by-field, and reports a stability score per field.

Interpretation
--------------
  High stability (identical/near-identical across runs)
      → the prompt is deterministic relative to chart data.  The LLM is
        reading the chart context and producing the same conclusions.
        If the output is also VAGUE, the fix is prompt engineering (ask
        for more specificity).  If it's PRECISE, you're already in good
        shape.

  Low stability (same field differs significantly across runs)
      → the LLM is filling gaps with plausible-sounding horoscope prose
        rather than reading the chart.  The fix is context packaging —
        enrich the prompt with more structured chart data (stelliums,
        exchange yogas, transit hits, dasha transitions) so Claude has
        real raw material to work with, not a blank slate.

Output
------
A markdown table + per-field sample trio.  Save the report to a file to
compare baselines across commits.

Usage
-----
    cd ~/antarai && source venv311/bin/activate
    python scripts/diagnose_prediction_stability.py \\
        --chart-id de02bb52-d43a-4b09-be25-b45a07bfbf8a \\
        --runs 3 \\
        --out prediction_stability_report.md

    # Or dump straight to stdout:
    python scripts/diagnose_prediction_stability.py \\
        --chart-id de02bb52-d43a-4b09-be25-b45a07bfbf8a
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
import time
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    print("✖ httpx not installed.  pip install httpx --break-system-packages", file=sys.stderr)
    sys.exit(2)


BASE_URL_DEFAULT = "https://antar-fastapi-production.up.railway.app"

# Per-endpoint config: route + field map {field_path: expectation}
#   'stable'   — chart-deterministic; should come back identical across runs.
#                Low stability here = LLM hallucinating.
#   'prose'    — narrative; natural-language variation expected but the
#                CLAIMS inside should be consistent.  Reported with a fuzzy
#                similarity score, not exact-match.
#   'list'     — list of strings; compare set semantics.
#   'enum'     — pick from fixed set; should be deterministic.

MONTHLY = {
    "route": "/api/v1/monthly-deepdive/{chart_id}",
    "fields": {
        "month_theme":        "prose",
        "energy_level":       "enum",
        "strong_planets":     "list",
        "weak_planets":       "list",
        "overview":           "prose",
        "best_week":          "stable",
        "caution_week":       "stable",
        "monthly_mantra":     "prose",
    },
    "action_field": ("priority_actions", "action"),   # list-of-dict, pluck .action
    "remedy_field": ("remedies",          "practice"),
}

ANNUAL = {
    "route": "/api/v1/annual-plan/{chart_id}",
    "fields": {
        "year_theme":         "prose",
        "year_quality":       "enum",
        "year_summary":       "prose",
        "year_mantra":        "prose",
    },
    "peak_windows_domains": ("career", "wealth", "relationships", "health", "foreign", "spiritual"),
    "list_fields": ("build_this_year", "protect_this_year", "release_this_year"),
    "crit_dates_field": "critical_dates",
    "remedy_field": ("yearly_remedies", "practice"),
}


def _call(client: httpx.Client, url: str) -> dict | None:
    r = client.get(url, params={"refresh": "true"}, timeout=60.0)
    if r.status_code != 200:
        print(f"   ✖ HTTP {r.status_code} — {r.text[:200]}", file=sys.stderr)
        return None
    try:
        return r.json()
    except Exception as e:
        print(f"   ✖ non-JSON response: {e}", file=sys.stderr)
        return None


def _sim(a: str, b: str) -> float:
    """SequenceMatcher ratio on token sequences — 0.0 to 1.0."""
    if not a or not b:
        return 0.0 if a != b else 1.0
    return difflib.SequenceMatcher(None, a.split(), b.split()).ratio()


def _stability_of_prose(samples: list[str]) -> tuple[float, str]:
    """Average pairwise similarity; classify."""
    if len(samples) < 2:
        return (1.0, "single-run")
    ratios = []
    for i in range(len(samples)):
        for j in range(i + 1, len(samples)):
            ratios.append(_sim(samples[i], samples[j]))
    avg = sum(ratios) / len(ratios)
    if avg >= 0.85:
        label = "STABLE"
    elif avg >= 0.55:
        label = "SEMI-STABLE"
    else:
        label = "NOISY"
    return (avg, label)


def _stability_of_exact(samples: list[Any]) -> tuple[float, str]:
    """Exact-match stability — fraction of run-pairs that agree."""
    if len(samples) < 2:
        return (1.0, "single-run")
    agrees = 0
    total = 0
    for i in range(len(samples)):
        for j in range(i + 1, len(samples)):
            agrees += 1 if samples[i] == samples[j] else 0
            total += 1
    frac = agrees / total if total else 1.0
    if frac == 1.0:
        label = "IDENTICAL"
    elif frac >= 0.5:
        label = "PARTIAL"
    else:
        label = "DRIFT"
    return (frac, label)


def _stability_of_list(samples: list[list[Any]]) -> tuple[float, str]:
    """Jaccard similarity on set representation."""
    if len(samples) < 2:
        return (1.0, "single-run")
    ratios = []
    for i in range(len(samples)):
        for j in range(i + 1, len(samples)):
            a, b = set(samples[i] or []), set(samples[j] or [])
            if not a and not b:
                ratios.append(1.0); continue
            if not a or not b:
                ratios.append(0.0); continue
            ratios.append(len(a & b) / len(a | b))
    avg = sum(ratios) / len(ratios)
    label = "IDENTICAL" if avg == 1.0 else ("OVERLAP" if avg >= 0.5 else "DISJOINT")
    return (avg, label)


def run_endpoint(base: str, route: str, chart_id: str, n: int) -> list[dict]:
    url = base.rstrip("/") + route.replace("{chart_id}", chart_id)
    runs = []
    with httpx.Client() as client:
        for i in range(n):
            print(f"   run {i+1}/{n}: {url}")
            d = _call(client, url)
            if d:
                runs.append(d)
            time.sleep(1.5)   # give Claude/Supabase a moment between calls
    return runs


def analyze_monthly(runs: list[dict]) -> list[str]:
    out = ["", "## Monthly Deepdive — field stability", "",
           "| field | type | stability | verdict |",
           "|---|---|---|---|"]
    for field, kind in MONTHLY["fields"].items():
        samples = [r.get(field, "") for r in runs]
        if kind == "prose":
            ratio, label = _stability_of_prose([str(s or "") for s in samples])
        elif kind == "enum":
            ratio, label = _stability_of_exact(samples)
        elif kind == "list":
            ratio, label = _stability_of_list(samples)
        elif kind == "stable":
            ratio, label = _stability_of_prose([str(s or "") for s in samples])
        out.append(f"| {field} | {kind} | {ratio:.2f} | {label} |")

    # priority_actions[].action — treat each domain's action independently
    action_samples_by_domain: dict[str, list[str]] = {}
    for r in runs:
        for pa in (r.get("priority_actions") or []):
            d = pa.get("domain", "?")
            action_samples_by_domain.setdefault(d, []).append(pa.get("action", ""))
    for domain, samples in action_samples_by_domain.items():
        ratio, label = _stability_of_prose(samples)
        out.append(f"| priority_actions[{domain}].action | prose | {ratio:.2f} | {label} |")

    # remedies[].practice — same treatment keyed by planet
    remedy_samples_by_planet: dict[str, list[str]] = {}
    for r in runs:
        for rm in (r.get("remedies") or []):
            p = rm.get("planet", "?")
            remedy_samples_by_planet.setdefault(p, []).append(rm.get("practice", ""))
    for planet, samples in remedy_samples_by_planet.items():
        ratio, label = _stability_of_prose(samples)
        out.append(f"| remedies[{planet}].practice | prose | {ratio:.2f} | {label} |")

    # Sample trio for eyeballing
    out.append("")
    out.append("### Sample trios (first 160 chars each run)")
    for field in ("month_theme", "overview", "best_week", "monthly_mantra"):
        out.append(f"\n**{field}:**")
        for i, r in enumerate(runs):
            v = str(r.get(field) or "")[:160]
            out.append(f"  - run{i+1}: {v}")
    return out


def analyze_annual(runs: list[dict]) -> list[str]:
    out = ["", "## Annual Plan — field stability", "",
           "| field | type | stability | verdict |",
           "|---|---|---|---|"]
    for field, kind in ANNUAL["fields"].items():
        samples = [r.get(field, "") for r in runs]
        if kind == "prose":
            ratio, label = _stability_of_prose([str(s or "") for s in samples])
        elif kind == "enum":
            ratio, label = _stability_of_exact(samples)
        out.append(f"| {field} | {kind} | {ratio:.2f} | {label} |")

    # peak_windows.<domain>.months — should be deterministic from dasha/transit data
    for domain in ANNUAL["peak_windows_domains"]:
        months_samples = [((r.get("peak_windows") or {}).get(domain) or {}).get("months", "")
                          for r in runs]
        signal_samples = [((r.get("peak_windows") or {}).get(domain) or {}).get("signal", "")
                          for r in runs]
        mr, ml = _stability_of_exact(months_samples)
        sr, sl = _stability_of_prose([str(s or "") for s in signal_samples])
        out.append(f"| peak_windows.{domain}.months | exact | {mr:.2f} | {ml} |")
        out.append(f"| peak_windows.{domain}.signal | prose | {sr:.2f} | {sl} |")

    # build/protect/release arrays — treat as list stability (Jaccard)
    for lf in ANNUAL["list_fields"]:
        samples = [r.get(lf) or [] for r in runs]
        lr, ll = _stability_of_list(samples)
        out.append(f"| {lf}[] | list | {lr:.2f} | {ll} |")

    # critical_dates[].date — should be deterministic from chart data
    dates_samples = []
    for r in runs:
        dates_samples.append(sorted([c.get("date", "") for c in (r.get("critical_dates") or [])]))
    dr, dl = _stability_of_list(dates_samples)
    out.append(f"| critical_dates[].date | list-exact | {dr:.2f} | {dl} |")

    # remedies[].practice — keyed by planet
    remedy_samples_by_planet: dict[str, list[str]] = {}
    for r in runs:
        for rm in (r.get("yearly_remedies") or []):
            p = rm.get("planet", "?")
            remedy_samples_by_planet.setdefault(p, []).append(rm.get("practice", ""))
    for planet, samples in remedy_samples_by_planet.items():
        ratio, label = _stability_of_prose(samples)
        out.append(f"| yearly_remedies[{planet}].practice | prose | {ratio:.2f} | {label} |")

    # Sample trios
    out.append("")
    out.append("### Sample trios (first 160 chars each run)")
    for field in ("year_theme", "year_summary", "year_mantra"):
        out.append(f"\n**{field}:**")
        for i, r in enumerate(runs):
            v = str(r.get(field) or "")[:160]
            out.append(f"  - run{i+1}: {v}")

    # Peak window month ranges per domain — super diagnostic
    out.append("\n**peak_windows months across runs (drift here = hallucination):**")
    for domain in ANNUAL["peak_windows_domains"]:
        months = [((r.get("peak_windows") or {}).get(domain) or {}).get("months", "?") for r in runs]
        out.append(f"  - {domain}: {months}")
    return out


def interpret(lines: list[str]) -> list[str]:
    """Parse the stability lines back out and add an interpretation block."""
    out = ["", "## Interpretation", ""]
    noisy = sum(1 for ln in lines if "NOISY" in ln or "DRIFT" in ln or "DISJOINT" in ln)
    stable = sum(1 for ln in lines if "STABLE" in ln or "IDENTICAL" in ln)
    total_rows = sum(1 for ln in lines if ln.startswith("| ") and not ln.startswith("| field"))
    if total_rows == 0:
        out.append("No fields scored (probably an error fetching data).")
        return out
    noise_pct = noisy / total_rows * 100 if total_rows else 0
    stable_pct = stable / total_rows * 100 if total_rows else 0
    out.append(f"- Total scored fields: **{total_rows}**")
    out.append(f"- STABLE / IDENTICAL: **{stable}** ({stable_pct:.0f}%)")
    out.append(f"- NOISY / DRIFT / DISJOINT: **{noisy}** ({noise_pct:.0f}%)")
    out.append("")
    if noise_pct > 40:
        out.append("**Diagnosis: LLM is filling gaps with horoscope prose.** "
                   "Different runs produce materially different claims from the same "
                   "chart input.  Next sprint should focus on **context packaging** — "
                   "enrich `_build_deepdive_context` / `_build_annual_context` to pull "
                   "richer chart data (stelliums, exchange yogas, transit-to-natal hits, "
                   "Nishekha placements, Jaimini karakas) so the prompt has more raw "
                   "material to reason from.")
    elif stable_pct > 75:
        out.append("**Diagnosis: prompt is stable across runs.** "
                   "The LLM is reading the chart consistently.  If the output is still "
                   "vague or formulaic, the next sprint is **prompt engineering** — "
                   "ask for more specificity, tighter word counts, chart-cross-referenced "
                   "claims.  If output is already precise, ship as-is.")
    else:
        out.append("**Diagnosis: mixed signal.** "
                   "Some fields are deterministic, others drift.  Look at which "
                   "specific fields are noisy — often peak_windows or priority_actions — "
                   "and decide field-by-field.  Typically the prose fields drift while "
                   "the structural fields (enums, lists) stay stable; that's expected.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chart-id", default="de02bb52-d43a-4b09-be25-b45a07bfbf8a",
                    help="Test chart ID (default: Raman Capricorn Rising)")
    ap.add_argument("--runs", type=int, default=3, help="Runs per endpoint")
    ap.add_argument("--base-url", default=BASE_URL_DEFAULT)
    ap.add_argument("--out", default=None, help="Write report to this file; default stdout")
    ap.add_argument("--endpoints", default="monthly,annual",
                    help="Comma-list of which to run: monthly,annual")
    args = ap.parse_args()

    endpoints = {x.strip() for x in args.endpoints.split(",")}
    report: list[str] = [
        f"# Prediction stability diagnostic",
        f"",
        f"- chart: `{args.chart_id}`",
        f"- runs per endpoint: {args.runs}",
        f"- base URL: {args.base_url}",
        f"- endpoints: {sorted(endpoints)}",
    ]

    monthly_runs: list[dict] = []
    annual_runs:  list[dict] = []

    if "monthly" in endpoints:
        print("\n▶ Monthly Deepdive")
        monthly_runs = run_endpoint(args.base_url, MONTHLY["route"], args.chart_id, args.runs)
        if monthly_runs:
            report.extend(analyze_monthly(monthly_runs))

    if "annual" in endpoints:
        print("\n▶ Annual Plan")
        annual_runs = run_endpoint(args.base_url, ANNUAL["route"], args.chart_id, args.runs)
        if annual_runs:
            report.extend(analyze_annual(annual_runs))

    report.extend(interpret(report))

    rendered = "\n".join(report) + "\n"
    if args.out:
        Path(args.out).write_text(rendered)
        print(f"\n✓ wrote {args.out}")
    else:
        print()
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
