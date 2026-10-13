from antar_engine.lk_annual_forecast import lk_annual_forecast

NATAL = {"planets": {"Sun": {"house": 5}, "Moon": {"house": 1}, "Mars": {"house": 10},
                     "Mercury": {"house": 5}, "Jupiter": {"house": 5}, "Venus": {"house": 5},
                     "Saturn": {"house": 3}, "Rahu": {"house": 3}, "Ketu": {"house": 10}}}


def test_annual_forecast_shape_and_determinism():
    a = lk_annual_forecast(NATAL, 45, "1981-03-02")
    assert a == lk_annual_forecast(NATAL, 45, "1981-03-02")
    assert set(a["annual_houses"]) == set(NATAL["planets"])
    assert all(1 <= h <= 12 for h in a["annual_houses"].values())
    assert a["running_year"] == 46
