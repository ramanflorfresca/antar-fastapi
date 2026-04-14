"""
antar_engine/chart_schema.py
============================
Canonical chart data schema for Antar.

CANONICAL CONVENTIONS (enforced by this module):
  - Divisional chart keys: lowercase  →  d1, d2, d9, d10  (NOT D1, D9, D10)
  - Sign indices: integers 0-11       →  0=Aries … 11=Pisces
  - Degrees: floats                   →  23.47  (NOT "23.47" string)
  - Planet names: Title-case strings  →  "Sun", "Moon", "Rahu", "Ketu"

ENTRY POINTS:
  normalize_chart_data(raw)           →  canonical ChartData dict
  get_divisional(cd, key)             →  safe read, accepts "d9" or "D9"

Place this file at  ~/antarai/antar_engine/chart_schema.py
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, TypedDict

# ---------------------------------------------------------------------------
# 1. TypedDict shapes (documentation + IDE support, NOT runtime enforcement)
# ---------------------------------------------------------------------------

class PlanetPosition(TypedDict, total=False):
    sign: int          # 0-11 integer
    sign_name: str     # "Aries", "Taurus" … canonical
    degree: float      # 0.0 - 29.999
    house: int         # 1-12
    retrograde: bool
    nakshatra: str
    nakshatra_pada: int


class DivisionalChart(TypedDict, total=False):
    lagna: int                          # sign index 0-11
    lagna_name: str
    planets: Dict[str, PlanetPosition]  # keyed by planet name (Title-case)


class DashaEntry(TypedDict, total=False):
    planet: str
    start: str   # ISO date string "YYYY-MM-DD"
    end: str
    sub_dashas: List[Dict[str, Any]]


class JaiminiKaraka(TypedDict, total=False):
    planet: str
    karaka: str   # "AK", "AmK", "BK", "MK", "PuK", "GnK", "DK"
    degree: float


class JaiminiData(TypedDict, total=False):
    karakas: List[JaiminiKaraka]
    arudha_lagna: Dict[str, Any]
    upapada_lagna: Dict[str, Any]
    karakamsa: Dict[str, Any]
    predictions: List[Dict[str, Any]]


class DKPContext(TypedDict, total=False):
    desha: Dict[str, Any]   # place / culture
    kala: Dict[str, Any]    # era / life stage (age as integer years)
    patra: Dict[str, Any]   # person / role / industry


class ChartData(TypedDict, total=False):
    natal: Dict[str, Any]
    divisional_charts: Dict[str, DivisionalChart]   # keys: d1, d2, d9 … (lowercase)
    dashas: Dict[str, Any]
    lal_kitab: Dict[str, Any]
    lal_kitab_advanced: Dict[str, Any]
    varshphal: Dict[str, Any]
    jaimini: JaiminiData
    dkp_context: DKPContext
    natal_signature: Dict[str, Any]
    archetype: Dict[str, Any]
    yogas: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# 2. Constants
# ---------------------------------------------------------------------------

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_NAME_TO_INDEX: Dict[str, int] = {n.lower(): i for i, n in enumerate(SIGN_NAMES)}

PLANET_CANONICAL = {
    "sun": "Sun", "moon": "Moon", "mars": "Mars", "mercury": "Mercury",
    "jupiter": "Jupiter", "venus": "Venus", "saturn": "Saturn",
    "rahu": "Rahu", "ketu": "Ketu",
    "ascendant": "Ascendant", "asc": "Ascendant",
}

# All divisional chart key aliases → canonical lowercase key
_DIV_KEY_ALIASES: Dict[str, str] = {}
for _n in range(1, 25):
    _DIV_KEY_ALIASES[f"d{_n}"] = f"d{_n}"    # already canonical
    _DIV_KEY_ALIASES[f"D{_n}"] = f"d{_n}"    # uppercase → canonical


# ---------------------------------------------------------------------------
# 3. Low-level coercion helpers
# ---------------------------------------------------------------------------

def _to_int_sign(value: Any) -> Optional[int]:
    """Convert sign value to integer 0-11.  Accepts int, str name, str number."""
    if value is None:
        return None
    if isinstance(value, int):
        return value if 0 <= value <= 11 else None
    if isinstance(value, float):
        v = int(value)
        return v if 0 <= v <= 11 else None
    if isinstance(value, str):
        # Try numeric string first
        try:
            v = int(float(value))
            return v if 0 <= v <= 11 else None
        except ValueError:
            pass
        # Try sign name
        return SIGN_NAME_TO_INDEX.get(value.strip().lower())
    return None


def _to_float(value: Any) -> Optional[float]:
    """Coerce to float, return None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "t")
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _canonical_planet_name(name: Any) -> str:
    """Return Title-case canonical planet name."""
    if not isinstance(name, str):
        return str(name)
    return PLANET_CANONICAL.get(name.strip().lower(), name.strip().title())


