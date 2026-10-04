"""Understanding layer (antar_engine/understand.py): strict parsing, menus, safety OR."""
import json
from antar_engine import understand as u


def _raw(**kw):
    base = {"language": "en", "standalone": "Will my partnership break?", "intent": "yes_no",
            "area": "partnership_ending", "subject": "business_partner", "polarity": "feared",
            "horizon_days": None, "yes_no_fit": True, "crisis": False, "gambling": False,
            "needs_clarification": False, "clarify": "", "confidence": 0.93}
    base.update(kw)
    return "here you go " + json.dumps(base)


def test_parse_valid_and_maps_to_kp_and_concern():
    r = u.parse(_raw(), "Will my partnership break")
    assert r["area"] == "partnership_ending" and r["polarity"] == "feared"
    assert u.kp_type(r) == "loss" and u.concern(r) == "business"


def test_unknown_area_rejected_and_bad_enums_defaulted():
    assert u.parse(_raw(area="astrology_stuff")) is None
    r = u.parse(_raw(intent="banana", language="klingon", subject="cat", horizon_days="soon"))
    assert r["intent"] == "open" and r["language"] == "other" and r["subject"] == "self"
    assert r["horizon_days"] is None


def test_garbage_is_none():
    assert u.parse("no json here") is None and u.parse("") is None


def test_every_area_says_how_kp_and_ask_read_it():
    from antar_engine.kp.kp_significators import QUESTION_TYPES
    for area, (qt, concern) in u.AREAS.items():
        assert concern, area
        assert qt is None or qt == "loss" or qt in QUESTION_TYPES, (area, qt)


def test_safety_is_an_or_never_weaker():
    assert u.safety({"crisis": False, "gambling": False}, True, False) == {"crisis": True, "gambling": False}
    assert u.safety({"crisis": True, "gambling": True}, False, False) == {"crisis": True, "gambling": True}
    assert u.safety(None, False, True)["gambling"] is True


def test_compare_flags_disagreements():
    r = u.parse(_raw())
    d = u.compare(r, {"language": "hinglish", "kp_type": None, "concern": "business",
                      "yes_no": True, "gambling": False, "crisis": False})
    assert not d["language"]["agree"] and not d["kp_type"]["agree"] and d["concern"]["agree"]


def test_request_carries_thread_and_saved_language():
    txt = u.request("and tomorrow?", [{"question": "How is speculation today?", "answer": "Cautious."}], "es")
    assert "Earlier question: How is speculation today?" in txt and "es" in txt
    assert txt.strip().endswith("Message: and tomorrow?")


def test_memo_and_worth_reading():
    k = u.memo_key("Will I pass?", [], "")
    u.memo_put(k, {"area": "education_exam"})
    assert u.memo_get(k) == {"area": "education_exam"}
    assert not u.worth_reading("13") and not u.worth_reading("ok") and u.worth_reading("Will I pass?")


def test_golden_set_is_valid():
    import os
    p = os.path.join(os.path.dirname(__file__), "fixtures", "nlu_golden.jsonl")
    for line in open(p):
        r = json.loads(line)
        for a in (r.get("area") or []):
            assert a in u.AREAS, a
        assert r.get("language") in (None,) + u.LANGS


def test_shadow_never_touches_the_answer(monkeypatch):
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    import main
    async def fake_call(**kw):
        return (_raw(), None)
    monkeypatch.setattr(main, "call_llm_claude", fake_call)
    monkeypatch.setattr(main, "_ask_recent_thread", lambda *a, **k: [])
    logged = []
    class T:
        def insert(self, row): logged.append(row); return self
        def execute(self): return None
    monkeypatch.setattr(main.supabase, "table", lambda name: T())
    asyncio.run(main._nlu_shadow("Will my partnership break", "c1", "en", "whatsapp", "explore"))
    assert logged and logged[0]["understanding"]["area"] == "partnership_ending"
    assert isinstance(logged[0]["disagree"], list) and logged[0]["channel"] == "whatsapp"


def test_feared_partnership_event_is_its_ending():
    r = u.parse(_raw(area="business_partnership", polarity="feared"))
    assert r["area"] == "partnership_ending" and u.kp_type(r) == "loss"
    r = u.parse(_raw(area="existing_relationship", polarity="feared"))
    assert r["area"] == "separation"
    r = u.parse(_raw(area="business_partnership", polarity="wanted"))
    assert r["area"] == "business_partnership"


