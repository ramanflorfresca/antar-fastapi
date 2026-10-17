"""[today-decision 2026-10-10] Today's one coherent decision block, composed from the daily payload."""
import pytest

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
    # the Moon-house area (fortune & travel) is only the THIRD lead (father); the prediction names work and network, so no spotlight sentence
    assert d["why"] == ("Until 1:10 PM the day runs against you; after that it is in your favour. "
                        "Your current chapter adds friction, so go steady.")
    # one voice: no star name, house number, planet or dasha chain in the user-facing why
    assert not any(w in d["why"] for w in ("Hasta", "Chitra", "house", "Rahu", "Moon", "9th"))
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
    assert d["why"].startswith("Hasta las 1:10 PM el d\u00eda va en tu contra; despu\u00e9s queda a tu favor.")
    assert "primer plano" not in d["why"] and "Tu etapa actual a\u00f1ade fricci\u00f3n" in d["why"]
    assert not any(w in d["why"] for w in ("Hasta ", "Chitra", "Rahu", "Luna", "casa 9")) or d["why"].startswith("Hasta las")
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
    assert "Some New Label" not in d["why"] and d["why"] == "Tu etapa actual a\u00f1ade fricci\u00f3n, as\u00ed que ve con calma."


def test_daily_signal_route_attaches_the_decision_block():
    import asyncio
    import main

    async def base(chart_id=None, request=None, language="en", date=None):
        return dict(P, date="2026-10-09")

    wrapped = main._attach_today_decision(base)
    out = asyncio.run(wrapped(chart_id="x", request={}, language="en"))
    assert out["decision"]["prediction"].startswith("Today favours work and reputation")
    es = asyncio.run(wrapped(chart_id="x", request={}, language="es"))
    assert es["decision"]["prediction"].startswith("Hoy favorece el trabajo y la reputaci\u00f3n")
    assert "decision" not in asyncio.run(wrapped(chart_id="x", request={}, language="pt"))
    assert "decision" not in asyncio.run(wrapped(chart_id="x", request={}, language="hinglish"))


def test_why_never_names_a_house_a_star_or_a_dasha_chain():
    """[plain-why 2026-10-17] Live: the sheet for another day said "Purva Ashadha ... It lights your 1st house ... Rahu\u2013Rahu\u2013Rahu".
    The user-facing why says the same facts in plain words, for every house and either language."""
    import re
    bad = re.compile(r"(?i)\b(\d+(st|nd|rd|th)|house|casa|rahu|ketu|saturn|mars|mercury|venus|jupiter|nakshatra|ashadha|chitra|"
                     r"dasha|periodo|per\u00edodo)\b")
    for lang in ("en", "es"):
        for h in range(1, 13):
            d = compose(dict(P, moon_house_from_lagna=h), lang)
            assert not bad.search(d["why"]), (lang, h, d["why"])
            if lang == "en":
                assert "Hasta" not in d["why"]
    # (every house, with a lead that matches it, still reads without jargon)
    for h, lit, lead_key in ((1, "self & vitality", "body"), (10, "career & visibility", "work"), (11, "gains & network", "network")):
        w = compose(dict(P, moon_house_from_lagna=h, lit_domain=lit, evidence={"chosen": [lead_key], "lead_dir": "positive"}))["why"]
        assert f"It puts {lit} in the spotlight." in w and not bad.search(w), (h, w)


def test_spotlight_only_when_it_is_an_area_the_prediction_leads_with():
    """[spotlight 2026-10-17] Live: the prediction led with visibility and reputation while the why said 'rest & retreat in the spotlight'."""
    mismatch = compose(dict(P, moon_house_from_lagna=12, lit_domain="rest & retreat",
                            evidence={"chosen": ["work", "network"], "lead_dir": "positive"}))
    assert "spotlight" not in mismatch["why"]
    match = compose(dict(P, moon_house_from_lagna=10, lit_domain="career & visibility",
                         evidence={"chosen": ["work", "network"], "lead_dir": "positive"}))
    assert "It puts career & visibility in the spotlight." in match["why"]


def test_pending_fast_phase_publishes_no_move():
    """The fast payload's do-item is a placeholder the full pass replaces; showing it made Home swap its move."""
    assert compose(dict(P, pending=True))["move"] == ""
    assert compose(dict(P, pending=False))["move"].startswith("After 1:10 PM")


# ---- [weekend + move-time 2026-10-11]
def _wk_payload(date_iso, day, item="Make the career move you've been sitting on — reach out to the decision-maker directly before noon."):
    return {"date": date_iso, "day": day, "evidence": {"chosen": ["work", "network"], "lead_dir": "positive"},
            "moon_sign": "Libra", "moon_house_from_lagna": 10, "lit_domain": "career & visibility",
            "hora": {"best_window": "12:17 PM – 1:05 PM"}, "rahu_kalam": "8:28 AM – 9:52 AM",
            "haz_hoy": [item], "dont_today": ["don't stake what you can't afford to lose"],
            "domains": [{"key": "work", "state": "caution", "name": {"en": "Work"}}],
            "day_energy": {"key": "light"}}