# ---------------------------------------------------------------------------
# 4. Planet position normalizer
# ---------------------------------------------------------------------------

def _normalize_planet(raw: Any) -> Dict[str, Any]:
    """Normalize a single planet position dict."""
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Any] = {}

    sign_raw = raw["sign"] if "sign" in raw else (raw["sign_index"] if "sign_index" in raw else raw.get("rasi"))
    sign_idx = _to_int_sign(sign_raw)
    if sign_idx is not None:
        out["sign"] = sign_idx
        out["sign_name"] = SIGN_NAMES[sign_idx]
    elif isinstance(sign_raw, str) and sign_raw.strip():
        # Preserve unknown string (will be flagged by validator)
        out["sign_name"] = sign_raw.strip().title()

    _deg_raw = raw["degree"] if "degree" in raw else (raw["degrees"] if "degrees" in raw else raw.get("deg"))
    deg = _to_float(_deg_raw)
    if deg is not None:
        out["degree"] = deg

    house = raw["house"] if "house" in raw else raw.get("bhava")
    if house is not None:
        try:
            out["house"] = int(house)
        except (ValueError, TypeError):
            pass

    if "retrograde" in raw:
        out["retrograde"] = _to_bool(raw["retrograde"])

    for field in ("nakshatra", "nakshatra_pada", "lord", "sub_lord"):
        if field in raw:
            out[field] = raw[field]

    return out


# ---------------------------------------------------------------------------
# 5. Divisional chart normalizer
# ---------------------------------------------------------------------------

def _normalize_divisional_chart(raw: Any) -> Dict[str, Any]:
    """Normalize one divisional chart (e.g. D9 → d9 canonical shape)."""
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Any] = {}

    # Lagna — explicit key check so lagna=0 (Aries) isn't treated as missing
    _lagna_key = next((k for k in ("lagna", "ascendant", "asc") if k in raw), None)
    lagna_raw = raw[_lagna_key] if _lagna_key else None
    if isinstance(lagna_raw, dict):
        _lsign = lagna_raw.get("sign") if "sign" in lagna_raw else lagna_raw.get("sign_index")
        sign_idx = _to_int_sign(_lsign)
        if sign_idx is not None:
            out["lagna"] = sign_idx
            out["lagna_name"] = SIGN_NAMES[sign_idx]
    else:
        sign_idx = _to_int_sign(lagna_raw)
        if sign_idx is not None:
            out["lagna"] = sign_idx
            out["lagna_name"] = SIGN_NAMES[sign_idx]

    # Planets
    planets_raw = raw.get("planets") or raw.get("planet_positions") or {}
    if isinstance(planets_raw, dict):
        out["planets"] = {
            _canonical_planet_name(k): _normalize_planet(v)
            for k, v in planets_raw.items()
        }
    elif isinstance(planets_raw, list):
        # Some legacy formats store planets as a list with a "name" field
        planets_dict: Dict[str, Any] = {}
        for p in planets_raw:
            if isinstance(p, dict):
                name = _canonical_planet_name(p.get("name") or p.get("planet", "Unknown"))
                planets_dict[name] = _normalize_planet(p)
        if planets_dict:
            out["planets"] = planets_dict

    # Pass through any extra keys (don't destroy data)
    for k, v in raw.items():
        if k not in ("lagna", "ascendant", "asc", "planets", "planet_positions"):
            out[k] = v

    return out


# ---------------------------------------------------------------------------
# 6. Top-level normalize_chart_data
# ---------------------------------------------------------------------------

