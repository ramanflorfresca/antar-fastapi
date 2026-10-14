from antar_engine import kp_rules

CH = {"cusps": {7: {"sub_lord": "Venus", "star_lord": "Moon", "sign_lord": "Venus"}},
      "planets": {"Venus": {"house": 5, "star_lord": "Mars", "sub_lord": "Sun", "sign_lord": "Venus"},
                  "Mars": {"house": 2, "star_lord": "Sun", "sub_lord": "Moon", "sign_lord": "Mars"}}}
ST = {"chart": CH, "sig": {"Venus": [2, 7], "Mars": [11]}, "gender": "female", "periods": None}


def test_cusp_sub_lord_modes():
    assert kp_rules.holds({"frame": "kp", "cusp": 7, "sub_lord_signifies": [7, 11], "mode": "any"}, ST)
    assert not kp_rules.holds({"frame": "kp", "cusp": 7, "sub_lord_signifies": [7, 11], "mode": "all"}, ST)
    assert kp_rules.holds({"frame": "kp", "cusp": 7, "sub_lord_signifies": [6, 8], "mode": "none"}, ST)


def test_planet_clauses_and_silence():
    assert kp_rules.holds({"frame": "kp", "planet": "Venus", "star_lord": "Mars"}, ST)
    assert kp_rules.holds({"frame": "kp", "planet": "Venus", "star_lord_signifies": [11]}, ST)
    assert not kp_rules.holds({"frame": "kp", "planet": "Venus", "in_house": [1]}, ST)
    assert not kp_rules.holds({"unparsed": "x"}, ST)
    assert not kp_rules.holds({"planet": "Venus", "in_houses": [5]}, ST)  # not kp frame: never holds


def test_standing_vs_timed_split_on_real_chart():
    import swisseph as swe
    from antar_engine.kp.kp_chart import compute_kp_chart
    st = kp_rules.kp_state(compute_kp_chart("1985-03-14", "10:30", 40.7, -74.0, tz_offset=-5), "male")
    cu = st["chart"]["cusps"][7]["sub_lord"]
    mine = {"id": "a", "requires": [{"frame": "kp", "cusp": 7, "sub_lord": cu}], "activation": []}
    timed = {**mine, "id": "b", "activation": [{"frame": "kp", "dasha_signifies": {"level": "md", "houses": list(range(1, 13)), "mode": "any"}}]}
    jd = swe.julday(2026, 10, 13, 12)
    assert [r["id"] for r in kp_rules.applying(st, None, [mine, timed])] == ["a"]
    assert [r["id"] for r in kp_rules.applying(st, jd, [mine, timed])] == ["b"]
    assert kp_rules.lords_at(st, jd)["md"]
