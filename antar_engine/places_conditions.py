"""
antar_engine/places_conditions.py
─────────────────────────────────────────────────────────────────────────────
PLACES — natal condition (dignity) layer.  Phase 1.

Each natal planet gets one condition that colours and weights its
astrocartography lines.  Conditions are birth-locked (cache per chart).

The dignity / friendship constants mirror the canonical tables already in
astar_engine (astrological_rules.OWN_SIGNS/EXALT_SIGNS/DEBIT_SIGNS,
d_charts_calculator.SIGN_LORDS, Compatibility.PLANET_FRIENDS).  They are
reproduced locally so this module imports cheaply and stays testable in
isolation; sleeping detection is delegated live to lal_kitab_advanced.
"""

from __future__ import annotations

from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Condition weights / colours / polarity  (LOCKED by contract)
# ─────────────────────────────────────────────────────────────────────────────

CONDITION_WEIGHTS: dict[str, dict] = {
    "exalted":     {"weight": 1.5, "color": "teal_bright",  "polarity": "supportive"},
    "own_sign":    {"weight": 1.3, "color": "teal",         "polarity": "supportive"},
    "friend":      {"weight": 1.0, "color": "teal_dim",     "polarity": "supportive"},
    "neutral":     {"weight": 0.9, "color": "neutral_grey", "polarity": "mixed"},
    "enemy":       {"weight": 0.7, "color": "amber",        "polarity": "mixed"},
    "debilitated": {"weight": 0.4, "color": "amber_strong", "polarity": "friction"},
    "combust":     {"weight": 0.3, "color": "amber_dim",    "polarity": "friction"},
    "sleeping":    {"weight": 0.5, "color": "purple_dim",   "polarity": "mixed"},
}

# [places-condition 2026-10-12] Neecha Bhanga lifts a debilitated planet from 0.4
# to roughly an enemy-sign planet; vargottama adds a modest bonus (capped at 1.5).
_CANCELLED_DEBILITY_WEIGHT = 0.9
_VARGOTTAMA_BONUS = 0.2

# Sign indices: 0 = Aries .. 11 = Pisces
EXALT_SIGNS = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6,
}
DEBIL_SIGNS = {
    "Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11,
    "Jupiter": 9, "Venus": 5, "Saturn": 0,
}
OWN_SIGNS = {
    "Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
    "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
}

SIGN_LORDS_BY_INDEX = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon", 4: "Sun", 5: "Mercury",
    6: "Venus", 7: "Mars", 8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter",
}

PLANET_FRIENDS = {
    "Sun":     {"friends": ["Moon", "Mars", "Jupiter"], "neutral": ["Mercury"], "enemies": ["Venus", "Saturn", "Rahu", "Ketu"]},
    "Moon":    {"friends": ["Sun", "Mercury"], "neutral": ["Mars", "Jupiter", "Venus", "Saturn"], "enemies": ["Rahu", "Ketu"]},
    "Mars":    {"friends": ["Sun", "Moon", "Jupiter"], "neutral": ["Venus", "Saturn"], "enemies": ["Mercury", "Rahu", "Ketu"]},
    "Mercury": {"friends": ["Sun", "Venus"], "neutral": ["Mars", "Jupiter", "Saturn"], "enemies": ["Moon", "Rahu", "Ketu"]},
    "Jupiter": {"friends": ["Sun", "Moon", "Mars"], "neutral": ["Saturn"], "enemies": ["Mercury", "Venus", "Rahu", "Ketu"]},
    "Venus":   {"friends": ["Mercury", "Saturn"], "neutral": ["Mars", "Jupiter"], "enemies": ["Sun", "Moon", "Rahu", "Ketu"]},
    "Saturn":  {"friends": ["Mercury", "Venus"], "neutral": ["Jupiter"], "enemies": ["Sun", "Moon", "Mars", "Rahu", "Ketu"]},
    "Rahu":    {"friends": ["Venus", "Saturn"], "neutral": ["Mercury", "Jupiter"], "enemies": ["Sun", "Moon", "Mars"]},
    "Ketu":    {"friends": ["Mars", "Jupiter"], "neutral": ["Venus", "Saturn"], "enemies": ["Sun", "Moon", "Mercury"]},
}

