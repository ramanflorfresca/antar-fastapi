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
    assert "What stands in the way:" in c and "a speculative gamble" in c


def test_family_meanings_differ():
    assert "doing the job itself well" in explain(_kp("yes", "job_new", [6], []))["condition"]
    assert "old friction" in explain(_kp("conditional", "marriage", [7], [6]))["condition"]


def test_languages_and_no_jargon():
    es = explain(_kp("conditional", "gain", [2, 11], [5, 8]), "es")["condition"]
    assert "lo que podría frenarlo" in es
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


# ─── neutral fallback for questions KP didn't recognise ───

def test_unrecognised_question_is_never_worded_as_money():
    kp = dict(_kp("conditional", "gain", [2, 6, 11], [8, 12]), generic=True)
    c = explain(kp, "en", "will my sister visit?")["condition"]
    for w in ("income", "savings", "loan", "credit", "side income"):
        assert w not in c.lower(), w
    # 2026-10-03: no invented specifics at all — an honest "general" note instead
    assert "doesn't name one area of life" in c and "people who already know you" not in c


def test_narrator_told_not_to_assume_money_for_unrecognised():
    nb = narrator_block(dict(_kp("yes", "gain", [11], []), generic=True, confidence=1, window={}))
    assert "never assume it is about money" in nb


def test_unmapped_question_is_logged(capsys):
    from antar_engine.kp.kp_prashna import kp_prashna
    kp_prashna({}, "will my sister visit soon", number=10)
    assert "[kp][unmapped] 'will my sister visit soon'" in capsys.readouterr().out


def test_live_gold_advisory_cast_names_one_condition():
    # live 2026-10-03, #88: "Will I make money with gold mine advisory" (side business)
    # got the side-income family, a written-commitment gate AND three watch-outs.
    kp = _kp("conditional", "gain", [6], [5, 8, 12], gate=False)
    c = explain(kp, "en", "Will I make money with gold mine advisory")["condition"]
    assert "serving well and outworking competitors" in c            # clients family
    assert "once a client has signed and paid" in c
    assert c.count("Watch out for") == 1 and "speculative" not in c and "cost more" not in c  # ONE
    es = explain(kp, "es", "¿Voy a ganar dinero con mi asesoría de oro?")["condition"]
    assert "un cliente haya firmado y pagado" in es


def test_whatsapp_yesno_says_the_condition_once():
    from antar_engine import messaging as msg
    p = {"mode": "yesno", "lean": "conditional", "verdict": "NO",
         "why": "A clear written commitment is missing, and spending is running ahead.",
         "condition": "The route is X, but the final yes isn't locked in.",
         "condition_label": "What it hinges on", "timing": "Oct 3, 2026 – Jan 9, 2027"}
    text, _ = msg.format_ask_whatsapp_v2(p, "en")
    assert "written commitment is missing" not in text and "What it hinges on" in text


def test_business_with_other_people_reads_as_a_partnership():
    # live 2026-10-03, #8: "defense related business with other people in Colombia"
    kp = _kp("conditional", "gain", [6, 11], [8, 12], gate=True)
    c = explain(kp, "en", "Will I make money in defense related business with other people in Colombia")
    assert "a lopsided split with your partners" in c["condition"]
    assert "the contacts your partners bring" in c["condition"]
    es = explain(kp, "es", "¿Ganaré dinero en un negocio de defensa con socios en Colombia?")["condition"]
    assert "socios" in es


import pytest  # noqa: E402


# ── live 2026-10-03, #101: "Will I find a new girl friend in next 60’days" ──
@pytest.mark.parametrize("q", ["Will I find a new girl friend in next 60’days",
                               "will I get a girlfriend this year", "Will I have a boyfriend soon?",
                               "¿Voy a tener novia este año?", "Vou arrumar uma namorada?",
                               "kya mujhe pyaar milega"])
def test_new_relationship_is_romance(q):
    from antar_engine.kp.kp_prashna import classify_question
    assert classify_question(q)[0] == "romance"


def test_marriage_and_ex_still_win():
    from antar_engine.kp.kp_prashna import classify_question
    assert classify_question("Will I marry my girlfriend?")[0] == "marriage"
    assert classify_question("Will my ex girlfriend come back?")[0] == "reunion"


@pytest.mark.parametrize("q,days", [("in next 60’days", 60), ("in next 60'days", 60),
                                    ("in the next 60-day stretch", 60), ("in 3 months", 90)])
def test_horizon_reads_through_apostrophes(q, days):
    from antar_engine.kp.kp_prashna import parse_horizon_days
    assert parse_horizon_days(q) == days


def test_romance_condition_speaks_about_love():
    c = explain(_kp("conditional", "romance", [5, 11], [6, 10]), "en",
                "Will I find a new girl friend in next 60 days")["condition"]
    assert "real chemistry" in c and "friends and family helping" in c
    assert "old friction" in c and "career pulling priorities away" in c
    assert "your own resources" not in c and "a risky bet" not in c