# ── stated life facts (live 2026-10-03: unemployed reader told about a promotion) ──
def test_stated_facts_parsed_and_menu_checked():
    r = u.parse(_raw(stated_facts={"work": "unemployed", "relationship": "astronaut",
                                   "children": "maybe", "other": ["has debt", "", "x" * 200, "a", "b"]}),
                "I am unemployed and I have debt.")
    f = r["stated_facts"]
    assert f["work"] == "unemployed" and f["relationship"] is None and f["children"] is None
    assert f["other"][0] == "has debt" and len(f["other"]) == 3 and len(f["other"][1]) <= 80


def test_unemployed_block_forbids_promotion_and_boss():
    r = u.parse(_raw(stated_facts={"work": "unemployed", "other": ["unfocused for months"]}),
                "I am unemployed and unfocused for months.")
    b = u.stated_block(r)
    assert "UNEMPLOYED" in b and "promotion" in b and "boss" in b
    assert "They told you: unfocused for months." in b
    assert u.life_overrides(r) == {"employed": False}


def test_no_stated_facts_no_block():
    r = u.parse(_raw())
    assert u.stated_block(r) == "" and u.life_overrides(r) == {}


def test_relationship_and_children_overrides():
    r = u.parse(_raw(stated_facts={"relationship": "divorced", "children": "no"}),
                "I'm divorced and I don't have kids.")
    assert u.life_overrides(r) == {"partnered": False, "has_children": False}
    assert "DIVORCED" in u.stated_block(r) and "NO children" in u.stated_block(r)


def test_harvest_writes_only_empty_fields(monkeypatch):
    from dotenv import load_dotenv
    load_dotenv()
    import main
    import antar_engine.profile_harvest as ph
    wrote = []
    monkeypatch.setattr(ph, "apply_harvest", lambda sb, cid, facts: wrote.append(facts) or {"written": list(facts)})
    r = u.parse(_raw(stated_facts={"work": "unemployed", "relationship": "single"}),
                "I'm single and unemployed.")
    row = {"career_stage": "", "marital_status": "married"}
    main._ask_harvest_stated("c1", row, r)
    assert wrote == [{"career_stage": {"value": "between_jobs", "evidence": "stated (nlu)"}}]
    assert row["career_stage"] == "between_jobs" and row["marital_status"] == "married"



# ── warm opening ──
def test_struggling_feeling_adds_a_warm_opening_rule():
    r = u.parse(_raw(feeling="stuck"))
    b = u.tone_block(r)
    assert "they sound stuck" in b and "Never open with blame" in b


def test_neutral_or_unknown_feeling_adds_nothing():
    assert u.tone_block(u.parse(_raw(feeling="curious"))) == ""
    assert u.parse(_raw(feeling="ecstatic-ish"))["feeling"] == "neutral"
    assert u.tone_block(u.parse(_raw())) == ""


# ── comparisons, how they earn, wealth promises (live 2026-10-03, Andres) ──
def test_options_and_earning_parsed():
    r = u.parse(_raw(intent="which", options=["gold mine deals", "defence contracts", "real estate", ""],
                     stated_facts={"work": "self_employed", "earning": ["advisory", "commission", "equity", "magic"]}),
                "Gold, defence or real estate? I earn advisory + commission + sweat equity")
    assert r["options"] == ["gold mine deals", "defence contracts", "real estate"]
    assert r["stated_facts"]["earning"] == ["advisory", "commission", "equity"]
    assert u.is_comparison(r)


def test_comparison_block_forbids_a_winner_and_uses_how_they_earn():
    r = u.parse(_raw(intent="which", options=["gold", "defence"],
                     stated_facts={"earning": ["advisory", "commission", "equity"]}),
                "gold or defence, advisory + commission + equity")
    b = u.comparison_block(r)
    assert "Do NOT name a winner" in b and "stronger bet" in b
    assert "advisory fees + commission + equity / sweat equity" in b
    assert "NEVER assume how a deal is structured" in b
    assert u.comparison_block(u.parse(_raw())) == ""