# Combustion orbs (deg).  Only these bodies can be combust (contract-locked).
COMBUST_ORBS = {
    "Mercury": 12.0, "Venus": 8.0, "Mars": 17.0, "Jupiter": 11.0, "Saturn": 15.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ang_sep(a: float, b: float) -> float:
    """Smallest separation between two ecliptic longitudes (0..180)."""
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def _planet_record(chart: dict, planet: str) -> dict:
    return (chart or {}).get("planets", {}).get(planet, {}) or {}


def _sign_index(rec: dict) -> Optional[int]:
    si = rec.get("sign_index")
    if si is not None:
        try:
            return int(si)
        except (TypeError, ValueError):
            pass
    # Derive from longitude if sign_index is absent.
    lon = rec.get("longitude")
    if lon is not None:
        try:
            return int((float(lon) % 360.0) // 30.0)
        except (TypeError, ValueError):
            pass
    return None


def _sleeping_set(chart: dict) -> set:
    """Planets currently 'sleeping' per the Lal Kitab detector."""
    planets = (chart or {}).get("planets", {})
    if not planets:
        return set()
    try:
        from antar_engine.lal_kitab_advanced import detect_sleeping_planets
        return {s["planet"] for s in detect_sleeping_planets(planets)}
    except Exception:
        return set()


def _kendra_from(a: int, b: int) -> bool:
    """True when sign index `a` is in a kendra (1/4/7/10) counted from sign `b`."""
    return ((a - b) % 12) in (0, 3, 6, 9)


def neecha_bhanga(planet: str, chart: dict) -> bool:
    """[places-condition 2026-10-12] Cancellation of debilitation. A debilitated
    planet is rescued when any of these sits in a kendra from the lagna or from
    the Moon: (A) the lord of the sign it is debilitated in; (B) the lord of the
    sign it would be exalted in; (C) a planet exalted in its debilitation sign.
    False when the planet is not debilitated or the data is missing."""
    rec = _planet_record(chart, planet)
    si = _sign_index(rec)
    deb = DEBIL_SIGNS.get(planet)
    if si is None or deb is None or si != deb:
        return False
    try:
        from antar_engine.places_relocation import _natal_lagna_index
        lagna = _natal_lagna_index(chart)
    except Exception:
        lagna = None
    moon = _sign_index(_planet_record(chart, "Moon"))
    refs = [r for r in (lagna, moon) if r is not None]
    if not refs:
        return False
    cands = {SIGN_LORDS_BY_INDEX[deb], SIGN_LORDS_BY_INDEX[EXALT_SIGNS[planet]]}
    cands |= {p2 for p2, ex in EXALT_SIGNS.items() if ex == deb}
    cands.discard(planet)
    for c in cands:
        ci = _sign_index(_planet_record(chart, c))
        if ci is not None and any(_kendra_from(ci, r) for r in refs):
            return True
    return False


def is_vargottama(planet: str, chart: dict) -> bool:
    """Same sign in the birth chart (D-1) and the navamsa (D-9)."""
    rec = _planet_record(chart, planet)
    si, lon = _sign_index(rec), rec.get("longitude")
    if si is None or lon is None:
        return False
    try:
        from antar_engine.antar_ephemeris import _divisional_sign_index
        return (_divisional_sign_index(float(lon), 9) % 12) == si
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Public
# ─────────────────────────────────────────────────────────────────────────────

def compute_natal_condition(
    planet: str,
    chart: dict,
    _sleeping: Optional[set] = None,
) -> str:
    """
    Return one of:
        exalted | own_sign | friend | neutral | enemy |
        debilitated | combust | sleeping

    Precedence (first match wins):
      1. exalted      2. debilitated   3. combust
      4. own_sign     5. sleeping      6. friend|neutral|enemy
    """
    rec = _planet_record(chart, planet)
    si = _sign_index(rec)

    # 1. exalted
    if si is not None and EXALT_SIGNS.get(planet) == si:
        return "exalted"

    # 2. debilitated
    if si is not None and DEBIL_SIGNS.get(planet) == si:
        return "debilitated"

    # 3. combust  (only the contract-listed bodies; needs Sun's longitude)
    if planet in COMBUST_ORBS:
        plon = rec.get("longitude")
        sun_lon = _planet_record(chart, "Sun").get("longitude")
        if plon is not None and sun_lon is not None:
            try:
                if _ang_sep(float(plon), float(sun_lon)) <= COMBUST_ORBS[planet]:
                    return "combust"
            except (TypeError, ValueError):
                pass

    # 4. own sign
    if si is not None and si in OWN_SIGNS.get(planet, []):
        return "own_sign"

    # 5. sleeping
    sleeping = _sleeping if _sleeping is not None else _sleeping_set(chart)
    if planet in sleeping:
        return "sleeping"

    # 6. friend / neutral / enemy — relative to the lord of the occupied sign
    if si is not None:
        sign_lord = SIGN_LORDS_BY_INDEX.get(si)
        rel = PLANET_FRIENDS.get(planet, {})
        if sign_lord:
            if sign_lord in rel.get("friends", []):
                return "friend"
            if sign_lord in rel.get("enemies", []):
                return "enemy"
        return "neutral"

    return "neutral"


def condition_meta(condition: str) -> dict:
    """Weight / colour / polarity for a condition (safe default = neutral)."""
    return CONDITION_WEIGHTS.get(condition, CONDITION_WEIGHTS["neutral"])


def compute_all_conditions(chart: dict) -> dict[str, dict]:
    """
    Condition + weight + colour + polarity for every natal planet.

    Returns:
        { "Saturn": {"condition": "exalted", "weight": 1.5,
                     "color": "teal_bright", "polarity": "supportive"}, ... }
    """
    from antar_engine.places_lines import PLANETS

    sleeping = _sleeping_set(chart)
    out: dict[str, dict] = {}
    for planet in PLANETS:
        if planet not in (chart or {}).get("planets", {}):
            continue
        cond = compute_natal_condition(planet, chart, _sleeping=sleeping)
        meta = condition_meta(cond)
        weight, polarity = meta["weight"], meta["polarity"]
        # Neecha Bhanga: a rescued debilitation is no longer a friction planet.
        # The condition NAME stays "debilitated" (many surfaces key on it); only
        # the weight/polarity move, plus an explicit flag.
        cancelled = cond == "debilitated" and neecha_bhanga(planet, chart)
        if cancelled:
            weight, polarity = _CANCELLED_DEBILITY_WEIGHT, "mixed"
        # Vargottama: strong in the navamsa too (planets already at the cap stay).
        varg = is_vargottama(planet, chart)
        if varg:
            weight = min(1.5, weight + _VARGOTTAMA_BONUS)
        out[planet] = {
            "condition": cond,
            "weight": weight,
            "color": meta["color"],
            "polarity": polarity,
            "cancelled": cancelled,
            "vargottama": varg,
        }
    return out
