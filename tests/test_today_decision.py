"""[today-decision 2026-10-10] Today's one coherent decision block, composed from the daily payload."""
from antar_engine.today_decision import compose

P = {
    "evidence": {"chosen": ["work", "network", "father"], "lead_dir": "positive"},
    "confidence": {"level": "low"}, "day_energy": {"key": "light"},
    "domains": [{"key": "body", "name": {"en": "Health"}, "state": "caution"},
                {"key": "work", "name": {"en": "Career"}, "state": "caution"},
                {"key": "mind", "name": {"en": "Mind"}, "state": "steady"}],
    "moon_sign": "Virgo", "moon_house_from_lagna": 9, "lit_domain": "fortune & travel",
    "moon_shift": {"changes_at": "1:10 PM", "from_nakshatra": "Hasta", "to_nakshatra": "Chitra",
                   "split": {"material": True, "direction": "improves", "at": "1:10 PM",
                             "before": {"quality_label": "Runs against you"}, "after": {"quality_label": "In your favour"}}},
    "signals": [{"key": "dasha", "value": "Rahu → Rahu → Rahu", "direction": "friction"}],
    "hora": {"best_window": "12:18 PM – 1:06 PM", "avoid_window": "9:52 AM – 11:17 AM"},
    "rahu_kalam": "9:52 AM – 11:17 AM",
    "haz_hoy": ["Audit one financial commitment that has been sitting unresolved."],
    "dont_today": ["don't stake what you can't afford to lose"],
}


def test_decision_has_prediction_why_holds_breaks_move():
    d = compose(P)
    assert d["prediction"].startswith("Today favours work and reputation, then income and your network.")
    assert "Health needs care." in d["prediction"] and "taking on too much at work" in d["prediction"]
    assert "lighter-touch day" in d["prediction"]
    assert "Hasta (runs against you) until 1:10 PM, then Chitra (in your favour)" in d["why"]
    assert "9th house (fortune & travel)" in d["why"] and "Rahu–Rahu–Rahu (friction)" in d["why"]
    assert d["holds"].startswith("It holds if you prepare before 1:10 PM and commit after it")
    assert "the sharpest single hour for an ask or a pitch is 12:18 PM \u2013 1:06 PM" in d["holds"]
    assert d["breaks"] == ("It breaks if you force a decision or a hard conversation between 9:52 AM and 11:17 AM, "
                           "or stake what you can't afford to lose.")
    assert d["move"].startswith("After 1:10 PM, audit one financial commitment")
    assert d["window"]["shift_at"] == "1:10 PM"


def test_worsening_shift_says_commit_before_it():
    q = dict(P, moon_shift=dict(P["moon_shift"], split=dict(P["moon_shift"]["split"], direction="worsens")))
    d = compose(q)
    assert d["holds"].startswith("It holds if you commit before 1:10 PM")
    assert d["move"].startswith("Before 1:10 PM,")


def test_negative_lead_is_a_hold_day_and_no_shift_uses_best_window():
    q = dict(P, evidence={"chosen": ["money"], "lead_dir": "negative"}, moon_shift={})
    d = compose(q)
    assert d["prediction"].startswith("Today is a hold day for money")
    assert d["holds"] == "It holds if the decision that matters goes between 12:18 PM and 1:06 PM."
    assert d["move"].startswith("Between 12:18 PM and 1:06 PM,")


def test_other_languages_and_empty_payloads_get_no_block():
    assert compose(P, "pt") is None and compose(P, "hi") is None
    assert compose({}) is None and compose({"evidence": {"chosen": []}}) is None


_ES_EN_WORDS = (" the ", " your ", " you ", " and ", " with ", " that ", " is ", " of ", "needs care", "holds", "breaks")


def test_spanish_block_is_native_spanish_with_no_english_leaks():
    q = dict(P, haz_hoy=["Revisa y ordena un compromiso financiero que lleva tiempo pendiente."],
             dont_today=["no apuestes lo que no puedas permitirte perder"],
             moon_shift=dict(P["moon_shift"], split=dict(P["moon_shift"]["split"],
                             before={"quality_label": "Runs against you"}, after={"quality_label": "In your favour"})))
    d = compose(q, "es")
    assert d["prediction"].startswith("Hoy favorece el trabajo y la reputaci\u00f3n, y luego los ingresos y tu red de contactos.")
    assert "La salud necesita cuidado." in d["prediction"] and "Cuida no asumir demasiado en el trabajo." in d["prediction"]
    assert d["why"].startswith("La Luna est\u00e1 en Virgo, en Hasta (va en tu contra) hasta las 1:10 PM, y luego en Chitra (a tu favor).")
    assert "Ilumina tu casa 9 (fortuna y viajes)." in d["why"] and "Rahu\u2013Rahu\u2013Rahu (fricci\u00f3n)" in d["why"]
    assert d["holds"].startswith("Se sostiene si preparas antes de las 1:10 PM y te comprometes despu\u00e9s")
    assert d["breaks"] == ("Se rompe si fuerzas una decisi\u00f3n o una conversaci\u00f3n dif\u00edcil entre 9:52 AM y 11:17 AM. "
                           "Y recuerda: no apuestes lo que no puedas permitirte perder.")
    assert d["move"] == "A partir de las 1:10 PM, revisa y ordena un compromiso financiero que lleva tiempo pendiente."
    for k in ("prediction", "why", "holds", "breaks", "move"):
        low = f" {d[k].lower()} "
        assert not any(w in low for w in _ES_EN_WORDS), (k, d[k])


def test_spanish_block_never_leaks_an_english_move_or_unknown_label():
    q = dict(P, haz_hoy=["Audit one financial commitment that has been sitting unresolved."], dont_today=["don't stake what you can't afford to lose"],
             moon_shift={"split": {"material": True, "direction": "improves", "at": "1:10 PM",
                                   "before": {"quality_label": "Some New Label"}, "after": {"quality_label": "In your favour"}},
                         "changes_at": "1:10 PM", "from_nakshatra": "Hasta", "to_nakshatra": "Chitra"})
    d = compose(q, "es")
    assert d["move"] == "" and "Audit" not in d["breaks"] and "stake" not in d["breaks"]
    assert "Some New Label" not in d["why"] and "La Luna est\u00e1 en Virgo, en Hasta." in d["why"]


def test_daily_signal_route_attaches_the_decision_block():
    import asyncio
    import main

    async def base(chart_id=None, request=None, language="en", date=None):
        return dict(P, date="2026-10-10")

    wrapped = main._attach_today_decision(base)
    out = asyncio.run(wrapped(chart_id="x", request={}, language="en"))
    assert out["decision"]["prediction"].startswith("Today favours work and reputation")
    es = asyncio.run(wrapped(chart_id="x", request={}, language="es"))
    assert es["decision"]["prediction"].startswith("Hoy favorece el trabajo y la reputaci\u00f3n")
    assert "decision" not in asyncio.run(wrapped(chart_id="x", request={}, language="pt"))
    assert "decision" not in asyncio.run(wrapped(chart_id="x", request={}, language="hinglish"))