def test_stored_earning_roundtrip():
    stored = u.EARNS_PREFIX + u.earning_text(["advisory", "commission"])
    assert u.stored_earning(stored) == "advisory fees + commission"
    assert "advisory fees + commission" in u.earning_line(stored)
    assert u.earning_line("Engineer") == "" and u.stored_earning("") == ""


def test_wealth_promise_gets_the_honesty_rule():
    r = u.parse(_raw(outcome_claim=True), "Which work gives me the most money?")
    assert "can't honestly promise an amount" in u.outcome_block(r)
    assert u.outcome_block(u.parse(_raw())) == ""


def test_earning_saved_into_empty_profession_only(monkeypatch):
    from dotenv import load_dotenv
    load_dotenv()
    import main
    import antar_engine.profile_harvest as ph
    wrote = []
    monkeypatch.setattr(ph, "apply_harvest", lambda sb, cid, facts: wrote.append(facts) or {})
    r = u.parse(_raw(stated_facts={"earning": ["advisory", "commission", "equity"]}),
                "I do advisory for a commission plus sweat equity")
    main._ask_harvest_stated("c1", {"profession": None, "career_stage": "x"}, r)
    assert wrote[-1]["profession"]["value"] == "Earns via advisory fees + commission + equity / sweat equity"
    wrote.clear()
    main._ask_harvest_stated("c1", {"profession": "Lawyer", "career_stage": "x"}, r)
    assert not wrote


def test_invented_role_is_replaced_by_the_stated_one_or_neutralised():
    t = "Your trading role is the same in both."
    known = "advisory fees + commission + equity / sweat equity"
    assert u.scrub_invented_role(t, known) == "Your role as an advisor earning commission and equity is the same in both."
    assert u.scrub_invented_role(t, "") == "Your role in these deals is the same in both."
    assert u.scrub_invented_role("Your role as a trader matters.", "") == "Your role matters."
    assert u.scrub_invented_role("As an investor you hold the lever.", "") == "In your role you hold the lever."
    assert u.scrub_invented_role("Your role as an advisor is clear.", known) == "Your role as an advisor is clear."



def test_earning_the_message_never_said_is_dropped():
    r = u.parse(_raw(stated_facts={"earning": ["trading"]}), "Gold or defence — which should I focus on?")
    assert r["stated_facts"]["earning"] == []
    r = u.parse(_raw(stated_facts={"earning": ["trading", "commission"]}), "Gano comisión por cada trato")
    assert r["stated_facts"]["earning"] == ["commission"]


# ── answer guards (live 2026-10-03, Raman's chart) ──
def test_wealth_creation_and_max_potential_are_outcome_claims():
    for q in ["Which helps me most with wealth creation or reaching my maximum potential?",
              "¿Cuál me hará millonario?", "Qual me dá o maior potencial?", "Will tech make me rich?"]:
        assert u.parse(_raw(), q)["outcome_claim"], q
    assert not u.parse(_raw(), "How is my career this year?")["outcome_claim"]


def test_investment_advice_sentence_is_dropped():
    t = ("Technology fits how you work. Put your savings into a few different tech companies "
         "instead of putting everything into just one. Cap what rides on any single venture.")
    out = u.guard_answer(t, "Which works best for me?")
    assert "savings into" not in out and out.startswith("Technology fits") and "Cap what rides" in out


def test_invented_industry_claim_is_dropped():
    t = ("Technology fits how you work. Defense and gold mining need lots of physical work and "
         "careful cost-cutting, which doesn't match your strengths. Your window is open now.")
    out = u.guard_answer(t, "q", ["defense", "gold mining", "technology"])
    assert "physical work" not in out and "Your window is open now." in out


def test_finances_are_reading_not_fact_unless_they_said_so():
    t = "Since you don't have much extra money saved up, go after the fastest deal."
    assert u.guard_answer(t, "Which works best?") == \
        "Since the reading shows pressure on your savings, go after the fastest deal."
    assert u.guard_answer(t, "I have no savings, which works best?") == t


def test_guard_never_empties_and_rules_block_exists():
    t = "Put your savings into stocks."
    assert u.guard_answer(t, "q") == t
    assert "Never tell them where to put savings" in u.guardrails_block()


def test_every_area_concern_is_a_real_ask_concern():
    from antar_engine.ask_consultation import CONCERN_HOUSES
    for area, (_qt, c) in u.AREAS.items():
        assert c in CONCERN_HOUSES, (area, c)


