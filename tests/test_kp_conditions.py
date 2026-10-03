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


# ─── change of residence (live: "will i move in next 30 days" read as money) ───

def test_move_questions_classify_as_residence():
    from antar_engine.kp.kp_prashna import classify_question as c
    for q in ("will i move in next 30 days", "Will I move to a new house this year?",
              "Will I relocate to Canada?", "¿Me voy a mudar este año?", "Kya main ghar badlunga?",
              "Will I shift to Pune?"):
        assert c(q)[0] == "residence", q
    assert c("Will I move abroad?")[0] == "foreign_travel"
    assert c("Will I move to a new job?")[0] == "job_new"
    assert c("Will I sell my house?")[0] == "property"


def test_residence_spec_and_condition():
    from antar_engine.kp.kp_significators import QUESTION_TYPES
    spec = QUESTION_TYPES["residence"]
    assert spec["primary_cusp"] == 3 and spec["favour"] == [3, 10, 12] and spec["against"] == [4]
    c = explain(_kp("yes", "residence", [3, 10], []), "en", "will i move in next 30 days")["condition"]
    assert c == "It's carried by actually leaving where you are now and a new base tied to your work."
    assert "income" not in c
    blk = explain(_kp("conditional", "residence", [12], [4]), "en", "will I move?")["condition"]
    assert "the pull to stay (lease, family or home ties)" in blk


def test_window_is_clipped_to_the_asked_horizon():
    from datetime import datetime, timezone
    import antar_engine.kp.kp_prashna as kpp
    orig = kpp.window_label
    seen = {}

    def fake_window(chart, qt, rp, horizon_days, loss_house=None):
        return {"start": "2026-10-03", "end": "2027-01-20", "ruler_ok": True}
    import antar_engine.kp.kp_horary as kh
    real = kh.timed_window
    kh.timed_window = fake_window
    try:
        r = kpp.kp_prashna({}, "will i move in next 30 days", number=26,
                           now_utc=datetime(2026, 10, 3, 3, 0, tzinfo=timezone.utc))
    finally:
        kh.timed_window = real
    assert r["window"]["end"] == "2026-11-02" and r["window"]["clipped_to_horizon"] is True
    assert r["window"]["label"] == "Oct 3 – Nov 2, 2026"
