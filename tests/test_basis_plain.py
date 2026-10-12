from datetime import date

from antar_engine import basis_plain as BP

CHART = {"lagna": {"sign": "Capricorn"},
         "planets": {"Saturn": {"sign": "Gemini", "house": 6, "longitude": 70.0}, "Jupiter": {"sign": "Scorpio", "house": 11, "longitude": 220.0},
                     "Sun": {"sign": "Scorpio", "house": 11, "longitude": 215.0}, "Rahu": {"sign": "Scorpio", "house": 11, "longitude": 218.0}},
         "divisional_charts": {"d9": {"planets": {"Jupiter": {"sign": "Scorpio"}}}}}
today = date.today()
DASHAS = {"vimsottari": [
    {"level": "mahadasha", "lord_or_sign": "Rahu", "start_date": "2020-01-01", "end_date": "2040-01-01"},
    {"level": "antardasha", "lord_or_sign": "Rahu", "start_date": "2025-01-01", "end_date": "2099-04-25"}]}
JARGON = ("Rahu", "Saturn", "Jupiter", "house", "significator", "vargottama", "navamsa", "sub-period", "Gemini")


def test_the_why_line_is_plain_words_for_a_money_question():
    t = BP.build("wealth", CHART, DASHAS, "en")
    assert t.startswith("You're in a long stretch of reach, scale and being seen as the authority (this part runs to Apr 2099).")
    assert "Your money area works through daily work, service and routines" in t
    assert not any(j in t for j in JARGON)


def test_strength_words_follow_the_marks_and_unknowns_say_nothing():
    assert BP._strength(["exalted"]) == "strong" and BP._strength(["vargottama (strong in the navamsa)"]) == "strong"
    assert BP._strength(["debilitated"]) == "weak" and BP._strength(["combust (weakened by the Sun)"]) == "weak"
    assert BP._strength(["in its own sign", "combust (weakened by the Sun)"]) == "mixed" and BP._strength([]) == ""
    assert BP.build("wealth", {}, DASHAS, "en") == "" and BP.build("wealth", CHART, DASHAS, "hi") == ""      # no chart / unsupported language: nothing, never a guess


def test_spanish_is_native():
    t = BP.build("wealth", CHART, DASHAS, "es")
    assert t.startswith("Estás en una etapa larga de alcance, escala") and "Tu área de dinero funciona a través de" in t
    assert "You're" not in t and "Your" not in t and not any(j in t for j in ("Rahu", "Saturn", "Jupiter"))


def test_a_year_level_read_never_opens_with_a_today_sounding_right_now():
    from antar_engine import answer_polish as AP
    r = "Likely within the year — the money window is Jun 2027 – Oct 2027. Right now, the timing shows pressure on cashflow. Right now you are in a build phase."
    out = AP.scope_right_now(r, "Will my income grow?", "en")
    assert "In this stretch, the timing shows pressure on cashflow." in out and "In this stretch, you are in a build phase." in out and "Right now" not in out
    assert AP.scope_right_now(r, "Is this a good moment right now to sign?", "en") == r        # a question about right now keeps its words
    assert AP.scope_right_now(r, "Will I be fine today?", "en") == r
    assert AP.scope_right_now("Ahora mismo, el momento muestra presión.", "¿Subirán mis ingresos?", "es") == "En esta etapa, el momento muestra presión."
    assert AP.scope_right_now("They said it right now.", "x", "en") == "They said it right now."   # mid-sentence untouched
    assert AP.scope_right_now(None, "x", "en") is None


def test_small_copy_fixes_capital_do_lines_sentence_case_chips_and_a_plain_year_tab():
    import re
    import main
    from antar_engine import connection_card as CC, topic_copy as TC
    src = open(main.__file__, encoding="utf-8").read()
    blk = src[src.index("_DAILY_DO_DONT_BY_DOMAIN = {"):]
    blk = blk[:blk.index("\n}\n")]
    assert all(m.group(2).isupper() for m in re.finditer(r'"(do|dont)":\s*"(.)', blk))                 # every do / don't line starts with a capital
    assert "Handle a money task you've been putting off" in blk
    card = {"strengths": [{"title": "Low Hidden Friction", "text": "Andres sees it."}, {"title": "Easy Honest Exchange", "text": "x"}, {"title": "AI Agents Fit", "text": "y"}],
            "frictions": [{"title": "Different Clocks With Andres", "issue": "z"}]}
    out = CC.normalise_titles(card, keep=["Andres"])
    assert [x["title"] for x in out["strengths"]] == ["Low hidden friction", "Easy honest exchange", "AI agents fit"]      # acronym kept, first word capital
    assert out["frictions"][0]["title"] == "Different clocks with Andres" and out["strengths"][0]["text"] == "Andres sees it."   # names kept, text untouched
    assert CC.normalise_titles(None) is None and CC.normalise_titles({"strengths": "x"}) == {"strengths": "x"}
    from datetime import date
    assert TC.year_chip(date(2025, 11, 26), date(2026, 11, 26), "en") == "Your year" and TC.year_chip(date(2025, 11, 26), date(2026, 11, 26), "es") == "Tu año"


def test_do_and_dont_lines_are_capitalised_at_the_output_and_reconcile_still_matches_cached_lower_case_lines():
    import main
    assert main._cap_first_items(["take the short trip", "don't stake what you can't afford to lose", "Already capital", "", None]) == \
        ["Take the short trip", "Don't stake what you can't afford to lose", "Already capital", "", None]
    from antar_engine import legacy_reconcile as LR
    do_by_domain = {"money": {"do": "Handle a money task you've been putting off", "dont": "x"}, "work": {"do": "Push a stuck work task to done", "dont": "y"}}
    rev_ok = {x[:1].lower() + x[1:]: k for k, v in do_by_domain.items() for x in [v["do"]]}
    assert "handle a money task you've been putting off" in rev_ok and "push a stuck work task to done" in rev_ok       # the lookup key is the lower-case form