def test_concern_override_only_when_confident_and_specific():
    r = u.parse(_raw(area="business_partnership", confidence=0.9))
    assert u.concern_override(r, "love") == "business"          # live: partners -> spouse
    assert u.concern_override(r, "business") is None
    assert u.concern_override(u.parse(_raw(area="business_partnership", confidence=0.5)), "love") is None
    assert u.concern_override(u.parse(_raw(area="general", confidence=0.99)), "love") is None


def test_what_to_do_questions_get_no_verdict_lead():
    assert u.suppress_verdict(u.parse(_raw(intent="what_to_do")))
    assert u.suppress_verdict(u.parse(_raw(intent="why")))
    assert not u.suppress_verdict(u.parse(_raw(intent="when")))
    assert not u.suppress_verdict(u.parse(_raw(intent="yes_no")))
    assert not u.suppress_verdict(None)


def test_invented_background_is_dropped_only_when_unknown():
    t = ("Your strongest asset is already built — finance and bookkeeping management expertise "
         "is real and marketable. Pick one low-cost course in financial analysis this week.")
    out = u.drop_invented_background(t, background_known=False)
    assert "already built" not in out and out.startswith("Pick one low-cost course")
    assert u.drop_invented_background(t, background_known=True) == t
    assert u.drop_invented_background("Your experience in sales helps.", False) == "Your experience in sales helps."  # never empty



def test_invented_background_variants():
    for t in ["Your core finance and bookkeeping expertise is already your strongest card — deepen it.",
              "Your finance and bookkeeping management expertise is real and marketable.",
              "Your background in finance is solid."]:
        out = u.drop_invented_background(t + " Pick one course this week.", False)
        assert out == "Pick one course this week.", (t, out)



def test_field_network_becomes_your_network_when_background_unknown():
    t = "Send one message to an authority figure from your finance network this week."
    assert u.drop_invented_background(t, False) == \
        "Send one message to an authority figure from your network this week."
    assert u.drop_invented_background(t, True) == t
    assert "your professional network" in u.drop_invented_background("Use your professional network.", False)



def test_past_work_needs_evidence_and_is_saved_to_empty_life_work(monkeypatch):
    msg = "Right now I am doing nothing. In June I was laid off, I was working as a finance/book keeping manager."
    r = u.parse(_raw(stated_facts={"work": "unemployed", "past_work": "finance / bookkeeping manager",
                                   "other": ["laid off in June"]}), msg)
    assert r["stated_facts"]["past_work"] == "finance / bookkeeping manager"
    assert u.parse(_raw(stated_facts={"past_work": "finance manager"}), "What work suits me?")["stated_facts"]["past_work"] is None
    from dotenv import load_dotenv
    load_dotenv()
    import main
    import antar_engine.profile_harvest as ph
    wrote = []
    monkeypatch.setattr(ph, "apply_harvest", lambda sb, cid, facts: wrote.append(facts) or {})
    main._ask_harvest_stated("c1", {"life_work": None, "career_stage": "between_jobs"}, r)
    assert wrote[-1]["life_work"]["value"] == "Formerly finance / bookkeeping manager (laid off)"
    assert "finance / bookkeeping manager" in u.past_work_line("Formerly finance / bookkeeping manager (laid off)")


def test_known_background_keeps_true_facts():
    t = "Harleen, being laid off is a hard stop. Message one contact from your finance network."
    kb = "Formerly finance / bookkeeping manager (laid off)"
    assert u.guard_answer(t, "What courses?", None, unemployed=True, known_background=kb) == t
    assert u.drop_invented_background(t, background_known=True) == t



def test_clear_open_question_word_beats_a_vague_model_intent():
    assert u.parse(_raw(intent="what_to_do"), "How is my income looking?")["intent"] == "how"
    assert u.parse(_raw(intent="what_to_do"), "¿Cómo va mi deuda?")["intent"] == "how"
    assert u.parse(_raw(intent="open"), "Where will my exam results take me?")["intent"] == "where_who"
    assert u.parse(_raw(intent="what_to_do"), "What should I do about my career?")["intent"] == "what_to_do"
    assert u.parse(_raw(intent="yes_no"), "When will I marry?")["intent"] == "yes_no"   # model's specific read kept

