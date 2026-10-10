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
    assert compose(P, "pt", TODAY) is None and compose(P, "hi", TODAY) is None and compose({}, "en", TODAY) is None


# a Spanish payload as the live API ships it: Spanish prose, English domain labels, a legacy week sentence
PES = dict(P, overview="Cuida los gastos inesperados: pueden aparecer sin aviso.",
           best_week="Semana del 26 de octubre \u2014 tu energ\u00eda de comunicaci\u00f3n se une a tu empuje",
           caution_week="Semana del 10 de octubre \u2014 evita decisiones de autoridad.",
           priority_actions=[
               {"action": "Limita tu exposici\u00f3n a cualquier apuesta especulativa antes del 8 de octubre.", "domain": "Risk & speculation"},
               {"action": "Pospon cualquier viaje largo hasta despu\u00e9s del 18 de octubre.", "domain": "Travel & foreign"},
               {"action": "Avanza en una decisi\u00f3n de ahorro o asegura un cobro entre el 14 y el 23 de octubre.", "domain": "Money & wealth"},
               {"action": "Pon tu nombre en un trabajo visible la semana del 19 de octubre.", "domain": "Work & reputation"}])
PES.pop("range")
PES["period_start"], PES["period_end"] = "2026-09-26", "2026-10-26"
_EN_LEAK = (" the ", " your ", " you ", " favours ", " holds ", " breaks ", " strong ", " strain ", "week of", " and ")


def test_spanish_month_block_is_native_spanish():
    d = compose(PES, "es", TODAY, "Est\u00e1s en el periodo Rahu\u2013Rahu (el subperiodo termina el 25 de abril de 2029)")
    assert d["prediction"] == ("Este mes (26 sep \u2013 26 oct) favorece el dinero y el trabajo. Ten cautela con los viajes. "
                               "El tramo m\u00e1s fuerte es la semana del 26 de octubre.")
    assert d["why"] == ("Marte y Mercurio est\u00e1n fuertes este mes; Sol, Rahu y Venus est\u00e1n bajo tensi\u00f3n. "
                        "Est\u00e1s en el periodo Rahu\u2013Rahu (el subperiodo termina el 25 de abril de 2029).")
    assert d["holds"] == ("Se sostiene si programas la decisi\u00f3n de ahorro o cobro del 14 al 23 de octubre y el trabajo visible "
                          "del 12 al 24 de octubre; la mejor semana en conjunto es la semana del 26 de octubre.")
    assert d["breaks"] == ("Se rompe si te comprometes con viajes largos durante la semana del 10 de octubre, "
                           "o dejas que el gasto se adelante a los ingresos.")
    assert d["move"].startswith("Avanza en una decisi\u00f3n de ahorro")
    for k in ("prediction", "why", "holds", "breaks"):
        assert not any(w in f" {d[k].lower()} " for w in _EN_LEAK), (k, d[k])


def test_spanish_stale_action_is_skipped_by_spanish_dates():
    q = dict(PES, priority_actions=[
        {"action": "Limita tu exposici\u00f3n antes del 8 de octubre.", "domain": "Money & wealth"},
        {"action": "Pon tu nombre en un trabajo visible la semana del 19 de octubre.", "domain": "Work & reputation"}])
    assert compose(q, "es", TODAY)["move"].startswith("Pon tu nombre en un trabajo visible")


def test_get_route_shapes_are_handled():
    q = dict(P, best_week="Week of October 26 \u2014 your pitch sharpens", caution_week="Week of October 10 \u2014 a bet can backfire")
    q.pop("range"); q["period_start"] = "2026-09-26"; q["period_end"] = "2026-10-26"
    d = compose(q, "en", TODAY)
    assert d["prediction"].startswith("This month (Sep 26 \u2013 Oct 26) favours")
    assert "The strongest stretch is week of October 26." in d["prediction"]
    assert "during week of October 10" in d["breaks"]
