"""[month-decision 2026-10-10] This Month's one coherent decision block."""
from datetime import date

from antar_engine.month_decision import compose

TODAY = date(2026, 10, 10)
P = {
    "month": "October 2026", "range": "SEP 26 – OCT 26",
    "overview": "Watch your spending on relationships and comfort. Overspending could undermine what you're building.",
    "best_week": {"label": "Oct 26 – Nov 1"}, "caution_week": {"label": "Oct 10–16"},
    "strong_planets": ["Mars", "Mercury"], "weak_planets": ["Sun", "Rahu", "Venus"],
    "active_domains": [
        {"key": "speculation", "label": "Risk & speculation", "score": 8.9, "window": "2026-10-07 – 2026-10-08",
         "caution": True, "polarity": "opportunity", "convergence": True},
        {"key": "travel", "label": "Travel & foreign", "score": 6.75, "window": "2026-10-09 – 2026-10-18",
         "caution": True, "polarity": "opportunity", "convergence": False},
        {"key": "money", "label": "Money & wealth", "score": 6.0, "window": "2026-10-14 – 2026-10-23",
         "caution": False, "polarity": "opportunity", "convergence": False},
        {"key": "work", "label": "Work & reputation", "score": 3.64, "window": "2026-10-12 – 2026-10-24",
         "caution": True, "polarity": "opportunity", "convergence": False}],
    "priority_actions": [
        {"action": "Cap your exposure on any speculative bet before October 8 — set a stop-loss.", "domain": "Risk & speculation"},
        {"action": "Delay any long trip or foreign commitment until after October 18.", "domain": "Travel & foreign"},
        {"action": "Move on a savings decision or lock in a payout between October 14 and 23.", "domain": "Money & wealth"},
        {"action": "Put your name on a visible piece of work the week of October 19.", "domain": "Work & reputation"}],
}


def test_month_decision_drops_past_windows_and_restraint_domains_from_the_favoured_list():
    d = compose(P, "en", TODAY, "You're running Rahu–Rahu (sub-period ends Apr 25, 2029)")
    assert d["prediction"] == ("This month (Sep 26 – Oct 26) favours money & wealth and work & reputation. "
                               "Travel & foreign calls for caution. The strongest stretch is Oct 26 – Nov 1.")
    assert "speculation" not in d["prediction"].lower()          # its window (Oct 7-8) is over
    assert d["why"].startswith("Mars and Mercury are strong this month; Sun, Rahu and Venus are under strain.")
    assert "Rahu–Rahu (sub-period ends Apr 25, 2029)" in d["why"]
    assert d["holds"] == ("It holds if you time the savings or payout decision for Oct 14 – Oct 23 and the visible work "
                          "for Oct 12 – Oct 24; the strongest week overall is Oct 26 – Nov 1.")
    assert d["breaks"] == "It breaks if you commit to long trips during Oct 10–16, or let spending run ahead of income."
    assert d["move"].startswith("Move on a savings decision")


def test_a_move_whose_dates_have_passed_is_never_offered():
    q = dict(P, priority_actions=[
        {"action": "Cap your exposure before October 8.", "domain": "Money & wealth"},
        {"action": "Put your name on a visible piece of work the week of October 19.", "domain": "Work & reputation"}])
    assert compose(q, "en", TODAY)["move"].startswith("Put your name on a visible piece of work")


def test_other_languages_and_empty_payloads_get_no_block():
    assert compose(P, "es", TODAY) is None and compose({}, "en", TODAY) is None
