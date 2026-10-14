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

from antar_engine import book_rules, combo_rules as cb, rule_registry as rr, weekly_layer as wl
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


def mechanisms(rule: dict) -> frozenset:
    """Independent timing signals a rule is activated by: running periods, transits, age-year cycle."""
    blob = json.dumps(rule.get("activation", []))
    m = set()
    if '"dasha"' in blob:
        m.add("dasha")
    if '"transit"' in blob or '"transit_conj"' in blob:
        m.add("transit")
    if '"age_year"' in blob:
        m.add("age")
    return frozenset(m)


def _drop_conflicts(spans: Dict[str, dict], by_id: dict) -> set:
    """Rules that fire together under the same timing condition and topic but point opposite ways: keep the clearly more
    specific tone, and drop both when it is a tie (the book is not telling us which)."""
    groups: Dict[tuple, list] = {}
    for rid, sp in spans.items():
        ev = sp["ev"]
        rule = by_id.get(rid[3:] if rid.startswith("BK.") else rid) or {}
        if ev.tone not in ("good", "bad") or not rule.get("activation"):
            continue
        spec = len(rule.get("requires", [])) + len(rule.get("activation", []))
        key = (json.dumps(rule["activation"], sort_keys=True), tuple(sorted(ev.subjects or ["other"])))
        groups.setdefault(key, []).append((ev.tone, spec, rid))
    drop = set()
    for rows in groups.values():
        tones = {t for t, _, _ in rows}
        if tones == {"good", "bad"}:
            top = max(spec for _, spec, _ in rows)
            winners = {t for t, spec, _ in rows if spec == top}
            for t, spec, rid in rows:
                if len(winners) > 1 or t not in winners:
                    drop.add(rid)
    return drop


