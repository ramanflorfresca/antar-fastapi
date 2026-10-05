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
    assert u.concern_override(r, "general") == "divorce"          # [r15] keyword found NO topic → 0.6 is enough
    assert u.concern_override(u.parse(_raw(area="separation", confidence=0.5)), "general") is None
    assert u.concern_override(r, "career") is None                # a real keyword topic still needs 0.75
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


# ── audit round 7 ─────────────────────────────────────────────────────────────
def test_off_topic_pressure_dropped_from_health_answer():
    t = "Your recovery is slow right now. Loan and business stress also weigh on the body. Sleep earlier."
    out = u.drop_off_topic_pressure(t, "health_self", "Why is my health so hard?")
    assert "business" not in out.lower() and "Sleep earlier" in out


def test_pressure_kept_when_topic_is_money_or_asker_raised_it():
    t = "Savings are under pressure. Pause one expense."
    assert u.drop_off_topic_pressure(t, "income_money", "Why is money tight?") == t
    assert u.drop_off_topic_pressure(t, "health_self", "Is my debt hurting my health?") == t


def test_pressure_guard_never_empties():
    t = "Your business is under pressure."
    assert u.drop_off_topic_pressure(t, "marriage", "Will I marry?") == t


def test_parent_work_skips_health_and_non_work_has_no_business_talk():
    from antar_engine import parent_work as pw
    assert not pw.applies("How is my father's health?", {"area": "health_other"})
    assert pw.applies("Is it better to work with my father?", {"area": "business_partnership"})
    assert pw.is_work_question("work with my father", {})
    assert not pw.is_work_question("Where will my relationship with my father take me?", {"area": "family"})


def test_relationship_answer_drops_deal_talk():
    t = "This is a heavy time. A partnership agreement you sign now needs care. Say one clear boundary this week."
    out = u.drop_off_topic_pressure(t, "separation", "Mera talaq kaisa rahega?")
    assert "agreement" not in out and "boundary" in out
    assert u.drop_off_topic_pressure(t, "separation", "Should I sign the partnership deal with my ex?") == t


def test_parent_health_block_forbids_conditions():
    from antar_engine import parent_work as pw
    b = pw.health_block("father")
    assert "Do NOT name any condition" in b and pw.health_block(None) == ""


# ── audit round 8 ─────────────────────────────────────────────────────────────
def test_separation_question_excludes_new_relationship():
    assert u.separation_question({"area": "separation"}, "Kya mera talaq safal hoga?")
    assert not u.separation_question({"area": "separation"}, "Will I remarry after the divorce?")
    assert not u.separation_question({"area": "marriage"}, "Will I marry?")
    assert "new partner" in u.separation_block()


def test_separation_answer_drops_new_partner_talk():
    t = "This is a heavy season. A new partnership is supported. Name one boundary this week."
    out = u.drop_off_topic_pressure(t, "separation", "Could my separation get better?")
    assert "partnership" not in out and "boundary" in out
    assert u.drop_off_topic_pressure(t, "separation", "Will I find a new partner after the divorce?") == t


def test_asserted_loans_dropped_unless_asked():
    t = "Buying him out looks supported. Only if the loan terms stay manageable. Check the price first."
    out = u.drop_asserted_loans(t, "Vale a pena comprar a parte dele?")
    assert "loan terms" not in out and "Check the price" in out
    assert u.drop_asserted_loans(t, "Should I take a loan to buy him out?") == t
    t2 = "Legal pressure is high. Not a loan or external capital — your reputation is the lever."
    assert "loan" not in u.drop_asserted_loans(t2, "Mera case itna mushkil kyun hai?")


def test_legal_and_move_topics_no_longer_exempt_from_pressure_guard():
    t = "The move needs a calm week. Your business isn't yet stable. Visit the place first."
    assert "business" not in u.drop_off_topic_pressure(t, "residence_move", "Should I move?")


def test_life_purpose_is_a_subject_not_vague():
    import main
    assert not main._ask_is_vague("What should I do about my life purpose?")
    assert not main._ask_is_vague("What should I do about my retirement?")
    assert main._ask_is_vague("What should I do?")


# ── audit round 9 ─────────────────────────────────────────────────────────────
def test_parse_model_json_takes_the_corrected_last_object():
    raw = ('```json\n{"read": "first", "next": "a"}\n``` Wait — let me fix that: json\n'
           '{"read": "second", "next": "b"}')
    assert u.parse_model_json(raw)["read"] == "second"
    assert u.parse_model_json('{"read": "ok", "next": null}')["read"] == "ok"
    assert u.parse_model_json("no json here") is None


