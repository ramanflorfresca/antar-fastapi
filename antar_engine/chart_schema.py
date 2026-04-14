"""
antar_engine/chart_schema.py
============================
Canonical chart data schema for Antar — built against the REAL Supabase schema.

REAL SCHEMA (confirmed Apr 14 2026 against production):
  chart_data (JSONB column on `charts` table):
    .lagna                  {sign: "Capricorn", degree: float, sign_index: int}
    .planets                {PlanetName: {sign: str, house: int, degree: float,
                                          sign_index: int, nakshatra: str, ...}}
    .divisional_charts      {d1..d60: {lagna: "SignName", meaning: str,
                                       planets: {PlanetName: {sign: str, house: int,
                                                              sign_lord: str}},
                                       lagna_lord: str}}
    .yogas                  [...]
    .house_lords            {...}
    .house_analysis         {...}
    .birth_jd               float
    .atmakaraka             str

  Separate columns on `charts` table (NOT inside chart_data):
    .lal_kitab_data         JSONB
    .jaimini_data           JSONB
    .lagna_sign             str  (e.g. "Capricorn")
    .lagna_degree           float

  Separate table:
    `dasha_periods`         (not `dashas`)

CANONICAL CONVENTIONS:
  - Divisional chart keys: lowercase  ->  d1, d9, d10  (already correct in prod)
  - Sign names: Title-case strings    ->  "Aries", "Capricorn" (preserved as-is)
  - Sign indices: integers 0-11       ->  sign_index field where present
  - Planet names: Title-case          ->  "Sun", "Moon", "Rahu"
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_NAME_TO_INDEX: Dict[str, int] = {n.lower(): i for i, n in enumerate(SIGN_NAMES)}

PLANET_CANONICAL: Dict[str, str] = {
    "sun": "Sun", "moon": "Moon", "mars": "Mars", "mercury": "Mercury",
    "jupiter": "Jupiter", "venus": "Venus", "saturn": "Saturn",
    "rahu": "Rahu", "ketu": "Ketu",
    "ascendant": "Ascendant", "asc": "Ascendant",
    "uranus": "Uranus", "neptune": "Neptune", "pluto": "Pluto",
}

_DIV_KEY_ALIASES: Dict[str, str] = {}
for _n in range(1, 61):
    _DIV_KEY_ALIASES[f"d{_n}"] = f"d{_n}"
    _DIV_KEY_ALIASES[f"D{_n}"] = f"d{_n}"


def sign_name_to_index(name: Any) -> Optional[int]:
    if isinstance(name, int) and 0 <= name <= 11:
        return name
    if isinstance(name, str):
        return SIGN_NAME_TO_INDEX.get(name.strip().lower())
    return None


def sign_index_to_name(idx: Any) -> Optional[str]:
    if isinstance(idx, int) and 0 <= idx <= 11:
        return SIGN_NAMES[idx]
    return None


def canonical_planet_name(name: Any) -> str:
    if not isinstance(name, str):
        return str(name)
    return PLANET_CANONICAL.get(name.strip().lower(), name.strip().title())


def _normalize_lagna(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out = dict(raw)
    if "sign_index" in out:
        try:
            out["sign_index"] = int(out["sign_index"])
        except (ValueError, TypeError):
            pass
    elif "sign" in out:
        idx = sign_name_to_index(out["sign"])
        if idx is not None:
            out["sign_index"] = idx
    if "sign" in out and isinstance(out["sign"], str):
        out["sign"] = out["sign"].strip().title()
    return out


def _normalize_natal_planet(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out = dict(raw)
    if "sign_index" in out:
        try:
            out["sign_index"] = int(out["sign_index"])
        except (ValueError, TypeError):
            pass
    elif "sign" in out:
        idx = sign_name_to_index(out["sign"])
        if idx is not None:
            out["sign_index"] = idx
    if "sign" in out and isinstance(out["sign"], str):
        out["sign"] = out["sign"].strip().title()
    return out


def _normalize_div_planet(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out = dict(raw)
    if "sign" in out and isinstance(out["sign"], str):
        out["sign"] = out["sign"].strip().title()
    if "sign" in out and "sign_index" not in out:
        idx = sign_name_to_index(out["sign"])
        if idx is not None:
            out["sign_index"] = idx
    return out


def _normalize_divisional_chart(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Any] = {}

    lagna_raw = raw.get("lagna")
    if isinstance(lagna_raw, str):
        out["lagna"] = lagna_raw.strip().title()
        idx = sign_name_to_index(lagna_raw)
        if idx is not None:
            out["lagna_index"] = idx
    elif isinstance(lagna_raw, int) and 0 <= lagna_raw <= 11:
        out["lagna_index"] = lagna_raw
        out["lagna"] = SIGN_NAMES[lagna_raw]

    for field in ("meaning", "lagna_lord"):
        if field in raw:
            out[field] = raw[field]

    planets_raw = raw.get("planets") or {}
    if isinstance(planets_raw, dict):
        out["planets"] = {
            canonical_planet_name(k): _normalize_div_planet(v)
            for k, v in planets_raw.items()
        }
    elif isinstance(planets_raw, list):
        pd: Dict[str, Any] = {}
        for p in planets_raw:
            if isinstance(p, dict):
                name = canonical_planet_name(p.get("name") or p.get("planet", "Unknown"))
                pd[name] = _normalize_div_planet(p)
        out["planets"] = pd

    for k, v in raw.items():
        if k not in ("lagna", "meaning", "lagna_lord", "planets"):
            out[k] = v

    return out


def normalize_chart_data(raw: Any) -> Dict[str, Any]:
    """
    Normalize chart_data JSONB from the charts table.
    Accepts real production shape, returns canonical dict for JSON context builder.
    Does NOT touch lal_kitab_data or jaimini_data (separate columns).
    """
    if not isinstance(raw, dict):
        return {}

    out: Dict[str, Any] = {}

    if "lagna" in raw:
        out["lagna"] = _normalize_lagna(raw["lagna"])

    planets_raw = raw.get("planets") or {}
    if isinstance(planets_raw, dict):
        out["planets"] = {
            canonical_planet_name(k): _normalize_natal_planet(v)
            for k, v in planets_raw.items()
        }

    div_raw = raw.get("divisional_charts") or {}
    if isinstance(div_raw, dict):
        canonical_div: Dict[str, Any] = {}
        for key, val in div_raw.items():
            canonical_key = _DIV_KEY_ALIASES.get(key, key.lower())
            canonical_div[canonical_key] = _normalize_divisional_chart(val)
        out["divisional_charts"] = canonical_div

    for field in ("yogas", "house_lords", "house_analysis", "birth_jd",
                  "atmakaraka", "yogas_prompt_block", "lagna_sign",
                  "lagna_degree", "house_cusps", "ayanamsa"):
        if field in raw:
            out[field] = raw[field]

    return out


def get_divisional(chart_data: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Safe read of a divisional chart. Accepts 'd9' or 'D9'. Returns {} if missing."""
    divs = chart_data.get("divisional_charts") or {}
    canonical = _DIV_KEY_ALIASES.get(key, key.lower())
    return divs.get(canonical) or divs.get(key) or {}


