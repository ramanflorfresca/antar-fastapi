"""
antar_engine/accuracy_board.py — does each engine beat chance, by how much, and
how sure are we? (Outcome loop, week 3. Spec: "Outcome Loop & Accuracy Board".)

Honest by construction:
  * Only explicit answers count. yes = 1, partly = 0.5, no = 0; "not sure" and
    unanswered are excluded from hit rates but reported (a low answer rate is a
    warning in itself).
  * A cell needs >= MIN_N answers before any status other than "Too few answers".
  * Holdout: charts are split into two halves by a hash of the chart id; a finding
    must hold in BOTH halves.
  * Chance: with no decoy check-ins there is NO measured base rate, so no cell can
    claim "beats chance" — it says "No baseline yet". Once decoys exist, their
    yes-rate per topic is the baseline and lift = hit rate − baseline.
  * Shared windows: many charts get the same event-engine window, so claims are
    correlated; each cell reports how many DISTINCT windows its answers cover.

Engine rule (v1, written down before any data): an engine is POSITIVE for a claim
when its own verdict isn't a denial AND its own window overlaps the claim's
window; NEGATIVE otherwise. It hits when positive & outcome yes/partly, or
negative & outcome no. KP "conditional" leans are reported in their own row,
never forced into right/wrong. An engine with no window is not scored.

Totals only — never a person, chart or question.
"""
from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from datetime import date
from typing import Optional

from antar_engine.outcomes import parse_window

MIN_N = 30
MIN_ANSWER_RATE = 0.30
SCORE = {"yes": 1.0, "partly": 0.5, "no": 0.0}
SOURCES = ("ask_explore", "ask_yesno", "decoy")
_DENIALS = {"NO", "DENIED", "DENIAL", "NOT_PROMISED"}


def half_of(chart_id: str) -> str:
    return "A" if int(hashlib.sha1((chart_id or "").encode()).hexdigest(), 16) % 2 == 0 else "B"


def wilson(successes: float, n: int, z: float = 1.96) -> tuple:
    """95% Wilson interval for a proportion (fractional successes allowed)."""
    if n <= 0:
        return (None, None)
    p = successes / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - h), 3), round(min(1.0, c + h), 3))


def _overlaps(a: tuple, b: tuple) -> bool:
    (s1, e1), (s2, e2) = a, b
    return bool(s1 and e1 and s2 and e2 and s1 <= e2 and s2 <= e1)


def engine_calls(claim: dict) -> dict:
    """{engine: 'positive'|'negative'|'conditional'} for the engines that can be
    scored on this claim (see the module rule)."""
    out = {}
    eng = claim.get("engines") or {}
    try:
        cw = (date.fromisoformat(str(claim.get("window_start") or claim.get("window_end"))[:10]),
              date.fromisoformat(str(claim.get("window_end"))[:10]))
    except Exception:
        return out
    for name, e in eng.items():
        if not isinstance(e, dict):
            continue
        if name == "kp":
            lean = str(e.get("lean") or "").lower()
            if lean == "yes":
                out["kp"] = "positive"
            elif lean in ("no", "not_now"):
                out["kp"] = "negative"
            elif lean == "conditional":
                out["kp"] = "conditional"
            continue
        verdict = str(e.get("client") or e.get("verdict") or "").upper()
        ew = parse_window(e.get("window") or "")
        if not ew[1]:
            continue                     # no window → not scorable
        out[name] = ("positive" if verdict not in _DENIALS and _overlaps(ew, cw) else "negative")
    return out


def _cell():
    return {"claims": 0, "sent": 0, "answered": 0, "not_sure": 0, "score": 0.0,
            "halves": {"A": [0.0, 0], "B": [0.0, 0]}, "windows": set()}


def _add(cell: dict, claim: dict, outcome: Optional[str], hit: Optional[float]):
    cell["claims"] += 1
    if claim.get("checkin_sent_at"):
        cell["sent"] += 1
    if outcome == "not_sure":
        cell["not_sure"] += 1
    if hit is None:
        return
    cell["answered"] += 1
    cell["score"] += hit
    h = cell["halves"][half_of(claim.get("chart_id"))]
    h[0] += hit
    h[1] += 1
    cell["windows"].add((claim.get("window_start"), claim.get("window_end")))