# ── explicit statements update the profile (owner 2026-10-03) ──
def _ex(msg, **sf):
    return u.parse(_raw(stated_facts=sf), msg)


def test_explicit_statement_updates_a_changed_value():
    r = _ex("I'm married now and we just moved", relationship="married", explicit_now=["relationship"])
    assert u.explicit_updates(r, {"marital_status": "single"}) == {"marital_status": ("single", "married")}
    r = _ex("I was laid off last week", work="unemployed", explicit_now=["work"])
    assert u.explicit_updates(r, {"career_stage": "mid_career"}) == {"career_stage": ("mid_career", "between_jobs")}


def test_same_meaning_or_no_evidence_or_question_changes_nothing():
    r = _ex("I run my own business", work="self_employed", explicit_now=["work"])
    assert u.explicit_updates(r, {"career_stage": "entrepreneur"}) == {}             # same meaning
    r = _ex("I have two kids", children="yes", explicit_now=["children"])
    assert u.explicit_updates(r, {"children_status": "adult_children"}) == {}        # compatible
    r = _ex("Will I get married next year?", relationship="married", explicit_now=["relationship"])
    assert r["stated_facts"]["explicit_now"] == []                                   # a question
    r = _ex("I'm separated. Will we get back together?", relationship="separated", explicit_now=["relationship"])
    assert r["stated_facts"]["explicit_now"] == ["relationship"]                     # statement + question
    r = _ex("Mi esposa y yo hablamos hoy", relationship="married", explicit_now=["relationship"])
    assert u.explicit_updates(r, {"marital_status": "separated"}) == {}              # "my wife" ≠ status
    r = _ex("Estoy separado de mi esposa", relationship="separated", explicit_now=["relationship"])
    assert u.explicit_updates(r, {"marital_status": "married"}) == {"marital_status": ("married", "separated")}


def test_between_jobs_reads_as_in_transition_not_job():
    from antar_engine.life_context import _norm_career
    assert _norm_career({"career_stage": "between_jobs"}) == "in_transition"


def test_explicit_update_goes_through_harvest_and_logs(monkeypatch):
    from dotenv import load_dotenv
    load_dotenv()
    import main
    import antar_engine.profile_harvest as ph
    wrote = []
    monkeypatch.setattr(ph, "apply_harvest", lambda sb, cid, facts: wrote.append(facts) or {})
    class T:
        def insert(self, row): return self
        def execute(self): return None
    monkeypatch.setattr(main.supabase, "table", lambda n: T())
    r = _ex("I just got a job at a bank", work="employed", explicit_now=["work"])
    row = {"career_stage": "between_jobs", "profession": None, "life_work": "x"}
    main._ask_harvest_stated("c1", row, r)
    assert wrote[-1]["career_stage"]["value"] == "employed" and row["career_stage"] == "employed"



def test_answer_audit_round_fixes():
    out = u.guard_answer("Be careful: you owe money on a loan, so go slow.", "What should I do to grow my business?")
    assert "you owe" not in out and "the reading shows loan pressure" in out
    b = u.what_to_do_block(u.parse(_raw(intent="what_to_do")))
    assert 'FIRST sentence of "read"' in b and "course" in b
    cb = u.comparison_block(u.parse(_raw(intent="which", options=["crypto", "gold"])))
    assert "INVESTMENTS" in cb and "SOMEONE ELSE" in cb and "FIELDS of work or study" in cb

# ── stated facts need evidence in the message (live eval 2026-10-03) ──
def test_guessed_facts_are_dropped():
    r = u.parse(_raw(stated_facts={"work": "unemployed"}), "¿Cuándo voy a conseguir trabajo estable en los próximos 3 meses?")
    assert r["stated_facts"]["work"] is None
    r = u.parse(_raw(stated_facts={"relationship": "single"}), "Is it a good time to talk to my ex again?")
    assert r["stated_facts"]["relationship"] is None
    r = u.parse(_raw(stated_facts={"work": "self_employed"}), "Meu sócio quer sair da empresa. Vale a pena comprar a parte dele?")
    assert r["stated_facts"]["work"] is None


