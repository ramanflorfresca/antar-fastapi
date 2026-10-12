from antar_engine import work_fit as WF

# Raman's real ranking (D-1 10th + D-10 + D-9 + dasha)
RAMAN = [{"field": "technology & innovation", "weight": 7.26}, {"field": "science & research", "weight": 6.17}, {"field": "networks / community / humanitarian", "weight": 5.08},
         {"field": "law & diplomacy", "weight": 4.85}, {"field": "communication & media", "weight": 4.54}, {"field": "arts & design", "weight": 4.45}]


def test_best_and_uphill_lanes_always_come_back_even_before_they_say_what_they_do():
    r = WF.fit(RAMAN, "", "en")
    assert r["best"] == ["technology & innovation", "science & research", "networks / community / humanitarian"] and r["tier"] is None
    assert {"food, flowers & hospitality", "retail & physical inventory", "operations-heavy businesses"} <= set(r["uphill"])      # nothing in the ranking supports these
    assert "guarantee" in r["caveat"]


def test_their_own_work_gets_a_tier_by_where_it_sits_in_the_ranking():
    assert WF.fit(RAMAN, "AI agents for small businesses", "en")["tier"] == "strong"
    assert WF.fit(RAMAN, "a law practice", "en")["tier"] == "workable"
    assert WF.fit(RAMAN, "a tech platform for flower delivery", "en")["tier"] == "against"      # wrapped in tech, still perishable daily logistics
    f = WF.fit(RAMAN, "a flower delivery platform", "en")                       # his real 2019 venture: perishable, daily logistics — the 'food / flowers' pattern
    assert f["tier"] == "against" and f["label"] == "Against the grain" and "under-return" in f["why"]
    assert WF.fit(RAMAN, "food delivery with loyalty", "en")["tier"] == "against"
    assert WF.fit(RAMAN, "something I can't describe", "en")["tier"] is None   # unknown line: no claim at all


def test_an_operations_chart_flips_the_same_line_and_es_is_native():
    ops = [{"field": "operations & service industries", "weight": 6.0}, {"field": "construction / heavy industry", "weight": 5.5}, {"field": "food & beverage", "weight": 4.0}]
    assert WF.fit(ops, "a restaurant", "en")["tier"] == "strong"
    assert WF.fit(ops, "an AI startup", "en")["tier"] != "strong"
    es = WF.fit(RAMAN, "agentes de IA para pequeños negocios software", "es")
    assert es["label"] == "Buen encaje" and es["best"][0] == "tecnología e innovación" and "your chart" not in es["why"]
    assert WF.fit([], "x", "en") is None


def test_a_line_touching_several_lanes_takes_the_best_one_and_only_hands_on_work_is_against_the_grain():
    harleen = [{"field": "finance & banking", "weight": 6.0}, {"field": "law", "weight": 5.0}, {"field": "arts / film / imagination", "weight": 4.0}]
    assert WF.fit(harleen, "a fintech app", "en")["tier"] == "strong"            # tech AND finance: finance is her top lane
    assert WF.fit(harleen, "an advisory practice", "en")["tier"] == "workable"   # not ranked, but nothing about it is hands-on: never 'against'
    harleen_h = harleen + [{"field": "hospitality", "weight": 2.0}]
    assert WF.fit(harleen, "a restaurant", "en")["tier"] == "against"            # hands-on, nothing in her ranking supports it
    assert WF.fit(harleen_h, "a restaurant", "en")["tier"] == "against"          # ranked, but far below her top three: still against the grain (her real restaurants)
    assert WF.fit(harleen, "an AI startup", "en")["tier"] == "workable"
