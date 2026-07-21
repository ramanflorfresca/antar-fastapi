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
