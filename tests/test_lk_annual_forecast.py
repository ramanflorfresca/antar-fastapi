from antar_engine import rc_rules as rc
from antar_engine.lk_annual_forecast import lk_annual_forecast, PRINCIPLE
from antar_engine.lk_year_lord import year_lord_for_running_year, year_lord_by_age

NATAL = {"planets": {"Sun": {"house": 5}, "Moon": {"house": 1}, "Mars": {"house": 10}, "Mercury": {"house": 5},
                     "Jupiter": {"house": 5}, "Venus": {"house": 5}, "Saturn": {"house": 3}, "Rahu": {"house": 3},
                     "Ketu": {"house": 10}}}


def test_year_lord_follows_the_age_cycle():
    assert [year_lord_for_running_year(r) for r in (1, 6, 7, 13, 16, 22, 24, 25, 28, 34, 36, 42, 48, 51, 57)] == [
        "Saturn", "Saturn", "Rahu", "Ketu", "Jupiter", "Sun", "Moon", "Venus", "Mars", "Mercury", "Saturn", "Rahu",
        "Ketu", "Jupiter", "Sun"]
    from datetime import date
    assert year_lord_by_age("1974-11-26", date(2026, 10, 13)) == "Jupiter"       # age 51 completed -> 52nd year
    assert year_lord_by_age("garbage") == ""


def test_annual_forecast_applies_only_the_rules_whose_conditions_hold(monkeypatch):
    rules = [
        {"id": "A1", "kind": "annual", "planet": "Moon", "annual_houses": [10], "requires": [{"planet": "Moon", "in": [1]}],
         "tone": "good", "topics": ["money"], "effect": "Gains come this year.", "effect_es": "Llegan ganancias este año.",
         "remedy": None, "clarity": "clear"},
        {"id": "A2", "kind": "annual", "planet": "Moon", "annual_houses": [10], "requires": [{"planet": "Moon", "in": [7]}],
         "tone": "bad", "topics": ["money"], "effect": "Losses this year.", "clarity": "clear"},
        {"id": "A3", "kind": "annual", "planet": "Moon", "annual_houses": [5], "requires": [], "tone": "bad",
         "topics": ["money"], "effect": "Wrong annual house.", "clarity": "clear"},
        {"id": "N1", "kind": "natal", "planet": "Moon", "houses": [1], "requires": [], "tone": "good",
         "topics": ["money"], "effect": "A natal rule is not an annual one.", "clarity": "clear"},
    ]
    monkeypatch.setattr(rc, "_cache", rules)
    # find an age at which the natal-1 Moon reaches annual house 10
    from antar_engine.varshaphal_table import get_annual_house
    age = next(a for a in range(0, 99) if get_annual_house(1, a) == 10)
    a = lk_annual_forecast(NATAL, age)
    assert [i["id"] for i in a["rc"]] == ["A1"]
    assert a["rc"][0]["es"] == "Llegan ganancias este año." and a["rc"][0]["subjects"] == ["money"]
    assert a == lk_annual_forecast(NATAL, age)                                           # deterministic
    assert a["running_year"] == age + 1 and a["year_lord"]
    other = next(x for x in range(0, 99) if get_annual_house(1, x) != 10)
    assert lk_annual_forecast(NATAL, other)["rc"] == []
    assert "43" in PRINCIPLE["en"] and "43" in PRINCIPLE["es"]


def test_gender_gated_annual_rule(monkeypatch):
    from antar_engine.varshaphal_table import get_annual_house
    monkeypatch.setattr(rc, "_cache", [{"id": "G1", "kind": "annual", "planet": "Moon", "annual_houses": [10],
                                       "requires": [{"chart": "female"}], "tone": "good", "topics": ["children"],
                                       "effect": "A child is likely this year.", "clarity": "clear"}])
    age = next(a for a in range(0, 99) if get_annual_house(1, a) == 10)
    assert lk_annual_forecast(NATAL, age, gender="female")["rc"][0]["id"] == "G1"
    assert lk_annual_forecast(NATAL, age, gender="male")["rc"] == []
    assert lk_annual_forecast(NATAL, age)["rc"] == []
