from datetime import date

from antar_engine import book_rules as br
from antar_engine import combo_rules as cb
from antar_engine import rule_registry as rr
from antar_engine.transit_signs import transit_signs
from tests.test_rule_registry import chart, ctx_v, SIGNS_A, TODAY, VIM

ARI, TAU, GEM, CAN, LEO, VIR, LIB, SCO, SAG, CAP, AQU, PIS = range(12)


def S(**kw):
    base = {"lagna": CAP, "signs": {p: ARI for p in cb.PLANETS}, "gender": "male"}
    base["signs"].update(kw.get("signs", {}))
    base.update({k: v for k, v in kw.items() if k != "signs"})
    return base


def test_activation_dasha_levels_and_lords():
    st = S(periods={"md": "Rahu", "ad": "Venus", "pd": "Moon", "sd": "Sun"})
    assert cb.act_holds({"dasha": {"level": "ad", "lords": ["Venus", "Mars"]}}, st)
    assert not cb.act_holds({"dasha": {"level": "md", "lords": ["Venus"]}}, st)
    assert cb.act_holds({"dasha": {"level": "ad", "lords": ["L10"]}}, st)                 # Capricorn lagna: 10th lord is Venus
    # L7 from Capricorn lagna is Moon (Cancer)
    assert cb.act_holds({"dasha": {"level": "pd", "lords": ["L7"]}}, st)
    assert not cb.act_holds({"dasha": {"level": "pd", "lords": ["L7"]}}, S())            # no periods known


def test_activation_transit_and_age_year():
    st = S(signs={"Moon": CAN}, transit={"Jupiter": LIB, "Saturn": CAN})
    assert cb.act_holds({"transit": {"planet": "Jupiter", "from": "Moon", "houses": [4]}}, st)      # Libra is 4th from Cancer
    assert cb.act_holds({"transit": {"planet": "Jupiter", "from": "lagna", "houses": [10]}}, st)    # Capricorn lagna: Libra is 10th
    assert not cb.act_holds({"transit": {"planet": "Jupiter", "from": "Moon", "houses": [1, 7]}}, st)
    assert cb.act_holds({"transit_conj": {"planet": "Saturn", "with": "Moon"}}, st)
    assert cb.act_holds({"age_year": [30, 31]}, S(age_year=31)) and not cb.act_holds({"age_year": [30]}, S(age_year=31))
    assert not cb.act_holds({"unparsed": "x"}, st) and not cb.act_holds({"frame": "kp", "dasha": {}}, st)


def test_timed_rule_needs_natal_and_activation():
    rule = {"requires": [{"planet": "Moon", "in_houses": [12]}],
            "activation": [{"dasha": {"level": "ad", "lords": ["Moon"]}}]}
    st = S(signs={"Moon": SAG}, periods={"ad": "Moon"})
    assert cb.timed_ok(rule, st)
    assert not cb.timed_ok(rule, S(signs={"Moon": ARI}, periods={"ad": "Moon"}))
    assert not cb.timed_ok(rule, S(signs={"Moon": SAG}, periods={"ad": "Mars"}))


def test_transit_signs_are_real_and_cached():
    t = transit_signs(date(2026, 10, 13))
    assert set(t) == {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"}
    assert all(0 <= v < 12 for v in t.values()) and (t["Rahu"] + 6) % 12 == t["Ketu"]
    assert t["Rahu"] == 10 and t == transit_signs(date(2026, 10, 13))           # Rahu in Aquarius now (sidereal)


def test_registry_applies_static_and_timed_library_rules(monkeypatch):
    rules = [
        {"id": "S1", "book": "kn_rao_x", "requires": [{"planet": "Moon", "in_houses": [3]}], "activation": [], "tone": "good",
         "topics": ["money"], "effect": "A steady trait.", "effect_es": "Un rasgo estable.", "clarity": "clear"},
        {"id": "T1", "book": "bv_raman_x", "requires": [], "activation": [{"dasha": {"level": "md", "lords": ["Moon"]}}],
         "tone": "good", "topics": ["money"], "effect": "A good phase for money.", "effect_es": "Una buena fase para el dinero.",
         "clarity": "clear"},
        {"id": "T2", "book": "bv_raman_x", "requires": [], "activation": [{"dasha": {"level": "md", "lords": ["Mars"]}}],
         "tone": "bad", "topics": ["money"], "effect": "Never shown.", "clarity": "clear"}]
    monkeypatch.setattr(br, "_cache", rules)
    c = ctx_v()                                                  # Moon major period; Moon in Pisces = house 3 from Capricorn
    ids = {e.rule_id for e in rr.applicable(c)}
    assert "BK.S1" in ids and "BK.T1" not in ids                 # timed rules are not standing traits
    now = {e.rule_id for e in rr.timed_book_evidence(c, TODAY)}
    assert now == {"BK.T1"}
    a = rr.answer(c, "money", "what", "en")
    assert "Active right now:" in a["lines"] and any("A good phase for money." in l for l in a["lines"])
    assert any("A steady trait." in l for l in a["lines"]) and not any("Never shown." in l for l in a["lines"])
    es = rr.answer(c, "money", "what", "es")
    assert any("Una buena fase" in l for l in es["lines"])
    assert br.label(rules[0]) == "K.N. Rao" and br.label(rules[1]) == "B.V. Raman"
