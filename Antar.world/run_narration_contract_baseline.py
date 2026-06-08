#!/usr/bin/env python3
"""
run_narration_contract_baseline.py — measurement runner for the gate.

Step 1 of the Ask Narration Contract sprint. Scores each of the 5
user-facing prediction surfaces against antar_engine.narration_contract
and produces a per-surface scorecard.

This is MEASUREMENT only — it does not modify any endpoint output. The
score it produces is the BEFORE number we'll measure step-2 fixes against.

USAGE
-----
    cd ~/antarai && source venv311/bin/activate
    python Antar.world/run_narration_contract_baseline.py

Reads the audit JSONs already pulled in:
    Antar.world/../outputs/audit/{ask_explore,home,month,year,life_arc}.json
    Antar.world/../outputs/audit/chart2/...same...
(those paths are sandbox-side; on the host they're under the session
outputs folder — Raman runs this locally where the path is just the
relative audit folder).

If the audit folder isn't found, the runner falls back to hitting the
live API itself (same chart IDs, same question).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make the antar_engine package importable when this script is run from
# the Antar.world folder.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from antar_engine.narration_contract import (   # noqa: E402
    DOMAIN_HOUSES,
    score_read,
    explain_failure,
)


# ── surface adapters ──────────────────────────────────────────────────
# Each adapter extracts the (read, next_step, houses) tuple appropriate
# for that surface so score_read can grade it. The activated-houses
# choice is conservative — for live wiring we'll switch to evidence-
# derived houses, but baseline uses domain defaults.

def _ask_adapter(payload: dict, question: str) -> tuple[str, str, list[int]]:
    # /ask /explore returns top-level read + next.
    q = question.lower()
    if any(w in q for w in ("speculation", "stock", "bet", "gamble")):
        houses = DOMAIN_HOUSES["speculation"]
    elif "money" in q or "income" in q:
        houses = DOMAIN_HOUSES["money"]
    elif any(w in q for w in ("job", "career", "promotion")):
        houses = DOMAIN_HOUSES["career"]
    elif "move" in q or "relocat" in q:
        houses = DOMAIN_HOUSES["relocation"]
    elif "love" in q or "partner" in q or "marri" in q:
        houses = DOMAIN_HOUSES["relationship"]
    elif "health" in q:
        houses = DOMAIN_HOUSES["health"]
    else:
        houses = DOMAIN_HOUSES["general"]
    return (payload.get("read") or "", payload.get("next") or "", houses)


# Panoramic surfaces (today/month/year/cycle) cover all life domains
# simultaneously — score against all 12 houses, not the narrow "general"
# set. Ask is the only domain-specific surface.
_ALL_HOUSES = list(range(1, 13))


def _today_adapter(payload: dict, _q: str) -> tuple[str, str, list[int]]:
    today = (payload.get("horizons") or {}).get("today") or {}
    # READ = gist (the verdict-bearing field per /home contract).
    # NEXT = do (the imperative-action field).
    read = today.get("gist") or ""
    nxt = today.get("do") or ""
    return (read, nxt, _ALL_HOUSES)


def _today_lkread_adapter(payload: dict, _q: str) -> tuple[str, str, list[int]]:
    """Second pass on /home today — the lkRead.gist sub-block. The audit
    showed this carries the concrete-nouns layer while today.gist itself
    is abstract. Worth scoring separately to confirm."""
    today = (payload.get("horizons") or {}).get("today") or {}
    lk = today.get("lkRead") or {}
    read = lk.get("gist") or ""
    nxt = lk.get("do") or ""
    return (read, nxt, _ALL_HOUSES)


def _month_adapter(payload: dict, _q: str) -> tuple[str, str, list[int]]:
    read = payload.get("overview") or ""
    # Action source: priority_actions[0].action is the real verb-first
    # imperative tied to a named domain ("Schedule a health checkup…",
    # "Have a direct conversation with your partner…"). The mantra is
    # a first-person commitment, not a directive — using it here was
    # the gate's R4 false-fail.
    pa = payload.get("priority_actions") or []
    first_action = ""
    for item in pa:
        if isinstance(item, dict):
            txt = (item.get("action") or "").strip()
            if txt:
                first_action = txt
                break
    nxt = first_action or " ".join([
        str(payload.get("best_week") or ""),
        str(payload.get("monthly_mantra") or ""),
    ]).strip()
    return (read, nxt, _ALL_HOUSES)


def _year_adapter(payload: dict, _q: str) -> tuple[str, str, list[int]]:
    read = payload.get("year_summary") or ""
    nxt = " ".join([
        str(payload.get("year_mantra") or ""),
        " | ".join(str(x) for x in (payload.get("build_this_year") or [])[:2]),
    ]).strip()
    return (read, nxt, _ALL_HOUSES)


def _cycle_adapter(payload: dict, _q: str) -> tuple[str, str, list[int]]:
    diag = payload.get("diagnostic") or {}
    # READ = concatenated current_stuckness_sources explanations — that's
    # the user-facing prose layer.
    sources = diag.get("current_stuckness_sources") or []
    read_parts = []
    for s in sources[:2]:
        if isinstance(s, dict):
            read_parts.append(s.get("explanation") or s.get("source") or "")
    read = " ".join(read_parts).strip()
    # NEXT = next_phase_shift.preparation_advice
    shift = diag.get("next_phase_shift") or {}
    nxt = shift.get("preparation_advice") or ""
    return (read, nxt, _ALL_HOUSES)


SURFACES = [
    ("Ask /explore",     "ask_explore.json", _ask_adapter),
    ("Today /home gist", "home.json",        _today_adapter),
    ("Today /home lkRead", "home.json",      _today_lkread_adapter),
    ("Month /monthly-deepdive", "month.json", _month_adapter),
    ("Year /annual-plan", "year.json",       _year_adapter),
    ("Cycle /life-arc",  "life_arc.json",    _cycle_adapter),
]

ASK_QUESTION = "how is speculation money flow today"


# ── runner ────────────────────────────────────────────────────────────

def score_chart(chart_label: str, audit_dir: Path) -> list[dict]:
    """Score all 5 surfaces for one chart's audit JSONs."""
    results = []
    for label, filename, adapter in SURFACES:
        path = audit_dir / filename
        if not path.exists():
            results.append({
                "chart": chart_label,
                "surface": label,
                "error": f"missing {path}",
            })
            continue
        try:
            payload = json.loads(path.read_text())
        except Exception as e:
            results.append({
                "chart": chart_label,
                "surface": label,
                "error": f"parse fail: {e}",
            })
            continue
        read, nxt, houses = adapter(payload, ASK_QUESTION)
        score = score_read(read, houses, nxt)
        results.append({
            "chart": chart_label,
            "surface": label,
            "read_preview": (read[:120] + "…") if len(read) > 120 else read,
            "houses_used": houses,
            "score": score,
            "why_fail": explain_failure(score),
        })
    return results


