#!/usr/bin/env python3
"""
tests/validation/build_fixtures.py
Assemble a validation cohort from REAL charts.                        2026-09-05

You provide a small LABELS file (chart_id + the known outcome). This pulls the
exact engine inputs (chart_data + dashas) from the live system via
GET /api/v1/debug/engine-inputs/{chart_id} and writes a fixtures.json the
validator can score. No reshaping — the fixture scores what the live engine sees.

LABELS FILE (JSON list) — you fill this:
  [
    {"chart_id": "<uuid>", "id": "gates",  "type": "career",
     "true_fields": ["technology", "business"]},
    {"chart_id": "<uuid>", "id": "personX","type": "concern",
     "concern": "funding", "polarity_kind": "gain", "outcome_positive": true}
  ]
  - id        : a human label for the report (defaults to chart_id[:8]).
  - type      : "career" or "concern".
  - true_fields (career): what they ACTUALLY do, in the engine's vocabulary.
  - concern / polarity_kind / outcome_positive (concern): see README.

HOW TO GET chart_ids for known-outcome people (no contamination — never a chart
you eyeballed while building the significator tables):
  - PUBLIC FIGURES with a reliable birth time (Rodden AA/A): create the chart
    through onboarding, note its chart_id. Career/outcomes are on the record.
  - Consenting contacts whose outcome you know.

USAGE
  python3 tests/validation/build_fixtures.py labels.json \
      --base https://antar-fastapi-production.up.railway.app \
      --out fixtures.cohort.json
  then:
  python3 tests/validation/run_significator_validation.py fixtures.cohort.json --out results_<date>.md
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

DEFAULT_BASE = "https://antar-fastapi-production.up.railway.app"


def _fetch(base: str, chart_id: str) -> dict:
    url = f"{base.rstrip('/')}/api/v1/debug/engine-inputs/{chart_id}"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print("usage: build_fixtures.py labels.json [--base URL] [--out fixtures.cohort.json]")
        return 2
    labels = json.loads(Path(args[0]).read_text())
    base = DEFAULT_BASE
    out = Path(__file__).parent / "fixtures.cohort.json"
    if "--base" in argv:
        base = argv[argv.index("--base") + 1]
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])

    cases, skipped = [], []
    for lab in labels:
        cid = lab.get("chart_id")
        rid = lab.get("id") or (cid or "?")[:8]
        if not cid:
            skipped.append(f"{rid}: no chart_id"); continue
        try:
            data = _fetch(base, cid)
        except Exception as e:
            skipped.append(f"{rid}: fetch failed ({e})"); continue
        if data.get("error"):
            skipped.append(f"{rid}: {data['error']}"); continue
        # sanity: warn if the engine will return unavailable
        if lab.get("type") == "career" and not (data.get("has_d10") and data.get("has_planets")):
            print(f"  WARN {rid}: chart_data missing planets/d10 — career engine will be UNAVAILABLE")
        case = {
            "id": rid,
            "type": lab.get("type"),
            "chart_data": data.get("chart_data") or {},
        }
        if lab.get("type") == "career":
            case["true_fields"] = lab.get("true_fields") or []
        elif lab.get("type") == "concern":
            case["concern"] = lab.get("concern")
            case["polarity_kind"] = lab.get("polarity_kind", "gain")
            case["outcome_positive"] = bool(lab.get("outcome_positive"))
            case["dashas"] = data.get("dashas") or {}
        cases.append(case)
        print(f"  ok   {rid}: {lab.get('type')} "
              f"(planets={data.get('has_planets')} d10={data.get('has_d10')} d9={data.get('has_d9')})")

    out.write_text(json.dumps(cases, indent=2, default=str))
    print(f"\n[build] wrote {len(cases)} cases → {out}")
    if skipped:
        print("[build] skipped:")
        for s in skipped:
            print(f"   - {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
