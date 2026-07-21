"""
tests/test_d10_dashamsha.py
Reference + regression harness for D-10 (Dashamsha).   2026-07-21

Written BEFORE fixing the calculators, because three implementations disagreed
and there was no way to tell which (if any) was right.

THE RULE (BPHS / standard Parashari):
  Each sign is divided into TEN equal parts of 3 degrees.
  part = int(degree_in_sign / 3)            -> 0..9
  odd sign  (Aries, Gemini, Leo, Libra, Sagittarius, Aquarius)
      -> the parts start from the SAME sign
  even sign (Taurus, Cancer, Virgo, Scorpio, Capricorn, Pisces)
      -> the parts start from the 9TH SIGN FROM IT

"9th from X" counts X itself as the 1st, so it is index + 8 — NOT index + 9.
That off-by-one is the exact bug in d_charts_calculator, and the "+8" here is
the whole reason this file exists.

Run:  ./venv311/bin/python -m pytest tests/test_d10_dashamsha.py -q
   or ./venv311/bin/python tests/test_d10_dashamsha.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def d10_reference(sign_index: int, degree_in_sign: float) -> int:
    """The authority this harness measures everything else against."""
    part = int(degree_in_sign // 3)          # 0..9, three degrees each
    is_odd = (sign_index % 2 == 0)           # Aries(0) is the 1st = ODD sign
    start = sign_index if is_odd else (sign_index + 8) % 12
    return (start + part) % 12


def d10_reference_from_longitude(longitude: float) -> int:
    return d10_reference(int(longitude / 30) % 12, longitude % 30)


# (sign_index, degree, expected_sign, why) — each hand-derivable.
CASES = [
    (0,  0.0,  "Aries",     "Aries odd, part 0 -> same sign"),
    (0, 29.9,  "Capricorn", "Aries odd, part 9 -> Aries+9"),
    (0, 15.0,  "Virgo",     "Aries odd, part 5 -> Aries+5 (harness caught a bad hand-derivation here)"),
    (1,  0.0,  "Capricorn", "Taurus even, part 0 -> 9th from Taurus"),
    (1, 29.9,  "Libra",     "Taurus even, part 9 -> Capricorn+9"),
    (9, 24.69, "Taurus",    "Capricorn even, part 8 -> Virgo+8  (Raman's lagna)"),
    (10, 8.28, "Aries",     "Aquarius odd, part 2 -> Aquarius+2 (JS's lagna)"),
    (2,  6.0,  "Leo",       "Gemini odd, part 2 -> Gemini+2"),
    (11, 3.0,  "Sagittarius", "Pisces even, part 1 -> Scorpio+1"),
]


def test_reference_matches_hand_derivations():
    for si, deg, expected, why in CASES:
        got = SIGNS[d10_reference(si, deg)]
        assert got == expected, f"{why}: expected {expected}, got {got}"


def test_ten_distinct_parts_per_sign():
    """A D-10 must map one sign onto TEN consecutive signs.

    Guards the impl B failure mode: a 15-degree half-split yields only 2
    distinct signs, which silently looks like a working divisional chart.
    """
    for si in range(12):
        seen = {d10_reference(si, p * 3 + 1.5) for p in range(10)}
        assert len(seen) == 10, f"{SIGNS[si]} produced {len(seen)} parts, expected 10"


def test_production_calculator_matches_reference():
    from antar_engine.d_charts_calculator import _divisional_sign_index
    bad = []
    for si in range(12):
        for p in range(10):
            deg = p * 3 + 1.5
            lng = si * 30 + deg
            got = _divisional_sign_index(lng, 10)
            want = d10_reference(si, deg)
            if got != want:
                bad.append(f"{SIGNS[si]} {deg:.1f}: got {SIGNS[got]}, want {SIGNS[want]}")
    assert not bad, "d_charts_calculator D-10 mismatches:\n  " + "\n  ".join(bad[:12])


def test_stored_chart_calculator_matches_reference():
    from antar_engine.divisional_charts import _get_divisional_sign as impl_b
    bad = []
    for si in range(12):
        for p in range(10):
            deg = p * 3 + 1.5
            got = impl_b(si * 30 + deg, 10)
            want = SIGNS[d10_reference(si, deg)]
            if got != want:
                bad.append(f"{SIGNS[si]} {deg:.1f}: got {got}, want {want}")
    assert not bad, "divisional_charts D-10 mismatches:\n  " + "\n  ".join(bad[:12])


if __name__ == "__main__":
    import traceback
    for fn in (test_reference_matches_hand_derivations,
               test_ten_distinct_parts_per_sign,
               test_production_calculator_matches_reference,
               test_stored_chart_calculator_matches_reference):
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}\n      {e}")
        except Exception:
            print(f"ERROR {fn.__name__}")
            traceback.print_exc()


def test_ketu_varga_comes_from_ketus_own_longitude():
    """Ketu's divisional position must be computed from KETU's longitude.

    Regression for a bug that added 180 degrees to Ketu's OWN longitude — which
    is already opposite Rahu — landing Ketu exactly on Rahu in every varga, so
    Ketu had no independent position anywhere and "where does Ketu cut" was
    unreadable.

    NOTE: this does NOT assert the nodes never share a varga sign. In compressed
    divisions (D-2 has only two possible signs) two opposite points legitimately
    collide. The invariant is the SOURCE longitude, not separation.
    """
    from antar_engine.divisional_charts import (
        calculate_all_divisional_charts, _get_divisional_sign,
    )
    rahu_lon, ketu_lon = 226.78, 46.78          # genuinely 180 apart
    planets = {"Rahu": {"longitude": rahu_lon}, "Ketu": {"longitude": ketu_lon}}
    charts = calculate_all_divisional_charts(planets, 294.69)
    div_of = {"d1": 1, "d3": 3, "d4": 4, "d5": 5, "d7": 7,
              "d9": 9, "d10": 10, "d12": 12}
    bad = []
    for name, div in div_of.items():
        pl = (charts.get(name) or {}).get("planets") or {}
        got = (pl.get("Ketu") or {}).get("sign")
        want = _get_divisional_sign(ketu_lon, div)
        if got and got != want:
            bad.append(f"{name}: Ketu got {got}, want {want} (from Ketu's own longitude)")
    assert not bad, "Ketu varga positions not derived from Ketu:\n  " + "\n  ".join(bad)


def test_ketu_is_independent_of_rahu_in_d10():
    """D-10 has ten distinct parts, so the nodes must NOT coincide there."""
    from antar_engine.divisional_charts import calculate_all_divisional_charts
    planets = {"Rahu": {"longitude": 226.78}, "Ketu": {"longitude": 46.78}}
    pl = calculate_all_divisional_charts(planets, 294.69)["d10"]["planets"]
    assert pl["Rahu"]["sign"] != pl["Ketu"]["sign"], (
        f"nodes coincide in D-10: both {pl['Rahu']['sign']}"
    )
