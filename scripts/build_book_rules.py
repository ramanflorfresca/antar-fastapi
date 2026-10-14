"""
Merge the reader outputs RULES_book_*_2026-10-13.json (one per book or book group, written to
Antar.world/BOOK_RULES_SPEC_2026-10-13.md) into the shipped rule files:
  antar_engine/data/book_rules.json        rules read in the ordinary chart (Parashari/Jaimini), natal and timed
  antar_engine/data/book_rules_kp.json     rules with a KP frame (own evaluator, internal until approved)
  antar_engine/data/book_rules_varsha.json rules read in the solar-return (Tajaka) chart (own evaluator)
Fixed filters: editor-dropped; no effect text; any unparsed clause; effect naming a planet or using technical words or a
character label; exact duplicates; same-topic good/bad contradictions under identical conditions are removed.
Usage: python scripts/build_book_rules.py [data_dir]
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.build_rc_rules import PLANET_RE, JARGON_RE, LABEL_RE

KEEP = ("id", "book", "requires", "activation", "tone", "topics", "effect", "effect_es", "remedy", "remedy_es",
        "timing_note", "clarity", "line")


def _has(clauses, key):
    return any(key in c or key in json.dumps(c) for c in clauses)


def frame_of(rule):
    blob = json.dumps(rule.get("requires", [])) + json.dumps(rule.get("activation", []))
    if '"frame": "kp"' in blob:
        return "kp"
    if '"frame": "varsha"' in blob:
        return "varsha"
    return "main"


def build(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "RULES_book_*_2026-10-1[34].json")))
    st = {"files": len(files), "raw": 0}
    out = {"main": [], "kp": [], "varsha": []}
    seen = set()
    for f in files:
        book = os.path.basename(f)[len("RULES_book_"):-len("_2026-10-13.json")]       # both dates have the same length
        for r in json.load(open(f)).get("rules", []):
            st["raw"] += 1
            en = (r.get("effect_en") or "").strip()
            if r.get("drop") or not en:
                st["dropped_by_reader"] = st.get("dropped_by_reader", 0) + 1
                continue
            clauses = list(r.get("requires", [])) + list(r.get("activation", []))
            if any("unparsed" in json.dumps(c) for c in clauses):
                st["dropped_unparsed"] = st.get("dropped_unparsed", 0) + 1
                continue
            if PLANET_RE.search(en) or JARGON_RE.search(en) or LABEL_RE.search(en):
                st["dropped_wording"] = st.get("dropped_wording", 0) + 1
                continue
            if re.search(r"\bsuit(s)? (you|your)\b", en) and "," in en:  # industry lists: vertical study closed negative
                st["dropped_vertical_list"] = st.get("dropped_vertical_list", 0) + 1
                continue
            if re.search(r"pin down|for (about|around|nearly) [\w\- ]+ years", en, re.I):  # vague multi-year spans
                st["dropped_vague_span"] = st.get("dropped_vague_span", 0) + 1
                continue
            if not clauses:
                st["dropped_no_condition"] = st.get("dropped_no_condition", 0) + 1
                continue
            es = (r.get("effect_es") or "").strip()
            if es and PLANET_RE.search(es):
                es = ""
            rem = (r.get("remedy_en") or "").strip() or None
            rem_es = (r.get("remedy_es") or "").strip() or None
            if rem and (PLANET_RE.search(rem) or JARGON_RE.search(rem)):
                rem = rem_es = None
            acts = r.get("activation", [])
            if r.get("zodiac") == "tropical":          # Butaney: his positions are tropical; mark each clause so the engine uses them
                acts = [{**a, "zodiac": "tropical"} if any(k.startswith("transit_") for k in a) else a for a in acts]
            rule = {"id": r["id"], "book": book, "requires": r.get("requires", []), "activation": acts,
                    "tone": r.get("tone", "info"), "topics": r.get("topics") or ["other"], "effect": en,
                    "effect_es": es or None, "remedy": rem, "remedy_es": rem_es if rem else None,
                    "timing_note": r.get("timing_note"), "clarity": r.get("clarity", "clear"), "line": r.get("line")}
            key = (json.dumps(rule["requires"], sort_keys=True), json.dumps(rule["activation"], sort_keys=True), rule["tone"], en)
            if key in seen:
                st["duplicates"] = st.get("duplicates", 0) + 1
                continue
            seen.add(key)
            out[frame_of(r)].append(rule)
    # owner overrides survive rebuilds: antar_engine/data/rule_overrides.json {"overrides": {id: {drop|effect|effect_es|tone|topics|remedy|remedy_es}}}
    ov_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "antar_engine", "data", "rule_overrides.json")
    try:
        ov = json.load(open(ov_path)).get("overrides", {})
    except Exception:
        ov = {}
    if ov:
        n_drop = n_edit = 0
        for fr in out:
            kept = []
            for r in out[fr]:
                o = ov.get(r["id"])
                if o and o.get("drop"):
                    n_drop += 1
                    continue
                if o:
                    r = {**r, **{k: v for k, v in o.items() if k in ("effect", "effect_es", "tone", "topics", "remedy", "remedy_es")}}
                    n_edit += 1
                kept.append(r)
            out[fr] = kept
        st["overrides_dropped"], st["overrides_edited"] = n_drop, n_edit
    # same conditions + same topic + good AND bad = contradiction: remove that topic from the clashing rules
    for fr, rules in out.items():
        def gk(r):
            return (json.dumps(r["requires"], sort_keys=True), json.dumps(r["activation"], sort_keys=True))
        tones = {}
        for r in rules:
            for t in r["topics"]:
                tones.setdefault((gk(r), t), set()).add(r["tone"])
        clash = {k for k, v in tones.items() if {"good", "bad"} <= v}
        kept = []
        for r in rules:
            tp = [t for t in r["topics"] if (gk(r), t) not in clash or r["tone"] not in ("good", "bad")]
            if tp:
                kept.append({**r, "topics": tp})
        st[f"{fr}_contradictory_dropped"] = len(rules) - len(kept)
        out[fr] = kept
    for fr in out:
        st[f"{fr}_final"] = len(out[fr])
        st[f"{fr}_timed"] = sum(1 for r in out[fr] if r["activation"])
    return out, st


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/antarai/Antar.world")
    out, stats = build(data_dir)
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "antar_engine", "data")
    for name, fr in (("book_rules.json", "main"), ("book_rules_kp.json", "kp"), ("book_rules_varsha.json", "varsha")):
        json.dump({"source": "astrology library, decomposed 2026-10-13 (see BOOK_INVENTORY)", "rules": out[fr]},
                  open(os.path.join(base, name), "w"), indent=0, ensure_ascii=False)
    print(json.dumps(stats, indent=1))