def _finish(cell: dict, baseline: Optional[float]) -> dict:
    n = cell["answered"]
    hit = round(cell["score"] / n, 3) if n else None
    asked = max(cell["sent"], n + cell["not_sure"])
    ar = round((n + cell["not_sure"]) / asked, 3) if asked else None
    halves = {k: (round(v[0] / v[1], 3) if v[1] else None, v[1]) for k, v in cell["halves"].items()}
    lo, hi = wilson(cell["score"], n)
    if n < MIN_N:
        status = "Too few answers"
    elif ar is not None and asked >= 10 and ar < MIN_ANSWER_RATE:
        status = "Unreliable"
    elif baseline is None:
        status = "No baseline yet"
    else:
        ok = all(
            v[1] >= MIN_N // 2 and wilson(v[0], v[1])[0] is not None
            and wilson(v[0], v[1])[0] > baseline
            for v in cell["halves"].values())
        status = "Beats chance" if ok else "No better than chance"
    return {"claims": cell["claims"], "sent": cell["sent"], "answered": n,
            "not_sure": cell["not_sure"], "answer_rate": ar, "hit_rate": hit,
            "ci95": [lo, hi], "baseline": baseline,
            "lift": (round(hit - baseline, 3) if (hit is not None and baseline is not None) else None),
            "halves": halves, "distinct_windows": len(cell["windows"]), "status": status}


def build(claims: list, outcomes: list) -> dict:
    """The whole board from raw rows (pure function — easy to test)."""
    outs = {o["claim_id"]: o for o in outcomes}
    claims = [c for c in claims if c.get("source") in SOURCES]

    # decoy base rates per topic (none until decoys exist)
    decoy = defaultdict(lambda: [0.0, 0])
    for c in claims:
        o = outs.get(c["id"], {}).get("outcome")
        if c.get("source") == "decoy" and o in SCORE:
            decoy[c.get("topic") or "general"][0] += SCORE[o]
            decoy[c.get("topic") or "general"][1] += 1
    baselines = {t: round(s / n, 3) for t, (s, n) in decoy.items() if n >= MIN_N}

    final = defaultdict(_cell)
    engines = defaultdict(_cell)
    calib = defaultdict(_cell)
    health = {"claims": 0, "due": 0, "sent": 0, "by_channel": defaultdict(int),
              "answered": 0, "not_sure": 0}
    months = defaultdict(lambda: [0.0, 0])
    today = date.today().isoformat()
    for c in claims:
        if c.get("source") == "decoy":
            continue
        o = outs.get(c["id"], {})
        outcome = o.get("outcome")
        hit = SCORE.get(outcome)
        topic = c.get("topic") or "general"
        health["claims"] += 1
        if str(c.get("checkin_due_at") or "")[:10] <= today:
            health["due"] += 1
        if c.get("checkin_sent_at"):
            health["sent"] += 1
            health["by_channel"][(c.get("checkin_channel") or "?").replace("+reask", "")] += 1
        if hit is not None:
            health["answered"] += 1
            m = str(o.get("answered_at") or "")[:7]
            months[m][0] += hit
            months[m][1] += 1
        elif outcome == "not_sure":
            health["not_sure"] += 1
        _add(final[(c.get("source"), topic)], c, outcome, hit)
        cw = c.get("confidence_word") or ((c.get("engines") or {}).get("kp") or {}).get("lean")
        if cw:
            _add(calib[str(cw)], c, outcome, hit)
        for eng, call in engine_calls(c).items():
            if call == "conditional":
                _add(engines[(eng + " (conditional)", topic)], c, outcome, hit)
                continue
            eh = None
            if hit is not None:
                eh = (1.0 if outcome in ("yes", "partly") else 0.0) if call == "positive" else \
                     (1.0 if outcome == "no" else 0.0)
            _add(engines[(eng, topic)], c, outcome, eh)

    return {
        "rules": {"min_answers": MIN_N, "min_answer_rate": MIN_ANSWER_RATE,
                  "scores": SCORE, "holdout": "chart-id hash, halves A/B",
                  "baselines_available": bool(baselines)},
        "final_answers": [dict(source=s, topic=t, **_finish(v, baselines.get(t)))
                          for (s, t), v in sorted(final.items())],
        "engines": [dict(engine=e, topic=t, **_finish(v, baselines.get(t)))
                    for (e, t), v in sorted(engines.items())],
        "calibration": [dict(word=w, **_finish(v, None)) for w, v in sorted(calib.items())],
        "health": dict(health, by_channel=dict(health["by_channel"])),
        "trend": [{"month": m, "answered": n, "hit_rate": round(s / n, 3)}
                  for m, (s, n) in sorted(months.items()) if m],
        "baselines": baselines,
    }


def load(sb) -> tuple:
    claims, off = [], 0
    while True:
        page = (sb.table("prediction_claims")
                .select("id,chart_id,source,topic,claim_type,window_start,window_end,verdict,"
                        "confidence_word,engines,checkin_due_at,checkin_sent_at,checkin_channel")
                .in_("source", list(SOURCES)).range(off, off + 999).execute().data) or []
        claims += page
        off += 1000
        if len(page) < 1000:
            break
    outs = (sb.table("prediction_outcomes").select("claim_id,outcome,answered_at")
            .limit(100000).execute().data) or []
    return claims, outs
