"""[authority-read 2026-10-11] employee / boss / advisor: authority and fit."""
from datetime import datetime

from antar_engine import authority_read as AR
from antar_engine import connection_card as CC
from antar_engine import people_reading as PR
from tests.test_partner_roles import _built, _chart, _dashas, TODAY


def test_only_the_three_types_get_a_read():
    for k in ("cofounder", "business", "friend", "sibling", "", None):
        assert AR.compare(k, _built(["Mercury"]), _dashas(), _built(["Saturn"]), _dashas(), "x", "en", TODAY) is None
    for k in ("employee", "boss", "boss-or-manager", "manager", "advisor", "mentor"):
        assert AR.compare(k, _built(["Mercury"]), _dashas(), _built(["Saturn"]), _dashas(), "x", "en", TODAY)["kind"] == "hierarchy"
    assert AR.compare("employee", {}, {}, _chart(), {}) is None and AR.compare("employee", None, None, None, None) is None


def test_employee_role_fit_strong_ok_weak():
    ops = _built(["Saturn", "Mars"])
    r = AR.compare("employee", _chart(), _dashas(), ops, _dashas(), "Dev", "en", TODAY, role="operations")
    assert r["fit"] == "strong" and "For the operations role that is a strong fit." in r["text"] and r["text"].startswith("How to manage Dev")
    weak = AR.compare("employee", _chart(), _dashas(), _built(["Venus", "Moon"]), _dashas(), "Dev", "en", TODAY, role="engineering")
    assert weak["fit"] in ("weak", "ok")
    assert "fit" not in AR.compare("employee", _chart(), _dashas(), ops, _dashas(), "Dev", "en", TODAY)          # no role -> no fit claim


def test_direction_taking_and_authority_style_follow_the_chart():
    disciplined = _built(["Saturn", "Mercury"])
    assertive = _built(["Sun", "Mars"])
    assert AR.direction_level(disciplined) in ("easy", "scope") and AR.direction_level(assertive) in ("scope", "own")
    assert AR.direction_level(disciplined) != "own" and AR.authority_style(_built(["Saturn"])) == "structured"
    assert AR.authority_style(_built(["Jupiter"])) == "guiding" and AR.authority_style(_built(["Sun", "Mars"])) == "decisive"
    assert AR.authority_style(_built(["Rahu", "Mercury"])) == "fast"


def test_boss_read_leads_with_what_they_value_and_how_to_win_with_them():
    r = AR.compare("boss", _built(["Mercury", "Rahu"]), _dashas(), _built(["Saturn", "Mars"]), _dashas(), "Priya", "en", TODAY)
    t = r["text"]
    assert t.startswith("How to work with Priya") and "They value" in t and "Their authority style is" in t and "You add where they are thin" in t
    assert "How to manage" not in t and "who should lead" not in t.lower()


def test_advisor_read_says_what_to_use_them_for_and_what_not():
    r = AR.compare("advisor", _built(["Mercury"]), _dashas(), _built(["Jupiter", "Sun"]), _dashas(), "Andres", "en", TODAY)
    t = r["text"]
    assert t.startswith("How to use Andres") and "Use Andres for" in t and "Do not lean on Andres for" in t and "advisory" in t


def test_spanish_is_native():
    r = AR.compare("employee", _chart(), _dashas(), _built(["Saturn", "Mars"]), _dashas(), "Dev", "es", TODAY, role="operations")
    t = r["text"]
    assert t.startswith("Cómo dirigir a Dev") and "Para el puesto de operaciones es un encaje fuerte." in t and "Su estilo de autoridad es" in t
    for en in ("strongest in", "Their authority", "takes", "How to"):
        assert en not in t


def test_the_card_facts_carry_authority_not_leads_and_the_validator_forbids_leads():
    roles = AR.compare("boss", _built(["Mercury"]), _dashas(), _built(["Saturn"]), _dashas(), "Priya", "en", TODAY)
    f = CC.build_facts({"name_b": "Priya", "compat_type": "boss", "roles": roles, "layers": []}, "en")
    assert "roles" not in f and f["authority"]["type"] == "boss" and f["authority"]["their_authority_style"]
    assert "REPORTING / ADVISORY" in CC.build_prompt(f)[1]
    card = {"headline": "h", "strengths": [{"title": "t", "text": "x"}] * 3, "frictions": [{"issue": "i", "do": "d"}] * 3,
            "dos": ["a", "b", "c"], "donts": ["a", "b", "c"], "leads": [{"lane": "tech", "who": "you", "line": "x"}]}
    assert not CC.validate(card, f)[0]
    del card["leads"]
    assert CC.validate(card, f)[0]


def test_reading_stage_marks_the_three_types_as_having_an_automatic_read():
    for t in ("employee", "boss", "advisor"):
        r = PR.stage("L1 sentence.", None, None, "x", "en", t)
        assert r["roles_auto"] and r["has_roles"] and r["next_step"] == "add_context"
    assert not PR.stage("L1.", None, None, "x", "en", "friend")["roles_auto"]


def test_contested_top_lane_needs_a_real_split_not_just_a_different_first_pick(monkeypatch):
    def fake(par, jai):
        def f(chart, dashas, today=None, jaimini=None):
            sc = {l: 0.5 for l in AR.P.LANES}
            return {"scores": sc, "parashari": par, "jaimini": jai, "parts": {l: {"dasha": 0.0} for l in AR.P.LANES}, "amk": "Saturn", "ak": "Moon",
                    "dk": "Sun", "md": "", "ad": "", "chara_md": "", "chara_ad": "", "have": {}}
        return f
    base = {l: 0.1 for l in AR.P.LANES}
    close_par = {**base, "ops": 0.9, "finance": 0.8}
    close_jai = {**base, "finance": 0.9, "ops": 0.8}                  # different first pick, same top two -> NOT contested
    monkeypatch.setattr(AR.P, "score_person", fake(close_par, close_jai))
    assert AR.compare("boss", _chart(), {}, _chart(), {}, "X", "en", TODAY)["contested_top"] is False
    far_jai = {**base, "creative": 0.9, "tech": 0.8, "vision": 0.7, "sales": 0.6}   # ops/finance outside its top three AND creative outside par's
    monkeypatch.setattr(AR.P, "score_person", fake(close_par, far_jai))
    assert AR.compare("boss", _chart(), {}, _chart(), {}, "X", "en", TODAY)["contested_top"] is True