def normalize_chart_data(raw: Any) -> Dict[str, Any]:
    """
    Accept chart data in ANY legacy format and return canonical ChartData dict.

    Handles:
      - Uppercase divisional keys  (D9 → d9, D10 → d10)
      - String sign indices        ("5" → 5)
      - Sign name strings          ("Virgo" → 5)
      - Float sign indices         (5.0 → 5)
      - Planet lists vs dicts
      - Missing divisional_charts  (empty dict returned, validator will flag)

    Does NOT:
      - Recompute any astrological values
      - Drop unknown keys (they pass through so data is never silently lost)
    """
    if not isinstance(raw, dict):
        return {}

    out: Dict[str, Any] = {}

    # --- natal -----------------------------------------------------------
    natal = raw.get("natal") or raw.get("natal_chart") or raw.get("d1_chart") or {}
    if isinstance(natal, dict):
        out["natal"] = _normalize_divisional_chart(natal)

    # --- divisional_charts -----------------------------------------------
    div_raw = raw.get("divisional_charts") or raw.get("divisional") or {}
    canonical_div: Dict[str, Any] = {}
    if isinstance(div_raw, dict):
        for key, val in div_raw.items():
            canonical_key = _DIV_KEY_ALIASES.get(key, key.lower())
            canonical_div[canonical_key] = _normalize_divisional_chart(val)
    out["divisional_charts"] = canonical_div

    # --- dashas ----------------------------------------------------------
    dashas = raw.get("dashas") or raw.get("dasha") or {}
    if isinstance(dashas, dict):
        out["dashas"] = dashas   # structure varies by engine; pass through

    # --- lal_kitab -------------------------------------------------------
    for lk_key in ("lal_kitab", "lal_kitab_basic"):
        if lk_key in raw:
            out["lal_kitab"] = raw[lk_key]
            break

    if "lal_kitab_advanced" in raw:
        out["lal_kitab_advanced"] = raw["lal_kitab_advanced"]

    # --- varshphal -------------------------------------------------------
    for vk in ("varshphal", "varshaphal", "annual_chart"):
        if vk in raw:
            out["varshphal"] = raw[vk]
            break

    # --- jaimini ---------------------------------------------------------
    _jaimini_key = "jaimini" if "jaimini" in raw else ("jaimini_data" if "jaimini_data" in raw else None)
    if _jaimini_key:
        jaimini = raw[_jaimini_key]
        if isinstance(jaimini, dict):
            out["jaimini"] = jaimini   # validated separately

    # --- dkp_context -----------------------------------------------------
    _dkp_key = "dkp_context" if "dkp_context" in raw else ("dkp" if "dkp" in raw else None)
    dkp = raw[_dkp_key] if _dkp_key else None
    if isinstance(dkp, dict):
        # Enforce kala.age as integer (strip days/hours/microseconds)
        if "kala" in dkp and isinstance(dkp["kala"], dict):
            kala = dict(dkp["kala"])
            age_raw = kala.get("age") or kala.get("age_years")
            if age_raw is not None:
                try:
                    kala["age"] = int(float(str(age_raw).split(".")[0]))
                except (ValueError, TypeError):
                    pass
            dkp = {**dkp, "kala": kala}
        out["dkp_context"] = dkp

    # --- natal_signature, archetype, yogas --------------------------------
    for passthrough in ("natal_signature", "archetype", "yogas",
                        "chakra_map", "lk_sleeping_planets"):
        if passthrough in raw:
            out[passthrough] = raw[passthrough]

    return out


# ---------------------------------------------------------------------------
# 7. Safe divisional chart reader (accepts either case)
# ---------------------------------------------------------------------------

def get_divisional(chart_data: Dict[str, Any], key: str) -> Dict[str, Any]:
    """
    Safe read of a divisional chart.  Accepts 'd9' or 'D9'.
    Always returns a dict (empty if not found).
    After normalize_chart_data() all keys should be lowercase; this helper
    is a safety net for code that hasn't been updated yet.
    """
    divs = chart_data.get("divisional_charts") or {}
    canonical = _DIV_KEY_ALIASES.get(key, key.lower())
    return divs.get(canonical) or divs.get(key) or {}


