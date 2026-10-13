from antar_engine.lal_kitab_events import lal_kitab_profile

SIGNS = {"Sun": 4, "Moon": 0, "Mars": 9, "Mercury": 4, "Jupiter": 4,
         "Venus": 4, "Saturn": 2, "Rahu": 2, "Ketu": 9}


def test_houses_are_sign_numbers_and_dormant_is_empty_and_unsighted():
    p = lal_kitab_profile(SIGNS, 38)
    assert p["houses"]["Sun"] == 5 and p["houses"]["Moon"] == 1
    for h in p["dormant_houses"]:
        assert h not in p["houses"].values()
    assert 7 not in p["dormant_houses"]  # Moon in 1 sights 7


def test_maturity_and_triggers():
    p = lal_kitab_profile({**SIGNS, "Jupiter": 1}, 38)   # Jupiter in house 2 -> big money at 39
    assert any(t["age"] == 39 and t["sign"] == "+" for t in p["age_triggers"])
    assert any(w["planet"] == "Saturn"
               for w in p["maturity_windows"])
    assert lal_kitab_profile(SIGNS, 38) == lal_kitab_profile(SIGNS, 38)


def test_speculation_flag():
    assert lal_kitab_profile({**SIGNS, "Rahu": 7}, 30)["speculation_tendency"]["flag"] in ("loss-prone", "mixed")
