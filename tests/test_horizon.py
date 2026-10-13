from antar_engine import horizon as H

SIG = {"headline": "A steady day for money and income.", "do_today": ["handle a money task"], "dont_today": ["Don't stake what you can't afford to lose"],
       "friction_for": ["Don't launch anything binding today"], "aligned_for": ["Audit a deal"],
       "windows": [{"kind": "avoid", "start": "4:54 PM", "end": "6:19 PM", "text": "Let it pass."},
                   {"kind": "best", "start": "12:17 PM", "end": "1:05 PM", "text": "Most auspicious."}],
       "hora": {"best_for": "the one thing that matters", "avoid_what": "hard conversations"}, "moon_sign": "Libra", "moon_nakshatra": "Swati"}
DEC = {"prediction": "Today favours work.", "why": "The Moon is in Libra.", "holds": "It holds if you decide at noon.",
       "breaks": "It breaks if you force a decision.", "move": "Between 12:17 PM and 1:05 PM, review a contract."}
FEED = {"next": [{"kind": "open", "topic": "money", "label": "Money", "start": "2027-01-10", "end": "2027-05-09"}],
        "care": [{"kind": "care", "topic": "business", "label": "Business", "start": "2027-02-09", "end": "2027-03-10"}]}
MONTH = {"decision": {"prediction": "This month favours money.", "why": "Mars is strong.", "holds": "It holds if you time the payout.",
                      "breaks": "It breaks if you bet.", "move": "Lock in a payout Oct 14-23."},
         "energy_level": "mixed", "period_start": "2026-09-26", "period_end": "2026-10-26",
         "best_week": "Week of October 26 — your pitch sharpens.", "caution_week": "Week of November 2 — a bet can backfire.",
         "priority_actions": [{"action": "Delay any long trip until after Oct 18."}, {"action": "Move on a savings decision Oct 14-23."},
                              {"action": "Put your name on visible work."}]}
YEAR = {"decision": {"prediction": "Career rises.", "why": "Two systems agree.", "holds": "It holds if you build.", "breaks": "It breaks if you gamble.", "move": "x"},
        "quality": "transformation", "period_end": "2026-11-26",
        "build_this_year": ["Your savings — guard them"], "release_this_year": ["Speculative bets — odds are poor"],
        "protect_this_year": ["Joint-money matters — hold off until 2027"],
        "critical_dates": [{"date": "October 2026", "event": "A collaboration smooths out."},
                           {"date": "November 2026", "event": "A speculative matter comes under pressure — protect savings."}]}


def test_today_blocks_and_order():
    c = H.build_today({**SIG, "decision": DEC}, FEED, "en", "Steady", "Monday, Oct 12")
    assert c["scope"] == "today" and c["available"] and c["tone"] == "Steady" and c["when"] == "Monday, Oct 12"
    assert c["short"] == "Today favours work." and c["watch"] == "It breaks if you force a decision." and c["work"] == "It holds if you decide at noon."
    assert c["do"][0] == "Handle a money task" and "Between 12:17" in c["do"][1] and len(c["do"]) == 2 and len(c["dont"]) == 2
    assert [x["kind"] for x in c["coming"]] == ["good", "care"] and c["coming"][0]["when"] == "12:17 PM – 1:05 PM"
    assert c["avoid"] == "Stay out of 4:54 PM – 6:19 PM for big decisions and tense conversations."
    assert c["far"] == "Next: money window: Jan 10 – May 9, 2027; care with business: Feb 9 – Mar 10, 2027"


def test_quiet_day_without_a_decision_falls_back_to_the_signals_own_lines():
    r = H.build_today(SIG, FEED, "en", "Steady", "Tue")
    assert r["short"] == "A steady day for money and income." and r["watch"] == "Avoid hard conversations."
    assert r["work"] == "The one thing that matters." and r["why"] == "The Moon is in Libra, in Swati."
    assert H.build_today(SIG, None, "en", "Steady", "Tue")["far"] == ""


def test_month_card():
    c = H.build_month(MONTH, FEED, "en")
    assert c["when"] == "Sep 26 – Oct 26" and c["tone"] == "Mixed"
    assert c["do"] == ["Move on a savings decision Oct 14-23.", "Put your name on visible work."] and c["dont"] == ["Delay any long trip until after Oct 18."]
    assert c["avoid"] == "Delay any long trip until after Oct 18." and c["coming"][0] == {"kind": "good", "title": "Strongest week", "when": "Week of October 26", "text": "Your pitch sharpens."}
    assert c["coming"][1]["kind"] == "care" and c["converse"]["chips"][0] == "How should I use the strongest week, Week of October 26?"


def test_year_card_labels_and_dates():
    c = H.build_year(YEAR, FEED, "en")
    assert c["when"] == "To Nov 26" and c["tone"] == "Transformation"
    assert c["do"] == ["Focus on: your savings — guard them"] and c["dont"] == ["Let go of: speculative bets — odds are poor"]
    assert c["avoid"] == "Joint-money matters — hold off until 2027"
    assert [x["kind"] for x in c["coming"]] == ["good", "care"] and c["coming"][0]["title"] == "October 2026"
    assert c["far"].startswith("Further ahead:") and c["converse"]["chips"][0] == "What should I do in October 2026?"


def test_missing_sources_are_unavailable_not_errors():
    for fn, arg in ((H.build_month, None), (H.build_year, {}), (H.build_month, {"decision": {}})):
        assert fn(arg, None, "en")["available"] is False
    assert H.build_today({}, None, "en")["available"] is False and H.build_today(None, None)["scope"] == "today"


def test_conversation_card_always_has_an_opener_and_a_focus_chip():
    c = H.build_year(YEAR, None, "en")
    assert c["converse"]["opener"] == "Want to talk this year through? Ask me anything about it." and len(c["converse"]["chips"]) == 3
    es = H.build_month(MONTH, None, "es")
    assert es["converse"]["opener"].startswith("¿Quieres hablar de este mes?") and es["label"] == "Este mes"
    assert es["converse"]["chips"][-1] == "¿En qué debo enfocarme este mes?"
