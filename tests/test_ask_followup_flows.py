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


def test_love_never_assumes_a_partner_unless_named():
    single = [f["q"] for f in af.pick("love", "When will I find love?", "en")]
    assert not any("partner" in q or "we?" in q for q in single), single
    paired = [f["q"] for f in af.pick("love", "Is my marriage going through a rough patch?", "en")]
    assert any("partner" in q or "compatible" in q for q in paired), paired
    es = [f["q"] for f in af.pick("love", "¿Cuándo llega el amor?", "es")]
    assert not any("pareja" in q or "somos" in q for q in es), es
def test_a_tapped_chip_keeps_its_topic():
    assert af.bucket_of("Should I concentrate or diversify?") == "money"
    assert af.bucket_of("Which profession fits me best?") == "career"
    assert af.bucket_of("¿Debo concentrarme o diversificar?") == "money"
    assert af.bucket_of("Will I be rich?") is None
    assert af.bucket_of("How is my money looking right now?") is None   # general → resolved concern decides


# ── [astrologer-voice 2026-10-10] a client's questions to an astrologer, not an advisor's ──
_ADVISOR = ("concentrate or diversify", "which profession", "business or a job", "build alone", "partner or alone",
            "first real customers", "kind of founder", "cash flow", "protect my cash", "keep speculation small",
            "debo concentrarme", "qué profesión", "devo concentrar", "qual profissão", "emprender solo", "empreender sozinho",
            "diversify karun", "kaun sa profession", "akele build",
            "how do i handle", "which daily practice", "what should i focus on", "which practice fits", "how do i steady")


def test_followups_read_like_a_client_asking_an_astrologer():
    for lang, table in af._Q.items():
        for bucket, lanes in table.items():
            for lane, q in lanes.items():
                assert not any(w in q.lower() for w in _ADVISOR), (lang, bucket, lane, q)


def test_old_advisor_chips_still_keep_their_topic_when_tapped():
    assert af.bucket_of("Should I concentrate or diversify?") == "money"
    assert af.bucket_of("Which profession fits me best?") == "career"
    assert af.bucket_of("What can I do to strengthen my money period?") == "money"
    assert af.bucket_of("How does my career period look this year?") == "career"


def test_what_to_do_lane_is_titled_what_helps():
    assert af._LANE_TITLE["en"]["how"] == "🪔 What helps"
    out = af.pick("money", "When does my strongest money window open?", "en")
    assert [o["title"] for o in out if o["lane"] == "how"] == ["🪔 What helps"]


def test_remaining_advisor_questions_are_gone_but_old_chips_still_map():
    assert af.bucket_of("How do I handle the tension at home right now?") == "family"
    assert af.bucket_of("Which daily practice fits me now?") == "health"
    assert af.bucket_of("How do I steady my mind this month?") == "spiritual"
    assert af.bucket_of("What helps steady my mind during this period?") == "spiritual"


# ── month / year answers get chips at that scale ─────────────────────────────
def test_scale_is_read_from_the_question_in_every_language():
    for q in ("How is my money this month?", "¿Cómo está mi dinero este mes?", "Como está meu dinheiro neste mês? próximo mês",
              "Is mahine mera paisa kaisa hai?", "What about the next 30 days?"):
        assert af.asked_scale(q) == "month", q
    for q in ("How is my career this year?", "¿Cómo está mi salud este año?", "E o próximo ano?", "Is saal mera career kaisa hai?"):
        assert af.asked_scale(q) == "year", q
    assert af.asked_scale("this month or this year?") == "year"
    assert af.asked_scale("How is my money?") is None and af.asked_scale("How is my day today?") is None


def test_month_answer_offers_the_week_and_the_year_beyond():
    out = af.pick("money", "How is my money this month?", "en")
    assert out[0] == {"q": "Which week this month is best for my money?", "lane": "when", "title": "⏳ Timing"}
    assert out[1]["q"] == "How does the year ahead look for my money?" and out[1]["lane"] == "wide"
    assert len(out) == 3 and out[2]["lane"] == "bridge"


def test_year_answer_offers_the_months_and_the_next_30_days():
    out = af.pick("career", "How is my career looking this year?", "en")
    assert out[0]["q"] == "Which months this year are strongest for my career?"
    assert out[1]["q"] == "How do the next 30 days look for my career?"


def test_scale_chips_exist_in_every_language_for_every_topic_and_read_like_a_client():
    for lang in af._SCALE_Q:
        for bucket in af._SCALE_AREA[lang]:
            for scale in ("month", "year"):
                pool = af.scale_pool(bucket, scale, lang)
                assert set(pool) == {"when", "how", "now", "wide"}
                for q in pool.values():
                    assert "{" not in q and not any(w in q.lower() for w in _ADVISOR), (lang, bucket, q)
    assert af.pick("money", "¿Cómo está mi dinero este año?", "es")[0]["q"] == "¿Qué meses de este año son más fuertes para mi dinero?"
    assert af.pick("money", "Is saal mera paisa kaisa hai?", "hinglish")[0]["q"].startswith("Is saal ke kaun se mahine paise")


def test_tapped_scale_chips_keep_their_topic_and_day_questions_are_untouched():
    assert af.bucket_of("Which months this year are strongest for my career?") == "career"
    assert af.bucket_of("Which week this month is best for my health?") == "health"
    assert [o["lane"] for o in af.pick("day", "How is my day today?", "en")] != ["when", "wide"]
    assert af.pick("money", "How is my money this month?", "en")[0]["q"] != af.pick("money", "How is my money?", "en")[0]["q"]
