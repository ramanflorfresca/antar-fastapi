#!/usr/bin/env python3
"""
scripts/dump_real_chronology.py
===============================
One-shot: dump the REAL sidereal Jupiter+Saturn+Mars sign chronology
(1960-2036) to Antar.world/real_chronology_1960_2036.json so the convergence
engine can be iterated in environments without swisseph (the Cowork sandbox
cannot install pyswisseph — calibration there needs the true sky).

Run on the Mac:
  cd ~/antarai && source venv311/bin/activate
  python scripts/dump_real_chronology.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from antar_engine.transit_engine import build_transit_chronology  # noqa: E402

OUT = os.path.join(ROOT, "Antar.world", "real_chronology_1960_2036.json")


def main():
    chrono = build_transit_chronology(
        "1960-01-01", "2036-01-01",
        planets=("Jupiter", "Saturn", "Mars"), step_days=5)
    for planet, segs in chrono.items():
        print(f"{planet}: {len(segs)} segments "
              f"({segs[0]['start']} → {segs[-1]['end']})")
    with open(OUT, "w") as f:
        json.dump(chrono, f)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
