"""
antar_engine/varshphal_chart.py — Phase 1 canonical Varshphal (Teva) chart object.

Every Phase 2 LK rule reads from the object this module emits. It is a thin,
pure wrapper over the already-verified annual-progression table
(`varshaphal_table.get_annual_house`, Phase 0 audited: JHora anchor passes,
stored placements match the table at the stored age on all test charts).

DESIGN RULES (from Phase 0 audit + Phase 1 plan):
  * Age comes from ONE function — age_utils.calculate_current_age — never the
    legacy `(today - born).days // 365` path (latent off-by-one).
  * `annual_houses` (planet -> annual house) IS the Varshphal chart.
  * `year_lord` / `annual_house_lords` are STUBBED (None). The only "year_lord"
    in the codebase today is a Tajika-style weekday-ruler read at its NATAL
    house — that is NOT the LK year-lord. Per the brief, no invented rule
    content: these stay None until Raman supplies the canonical LK rule +
    LK-1/LK-2 citation.
  * `low_confidence` propagates an unverified lagna (wrong birth time ->
    wrong lagna -> wrong annual houses).
  * Annual houses 10–12 are JHora-verified only for RY 56/57 (Phase 0). The
    per-house `provisional` decision is made by the consuming rule, but this
    module exposes `H10_12_UNVERIFIED` so rules don't have to re-derive it.

This module performs NO IO and is safe to import anywhere.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Any, Dict, List, Optional

from antar_engine.varshaphal_table import get_annual_house
from antar_engine.age_utils import calculate_current_age

# Annual houses above H9 are only JHora-verified for RY 56 & 57 (Phase 0 audit).
# Rules that read a planet's annual house in this set should mark it provisional.
H10_12_UNVERIFIED = {10, 11, 12}

_ALL_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                "Venus", "Saturn", "Rahu", "Ketu")


def _natal_houses_from_chart(natal_chart: Dict[str, Any]) -> Dict[str, int]:
    """Extract {planet -> natal house} from a stored chart_data dict.

    Accepts the canonical chart_data shape: {"planets": {name: {"house": int,
    ...}}}. Planets with a missing/out-of-range house are dropped (the annual
    table is only defined for natal houses 1..12)."""
    planets = (natal_chart or {}).get("planets", {})
    out: Dict[str, int] = {}
    for name, pdata in planets.items():
        if not isinstance(pdata, dict):
            continue
        h = pdata.get("house")
        if isinstance(h, int) and 1 <= h <= 12:
            out[name] = h
    return out


def _birthday_window(birth_date: str, on_date: _date) -> (str, str):
    """Return (period_start, period_end) ISO strings for the Varshphal year
    that CONTAINS on_date — i.e. the most recent birthday up to on_date, and
    the following birthday. Handles Feb-29 births by clamping to Feb-28."""
    bd = _date.fromisoformat(str(birth_date)[:10])

    def _safe_bday(year: int) -> _date:
        try:
            return bd.replace(year=year)
        except ValueError:        # Feb 29 in a non-leap year
            return bd.replace(year=year, day=28)

    this_year_bday = _safe_bday(on_date.year)
    if on_date >= this_year_bday:
        start = this_year_bday
        end = _safe_bday(on_date.year + 1)
    else:
        start = _safe_bday(on_date.year - 1)
        end = this_year_bday
    return start.isoformat(), end.isoformat()


def build_varshphal_chart(
    natal_chart: Dict[str, Any],
    birth_date: str,
    on_date: Optional[_date] = None,
    lagna_verified: bool = True,
) -> Dict[str, Any]:
    """Build the canonical Varshphal chart object for the year containing
    `on_date` (defaults to today).

    Returns a dict with:
      year_key, age, period_start, period_end,
      annual_houses        : {planet -> annual house}            (the Teva chart)
      annual_occupants     : {house -> [planets]}                (rule convenience)
      year_lord            : None  (SOURCE NEEDED — LK rule + citation owed)
      annual_house_lords   : None  (SOURCE NEEDED)
      low_confidence       : bool  (unverified lagna)
      source               : provenance string
    """
    if on_date is None:
        on_date = _date.today()

    age = calculate_current_age(str(birth_date)[:10])     # age at last birthday
    natal_houses = _natal_houses_from_chart(natal_chart)

    annual_houses: Dict[str, int] = {
        planet: get_annual_house(h, age)
        for planet, h in natal_houses.items()
    }

    annual_occupants: Dict[int, List[str]] = {}
    for planet, h in annual_houses.items():
        annual_occupants.setdefault(h, []).append(planet)

    period_start, period_end = _birthday_window(birth_date, on_date)
    birthday_year = int(period_start[:4])

    return {
        "year_key": f"{birthday_year}-{birthday_year + 1}",
        "age": age,
        "running_year": max(1, min(120, age + 1)),
        "period_start": period_start,
        "period_end": period_end,
        "annual_houses": annual_houses,
        "annual_occupants": annual_occupants,
        # SOURCE NEEDED — do not populate from the weekday-lord construct.
        "year_lord": None,
        "annual_house_lords": None,
        "low_confidence": (not lagna_verified),
        "source": (
            "LK annual progression: varshaphal_table.get_annual_house "
            "(H1-H9 verified all ages; H10-H12 JHora-verified RY56/57 only)"
        ),
    }