def test_json_leak_detector():
    assert u.looks_like_json_leak('`json\n{"read": "x"}')
    assert u.looks_like_json_leak('{"read": "x"}')
    assert not u.looks_like_json_leak("Raman, this is a normal answer.")


def test_child_word_lowers_children_override_floor():
    uu = {"area": "children_wellbeing", "confidence": 0.65}
    assert u.concern_override(uu, "career", question="Mere bachcha ke liye kya karun?") == "children"
    assert u.concern_override(uu, "career", question="What should I do for work?") is None


def test_why_and_kids_blocks():
    assert "REASON" in u.why_block({"intent": "why"}) and u.why_block({"intent": "when"}) == ""
    assert "mentee" in u.kids_block({"area": "children_conception"}) and u.kids_block({"area": "marriage"}) == ""


def test_existing_relationship_drops_new_partner_talk():
    t = "This weight is real. A future partnership is supported. Say one honest thing this week."
    out = u.drop_off_topic_pressure(t, "existing_relationship", "Why is my marriage so hard?")
    assert "partnership" not in out and "honest thing" in out


def test_separation_does_not_assume_home():
    t = "The stretch is hard. Protect your home and any financial agreement. Get documents reviewed."
    out = u.separation_assumes_home(t, "Como está meu separação?")
    assert "home" not in out and "documents" in out
    assert u.separation_assumes_home(t, "Who keeps the house?") == t


# ── audit round 10 ────────────────────────────────────────────────────────────
def test_kids_block_male_and_never_asserts_pregnancy():
    b = u.kids_block({"area": "children_conception"}, "", "male")
    assert "MAN" in b and "NEVER state that a pregnancy" in b and "mentors" in b
    assert "MAN" not in u.kids_block({"area": "children_conception"}, "", "female")


def test_separation_block_assumes_no_legal_papers():
    b = u.separation_block()
    assert "Do NOT assume legal proceedings" in b and "document reviewed" not in b


def test_safe_next_separation_and_purpose():
    n = "Kisi trusted professional se apne documents review karwao — khud sign karne se pehle."
    assert "documents" not in u.safe_next("separation", n, "Kya mera talaq behtar hoga?", "hinglish")
    assert u.safe_next("separation", n, "My lawyer sent the settlement papers", "en") == n
    biz = "Kal apne business ka sabse bada blocker likh lo."
    assert "business" not in u.safe_next("purpose_spiritual", biz, "Mere jeevan ka maqsad?", "hinglish")
    assert u.safe_next("career_job", biz, "x", "en") == biz


def test_loan_wording_widened_but_money_topics_exempt():
    t = "Buying him out fits, but only if o empréstimo ou os termos forem administráveis. Revise o preço."
    out = u.drop_asserted_loans(t, "Vale a pena comprar a parte dele?", "business_partnership")
    assert "empréstimo" not in out and "Revise o preço" in out
    assert u.drop_asserted_loans(t, "Devo captar?", "funding_investment") == t


def test_purpose_block():
    assert "not work" in u.purpose_block({"area": "purpose_spiritual"})
    assert u.purpose_block({"area": "career_job"}) == ""


def test_kids_offtopic_drops_mentor_and_fathers_side():
    t = "Conditions are mixed. Your father's side looks steady. A mentor is worth leaning on. See your doctor."
    out = u.kids_offtopic(t, "children_conception", "How is my pregnancy looking?")
    assert "mentor" not in out and "father" not in out and "doctor" in out
    assert u.kids_offtopic(t, "children_conception", "How is my father with my pregnancy?") == t
    assert u.kids_offtopic(t, "career_job", "x") == t


# ── audit round 11 ────────────────────────────────────────────────────────────
def test_legal_cause_words_dropped_unless_asked():
    t = "The case leans in your favour. It likely touches fraud or a regulatory angle. Prepare your papers."
    out = u.drop_other_people_claims(t, "legal_case", "Why is my court case so hard?")
    assert "fraud" not in out and "Prepare" in out
    assert u.drop_other_people_claims(t, "legal_case", "My case is about tax fraud") == t


