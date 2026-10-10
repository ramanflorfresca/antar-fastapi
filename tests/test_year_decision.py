"""[year-decision 2026-10-10] This Year's one coherent decision block."""
from datetime import date

from antar_engine.year_decision import compose

TODAY = date(2026, 10, 10)
P = {
    "period_end": "2026-11-26",
    "arcs": [{"key": "career", "name": "Career", "trend": "rising", "when": "peaks Oct 2026"},
             {"key": "business", "name": "Business", "trend": "steady", "when": "no clear signal this year"},
             {"key": "wealth", "name": "Wealth", "trend": "pressure", "when": "peaks Nov 2026"}],
    "active_domains": [{"label": "Risk & speculation", "convergence": True, "window": "2026-11-01 – 2026-11-13"}],
    "active": "Growth and teaching are the year's switched-on forces — mentor, learn, expand.",
    "build_this_year": ["Your savings and the money you keep — guard what you've made",
                        "A close professional collaboration that's been waiting — October through mid-November"],
    "protect_this_year": ["Any speculative bet — November brings risk"],
    "release_this_year": ["Any high-risk venture you've been considering — the odds are not in your favour"],
    "events": [{"date_label": "Aug 2026", "polarity": 1, "text": "A raise comes through."},
               {"date_label": "Oct 2026", "polarity": 1, "text": "A visible step up at work — take the high-stakes role."},
               {"date_label": "Nov 2026", "polarity": -1, "text": "Money comes under pressure."}],
}


def test_year_decision_counts_the_weeks_left_and_composes_from_structured_fields():
    d = compose(P, "en", TODAY, "You're running Rahu–Rahu (sub-period ends Apr 25, 2029)")
    assert d["prediction"] == ("This year (6 weeks left, to Nov 26): career is rising, peaks Oct 2026; "
                               "wealth comes under pressure, peaks Nov 2026.")
    assert d["why"].startswith("You're running Rahu–Rahu (sub-period ends Apr 25, 2029).")
    assert "Two timing systems agree on risk & speculation (Nov 1 to Nov 13)." in d["why"]
    assert d["holds"] == ("It holds if you build on your savings and the money you keep and a close professional "
                          "collaboration that's been waiting.")
    assert d["breaks"] == ("It breaks if you take on any high-risk venture you've been considering — "
                           "Nov 2026 is where the pressure lands.")
    assert d["move"].startswith("Oct 2026: a visible step up at work")


def test_a_past_months_event_is_never_the_move():
    q = dict(P, events=[{"date_label": "Aug 2026", "polarity": 1, "text": "A raise comes through."}])
    assert compose(q, "en", TODAY)["move"].startswith("Before Nov 26: protect any speculative bet")


def test_other_languages_and_empty_payloads_get_no_block():
    assert compose(P, "es", TODAY) is None and compose({}, "en", TODAY) is None
