"""
Combined 'when will X happen': independent timing signals laid on one calendar.
  timing_methods : the Jaimini + Parashari + D-10 windows from the reading (counts as 2 when both agree, else 1)
  kp             : KP period + transit windows (internal flag; supplied by the caller)
  lal_kitab_year : the running Lal Kitab year, when a favourable annual rule for the subject applies
A date range is headlined only where at least two independent signals overlap; single-signal ranges stay in `also`.
The KP promise test is shown as a confidence level, never as a veto.
"""
from datetime import date, timedelta
from typing import Dict, List, Optional

from antar_engine import rule_registry as rr, rc_rules


def _d(s: str) -> date:
    s = str(s)[:10]
    return date.fromisoformat(s if len(s) == 10 else (s + "-01" if len(s) == 7 else s + "-01-01"))


def _lk_year(ctx, subject: str) -> Optional[tuple]:
    try:
        if not ctx.birth_date:
            return None
        rules = [r for r in rc_rules.applying(ctx.rc_state(), "annual") if r.get("tone") == "good" and subject in rc_rules.subjects_of(r)]
        if not rules:
            return None
        b = _d(ctx.birth_date)
        yr = ctx.today.year - ((ctx.today.month, ctx.today.day) < (b.month, b.day))
        a = date(yr, b.month, min(b.day, 28))
        return a, date(yr + 1, b.month, min(b.day, 28))
    except Exception:
        return None


NAMES = {"en": {"timing_methods": "timing methods", "kp": "KP periods", "lal_kitab_year": "Lal Kitab year"},
         "es": {"timing_methods": "métodos de tiempo", "kp": "periodos KP", "lal_kitab_year": "año de Lal Kitab"}}


def build(ctx, subject: str, lang: str = "en", kp: Optional[dict] = None, horizon_months: int = 24) -> dict:
    lang = "es" if lang == "es" else "en"
    end_h = ctx.today + timedelta(days=int(horizon_months * 30.4))
    spans = []                                    # (line, weight, start, end)
    for w in rr._windows(ctx, subject, lang):
        spans.append(("timing_methods", 2 if w.get("both_systems") else 1, _d(w["start"]), _d(w["end"])))
    if kp:
        for w in kp.get("windows", []):
            spans.append(("kp", 1, _d(w["start"]), _d(w["end"])))
    lk = _lk_year(ctx, subject)
    if lk:
        spans.append(("lal_kitab_year", 1, lk[0], lk[1]))
    cuts = sorted({max(ctx.today, min(end_h, x)) for _, _, a, b in spans for x in (a, b)})
    segs = []
    for i in range(len(cuts) - 1):
        a, b = cuts[i], cuts[i + 1]
        if a >= b:
            continue
        mid = a + (b - a) / 2
        on = [(ln, wt) for ln, wt, s, e in spans if s <= mid <= e]
        if not on:
            continue
        lines = sorted({ln for ln, _ in on})
        signals = sum(max(wt for l2, wt in on if l2 == ln) for ln in lines)
        if segs and segs[-1]["lines"] == lines and segs[-1]["end"] == a:
            segs[-1]["end"] = b
        else:
            segs.append({"start": a, "end": b, "lines": lines, "signals": signals})
    names = NAMES[lang]
    out = []
    for s in segs:
        out.append({"start": s["start"].isoformat(), "end": s["end"].isoformat(), "signals": s["signals"],
                    "lines": s["lines"], "line_names": [names[l] for l in s["lines"]],
                    "strength": "strong" if s["signals"] >= 3 else "good" if s["signals"] == 2 else "possible"})
    # contiguous stretches with >= 2 signals become ONE range; the sub-ranges with the most signals are its peaks
    agree, cur = [], None
    for w in out:
        if w["signals"] >= 2:
            if cur and cur["end"] == w["start"]:
                cur["end"] = w["end"]
                cur["_segs"].append(w)
            else:
                cur = {"start": w["start"], "end": w["end"], "_segs": [w]}
                agree.append(cur)
        else:
            cur = None
    for a in agree:
        def _len(x):
            return (date.fromisoformat(x["end"]) - date.fromisoformat(x["start"])).days
        top = max(x["signals"] for x in a["_segs"])
        peaks = [x for x in a["_segs"] if x["signals"] == top]
        # a peak shorter than two weeks is shown but does not lift the whole range's strength
        sustained = [x["signals"] for x in a["_segs"] if _len(x) >= 14]
        a["signals"] = max(sustained) if sustained else min(top, 2)
        a["lines"] = sorted({l for x in a["_segs"] for l in x["lines"]})
        a["line_names"] = [names[l] for l in a["lines"]]
        a["strength"] = "strong" if a["signals"] >= 3 else "good"
        a["peaks"] = [{"start": x["start"], "end": x["end"]} for x in peaks] if top > min(x["signals"] for x in a["_segs"]) else []
        del a["_segs"]
    also = [w for w in out if w["signals"] < 2]
    return {"agree": agree, "also": also, "kp_promise": (kp or {}).get("promise"), "kp_on": bool(kp)}
