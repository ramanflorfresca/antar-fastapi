#!/usr/bin/env python3
"""
tools/regression_predict.py
────────────────────────────
Reusable acceptance-matrix runner for /predict.

What it checks (V2.2 acceptance gates):

  G1  DETERMINISM
        5x identical-input runs → identical signal_line AND identical
        action_item. The Python-authored verdict is the same every call.

  G2  TIMEFRAME HONESTY
        A "today" question MUST NOT headline a multi-year deferral.
        signal_line/plain_summary first sentence must not lead with a
        date >= 12 months out.

  G3  NO TEMPLATE LEAK
        Across every response, zero "wait until to" / "wait until when"
        / empty-placeholder ("wait until ___") patterns.

  G4  NO ENERGY-LABEL LEAK
        Across every response, zero internal hyphenated energy labels
        (structure-and-persistence, identity-and-authority, etc.).

  G5  PROPERTY REGRESSION (CASE 2 from the brief)
        "how is buying property for me today" must route to PROPERTY
        (not wealth), and the signal_line must address PROPERTY by name
        with a band-consistent prose body.

  G6  FIELD-TYPE INVARIANTS
        signal_confidence is a string ("high"/"medium"/"low").
        confidence is a float in [0, 1].

USAGE:
    cd ~/antarai && source venv311/bin/activate
    python tools/regression_predict.py
    # or
    python tools/regression_predict.py \
        --chart-id de0c6265-96cc-41ba-a39c-e55868fa5806 \
        --base-url https://antar-fastapi-production.up.railway.app \
        --runs 5

Exit code:
    0 = all gates passed
    1 = at least one gate failed (prints which)
    2 = environment error (could not reach the server)

The script reads no env vars, takes no auth — it hits the public
endpoint with a chart_id you pass. To exercise leak paths on a specific
chart, pass --chart-id.
"""

from __future__ import annotations
import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib import request as _urlreq, error as _urlerr


# ─────────────────────────────────────────────────────────────────────
# Defaults — match the project's documented test chart and base URL.
# ─────────────────────────────────────────────────────────────────────

DEFAULT_CHART_ID = "de0c6265-96cc-41ba-a39c-e55868fa5806"
DEFAULT_BASE_URL = "https://antar-fastapi-production.up.railway.app"
DEFAULT_RUNS = 5
DEFAULT_TIMEOUT = 35.0

PREDICT_PATH = "/api/v1/predict"

# Banned hyphenated energy labels (mirrors antar_engine/banned_labels.py).
BANNED_ENERGY_LABELS = [
    "structure-and-persistence", "discipline-and-structure",
    "identity-and-authority", "command-and-authority",
    "release-and-dissolution", "release-and-letting-go",
    "growth-and-wisdom", "expansion-and-wisdom",
    "action-and-drive", "drive-and-action",
    "love-and-partnership", "harmony-and-comfort", "beauty-and-harmony",
    "communication-and-intellect", "clarity-and-communication",
    "ambition-and-amplification", "desire-and-amplification",
    "emotional-and-nurturing", "emotion-and-intuition",
]

# Dangling template patterns Claude has been known to emit.
DANGLING_PATTERNS = [
    re.compile(r"\bwait until to\b", re.I),
    re.compile(r"\bwait until when\b", re.I),
    re.compile(r"\bwait until\s*[._-]+\b", re.I),
    re.compile(r"\bwait until\s*[.,;]", re.I),
    re.compile(r"\bwait until\s+\[\s*\]", re.I),
]

# Future-year deferral pattern for G2 (today-question multi-year headline).
# Matches any month-name + year >= current_year + 1, OR bare 4-digit year
# >= current_year + 1, in the first sentence.
_MONTHS = (
    "january|february|march|april|may|june|july|august|"
    "september|october|november|december|"
    "enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    "septiembre|octubre|noviembre|diciembre"
)
_BARE_YEAR_RE = re.compile(r"\b(20\d{2})\b")


# ─────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────

