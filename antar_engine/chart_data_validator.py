"""
antar_engine/chart_data_validator.py
=====================================
Schema enforcement for Antar chart data — real Supabase schema.

Validates chart_data JSONB AFTER normalize_chart_data() has been applied.

REAL SCHEMA facts:
  - chart_data.lagna          {sign: str, degree: float, sign_index: int}
  - chart_data.planets        {PlanetName: {sign: str, house: int, sign_index: int, ...}}
  - chart_data.divisional_charts.dN.lagna  = "SignName" (string)
  - chart_data.divisional_charts.dN.planets.PlanetName = {sign: str, house: int, ...}
  - NO dashas inside chart_data (separate dasha_periods table)
  - NO lal_kitab_data inside chart_data (separate column)
  - NO jaimini_data inside chart_data (separate column)

USAGE:
    ok, errors = validate_chart_data(chart_data)
    hard, warnings = split_errors_warnings(errors)
"""

from __future__ import annotations
from typing import Any, Dict, List, Tuple

from antar_engine.chart_schema import SIGN_NAMES, PLANET_CANONICAL, sign_name_to_index

CANONICAL_PLANET_NAMES = set(PLANET_CANONICAL.values())
REQUIRED_DIVISIONAL_CHARTS = ["d1", "d9", "d10"]
EXPECTED_DIVISIONAL_CHARTS = ["d1", "d2", "d9", "d10", "d12"]


def _is_valid_sign_name(v: Any) -> bool:
    return isinstance(v, str) and v.strip().title() in SIGN_NAMES


def _is_valid_sign_index(v: Any) -> bool:
    return isinstance(v, int) and 0 <= v <= 11


def _is_valid_house(v: Any) -> bool:
    return isinstance(v, int) and 1 <= v <= 12


def validate_lagna(lagna: Any) -> List[str]:
    errors = []
    if not isinstance(lagna, dict):
        return ["lagna: expected dict"]
    if "sign" not in lagna:
        errors.append("lagna: missing 'sign' field")
    elif not _is_valid_sign_name(lagna["sign"]):
        errors.append(f"lagna.sign: unrecognized sign name {lagna['sign']!r}")
    if "sign_index" in lagna and not _is_valid_sign_index(lagna["sign_index"]):
        errors.append(f"lagna.sign_index: expected int 0-11, got {lagna['sign_index']!r}")
    return errors


def validate_natal_planets(planets: Any) -> List[str]:
    errors = []
    if not isinstance(planets, dict):
        return ["planets: expected dict"]
    for pname, pdata in planets.items():
        pe = f"planets.{pname}"
        if pname not in CANONICAL_PLANET_NAMES:
            errors.append(f"{pe}: non-canonical name (expected Title-case)")
        if not isinstance(pdata, dict):
            errors.append(f"{pe}: expected dict")
            continue
        if "sign" in pdata and not _is_valid_sign_name(pdata["sign"]):
            errors.append(f"{pe}.sign: unrecognized {pdata['sign']!r}")
        if "sign_index" in pdata and not _is_valid_sign_index(pdata["sign_index"]):
            errors.append(f"{pe}.sign_index: expected int 0-11, got {pdata['sign_index']!r}")
        if "house" in pdata and not _is_valid_house(pdata["house"]):
            errors.append(f"{pe}.house: expected int 1-12, got {pdata['house']!r}")
    return errors


def validate_divisional_chart(key: str, chart: Any) -> List[str]:
    errors = []
    prefix = f"divisional_charts.{key}"
    if not isinstance(chart, dict):
        return [f"{prefix}: not a dict"]

    # lagna is a sign name string in divisional charts
    lagna = chart.get("lagna")
    if lagna is None:
        errors.append(f"{prefix}: missing 'lagna' field")
    elif not _is_valid_sign_name(lagna):
        errors.append(f"{prefix}.lagna: unrecognized sign {lagna!r}")

    planets = chart.get("planets")
    if planets is None:
        errors.append(f"{prefix}: missing 'planets' dict")
    elif not isinstance(planets, dict):
        errors.append(f"{prefix}.planets: expected dict")
    else:
        for pname, pdata in planets.items():
            pe = f"{prefix}.planets.{pname}"
            if pname not in CANONICAL_PLANET_NAMES:
                errors.append(f"{pe}: non-canonical name")
            if not isinstance(pdata, dict):
                errors.append(f"{pe}: expected dict")
                continue
            if "sign" in pdata and not _is_valid_sign_name(pdata["sign"]):
                errors.append(f"{pe}.sign: unrecognized {pdata['sign']!r}")
            if "sign_index" in pdata and not _is_valid_sign_index(pdata["sign_index"]):
                errors.append(f"{pe}.sign_index: expected int 0-11")
    return errors


