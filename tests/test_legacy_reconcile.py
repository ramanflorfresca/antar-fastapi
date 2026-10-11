"""[legacy-reconcile 2026-10-11] the old Today / Month / Year fields must agree with the decision block."""
from datetime import date

from antar_engine import legacy_reconcile as LR
from antar_engine import today_decision as TD
from antar_engine import month_decision as MD
from antar_engine import year_decision as YD

DO_MAP = {
    "work": {"do": "push a stuck work task to done", "dont": "x"},
    "money": {"do": "handle a money task you've been putting off", "dont": "y"},
    "travel": {"do": "take the short trip or make the far-off call", "dont": "z"},
    "speculation": {"do": "take a small, capped position only if you must", "dont": "s"},
}


def _today():
    return {
        "headline": "Today lights up a journey or something far from home — take it, but keep a stop.",
        "highlight": "Today's momentum is in a journey or something far from home — lean in.",
        "todays_nudge": "Say yes to the new thing today.", "move": "Say yes to the new thing today.",
        "el_movimiento": "Say yes to the new thing today.",
        "moon_nakshatra": "Swati", "moon_sign": "Libra", "moon_house_from_lagna": 10, "lit_domain": "career & visibility",
        "signals": [{"key": "nakshatra", "value": "Chitra · Sadhana", "direction": "supportive"}],
        "evidence": {"chosen": ["work", "network"], "lead_dir": "positive"},
        "headline_domains": ["Travel & foreign", "Risk & speculation", "Work & reputation", "Money & wealth"],
        "do_today": ["take the short trip or make the far-off call", "push a stuck work task to done",
                     "handle a money task you've been putting off"],
        "do_today_why": ["w-travel", "w-work", "w-money"],
        "dont_today": ["don't stake what you can't afford to lose"],
        "haz_hoy": ["Make the career move you've been sitting on."],
        "hora": {"best_window": "12:17 PM – 1:05 PM"}, "rahu_kalam": "8:28 AM – 9:52 AM",
        "domains": [{"key": "money", "state": "caution", "name": {"en": "Money"}}],
    }


def test_today_headline_and_move_follow_the_decision():
    p = _today()
    dec = TD.compose(p, "en")
    LR.today(p, dec, "en", do_by_domain=DO_MAP)
    assert "journey" not in p["headline"].lower() and "work and reputation" in p["headline"]
    assert p["highlight"] == dec["move"] == p["todays_nudge"] == p["move"] == p["el_movimiento"]


def test_today_moon_star_comes_from_the_signal_row():
    p = _today()
    LR.today(p, TD.compose(p, "en"), "en")
    assert p["moon_nakshatra"] == "Chitra"


def test_today_do_list_drops_the_off_lead_item_and_keeps_alignment():
    p = _today()
    LR.today(p, TD.compose(p, "en"), "en", do_by_domain=DO_MAP)
    assert p["do_today"] == ["push a stuck work task to done", "handle a money task you've been putting off"]
    assert p["do_today_why"] == ["w-work", "w-money"]


def test_today_do_list_never_empties():
    p = _today()
    p["do_today"] = ["take the short trip or make the far-off call"]
    p["do_today_why"] = ["w-travel"]
    LR.today(p, TD.compose(p, "en"), "en", do_by_domain=DO_MAP)
    assert p["do_today"] == ["push a stuck work task to done"] and len(p["do_today_why"]) == 1


def test_today_headline_chips_lead_with_the_decision_lead():
    p = _today()
    LR.today(p, TD.compose(p, "en"), "en", do_by_domain=DO_MAP)
    assert p["headline_domains"][0] == "Work & reputation" and p["headline_domains"][1] == "Money & wealth"