def test_other_people_claims_dropped():
    assert "reliab" not in u.drop_other_people_claims(
        "Caution. La confiabilidad de tu hermano en el seguimiento se lee más débil. Escribe los términos.",
        "business_partnership", "¿Me conviene asociarme con mi hermano?")
    assert "mushkil" not in u.drop_other_people_claims(
        "Aapka bachcha mushkil mein hai. Doctor se baat karo.", "health_other", "Mera bachcha kab theek hoga?")
    assert "family se door" not in u.drop_other_people_claims(
        "Abhi aapka family se door hona kathin hai. Kisi trusted insaan se baat karo.", "separation", "Talaq?")
    assert "contract" not in u.drop_other_people_claims(
        "Aapka property ya contract foreign land mein ready hai. Mentor se baat karo.", "foreign_travel_visa", "Videsh?")
    assert "hidden gains" not in u.drop_other_people_claims(
        "Your hidden gains and home are safer with trust. Take it slowly.", "marriage", "Where will my marriage lead?")


def test_retirement_question_gets_retirement_block_and_next():
    assert u.is_retirement_q("¿Cómo va mi jubilación?") and u.is_retirement_q("Mera retirement kab theek hoga?")
    assert "Do NOT answer with client wins" in u.retirement_block("How is my retirement?")
    assert u.retirement_block("How is my work?") == ""
    n = "Is hafte ek concrete step lo apne business ke cashflow ko stable karne ke liye."
    assert "business" not in u.safe_next("general", n, "Mera retirement kab theek hoga?", "hinglish")


def test_kids_offtopic_covers_portuguese_fathers_side():
    t = "Há pressão este ano. O lado da família do seu pai parece mais apoiado. Fale com seu médico."
    assert "pai" not in u.kids_offtopic(t, "children_conception", "Como está meu gravidez?")


# ── audit round 12 ────────────────────────────────────────────────────────────
def test_loan_clause_cut_from_a_one_sentence_next_step():
    t = "Analise a avaliação da compra da participação e quaisquer termos de empréstimo linha por linha antes de aceitar."
    out = u.drop_asserted_loans(t, "Vale a pena comprar a parte dele?", "business_partnership")
    assert "empréstimo" not in out and "Analise a avaliação" in out and "linha por linha" in out


# ── audit round 13 ────────────────────────────────────────────────────────────
def test_kids_guard_drops_congratulations_and_older_helper():
    t = "Felicidades por el embarazo. La temporada pide pasos firmes. Seu pai ou alguém mais velho pode ajudar. Fale com seu médico."
    out = u.kids_offtopic(t, "children_conception", "¿Qué debo hacer con mi embarazo?")
    assert "Felicidades" not in out and "mais velho" not in out and "médico" in out
    # congratulations are dropped even if a parent is named
    assert "Congratulations" not in u.kids_offtopic("Congratulations! Rest well.", "children_conception", "My mother and my pregnancy")


def test_relationship_floor_adds_reason_and_soft_when():
    one = "Raman, yeh dard real hai — aur aap akele nahi hain isme."
    out = u.relationship_floor(one, {"area": "separation", "intent": "why"}, "hinglish")
    assert out.startswith(one) and "strain" in out
    two = "Hard stretch. Steady choices help."
    assert u.relationship_floor(two, {"area": "separation", "intent": "why"}, "en") == two
    w = u.relationship_floor("This is a heavy season. Lean on someone.", {"area": "separation", "intent": "when"}, "en")
    assert "No single date" in w
    assert u.relationship_floor("Easing by Nov 2026. Hold on.", {"area": "separation", "intent": "when"}, "en") == "Easing by Nov 2026. Hold on."
    assert u.relationship_floor("Text.", {"area": "career_job", "intent": "when"}, "en") == "Text."


def test_kids_guard_restores_an_on_topic_sentence():
    t = "Felicidades por el embarazo. Tus ahorros están bajo presión."
    out = u.kids_offtopic(t, "children_conception", "¿Qué debo hacer con mi embarazo?", "es")
    assert "Felicidades" not in out and "crecimiento familiar" in out and "ahorros" in out


# ── audit round 14 ────────────────────────────────────────────────────────────
def test_dharma_never_reaches_the_user():
    assert u.strip_system_terms("pode fazer o dharma (propósito de vida) parecer distante", "pt") == \
        "pode fazer o propósito de vida parecer distante"
    assert "dharma" not in u.strip_system_terms("Tu dharma pide calma.", "es").lower()
    assert u.strip_system_terms("Nothing special here.", "en") == "Nothing special here."


