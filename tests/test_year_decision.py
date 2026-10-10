"""[year-decision 2026-10-10] This Year's one coherent decision block."""
from datetime import date

from antar_engine.year_decision import compose

TODAY = date(2026, 10, 10)
P = {
    "period_end": "2026-11-26",
    "arcs": [{"key": "career", "name": "Career", "trend": "rising", "when": "peaks Oct 2026"},
             {"key": "business", "name": "Business", "trend": "steady", "when": "no clear signal this year"},
             {"key": "wealth", "name": "Wealth", "trend": "pressure", "when": "peaks Nov 2026"}],
    "active_domains": [{"key": "speculation", "label": "Risk & speculation", "convergence": True, "window": "2026-11-01 – 2026-11-13"}],
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
    assert compose(P, "pt", TODAY) is None and compose(P, "hi", TODAY) is None and compose({}, "en", TODAY) is None


# a Spanish annual plan as the live API ships it: Spanish lists, English arc names / `when` / `active`
PES = dict(P, build_this_year=["Tus ahorros \u2014 guarda m\u00e1s de lo que gastes", "Relaciones que te apoyen de verdad"],
           protect_this_year=["Cualquier proyecto creativo o especulativo \u2014 no apuestes grande"],
           release_this_year=["Gastos innecesarios \u2014 compra menos, ahorra m\u00e1s"],
           events=[{"date_label": "oct 2026", "polarity": 1, "text": "Un paso visible en el trabajo \u2014 toma el rol de alto riesgo."},
                   {"date_label": "nov 2026", "polarity": -1, "text": "El dinero est\u00e1 bajo presi\u00f3n."}])
_EN = (" the ", " your ", " you ", " year ", " holds ", " breaks ", " rising ", " pressure ", " and ", " left ")


def test_spanish_year_block_is_native_spanish():
    d = compose(PES, "es", TODAY, "Est\u00e1s en el periodo Rahu\u2013Rahu (el subperiodo termina el 25 de abril de 2029)")
    assert d["prediction"] == ("Este a\u00f1o (quedan 6 semanas, hasta el 26 nov): la carrera va en ascenso, con el pico en oct 2026; "
                               "el dinero est\u00e1 bajo presi\u00f3n, con el pico en nov 2026.")
    assert d["why"] == ("Est\u00e1s en el periodo Rahu\u2013Rahu (el subperiodo termina el 25 de abril de 2029). "
                        "Dos sistemas de tiempos coinciden en la especulaci\u00f3n (del 1 al 13 de noviembre).")
    assert d["holds"] == "Se sostiene si construyes sobre tus ahorros y relaciones que te apoyen de verdad."
    assert d["breaks"] == "Se rompe si cedes a gastos innecesarios \u2014 nov 2026 es donde cae la presi\u00f3n."
    assert d["move"] == "oct 2026: un paso visible en el trabajo \u2014 toma el rol de alto riesgo."
    for k in ("prediction", "why", "holds", "breaks"):
        assert not any(w in f" {d[k].lower()} " for w in _EN), (k, d[k])


def test_spanish_year_block_drops_english_leftovers_instead_of_showing_them():
    q = dict(PES, build_this_year=["Your savings and the money you keep \u2014 guard what you've made"],
             release_this_year=["Any high-risk venture you've been considering \u2014 the odds are not in your favour"],
             protect_this_year=["Any speculative bet \u2014 November brings risk"],
             events=[{"date_label": "oct 2026", "polarity": 1, "text": "A visible step up at work \u2014 take the high-stakes role."}])
    d = compose(q, "es", TODAY)
    assert d["holds"] == "Se sostiene si pones tu esfuerzo donde el a\u00f1o va en ascenso."
    assert d["breaks"] == "Se rompe si te excedes donde el a\u00f1o est\u00e1 bajo presi\u00f3n."
    assert d["move"] == ""            # English event text + no usable Spanish protect line: nothing, never English


def test_spanish_year_uses_spanish_months_and_falls_back_to_protect_when_the_event_text_is_english():
    q = dict(PES, events=[{"date_label": "Oct 2026", "polarity": 1, "text": "A visible step up at work \u2014 take the role."},
                          {"date_label": "Nov 2026", "polarity": -1, "text": "Money comes under pressure."}])
    d = compose(q, "es", TODAY)
    assert d["breaks"] == "Se rompe si cedes a gastos innecesarios \u2014 nov 2026 es donde cae la presi\u00f3n."
    assert d["move"] == "Antes del 26 nov: protege cualquier proyecto creativo o especulativo."


def test_merge_structure_takes_engine_fields_from_the_canonical_plan_and_keeps_spanish_prose():
    from antar_engine.year_decision import merge_structure
    es = {"arcs": [{"key": "career", "name": "Career", "trend": "steady", "when": "no clear signal this year"}], "events": [],
          "build_this_year": ["Tus ahorros"], "period_end": "2026-11-26"}
    m = merge_structure(es, P)
    assert m["arcs"] == P["arcs"] and m["events"] == P["events"] and m["build_this_year"] == ["Tus ahorros"]
    assert es["events"] == []         # the payload that is sent is untouched
