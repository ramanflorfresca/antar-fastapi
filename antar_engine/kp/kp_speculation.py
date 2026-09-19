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
        sc = kp_horary_score(chart)
        # plain lean for the narrator (never a planet/house name, never "you'll win")
        _lean = {"yes": "the moment reads as mildly supportive",
                 "conditional": "the moment reads as mixed / borderline",
                 "no": "the moment does not read as supportive"}.get(
                     v.get("verdict"), "the moment reads as unclear")
        return {"available": True, "verdict": v.get("verdict"),
                "confidence": v.get("confidence"), "lean": _lean,
                "score": sc.get("score"), "band": sc.get("band"),
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


def _parse_kp_score(trackable_claim):
    m = _re.search(r"score=(\d+)", str(trackable_claim or ""))
    return int(m.group(1)) if m else None


def _score_bucket(s):
    if s is None:
        return "unknown"
    return "high (62-100)" if s >= 62 else "mid (45-61)" if s >= 45 else "low (5-44)"


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
    by_bucket = {}  # score bucket -> {win, loss} (the real calibration question)
    for r in answered:
        won = str(r.get("feedback_status")).lower() == "yes"
        # score-bucket calibration: does a higher KP signal win more often?
        b = _score_bucket(_parse_kp_score(r.get("trackable_claim")))
        bd = by_bucket.setdefault(b, {"win": 0, "loss": 0})
        bd["win" if won else "loss"] += 1
        lean = _parse_kp_lean(r.get("trackable_claim"))
        if lean is None:
            continue
        d = by_lean.setdefault(lean, {"win": 0, "loss": 0})
        d["win" if won else "loss"] += 1
        if lean == "conditional":
            mixed += 1
            continue
        directional += 1
        if (lean == "yes" and won) or (lean == "no" and not won):
            hits += 1
    # win-rate per score bucket — the honest signal-quality check
    for b, bd in by_bucket.items():
        n = bd["win"] + bd["loss"]
        bd["win_rate"] = round(bd["win"] / n, 3) if n else None
    return {
        "available": True,
        "n_answered": len(answered),
        "n_directional": directional,
        "hits": hits,
        "hit_rate": round(hits / directional, 3) if directional else None,
        "n_mixed": mixed,
        "by_lean": by_lean,
        "by_score_bucket": by_bucket,
        "note": ("CALIBRATION ONLY — not a validated predictor; does not open any "
                 "gate. by_score_bucket win-rate is the key check: a real signal "
                 "should win more often in the high bucket than the low. Directional "
                 "hit_rate treats yes/no leans; mixed excluded."),
    }


# ── HORARY FAVORABILITY SCORE (0-100) ─────────────────────────────────────────
# A graded KP SIGNAL for the moment, instead of a bare yes/no. It is the
# smoothed proportion of KP "votes" that back speculation right now: the sub-lord
# of each speculation-favour cusp (2 money, 5 speculation, 6 winning, 11 gain)
# votes SUPPORTIVE if it signifies any favour house {2,5,6,11}, and a DRAG if it
# signifies a spoiler {8,12}; the 11th cuspal sub-lord signifying the 11th
# (materialisation) adds one supportive vote. Laplace-smoothed so it never reads
# a false 0 or 100. THIS IS SIGNAL STRENGTH, NOT A PROBABILITY OF WINNING — it is
# uncalibrated and under test (the calibration log will tell us if it means
# anything). Deterministic; the arithmetic a KP astrologer does by hand.
_FAVOUR_CUSPS = (2, 5, 6, 11)


def kp_horary_score(chart) -> dict:
    """{score 0-100, band, supportive, drag, gate}. Never raises."""
    try:
        from .kp_significators import build_significators
        _house_sig, planet_sig = build_significators(chart)
        supportive, drag = 0, 0
        for c in _FAVOUR_CUSPS:
            csl = chart["cusps"][c]["sub_lord"]
            houses = set(planet_sig.get(csl, []))
            if houses & SPEC_FAVOUR:
                supportive += 1
            if houses & SPEC_AGAINST:
                drag += 1
        # materialisation: 11th CSL signifies the 11th
        gate = 11 in set(planet_sig.get(chart["cusps"][11]["sub_lord"], []))
        if gate:
            supportive += 1
        # Laplace-smoothed supportive share -> 0..100
        score = round(100.0 * (supportive + 0.5) / (supportive + drag + 1.0))
        score = max(5, min(95, score))
        band = ("supportive" if score >= 62 else
                "mixed" if score >= 45 else "not supportive")
        return {"score": score, "band": band, "supportive": supportive,
                "drag": drag, "gate": bool(gate)}
    except Exception as e:
        return {"score": None, "band": "unclear", "error": str(e)[:160]}


def kp_horary_week(lat, lon, start_utc=None, days=7, local_hour=20,
                   tz_offset=0.0) -> dict:
    """Scan the next `days` days and score each at a representative local hour
    (default 20:00). Returns {available, days:[{date, score, band}], best:{...}}.
    A proxy for 'which day this week' — clearly approximate (a true horary is a
    single moment), useful for ranking days. Never raises."""
    try:
        from datetime import datetime, timedelta
        from .kp_chart import compute_kp_chart
        base = start_utc or datetime.utcnow()
        out = []
        for i in range(int(days)):
            d = (base + timedelta(days=i))
            # cast at local_hour local time -> convert to the chart's tz input
            when_local = d.replace(hour=int(local_hour), minute=0, second=0,
                                   microsecond=0)
            chart = compute_kp_chart(when_local.strftime("%Y-%m-%d"),
                                     when_local.strftime("%H:%M"),
                                     float(lat), float(lon),
                                     tz_offset=float(tz_offset))
            sc = kp_horary_score(chart)
            out.append({"date": when_local.strftime("%Y-%m-%d"),
                        "score": sc.get("score"), "band": sc.get("band")})
        ranked = [x for x in out if isinstance(x.get("score"), int)]
        best = max(ranked, key=lambda x: x["score"]) if ranked else None
        return {"available": bool(ranked), "days": out, "best": best,
                "local_hour": int(local_hour)}
    except Exception as e:
        return {"available": False, "error": str(e)[:160]}