def test_invented_bail_dropped_unless_asked():
    t = "Ainda não. A caução está segurando o avanço. Liste os obstáculos."
    assert "caução" not in u.drop_invented_legal(t, "Quando vai melhorar meu processo?")
    assert u.drop_invented_legal(t, "A caução foi paga, e agora?") == t


def test_education_floor_and_next():
    r, n = u.education_floor("O potencial de negócios é real.", "Anote o que seu negócio precisa.",
                             {"area": "education_exam"}, "O que devo fazer com meu prova?", "pt")
    assert "estudo" in r and "bloco diário de estudo" in n
    r2, n2 = u.education_floor("Your exam preparation is steady.", "", {"area": "education_exam"}, "x", "en")
    assert r2 == "Your exam preparation is steady." and "study block" in n2
    assert u.education_floor("Text", "Next", {"area": "career_job"}, "x", "en") == ("Text", "Next")


def test_new_bond_and_foreign_property_variants():
    t = "A promessa de um novo vínculo está no seu mapa. Fale com alguém de confiança."
    assert "novo vínculo" not in u.drop_off_topic_pressure(t, "existing_relationship", "Quando vai melhorar meu casamento?")
    f = "Há um contrato ou questão de propriedade a resolver. Defina três passos."
    assert "propriedade" not in u.drop_other_people_claims(f, "foreign_travel_visa", "Onde minha mudança vai me levar?")


# ── audit round 15 ────────────────────────────────────────────────────────────
def test_guards_never_leave_only_a_question():
    t = "O potencial de negócios é real. Quer que eu olhe os próximos meses para ver onde o ritmo muda?"
    out = u.drop_off_topic_pressure(t, "residence_move", "Qual é o melhor caminho para meu casa nova?")
    assert "potencial" in out                      # the reading survives; the offer alone would not
    ok = "A casa tem apoio. Quer que eu olhe os próximos meses?"
    assert u.drop_off_topic_pressure(ok, "residence_move", "x") == ok


def test_keyword_general_yields_to_a_specific_reading_at_lower_confidence():
    uu = {"area": "health_self", "confidence": 0.6}
    assert u.concern_override(uu, "general") == "health"
    assert u.concern_override(uu, "career") is None        # a real keyword topic still needs 0.75


def test_separation_word_beats_a_residence_misread():
    raw = '{"area":"residence_move","intent":"yes_no","confidence":0.8,"language":"pt"}'
    r = u.parse(raw, "Seria bom mudar meu separação?")
    assert r and r["area"] == "separation"
    r2 = u.parse(raw, "Seria bom mudar minha casa?")
    assert r2 and r2["area"] == "residence_move"


def test_separation_outlook_line_for_where_how_and_works_out():
    for intent in ("where_who", "how", "yes_no"):
        out = u.relationship_floor("This stretch is hard. Lean on someone.", {"area": "separation", "intent": intent}, "en")
        assert "slow easing" in out
    already = "It is hard but it does ease over time."
    assert u.relationship_floor(already, {"area": "separation", "intent": "how"}, "en") == already
    assert u.relationship_floor("Hard stretch.", {"area": "separation", "intent": "how"}, "es").endswith("ayudan.")


def test_invented_home_strain_dropped_for_separation():
    t = "This is a tough time. Things at home feel strained. Name one boundary."
    assert "at home" not in u.separation_assumes_home(t, "How is my separation looking?")


def test_pregnancy_in_progress_drops_the_window_sentence():
    assert u.pregnancy_in_progress("Quando vai melhorar meu gravidez?") and not u.pregnancy_in_progress("When will I conceive?")
    t = "A janela de outubro a janeiro é a mais favorável para a área de família. Fale com seu médico."
    out = u.kids_offtopic(t, "children_conception", "Quando vai melhorar meu gravidez?", "pt")
    assert "janela" not in out and "médico" in out


def test_pregnancy_in_progress_drops_month_range_family_growth_sentence():
    t = "O período de outubro até janeiro traz o sinal mais favorável do ano para crescimento familiar. Marque uma consulta médica."
    out = u.kids_offtopic(t, "children_conception", "Quando vai melhorar meu gravidez?", "pt")
    assert "outubro" not in out and "consulta" in out


# ── audit round 16 ────────────────────────────────────────────────────────────
def test_explicit_topic_word_names_one_area_or_none():
    assert u.explicit_area("Vale a pena mudar meu separação?") == "separation"
    assert u.explicit_area("¿Me conviene cambiar mi salud?") == "health_self"
    assert u.explicit_area("Why is my income so hard?") == "income_money"
    assert u.explicit_area("Does my health affect my income?") is None        # two topics → no lock
    assert u.explicit_area("What should I do?") is None


