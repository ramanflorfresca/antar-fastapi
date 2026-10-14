import json
from antar_engine import public_view as pv

BANNED = ("K.N. Rao", "Raman", "Jaimini", "Vimshottari", "Lal Kitab", "KP", "Jataka", "Parijata", "Mehta", "Chatterjee", "BK.", "rule_id",
          "source", "timing_methods", "kp", "lal_kitab")


def _blob(x):
    return json.dumps(x, ensure_ascii=False)


def test_ref_is_stable_opaque_and_resolvable():
    r = pv.ref_for("BK.BVJ1.13")
    assert r == pv.ref_for("BK.BVJ1.13") and "BVJ" not in r and len(r) == 12
    assert pv.resolve_ref(r) == "BK.BVJ1.13"
    assert pv.ref_for(None) is None


def test_week_public_view_has_no_method_names():
    internal = {"start": "2026-10-14", "days": 7,
                "vimshottari": {"periods_now": {"md": "Rahu"}, "gochara": {"best_days": ["2026-10-16"], "slow_days": ["2026-10-14"],
                                                                         "background": [{"planet_key": "Jupiter"}]}},
                "jaimini": [{"rule_id": "BK.X", "book": "K.N. Rao"}], "lal_kitab": {"year_lord": "Jupiter", "rules": []},
                "lean_in": [{"line": "jaimini", "source": "K.N. Rao", "text": "Partnership is likely.", "rule_id": "BK.BVJ1.13",
                             "days": ["2026-10-14"], "tendency": False},
                            {"line": "book", "source": "Jataka Parijata", "text": "Partnership is likely.", "rule_id": "BK.JP2.5", "tendency": True}],
                "watch": [{"line": "vimshottari", "source": "B.V. Raman", "text": "Hold off.", "rule_id": "BK.BVHPA1.2", "do": "Wait a day.",
                           "tendency": True}],
                "watch_more": [1, 2],
                "wellness": {"themes": [{"rule_id": "BK.CHM.5", "source": "Medical astrology (Chatterjee)", "text": "Your digestion may need care.",
                                         "timing": "now", "label": "Oct 2026", "remedy": "Eat lighter."}], "more": 1, "note": "n"}}
    out = pv.week(internal)
    b = _blob(out)
    for w in BANNED:
        assert w not in b, w
    assert len(out["lean_in"]) == 1                       # duplicate text collapsed
    assert out["lean_in"][0]["confidence"] == "likely" and out["watch"][0]["confidence"] == "possible"
    assert out["watch"][0]["do"] == "Wait a day." and out["watch_more"] == 2
    assert out["wellness"]["themes"][0]["ref"] and out["wellness"]["note"] == "n"


def test_answer_and_when_public_view():
    a = {"available": True, "subject": "money", "qword": "when", "headline": "h", "lines": ["x"], "applicable": True, "text": "t",
         "rules_used": ["BK.A.1", "WINDOW.money"], "periods_now": {"md": "Rahu"},
         "windows": [{"start": "2026-10", "end": "2027-01", "label": "Oct", "strength": "good", "why": "w", "action": "a", "srcs": ["jaimini"]}],
         "when_combined": {"agree": [{"start": "2026-10-14", "end": "2027-01-01", "strength": "strong", "signals": 3,
                                      "lines": ["kp", "timing_methods"], "line_names": ["KP periods"], "peaks": []}],
                           "also": [{"start": "2028-01-01", "end": "2028-02-01", "lines": ["kp"]}], "kp_promise": "weak", "kp_on": True}}
    out = pv.answer(a)
    b = _blob(out)
    for w in BANNED + ("periods_now", "kp_promise", "line_names", "srcs"):
        assert w not in b, w
    assert out["when"]["agree"][0]["strength"] == "strong" and out["refs"]


def test_library_merges_lines_into_one_list():
    lib = {"horizon": ["a", "b"], "agree": [{"subject": "money", "start": "s", "end": "e", "signals": ["dasha", "transit"], "text": "t"}],
           "vimshottari": {"lean_in": [{"rule_id": "BK.A", "source": "x", "text": "One.", "start": "2026-11-01", "tendency": False}], "watch": []},
           "jaimini": {"lean_in": [{"rule_id": "BK.B", "source": "y", "text": "Two.", "start": "2026-10-01", "tendency": True}], "watch": []},
           "wellness": None}
    out = pv.library(lib)
    assert [i["text"] for i in out["lean_in"]] == ["Two.", "One."]
    assert "signals" not in _blob(out) and "vimshottari" not in _blob(out)


def test_answer_text_has_no_method_names():
    from tests.test_rule_registry import ctx
    from antar_engine import rule_registry as rr
    t = rr.answer(ctx(), "money", "when", "en")["text"]
    for w in ("KP", "Jaimini", "Vimshottari", "Lal Kitab", "timing methods", "both timing systems"):
        assert w not in t, w
