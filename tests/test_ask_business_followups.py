"""[business-followups 2026-10-02] A startup question got career chips ("Which
profession fits me best?") and the career practice ("Before the hard
conversation…"). Business now has its own follow-ups and practice."""


def _m():
    from dotenv import load_dotenv
    load_dotenv()
    import main
    return main


def test_business_and_startup_get_business_followups():
    m = _m()
    for concern in ("business", "startup"):
        for lang in ("en", "es", "pt"):
            fus = m._ask_followups(concern, "When does my startup take off", lang)
            assert fus and not any("profes" in q.lower() for q in fus), (concern, lang, fus)
    assert "Which profession fits me best?" in m._ask_followups("career", "x", "en")


def test_business_practice_is_not_the_career_one():
    m = _m()
    for lang in ("en", "es", "pt"):
        assert m._ask_practice_cta("business", lang)["step"] != m._ask_practice_cta("career", lang)["step"]