def test_unsure_reading_yields_to_the_topic_word():
    raw = '{"area":"speculation_betting","intent":"yes_no","confidence":0.3,"language":"pt"}'
    r = u.parse(raw, "Vale a pena mudar meu saúde?")
    assert r and r["area"] == "health_self"
    # a confident reading is not overridden
    raw2 = '{"area":"career_job","intent":"yes_no","confidence":0.9,"language":"en"}'
    assert u.parse(raw2, "Will my health startup raise money?")["area"] == "career_job"


def test_named_topic_the_reading_agrees_with_needs_almost_no_confidence():
    uu = {"area": "separation", "confidence": 0.3}
    assert u.concern_override(uu, "speculation", question="Vale a pena mudar meu separação?") == "divorce"
    assert u.concern_override(uu, "speculation", question="Vale a pena mudar?") is None


def test_guard_never_starts_on_a_sentence_that_leans_on_a_deleted_one():
    t = ("Your business has hidden gains in play. These build the exact skills that raise your odds. "
         "Pick one course this week.")
    out = u.drop_off_topic_pressure(t, "education_exam", "What type of courses should I take?")
    assert not out.lstrip().startswith("These")


def test_father_asserted_and_single_child_claims():
    t = "Your father is the authority figure backing you. Pick one clear role."
    assert "authority figure backing" not in u.drop_other_people_claims(t, "business_partnership", "Father or partners?")
    assert "tends to" in u.drop_other_people_claims("Your father's backing tends to help. Write roles down.",
                                                    "business_partnership", "Father or partners?")
    es = "Llama a tu hijo esta semana. Escribe lo que necesitas."
    out = u.drop_other_people_claims(es, "separation", "¿Cuál es el mejor camino para mi separación?")
    assert "tu hijo" not in out and "uno de tus hijos" in out
    assert "tu hijo" in u.drop_other_people_claims(es, "separation", "¿Debo llamar a mi hijo?")


def test_lean_not_field_rule_is_in_the_guardrails():
    assert "LEAN" in u.guardrails_block()


def test_connector_openers_count_as_dangling():
    t = "A separação pesa agora. Porém, o período pede cuidado. Fale com alguém de confiança."
    out = u.drop_off_topic_pressure("Seu negócio tem pressão. " + t.split(". ", 1)[1], "separation", "Vale a pena mudar meu separação?")
    assert not out.lstrip().startswith("Porém")


# ── audit round 17 ────────────────────────────────────────────────────────────
def test_window_started_helper():
    import main
    from datetime import date
    t = date(2026, 10, 5)
    assert main._ask_window_started("Oct 2026", t) and main._ask_window_started("Sep 2026 – Nov 2026", t)
    assert not main._ask_window_started("Nov 2026 – Jan 2027", t) and not main._ask_window_started("", t)


def test_retirement_word_locks_the_money_topic():
    assert u.explicit_area("Mera retirement kab theek hoga?") == "income_money"


def test_kids_guard_drops_hinglish_and_english_fathers_side():
    t = "Conditions are mixed. Aapke father ki taraf se jo long-view support hai, woh stable hai. Doctor se baat karo."
    assert "father" not in u.kids_offtopic(t, "children_wellbeing", "Mera bachcha mujhe kahan le jayega?", "hinglish")
    e = "Mixed season. Your father's influence and the long view look supported. See your doctor."
    assert "father" not in u.kids_offtopic(e, "children_conception", "How is my pregnancy looking?", "en")


def test_no_boss_for_the_self_employed():
    assert "chefe" not in u.no_boss("Revise o que seu chefe ou clientes precisam.", "Como está meu primeiro emprego?")
    assert u.no_boss("Your boss sees it.", "Should I tell my boss?") == "Your boss sees it."
    assert "key clients" in u.no_boss("Your boss sees it.", "How is work?")


def test_voice_gate_allows_literal_house_on_home_questions():
    import main
    t = "Your new house needs steady care this year."
    assert "house" not in main._ask_voice_text(t, "O que devo fazer com meu casa nova?")
    assert main._ask_voice_text("The seventh house is active.", "What about my new house?") == "The seventh house is active."
    assert main._ask_voice_text(t, "How is my career?") == t


