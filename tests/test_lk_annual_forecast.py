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


def test_good_bad_only_where_the_books_do_not_contradict():
    from antar_engine.lk_annual_forecast import GOOD_PLACE, BAD_PLACE, EARLY_GOOD, EARLY_BAD, GOSVAMI_BAD
    for p in GOSVAMI_BAD:
        assert not (GOOD_PLACE[p] & BAD_PLACE[p])
        assert not (GOOD_PLACE[p] & EARLY_BAD.get(p, set()))      # early books call it bad -> not good
        assert not (BAD_PLACE[p] & EARLY_GOOD.get(p, set()))      # early books call it good -> not bad
    assert 8 not in GOOD_PLACE["Jupiter"] and 8 not in BAD_PLACE["Jupiter"]   # disputed: left out
    assert 9 in GOOD_PLACE["Jupiter"] and 9 not in GOOD_PLACE["Venus"]   # Venus 9: books disagree
    assert 5 in GOOD_PLACE["Sun"]                                  # book-only cell, no conflict
