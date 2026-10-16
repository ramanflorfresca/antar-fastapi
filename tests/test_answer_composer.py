"""[answer-composer 2026-10-16] One astrologer-shaped answer from the engines' own numbers; no disclaimer step; plain; dated."""
from datetime import date

from antar_engine import answer_composer as ac, ritual_today as rt

TODAY = date(2026, 10, 16)


def test_plan_routes_a_confident_own_life_question_and_picks_the_horizon():
    u = {"area": "health_self", "intent": "how", "confidence": 0.9, "subject": "self", "horizon_days": 200}
    assert ac.plan(u) == {"topic": "health", "scope": "year", "gambling": False}
    assert ac.plan({**u, "horizon_days": 1})["scope"] == "day" and ac.plan({**u, "horizon_days": 5})["scope"] == "week"
    assert ac.plan({**u, "horizon_days": 30})["scope"] == "month"


def test_plan_leaves_crisis_other_people_yes_no_and_unknown_areas_alone():
    base = {"area": "health_self", "intent": "how", "confidence": 0.9, "subject": "self", "horizon_days": 30}
    assert ac.plan({**base, "crisis": True}) is None and ac.plan({**base, "subject": "other"}) is None
    assert ac.plan({**base, "intent": "yes_no"}) is None and ac.plan({**base, "area": "nonsense"}) is None
    assert ac.plan({**base, "confidence": 0.2}) is None and ac.plan(None) is None


HEALTH = {"available": True, "constitution": {"level": "moderate"}, "chronic": {"is_chronic": False},
          "nature": ["the nervous system, skin, or anxiety — the digestive system"],
          "care": ["steady the nervous system and skin — regular sleep, less caffeine and screen time; in Ayurveda, brahmi or gotu kola"]}
HTIME = {"windows": [{"start": "2027-01-01", "end": "2027-12-31", "year": 2027}]}


def test_health_answer_says_focus_on_health_names_the_area_and_ends_with_checkups_no_herbs_or_disclaimer():
    r = ac.compose(ac.health_facts(HEALTH, HTIME, "year", TODAY), TODAY)
    assert r["read"].startswith("Your chart asks you to put your health first this year.")
    assert "It points to the nervous system, skin, or anxiety, with the digestive system most exposed, and it reads as something passing, not structural." in r["read"]
    assert "The most sensitive stretch is around 2027." in r["read"]
    assert r["next"].endswith("and keep regular medical checkups.") and "Ayurveda" not in r["next"] and "brahmi" not in r["next"]
    assert "not a diagnosis" not in r["read"] and rt.jargon_leaks({"r": r["read"], "n": r["next"]}) == []


def test_robust_health_with_no_window_says_steady():
    h = {**HEALTH, "constitution": {"level": "robust"}}
    r = ac.compose(ac.health_facts(h, {"windows": []}, "month", TODAY), TODAY)
    assert r["read"].startswith("Your health looks steady this month")


LEGAL = {"available": True, "propensity": {"level": "elevated"}, "outcome": {"lean": "contested"},
         "likely_causes": ["partnership and paperwork"]}


def test_legal_answer_names_what_is_showing_and_gives_the_practical_step():
    r = ac.compose(ac.legal_facts(LEGAL, {"windows": [{"start": "2026-09-01", "end": "2026-12-31"}]}, "year", TODAY), TODAY)
    assert r["read"].startswith("Legal and paperwork matters are showing this year, tied to partnership and paperwork.")
    assert "leans both ways" in r["read"] and "This stretch runs until Dec 31." in r["read"]
    assert "Be careful what you sign" in r["next"] and "speak to a lawyer" not in r["read"].lower()


def test_quiet_legal_year_still_gives_the_careful_step():
    r = ac.compose(ac.legal_facts({"available": True, "propensity": {"level": "low"}}, {"windows": []}, "year", TODAY), TODAY)
    assert r["read"].startswith("No strong legal pressure shows this year") and r["next"].startswith("Be careful what you sign")


def test_period_paragraph_is_used_as_is():
    f = ac.period_facts({"paragraph": "Career is steady this month. Nothing strong pushes it either way."}, None, None, "career", "month")
    assert ac.compose(f, TODAY)["read"].startswith("Career is steady this month.")
    assert ac.period_facts({"paragraph": ""}, None, None, "career", "month") is None


def test_when_sentence_now_next_and_year_labels():
    w = [{"kind": "care", "start": "2026-08-01", "end": "2026-10-31"}, {"kind": "open", "start": "2027-02-01", "end": "2027-03-01"}]
    assert ac.when_sentence(w, TODAY, "en") == "This stretch runs until Oct 31."
    assert ac.when_sentence(w[1:], TODAY, "en") == "The next open stretch starts Feb 1, 2027 – Mar 1, 2027."
    assert ac.when_sentence([], TODAY, "en") is None


def test_nothing_real_means_none():
    assert ac.compose(None, TODAY) is None and ac.health_facts({"available": False}, {}, "month", TODAY) is None
    assert ac.legal_facts(None, {}, "month", TODAY) is None


def test_speculation_answer_is_the_persons_own_pattern_with_no_best_day_and_no_game_line():
    for st, must in (("losses", "points to losses"), ("no", "honest answer is no"), ("later", "opens Jun 2027"), ("open", "open now")):
        f = ac.speculation_facts(st, "Jun 2027" if st in ("later", "open") else "", "month", None, "how is my casino luck", "en")
        r = ac.compose(f, TODAY)
        assert must in r["read"] and r["next"]
        assert "casino, lottery or betting-specific" not in r["read"] and "best day" not in r["read"].lower()
        assert rt.jargon_leaks({"r": r["read"], "n": r["next"]}) == []


def test_speculation_day_question_puts_todays_read_first_and_unknown_state_is_none():
    f = ac.speculation_facts("losses", "", "day", "Risk runs against you today — a bet is prone to unravel.", "how is speculation today", "en")
    assert ac.compose(f, TODAY)["read"].startswith("Risk runs against you today")
    assert ac.speculation_facts("weird", "", "day", None, "", "en") is None


def _ses(*nets, valid=True):
    return [{"net_units": n, "valid": valid} for n in nets]


def test_own_pattern_speaks_only_when_clear_and_a_caution():
    assert ac.own_pattern(_ses(-50, -20, 30, -10, -40, 5), "en") == (
        "Your own logged sessions point the same way: 2 of 6 finished up, and the total is down. "
        "Use the window for unearned income and keep any play small and capped.")
    assert ac.own_pattern(_ses(-50, -20, 30, -10), "en") is None                       # too few sessions
    assert ac.own_pattern(_ses(80, 20, 30, -10, 40, 5), "en") is None                 # a good run: say nothing, never encourage
    assert ac.own_pattern(_ses(-50, 20, 30, -10, -40, 25), "en") is None              # up 3 of 6: not clearly against
    assert ac.own_pattern(_ses(-5, -5, -5, -5, -5, valid=False), "en") is None        # invalid sessions are ignored
    assert ac.own_pattern([{"net_units": None, "valid": True}] * 6, "en") is None and ac.own_pattern(None) is None


def test_own_pattern_is_added_after_the_window_and_stays_plain():
    own = ac.own_pattern(_ses(-50, -20, 30, -10, -40, 5), "en")
    r = ac.compose(ac.speculation_facts("later", "Jun 2027 – Oct 2027", "year", None, "how is speculation", "en", own), TODAY)
    assert r["read"].index("opens Jun 2027") < r["read"].index("Your own logged sessions") and rt.jargon_leaks({"r": r["read"]}) == []
