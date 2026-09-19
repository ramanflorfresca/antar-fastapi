"""
antar_engine/kp/kp_speculation.py

Dated KP speculation scorer — "was date D favourable for a bet, for this chart?"
Used ONLY by the gambling backtest (validate-first). Never user-facing until the
gambling gate opens at >=70% on real dated win/loss cases.

Rule (KP): the dasha says WHICH period is favourable for the matter. For
speculation the favourable houses are {2,5,6,11} and the spoilers {8,12}
(kp_significators.QUESTION_TYPES['speculation']). A date is scored 'yes' (a win
is supported) when the running dasha lords (per `strictness`) are net
significators of the speculation-favour houses; optionally tightened by a
transit trigger. Otherwise 'no' (loss more likely).
"""
from __future__ import annotations

SPEC_FAVOUR = {2, 5, 6, 11}
SPEC_AGAINST = {8, 12}


def speculation_significators(chart, strong=True):
    from .kp_timing import _net_positive
    from .kp_significators import ALL_PLANETS
    return {p for p in ALL_PLANETS
            if _net_positive(chart, p, SPEC_FAVOUR, SPEC_AGAINST, strong=strong)}


def kp_speculation_on_date(chart, date_str, strictness="ad_pd",
                           require_transit=False, strong=True) -> dict:
    """{pred: 'yes'|'no', md, ad, pd, sigs}. Never raises into the caller."""
    try:
        from .kp_timing import (build_timeline, lords_at, _combined_pass,
                                _date_to_jd)
        sigs = speculation_significators(chart, strong=strong)
        jd = _date_to_jd(date_str)
        periods = build_timeline(chart, jd + 1)
        md, ad, pd = lords_at(periods, jd)
        passed = _combined_pass(periods, sigs, jd, strictness, require_transit)
        return {"pred": "yes" if passed else "no",
                "md": md, "ad": ad, "pd": pd, "sigs": sorted(sigs)}
    except Exception as e:
        return {"pred": None, "error": str(e)[:160]}


# ── KP HORARY (prashna) — moment-based speculation reading ────────────────────
# Natal-dasha can't resolve a single night (a person's wins+losses fall in the
# same dasha — proven on real data). Horary casts the chart for the MOMENT of the
# question, which DOES change through the day. This is the KP method actually used
# for gambling. Presented as a READING (transparent + caveated), never a
# guaranteed win; logged for calibration so the claim earns or loses trust.
def kp_horary_speculation(lat, lon, when_utc=None) -> dict:
    """Cast a KP chart for the moment at the querent's location; read the
    speculation verdict. {available, verdict yes|no|conditional, confidence 0-3,
    drivers, moment_utc}. Never raises."""
    try:
        from datetime import datetime
        from .kp_chart import compute_kp_chart
        from .kp_significators import verdict
        now = when_utc or datetime.utcnow()
        chart = compute_kp_chart(now.strftime("%Y-%m-%d"), now.strftime("%H:%M"),
                                 float(lat), float(lon), tz_offset=0.0)
        v = verdict(chart, "speculation")
        # plain lean for the narrator (never a planet/house name, never "you'll win")
        _lean = {"yes": "the moment reads as mildly supportive",
                 "conditional": "the moment reads as mixed / borderline",
                 "no": "the moment does not read as supportive"}.get(
                     v.get("verdict"), "the moment reads as unclear")
        return {"available": True, "verdict": v.get("verdict"),
                "confidence": v.get("confidence"), "lean": _lean,
                "drivers": v.get("drivers"), "moment_utc": now.isoformat() + "Z"}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}


# ── CALIBRATION SCORER ────────────────────────────────────────────────────────
# Reads the reconciled speculation rows the /ask path logged (user_correlations,
# trackable_claim carries "[KP_LEAN=<v>;conf=<n>]") and scores the KP moment-read
# against the real reported outcome. This is a CALIBRATION report only — it does
# NOT open any gate and must never be presented as a validated win-predictor.
# Feedback mapping: status 'yes' = the bet went well (win), 'no' = it did not
# (loss); 'partial'/'skipped'/'pending' are excluded. Directional hit = a
# 'supportive' read that won, or a 'not supportive' read that lost. 'mixed'
# (conditional) reads are reported separately (no directional claim was made).
import re as _re


def _parse_kp_lean(trackable_claim):
    m = _re.search(r"KP_LEAN=([a-z]+)", str(trackable_claim or ""))
    return m.group(1) if m else None


def score_kp_horary_calibration(sb, chart_id=None) -> dict:
    """{available, n_answered, n_directional, hits, hit_rate, by_lean:{...},
    n_mixed, note}. Never raises."""
    try:
        q = (sb.table("user_correlations")
             .select("trackable_claim,feedback_status,chart_id")
             .eq("concern", "speculation"))
        if chart_id:
            q = q.eq("chart_id", chart_id)
        rows = (q.execute().data) or []
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}

    answered = [r for r in rows if str(r.get("feedback_status") or "").lower()
                in ("yes", "no")]
    directional, hits, mixed = 0, 0, 0
    by_lean = {}  # lean -> {win, loss}
    for r in answered:
        lean = _parse_kp_lean(r.get("trackable_claim"))
        if lean is None:
            continue
        won = str(r.get("feedback_status")).lower() == "yes"
        d = by_lean.setdefault(lean, {"win": 0, "loss": 0})
        d["win" if won else "loss"] += 1
        if lean == "conditional":
            mixed += 1
            continue
        directional += 1
        if (lean == "yes" and won) or (lean == "no" and not won):
            hits += 1
    return {
        "available": True,
        "n_answered": len(answered),
        "n_directional": directional,
        "hits": hits,
        "hit_rate": round(hits / directional, 3) if directional else None,
        "n_mixed": mixed,
        "by_lean": by_lean,
        "note": ("CALIBRATION ONLY — not a validated predictor; does not open any "
                 "gate. Directional = supportive/not-supportive reads with a known "
                 "win/loss; mixed reads excluded."),
    }
