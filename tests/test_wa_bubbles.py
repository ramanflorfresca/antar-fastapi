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
    assert build_basis("career", chart, dashas, "es") == ""          # no wrong-language text
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
        "Moon": {"sign": "Pisces", "house": 3, "longitude": 340.0}}},
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
    assert "7th house sits in your 3rd house" in love and "first move" in love
    assert chart_move("career", chart, dashas, "es") == ""          # English only
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
