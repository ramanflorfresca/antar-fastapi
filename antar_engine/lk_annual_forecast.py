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

# Planet-in-house verdicts from the two books (ledger section 3): where the books call the
# placement money/fortune-positive vs money/trouble-negative. The books contradict
# themselves in places; only placements listed on one side are classified.
GOOD_PLACE = {"Jupiter": {2, 3, 4, 9, 10, 11}, "Sun": {1, 3, 10}, "Moon": {4, 7, 11},
              "Venus": {2, 4, 7, 9, 11}, "Mars": {1, 7, 10}, "Mercury": {4, 7, 12},
              "Saturn": {6, 7, 11}, "Rahu": {3, 6, 10, 11}, "Ketu": {3, 10, 11}}
BAD_PLACE = {"Jupiter": {8, 12}, "Sun": {7, 8}, "Moon": {6}, "Venus": {12}, "Mars": {4, 8},
             "Mercury": {2, 8, 10}, "Saturn": {1, 2, 4, 5, 8, 9}, "Rahu": {1, 2, 8, 12},
             "Ketu": {1, 2, 12}}


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
    good = [{"planet": p, "house": h} for p, h in houses.items() if h in GOOD_PLACE.get(p, ())]
    bad = [{"planet": p, "house": h} for p, h in houses.items() if h in BAD_PLACE.get(p, ())]
    bad_planets = {b["planet"] for b in bad}
    troubled = [p for p, h in houses.items() if (p, h) in PAIN or p in bad_planets
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
            "good_placements": good, "bad_placements": bad,
            "blind": prof["blind"], "speculation_tendency": prof["speculation_tendency"],
            "remedies": remedies}