def test_move_that_already_names_a_time_gets_no_window_in_front_of_it():
    from antar_engine.today_decision import compose
    d = compose(_wk_payload("2026-10-12", "Monday"), "en")      # Monday
    assert d["move"].startswith("Make the career move") and "Between" not in d["move"] and d["move"].count("noon") == 1


def test_move_without_a_time_still_gets_the_window():
    from antar_engine.today_decision import compose
    d = compose(_wk_payload("2026-10-12", "Monday", "Make the career move you've been sitting on"), "en")
    assert d["move"].startswith("Between 12:17 PM and 1:05 PM, make the career move")


def test_sunday_says_visibility_not_workload_and_does_not_send_you_to_a_decision_maker():
    from antar_engine.today_decision import compose
    d = compose(_wk_payload("2026-10-11", "Sunday"), "en")
    assert "visibility and reputation" in d["prediction"] and "taking on too much at work" not in d["prediction"]
    assert "Monday" in d["move"] and "decision-maker" not in d["move"] and "before noon" not in d["move"]
    assert "send nothing until Monday" in d["holds"]


def test_weekday_keeps_the_work_wording_and_overreach_warning():
    from antar_engine.today_decision import compose
    d = compose(_wk_payload("2026-10-12", "Monday"), "en")
    assert "work and reputation" in d["prediction"] and "taking on too much at work" in d["prediction"]


def test_saturday_spanish_is_native_and_has_no_english():
    from antar_engine.today_decision import compose, _looks_english
    p = _wk_payload("2026-10-10", "sábado", "Contacta al tomador de decisiones antes del mediodía.")
    d = compose(p, "es")
    assert "visibilidad" in d["prediction"] and "lunes" in d["move"] and "lunes" in d["holds"]
    assert not _looks_english(d["move"]) and not _looks_english(d["holds"])


def test_sunday_spanish_call_the_key_contact_becomes_a_monday_draft():
    from antar_engine.today_decision import compose
    p = _wk_payload("2026-10-11", "domingo", "Llama o escribe al contacto clave antes del mediodía — hoy tu voz llega con más peso que de costumbre.")
    d = compose(p, "es")
    assert "lunes" in d["move"] and "mediodía" not in d["move"] and "Llama" not in d["move"]


# ── structured clock range for "add to calendar" ──
from antar_engine.today_decision import clock_range  # noqa: E402


@pytest.mark.parametrize("w,expected", [
    ("12:18 PM – 1:06 PM", ("12:18", "13:06")),
    ("12:17 PM - 1:05 PM", ("12:17", "13:05")),
    ("9:52 AM – 11:17 AM", ("09:52", "11:17")),
    ("11:30 – 12:15 PM", ("11:30", "12:15")),          # start inherits PM, flips to AM to stay before the end
    ("12:00 AM – 1:30 AM", ("00:00", "01:30")),
    ("8:28 AM to 9:52 AM", ("08:28", "09:52")),
    ("", None), (None, None), ("sunrise", None),
    ("13:00 PM – 14:00 PM", None),                      # not a 12-hour time
    ("5:00 PM – 4:00 PM", None),                        # backwards
])
def test_clock_range(w, expected):
    assert clock_range(w) == expected


def test_decision_window_carries_the_clock_range_only_when_readable():
    d = compose(P)
    assert d["window"]["best_start"] == "12:18" and d["window"]["best_end"] == "13:06"
    # no best window at all: the keys are simply absent, never null
    q = {**P, "hora": {}, "panchanga": {}, "abhijit": None}
    assert "best_start" not in compose(q)["window"]
    # a window the parser cannot read is left out, the prose is unchanged
    r = {**P, "hora": {"best_window": "around noon"}}
    out = compose(r)
    assert out["window"]["best"] == "around noon" and "best_start" not in out["window"]


def test_spotlight_compares_with_the_two_areas_the_prediction_names():
    """[spotlight 2026-10-17] Live Oct 19: the prediction named 'home and property, then income and your network' while a third lead
    (health) matched the Moon-house area, so 'self & vitality in the spotlight' still told a second story."""
    two = compose(dict(P, moon_house_from_lagna=1, lit_domain="self & vitality",
                       evidence={"chosen": ["home", "network", "body"], "lead_dir": "positive"}))
    assert "spotlight" not in two["why"]
    first = compose(dict(P, moon_house_from_lagna=1, lit_domain="self & vitality",
                         evidence={"chosen": ["work", "body", "network"], "lead_dir": "positive"}))
    assert "It puts self & vitality in the spotlight." in first["why"]
