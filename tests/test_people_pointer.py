from antar_engine import people_pointer as pp

CAUGHT = [
    ("Is my partner compatible with me?", "compat"), ("Is my partner the right one for me?", "compat"),
    ("Is he the one?", "compat"), ("Are we compatible?", "compat"),
    ("Does my partner truly love me?", "state"), ("Will my spouse love me?", "state"),
    ("Is my spouse's dasha affecting our marriage?", "state"),
]
LEFT_ALONE = ["Is my boss compatible with me?", "Is the deal the right one?", "Does my partner approve the plan?",
              "Is he the one who called?", "Is my partner the right one for the deal?", "Will my marriage last?",
              "Will I ever get married?", "Does he love me?"]       # the last: no anchor person -> other_person rewrite, not this


def test_classify():
    for q, k in CAUGHT:
        assert pp.classify(q) == k, q
    for q in LEFT_ALONE:
        assert pp.classify(q) is None, q


def test_partner_candidates_romantic_only():
    people = [{"chart_id_b": "1", "name_b": "Dana", "compat_type": "romantic"},
              {"chart_id_b": "2", "name_b": "Biz", "compat_type": "cofounder"},
              {"chart_id_b": "3", "name_b": "Old", "compat_type": "romantic", "relation": "ex"},
              {"chart_id_b": "4", "name_b": "Sam", "compat_type": "friend"}]
    assert [p["name_b"] for p in pp.partner_candidates(people)] == ["Dana"]


def _chart():
    # Aries lagna -> 7th is Libra (lord Venus). Venus in Taurus (2nd house)
    return {"lagna": {"sign": "Aries"}, "planets": {
        "Sun": {"sign": "Leo", "house": 5, "degree": 15.0}, "Moon": {"sign": "Virgo", "house": 6, "degree": 25.0},
        "Mars": {"sign": "Aries", "house": 1, "degree": 22.0}, "Mercury": {"sign": "Gemini", "house": 3, "degree": 18.0},
        "Jupiter": {"sign": "Sagittarius", "house": 9, "degree": 20.0}, "Venus": {"sign": "Taurus", "house": 2, "degree": 12.0},
        "Saturn": {"sign": "Capricorn", "house": 10, "degree": 27.0}, "Rahu": {"sign": "Pisces", "house": 12, "degree": 5.0},
        "Ketu": {"sign": "Virgo", "house": 6, "degree": 5.0}}}


def _dashas(md, ad, pd):
    from datetime import date, timedelta
    s, e = (date.today() - timedelta(days=30)).isoformat(), (date.today() + timedelta(days=30)).isoformat()
    return {"vimsottari": [{"level": "mahadasha", "lord": md, "start_date": s, "end_date": e},
                           {"level": "antardasha", "lord": ad, "start_date": s, "end_date": e},
                           {"level": "pratyantardasha", "lord": pd, "start_date": s, "end_date": e}]}


def test_partner_activation_states():
    ch = _chart()
    # Venus is the 7th lord: a Venus main chapter is wired to partnership
    assert pp.partner_activation(ch, _dashas("Venus", "Saturn", "Saturn"))["state"] == "active"
    # Saturn looks at the 7th (10th -> 7th aspect), Mercury/Ketu/Rahu are not connected
    q = pp.partner_activation(ch, _dashas("Mercury", "Mercury", "Mercury"))
    assert q["state"] == "quiet" and q["tiers"] == []
    assert pp.partner_activation(ch, _dashas("Mercury", "Mercury", "Venus"))["state"] == "touching"
    assert pp.partner_activation({}, {}) == {"available": False}


def test_no_feelings_and_no_jargon_in_any_language():
    ch = _chart()
    for lang in ("en", "es", "pt", "hinglish", "hi"):
        for payload in (pp.missing_payload(lang, ch), pp.partner_payload("Dana", lang, ch, ch, _dashas("Mercury", "Mercury", "Mercury"))):
            txt = (payload["read"] + " " + (payload.get("next") or "")).lower()
            for bad in ("darakaraka", "upapada", "navamsa", "saturn", "rahu", "ketu", "he loves", "she loves", "doesn't love", "does not love"):
                assert bad not in txt, (lang, bad)
            assert payload["people_pointer"]["state"] in ("missing", "read", "unreadable")


def test_missing_payload_points_to_people():
    p = pp.missing_payload("en", _chart())
    assert "People" in p["read"] and p["subject"]["chart_available"] is False and p["people_pointer"]["state"] == "missing"


def test_stop_verdict_only_when_both_sides_agree():
    ch = _chart()
    fragile = {"lagna": {"sign": "Aries"}}          # no planets -> band None -> mixed wording, never the stop verdict
    p = pp.partner_payload("Dana", "en", fragile, ch, _dashas("Mercury", "Mercury", "Mercury"))
    assert "stop waiting" not in p["read"]


def test_bare_aspect_alone_is_not_a_partnership_chapter():
    ch = _chart()
    # Ketu only LOOKS at Venus / the 7th lord (9th aspect) and nothing rules, occupies or conjoins -> not "active" from the sub-chapter alone
    r = pp.partner_activation(ch, _dashas("Mercury", "Ketu", "Mercury"))
    assert r["state"] == "touching" and "ad" in r["tiers"]
    # but a main chapter that IS the 7th lord is active even with a quiet sub-chapter
    assert pp.partner_activation(ch, _dashas("Venus", "Mercury", "Mercury"))["state"] == "active"


def test_feelings_question_opens_by_saying_a_chart_cannot_read_feelings():
    ch = _chart()
    for lang in ("en", "es", "pt", "hinglish"):
        st = pp.partner_payload("Dana", lang, ch, ch, _dashas("Venus", "Venus", "Venus"), "state")["read"]
        co = pp.partner_payload("Dana", lang, ch, ch, _dashas("Venus", "Venus", "Venus"), "compat")["read"]
        assert len(st) > len(co) and "Dana" in st