def test_app_why_becomes_the_condition():
    import main
    p = {"mode": "yesno", "why": "Vague narrated paraphrase.", "condition": "Count on it once a client has paid."}
    main._yn_why_is_condition(p)
    assert p["why"] == "Count on it once a client has paid."
    q = {"mode": "yesno", "why": "Binary why stays."}
    main._yn_why_is_condition(q)
    assert q["why"] == "Binary why stays."


# ── live 2026-10-03, #2: "Will my partnership break" read as generic gain ──
@pytest.mark.parametrize("q", ["Will my partnership break", "Will my business partner leave the company?",
                               "will we end the partnership this year", "Will my co-founder quit?",
                               "¿Se va a romper mi sociedad?", "Meu sócio vai sair da empresa?"])
def test_partnership_ending_is_a_separation(q):
    from antar_engine.kp.kp_prashna import classify_question
    assert classify_question(q)[:2] == ("loss", 7)


def test_partnership_growth_is_not_a_separation():
    from antar_engine.kp.kp_prashna import classify_question
    assert classify_question("Will my partnership make money?")[0] != "loss"


def test_separation_wording_reads_as_a_split():
    k = {"lean": "conditional", "question_type": "loss", "debug": {"favour_hit": [6], "against_hit": [7], "gate_ok": True}}
    c = explain(k, "en", "Will my partnership break")["condition"]
    assert c == ("It can split over disputes about work, money or terms, unless your partner's "
                 "own wish to keep it going holds it together.")
    assert "hard, steady work" not in c


def test_generic_question_gets_an_honest_note_not_fake_specifics():
    k = {"lean": "conditional", "question_type": "gain", "generic": True,
         "debug": {"favour_hit": [6, 11], "against_hit": [8, 12], "gate_ok": True}}
    x = explain(k, "en", "Will it happen?")
    assert x["label"] == "Note" and "doesn't name one area of life" in x["condition"]
    assert "hard, steady work" not in x["condition"] and "people who already know" not in x["condition"]


def test_every_question_type_reads_differently():
    # owner 2026-10-03: "the reasoning cannot be the same for every question"
    from antar_engine.kp.kp_significators import QUESTION_TYPES as Q
    qs = {"gain": "Will I make more money this year?", "money": "Will I get the loan?",
          "deal_closes": "Will the client sign the contract?"}
    for lang in ("en", "es", "pt"):
        seen = {}
        for qt, v in Q.items():
            for gate in (True, False):
                k = {"lean": "conditional", "question_type": qt,
                     "debug": {"favour_hit": v["favour"][:2], "against_hit": v["against"][:2], "gate_ok": gate}}
                c = explain(k, lang, qs.get(qt, "q"))["condition"]
                assert c not in seen or seen[c] == qt, (lang, qt, seen.get(c), c)
                seen[c] = qt


def test_car_lease_does_not_get_house_buying_words():
    from antar_engine.kp.kp_conditions import explain
    kp = {"question_type": "property", "lean": "conditional",
          "debug": {"favour_hit": [4], "against_hit": [3], "gate_ok": True}}
    for q in ("Can I lease a car this month?", "¿Puedo alquilar un coche este mes?", "Posso fazer leasing de um carro?"):
        c = explain(kp, "en", q)["condition"]
        assert "clean title" not in c and "rushed paperwork" not in c
    assert "terms you've read in full" in explain(kp, "en", "Can I lease a car?")["condition"]
    assert "clean title" in explain(kp, "en", "Can I buy a house?")["condition"]


def test_conditional_lean_labels_the_line_the_condition():
    from antar_engine.kp.kp_conditions import explain
    base = {"question_type": "property", "debug": {"favour_hit": [4], "against_hit": [3], "gate_ok": True}}
    for lang, cond, other in (("en", "The condition", "What it hinges on"),
                              ("es", "La condición", "De qué depende"),
                              ("pt", "A condição", "Do que depende")):
        assert explain({**base, "lean": "conditional"}, lang, "Can I lease a car?")["label"] == cond
        assert explain({**base, "lean": "yes"}, lang, "Can I lease a car?")["label"] == other


def test_condition_opens_with_the_deciding_planet_and_houses():
    from antar_engine.kp.kp_conditions import explain
    kp = {"question_type": "property", "lean": "conditional",
          "debug": {"csl": "Venus", "favour_hit": [4, 11], "against_hit": [3], "gate_ok": True}}
    c = explain(kp, "en", "Can I lease a car this month?")["condition"]
    assert c == "Venus decides this: it backs it through your 4th and 11th house and works against it through your 3rd house."
    assert explain(kp, "es", "¿Puedo alquilar un coche?")["condition"].startswith("Venus decide esto: lo respalda por tu casa 4 y 11 y lo frena por tu casa 3.")
    assert explain(kp, "pt", "Posso alugar um carro?")["condition"].startswith("Vênus decide isto:")
    kp["debug"].pop("csl")      # no deciding planet -> the plain-language sentence is the fallback
    assert "terms you've read in full" in explain(kp, "en", "Can I lease a car?")["condition"]
