"""
Lal Kitab annual (varshphal) forecast, deterministic, built on Pt. Roop Chand's annual-chart rules.

For one running year of life:
  - annual houses: where each natal planet moves this year (varshaphal_table.py; rows 1-100 are the printed
    matrix, which Roop Chand's compilation does not contain as a table)
  - the rules from his text about the year chart (kind "annual" in data/lk_roop_chand_rules.json) that APPLY:
    the planet reaches the annual house the rule names and every condition on the birth chart (and on the year chart,
    where the rule says so) holds. A rule whose condition is not met says nothing.
  - the remedies those rules attach, and his remedy principle (43 days, uninterrupted, daylight, one measure at a time)
  - the year lord by the age cycle (context only: his annual rules do not use it)
Nothing here claims accuracy; the text is untested. No LLM.
"""
from typing import Dict, List, Optional

from antar_engine import rc_rules as rc
from antar_engine.varshaphal_table import get_annual_house
from antar_engine.lk_year_lord import year_lord_for_running_year

PRINCIPLE = {
    "en": "Run a remedy for 43 days without a break, in daylight, one measure at a time. If you miss a day, start again.",
    "es": "Haz un remedio durante 43 días sin interrupción, a la luz del día, una medida a la vez. Si fallas un día, empieza de nuevo.",
}


def annual_houses(natal_houses: Dict[str, int], age_completed: int) -> Dict[str, int]:
    return {p: get_annual_house(h, age_completed) for p, h in natal_houses.items()}


def lk_annual_forecast(natal_chart: Dict, age: int, birth_date=None, today=None, gender: Optional[str] = None,
                       lagna_sign: Optional[str] = None) -> dict:
    """natal_chart: {"planets": {planet: {"house": LK house (fixed frame)}}}; age = years completed."""
    natal = {p: d["house"] for p, d in natal_chart["planets"].items()}
    annual = annual_houses(natal, age)
    state = {"natal": natal, "annual": annual, "gender": gender if gender in ("male", "female") else None,
             "lagna_sign": lagna_sign}
    items: List[dict] = []
    for r in rc.applying(state, kind="annual"):
        items.append({"id": r["id"], "tone": r["tone"] if r["tone"] in ("good", "bad") else "info",
                      "topics": r.get("topics", []), "subjects": rc.subjects_of(r), "planet": r.get("planet"),
                      "en": r["effect"], "es": r.get("effect_es"),
                      "remedy_en": r.get("remedy"), "remedy_es": r.get("remedy_es")})
    running = max(1, min(120, age + 1))
    return {"age": age, "running_year": running, "annual_houses": annual,
            "year_lord": year_lord_for_running_year(running), "special_cycle": None, "rc": items,
            "principle": PRINCIPLE}
