"""[wa-bubbles / ask-direct 2026-10-10] WhatsApp answers arrive as short bubbles, verdict first;
a dasha question gets the named, dated period (not a chapter essay)."""
from datetime import date

from antar_engine import messaging as m

TEXT = ("*Raman, this chapter runs — nearly two more decades of building.*\n\n"
        "The period favours reach and recognition: your reputation grows, your network widens. "
        "The friction is real too — cashflow stays uneven. Caution matters more than ever.\n\n"
        "→ Review the loan terms.\n\n"
        "1  Q one?\n2  Q two?\n_…or just type your own question._")


def test_verdict_is_its_own_plain_bubble_and_followups_split_off():
    bubbles, fu = m.split_ask_bubbles(TEXT)
    assert bubbles[0] == "Raman, this chapter runs — nearly two more decades of building."
    assert all(len(b) <= 190 for b in bubbles if not b.startswith("→"))
    assert bubbles[-1] == "→ Review the loan terms."
    assert fu.startswith("1  Q one?") and "own question" in fu


def test_bubbles_never_cut_a_sentence_or_lose_text():
    bubbles, fu = m.split_ask_bubbles(TEXT)
    joined = " ".join(bubbles)
    for frag in ("reach and recognition", "cashflow stays uneven", "Caution matters more than ever."):
        assert frag in joined


def test_canned_fallback_move_is_dropped_from_whatsapp():
    p = {"mode": "explore", "read": "Hold until spring. The stronger move opens in March.",
         "next": "Block one hour this week for the task that moves your work forward most, and do it first."}
    text, _ = m.format_ask_whatsapp_v2(p, "en", asked="x")
    assert "→" not in text
    p["next"] = "Update your portfolio this month."
    assert "→ Update your portfolio" in m.format_ask_whatsapp_v2(p, "en", asked="x")[0]


def _main():
    import main
    return main


def test_dasha_question_names_period_dates_and_antardasha_end():
    main = _main()
    today = date.today()
    y = today.year

    def row(lvl, planet, s, e):
        return {"level": lvl, "planet_or_sign": planet, "lord_or_sign": planet,
                "start_date": s, "end_date": e}
    dashas = {"vimsottari": [
        row("mahadasha", "Rahu", f"{y-1}-08-01", f"{y+17}-08-01"),
        row("antardasha", "Rahu", f"{y-1}-08-01", f"{y+2}-04-25"),
        row("antardasha", "Jupiter", f"{y+2}-04-25", f"{y+5}-09-10"),
    ]}
    chart = {"lagna": {"sign": "Capricorn"},
             "planets": {"Rahu": {"sign": "Scorpio", "house": 11, "nakshatra": "Jyeshtha"}}}
    out = main._ask_period_payload(chart, dashas)["read"]
    assert "Rahu mahadasha" in out and "Rahu-Rahu antardasha" in out
    assert f"April 25, {y+2}" in out and "from today" in out
    assert "11th house" in out and "Jyeshtha" in out
    assert "Rahu-Jupiter" in out


def test_chara_dasha_names_sign_house_and_dates():
    main = _main()
    y = date.today().year
    dashas = {"jaimini": [
        {"planet_or_sign": "Taurus", "start_date": f"{y-1}-11-26", "end_date": f"{y+5}-11-26"},
        {"planet_or_sign": "Aries", "start_date": f"{y+5}-11-26", "end_date": f"{y+15}-11-26"}]}
    chart = {"lagna": {"sign": "Capricorn"}, "planets": {"Ketu": {"house": 5}}}
    out = main._ask_chara_payload(chart, dashas)["read"]
    assert "Taurus chara dasha" in out and "5th house" in out and "Ketu" in out and "Aries from" in out


def test_dasha_question_detection():
    main = _main()
    assert main._is_dasha_q("what's the outcome of this dasha?")
    assert main._wants_chara("tell me specifics for my Taurus dasha")
    assert not main._is_dasha_q("how is my money this month")