def test_real_statements_are_kept():
    assert u.parse(_raw(stated_facts={"work": "unemployed"}), "I was laid off in March.")["stated_facts"]["work"] == "unemployed"
    assert u.parse(_raw(stated_facts={"relationship": "married"}), "We just got married.")["stated_facts"]["relationship"] == "married"
    assert u.parse(_raw(stated_facts={"children": "yes"}), "Mera beta 12th mein hai")["stated_facts"]["children"] == "yes"
    assert u.parse(_raw(stated_facts={"work": "self_employed"}), "Will my startup get funded?")["stated_facts"]["work"] == "self_employed"



def test_own_topic_threshold_is_lower_than_override():
    r = u.parse(_raw(area="separation", confidence=0.7))
    assert u.concern_override(r, "general") is None                                   # 0.75 rule
    assert u.concern_override(r, "general", u.OWN_TOPIC_MIN_CONFIDENCE) == "divorce"  # beats inheritance
    assert u.concern_override(u.parse(_raw(area="general", confidence=0.99)), "general", 0.6) is None



def test_loans_asserted_as_existing_are_rewritten_in_three_languages():
    g = u.guard_answer
    assert "existing" not in g("Watch your existing loans before expanding.", "How is my business this month?")
    assert "debt service" not in g("The debt service claims each wave of income.", "Why does my money never last?")
    assert "préstamo existente" not in g("Ten cuidado con un préstamo existente.", "¿Cómo está mi negocio este mes?")
    assert "deuda vigente" not in g("Hay una carga de deuda vigente.", "¿Debo invertir en mi negocio ahora?")
    assert "dívidas existentes" not in g("Cuidado com dívidas existentes.", "Devo investir no meu negócio agora?")
    # they mentioned their loan → left alone
    t = "Watch your existing loans before expanding."
    assert g(t, "I have a loan — should I expand?") == t


def test_comparison_match_names_the_fitting_option():
    r = u.parse(_raw(intent="which", options=["technology", "brokerage transactions"]))
    b = u.comparison_block(r, "", fit_fields=["technology & innovation", "science & research"])
    assert 'MATCH: the option "technology" matches their #1 field' in b
    r = u.parse(_raw(intent="which", options=["gold mine deals", "defence contracts"]))
    assert "MATCH" not in u.comparison_block(r, "", fit_fields=["technology & innovation"])


# ── audit round 6 (2026-10-03) ──
def test_listing_things_is_not_a_choice():
    r = u.parse(_raw(intent="yes_no", options=["gold mine deals", "processing plant", "refinery"]),
                "Will I make good money doing deals with gold mine, processing plant and refinery")
    assert not u.is_comparison(r)
    r = u.parse(_raw(intent="yes_no", options=["technology", "brokerage"]),
                "Should I focus on technology or brokerage transactions")
    assert u.is_comparison(r)
    r = u.parse(_raw(intent="which", options=[]), "Gold or defence — which should I focus on?")
    assert u.is_comparison(r)
    assert u.parse(_raw(options=["a", "b"]), "¿Me conviene vender o quedarme?")["has_choice"]


def test_parent_gains_are_a_tendency_not_a_history():
    g = u.guard_answer
    assert g("Your father's backing helps; some of your gains have come through him, and that holds.", "q") == \
        "Your father's backing helps; his backing tends to help some of your gains, and that holds." or \
        "have come through him" not in g("some of your gains have come through him.", "q")
    assert "have come through" not in g("Your gains came from your father.", "q")
    assert g("Your gains come from your own effort.", "q") == "Your gains come from your own effort."


def test_unemployed_next_step_no_longer_implies_a_current_job():
    out = u.guard_answer("Ask anyone in charge at your money or bookkeeping job for a lead.", "q", unemployed=True)
    assert "your money or bookkeeping job" not in out and "in your field" in out
    keep = "Ask anyone in charge at your money or bookkeeping job for a lead."
    assert u.guard_answer(keep, "q", unemployed=False) == keep


def test_ordinary_good_money_question_is_not_a_wealth_promise():
    r = u.parse(_raw(outcome_claim=True, intent="yes_no"),
                "Will I make good money doing deals with gold mine, processing plant and refinery")
    assert not r["outcome_claim"]
    assert u.parse(_raw(outcome_claim=True), "Which work will give me the most money?")["outcome_claim"]
    assert u.parse(_raw(outcome_claim=False), "Does technology suit me to make me a millionaire?")["outcome_claim"]
    assert u.parse(_raw(outcome_claim=True), "Will I earn 10 million by 2030?")["outcome_claim"]
