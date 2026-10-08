"""
antar_engine/circle_overlap.py - the "Between us" windows.

NO new astrology. For each topic and scale the topic engine already scans each chart and finds
its own dated runs (`topic_engine.windows_for`: every open run and every care run, never in the
past). A shared window is only ever the INTERSECTION of those two charts' runs:

    best overlap  =  (A's open runs)  intersect  (B's open runs)       both open
    care overlap  =  (A's care runs)  union      (B's care runs)       either needs care

Where nothing overlaps the page says so plainly; a window is never invented, stretched or
padded to look useful. Confidence is the LOWER of the two sides' own confidence, so a pair read
is never surer than its weaker half. A best overlap can never sit on a care day, because each day
of a chart is open OR care, never both.

Pure functions over dates (testable without a database) plus `record_joint`, which writes each
window shown as a claim for BOTH charts (source "circle_window") so the existing "did it hold?"
check-back (topic_checkback.py) asks each person separately.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from antar_engine import circle_copy as CC
from antar_engine import topic_copy as C

logger = logging.getLogger(__name__)

SCALES = ("month", "season")
MAX_PER_KIND = 3                      # windows listed per topic per kind
_RANK = {"low": 0, "medium": 1, "high": 2}
_NAME = {v: k for k, v in _RANK.items()}

Run = Tuple[date, date, str]          # (start, end, confidence)


def _lower(a: str, b: str) -> str:
    return _NAME[min(_RANK.get(a, 0), _RANK.get(b, 0))]


def _runs(lst) -> List[Run]:
    return sorted((r["start"], r["end"], r.get("confidence") or "low") for r in (lst or []))


def merge_adjacent(runs: List[Run]) -> List[Run]:
    """Join runs that overlap or touch (a day apart). Confidence of a joined run = the lowest."""
    out: List[Run] = []
    for s, e, c in sorted(runs):
        if out and (s - out[-1][1]).days <= 1:
            ps, pe, pc = out[-1]
            out[-1] = (ps, max(pe, e), _lower(pc, c))
        else:
            out.append((s, e, c))
    return out


def intersect(a: List[Run], b: List[Run]) -> List[Run]:
    """Days that fall inside a run of A AND a run of B."""
    out: List[Run] = []
    for s1, e1, c1 in a:
        for s2, e2, c2 in b:
            s, e = max(s1, s2), min(e1, e2)
            if s <= e:
                out.append((s, e, _lower(c1, c2)))
    return merge_adjacent(out)


def union(a: List[Run], b: List[Run]) -> List[Run]:
    return merge_adjacent(list(a) + list(b))


def shared_runs(wa: dict, wb: dict) -> dict:
    """{"best": [...], "care": [...]} for two `windows_for` results. Pure."""
    return {"best": intersect(_runs(wa.get("open")), _runs(wb.get("open"))),
            "care": union(_runs(wa.get("care")), _runs(wb.get("care")))}


# ── presentation ─────────────────────────────────────────────────────────────
def _range(s: date, e: date, lang: str, today: Optional[date] = None) -> str:
    # a window in another calendar year than today carries its year: "Jul 5 - Sep 2" would read as this July
    if s.year != e.year or (e - s).days >= 90 or (today and s.year != today.year):
        return f"{C.day_label_y(s, lang)} – {C.day_label_y(e, lang)}"
    return C.range_label(s, e, lang)


def _window(run: Run, kind: str, topic: str, scale: str, lang: str, today: Optional[date] = None) -> dict:
    s, e, conf = run
    area = C.pick(C.AREA, lang)[topic]
    B = CC.pick(CC.BULLET, lang)
    bullets = ([B["best_both"].format(area=area), B["best_overlap"]] if kind == "best"
               else [B["care_one"].format(area=area), B["care_why"]])
    view = "month" if scale == "month" else "chapter"
    return {
        "start": s.isoformat(), "end": e.isoformat(), "label": _range(s, e, lang, today),
        "days": (e - s).days + 1, "kind": kind,
        "reasoning": {
            "bullets": bullets,
            "based_on": [{"label": CC.pick(CC.BASED_ON_BOTH, lang), "view": view}],
            "confidence": {"level": conf, "note": C.pick(C.CONFIDENCE_NOTE, lang)[conf]},
        },
    }


def _pick(runs: List[Run]) -> List[Run]:
    """The earliest few; a long run is not worth more than a short one for 'when'."""
    return sorted(runs)[:MAX_PER_KIND]


def build_topic(topic: str, wa: dict, wb: dict, scale: str, lang: str, today: Optional[date] = None) -> dict:
    sr = shared_runs(wa, wb)
    best = [_window(r, "best", topic, scale, lang, today) for r in _pick(sr["best"])]
    care = [_window(r, "care", topic, scale, lang, today) for r in _pick(sr["care"])]
    area = C.pick(C.AREA, lang)[topic]
    span = CC.SPAN[scale].get(lang) or CC.SPAN[scale]["en"]
    if best:
        note = None
    elif care:
        note = CC.pick(CC.NONE_BEST, lang).format(area=area, span=span)
    else:
        note = CC.pick(CC.NONE_ALL, lang).format(span=span)
    return {"topic": topic, "label": C.LABEL[lang][topic], "scale": scale,
            "has_overlap": bool(best), "best": best, "care": care, "note": note}


def build_page(windows_a: Dict[str, dict], windows_b: Dict[str, dict], scale: str, lang: str,
               today: Optional[date] = None) -> dict:
    """{"topics": [...in the standard topic order], "headline": {...}} from two charts' per-topic
    `windows_for` results. A topic one side could not be scanned for is simply left out."""
    topics = []
    for t in C.TOPIC_KEYS:
        if t in windows_a and t in windows_b:
            topics.append(build_topic(t, windows_a[t], windows_b[t], scale, lang, today))
    firsts = [(w["start"], -w["days"], tp["topic"], w) for tp in topics for w in tp["best"][:1]]
    if firsts:
        _, _, topic, w = min(firsts)
        s, e = date.fromisoformat(w["start"]), date.fromisoformat(w["end"])
        text = CC.pick(CC.HEADLINE_BEST, lang).format(topic=C.LABEL[lang][topic].lower(), range=_range(s, e, lang, today))
        headline = {"text": text, "topic": topic, "window": w}
    else:
        headline = {"text": CC.pick(CC.HEADLINE_NONE, lang), "topic": None, "window": None}
    return {"topics": topics, "headline": headline}


# ── joint check-back claims ──────────────────────────────────────────────────
def window_id(pair_id: str, topic: str, scale: str, kind: str, s: str, e: str) -> str:
    return hashlib.sha1(f"{pair_id}|{topic}|{scale}|{kind}|{s}|{e}".encode()).hexdigest()[:16]


def joint_claim_rows(topics: List[dict], chart_id: str, pair_id: str, scale: str,
                     horizon: Optional[date], today: date, language: str = "en") -> List[dict]:
    """prediction_claims rows (source circle_window) for the shared windows on the page, for ONE
    of the two charts. Mirrors topic_checkback.build_claims: month/season only, never a window
    already over, never one running into a moving scan edge (that is a view of its start, not a
    window with a known end). Care windows are recorded with kind "watch" - the check-back
    vocabulary ("did the caution matter?")."""
    from antar_engine import topic_checkback as tcb
    if scale not in tcb.RECORDED_SCALES:
        return []
    rows = []
    for tp in topics:
        for key, kind in (("best", "best"), ("care", "watch")):
            for w in tp.get(key) or []:
                s, e = date.fromisoformat(w["start"]), date.fromisoformat(w["end"])
                if e < today or (horizon and e >= horizon):
                    continue
                rows.append({
                    "chart_id": chart_id, "source": tcb.CIRCLE_SOURCE, "topic": tp["topic"],
                    "claim_type": "window", "window_start": w["start"], "window_end": w["end"],
                    "text_shown": (w["reasoning"]["bullets"][0] if w.get("reasoning") else "")[:500] or None,
                    "language": language, "channel": "app",
                    "verdict": "open" if kind == "best" else "care",
                    "engines": {"topic_read": {
                        "kind": kind, "scale": scale, "tone": "open" if kind == "best" else "care",
                        "joint": True, "pair_id": pair_id,
                        "window_id": window_id(pair_id, tp["topic"], scale, kind, w["start"], w["end"])}},
                    "dedupe_key": f"{chart_id}|{pair_id}|{tp['topic']}|circle_window:{scale}:{kind}|{w['start']}|{w['end']}",
                    "checkin_due_at": datetime.combine(e + timedelta(days=tcb.DUE_AFTER_END_DAYS),
                                                       datetime.min.time(), tzinfo=timezone.utc).isoformat(),
                })
    return rows


def record_joint(sb, chart_ids: Tuple[str, str], pair_id: str, topics: List[dict], scale: str,
                 horizon: Optional[date], today: date, language: str = "en") -> int:
    """Record every shared window for BOTH charts. Idempotent and overlap-aware (see
    topic_checkback.write_new_claims). Never raises; never records on the demo chart."""
    from antar_engine import topic_checkback as tcb
    from antar_engine.outcomes import _table_missing
    wrote = 0
    try:
        for cid in chart_ids:
            if tcb.is_demo(sb, cid):
                continue
            rows = joint_claim_rows(topics, cid, pair_id, scale, horizon, today, language)
            if rows:
                wrote += tcb.write_new_claims(sb, cid, rows, tcb.CIRCLE_SOURCE)
    except Exception as e:
        if _table_missing(e):
            tcb._warn_once("missing", "[circle] prediction_claims not available yet - not recording shared windows")
        else:
            logger.warning("[circle] record_joint failed: %s", str(e)[:200])
    return wrote