def test_basis_names_real_chart_facts():
    from antar_engine.ask_basis import build_basis
    from datetime import date
    y = date.today().year
    dashas = {"vimsottari": [
        {"level": "mahadasha", "planet_or_sign": "Rahu", "start_date": f"{y-1}-01-01", "end_date": f"{y+9}-01-01"},
        {"level": "antardasha", "planet_or_sign": "Saturn", "start_date": f"{y-1}-01-01", "end_date": f"{y+2}-04-25"}]}
    chart = {"lagna": {"sign": "Capricorn"}, "planets": {
        "Sun": {"sign": "Scorpio", "house": 11, "longitude": 220.0},
        "Venus": {"sign": "Scorpio", "house": 11, "longitude": 225.0},
        "Saturn": {"sign": "Gemini", "house": 6, "longitude": 70.0}}}
    b = build_basis("career", chart, dashas)
    assert "Rahu–Saturn" in b and f"Apr 25, {y+2}" in b
    assert "10th house (career) is ruled by Venus" in b and "11th house in Scorpio" in b and "combust" in b
    assert "Saturn, the main significator" in b or "Sun, the main significator" in b
    assert build_basis("career", chart, dashas, "pt") == ""          # no wrong-language text
    assert build_basis("career", {}, dashas) == ""                    # nothing true to say → nothing


def test_basis_rides_the_whatsapp_answer_as_its_own_bubble():
    p = {"mode": "explore", "read": "Hold until spring. The stronger move opens in March.",
         "basis": "You're running Rahu–Saturn (sub-period ends Apr 25, 2029)."}
    text, _ = m.format_ask_whatsapp_v2(p, "en", asked="x")
    bubbles, _fu = m.split_ask_bubbles(text)
    assert "📍 You're running Rahu–Saturn (sub-period ends Apr 25, 2029)." in bubbles


def _chart():
    return ({"lagna": {"sign": "Capricorn"}, "planets": {
        "Sun": {"sign": "Scorpio", "house": 11, "longitude": 220.0},
        "Venus": {"sign": "Scorpio", "house": 11, "longitude": 225.0},
        "Moon": {"sign": "Pisces", "house": 3, "longitude": 340.0},
        "Mercury": {"sign": "Libra", "house": 10, "longitude": 215.0},
        "Mars": {"sign": "Libra", "house": 10, "longitude": 218.0}}},
        {"vimsottari": [
            {"level": "mahadasha", "planet_or_sign": "Rahu", "start_date": "2000-01-01", "end_date": "2100-01-01"},
            {"level": "antardasha", "planet_or_sign": "Rahu", "start_date": "2000-01-01", "end_date": "2100-04-25"}]})


def test_chart_move_follows_the_topic_and_the_chart():
    from antar_engine.ask_basis import chart_move
    chart, dashas = _chart()
    career = chart_move("career", chart, dashas)
    assert "10th house is weakened" in career or "ruler of your 10th house is weakened" in career
    assert "your network and gains" in career and "Apr 25, 2100" in career
    love = chart_move("love", chart, dashas)
    assert "your own initiative and communication" in love and "first move" in love and "7th" not in love
    assert chart_move("career", chart, dashas, "pt") == ""          # English only
    assert chart_move("legal", chart, dashas) == ""                  # no template → canned fallback stays


def test_polish_uses_chart_move_before_canned_line_and_drops_invented_health_move():
    from antar_engine.answer_polish import polish_answer
    chart, dashas = _chart()
    p = polish_answer({"read": "Likely. The window is Oct 2026.", "next": None}, "en", "Will I get promoted?",
                      concern="career", chart_data=chart, dashas=dashas)
    assert "Block one hour" not in p["next"] and "network and gains" in p["next"]
    p = polish_answer({"read": "Likely.", "next": "Book a medical consultation this month."}, "en",
                      "Will I have children?", concern="children", chart_data=chart, dashas=dashas)
    assert "medical" not in (p["next"] or "").lower()


def test_polish_keeps_the_readers_relationship_and_drops_dangling_moves():
    from antar_engine.answer_polish import polish_answer
    p = polish_answer({"read": "You're not currently in a relationship — so this reads as a question about your past marriage. "
                               "The bond has real promise. Strain shows up as distance.",
                       "next": "Then build or improve it until it's perfect."},
                      "en", "Is my current relationship going to last?", concern="love")
    assert "not currently in a relationship" not in p["read"] and "promise" in p["read"]
    assert not p["next"].lower().startswith("then")
    q = polish_answer({"read": "You're not in a relationship. Closeness takes effort. Keep it slow.", "next": "Go."},
                      "en", "Will I find someone?", concern="love")
    assert "not in a relationship" in q["read"]       # not presupposed → left alone



def test_conditions_say_what_makes_it_true_and_what_breaks_it():
    from antar_engine.ask_basis import conditions
    chart, dashas = _chart()
    c = conditions("career", chart, dashas)
    assert c.startswith("It holds if you build it through your network and gains")
    assert "weakened" in c and "It breaks if" in c and "recognition lags effort" in c
    h = conditions("health", chart, dashas)
    assert "recognition" not in h and "Risk stays small" in h
    assert "recognition" not in conditions("property", chart, dashas)
    assert conditions("career", chart, dashas, "pt") == "" and conditions("legal", chart, dashas) == ""