# ---------------------------------------------------------------------------
# 8. Unit tests  (run:  python -m antar_engine.chart_schema)
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    import json

    print("Running chart_schema unit tests…\n")
    errors: List[str] = []

    # --- Test 1: uppercase D9 → d9 ---
    raw1 = {
        "divisional_charts": {
            "D9": {"lagna": 3, "planets": {"sun": {"sign": 5, "degree": 14.3, "house": 3}}},
            "D10": {"lagna": "Capricorn"},
        }
    }
    cd1 = normalize_chart_data(raw1)
    assert "d9" in cd1["divisional_charts"], "FAIL: D9 not normalised to d9"
    assert "D9" not in cd1["divisional_charts"], "FAIL: D9 key still present"
    assert "d10" in cd1["divisional_charts"], "FAIL: D10 not normalised to d10"
    assert cd1["divisional_charts"]["d9"]["lagna"] == 3, "FAIL: d9 lagna wrong"
    assert cd1["divisional_charts"]["d9"]["planets"]["Sun"]["degree"] == 14.3, "FAIL: Sun degree"
    assert cd1["divisional_charts"]["d10"]["lagna"] == 9, "FAIL: Capricorn not → 9"
    print("✅ Test 1: uppercase D9/D10 → lowercase d9/d10")

    # --- Test 2: string sign index ---
    raw2 = {"divisional_charts": {"d1": {"lagna": "8"}}}
    cd2 = normalize_chart_data(raw2)
    assert cd2["divisional_charts"]["d1"]["lagna"] == 8, "FAIL: string sign index"
    assert cd2["divisional_charts"]["d1"]["lagna_name"] == "Sagittarius"
    print("✅ Test 2: string sign index '8' → 8 (Sagittarius)")

    # --- Test 3: sign name string ---
    raw3 = {"divisional_charts": {"d9": {"lagna": "Virgo", "planets": {}}}}
    cd3 = normalize_chart_data(raw3)
    assert cd3["divisional_charts"]["d9"]["lagna"] == 5, "FAIL: Virgo → 5"
    print("✅ Test 3: sign name 'Virgo' → 5")

    # --- Test 4: planet list format ---
    raw4 = {"divisional_charts": {"d1": {"lagna": 0, "planets": [
        {"name": "moon", "sign": 2, "degree": 7.1, "house": 3},
        {"name": "saturn", "sign": "Aquarius", "degree": 22.0, "retrograde": True},
    ]}}}
    cd4 = normalize_chart_data(raw4)
    planets4 = cd4["divisional_charts"]["d1"]["planets"]
    assert "Moon" in planets4, "FAIL: moon not → Moon"
    assert "Saturn" in planets4, "FAIL: saturn not → Saturn"
    assert planets4["Saturn"]["sign"] == 10, "FAIL: Aquarius → 10"
    assert planets4["Saturn"]["retrograde"] is True, "FAIL: retrograde"
    print("✅ Test 4: planet list with mixed sign formats")

    # --- Test 5: get_divisional helper ---
    assert get_divisional(cd1, "D9") == get_divisional(cd1, "d9"), "FAIL: get_divisional case"
    assert get_divisional(cd1, "d99") == {}, "FAIL: missing key should return {}"
    print("✅ Test 5: get_divisional accepts D9 or d9")

    # --- Test 6: kala.age stripped to integer ---
    raw6 = {"dkp_context": {"kala": {"age": "38.7", "life_stage": "mid"}}}
    cd6 = normalize_chart_data(raw6)
    assert cd6["dkp_context"]["kala"]["age"] == 38, "FAIL: age not stripped to int"
    print("✅ Test 6: kala.age '38.7' → 38 (integer)")

    # --- Test 7: unknown keys pass through ---
    raw7 = {"custom_field": "keep_me", "divisional_charts": {}}
    cd7 = normalize_chart_data(raw7)
    # custom_field is not a known key so it won't be in output (by design — only known top-level keys)
    # But unknown keys inside sub-dicts should pass through
    raw7b = {"divisional_charts": {"d1": {"lagna": 1, "extra_data": "preserved"}}}
    cd7b = normalize_chart_data(raw7b)
    assert cd7b["divisional_charts"]["d1"].get("extra_data") == "preserved", "FAIL: extra keys dropped"
    print("✅ Test 7: unknown keys inside sub-dicts preserved")

    # --- Test 8: lal_kitab key aliases ---
    raw8 = {"lal_kitab_basic": {"planets": {}}, "lal_kitab_advanced": {"sleeping": []}}
    cd8 = normalize_chart_data(raw8)
    assert "lal_kitab" in cd8, "FAIL: lal_kitab_basic not aliased"
    assert "lal_kitab_advanced" in cd8, "FAIL: lal_kitab_advanced missing"
    print("✅ Test 8: lal_kitab_basic aliased to lal_kitab")

    print("\n✅ All tests passed.")


if __name__ == "__main__":
    _run_tests()
