"""[day-answers 2026-10-05] From the full 10-chain audit (weakest topics: days 2.73, money 2.75, career change 3.00).

1. Day/week answers were GARBLED in 9 of 18 runs: apply_user_facing_strips('plain') runs _strip_day_names, which
   deletes bare weekday names — "but Monday carries the least strain" → "but carries…", "for Monday, and keep
   Tuesday light" → "for, and keep light" — and a second AI step then guessed at repairs. The weekly briefing hit
   the same bug on 2026-09-23 and fixed it with field_type='timing'; Ask never got the fix.
2. A hard-coded sentence in the 'deeper cross-check' layer ("Steady, grounded choices … than bold new bets")
   contradicted a YES / 'supports bold decisions' answer in the next turn.
3. 'against your timing's grain' leaked past the 'your grain' swap."""
import asyncio
from antar_engine import answer_polish as ap
from antar_engine.output_strips import apply_user_facing_strips as strips


def test_timing_field_type_keeps_weekdays_plain_deletes_them():
    t = "Monday, 5 Oct is your clearest day — but Monday carries the least strain. Schedule it for Monday, and keep Tuesday light."
    kept = strips(t, language="en", field_type="timing")
    assert "for Monday, and keep Tuesday light" in kept and "but Monday carries" in kept
    assert "for, and keep light" in strips(t, language="en", field_type="plain")   # the bug this avoids


def test_ask_localize_keeps_weekdays_only_for_day_questions():
    import main
    payload = {"read": "Monday is your clearest day, but Monday carries the least strain.",
               "next": "Schedule it for Monday, and keep Tuesday light."}
    kept = asyncio.run(main._ask_localize(dict(payload), "en", ["read", "next"], None, keep_days=True))
    assert "for Monday, and keep Tuesday light" in kept["next"] and "but Monday carries" in kept["read"]
    plain = asyncio.run(main._ask_localize(dict(payload), "en", ["read", "next"], None))
    assert "for, and keep light" in plain["next"]          # non-day answers still strip invented weekdays
    assert main._ASK_DAYNAME_Q.search("Is Friday good for the meeting?") and main._ASK_DAYNAME_Q.search("¿Va bien el lunes?")
    assert not main._ASK_DAYNAME_Q.search("How is my money looking right now?")


def test_a_yes_answer_does_not_also_warn_against_moving():
    p = {"read": "Yes — the window is open now. Steady, grounded choices beat bold bets. Your work is supported. Go ahead.",
         "next": "Send the proposal.", "verdict": "YES"}
    ap.polish_answer(p, "en", "When is a good time to make a big change?", "career", "")
    assert "bold bets" not in p["read"] and "Your work is supported" in p["read"]
    q = {"read": "Not yet — building. The reading strongly supports bold decisions. Prepare first. Keep notes.",
         "next": "Write the plan.", "verdict": "NOT_YET"}
    ap.polish_answer(q, "en", "When is a good time to make a big change?", "career", "")
    assert "bold decisions" not in q["read"]
    r = {"read": "a. Steady, grounded choices work here. c. d.", "next": "Do it.", "verdict": "YES"}
    ap.polish_answer(r, "en", "Is it risky to make bold bets?", "career", "")   # they asked about it → kept
    assert "Steady, grounded" in r["read"]


def test_cross_check_layer_no_longer_hardcodes_a_caution():
    import inspect, main
    src = inspect.getsource(main)
    assert "Steady, grounded choices tend to work" not in src


def test_timings_grain_and_single_best_client_move():
    assert ap.plain_words("The year runs with your timing's grain.", "en") == "The year runs with your timing."
    assert ap.plain_words("It is against the grain of your timing, honestly.", "en") .startswith("It is against your timing")
    for t in ("Identify your single highest-paying service or client this week and put more of your time there.",
              "Pick the one venture where your insight is the product."):
        p = {"read": "a. b. c.", "next": t}
        ap.polish_answer(p, "en", "Which profession fits me best?", "career", "spread")
        assert p["next"] != t
    ok = {"read": "a. b. c.", "next": "Review your costs this week."}
    ap.polish_answer(ok, "en", "q", "career", "spread")
    assert ok["next"] == "Review your costs this week."


def test_grain_is_gone_from_prompts_and_polished_when_it_leaks():
    import inspect, main
    src = inspect.getsource(main)
    assert "chart's grain" not in src and "AGAINST THE GRAIN" not in src and "scale grain" not in src
    assert ap.plain_words("Technology fits your grain, which is why it works.", "en") == \
        "Technology fits your natural strengths, which is why it works."
    assert ap.plain_words("It runs with your timing's strongest grain — that line.", "en") == \
        "It runs with your timing's natural fit — that line."
    assert ap.plain_words("Choose whole grain bread.", "en") == "Choose whole grain bread."   # food stays


def test_role_clarify_looks_at_what_was_typed_not_the_follow_up_rewrite():
    import main
    typed = "Which day this week is best for me?"
    rewritten = "Which day this week is best for me to push forward with new deals or big decisions?"
    assert main._ask_needs_role_clarify(rewritten, [])          # the trap: the rewrite looks like a deal question
    assert not main._ask_needs_role_clarify(typed, [])          # what they typed is not


