"""
python -m antar_engine.profession.selftest

Smoke test on a synthetic chart (pure longitude math — no Swiss Ephemeris).
Runs the full read with require_gate=False (so the quarantined engine still
computes) + include_evidence=True, and asserts the contract:
  * one archetype, 3-4 arenas
  * arenas traceable to D10 / AmK-house / Karakamsa
  * NO jargon on the surface
  * gate is CLOSED by default (is_gate_open() == False)
"""

import json

from .profession_service import get_profession_read
from .profession_gate import is_gate_open

# A synthetic but internally-consistent chart_data (Capricorn lagna).
CHART = {
    "lagna": {"sign": "Capricorn", "degree": 10.0},
    "planets": {
        "Sun":     {"sign": "Aries",       "degree": 10.0, "longitude": 10.0},   # exalted
        "Moon":    {"sign": "Taurus",      "degree": 3.0,  "longitude": 33.0},   # exalted
        "Mars":    {"sign": "Capricorn",   "degree": 28.0, "longitude": 298.0},  # exalted, high deg
        "Mercury": {"sign": "Gemini",      "degree": 22.0, "longitude": 82.0},   # own
        "Jupiter": {"sign": "Cancer",      "degree": 5.0,  "longitude": 95.0},   # exalted
        "Venus":   {"sign": "Pisces",      "degree": 14.0, "longitude": 344.0},  # exalted
        "Saturn":  {"sign": "Libra",       "degree": 19.0, "longitude": 199.0},  # exalted
        "Rahu":    {"sign": "Gemini",      "degree": 8.0,  "longitude": 68.0},
        "Ketu":    {"sign": "Sagittarius", "degree": 8.0,  "longitude": 248.0},
    },
}


def main():
    assert is_gate_open() is False, "gate must default CLOSED"

    # gated path surfaces nothing
    gated = get_profession_read(CHART, require_gate=True)
    assert gated.get("eligible") is False, "gated read must be ineligible while closed"
    print("[1/6] gate closed -> read ineligible  OK")

    r = get_profession_read(CHART, include_evidence=True, require_gate=False)
    assert r.get("eligible") is True
    print("[2/6] ungated read eligible  OK")

    arch = r["archetype"]
    assert arch.get("name"), "archetype must have a name"
    print(f"[3/6] archetype = {arch['name']} ({arch['tagline']})  OK")

    arenas = r["arenas"]
    assert 3 <= len(arenas) <= 4, f"expected 3-4 arenas, got {len(arenas)}"
    print(f"[4/6] {len(arenas)} arenas  OK")
    for a in arenas:
        print(f"        - {a['label']}  (why: {a['why']})")

    sources = {f["source"] for f in r["evidence"]["arena_factors"]}
    assert {"D10", "AmK-house", "Karakamsa"} <= sources, \
        f"arenas must trace to all three sources, got {sources}"
    print(f"[5/6] arenas traceable to sources {sorted(sources)}  OK")

    assert r["_jargon_clean"] is True, "surface leaked jargon!"
    print("[6/6] no jargon on surface  OK")

    print("\n--- evidence (internal) ---")
    ev = r["evidence"]
    print("dominant:", ev["dominant_planet"],
          "| conviction:", r["conviction"],
          "| dignity_pts:", ev["dignity_points"], ev["dignity_where"],
          "| converged sources:", ev["dominant_sources"])
    print("AmK house:", ev["amk"]["d1_house"], "->", ev["amk"]["family_text"])
    print("Karakamsa:", ev["karakamsa"]["sign"],
          "| 10th-from:", ev["karakamsa"]["tenth_from_sign"])
    print("\nALL PROFESSION SELFTESTS PASSED")


if __name__ == "__main__":
    main()
