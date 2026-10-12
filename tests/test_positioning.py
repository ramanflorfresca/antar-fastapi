import re

from antar_engine import positioning as POS
from antar_engine import work_fit as WF

RAMAN_RANK = [{"field": "technology & innovation", "weight": 7.26}, {"field": "science & research", "weight": 6.17}, {"field": "networks / community / humanitarian", "weight": 5.08},
              {"field": "law & diplomacy", "weight": 4.85}, {"field": "communication & media", "weight": 4.54}, {"field": "arts & design", "weight": 4.45}]
CHART = {"lagna": {"sign": "Capricorn"}, "planets": {"Rahu": {"sign": "Scorpio", "house": 11}, "Venus": {"sign": "Scorpio", "house": 11}, "Sun": {"sign": "Scorpio", "house": 11}},
         "divisional_charts": {"d10": {"planets": {"Rahu": {"sign": "Sagittarius", "house": 8}}}}}
PROFILE = {"role": "running_business", "what": "AI agents for small businesses", "stage": "launched"}
JARGON = ("Rahu", "Venus", "Saturn", "Jupiter", "Mercury", "dasha", "Vimshottari", "D-10", "D10", "Parashari", "yoga", "nakshatra", "house of")


def test_intent_detection():
    for q in ("How should I position my AI agents platform for small businesses?", "how do I pitch my startup", "What should I lead with when I sell my service?",
              "Cómo debo posicionar mi plataforma de IA", "go to market for my app?"):
        assert POS.is_positioning_q(q), q
    for q in ("Should I switch careers?", "When will I get a raise?", "What position is Mars in my chart?", "Is this a good week to sign a lease?", ""):
        assert not POS.is_positioning_q(q), q


def test_the_interview_asks_role_then_what_then_stops():
    assert POS.ask_back({}, "en")["key"] == "role" and POS.ask_back({"role": "job"}, "en")["key"] == "what"
    assert POS.ask_back({"role": "job", "what": "x"}, "en") is None
    i = POS.interview({}, "en")
    assert i["messages"] == [POS.ask_back({}, "en")["prompt"]] and i["ask_back"]["options"][0]["value"] == "running_business"
    assert POS.interview({"role": "job", "what": "x"}, "en") is None
    assert POS.ask_back({}, "es")["prompt"].startswith("Antes de responder")


def test_a_full_answer_is_short_messages_from_the_chart_with_no_planet_talk(monkeypatch):
    monkeypatch.setattr(POS, "_recognition_lags", lambda chart: True)
    fit = WF.fit(RAMAN_RANK, PROFILE["what"], "en")
    r = POS.compose(CHART, fit, dict(PROFILE, market="small shops in the US and LATAM"), md="Rahu", until="Apr 2029", window="Nov 2026 – Jan 2027",
                    leadership="executive / leader", past_hands_on=["Tech platform for flower delivery"], lang="en")
    m = r["messages"]
    assert 5 <= len(m) <= 9 and all(len(x.splitlines()) <= 5 for x in m)                      # a run of short messages, never one essay
    text = "\n".join(m)
    assert m[0] == "Straight answer on positioning AI agents for small businesses: lead with what it actually does, and put your own judgment behind it."
    assert "technology & innovation, then science & research" in text and "That matches where your career path leans: systems, other people's money and AI." in text      # the D-10 Rahu fact, stated without naming the planet or the house
    assert "Lead with:" in text and "expert voice" in text and "paying customer" in text
    assert "Avoid:" in text and "Selling it to everyone" in text and "daily logistics" in text and "like your Tech platform for flower delivery" in text and "Quick bets" in text
    assert "reach, scale and being seen as the authority" in text and "to Apr 2029" in text and "Nov 2026 – Jan 2027" in text
    assert "small shops in the US and LATAM" in text and r["next"] and "ten more real prospects" in r["next"]
    assert not any(j in text for j in JARGON)
    assert [c["title"] for c in r["chips"]] == ["Who to partner with", "Does this fit me?"]               # market already named


def test_a_specialist_chart_gets_a_different_answer(monkeypatch):
    monkeypatch.setattr(POS, "_recognition_lags", lambda chart: False)
    rank = [{"field": "finance & banking", "weight": 6.0}, {"field": "law", "weight": 5.0}, {"field": "arts / film / imagination", "weight": 4.0}]
    chart = {"lagna": {"sign": "Pisces"}, "planets": {"Rahu": {"sign": "Virgo", "house": 6}}, "divisional_charts": {"d10": {"planets": {"Rahu": {"house": 5}}}}}
    r = POS.compose(chart, WF.fit(rank, "a fintech app for freelancers", "en"), {"role": "running_business", "what": "a fintech app for freelancers"}, md="Jupiter",
                    leadership="individual / specialist", lang="en")
    text = "\n".join(r["messages"])
    assert "specialist" in text and "expert voice behind it" not in text and "Selling it to everyone" not in text and "Quick bets" not in text and "paying customer" not in text
    assert "clarity about money" in text and "teaching, trust" in text and "Who is it for, and where?" in text
    assert [c["title"] for c in r["chips"]][0] == "Which market first?"


def test_spanish_is_native_and_nothing_without_a_fit_or_a_what():
    fit = WF.fit(RAMAN_RANK, "agentes de IA para pequeños negocios software", "es")
    r = POS.compose(CHART, fit, {"role": "running_business", "what": "agentes de IA para pequeños negocios"}, md="Rahu", until="abr 2029", leadership="executive / leader", lang="es")
    text = "\n".join(r["messages"])
    assert text.startswith("Respuesta directa") and "Empieza por:" in text and "Evita:" in text and "Why:" not in text and "Lead with" not in text and "Avoid" not in text
    assert POS.compose(CHART, None, PROFILE, lang="en") is None and POS.compose(CHART, WF.fit(RAMAN_RANK, "", "en"), {"role": "job"}, lang="en") is None


def test_positioning_is_answered_early_by_a_shared_helper(monkeypatch):
    import asyncio
    import main

    class _Boom:
        def table(self, name):
            raise RuntimeError("no table")
    monkeypatch.setattr(main, "supabase", _Boom())             # no work profile anywhere -> the interview, without touching a database
    r = asyncio.run(main._positioning_answer("c1", {"planets": {}}, {}, None, "1990-01-01", "How should I position my startup?", "en"))
    assert r["ask_back"]["key"] == "role" and r["messages"] == [r["ask_back"]["prompt"]]
    assert asyncio.run(main._positioning_answer("c1", {}, {}, None, "", "When will my income increase?", "en")) is None      # not a positioning question
    assert asyncio.run(main._positioning_answer("c1", {}, {}, None, "", "How should I position my startup?", "pt")) is None    # en / es only
    p = main._positioning_payload(r)
    assert p["answer_kind"] == "positioning" and p["messages"] == r["messages"] and p["read"] == r["messages"][0] and p["verdict"] is None and p["basis"] == ""
    src = open(main.__file__, encoding="utf-8").read()
    early = src.index("[positioning-early 2026-10-12]")
    assert 'str(chart_row.data.get("birth_date") or "")[:10]' in src[early - 300:early]                  # right after the chart loads
    assert early < src.index("[career-clarify 2026-09-24]", early) < src.index("_known_role = _ask_known_current_role", early)    # before the career clarify and before any LLM work