def test_emergency_fund_is_not_funding_and_pick_one_direction_is_caught():
    p = {"read": "Income is steady. Open an emergency fund and move 10% of each payment into it. Keep costs low.",
         "next": "Open the emergency fund account this week."}
    ap.polish_answer(p, "en", "How is my money looking right now?", "finance", "")
    assert "emergency fund" in p["read"] and "emergency fund" in p["next"]
    q = {"read": "a. b. c.", "next": "Pick one clear direction over three scattered ones and give it your week."}
    ap.polish_answer(q, "en", "Which profession fits me best?", "career", "spread")
    assert "Pick one clear direction" not in q["next"]
    r = {"read": "a. Your next step is raising funding from investors. c.", "next": "Call two investors."}
    ap.polish_answer(r, "en", "How is my money looking right now?", "finance", "")
    assert "investors" not in r["read"] and "investors" not in (r["next"] or "")   # genuine unasked funding still dropped


def test_profession_answer_cannot_tell_a_spread_reader_to_narrow():
    cases = [("Raman, startup founder fits you. You have a pull toward leading; unfocused, that same drive scatters into too many "
              "directions at once. Operations-heavy work is uphill.", "Write down the kind of work where people come to you."),
             ("Shashi, you are built for research and public roles. Without focus, that same drive pulls you in too many "
              "directions, so pick your focus and commit to it. After 2028 analytical work fits.", "Keep it up.")]
    for r, n in cases:
        p = {"read": r, "next": n}
        ap.polish_answer(p, "en", "Which profession fits me best?", "career", "spread")
        assert not any(w in p["read"].lower() for w in ("scatter", "too many directions", "pick your focus", "commit to it"))
    q = {"read": "a. Unfocused drive scatters. c.", "next": "Do it."}
    ap.polish_answer(q, "en", "Which profession fits me best?", "career", "concentrate")
    assert "scatters" in q["read"]                      # concentrate charts are untouched
    es = {"read": "a. b. c.", "next": "Elige el próximo proyecto por su modo: asesoría o red."}
    ap.polish_answer(es, "es", "¿Qué profesión encaja mejor conmigo?", "career", "spread")
    assert "Elige el próximo proyecto" not in es["next"]


def test_career_fit_prompt_and_labels_do_not_say_scatter_or_grain():
    import inspect, main
    from antar_engine import subject_promise as sp
    src = inspect.getsource(main)
    assert "scatters into over-reach when unfocused" not in src and "KIND OF WORK, NOT HOW MANY" in src
    assert "against the grain" not in inspect.getsource(sp)


def test_lean_guard_forbids_praising_several_ventures_too():
    from antar_engine import wealth_magnitude as wm
    g = wm.LEAN_CONSISTENCY["spread"].lower()
    assert "never praise or recommend running several" in g and "reserve outside" in g


def test_money_fallback_varies_with_the_answer_and_never_repeats():
    tight = {"read": "Outflow is running ahead of what comes in. Savings feel pressured. Keep costs lean.", "next": None}
    ap.polish_answer(tight, "en", "How is my money looking right now?", "finance", "")
    assert "outflows" in tight["next"]
    easy = {"read": "Income is well supported. Gains are active. Keep going.", "next": None}
    ap.polish_answer(easy, "en", "How is my money looking right now?", "finance", "")
    assert "10%" in easy["next"]
    again = {"read": "Income is well supported. Gains are active. Keep going.", "next": None}
    ap.polish_answer(again, "en", "How is my money looking right now?", "finance", "", prev_moves=[easy["next"]])
    assert "10%" not in again["next"]
    rep = {"read": "a. b. c.", "next": "Name your biggest cash drain this week and cut it."}
    ap.polish_answer(rep, "en", "q", "finance", "", prev_moves=["Name your biggest cash drain this week and cut it."])
    assert rep["next"] != "Name your biggest cash drain this week and cut it."


def test_concentrate_or_diversify_verdict_sentence_is_pythons():
    from antar_engine import wealth_magnitude as wm
    r = wm.apply_alloc_opener("Raman, spread across more than one venture — don't put everything on one. Your earning power is "
                              "real. Cap each one.", "cvd_spread", "en", "Raman")
    assert r.startswith("Raman, spread your risk — keep part of what you earn in a reserve outside your ventures")
    assert "more than one venture" not in r and "Your earning power is real." in r
    es = wm.apply_alloc_opener("Jaime, diversifica — no concentres todo en un solo emprendimiento. Tus ingresos tienen espacio. "
                               "Guarda una parte.", "cvd_spread", "es", "Jaime")
    assert es.startswith("Jaime, reparte el riesgo") and "diversifica" not in es
    c = wm.apply_alloc_opener("Harleen, concentrate — put your main effort into what works. Your reputation builds. Pause the rest.",
                              "cvd_concentrate", "en", "Harleen")
    assert c.startswith("Harleen, concentrate — put your main effort and money behind what is already working")


def test_more_spanish_pick_one_forms_and_that_grain():
    for t in ("Elige un área concreta — asesoría, formación o análisis.", "Elige el próximo cliente o proyecto y ciérralo primero."):
        p = {"read": "a. b. c.", "next": t}
        ap.polish_answer(p, "es", "¿Qué profesión encaja mejor conmigo?", "career", "spread")
        assert p["next"] != t, t
    assert ap.plain_words("Your work as a founder already runs with that grain.", "en") == "Your work as a founder already fits that."
    import inspect, main
    assert "TIMING GRAIN" not in inspect.getsource(main)
