from datetime import date
from antar_engine import combo_rules as cb


LON = {"Saturn": 236.5, "Mars": 241.0, "Jupiter": 10.0}   # Scorpio 26.5, Sagittarius 1, Aries 10


def test_degree_window_in_sign():
    a = {"transit_deg": {"planet": "Saturn", "sign": "Scorpio", "from_deg": 26, "to_deg": 30}}
    assert cb.act_holds(a, {"transit_lon": LON})
    assert not cb.act_holds({"transit_deg": {"planet": "Saturn", "sign": "Scorpio", "from_deg": 0, "to_deg": 10}}, {"transit_lon": LON})
    assert not cb.act_holds(a, {"transit_lon": {"Saturn": 100.0}})


def test_nakshatra_sign_and_aspect():
    assert cb.act_holds({"transit_nakshatra": {"planet": "Jupiter", "nakshatra": "Ashwini"}}, {"transit_lon": {"Jupiter": 10.0}})
    assert cb.act_holds({"transit_nakshatra": {"planet": "Jupiter", "nakshatra": "Bharani"}}, {"transit_lon": {"Jupiter": 15.0}})
    assert cb.act_holds({"transit_sign": {"planet": "Jupiter", "signs": ["Aries", "Leo"]}}, {"transit_lon": LON})
    assert cb.act_holds({"transit_aspect": {"a": "Saturn", "b": "Mars", "aspect": "conjunct", "orb": 8}}, {"transit_lon": LON})
    assert not cb.act_holds({"transit_aspect": {"a": "Saturn", "b": "Jupiter", "aspect": "square", "orb": 3}}, {"transit_lon": LON})


def test_missing_longitudes_never_hold_and_impersonal_flag():
    assert not cb.act_holds({"transit_sign": {"planet": "Jupiter", "signs": ["Aries"]}}, {})
    r = {"requires": [], "activation": [{"transit_sign": {"planet": "Jupiter", "signs": ["Aries"]}}]}
    assert cb.is_impersonal(r)
    assert not cb.is_impersonal({**r, "requires": [{"house": 7, "empty": True}]})
    assert not cb.is_impersonal({"requires": [], "activation": [{"dasha": {"level": "md", "lords": ["Mars"]}}]})


def test_transit_longitudes_consistent_with_signs():
    from antar_engine.transit_signs import transit_longitudes, transit_signs
    d = date(2026, 10, 14)
    assert all(int(l // 30) == transit_signs(d)[p] for p, l in transit_longitudes(d).items())


def test_tropical_clause_uses_tropical_longitudes_and_offset_nakshatra():
    a = {"transit_sign": {"planet": "Sun", "signs": ["Aries"]}, "zodiac": "tropical"}
    st = {"transit_lon": {"Sun": 350.0}, "transit_lon_trop": {"Sun": 10.0}}
    assert cb.act_holds(a, st) and not cb.act_holds({**a, "zodiac": None}, st)
    n = {"transit_nakshatra": {"planet": "Sun", "nakshatra": "Ashwini"}, "zodiac": "tropical"}
    assert cb.act_holds(n, {"transit_lon_trop": {"Sun": 355.0}})           # Ashwini starts at 23deg20 Pisces (353.33)
    assert not cb.act_holds({**n, "zodiac": None}, {"transit_lon": {"Sun": 355.0}})


def test_wellness_block_carries_care_line_and_remedy(monkeypatch):
    from tests.test_rule_registry import ctx
    from antar_engine import reading_library as rl, book_rules
    rules = [{"id": "H1", "requires": [], "activation": [{"dasha": {"level": "md", "lords": ["Moon", "Mars", "Sun", "Venus", "Saturn", "Mercury", "Jupiter", "Rahu", "Ketu"]}}],
              "tone": "info", "topics": ["health"], "effect": "Your digestion may need extra care.", "remedy": "Eat lighter now and then.", "book": "chatterjee_medical"}]
    ev = [rl.rr._book_evidence(r) for r in rules]
    monkeypatch.setattr(rl.rr, "timed_book_evidence", lambda c, d: ev)
    monkeypatch.setattr(rl.rr, "_book_family", lambda c: [])
    monkeypatch.setattr(book_rules, "load_rules", lambda: rules)
    w = rl.wellness(ctx(), language="en")
    assert w["themes"][0]["timing"] == "now" and w["themes"][0]["remedy"] == "Eat lighter now and then."
    assert "not a diagnosis" in w["note"] and "check-up" in w["note"]
    assert "diagnóstico" in rl.wellness(ctx(), language="es")["note"]
