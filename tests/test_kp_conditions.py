"""[kp-conditions 2026-10-02] A KP Yes/No names WHAT it hinges on, from the
deciding cusp's supporting / blocking houses — never "one hurdle"."""
from antar_engine.kp.kp_conditions import explain
from antar_engine.kp.kp_prashna import narrator_block


def _kp(lean, qt, fav, ag, gate=True):
    return {"lean": lean, "question_type": qt,
            "debug": {"favour_hit": fav, "against_hit": ag, "gate_ok": gate}}


def test_money_condition_is_specific():
    c = explain(_kp("conditional", "gain", [2, 11], [5, 8]), "en", "Will I raise funding by March?")["condition"]
    assert "people who already know your work" in c and "heavy strings attached" in c
    assert "hurdle" not in c and "piece" not in c


def test_gate_not_confirmed_asks_for_a_written_commitment():
    c = explain(_kp("conditional", "gain", [6], [12], gate=False), "en", "Will I get a loan?")["condition"]
    assert c.startswith("The route is a loan or credit") and "written commitment" in c


def test_no_names_what_stands_in_the_way():
    c = explain(_kp("no", "gain", [], [5, 8], gate=False))["condition"]
    assert "What stands in the way: a speculative gamble" in c


def test_family_meanings_differ():
    assert "doing the job itself well" in explain(_kp("yes", "job_new", [6], []))["condition"]
    assert "old friction" in explain(_kp("conditional", "marriage", [7], [6]))["condition"]


def test_languages_and_no_jargon():
    es = explain(_kp("conditional", "gain", [2, 11], [5, 8]), "es")["condition"]
    assert "pero solo si evitas" in es
    for lang in ("en", "es", "pt"):
        c = explain(_kp("conditional", "gain", [2, 11], [5, 8, 12]), lang)["condition"].lower()
        assert not any(w in c for w in ("house", "casa 1", "planet", "sub-lord", "cusp"))


def test_narrator_is_told_the_condition():
    nb = narrator_block(dict(_kp("conditional", "gain", [2, 11], [5, 8]), confidence=1, window={}),
                        "Will I raise funding by March?")
    assert "SPECIFIC CONDITION" in nb and "heavy strings attached" in nb


def test_missing_debug_is_safe():
    assert explain({"lean": "yes"}) == {}



def test_clients_question_gets_sales_meanings_not_loans():
    kp = _kp("yes", "gain", [2, 6, 11], [8, 12])
    c = explain(kp, "en", "Will I get new clients this month?")["condition"]
    assert "referrals from people who know your work" in c and "loan" not in c
    f = explain(kp, "en", "Will I raise funding by March?")["condition"]
    assert "a loan or credit" in f
