"""
Library rules in the reading: the timed book rules (K.N. Rao, B.V. Raman, classical) that hold in this chart, laid out as
date windows across the reading horizon and split into two separately labelled lines:
  jaimini     rules that read karakas, arudha points (AL/UL/A7/KL) or sign aspects
  vimshottari everything else (house/lord/dasha/transit rules)
The Lal Kitab line stays in the composer's `year` block and the remedy calendar. For each line and topic only the most
specific rule per tone is shown (the rest are counted under `more`); a caution is shown only with a next step.
Deterministic, no LLM, silent where nothing applies.
"""
import json
from datetime import date, timedelta
from typing import Dict, List, Optional

from antar_engine import book_rules, rule_registry as rr, weekly_layer as wl
from antar_engine.reading_composer import _fmt

JAIMINI_KEYS = ('"AK"', '"AmK"', '"BK"', '"MK"', '"PK"', '"GK"', '"DK"', '"AL"', '"UL"', '"A7"', '"KL"', '"touches"')
STEP_DAYS = 15
MAX_PER_BLOCK = 4


def line_of(rule: dict) -> str:
    blob = json.dumps(rule.get("requires", []))
    return "jaimini" if any(k in blob for k in JAIMINI_KEYS) else "vimshottari"


def _spans(ctx, start: date, horizon_days: int) -> Dict[str, dict]:
    """rule_id -> {'ev': Evidence, 'start': date, 'end': date}; contiguous samples merge into one window."""
    seen: Dict[str, dict] = {}
    d, end = start, start + timedelta(days=horizon_days)
    while d <= end:
        for ev in rr.timed_book_evidence(ctx, d):
            row = seen.get(ev.rule_id)
            last = min(d + timedelta(days=STEP_DAYS - 1), end)
            if row and (d - row["end"]).days <= STEP_DAYS:
                row["end"] = last
            elif row is None:
                seen[ev.rule_id] = {"ev": ev, "start": d, "end": last}
            else:                                        # a second, separate window of the same rule: keep the earliest
                continue
        d += timedelta(days=STEP_DAYS)
    return seen


def build(ctx, months: int = 6, language: str = "en", start: Optional[date] = None) -> dict:
    lang = "es" if language == "es" else "en"
    start = start or ctx.today
    by_id = {r["id"]: r for r in book_rules.load_rules()}
    spans = _spans(ctx, start, int(months * 30.4))
    out = {"vimshottari": {"lean_in": [], "watch": []}, "jaimini": {"lean_in": [], "watch": []}}
    best: Dict[tuple, dict] = {}
    pool: Dict[tuple, list] = {}
    for rid, sp in spans.items():
        ev = sp["ev"]
        rule = by_id.get(rid[3:] if rid.startswith("BK.") else rid) or {}
        if ev.tone not in ("good", "bad"):
            continue
        line = line_of(rule)
        spec = len(rule.get("requires", [])) + len(rule.get("activation", []))
        text = ev.plain.get(lang) or ev.plain.get("en")
        item = {"rule_id": rid, "source": ev.book, "text": text, "start": sp["start"].isoformat(),
                "end": sp["end"].isoformat(), "label": _fmt(lang, sp["start"].isoformat(), sp["end"].isoformat()),
                "_spec": spec, "_subjects": ev.subjects}
        if ev.tone == "bad":
            act = wl._action(ev.subjects, ev.remedy, lang)
            if not act:
                continue                                  # a caution with nothing to do is hidden
            item["do"] = act
        for subj in (ev.subjects or ["other"]):
            k = (line, ev.tone, subj)
            pool.setdefault(k, []).append(item)
            if k not in best or (spec, -sp["start"].toordinal()) > (best[k]["_spec"], -date.fromisoformat(best[k]["start"]).toordinal()):
                best[k] = item
    shown = {}
    for (line, tone, subj), item in sorted(best.items(), key=lambda kv: (-kv[1]["_spec"], kv[1]["start"])):
        block = out[line]["lean_in" if tone == "good" else "watch"]
        if item["rule_id"] in shown or len(block) >= MAX_PER_BLOCK:
            continue
        shown[item["rule_id"]] = item
        others = {i["rule_id"] for i in pool[(line, tone, subj)]} - {item["rule_id"]}
        block.append({**{k: v for k, v in item.items() if not k.startswith("_")}, "subject": subj, "more": len(others)})
    for line in out.values():
        for blk in line.values():
            blk.sort(key=lambda i: i["start"])
    out["horizon"] = [start.isoformat(), (start + timedelta(days=int(months * 30.4))).isoformat()]
    return out
