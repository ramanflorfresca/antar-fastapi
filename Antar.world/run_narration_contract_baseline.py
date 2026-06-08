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
import os  # BASELINE_RUNNER_LIVE_FALLBACK 2026-06-07
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
    # READ = source (verdict-first headline) + explanation (body)
    # concatenated for each of the first 2 stuckness sources. The
    # source field is the verdict-first sentence post step-3 patch
    # ("Your work routine is under pressure..."); explanation is the
    # 2-3 sentence body that names the nouns + duration.
    sources = diag.get("current_stuckness_sources") or []
    read_parts = []
    for s in sources[:2]:
        if isinstance(s, dict):
            src = (s.get("source") or "").strip()
            expl = (s.get("explanation") or "").strip()
            joined = " ".join(p for p in (src, expl) if p)
            if joined:
                read_parts.append(joined)
    read = " ".join(read_parts).strip()
    # NEXT = next_phase_shift.preparation_advice
    shift = diag.get("next_phase_shift") or {}
    nxt = shift.get("preparation_advice") or ""
    return (read, nxt, _ALL_HOUSES)


# ── BASELINE_RUNNER_LIVE_FALLBACK helper ────────────────────────────
import time as _br_time
import urllib.request as _br_urlreq
import urllib.error as _br_urlerr

_BR_BASE = "https://antar-fastapi-production.up.railway.app"


def _fetch_life_arc_live(chart_id: str) -> dict | None:
    """Pull /life-arc for chart_id, polling past the cache-miss stub.
    Returns None on hard failure. Used by the runner when the audit
    JSON is absent or a generating stub."""
    if not chart_id:
        return None
    url = f"{_BR_BASE}/api/v1/life-arc/{chart_id}?horizon_months=12"
    # Trigger a force_refresh first to invalidate any v2.1-era stale
    # entry, then poll the non-refresh URL until diagnostic populates.
    try:
        _br_urlreq.urlopen(url + "&force_refresh=true", timeout=60).read()
    except Exception:
        pass
    for _ in range(15):  # ~75s max
        try:
            resp = _br_urlreq.urlopen(url, timeout=15).read()
            payload = json.loads(resp)
            if (isinstance(payload, dict)
                    and payload.get("diagnostic")
                    and not (payload.get("status") == "generating")):
                return payload
        except Exception:
            pass
        _br_time.sleep(5)
    return None


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
            # BASELINE_RUNNER_LIVE_FALLBACK: only the cycle surface
            # auto-pulls live. The other surfaces still require pre-
            # cached audit JSONs.
            if label == "Cycle /life-arc":
                payload = _fetch_life_arc_live(os.environ.get("BASELINE_CHART_ID", ""))
                if payload is None:
                    results.append({
                        "chart": chart_label,
                        "surface": label,
                        "error": f"live fallback failed: no chart_id or HTTP error",
                    })
                    continue
            else:
                results.append({
                    "chart": chart_label,
                    "surface": label,
                    "error": f"missing {path}",
                })
                continue
        else:
            try:
                payload = json.loads(path.read_text())
            except Exception as e:
                results.append({
                    "chart": chart_label,
                    "surface": label,
                    "error": f"parse fail: {e}",
                })
                continue
        # Cache-miss guard: /life-arc returns {"status":"generating",
        # "retry_after_ms": N} while a force_refresh-triggered regen
        # completes in the background. Scoring this as zeros is a
        # misleading false-fail — flag it loudly so the user re-pulls
        # without force_refresh after the warm cache fills.
        if (isinstance(payload, dict)
                and payload.get("status") == "generating"
                and len(payload) <= 3):
            if label == "Cycle /life-arc":
                # Live fallback: keep polling for up to ~75s.
                live = _fetch_life_arc_live(os.environ.get("BASELINE_CHART_ID", ""))
                if live and live.get("diagnostic"):
                    payload = live
                else:
                    results.append({
                        "chart": chart_label,
                        "surface": label,
                        "error": f"CACHE MISS — live fallback also empty",
                    })
                    continue
            else:
                results.append({
                    "chart": chart_label,
                    "surface": label,
                    "error": f"CACHE MISS (force_refresh in flight) — re-pull "
                             f"without force_refresh in ~10s",
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
    # ── BASELINE_RUNNER_LIVE_FALLBACK 2026-06-07 ────────────────────────
    # Chart 2 truncated label was 062bc778; full UUID is
    # 062bc778-09a1-4c8e-a281-b822e96f92e9. Both chart_ids are now
    # exposed via env so the live HTTP fallback can pull them when the
    # audit JSON is missing or a cache-miss stub.
    _CHARTS = [
        ("chart1 (Raman de0c6265)", "",       "de0c6265-96cc-41ba-a39c-e55868fa5806"),
        ("chart2 (RC 062bc778)",    "chart2", "062bc778-09a1-4c8e-a281-b822e96f92e9"),
    ]
    for chart_label, subdir, _chart_uuid in _CHARTS:
        os.environ["BASELINE_CHART_ID"] = _chart_uuid
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
