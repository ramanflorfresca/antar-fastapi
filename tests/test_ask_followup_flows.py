"""[followup-flows 2026-10-04] Next questions are chosen by intent lane, carry a
short lane title (no duplicated truncated question on tap), end with one bridge
to a neighbouring life area, and WhatsApp always offers 'Ask your own'."""
from antar_engine import ask_followups as af


def _lanes(out):
    return [f["lane"] for f in out]


def test_asked_lane_detection_all_languages():
    assert af.asked_lane("When does my career take off?") == "when"
    assert af.asked_lane("¿Cuándo despegará mi carrera?") == "when"
    assert af.asked_lane("Mera career kab take off karega?") == "when"
    assert af.asked_lane("How do I keep speculation small?") == "how"
    assert af.asked_lane("Why does work feel stuck?") == "why"
    assert af.asked_lane("How is my money looking right now?") == "now"


def test_asked_lane_goes_last_and_bridge_is_third():
    out = af.pick("money", "When does my money window open?", "en")
    assert "when" not in _lanes(out)[:2] and _lanes(out)[2] == "bridge"
    assert out[2]["title"] == "↔ Career"


def test_distress_leads_with_agency():
    out = af.pick("career", "I feel so stuck at work, what is going on?", "en")
    assert out[0]["lane"] == "how"


def test_dated_answer_does_not_lead_with_another_when():
    out = af.pick("love", "How is my love life?", "en", answered_when=True)
    assert out[0]["lane"] != "when"


def test_titles_fit_whatsapp_and_never_repeat_the_question():
    for lang in ("en", "es", "pt", "hinglish"):
        for bucket in af._Q["en"]:
            for f in af.pick(bucket, "x", lang):
                assert len(f["title"]) <= 24 and f["title"] != f["q"]
        t, iid, d = af.own_row(lang)
        assert iid == "own" and len(t) <= 24 and len(d) <= 72


def test_every_language_has_every_lane():
    for lang, table in af._Q.items():
        assert set(table) == set(af._Q["en"]), lang
        for b, lanes in table.items():
            assert set(lanes) == set(af._Q["en"][b]), (lang, b)


def test_day_bucket_stays_in_domain():
    out = af.pick("day", "How is my day today?", "en")
    assert "bridge" not in _lanes(out) and len(out) == 3