def _run_tests() -> None:
    print("Running chart_schema unit tests (real schema)...\n")

    real_shape = {
        "lagna": {"sign": "Capricorn", "degree": 24.69, "sign_index": 9},
        "planets": {
            "Sun": {"sign": "Scorpio", "house": 11, "degree": 10.1,
                    "sign_index": 7, "nakshatra": "Anuradha", "nakshatra_lord": "Saturn"}
        },
        "divisional_charts": {
            "d1": {"lagna": "Capricorn", "meaning": "D1", "planets": {
                "Sun": {"sign": "Scorpio", "house": 11, "sign_lord": "Mars"}
            }},
            "d9": {"lagna": "Leo", "meaning": "Navamsa", "planets": {
                "Sun": {"sign": "Libra", "house": 3, "sign_lord": "Venus"}
            }},
        },
        "yogas": [],
    }
    cd = normalize_chart_data(real_shape)
    assert cd["lagna"]["sign_index"] == 9
    assert cd["lagna"]["sign"] == "Capricorn"
    assert cd["planets"]["Sun"]["sign_index"] == 7
    assert "d1" in cd["divisional_charts"]
    assert "d9" in cd["divisional_charts"]
    assert cd["divisional_charts"]["d9"]["lagna"] == "Leo"
    assert cd["divisional_charts"]["d9"]["lagna_index"] == 4
    assert cd["divisional_charts"]["d9"]["planets"]["Sun"]["sign_index"] == 6
    print("✅ Test 1: real production shape normalizes correctly")

    raw2 = {"divisional_charts": {
        "D9": {"lagna": "Leo", "planets": {}},
        "D10": {"lagna": "Capricorn", "planets": {}},
    }}
    cd2 = normalize_chart_data(raw2)
    assert "d9" in cd2["divisional_charts"]
    assert "D9" not in cd2["divisional_charts"]
    assert "d10" in cd2["divisional_charts"]
    print("✅ Test 2: uppercase D9/D10 -> lowercase d9/d10")

    raw3 = {"lagna": {"sign": "Aries", "degree": 5.0}}
    cd3 = normalize_chart_data(raw3)
    assert cd3["lagna"]["sign_index"] == 0
    print("✅ Test 3: lagna sign_index computed from name when missing")

    raw4 = {"divisional_charts": {"d9": {"lagna": "Virgo", "planets": {}}}}
    cd4 = normalize_chart_data(raw4)
    assert cd4["divisional_charts"]["d9"]["lagna_index"] == 5
    print("✅ Test 4: divisional chart lagna_index added from sign name")

    raw5 = {"divisional_charts": {"d9": {"lagna": "Leo", "planets": {
        "moon": {"sign": "Taurus", "house": 2, "sign_lord": "Venus"}
    }}}}
    cd5 = normalize_chart_data(raw5)
    moon = cd5["divisional_charts"]["d9"]["planets"]["Moon"]
    assert moon["sign_index"] == 1
    assert moon["sign"] == "Taurus"
    print("✅ Test 5: sign_index added to divisional planets, Moon canonicalized")

    assert get_divisional(cd2, "D9") == get_divisional(cd2, "d9")
    assert get_divisional(cd2, "d99") == {}
    print("✅ Test 6: get_divisional accepts D9 or d9, returns {} for missing")

    raw7 = {"divisional_charts": {
        "d1": {"lagna": "Aries", "planets": {}, "extra": "preserved"}
    }}
    cd7 = normalize_chart_data(raw7)
    assert cd7["divisional_charts"]["d1"]["extra"] == "preserved"
    print("✅ Test 7: unknown keys inside sub-dicts preserved")

    raw8 = {"divisional_charts": {"d1": {"lagna": "Aries", "planets": {
        "sun": {"sign": "Leo", "house": 1},
        "MOON": {"sign": "Cancer", "house": 4},
    }}}}
    cd8 = normalize_chart_data(raw8)
    planets8 = cd8["divisional_charts"]["d1"]["planets"]
    assert "Sun" in planets8
    assert "Moon" in planets8
    print("✅ Test 8: planet names canonicalized to Title-case")

    print("\n✅ All tests passed.")


if __name__ == "__main__":
    _run_tests()