@dataclass
class GateResult:
    name: str
    passed: bool
    detail: str = ""
    samples: List[str] = field(default_factory=list)


@dataclass
class PredictResponse:
    raw: Dict[str, Any]

    def field(self, name: str) -> str:
        v = self.raw.get(name)
        return v if isinstance(v, str) else (str(v) if v is not None else "")

    @property
    def signal_line(self) -> str:        return self.field("signal_line")
    @property
    def plain_summary(self) -> str:      return self.field("plain_summary")
    @property
    def action_item(self) -> str:        return self.field("action_item")
    @property
    def timing_window(self) -> str:      return self.field("timing_window")
    @property
    def why_this(self) -> str:           return self.field("why_this")
    @property
    def bridge_practice_note(self) -> str: return self.field("bridge_practice_note")
    @property
    def signal_confidence(self) -> Any:  return self.raw.get("signal_confidence")
    @property
    def confidence(self) -> Any:         return self.raw.get("confidence")

    def all_user_fields_blob(self) -> str:
        return " | ".join([
            self.signal_line, self.plain_summary, self.action_item,
            self.timing_window, self.why_this, self.bridge_practice_note,
        ])


# ─────────────────────────────────────────────────────────────────────
# HTTP
# ─────────────────────────────────────────────────────────────────────

def call_predict(base_url: str, chart_id: str, question: str,
                 language: str = "en",
                 timeout: float = DEFAULT_TIMEOUT) -> PredictResponse:
    url = base_url.rstrip("/") + PREDICT_PATH
    body = json.dumps({
        "chart_id": chart_id, "question": question, "language": language,
    }).encode("utf-8")
    req = _urlreq.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with _urlreq.urlopen(req, timeout=timeout) as r:
            payload = r.read().decode("utf-8")
    except _urlerr.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} from {url}: {e.read()[:300]!r}") from e
    except _urlerr.URLError as e:
        raise RuntimeError(f"URL error reaching {url}: {e}") from e
    try:
        return PredictResponse(raw=json.loads(payload))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"non-JSON response from {url}: {payload[:300]!r}") from e


# ─────────────────────────────────────────────────────────────────────
# Gates
# ─────────────────────────────────────────────────────────────────────

def gate_determinism(responses: List[PredictResponse], n: int) -> GateResult:
    lines = {r.signal_line for r in responses if r.signal_line}
    moves = {r.action_item for r in responses if r.action_item}
    if len(lines) == 1 and len(moves) == 1:
        return GateResult(
            name=f"G1 DETERMINISM ({n}x)",
            passed=True,
            detail="identical signal_line + identical action_item",
            samples=[next(iter(lines))[:120], next(iter(moves))[:120]],
        )
    return GateResult(
        name=f"G1 DETERMINISM ({n}x)",
        passed=False,
        detail=f"{len(lines)} unique signal_line(s), {len(moves)} unique action_item(s)",
        samples=[*list(lines)[:3], *list(moves)[:3]],
    )


def _has_future_year_headline(first_sentence: str, current_year: int) -> Optional[int]:
    """Return the offending year if a future year appears in the first
    sentence of a TODAY response, else None."""
    if not first_sentence:
        return None
    for y in _BARE_YEAR_RE.findall(first_sentence):
        yi = int(y)
        if yi >= current_year + 1:
            return yi
    return None


def gate_timeframe_honesty(responses: List[PredictResponse]) -> GateResult:
    current_year = time.gmtime().tm_year
    offenders: List[str] = []
    for r in responses:
        first = r.signal_line.split(".")[0]
        y = _has_future_year_headline(first, current_year)
        if y:
            offenders.append(f"signal_line headlines {y}: {r.signal_line[:120]!r}")
        # plain_summary first sentence too
        first_ps = r.plain_summary.split(".")[0]
        y2 = _has_future_year_headline(first_ps, current_year)
        if y2:
            offenders.append(f"plain_summary headlines {y2}: {r.plain_summary[:120]!r}")
    if offenders:
        return GateResult(
            name="G2 TIMEFRAME HONESTY",
            passed=False,
            detail=f"{len(offenders)} responses headline a future-year deferral on a TODAY question",
            samples=offenders[:3],
        )
    return GateResult(
        name="G2 TIMEFRAME HONESTY",
        passed=True,
        detail="no TODAY response headlines a multi-year deferral",
    )