def validate_chart_data(cd: Any) -> Tuple[bool, List[str]]:
    """
    Validate canonical chart_data dict (call after normalize_chart_data).

    Returns:
        (True, [...])   — valid (may include WARN: entries)
        (False, [...])  — invalid (has hard errors)
    """
    if not isinstance(cd, dict):
        return False, [f"chart_data: expected dict, got {type(cd).__name__}"]

    errors: List[str] = []

    # Required top-level fields
    if "lagna" not in cd:
        errors.append("Missing required field: 'lagna'")
    else:
        errors.extend(validate_lagna(cd["lagna"]))

    if "planets" not in cd:
        errors.append("Missing required field: 'planets'")
    else:
        errors.extend(validate_natal_planets(cd["planets"]))

    # Divisional charts
    div = cd.get("divisional_charts")
    if not isinstance(div, dict):
        errors.append("Missing or invalid 'divisional_charts'")
    else:
        # Catch any uppercase keys that slipped through normalize
        uppercase_keys = [k for k in div if k != k.lower()]
        if uppercase_keys:
            errors.append(
                f"divisional_charts: uppercase keys {uppercase_keys} — run normalize_chart_data()"
            )
        for req in REQUIRED_DIVISIONAL_CHARTS:
            if req not in div:
                errors.append(f"divisional_charts: missing required chart '{req}'")
            else:
                errors.extend(validate_divisional_chart(req, div[req]))
        for exp in EXPECTED_DIVISIONAL_CHARTS:
            if exp not in div and exp not in REQUIRED_DIVISIONAL_CHARTS:
                errors.append(f"WARN: divisional_charts: '{exp}' not present")

    is_valid = not any(e for e in errors if not e.startswith("WARN:"))
    return is_valid, errors


def split_errors_warnings(errors: List[str]) -> Tuple[List[str], List[str]]:
    hard = [e for e in errors if not e.startswith("WARN:")]
    warnings = [e[len("WARN: "):] for e in errors if e.startswith("WARN:")]
    return hard, warnings


def _run_tests() -> None:
    from antar_engine.chart_schema import normalize_chart_data
    print("Running chart_data_validator unit tests (real schema)...\n")

    # Valid chart
    cd_valid = normalize_chart_data({
        "lagna": {"sign": "Capricorn", "degree": 24.69, "sign_index": 9},
        "planets": {
            "Sun": {"sign": "Scorpio", "house": 11, "degree": 10.1, "sign_index": 7}
        },
        "divisional_charts": {
            "d1": {"lagna": "Capricorn", "planets": {"Sun": {"sign": "Scorpio", "house": 11}}},
            "d9": {"lagna": "Leo", "planets": {"Sun": {"sign": "Libra", "house": 3}}},
            "d10": {"lagna": "Aries", "planets": {}},
        },
    })
    ok, errs = validate_chart_data(cd_valid)
    hard, warns = split_errors_warnings(errs)
    assert ok, f"FAIL: valid chart should pass. Errors: {hard}"
    print("✅ Test 1: valid canonical chart passes")

    # Uppercase D9 key
    cd_upper = {"divisional_charts": {"D9": {"lagna": "Leo", "planets": {}}}}
    ok2, errs2 = validate_chart_data(cd_upper)
    assert not ok2
    assert any("uppercase" in e for e in errs2)
    print("✅ Test 2: uppercase D9 caught as error")

    # Missing d9
    cd_no_d9 = normalize_chart_data({
        "lagna": {"sign": "Aries", "sign_index": 0},
        "planets": {"Sun": {"sign": "Leo", "house": 5}},
        "divisional_charts": {"d1": {"lagna": "Aries", "planets": {}}},
    })
    ok3, errs3 = validate_chart_data(cd_no_d9)
    assert not ok3
    assert any("d9" in e for e in errs3)
    print("✅ Test 3: missing d9 flagged as error")

    # Warnings don't fail
    cd_warn = normalize_chart_data({
        "lagna": {"sign": "Aries", "sign_index": 0},
        "planets": {"Sun": {"sign": "Leo", "house": 5}},
        "divisional_charts": {
            "d1": {"lagna": "Aries", "planets": {}},
            "d9": {"lagna": "Leo", "planets": {}},
            "d10": {"lagna": "Capricorn", "planets": {}},
        },
    })
    ok4, errs4 = validate_chart_data(cd_warn)
    hard4, warns4 = split_errors_warnings(errs4)
    assert ok4, f"FAIL: warnings-only chart should pass. Hard: {hard4}"
    assert len(warns4) > 0
    print(f"✅ Test 4: warnings don't fail validation ({len(warns4)} warnings)")

    print("\n✅ All validator tests passed.")


if __name__ == "__main__":
    _run_tests()
