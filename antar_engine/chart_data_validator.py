"""
antar_engine/chart_data_validator.py
=====================================
Schema enforcement layer for Antar chart data.

Validates that chart data conforms to the canonical schema AFTER
normalize_chart_data() has been applied.  Returns a list of human-readable
errors so callers can decide to reject, warn, or log.

USAGE:
    from antar_engine.chart_data_validator import validate_chart_data

    ok, errors = validate_chart_data(chart_data)
    if not ok:
        logger.warning("Chart data schema violations: %s", errors)

ENTRY POINTS:
    validate_chart_data(cd)            →  (bool, List[str])
    validate_divisional_chart(key, cd) →  List[str]   (errors only)
    validate_jaimini(jaimini_data)     →  List[str]
    validate_dkp_context(dkp)          →  List[str]

Place this file at  ~/antarai/antar_engine/chart_data_validator.py
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

# Lazy import to avoid circular dependency — schema module has no deps on validator
from antar_engine.chart_schema import SIGN_NAMES, PLANET_CANONICAL


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

REQUIRED_TOP_LEVEL_KEYS = [
    "natal",
    "divisional_charts",
    "dashas",
]

REQUIRED_DIVISIONAL_CHARTS = ["d1", "d9", "d10"]   # minimum required for predictions
EXPECTED_DIVISIONAL_CHARTS = ["d1", "d2", "d7", "d9", "d10", "d12"]  # full set

CANONICAL_PLANET_NAMES = set(PLANET_CANONICAL.values())  # Title-case

KARAKA_ROLES = {"AK", "AmK", "BK", "MK", "PuK", "GnK", "DK"}


# ---------------------------------------------------------------------------
# 2. Low-level helpers
# ---------------------------------------------------------------------------

def _is_valid_sign_index(v: Any) -> bool:
    return isinstance(v, int) and 0 <= v <= 11


def _is_valid_degree(v: Any) -> bool:
    return isinstance(v, float) and 0.0 <= v < 30.0


def _is_valid_house(v: Any) -> bool:
    return isinstance(v, int) and 1 <= v <= 12


# ---------------------------------------------------------------------------
# 3. Sub-validators
# ---------------------------------------------------------------------------

def validate_divisional_chart(chart_key: str, chart: Any) -> List[str]:
    """Return list of error strings for one divisional chart."""
    errors: List[str] = []
    prefix = f"divisional_charts.{chart_key}"

    if not isinstance(chart, dict):
        return [f"{prefix}: not a dict (got {type(chart).__name__})"]

    # Lagna
    if "lagna" not in chart:
        errors.append(f"{prefix}: missing 'lagna' field")
    elif not _is_valid_sign_index(chart["lagna"]):
        errors.append(
            f"{prefix}.lagna: expected int 0-11, got {chart['lagna']!r}"
        )

    # Planets
    planets = chart.get("planets")
    if planets is None:
        errors.append(f"{prefix}: missing 'planets' dict")
    elif not isinstance(planets, dict):
        errors.append(f"{prefix}.planets: expected dict, got {type(planets).__name__}")
    else:
        for pname, pdata in planets.items():
            pe = f"{prefix}.planets.{pname}"
            # Planet name should be Title-case canonical
            if pname not in CANONICAL_PLANET_NAMES and pname != "Ascendant":
                errors.append(f"{pe}: non-canonical name '{pname}'")
            if not isinstance(pdata, dict):
                errors.append(f"{pe}: expected dict, got {type(pdata).__name__}")
                continue
            if "sign" in pdata and not _is_valid_sign_index(pdata["sign"]):
                errors.append(f"{pe}.sign: expected int 0-11, got {pdata['sign']!r}")
            if "degree" in pdata and not _is_valid_degree(pdata["degree"]):
                errors.append(f"{pe}.degree: expected float 0-30, got {pdata['degree']!r}")
            if "house" in pdata and not _is_valid_house(pdata["house"]):
                errors.append(f"{pe}.house: expected int 1-12, got {pdata['house']!r}")

    return errors


def validate_dashas(dashas: Any) -> List[str]:
    """Basic dasha structure check."""
    errors: List[str] = []
    if not isinstance(dashas, dict):
        return ["dashas: expected dict"]
    for required_key in ("vimsottari",):
        if required_key not in dashas:
            errors.append(f"dashas: missing '{required_key}' block")
    return errors


def validate_jaimini(jaimini: Any) -> List[str]:
    """Validate jaimini sub-dict."""
    errors: List[str] = []
    if not isinstance(jaimini, dict):
        return ["jaimini: expected dict"]

    karakas = jaimini.get("karakas")
    if karakas is None:
        errors.append("jaimini: missing 'karakas' list")
    elif not isinstance(karakas, list):
        errors.append(f"jaimini.karakas: expected list, got {type(karakas).__name__}")
    else:
        seen_roles = set()
        for i, k in enumerate(karakas):
            if not isinstance(k, dict):
                errors.append(f"jaimini.karakas[{i}]: expected dict")
                continue
            role = k.get("karaka")
            if role and role in seen_roles:
                errors.append(f"jaimini.karakas: duplicate karaka role '{role}'")
            if role:
                seen_roles.add(role)
            if role and role not in KARAKA_ROLES:
                errors.append(f"jaimini.karakas[{i}].karaka: unknown role '{role}'")

    return errors


def validate_dkp_context(dkp: Any) -> List[str]:
    """Validate DKP context block."""
    errors: List[str] = []
    if not isinstance(dkp, dict):
        return ["dkp_context: expected dict"]

    for block in ("desha", "kala", "patra"):
        if block not in dkp:
            errors.append(f"dkp_context: missing '{block}' block")

    # kala.age must be integer
    kala = dkp.get("kala") or {}
    if isinstance(kala, dict):
        age = kala.get("age")
        if age is not None and not isinstance(age, int):
            errors.append(
                f"dkp_context.kala.age: expected int, got {type(age).__name__} ({age!r}). "
                "Run normalize_chart_data() to strip to integer."
            )

    return errors


# ---------------------------------------------------------------------------
# 4. Top-level validate_chart_data
# ---------------------------------------------------------------------------

def validate_chart_data(cd: Any) -> Tuple[bool, List[str]]:
    """
    Validate canonical chart data dict.

    Call AFTER normalize_chart_data().

    Returns:
        (True, [])            — data is valid
        (False, [error, …])   — data has schema violations

    Design philosophy:
        - Warnings for missing-but-recoverable fields (e.g. d7 not present)
        - Errors for fields that will silently produce wrong predictions
          (e.g. D9 uppercase key, sign as string, missing d9 entirely)
    """
    if not isinstance(cd, dict):
        return False, [f"chart_data: expected dict, got {type(cd).__name__}"]

    errors: List[str] = []

    # --- Required top-level keys ----------------------------------------
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in cd:
            errors.append(f"Missing required top-level key: '{key}'")

    # --- Natal chart (should be present and valid after normalize) -------
    natal = cd.get("natal")
    if natal is not None:
        errors.extend(validate_divisional_chart("natal", natal))

    # --- Divisional charts -----------------------------------------------
    div = cd.get("divisional_charts")
    if not isinstance(div, dict):
        errors.append("divisional_charts: expected dict")
    else:
        # Check no uppercase keys slipped through
        uppercase_keys = [k for k in div if k != k.lower()]
        if uppercase_keys:
            errors.append(
                f"divisional_charts: uppercase keys found {uppercase_keys}. "
                "Call normalize_chart_data() first."
            )

        # Required charts for prediction quality
        for req_key in REQUIRED_DIVISIONAL_CHARTS:
            if req_key not in div:
                errors.append(
                    f"divisional_charts: missing required chart '{req_key}'. "
                    "Predictions will degrade."
                )
            else:
                errors.extend(validate_divisional_chart(req_key, div[req_key]))

        # Warn (not error) about missing but expected charts
        # (stored as errors with a WARN: prefix so callers can filter)
        for exp_key in EXPECTED_DIVISIONAL_CHARTS:
            if exp_key not in div and exp_key not in REQUIRED_DIVISIONAL_CHARTS:
                errors.append(f"WARN: divisional_charts: '{exp_key}' not present")

    # --- Dashas ----------------------------------------------------------
    dashas = cd.get("dashas")
    if dashas is not None:
        errors.extend(validate_dashas(dashas))

    # --- Jaimini (optional but impactful) --------------------------------
    jaimini = cd.get("jaimini")
    if jaimini is not None:
        errors.extend(validate_jaimini(jaimini))

    # --- DKP context (optional) ------------------------------------------
    dkp = cd.get("dkp_context")
    if dkp is not None:
        errors.extend(validate_dkp_context(dkp))

    # --- Presence checks for prediction-quality fields -------------------
    if "lal_kitab" not in cd:
        errors.append("WARN: lal_kitab missing — sleeping planet rules won't fire")
    if "jaimini" not in cd:
        errors.append("WARN: jaimini missing — Karakamsa predictions unavailable")

    is_valid = not any(e for e in errors if not e.startswith("WARN:"))
    return is_valid, errors


# ---------------------------------------------------------------------------
# 5. Convenience: strict errors vs warnings split
# ---------------------------------------------------------------------------

def split_errors_warnings(errors: List[str]) -> Tuple[List[str], List[str]]:
    """Split validate_chart_data errors into (hard_errors, warnings)."""
    hard = [e for e in errors if not e.startswith("WARN:")]
    warnings = [e[len("WARN: "):] for e in errors if e.startswith("WARN:")]
    return hard, warnings


# ---------------------------------------------------------------------------
# 6. Unit tests  (run:  python -m antar_engine.chart_data_validator)
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    from antar_engine.chart_schema import normalize_chart_data

    print("Running chart_data_validator unit tests…\n")

    # --- Test 1: valid canonical chart passes ---
    cd_valid = normalize_chart_data({
        "natal": {
            "lagna": 0,
            "planets": {
                "Sun": {"sign": 5, "degree": 14.3, "house": 6},
                "Moon": {"sign": 2, "degree": 7.1, "house": 3},
            }
        },
        "divisional_charts": {
            "d1": {"lagna": 0, "planets": {"Sun": {"sign": 5, "degree": 14.3, "house": 6}}},
            "d9": {"lagna": 3, "planets": {"Sun": {"sign": 1, "degree": 22.5, "house": 2}}},
            "d10": {"lagna": 1, "planets": {}},
        },
        "dashas": {
            "vimsottari": {"current": "Venus", "sub": "Mercury"},
        },
        "jaimini": {
            "karakas": [
                {"planet": "Sun", "karaka": "AK", "degree": 25.3},
                {"planet": "Moon", "karaka": "AmK", "degree": 18.2},
            ]
        },
        "dkp_context": {
            "desha": {"country": "CO", "city": "Bogotá"},
            "kala": {"age": 38, "life_stage": "mid"},
            "patra": {"role": "founder", "industry": "tech"},
        }
    })
    ok, errs = validate_chart_data(cd_valid)
    hard, warns = split_errors_warnings(errs)
    assert ok, f"FAIL: valid chart should pass. Hard errors: {hard}"
    print("✅ Test 1: valid canonical chart passes validation")

    # --- Test 2: uppercase D9 key caught ---
    cd_bad = {"divisional_charts": {"D9": {"lagna": 3, "planets": {}}}}
    ok2, errs2 = validate_chart_data(cd_bad)
    assert not ok2, "FAIL: uppercase D9 should fail"
    assert any("uppercase" in e for e in errs2), "FAIL: no uppercase error reported"
    print("✅ Test 2: uppercase D9 key caught as error")

    # --- Test 3: missing d9 flagged ---
    cd_no_d9 = {
        "natal": {"lagna": 0, "planets": {}},
        "divisional_charts": {"d1": {"lagna": 0, "planets": {}}},
        "dashas": {"vimsottari": {}},
    }
    ok3, errs3 = validate_chart_data(cd_no_d9)
    assert not ok3
    assert any("d9" in e and "missing" in e for e in errs3), f"FAIL: missing d9 not flagged. Got: {errs3}"
    print("✅ Test 3: missing d9 flagged as error")

    # --- Test 4: string sign index in planet caught ---
    cd_str_sign = normalize_chart_data({
        "natal": {"lagna": 0, "planets": {}},
        "divisional_charts": {
            "d1": {"lagna": 0, "planets": {"Sun": {"sign": 5, "degree": 14.3}}},
            "d9": {"lagna": 3, "planets": {}},
            "d10": {"lagna": 1, "planets": {}},
        },
        "dashas": {"vimsottari": {}},
    })
    # Manually inject a string sign to simulate a chart that bypassed normalize
    cd_str_sign["divisional_charts"]["d1"]["planets"]["Moon"] = {"sign": "5", "degree": 7.1}
    ok4, errs4 = validate_chart_data(cd_str_sign)
    assert not ok4
    assert any("Moon" in e and "sign" in e for e in errs4), f"FAIL: string sign not caught. Got: {errs4}"
    print("✅ Test 4: string sign index in planet caught as error")

    # --- Test 5: kala.age as float caught ---
    cd_age = normalize_chart_data({
        "natal": {"lagna": 0, "planets": {}},
        "divisional_charts": {
            "d1": {"lagna": 0, "planets": {}},
            "d9": {"lagna": 0, "planets": {}},
            "d10": {"lagna": 0, "planets": {}},
        },
        "dashas": {"vimsottari": {}},
        "dkp_context": {"kala": {}, "desha": {}, "patra": {}},
    })
    # Manually inject float age after normalization
    cd_age["dkp_context"]["kala"]["age"] = 38.5
    ok5, errs5 = validate_chart_data(cd_age)
    assert not ok5
    assert any("kala.age" in e for e in errs5), f"FAIL: float age not caught. Got: {errs5}"
    print("✅ Test 5: kala.age float caught as error")

    # --- Test 6: warnings don't fail validation ---
    # A chart missing lal_kitab or jaimini should produce warnings but still pass (ok=True)
    cd_warn = normalize_chart_data({
        "natal": {"lagna": 0, "planets": {}},
        "divisional_charts": {
            "d1": {"lagna": 0, "planets": {}},
            "d9": {"lagna": 0, "planets": {}},
            "d10": {"lagna": 0, "planets": {}},
        },
        "dashas": {"vimsottari": {}},
        # no lal_kitab, no jaimini → should generate WARN: entries only
    })
    ok6, errs6 = validate_chart_data(cd_warn)
    hard6, warns6 = split_errors_warnings(errs6)
    assert ok6, f"FAIL: should pass (only warnings). Hard errors: {hard6}"
    assert len(warns6) > 0, "FAIL: expected warnings for missing lal_kitab/jaimini"
    print(f"✅ Test 6: warnings don't fail validation (got {len(warns6)} warnings)")

    print("\n✅ All validator tests passed.")


if __name__ == "__main__":
    _run_tests()
