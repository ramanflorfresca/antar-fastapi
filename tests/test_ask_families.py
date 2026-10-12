"""[ask-families + clock-deadline 2026-10-11] fixes from the 37-question money / business / job audit."""
from antar_engine import answer_polish as AP
from antar_engine import ask_families as F
from antar_engine.ask_basis import conditions
from tests.test_wa_bubbles import _chart as _base_chart


def _chart():
    """The shared fixture plus Saturn (ruler of the 2nd for a Capricorn lagna) and Jupiter so the money topics have a ruler to read."""
    chart, dashas = _base_chart()
    chart["planets"]["Saturn"] = {"sign": "Capricorn", "house": 1, "longitude": 280.0}
    chart["planets"]["Jupiter"] = {"sign": "Taurus", "house": 5, "longitude": 40.0}
    return chart, dashas


def test_each_decision_gets_its_own_family():
    cases = {"Should I fire someone on my team?": "fire", "Should I take this investor's offer?": "funding", "Should I bootstrap or raise?": "funding",
             "Will my startup get funded?": "funding", "Should I take a loan for my business?": "loan", "Should I consolidate my debts?": "debt",
             "When will I be debt free?": "debt", "Should I raise my prices?": "price", "How do I get more clients?": "clients",
             "Should I hire my first employee now?": "hire", "Should I hire a co-founder or stay solo?": "hire",
             "Should I take the new job offer?": "job_offer", "Is it a good time to ask for a raise?": "promotion",
             "Will I get promoted this year?": "promotion", "Should I quit my job and start my business?": "quit",
             "Should I switch careers?": "switch_career", "Should I expand my business now?": "expand", "Should I sell my business?": "sell",
             "Should I pivot my business?": "pivot", "Should I start a second business?": "second_business",
             "Is this a good year to buy a house?": "property", "Will my income increase this year?": "income"}
    for q, want in cases.items():
        assert F.family(q) and F.family(q)[0] == want, (q, F.family(q))
    assert F.family("") is None and F.family("What is my lucky colour?") is None and F.family(None) is None


def test_conditions_are_question_specific_but_keep_the_chart_clause():
    chart, dashas = _chart()
    debt = conditions("wealth", chart, dashas, "en", "Should I consolidate my debts?")
    price = conditions("wealth", chart, dashas, "en", "Should I raise my prices?")
    fund = conditions("funding", chart, dashas, "en", "Should I take this investor's offer?")
    assert debt.startswith("It works if each repayment fits inside your leanest month's income") and "new obligations arrive before the old ones are cleared" in debt
    assert price.startswith("It works if you test the new price on one new client") and "the price rises without the value they can see" in price
    assert "an investor can verify" in fund and "the terms are understood" in fund
    assert len({debt, price, fund}) == 3 and all("It breaks if" in c for c in (debt, price, fund))
    assert "In your chart it also helps if" in debt and "It holds if" not in debt       # the chart clause is still there, without a second lead-in
    generic = conditions("wealth", chart, dashas, "en", "What is going on with money?")
    assert not generic.startswith("It works if") and "It breaks if spending and commitments rise as fast as income does" in generic


def test_other_topics_and_languages_are_untouched():
    chart, dashas = _chart()
    assert not conditions("love", chart, dashas, "en", "Should I hire someone?").startswith("It works if")
    assert not conditions("health", chart, dashas, "en", "Should I fire someone?").startswith("It works if")
    assert conditions("career", chart, dashas, "pt", "Should I fire someone?") == ""


def test_clock_time_deadlines_are_removed_from_long_range_answers():
    read = "Expansion is moderately favorable now. Best window: act before 22:24 tonight on any outreach or pitch. Your network is the lever."
    new, ch = AP.strip_clock_deadlines(read, "Should I expand my business now?")
    assert ch and "22:24" not in new and "tonight" not in new and "Your network is the lever." in new
    nx, ch2 = AP.strip_clock_deadlines("Send the one pitch you've been delaying — before 22:24 tonight.", "Should I expand my business now?", allow_empty=True)
    assert ch2 and nx == ""
    hire = "Adding a hire before Nov 2026 puts pressure on cashflow. Wait until 22:24 tonight to make any commitments. Track where your hours go."
    new, ch3 = AP.strip_clock_deadlines(hire, "Should I hire my first employee now?")
    assert ch3 and "22:24" not in new and new.startswith("Adding a hire before Nov 2026") and new.endswith("Track where your hours go.")


def test_day_scope_questions_keep_their_clock_times():
    read = "The best window is before 22:24 tonight."
    for q in ("What should I do today?", "Is tonight a good time to sign?", "How is my day looking right now?"):
        assert AP.strip_clock_deadlines(read, q) == (read, False)
    assert AP.strip_clock_deadlines("Plain sentence.", "x") == ("Plain sentence.", False) and AP.strip_clock_deadlines(None, "x") == (None, False)


