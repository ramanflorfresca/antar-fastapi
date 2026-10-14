"""
Build antar_engine/data/raman_combinations_rules.json from the two reader outputs
(DATA_combo_rules_{A,B}_*.json: B.V. Raman's Part I combinations 1-162 written as machine-checkable clauses, with
plain-language effects in English and Spanish) and DATA_raman_300_combinations_*.json (names, internal use only).
Fixed steps: drop editor-dropped entries; drop any rule with an unparsed clause; drop sentences that name a planet,
use technical words, or carry a character label; drop exact duplicates.
Usage: python scripts/build_combo_rules.py [data_dir]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.build_rc_rules import PLANET_RE, JARGON_RE, LABEL_RE   # same filters as the Lal Kitab build


def build(data_dir):
    names = {r["n"]: r["name"] for r in json.load(open(os.path.join(data_dir, "DATA_raman_300_combinations_2026-10-13.json")))}
    raw = []
    for x in "AB":
        raw += json.load(open(os.path.join(data_dir, f"DATA_combo_rules_{x}_2026-10-13.json")))["rules"]
    st = {"raw": len(raw)}
    out, seen = [], set()
    for r in raw:
        if r.get("drop") or not (r.get("effect_en") or "").strip():
            st["dropped_by_editor"] = st.get("dropped_by_editor", 0) + 1
            continue
        if any("unparsed" in c for c in r.get("requires", [])) or not r.get("requires"):
            st["dropped_unparsed_or_empty"] = st.get("dropped_unparsed_or_empty", 0) + 1
            continue
        en, es = r["effect_en"].strip(), (r.get("effect_es") or "").strip()
        if PLANET_RE.search(en) or JARGON_RE.search(en) or LABEL_RE.search(en):
            st["dropped_wording"] = st.get("dropped_wording", 0) + 1
            continue
        if es and PLANET_RE.search(es):
            es = ""
        key = (json.dumps(r["requires"], sort_keys=True), en)
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": r["id"], "n": r["n"], "name": names.get(r["n"]), "requires": r["requires"], "tone": r["tone"],
                    "topics": r.get("topics") or ["other"], "effect": en, "effect_es": es or None,
                    "clarity": r.get("clarity", "clear")})
    st["final"] = len(out)
    return out, st


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/antarai/Antar.world")
    rules, stats = build(data_dir)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "antar_engine", "data",
                       "raman_combinations_rules.json")
    json.dump({"source": "B.V. Raman, Three Hundred Important Combinations, Part I (1-162), decomposed 2026-10-13",
               "rules": rules}, open(out, "w"), indent=0, ensure_ascii=False)
    print(json.dumps(stats, indent=1))