def test_polish_builds_prediction_holds_breaks_and_drops_invented_or_unasked_text():
    from antar_engine.answer_polish import polish_answer
    chart, dashas = _chart()
    p = polish_answer({
        "read": "Yes — reconnection window is open now, through Jan 2027. The timing shows your ex's side of the timing "
                "is strong. Your marriage ended, so this chapter has closed. The window favours a direct first move.",
        "next": "Send one short message this week."}, "en", "Will my ex come back?", concern="reconciliation",
        chart_data=chart, dashas=dashas)
    r = p["read"]
    assert r.startswith("Yes — reconnection window") and "ex's side" not in r and "chapter has closed" not in r
    assert "It holds if" in r and "It breaks if" in r
    h = polish_answer({"read": "Likely — health window Oct 2026 – Jan 2027. Watch sleep.",
                       "next": "Book a check-up. Traditionally, Ayurveda associates this period with brahmi — supportive practice."},
                      "en", "Will I have a health scare?", concern="health", chart_data=chart, dashas=dashas)
    assert "brahmi" not in h["next"].lower() and "check-up" in h["next"]
    h2 = polish_answer({"read": "Likely — Oct 2026.", "next": "Take brahmi daily."}, "en",
                       "Any herbs for stress?", concern="health", chart_data=chart, dashas=dashas)
    assert "brahmi" in h2["next"]


def test_health_and_speculation_wording_is_topic_specific():
    from antar_engine.ask_basis import conditions, chart_move
    chart, dashas = _chart()
    chart["planets"]["Jupiter"] = {"sign": "Taurus", "house": 5, "longitude": 40.0}
    h = conditions("health", chart, dashas)
    assert h.startswith("Risk stays small if you act early and protect sleep and recovery time.")
    assert "recovery runs slower" in h and "public work" not in h and "It breaks if strain" in h
    assert "results lag effort" not in chart_move("health", chart, dashas)
    assert "sleep and meal times" in chart_move("health", chart, dashas)
    sp = conditions("speculation", chart, dashas)
    assert "afford to lose" in sp and "It breaks if position size" in sp
    assert "afford to lose" in chart_move("speculation", chart, dashas)


def test_dasha_answers_carry_a_decision_not_just_facts():
    main = _main()
    y = date.today().year
    rows = lambda l, p, s, e: {"level": l, "planet_or_sign": p, "lord_or_sign": p, "start_date": s, "end_date": e}
    dashas = {"vimsottari": [
        rows("mahadasha", "Rahu", f"{y-1}-08-01", f"{y+17}-08-01"),
        rows("antardasha", "Rahu", f"{y-1}-08-01", f"{y+2}-04-25"),
        rows("antardasha", "Jupiter", f"{y+2}-04-25", f"{y+5}-09-10")]}
    chart = {"lagna": {"sign": "Capricorn"}, "planets": {"Rahu": {"sign": "Scorpio", "house": 11}}}
    p = main._ask_period_payload(chart, dashas)
    assert "Use this period for reach, networks" in p["read"] and "wasted by chasing every opportunity" in p["read"]
    assert p["next"].startswith("Pick the one scalable bet") and f"April 25, {y+2}" in p["next"]
    d2 = {"jaimini": [
        {"planet_or_sign": "Taurus", "start_date": f"{y-1}-11-26", "end_date": f"{y+5}-11-26"},
        {"planet_or_sign": "Aries", "start_date": f"{y+5}-11-26", "end_date": f"{y+15}-11-26"}]}
    c = main._ask_chara_payload({"lagna": {"sign": "Capricorn"}, "planets": {}}, d2)
    assert "the focus turns to" in c["read"] and "Decide what you want to have built by" in c["next"] and "these years are for that" in c["next"]


def test_filler_openers_and_count_claims_are_removed_but_substance_stays():
    from antar_engine.answer_polish import polish_answer
    chart, dashas = _chart()
    p = polish_answer({"read": "Raman, this concern is real — and worth acting on, not worrying over. "
                               "Five separate patterns flag it as a health-sensitive window, tending toward skin and sleep. "
                               "Watch your routine.", "next": "Fix sleep times."},
                      "en", "any health issues this year", concern="health", chart_data=chart, dashas=dashas)
    assert "concern is real" not in p["read"] and "Five separate" not in p["read"]
    assert "several signals flag it" in p["read"] and "skin and sleep" in p["read"]