def print_table(rows: list[dict]) -> None:
    """Compact terminal scorecard."""
    print()
    print(f"{'Surface':28s}  {'V':2s} {'N':3s} {'W':2s} {'A':2s}  "
          f"{'Energy':18s} {'Jargon':18s}  PASS")
    print("─" * 96)
    for r in rows:
        if "error" in r:
            print(f"{r['surface']:28s}  -- {r['error']}")
            continue
        s = r["score"]
        v = "✓" if s["verdict_first"] else "✗"
        n = f"{s['noun_count']}"
        w = "✓" if s["window_present"] else "✗"
        a = "✓" if s["concrete_action"] else "✗"
        eng = ",".join(s["energy_leaks"])[:18] or "—"
        jrg_keys = ",".join(s["jargon_leaks"].keys())[:18] or "—"
        passed = "✅" if s["passes_contract"] else "❌"
        print(f"{r['surface']:28s}  {v:2s} {n:3s} {w:2s} {a:2s}  "
              f"{eng:18s} {jrg_keys:18s}  {passed}")


def main() -> int:
    # Auto-locate audit dir relative to this script (sandbox path uses
    # ../outputs; host path uses ../../local_*/outputs — both work
    # through the symlink chain). The runner is host-friendly; pass an
    # override via $AUDIT_DIR if needed.
    audit_root = Path(os.environ.get("AUDIT_DIR") or
                      (HERE.parent / "_audit_baseline"))
    if not audit_root.exists():
        print(f"❌ Audit dir not found: {audit_root}\n"
              f"   Set $AUDIT_DIR to the folder containing the 5 JSONs.")
        return 1

    all_rows: list[dict] = []
    for chart_label, subdir in [("chart1 (Raman de0c6265)", ""),
                                 ("chart2 (RC 062bc778)",   "chart2")]:
        d = audit_root / subdir if subdir else audit_root
        if not d.exists():
            print(f"⚠ skip {chart_label}: {d} not found")
            continue
        print(f"\n{'=' * 96}\n{chart_label}\n{'=' * 96}")
        rows = score_chart(chart_label, d)
        print_table(rows)
        all_rows.extend(rows)

    # Aggregate counters
    passed = sum(1 for r in all_rows if r.get("score", {}).get("passes_contract"))
    total = sum(1 for r in all_rows if "score" in r)
    print(f"\n{'─' * 96}\nBASELINE TOTAL: {passed} / {total} surfaces pass the contract.\n")

    # Emit JSON summary for downstream tooling.
    out = HERE / "narration_contract_baseline.json"
    out.write_text(json.dumps(all_rows, indent=2, default=str))
    print(f"JSON: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
