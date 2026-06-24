"""
antar_engine/profession/profession_gate.py  —  CONVICTION GATE

The profession read stays QUARANTINED behind this gate until it is validated
against a set of known charts + their real professions (Raman provides the set)
AND Raman approves. Same discipline as the KP and past-events engines.

The gate refuses to open on the shipped template/example rows (a recurring
foot-gun: a gate that opens on placeholder data). A real validation row must
name a real chart and a real profession/arena outcome.

Validation roster format (validation/profession_validation.json):
{
  "min_accuracy": 0.70,
  "cases": [
    {
      "id": "person-real-1",
      "chart_data": { "lagna": {...}, "planets": {...} },
      "known_profession": "founder / hard-tech",     # what they actually do
      "expected_arena_keywords": ["venture", "engineering"],
      "expected_archetype": "THE CATALYST"           # optional
    }
  ]
}
A case scores a HIT if the predicted dominant arena set matches an
expected_arena_keyword OR the predicted archetype matches expected_archetype.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

PASS_THRESHOLD = 0.70
MIN_CASES = 8

_HERE = os.path.dirname(os.path.abspath(__file__))
VALIDATION_DIR = os.path.join(_HERE, "validation")
DEFAULT_ROSTER = os.path.join(VALIDATION_DIR, "profession_validation.json")
GATE_STATUS_PATH = os.path.join(VALIDATION_DIR, "profession_gate_status.json")

_PLACEHOLDER_TOKENS = ("example", "template", "sample", "dummy", "replace")


def _is_placeholder_case(case) -> bool:
    if not isinstance(case, dict):
        return True
    cid = str(case.get("id", "")).lower()
    if any(tok in cid for tok in _PLACEHOLDER_TOKENS):
        return True
    if not case.get("chart_data"):
        return True
    if not str(case.get("known_profession", "")).strip():
        return True
    notes = str(case.get("notes", "")).lower()
    if "replace" in notes or "example row" in notes:
        return True
    return False


def is_gate_open() -> bool:
    """Single source of truth any surface MUST consult. Closed unless passed."""
    try:
        with open(GATE_STATUS_PATH) as f:
            return bool(json.load(f).get("passed") is True)
    except Exception:
        return False


def _write_status(sc: dict) -> None:
    os.makedirs(VALIDATION_DIR, exist_ok=True)
    with open(GATE_STATUS_PATH, "w") as f:
        json.dump(sc, f, indent=2)


def _score_case(case) -> bool:
    from .profession_service import get_profession_read
    read = get_profession_read(case["chart_data"], include_evidence=True,
                               require_gate=False)
    pred_arenas = " ".join(a["label"].lower() for a in read["arenas"])
    pred_arch = (read["archetype"]["name"] or "").upper()

    for kw in case.get("expected_arena_keywords", []):
        if kw.lower() in pred_arenas:
            return True
    exp_arch = str(case.get("expected_archetype", "")).upper().strip()
    if exp_arch and exp_arch in pred_arch:
        return True
    return False


def run_validation(roster_path: str = DEFAULT_ROSTER, write: bool = True) -> dict:
    if not os.path.exists(roster_path):
        sc = {"passed": False, "reason": "no validation set provided",
              "n_cases": 0, "timestamp": datetime.utcnow().isoformat() + "Z"}
        if write:
            _write_status(sc)
        return sc

    with open(roster_path) as f:
        roster = json.load(f)
    cases = roster.get("cases", [])
    real = [c for c in cases if not _is_placeholder_case(c)]
    dropped = len(cases) - len(real)

    if len(real) < MIN_CASES:
        sc = {"passed": False,
              "reason": (f"only {len(real)} real case(s) "
                         f"({dropped} placeholder dropped) — need >= {MIN_CASES}. "
                         f"Gate CLOSED (profession quarantined)."),
              "n_cases": len(real), "n_placeholder_dropped": dropped,
              "timestamp": datetime.utcnow().isoformat() + "Z"}
        if write:
            _write_status(sc)
        return sc

    hits = 0
    rows = []
    for c in real:
        try:
            hit = _score_case(c)
        except Exception as e:
            hit = False
            rows.append({"id": c.get("id"), "error": str(e), "hit": False})
            continue
        hits += int(hit)
        rows.append({"id": c.get("id"), "known": c.get("known_profession"),
                     "hit": hit})

    n = len(real)
    acc = hits / n if n else None
    threshold = roster.get("min_accuracy", PASS_THRESHOLD)
    passed = bool(n >= MIN_CASES and acc is not None and acc >= threshold)

    sc = {
        "passed": passed,
        "reason": ("gate open" if passed else
                   f"accuracy {acc} < {threshold} or n {n} < {MIN_CASES}"),
        "n_cases": n, "hits": hits, "accuracy": acc, "threshold": threshold,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if write:
        os.makedirs(VALIDATION_DIR, exist_ok=True)
        with open(os.path.join(VALIDATION_DIR, "profession_validation_results.json"),
                  "w") as f:
            json.dump({"scorecard": sc, "rows": rows}, f, indent=2)
        _write_status(sc)
    return sc


if __name__ == "__main__":
    s = run_validation()
    print(json.dumps(s, indent=2))
    print("\nGATE OPEN" if s["passed"] else "\nGATE CLOSED (profession quarantined)")