def gate_no_template_leak(responses: List[PredictResponse]) -> GateResult:
    hits: List[str] = []
    for r in responses:
        blob = r.all_user_fields_blob()
        for pat in DANGLING_PATTERNS:
            if pat.search(blob):
                hits.append(f"{pat.pattern}: {blob[:140]!r}")
    if hits:
        return GateResult(
            name="G3 NO TEMPLATE LEAK",
            passed=False,
            detail=f"{len(hits)} dangling-pattern hits across responses",
            samples=hits[:3],
        )
    return GateResult(name="G3 NO TEMPLATE LEAK", passed=True, detail="zero dangling patterns")


def gate_no_energy_label_leak(responses: List[PredictResponse]) -> GateResult:
    hits: List[str] = []
    for r in responses:
        blob = r.all_user_fields_blob().lower()
        for label in BANNED_ENERGY_LABELS:
            if label in blob:
                hits.append(f"{label}: {blob[:140]!r}")
    if hits:
        return GateResult(
            name="G4 NO ENERGY-LABEL LEAK",
            passed=False,
            detail=f"{len(hits)} banned-label hits across responses",
            samples=hits[:3],
        )
    return GateResult(name="G4 NO ENERGY-LABEL LEAK", passed=True, detail="zero banned labels")


def gate_property_regression(r: PredictResponse) -> GateResult:
    """signal_line must mention 'property' (not 'wealth' as the headline)
    and the plain_summary must be band-consistent (no positive narration
    contradicting a FLAT/WEAK signal_line, and vice versa)."""
    sl = r.signal_line.lower()
    ps = r.plain_summary.lower()
    issues = []
    if "wealth is " in sl and "property" not in sl:
        issues.append(f"signal_line headlines 'wealth' instead of 'property': {r.signal_line[:120]!r}")
    if "property" not in sl and "property" not in ps[:200]:
        issues.append(f"property not addressed in headline or first 200 chars: sl={r.signal_line[:80]!r}")
    # Band-consistency: FLAT/WEAK in signal_line shouldn't pair with overtly positive prose.
    flat_signals = ("flat", "soft window", "hold off", "neutral window")
    positive_prose = (
        "well-supported", "is supportive", "is strong", "supports your",
        "supports property acquisition", "favorable", "act now",
        "good decision",
    )
    if any(f in sl for f in flat_signals) and any(p in ps for p in positive_prose):
        issues.append(
            f"band contradiction: signal_line says flat/soft but plain_summary uses positive language: "
            f"sl={r.signal_line[:80]!r}  ps={r.plain_summary[:140]!r}"
        )
    if issues:
        return GateResult(
            name="G5 PROPERTY REGRESSION",
            passed=False,
            detail=f"{len(issues)} issue(s) in property today response",
            samples=issues,
        )
    return GateResult(
        name="G5 PROPERTY REGRESSION",
        passed=True,
        detail=f"signal_line: {r.signal_line[:100]!r}",
    )


def gate_field_types(responses: List[PredictResponse]) -> GateResult:
    issues = []
    for i, r in enumerate(responses):
        sc, cf = r.signal_confidence, r.confidence
        if not isinstance(sc, str):
            issues.append(f"run {i+1}: signal_confidence is {type(sc).__name__}={sc!r}, expected str")
        elif sc.lower() not in {"high", "medium", "low"}:
            issues.append(f"run {i+1}: signal_confidence={sc!r} not in {{high,medium,low}}")
        if not isinstance(cf, (int, float)):
            issues.append(f"run {i+1}: confidence is {type(cf).__name__}={cf!r}, expected float")
        elif not (0.0 <= float(cf) <= 1.0):
            issues.append(f"run {i+1}: confidence={cf!r} out of [0,1]")
    if issues:
        return GateResult(
            name="G6 FIELD-TYPE INVARIANTS",
            passed=False,
            detail=f"{len(issues)} field-type violations",
            samples=issues[:3],
        )
    return GateResult(
        name="G6 FIELD-TYPE INVARIANTS",
        passed=True,
        detail="signal_confidence:str, confidence:float across all runs",
    )