def test_a_short_question_with_its_own_topic_is_not_a_chapter_followup():
    import main
    prev = "What is the outcome of my current dasha?"
    assert not main._chapter_followup(prev, "Will my ex come back?", own_topic=True)
    assert not main._chapter_followup(prev, "Is it a good time to ask for a raise?", own_topic=True)
    assert main._chapter_followup(prev, "what happens in it?", own_topic=False)          # real follow-up
    assert main._chapter_followup(prev, "tell me more about the next five years", own_topic=True)
    assert main._chapter_followup(prev, "and then?", own_topic=False)
    assert not main._chapter_followup("Will my ex come back?", "what happens in it?", own_topic=False)  # prev not a chapter q


def test_reconciliation_gets_a_topic_specific_fallback_move_and_generic_ones_are_dropped():
    from antar_engine.ask_basis import chart_move
    from antar_engine.answer_polish import polish_answer
    chart, dashas = _chart()
    mv = chart_move("reconciliation", chart, dashas)
    assert "first contact" in mv and "let them choose the next step" in mv
    p = polish_answer({"read": "Yes — reconnection window is open now, through Jan 2027. Both of you are open to talking. Keep it short.",
                       "next": "This week, write down what a good partnership looks like for you now."},
                      "en", "Will my ex come back?", concern="reconciliation", chart_data=chart, dashas=dashas)
    assert "good partnership looks like" not in p["next"] and "first contact" in p["next"]
    assert "Both of you are open" not in p["read"]


_ES_LEAK = (" the ", " your ", " you ", " it holds ", " it breaks ", " ruler ", " sub-period", " house ", " weakened", " and ")


def test_spanish_basis_conditions_and_moves_are_native_spanish():
    from antar_engine.ask_basis import build_basis, conditions, chart_move, running_period
    chart, dashas = _chart()
    assert running_period(dashas, "es") == ("Estás en el periodo Rahu–Rahu "
                                            "(el subperiodo termina el 25 de abril de 2100)")
    b = build_basis("career", chart, dashas, "es")
    assert b.startswith("Estás en el periodo Rahu–Rahu (el subperiodo termina el 25 de abril de 2100).")
    assert ("Tu casa 10 (carrera) está regida por Venus, que está en tu casa 11 en Escorpio, "
            "combusto (debilitado por el Sol).") in b
    assert "el principal significador aquí" in b
    c = conditions("career", chart, dashas, "es")
    assert c.startswith("Se sostiene si lo construyes a través de tu red de contactos y tus ganancias y dejas que los resultados se acumulen")
    assert "el regente de tu casa 10 está debilitado" in c and c.endswith("o esperas un título en lugar de entregar un resultado visible.")
    h = conditions("health", chart, dashas, "es")
    assert h.startswith("El riesgo se mantiene bajo si actúas pronto") and h.endswith("sin dejar tiempo de recuperación.")
    assert "primer contacto breve y directo" in chart_move("reconciliation", chart, dashas, "es")
    assert chart_move("health", chart, dashas, "es").startswith("Ordena primero los horarios de sueño y comida")
    assert "Fija lo máximo que puedes permitirte perder" in chart_move("speculation", chart, dashas, "es")
    for txt in (b, c, h, chart_move("career", chart, dashas, "es"), chart_move("love", chart, dashas, "es")):
        assert not any(w in f" {txt.lower()} " for w in _ES_LEAK), txt
    assert build_basis("career", chart, dashas, "pt") == "" and conditions("career", chart, dashas, "pt") == ""


def test_spanish_polish_appends_spanish_conditions_after_a_spanish_read():
    from antar_engine.answer_polish import polish_answer
    chart, dashas = _chart()
    p = polish_answer({"read": "Sí — la ventana de reconexión está abierta hasta enero de 2027.", "next": None},
                      "es", "¿Volverá mi ex?", concern="reconciliation", chart_data=chart, dashas=dashas)
    assert p["read"].startswith("Sí — la ventana de reconexión") and "Se sostiene si" in p["read"] and "Se rompe si" in p["read"]
    assert "primer contacto breve y directo" in p["next"]


def test_chara_detection_understands_spanish_sign_names():
    main = _main()
    assert main._wants_chara("H\u00e1blame de mi dasha de Tauro") and main._wants_chara("mi dasha de Escorpio")
    assert not main._wants_chara("\u00bfCu\u00e1l es el resultado de mi dasha actual?")
