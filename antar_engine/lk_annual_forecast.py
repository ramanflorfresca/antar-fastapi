"""
Lal Kitab annual (varshphal) forecast + remedies, deterministic. Builds on the engine's
authentic varshphal table (lal_kitab.calculate_varshphal_chart) and remedy catalogue
(lal_kitab.get_remedies_for_planet); adds the books' dormant-house / blindness / tendency
reading on the ANNUAL chart and maps annual house occupancy to life events.
Every fired rule has a stable id for later feedback grading. No LLM, no accuracy gate.
"""
from typing import Dict, List

from antar_engine.lal_kitab import calculate_varshphal_chart, get_remedies_for_planet
from antar_engine.lal_kitab_events import lal_kitab_profile
from antar_engine.lal_kitab_advanced import year_lord_for

# annual house occupied -> life area opened this year (house meanings used by LK)
EVENT_HOUSES = {
    "marriage_partnership": 7, "children": 5, "career_status": 10,
    "income_gains": 11, "savings_family": 2, "home_property": 4,
    "foreign_expense": 12, "luck_dharma": 9,
}
PAIN = {("Mars", 2), ("Mercury", 8), ("Jupiter", 12), ("Venus", 1)}


def lk_annual_forecast(natal_chart: Dict, age: int, birth_date=None, today=None) -> dict:
    v = calculate_varshphal_chart(natal_chart, age)
    houses = v.placements                                   # planet -> annual house
    prof = lal_kitab_profile({p: h - 1 for p, h in houses.items()}, age, horizon=0)

    areas: List[dict] = []
    for area, h in EVENT_HOUSES.items():
        occ = sorted(p for p, ph in houses.items() if ph == h)
        if occ:
            areas.append({"rule": f"LK.annual_house_{h}_occupied", "area": area, "house": h,
                          "planets": occ})
    dormant_areas = [{"rule": "LK.annual_house_dormant", "area": a, "house": h}
                     for a, h in EVENT_HOUSES.items() if h in prof["dormant_houses"]]

    yl = year_lord_for(birth_date, today) if birth_date else None
    troubled = [p for p, h in houses.items() if (p, h) in PAIN
                or (prof["speculation_tendency"]["flag"] != "none"
                    and f"{p} in {h}" in prof["speculation_tendency"]["loss_placements"])]
    if yl and yl not in troubled and yl in houses:
        troubled.append(yl)                                  # year lord is always tended
    remedies = {}
    for p in troubled:
        rs = get_remedies_for_planet(p, houses[p])
        if rs:
            remedies[p] = [{"name": r.name, "do": r.instructions, "duration": r.duration,
                            "timing": r.timing, "materials": r.materials} for r in rs]
    return {"age": age, "running_year": v.table_age, "annual_houses": houses,
            "year_lord": yl, "special_cycle": v.cycle_significance,
            "opened_areas": areas, "dormant_areas": dormant_areas,
            "blind": prof["blind"], "speculation_tendency": prof["speculation_tendency"],
            "remedies": remedies}
