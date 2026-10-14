"""
KP timing line for 'when will X happen' (INTERNAL, behind the `kp_when` app_config flag: 'off' | 'all' | chart ids).
Windows = days when the sub and sub-sub period lords (strong significators of the matter's houses) both signify it AND the
transit gate confirms, merged into date ranges. The KP promise test (11th/primary cusp sub lord) is NOT a veto: it comes back
as a confidence level ('strong' / 'partial' / 'weak') next to the windows.
"""
from datetime import date
from typing import Dict, List, Optional

SUBJECT_TO_QUESTION = {"marriage": "marriage", "love": "romance", "money": "money", "funding": "deal_closes", "career": "promotion",
                       "job": "job_new", "business": "deal_closes", "children": "childbirth", "education": "education",
                       "property": "property", "foreign": "foreign_travel", "speculation": "speculation"}
HORIZON_DAYS = 730
MAX_WINDOWS = 8
STEP = 3.0


def enabled_for(supabase, chart_id: str) -> bool:
    try:
        from antar_engine import app_config
        v = str(app_config.get(supabase, "kp_when", "off")).strip().lower()
    except Exception:
        return False
    if v in ("", "off", "false", "0"):
        return False
    return v in ("all", "on") or str(chart_id).lower() in {x.strip() for x in v.split(",")}


def windows(chart: dict, subject: str, today: Optional[date] = None) -> Optional[dict]:
    import swisseph as swe
    from antar_engine.kp import kp_timing as kt, kp_significators as ks
    q = SUBJECT_TO_QUESTION.get(subject)
    spec = ks.QUESTION_TYPES.get(q) if q else None
    if not spec:
        return None
    favour, against = set(spec["favour"]), set(spec["against"])
    sigs = {p for p in ks.ALL_PLANETS if kt._net_positive(chart, p, favour, against)}
    today = today or date.today()
    start = swe.julday(today.year, today.month, today.day, 12.0)
    periods = kt.build_timeline(chart, start + HORIZON_DAYS + 400.0)
    spans, st, last, j = [], None, None, start
    while j <= start + HORIZON_DAYS:
        if kt._combined_pass(periods, sigs, j, "ad_pd", True):
            if st is not None and j - last > 12.0:           # gap > 12 days: a new window
                spans.append((st, last + STEP))
                st = None
            st = j if st is None else st
            last = j
        j += STEP
    if st is not None:
        spans.append((st, last + STEP))
    out = []
    for a, b in spans[:MAX_WINDOWS]:
        ya, ma, da = swe.revjul(a)[:3]
        yb, mb, db = swe.revjul(b)[:3]
        out.append({"start": date(ya, ma, da).isoformat(), "end": date(yb, mb, db).isoformat()})
    v = ks.verdict(chart, q)
    promise = {"yes": "strong", "conditional": "partial"}.get(v["verdict"], "weak")
    return {"windows": out, "promise": promise}