def test_today_is_idempotent_and_spanish_leaves_english_only_filters_alone():
    p = _today()
    dec = TD.compose(p, "en")
    LR.today(p, dec, "en", do_by_domain=DO_MAP)
    snap = dict(p)
    assert LR.today(p, dec, "en", do_by_domain=DO_MAP) == [] and p == snap
    q = _today()
    q["do_today"] = ["haz un viaje corto"]
    q["headline_domains"] = ["Viajes"]
    LR.today(q, TD.compose(_today(), "en"), "es", do_by_domain=DO_MAP)
    assert q["do_today"] == ["haz un viaje corto"] and q["headline_domains"] == ["Viajes"]


def test_today_garbage_never_raises():
    assert LR.today(None, None) == [] and LR.today({}, {}) == [] and LR.today({"signals": [None]}, {"move": "x"}) is not None


# ---- month
def test_month_drops_actions_whose_deadline_has_passed():
    p = {"priority_actions": [
        {"action": "Cap your exposure on any speculative bet before October 8 — set a stop-loss.", "domain": "Risk & speculation"},
        {"action": "Delay any long trip until after October 18.", "domain": "Travel & foreign"},
        {"action": "Lock in a payout between October 14 and 23.", "domain": "Money & wealth"}]}
    LR.month(p, {"x": 1}, date(2026, 10, 11))
    assert [a["domain"] for a in p["priority_actions"]] == ["Travel & foreign", "Money & wealth"]


def test_month_breaks_names_the_caution_weeks_own_risk():
    p = {"month": "October 2026", "period_start": "2026-09-26", "period_end": "2026-10-26",
         "active_domains": [
             {"key": "money", "label": "Money & wealth", "score": 7, "window": "2026-10-14 – 2026-10-23", "polarity": "opportunity"},
             {"key": "work", "label": "Work & reputation", "score": 6, "window": "2026-10-12 – 2026-10-24", "polarity": "opportunity"},
             {"key": "travel", "label": "Travel & foreign", "score": 5, "window": "2026-10-09 – 2026-10-18", "caution": True, "polarity": "opportunity"},
             {"key": "speculation", "label": "Risk & speculation", "score": 8, "window": "2026-10-11 – 2026-10-20", "caution": True, "polarity": "risk"}],
         "caution_week": "Week of October 11 — a speculative bet or creative risk can backfire fast.",
         "best_week": "Week of October 26 — pitch.", "priority_actions": []}
    d = MD.compose(p, "en", today=date(2026, 10, 11))
    assert d["breaks"].startswith("It breaks if you commit to speculative bets")


# ---- year
def _year():
    return {"period_end": "2026-11-26", "theme": "A year of expansion — opportunities open.",
            "year_theme": "Guard your speculative bets.", "year_summary": "Your money is the strong axis.",
            "active": "Growth and teaching are the year's switched-on forces — expand.",
            "arcs": [{"key": "career", "name": "Career", "trend": "rising", "when": "peaks Oct 2026"},
                     {"key": "wealth", "name": "Wealth", "trend": "pressure", "when": "peaks Nov 2026"}],
            "events": [{"date_label": "Oct 2026", "polarity": 1, "text": "A visible step up at work — take the high-stakes role."},
                       {"date_label": "Nov 2026", "polarity": -1, "text": "Money comes under pressure."}],
            "build_this_year": ["Your savings — guard it"],
            "protect_this_year": ["Your reputation and your business standing — not the year to gamble visibility"],
            "release_this_year": ["Any high-risk venture — the odds are poor"]}


def test_year_theme_and_summary_follow_the_decision_and_the_expand_line_goes():
    p = _year()
    d = YD.compose(p, "en", today=date(2026, 10, 11))
    LR.year(p, d, "en")
    assert p["theme"] == p["year_theme"] == d["prediction"]
    assert "strong axis" not in p["year_summary"] and d["holds"] in p["year_summary"]
    assert p["active"] == ""
    assert "expand" not in d["why"].lower()


def test_year_move_does_not_tell_you_to_gamble_visibility_while_the_plan_says_protect_it():
    d = YD.compose(_year(), "en", today=date(2026, 10, 11))
    assert "high-stakes" not in d["move"] and d["move"].startswith("Before ")