def _agree(ctx, pool: dict, start: date, horizon: int, lang: str) -> list:
    """Topics where independent timing signals (running periods, transits, the Lal Kitab year) all favour the same
    topic in overlapping windows. Rules sharing one signal count once; a single signal is never 'agreement'."""
    from antar_engine import rc_rules
    by_subj: Dict[str, list] = {}
    for (line, tone, subj), items in pool.items():
        if tone == "good":
            by_subj.setdefault(subj, []).extend(items)
    try:
        lk = [r for r in rc_rules.applying(ctx.rc_state(), "annual") if r.get("tone") == "good"]
    except Exception:
        lk = []
    end = start + timedelta(days=horizon)
    out = []
    for subj, items in by_subj.items():
        if subj not in rr.SUBJECTS:
            continue
        sigs = {}
        for it in items:
            for m in it["_mech"]:
                sigs.setdefault(m, []).append(it)
        if any(subj in rc_rules.subjects_of(r) for r in lk):
            sigs["lal_kitab_year"] = []
        if len(sigs) < 2:
            continue
        starts = [date.fromisoformat(i["start"]) for v in sigs.values() for i in v]
        ends = [date.fromisoformat(i["end"]) for v in sigs.values() for i in v]
        lo, hi = max(starts + [start]), min(ends + [end])
        if sigs.get("dasha") and sigs.get("transit"):       # windows must overlap between the dated signals
            a = max(min(date.fromisoformat(i["start"]) for i in sigs["dasha"]), min(date.fromisoformat(i["start"]) for i in sigs["transit"]))
            b = min(max(date.fromisoformat(i["end"]) for i in sigs["dasha"]), max(date.fromisoformat(i["end"]) for i in sigs["transit"]))
            if a > b:
                continue
            lo, hi = a, b
        label = rr.SUBJECTS[subj]["label"][lang]
        text = (f"Independent signals point the same way on {label}." if lang == "en"
                else f"Señales independientes apuntan en la misma dirección en {label}.")
        out.append({"subject": subj, "signals": sorted(sigs), "text": text, "start": lo.isoformat(), "end": max(lo, hi).isoformat()})
    out.sort(key=lambda r: (-len(r["signals"]), r["start"]))
    seen, uniq = set(), []
    for r in out:                       # love / marriage and similar twins share one line
        k = (tuple(r["signals"]), r["start"], r["end"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq[:3]


def build(ctx, months: int = 6, language: str = "en", start: Optional[date] = None) -> dict:
    lang = "es" if language == "es" else "en"
    start = start or ctx.today
    by_id = {r["id"]: r for r in book_rules.load_rules()}
    spans = _spans(ctx, start, int(months * 30.4))
    out = {"vimshottari": {"lean_in": [], "watch": []}, "jaimini": {"lean_in": [], "watch": []}}
    conflicts = _drop_conflicts(spans, by_id)
    best: Dict[tuple, dict] = {}
    pool: Dict[tuple, list] = {}
    for rid, sp in spans.items():
        ev = sp["ev"]
        rule = by_id.get(rid[3:] if rid.startswith("BK.") else rid) or {}
        if ev.tone not in ("good", "bad") or rid in conflicts or cb.is_impersonal(rule):
            continue                                      # impersonal (same for everyone) rules answer speculation questions only
        line = line_of(rule)
        spec = len(rule.get("requires", [])) + len(rule.get("activation", []))
        text = ev.plain.get(lang) or ev.plain.get("en")
        item = {"rule_id": rid, "source": ev.book, "text": text, "start": sp["start"].isoformat(),
                "end": sp["end"].isoformat(), "label": _fmt(lang, sp["start"].isoformat(), sp["end"].isoformat()),
                "_spec": spec, "_subjects": ev.subjects, "_mech": mechanisms(rule),
                "_rank": (1 if ev.precision == "specific" else 0, spec), "tendency": ev.precision != "specific"}
        if ev.tone == "bad":
            act = wl._action(ev.subjects, ev.remedy, lang)
            if not act:
                continue                                  # a caution with nothing to do is hidden
            item["do"] = act
        for subj in (ev.subjects or ["other"]):
            k = (line, ev.tone, subj)
            pool.setdefault(k, []).append(item)
            if k not in best or (item["_rank"], -sp["start"].toordinal()) > (best[k]["_rank"], -date.fromisoformat(best[k]["start"]).toordinal()):
                best[k] = item
    shown = {}
    for (line, tone, subj), item in sorted(best.items(), key=lambda kv: (-kv[1]["_rank"][0], -kv[1]["_rank"][1], kv[1]["start"])):
        block = out[line]["lean_in" if tone == "good" else "watch"]
        if item["rule_id"] in shown or len(block) >= MAX_PER_BLOCK:
            continue
        shown[item["rule_id"]] = item
        others = {i["rule_id"] for i in pool[(line, tone, subj)]} - {item["rule_id"]}
        block.append({**{k: v for k, v in item.items() if not k.startswith("_")}, "subject": subj, "more": len(others)})
    out["agree"] = _agree(ctx, pool, start, int(months * 30.4), lang)
    for line in ("vimshottari", "jaimini"):
        for blk in out[line].values():
            blk.sort(key=lambda i: i["start"])
    out["wellness"] = wellness(ctx, start, min(int(months * 30.4), 150), language)
    out["horizon"] = [start.isoformat(), (start + timedelta(days=int(months * 30.4))).isoformat()]
    return out


WELLNESS_LINE = {"en": "These are themes to look after, not a diagnosis, and not a substitute for medical care. If something worries you, book a check-up.",
                 "es": "Son temas de cuidado, no un diagnóstico ni un sustituto de la atención médica. Si algo te preocupa, agenda un chequeo."}
MAX_WELLNESS = 3


def wellness(ctx, start: Optional[date] = None, horizon_days: int = 120, language: str = "en") -> dict:
    """Health care themes that apply to this chart now or in the coming weeks/months (Chatterjee and any rule with the
    health topic). Timed rules whose period is running or about to begin come first, then standing themes. Each carries
    the book's own remedy (diet, habit, ritual) when it has one. Never a diagnosis; the care line is always attached."""
    lang = "es" if language == "es" else "en"
    start = start or ctx.today
    by_id = {r["id"]: r for r in book_rules.load_rules()}
    items, seen_text = [], set()
    spans = _spans(ctx, start, horizon_days)
    for rid, sp in spans.items():
        ev = sp["ev"]
        if "health" not in (ev.subjects or []):
            continue
        text = ev.plain.get(lang) or ev.plain.get("en")
        if text in seen_text:
            continue
        seen_text.add(text)
        rule = by_id.get(rid[3:] if rid.startswith("BK.") else rid) or {}
        items.append({"rule_id": rid, "source": ev.book, "text": text, "start": sp["start"].isoformat(), "end": sp["end"].isoformat(),
                      "label": _fmt(lang, sp["start"].isoformat(), sp["end"].isoformat()), "timing": "now" if sp["start"] <= start else "soon",
                      "remedy": (ev.remedy or {}).get(lang) or (ev.remedy or {}).get("en"), "_s": len(rule.get("requires", []))})
    for ev in rr._book_family(ctx):
        if "health" not in (ev.subjects or []):
            continue
        text = ev.plain.get(lang) or ev.plain.get("en")
        if text in seen_text:
            continue
        seen_text.add(text)
        items.append({"rule_id": ev.rule_id, "source": ev.book, "text": text, "start": None, "end": None, "label": None, "timing": "standing",
                      "remedy": (ev.remedy or {}).get(lang) or (ev.remedy or {}).get("en"), "_s": 0})
    order = {"now": 0, "soon": 1, "standing": 2}
    items.sort(key=lambda i: (order[i["timing"]], -i["_s"], bool(i["remedy"]) is False))
    # show distinct habits: a theme whose habit another shown theme already carries is held back (or, if nothing else is left,
    # shown without repeating the habit)
    chosen, held, used = [], [], set()
    for i in items:
        r = i.get("remedy")
        if r and r in used:
            held.append(i)
        else:
            if r:
                used.add(r)
            chosen.append(i)
    chosen = chosen[:MAX_WELLNESS]
    for i in held:
        if len(chosen) >= MAX_WELLNESS:
            break
        chosen.append({**i, "remedy": None})
    top = [{k: v for k, v in i.items() if k != "_s"} for i in chosen]
    return {"themes": top, "more": max(0, len(items) - len(top)), "note": WELLNESS_LINE[lang]}
