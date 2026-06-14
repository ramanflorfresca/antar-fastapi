"""
antar_engine/lk_rules/sleeping.py — Rule 1: LK sleeping-planet engine.

Dual sleep + maturity gate. This is the template for the rest of Phase 2.

THE ANTI-GENERIC MECHANISM
  A planet gets TWO independent sleep checks, both using the SAME existing LK
  sleeping-condition function (lal_kitab_advanced.detect_sleeping_planets) on
  TWO different chart inputs:
    natal_sleep   = sleep over the NATAL houses   (structural / chronic)
    annual_sleep  = sleep over the VARSHPHAL annual houses (moves every birthday)
  Because annual_sleep is recomputed against the Varshphal chart, "This Year"
  changes year to year instead of echoing the natal chart.

MATURITY GATE
  The annual-sleep awaken-remedy only fires once the planet has reached its LK
  maturity age (lk_rules.maturity). An OPENING (annual = awake) is NOT maturity
  gated — an opening is an opening.

PROVENANCE
  maturity: Goswami 1952 / Mahajan 2014
  sleep:    lal_kitab_advanced.detect_sleeping_planets (LK_SLEEPING_PLANET table)

NOTE: detect_sleeping_planets' own sleeping-condition is reused AS-IS so natal
and annual stay consistent. If that condition is later found to need source
verification, that is a separate validation pass — flagged, not blocking here.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from antar_engine.lal_kitab_advanced import (
    detect_sleeping_planets,
    LK_SLEEPING_PLANET,
    BENEFICS,
)
from antar_engine.lk_rules.maturity import LK_MATURITY_AGE, is_mature
from antar_engine.varshphal_chart import H10_12_UNVERIFIED

# Outcome labels
PRIORITY_AWAKEN = "PRIORITY_AWAKEN"          # natal sleep + annual sleep (+ mature)
YEAR_CAUTION_AWAKEN = "YEAR_CAUTION_AWAKEN"  # natal awake -> annual sleep (+ mature)
OPENING = "OPENING"                          # natal sleep -> annual awake
SUPPRESSED_IMMATURE = "SUPPRESSED_IMMATURE"  # annual sleep but planet immature
CLEAR = "CLEAR"                              # awake both — nothing fires

# Ranking for the year-level list (higher = surfaced first).
SLEEP_OUTCOME_RANK = {
    PRIORITY_AWAKEN: 3,
    YEAR_CAUTION_AWAKEN: 2,
    OPENING: 1,
    SUPPRESSED_IMMATURE: 0,
    CLEAR: 0,
}

_SOURCE = ("LK maturity: Goswami1952/Mahajan2014; "
           "sleep: lal_kitab_advanced.detect_sleeping_planets")


def _sleeping_name_set(planets_by_house: Dict[str, Dict[str, Any]]) -> set:
    """Run the existing LK sleep determination and return the SET of sleeping
    planet names. `planets_by_house` is {planet: {"house": int, ...}}."""
    rows = detect_sleeping_planets(planets_by_house or {})
    return {r["planet"] for r in rows if isinstance(r, dict) and r.get("planet")}


def _natal_planets_map(natal_chart: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """{planet: {"house":int, "sign":str}} from chart_data, houses 1..12 only."""
    out: Dict[str, Dict[str, Any]] = {}
    for name, pdata in (natal_chart or {}).get("planets", {}).items():
        if not isinstance(pdata, dict):
            continue
        h = pdata.get("house")
        if isinstance(h, int) and 1 <= h <= 12:
            out[name] = {"house": h, "sign": pdata.get("sign", "")}
    return out


def _resolve_outcome(natal_sleep: bool, annual_sleep: bool, matured: bool):
    """Cross-product resolution. Returns (outcome, remedy_fires, light)."""
    if annual_sleep:
        if not matured:
            return SUPPRESSED_IMMATURE, False, False
        if natal_sleep:
            return PRIORITY_AWAKEN, True, False
        return YEAR_CAUTION_AWAKEN, True, False
    # annual awake
    if natal_sleep:
        return OPENING, True, True          # opening — light / opportunity framing
    return CLEAR, False, False


def evaluate_sleeping_planets(
    varshphal_chart: Dict[str, Any],
    natal_chart: Dict[str, Any],
) -> Dict[str, Any]:
    """Rule 1 entry point.

    Returns:
      {
        "rule": "sleeping_planets",
        "per_planet": [ {planet schema, all 9 evaluated planets}, ... ],
        "firing": [ planets where remedy_fires, ranked ],
        "source": "...",
      }
    Pure — no IO. Reads only the Phase 1 vc object + natal chart_data.
    """
    age = int(varshphal_chart.get("age", 0))
    annual_houses: Dict[str, int] = varshphal_chart.get("annual_houses", {}) or {}
    vc_low_conf = bool(varshphal_chart.get("low_confidence", False))

    natal_map = _natal_planets_map(natal_chart)
    natal_sleep_set = _sleeping_name_set(natal_map)
    annual_map = {p: {"house": h} for p, h in annual_houses.items()}
    annual_sleep_set = _sleeping_name_set(annual_map)

    per_planet: List[Dict[str, Any]] = []
    for planet in LK_MATURITY_AGE.keys():           # all 9 grahas, deterministic order
        if planet not in annual_houses:
            continue                                # planet absent from this chart
        n_sleep = planet in natal_sleep_set
        a_sleep = planet in annual_sleep_set
        matured = is_mature(planet, age)
        outcome, fires, light = _resolve_outcome(n_sleep, a_sleep, matured)
        a_house = annual_houses[planet]
        provisional = a_house in H10_12_UNVERIFIED

        # Remedy: the planet-specific LK AWAKENING remedy (source-cited),
        # NOT the generic weekly-practice archetype table. The house-lord-
        # specific refinement (per annual house) is deferred to Phase 3 once
        # vc.annual_house_lords lands — exposed as remedy_basis for that swap.
        remedy_hint = (LK_SLEEPING_PLANET.get(planet, {}).get("awakening", "")
                       if fires else "")
        per_planet.append({
            "planet": planet,
            "natal_sleep": n_sleep,
            "annual_sleep": a_sleep,
            "annual_house": a_house,
            "matured": matured,
            "maturity_age": LK_MATURITY_AGE[planet],
            "user_age": age,
            "outcome": outcome,
            "remedy_fires": fires,
            "light": light,
            "remedy_hint": remedy_hint,
            "remedy_basis": {"planet": planet, "annual_house": a_house,
                             "kind": "annual_house_lord_remedy_PENDING"},
            "provisional": provisional,          # annual house 10-12 unverified
            "low_confidence": vc_low_conf,        # unverified lagna
            "is_benefic": planet in BENEFICS,
            "source": _SOURCE,
        })

    firing = [p for p in per_planet if p["remedy_fires"]]
    firing.sort(key=lambda p: (
        SLEEP_OUTCOME_RANK.get(p["outcome"], 0),
        0 if p["provisional"] else 1,            # verified before provisional
        p["is_benefic"],                          # benefic awakenings first within tier
    ), reverse=True)

    return {
        "rule": "sleeping_planets",
        "per_planet": per_planet,
        "firing": firing,
        "source": _SOURCE,
    }