# ─────────────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────────────

def _bar(c="═", n=72): return c * n

def _print_response_brief(label: str, r: PredictResponse) -> None:
    print(f"  [{label}]")
    print(f"    signal_line  : {r.signal_line}")
    print(f"    action_item  : {r.action_item}")
    print(f"    timing_window: {r.timing_window}")
    print(f"    plain_summary: {r.plain_summary[:200]}")
    print(f"    signal_conf  : {r.signal_confidence!r}    confidence: {r.confidence!r}")


def run_matrix(chart_id: str, base_url: str, runs: int,
               timeout: float, verbose: bool) -> int:
    print(_bar())
    print(f"  regression matrix")
    print(f"  base_url : {base_url}")
    print(f"  chart_id : {chart_id}")
    print(f"  runs     : {runs}")
    print(_bar())

    # ── Determinism block: speculation TODAY ──
    spec_q = "how is my speculation income today"
    spec_responses: List[PredictResponse] = []
    print(f"\n[1/2] DETERMINISM — {runs}x speculation today")
    for i in range(runs):
        try:
            r = call_predict(base_url, chart_id, spec_q, timeout=timeout)
        except RuntimeError as e:
            print(f"  ✗ run {i+1} failed: {e}")
            return 2
        spec_responses.append(r)
        if verbose:
            _print_response_brief(f"run {i+1}", r)
        else:
            print(f"  run {i+1}: {r.signal_line!r}")

    # ── Property regression block ──
    print(f"\n[2/2] PROPERTY — buying property today")
    try:
        prop_r = call_predict(
            base_url, chart_id, "how is buying property for me today",
            timeout=timeout,
        )
    except RuntimeError as e:
        print(f"  ✗ property run failed: {e}")
        return 2
    _print_response_brief("property", prop_r)

    # Bundle for cross-response leak checks.
    all_responses = list(spec_responses) + [prop_r]

    # ── Run gates ──
    print(f"\n{_bar('─')}")
    print("  acceptance gates")
    print(_bar("─"))
    gates: List[GateResult] = [
        gate_determinism(spec_responses, runs),
        gate_timeframe_honesty(spec_responses),  # speculation today is the timeframe test
        gate_no_template_leak(all_responses),
        gate_no_energy_label_leak(all_responses),
        gate_property_regression(prop_r),
        gate_field_types(all_responses),
    ]
    for g in gates:
        mark = "✓" if g.passed else "✗"
        print(f"  {mark} {g.name:32s} — {g.detail}")
        for s in g.samples[:3]:
            print(f"      • {s}")

    n_pass = sum(1 for g in gates if g.passed)
    n_fail = len(gates) - n_pass
    print(f"\n{_bar()}")
    print(f"  result: {n_pass}/{len(gates)} passed, {n_fail} failed")
    print(_bar())
    return 0 if n_fail == 0 else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Antar /predict regression matrix")
    ap.add_argument("--chart-id", default=DEFAULT_CHART_ID,
                    help=f"chart UUID (default: {DEFAULT_CHART_ID})")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help=f"base URL (default: {DEFAULT_BASE_URL})")
    ap.add_argument("--runs", type=int, default=DEFAULT_RUNS,
                    help=f"determinism repeats (default: {DEFAULT_RUNS})")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                    help=f"per-call timeout seconds (default: {DEFAULT_TIMEOUT})")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="print full response brief for each run")
    args = ap.parse_args(argv)
    return run_matrix(
        chart_id=args.chart_id,
        base_url=args.base_url,
        runs=args.runs,
        timeout=args.timeout,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