def test_a_read_is_never_emptied_by_the_clock_filter():
    only = "Act before 22:24 tonight."
    assert AP.strip_clock_deadlines(only, "Should I expand?") == (only, False)


# ---- operational decisions + question-specific fallback moves (owner 2026-10-11)
def test_operational_choices_are_recommendations_not_window_verdicts():
    from antar_engine import understand as U
    for q in ("Should I fire someone on my team?", "Should I raise my prices?", "How do I get more clients?", "Should I consolidate my debts?",
              "Should I pay off debt or invest first?"):
        assert F.is_operational(q) and U.suppress_verdict({"intent": "when"}, q), q
    for q in ("When will I be debt free?", "Should I hire my first employee now?", "Should I take a loan for my business?", "Will my startup get funded?",
              "Should I quit my job and start my business?", "Will I get out of financial trouble soon?", "Is it a good time to ask for a raise?", ""):
        assert not F.is_operational(q), q


def test_each_family_has_its_own_fallback_move_and_the_chart_clause_survives():
    from antar_engine.ask_basis import chart_move
    chart, dashas = _chart()
    moves = {}
    for q in ("Should I quit my job and start my business?", "Should I switch careers?", "Should I start a second business?",
              "Should I pivot my business?", "Should I sell my business?", "Should I expand my business now?", "Should I hire my first employee now?"):
        m = chart_move("business", chart, dashas, "en", q)
        assert m and m not in moves.values(), (q, m)
        moves[q] = m
    assert "runway in months" in moves["Should I quit my job and start my business?"]
    assert "paying customers" in moves["Should I pivot my business?"] and "run a month without you" in moves["Should I start a second business?"]
    assert all("your network and gains" in m for m in moves.values())              # the chart channel is in every one
    assert chart_move("business", chart, dashas, "en", "Anything about my business?") == chart_move("business", chart, dashas, "en")   # no family -> the old move
    assert chart_move("business", chart, dashas, "es", "Should I pivot?") == "" or isinstance(chart_move("business", chart, dashas, "es", "x"), str)


def test_the_old_canned_business_move_is_no_longer_the_answer_to_a_specific_decision():
    from antar_engine.ask_basis import chart_move
    chart, dashas = _chart()
    canned = chart_move("business", chart, dashas, "en")
    for q in ("Should I quit my job and start my business?", "Should I switch careers?", "Should I start a second business?"):
        assert chart_move("business", chart, dashas, "en", q) != canned


def test_polish_drops_the_verdict_and_timing_chips_for_an_operational_question():
    payload = {"read": "Hold the decision. It works if the expectations were written down.", "next": "Write down three things.", "verdict": "NOT_YET",
               "timing": "Nov 2026 \u2013 Jan 2027"}
    AP.polish_answer(payload, language="en", typed_question="Should I fire someone on my team?", concern="career")
    assert payload["verdict"] is None and payload["timing"] is None
    keep = {"read": "Likely within the year.", "next": "Do it.", "verdict": "LIKELY", "timing": "Jun 2027 \u2013 Oct 2027"}
    AP.polish_answer(keep, language="en", typed_question="When will I earn more?", concern="wealth")
    assert keep["verdict"] == "LIKELY" and keep["timing"] == "Jun 2027 \u2013 Oct 2027"


def test_operational_answers_never_talk_about_a_window_or_a_month():
    read = ("Hold off until Nov 2026 \u2014 that's the cleaner window for this call. A firing today carries real risk of blowback. "
            "It works if the expectations were written down. It holds if you build it \u2014 the ruler of your 10th house is weakened (the current sub-period runs to Apr 25, 2029). "
            "It breaks if the exit is made in frustration.")
    new, ch = AP.strip_window_talk(read)
    assert ch and "Nov 2026" not in new and "window" not in new and "A firing today carries real risk of blowback." in new
    assert "the current sub-period runs to Apr 25, 2029" in new                       # an engine fact, not a window
    nx, ch2 = AP.strip_window_talk("Document three incidents \u2014 have that record ready before Nov.", allow_empty=True)
    assert ch2 and nx == ""
    assert AP.strip_window_talk("Write down three things this person must change.") == ("Write down three things this person must change.", False)
    only = "The window for this is Nov 2026."
    assert AP.strip_window_talk(only) == (only, False)                                  # never empties a read


def test_polish_removes_window_talk_and_falls_back_to_the_decisions_own_move():
    payload = {"read": "Hold off until Nov 2026. A hasty firing risks blowback. It breaks if the exit is made in frustration.",
               "next": "Have that record ready before Nov.", "verdict": None, "timing": None}
    AP.polish_answer(payload, language="en", typed_question="Should I fire someone on my team?", concern="business")
    assert "Nov" not in payload["read"] and "Nov" not in (payload.get("next") or "") and payload["next"]