# ── audit round 18 ────────────────────────────────────────────────────────────
def test_far_years_are_cut_unless_asked():
    out = u.drop_far_years("Is saal chances kam hain; yeh period partnership ke liye quieter hai, 2044 tak.", "Kya is saal meri shaadi hogi?")
    assert "2044" not in out and out.endswith("quieter hai.")
    assert "2040s" not in u.drop_far_years("This chapter runs through the early 2040s for ventures.", "How is my career?")
    assert "2027" in u.drop_far_years("The window opens Jun 2027.", "When?")
    assert "2044" in u.drop_far_years("By 2044 you retire.", "Will I retire by 2044?")


def test_male_pregnancy_guard():
    t = "Carrying a pregnancy solo takes courage. The season is mixed. Call your midwife or doctor today."
    out = u.male_pregnancy_guard(t, "children_conception", "male")
    assert "Carrying" not in out and "midwife" not in out and "doctor" in out
    assert u.male_pregnancy_guard(t, "children_conception", "female") == t


def test_next_floor_replaces_fragments():
    # [audit-b3] a fragment is handed to answer_polish's topic-specific fallback (None here)
    assert u.next_floor("Keep it practical.", "en") is None
    assert u.next_floor("Mantenha isso prático, não romântico.", "pt") is None
    long = "Call your father this week and say the one thing you have been holding back."
    assert u.next_floor(long, "en") == long and u.next_floor(None, "en") is None


def test_kids_next_replaces_mentor_step():
    n = "Call your mentor or a trusted elder this week and talk through what support looks like."
    assert "doctor" in u.kids_next(n, "children_conception", "Why is my pregnancy so hard?", "en")
    assert u.kids_next(n, "career_job", "x", "en") == n


# ── audit round 19 ────────────────────────────────────────────────────────────
def test_relationship_next_replaces_money_steps():
    n = "Apne savings ko pehle protect karo — ek stable income base banao."
    assert "rishta" in u.relationship_next(n, "marriage", "Kya is saal meri shaadi hogi?", "hinglish")
    b = "This week, name one concrete thing in your business that needs steadying."
    assert "partnership" in u.relationship_next(b, "existing_relationship", "When will my marriage improve?", "en")
    ok = "Tell one trusted friend what you want from your next relationship."
    assert u.relationship_next(ok, "marriage", "Will I marry?", "en") == ok
    assert u.relationship_next(n, "marriage", "Will money problems hurt my marriage?", "en") == n


def test_drop_asker_health_on_parent_health_questions():
    t = "Your father needs a check-up. Health issues are active on your end though. Book it today."
    out = u.drop_asker_health(t, "health_other", "When will my father's health improve?")
    assert "your end" not in out and "check-up" in out


def test_credit_related_terms_and_later_years():
    t = "Review your case documents. Check the credit-related terms carefully. Bring questions to your lawyer."
    assert "credit" not in u.drop_asserted_loans(t, "Kya mera case safal hoga?", "legal_case")
    assert u.explicit_area("Could my later years get better this year?") == "income_money"
    assert u.is_retirement_q("How will my later life look?")


# ── audit round 20 ────────────────────────────────────────────────────────────
def test_plain_money_and_spanish_financial_stress_leave_love_and_health_answers():
    t = "Partnership is possible. Money and family matters would pile on stress. Start with something light."
    out = u.drop_off_topic_pressure(t, "existing_relationship", "Which path is best for my love life?")
    assert "Money" not in out and "light" in out
    h = "Tu cuerpo pide estabilidad. Hay estrés financiero al mismo tiempo. Descansa cada día."
    assert "financiero" not in u.drop_off_topic_pressure(h, "health_self", "¿Qué debo hacer con mi salud?")


def test_male_pregnancy_big_news_and_next_step():
    t = "Raman, esto es una noticia grande. La temporada es mixta."
    assert "noticia" not in u.male_pregnancy_guard(t, "children_conception", "male")
    n = "Llama esta semana a tu médico para hablar sobre tu embarazo."
    assert "en tu familia" in u.male_pregnancy_guard(n, "children_conception", "male")


def test_new_union_wording_dropped_for_existing_relationship():
    t = "La promesa de una nueva unión es real. Escribe lo que necesitas de verdad."
    out = u.drop_off_topic_pressure(t, "existing_relationship", "¿Cuándo mejorará mi matrimonio?")
    assert "unión" not in out and "Escribe" in out
