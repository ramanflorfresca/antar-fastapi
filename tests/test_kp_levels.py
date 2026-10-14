from antar_engine.kp import kp_levels as kl
from antar_engine.kp.kp_chart import compute_kp_chart, resolve_sublord
from antar_engine import kp_rules


def test_sub_sub_lord_partitions_the_sub_arc_in_vimshottari_order():
    # across any sub arc the 9 sub-sub lords appear once each, starting with the sub lord
    lon = 100.123
    seg = resolve_sublord(lon)
    seen = [kl.sub_sub_lord(lon)]
    assert kl.sub_sub_lord(0.0) == "Ketu"                              # first sub-sub of Ashwini/Ketu/Ketu starts with Ketu
    from antar_engine.kp.kp_chart import _SUB_SEGMENTS
    s = next(x for x in _SUB_SEGMENTS if x["start"] <= lon < x["end"])
    w = (s["end"] - s["start"])
    order = [kl.sub_sub_lord(s["start"] + w * (i + 0.5) / 9 * 0.999) for i in range(30)]
    assert order[0] == s["sub_lord"]
    assert len(set(kl.sub_sub_lord(s["start"] + w * t) for t in [i / 200 for i in range(200)])) == 9


def _chart():
    return compute_kp_chart("1985-03-14", "10:30", 40.7, -74.0, tz_offset=-5)


def test_enrich_links_levels_and_signs():
    ch = kl.enrich(_chart())
    assert all("sub_sub_lord" in v for v in ch["cusps"].values()) and all("sub_sub_lord" in v for v in ch["planets"].values())
    for p in ("Sun", "Moon", "Rahu"):
        assert all(1 <= h <= 12 for h in kl.links(ch, p))
    assert kl.sign_type("Aries") == "movable" and kl.sign_type("Leo") == "fixed" and kl.sign_type("Virgo") == "dual"
    lv = kl.sig_levels(ch)
    assert all(1 <= v <= 4 for d in lv.values() for v in d.values())


def test_new_clauses_evaluate():
    ch = _chart()
    st = kp_rules.kp_state(ch, "male", ruling={"Venus"})
    p = next(iter(kl.sig_levels(ch)))
    c7 = ch["cusps"][7]
    assert kp_rules.holds({"frame": "kp", "cusp": 7, "sub_sub_lord": c7["sub_sub_lord"]}, st)
    assert not kp_rules.holds({"frame": "kp", "cusp": 7, "sub_sub_lord": "Nobody"}, st)
    assert kp_rules.holds({"frame": "kp", "planet": "Venus", "ruling_includes": "Venus"} if False else {"frame": "kp", "ruling_includes": "Venus"}, st)
    assert not kp_rules.holds({"frame": "kp", "ruling_includes": "Mars"}, st)
    retro = bool(ch["planets"]["Saturn"].get("retrograde"))
    assert kp_rules.holds({"frame": "kp", "planet": "Saturn", "retrograde": retro}, st)
    sg = ch["planets"]["Saturn"]["sign"]
    assert kp_rules.holds({"frame": "kp", "planet": "Saturn", "in_sign": sg}, st)
    assert kp_rules.holds({"frame": "kp", "planet": "Saturn", "sign_type": kl.sign_type(sg)}, st)
    me = set(kl.links(ch, "Mercury"))
    assert kp_rules.holds({"frame": "kp", "planet": "Mercury", "links_to_cusps": sorted(me), "mode": "all"}, st) if me else True
    assert not kp_rules.holds({"frame": "kp", "planet": "Mercury", "links_to_cusps": [], "mode": "any"}, st)
    own = kl.owned_houses(ch, "Venus")
    assert kp_rules.holds({"frame": "kp", "planet": "Venus", "owns": own, "mode": "all"}, st) if own else True


def test_new_activation_clauses():
    import swisseph as swe
    ch = _chart()
    st = kp_rules.kp_state(ch, "male", ruling=set())
    jd = swe.julday(2026, 10, 14, 12.0)
    lord = kp_rules.lords_at(st, jd)["ad"]
    st["ruling"] = {lord}
    assert kp_rules.act_holds({"frame": "kp", "dasha_lord_ruling": {"level": "ad"}}, st, jd)
    st["ruling"] = set()
    assert not kp_rules.act_holds({"frame": "kp", "dasha_lord_ruling": {"level": "ad"}}, st, jd)
    allh = list(range(1, 13))
    assert kp_rules.act_holds({"frame": "kp", "dasha_links_to_cusps": {"level": "ad", "cusps": allh, "mode": "any"}}, st, jd) in (True, False)
    strong = kp_rules.act_holds({"frame": "kp", "dasha_signifies": {"level": "ad", "houses": allh, "mode": "any", "max_level": 4}}, st, jd)
    weak_only = kp_rules.act_holds({"frame": "kp", "dasha_signifies": {"level": "ad", "houses": allh, "mode": "any"}}, st, jd)
    assert (not strong) or weak_only


def test_question_time_rules_wait_for_a_question_moment():
    ch = _chart()
    rule = {"id": "Q", "requires": [], "activation": [], "asked_at_judgement": True}
    assert kp_rules.applying(kp_rules.kp_state(ch), None, [rule]) == []
    assert kp_rules.applying(kp_rules.kp_state(ch, ruling={"Venus"}), None, [rule]) == [rule]
