"""
The week ahead as three separately labelled lines (no blending):
  vimshottari : running major/sub/pratyantara/sookshma lords + Moon-based Gochara (gochara.py)
  jaimini     : timed library rules (K.N. Rao and other book rules) whose natal condition holds and whose dasha/transit
                activation holds on a day this week
  lal_kitab   : this year's Roop Chand annual rules and the age-cycle year lord
Deterministic; a line with nothing to say is empty. Accuracy gating comes later, from user check-ins.
"""
from datetime import date, timedelta
from typing import Optional

from antar_engine import gochara
from antar_engine import rule_registry as rr


def _book_lines(ctx, start: date, days: int, language: str) -> list:
    seen, out = {}, []
    for i in range(days):
        d = start + timedelta(days=i)
        for ev in rr.timed_book_evidence(ctx, d):
            if ev.rule_id in seen:
                seen[ev.rule_id]["days"].append(d.isoformat())
                continue
            row = {"rule_id": ev.rule_id, "book": ev.book, "tone": ev.tone, "subjects": ev.subjects,
                   "text": ev.plain.get(language) or ev.plain.get("en"), "days": [d.isoformat()]}
            seen[ev.rule_id] = row
            out.append(row)
    return out


def _lk_line(ctx, language: str) -> dict:
    from antar_engine import lk_year_lord
    out = {"year_lord": None, "rules": []}
    try:
        if ctx.birth_date:
            out["year_lord"] = lk_year_lord.year_lord_by_age(ctx.birth_date, ctx.today)
    except Exception:
        pass
    try:
        from antar_engine import rc_rules
        st = ctx.rc_state()
        for r in rc_rules.applying(st, "annual"):
            eff = (r.get("effect_es") if language == "es" else None) or r.get("effect")
            out["rules"].append({"rule_id": r.get("id"), "tone": r.get("tone"), "text": eff})
    except Exception:
        pass
    return out


def week(ctx, language: str = "en", days: int = 7, start: Optional[date] = None) -> dict:
    start = start or ctx.today
    moon = ctx.planets.get("Moon")
    vim = {"periods_now": ctx.periods_at(start), "gochara": None}
    if moon is not None:
        vim["gochara"] = gochara.outlook(moon.sign, start, days, language)
    return {"start": start.isoformat(), "days": days,
            "vimshottari": vim,
            "jaimini": _book_lines(ctx, start, days, language),
            "lal_kitab": _lk_line(ctx, language)}
