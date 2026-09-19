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
