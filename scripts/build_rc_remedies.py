"""
Build antar_engine/data/lk_roop_chand_remedies.json from the two reader outputs (DATA_rc_remedies_{A,B}_*.json):
Pt. Roop Chand's remedies, each tied to the chart condition it treats, in plain English and Spanish.
Fixed filters: editor-dropped, unparsed condition, no steps, steps naming a planet or technical word, character labels.
Usage: python scripts/build_rc_remedies.py [data_dir]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.build_rc_rules import PLANET_RE, JARGON_RE, LABEL_RE


def build(data_dir):
    raw = []
    for x in "AB":
        raw += json.load(open(os.path.join(data_dir, f"DATA_rc_remedies_{x}_2026-10-13.json")))["remedies"]
    st, out, seen = {"raw": len(raw)}, [], set()
    for r in raw:
        steps = [s.strip() for s in r.get("steps_en") or [] if s and s.strip()]
        steps_es = [s.strip() for s in r.get("steps_es") or [] if s and s.strip()]
        if r.get("drop") or not steps or not (r.get("problem_en") or "").strip():
            st["dropped_by_editor_or_empty"] = st.get("dropped_by_editor_or_empty", 0) + 1
            continue
        if any("unparsed" in c for c in r.get("requires", [])):
            st["dropped_unparsed"] = st.get("dropped_unparsed", 0) + 1
            continue
        blob = " ".join(steps + [r["problem_en"]])
        if PLANET_RE.search(blob) or JARGON_RE.search(blob) or LABEL_RE.search(blob):
            st["dropped_wording"] = st.get("dropped_wording", 0) + 1
            continue
        key = (json.dumps(r["requires"], sort_keys=True), tuple(steps))
        if key in seen:
            continue
        seen.add(key)
        ok_es = steps_es and len(steps_es) == len(steps) and not PLANET_RE.search(" ".join(steps_es))
        out.append({"id": r["id"], "line": r.get("line"), "requires": r["requires"], "topics": r.get("topics") or [],
                    "problem": r["problem_en"].strip(), "problem_es": (r.get("problem_es") or "").strip() or None,
                    "steps": steps, "steps_es": steps_es if ok_es else None,
                    "duration": (r.get("duration_en") or None), "duration_es": (r.get("duration_es") or None)})
    st["final"] = len(out)
    return out, st


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/antarai/Antar.world")
    rem, stats = build(data_dir)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "antar_engine", "data",
                       "lk_roop_chand_remedies.json")
    json.dump({"source": "Pt. Roop Chand Joshi, Text Book of Lal Kitab: remedies, decomposed 2026-10-13",
               "remedies": rem}, open(out, "w"), indent=0, ensure_ascii=False)
    print(json.dumps(stats, indent=1))
