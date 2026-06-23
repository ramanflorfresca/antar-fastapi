"""
verify_a1.py — A1 acceptance runner. RUN ON THE MAC VENV (has Swiss Ephemeris):

    cd ~/antarai && source venv311/bin/activate
    python -m antar_engine.kp.verify_a1

For each reference chart it prints the computed 12 cuspal sub-lords (+ ascendant)
and, if expected_cusp_sublords is filled in kp_reference_charts.json, reports
match/mismatch per cusp. Pure read-only; touches nothing else.
"""

import os
import json

from .kp_chart import compute_kp_chart

_HERE = os.path.dirname(os.path.abspath(__file__))
REF_PATH = os.path.join(_HERE, "validation", "kp_reference_charts.json")


def main():
    with open(REF_PATH) as f:
        ref = json.load(f)

    print(f"Ayanamsa: {ref.get('ayanamsa')}  Node: {ref.get('node')}\n")
    for c in ref["charts"]:
        if not c.get("birth_date"):
            continue
        print("=" * 64)
        print(c["name"])
        chart = compute_kp_chart(c["birth_date"], c["birth_time"],
                                 c["lat"], c["lon"], tz_offset=c["tz_offset"])
        asc = chart["ascendant"]
        print(f"  ASC {asc['longitude']:.3f} {asc['sign']} "
              f"(sub-lord {asc['sub_lord']})  ayan={chart['ayanamsa_value']}")
        expected = c.get("expected_cusp_sublords")
        for h in range(1, 13):
            cu = chart["cusps"][h]
            line = (f"  H{h:>2}: {cu['longitude']:7.3f} {cu['sign']:<11} "
                    f"sub={cu['sub_lord']:<8}")
            if isinstance(expected, dict) and str(h) in expected:
                exp = expected[str(h)]
                ok = "MATCH" if exp == cu["sub_lord"] else f"MISMATCH (exp {exp})"
                line += "  " + ok
            print(line)
        print()


if __name__ == "__main__":
    main()
