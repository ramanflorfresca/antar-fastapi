"""topic-read `detail`: the depth the old Today / month / year / life-chapter views showed, cut to one
topic from the existing engines' payloads. Fixtures mirror real production payloads (trimmed); the
engines themselves are never called."""
import copy
import re
from datetime import date, timedelta

import pytest

from antar_engine import topic_copy as C
from antar_engine import topic_detail as D
from antar_engine import topic_engine as T

TODAY = date(2026, 10, 8)
LANGS = ("en", "es", "pt", "hinglish")
KEYS = C.TOPIC_KEYS

_JARGON = re.compile(
    r"\b(dasha|dasa|mahadasha|antardasha|pratyantar\w*|jaimini|vimsottari|vimshottari|chara|malefic\w*|benefic\w*|"
    r"transits?|gochar|karakas?|lagna|nakshatra|navamsa|dusthana|kendra|trikona|ascendant|houses?|d-?\d{1,2}|"
    r"sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu)\b", re.I)

DAILY = {
    "headline": "Not a day to take a money or speculative risk — hold off, and keep anything you're already in small.",
    "move": "If a money decision is ready, make it today at half the size you planned.",
    "wow": "A client, partner, or counterpart reaches out or becomes available today. The signal to watch: someone on the other side of a deal moves first.",
    "do_today": ["handle a money task you've been putting off", "take the short trip or make the far-off call",
                 "go for a walk and eat early"],
    "dont_today": ["avoid difficult intellectual work", "conflict", "a large purchase"],
    "windows": [
        {"kind": "best", "start": "12:18 PM", "end": "1:07 PM", "text": "The day's most auspicious window — use it for beauty work."},
        {"kind": "avoid", "start": "2:08 PM", "end": "3:34 PM", "text": "Avoid difficult intellectual work in this window."}],
    "confidence": {"level": "low", "line": "Today's read is light — take it as a gentle nudge."},
    "domains": [
        {"key": "money", "state": "favorable", "state_label": "RISING", "line": "Money matters carry tailwind today — send invoices."},
        {"key": "body", "state": "favorable", "state_label": "RISING", "line": "Body holds up well today — a good day for movement."},
        {"key": "work", "state": "steady", "state_label": "STEADY", "line": "Work is steady today — ship small things."},
        {"key": "mind", "state": "steady", "state_label": "STEADY", "line": "Mental texture is steady today."},
        {"key": "people", "state": "steady", "state_label": "STEADY", "line": "People run hot and cold today."}],
    "active_domains": [{"key": "speculation", "label": "Risk & speculation", "caution": True},
                       {"key": "travel", "label": "Travel & foreign", "caution": True}],
    "quiet_domains": [],
}
MONTH = {
    "month_theme": "Your reputation and income both move this month — one needs a bold push, the other a guardrail.",
    "overview": "Focus on your work reputation and a creative project. After mid-month, your income and a payout look strong. "
                "But watch your spending on comfort. Your health is steady.",
    "best_week": "Week of October 26 — income and recognition converge.",
    "caution_week": "Week of October 9 — a speculative bet or creative risk can backfire fast.",
    "priority_actions": [
        {"action": "Cap your exposure on any speculative bet.", "domain": "Risk & speculation"},
        {"action": "Delay any long trip until after October 18.", "domain": "Travel & foreign"},
        {"action": "Lock in a payout between October 14 and 23.", "domain": "Money & wealth"},
        {"action": "Put your name on a visible piece of work.", "domain": "Work & reputation"}],
    "highlights": [{"domain": "work", "text": "Work is where the month rewards you.", "priority": 1},
                   {"domain": "mind", "text": "The month swings between high and low.", "priority": 2}],
    "active_domains": [{"key": "money", "label": "Money & wealth", "window": "2026-10-14 – 2026-10-23", "caution": False},
                       {"key": "work", "label": "Work & reputation", "window": "2026-10-12 – 2026-10-24", "caution": True}],
    "remedies": [{"planet": "general", "practice": "Morning sunlight for 10 minutes daily."}],
    "monthly_mantra": "I move boldly and spend wisely.", "energy_level": "mixed",
}
YEAR = {
    "year_theme": "Guard your speculative bets and protect the gains already made.",
    "year_summary": "Protect your savings first. October brings a grace period for a partnership. Your health needs a steadier routine.",
    "year_mantra": "I protect what I've built.",
    "peak_windows": {"career": {"months": "October", "signal": "Your work standing gets a quiet boost."},
                     "wealth": {"months": "All year", "signal": "Your savings are steady — protect them."},
                     "health": {"months": "November", "signal": "Your routine improves in November."}},
    "critical_dates": [{"date": "November 2026", "event": "A speculative matter comes under pressure — protect your savings."},
                       {"date": "November 2026", "event": "Your daily routine and health improve."}],
    "build_this_year": ["Your savings and the money you keep", "A close professional collaboration"],
    "protect_this_year": ["Any speculative bet — hold off until 2027", "Your health and energy"],
    "release_this_year": ["Any high-risk venture or speculative investment"],
    "events": [{"date_label": "Nov 2026", "domain": "Wealth", "polarity": -1, "text": "Money comes under pressure — protect savings."},
               {"date_label": "Oct 2026", "domain": "Career", "polarity": 1, "text": "A visible step up at work."}],
    "arcs": [{"key": "career", "trend": "rising", "when": "peaks Oct 2026"}, {"key": "wealth", "trend": "pressure", "when": "peaks Nov 2026"},
             {"key": "health", "trend": "steady", "when": "no clear signal this year"}],
}
ARC = {
    "gist": "Build your unconventional path steadily now — the groundwork you lay pays off before April 2029.",
    "verdict": "This is the wealth, network, and name-and-fame chapter you've been building toward.",
    "arc": {"began_label": "Began 2026", "end_label": "New chapter Aug 2044"},
    "cycle_timeline": [
        {"kind": "now", "start": "2026-08-13", "end": "2027-01-08", "title": "The tightest stretch of this",
         "body": "Pressure concentrates on income and a sibling. Hold steady — don't expand on credit.", "when_label": "until early Jan 2027", "events": []},
        {"kind": "sub_chapter", "start": "2026-08-13", "end": "2029-04-25", "title": "A restless, ambitious undercurrent",
         "body": "Boundary-pushing, unconventional moves.", "when_label": "to Apr 2029",
         "events": [{"title": "A partnership window opens", "category": "RELATIONSHIP", "window_label": "through late Apr 2029"},
                    {"title": "A major acquisition lands", "category": "WORK", "window_label": "Q3 2028", "conviction_label": "Likely"}]},
        {"kind": "turn", "start": "2029-04-25", "end": "2031-09-19", "title": "The pressure lifts",
         "body": "Expansion and mentorship.", "events": [{"title": "A meaningful move", "category": "RELOCATION", "window_label": "around 2031"},
                                                        {"title": "A partnership reshapes", "category": "RELATIONSHIP", "window_label": "around 2030"}]},
        {"kind": "new_chapter", "start": "2044-08-13", "end": "2060-08-13", "title": "A different 16-year chapter opens", "body": "The whole tone resets.", "events": []}],
    "predicted_events": [
        {"title": "A pay rise lands", "category": "WORK", "window_start": "2027-03-01", "window_label": "Q1 2027", "conviction_label": "Likely"},
        {"title": "A far-off event", "category": "WORK", "window_start": "2029-03-01", "window_label": "2029"},
        {"title": "Savings grow", "category": "WEALTH", "window_start": "2026-12-01", "window_label": "Dec 2026"}],
}
SRC = {"daily": DAILY, "month": MONTH, "year": YEAR, "arc": ARC}
SCALES = ("today", "month", "year", "season", "chapter")


def _strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            if k not in ("start", "end", "when", "state", "level", "trend", "energy_level"):
                yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)


# ── detail present, topic-filtered, on every scale, for all seven topics ─────
@pytest.mark.parametrize("topic", KEYS)
@pytest.mark.parametrize("scale", SCALES)
def test_detail_is_a_dict_or_none_and_never_empty(topic, scale):
    d = D.build_detail(topic, scale, SRC, TODAY)
    assert d is None or (isinstance(d, dict) and any(v not in (None, [], {}, "") for v in d.values()))


def test_every_scale_has_detail_for_the_topics_the_fixtures_speak_to():
    assert D.build_detail("money", "today", SRC, TODAY)["do"]
    assert D.build_detail("money", "month", SRC, TODAY)["priority_actions"]
    assert D.build_detail("money", "year", SRC, TODAY)["caution"]
    assert D.build_detail("money", "season", SRC, TODAY)["tightest_stretch"]
    assert D.build_detail("business", "chapter", SRC, TODAY)["story"]
    for topic in KEYS:   # every topic gets something at the day level (confidence + times at least)
        assert D.build_detail(topic, "today", SRC, TODAY)["best_times"]


def test_today_is_cut_to_the_topic():
    money, health = D.build_detail("money", "today", SRC, TODAY), D.build_detail("health", "today", SRC, TODAY)
    assert "handle a money task you've been putting off" in money["do"]
    assert money["domain"] == {"state": "favorable", "state_label": "RISING", "line": DAILY["domains"][0]["line"]}
    assert money["do"][0] == DAILY["domains"][0]["line"]                      # the topic's own line leads
    assert "a large purchase" in money["avoid"] and "a large purchase" not in health["avoid"]
    assert not any("money" in x.lower() for x in health["do"])
    assert health["domain"]["line"] == DAILY["domains"][1]["line"]
    # an item that matches no topic is kept under `day`, not dropped
    assert "take the short trip or make the far-off call" in money["day"]["do"]
    assert "take the short trip or make the far-off call" not in money["do"]
    assert money["watch_for"] is None                                           # the signal is about a deal -> business
    assert "someone on the other side of a deal moves first" in D.build_detail("business", "today", SRC, TODAY)["watch_for"]
    assert money["best_times"] == [{"start": "12:18 PM", "end": "1:07 PM", "text": DAILY["windows"][0]["text"]}]
    assert money["steer_clear"][0]["start"] == "2:08 PM"
    assert money["confidence"]["level"] == "low"


def test_month_is_cut_to_the_topic():
    m = D.build_detail("money", "month", SRC, TODAY)
    assert [a["domain"] for a in m["priority_actions"]] == ["Risk & speculation", "Money & wealth"]
    assert m["overview"] == "After mid-month, your income and a payout look strong. But watch your spending on comfort."
    assert m["theme"] == MONTH["month_theme"] and m["mantra"] and m["energy_level"] == "mixed"
    assert m["focus"] == {"window": "2026-10-14 – 2026-10-23", "careful": False}
    assert m["remedies"] and m["best_week"] and m["caution_week"]
    h = D.build_detail("health", "month", SRC, TODAY)
    assert h["priority_actions"] == [] and "health is steady" in h["overview"]
    assert [x["domain"] for x in D.build_detail("career", "month", SRC, TODAY)["highlights"]] == ["work"]


def test_year_is_cut_to_the_topic():
    y = D.build_detail("money", "year", SRC, TODAY)
    assert y["theme"] == YEAR["year_theme"]
    assert y["caution"] == [{"when": "Nov 2026", "text": "Money comes under pressure — protect savings."}]
    assert y["strong"] == [] and y["peak"]["months"] == "All year"
    assert y["trend"] == {"trend": "pressure", "when": "peaks Nov 2026"}
    assert y["prioritise"] == ["Your savings and the money you keep"]
    assert len(y["key_months"]) == 1 and y["release"]
    c = D.build_detail("career", "year", SRC, TODAY)
    assert c["strong"] and not c["caution"] and c["peak"]["text"].startswith("Your work standing")


def test_stretch_and_chapter_are_cut_to_the_topic():
    s = D.build_detail("money", "season", SRC, TODAY)
    assert s["story"].startswith("Build your unconventional path")
    assert s["tightest_stretch"]["title"] == "The tightest stretch of this" and s["tightest_stretch"]["when"] == "until early Jan 2027"
    assert [x["title"] for x in s["next_months"]] == ["Savings grow"]          # inside 12 months, this topic only
    career = D.build_detail("career", "season", SRC, TODAY)
    assert career["ahead"][0]["events"] == [{"title": "A major acquisition lands", "when": "Q3 2028", "likelihood": "Likely"}]
    assert [x["title"] for x in career["next_months"]] == ["A pay rise lands"]
    ch = D.build_detail("love", "chapter", SRC, TODAY)
    assert ch["story"].startswith("This is the wealth") and ch["began"] == "Began 2026"
    assert ch["ahead"][0]["events"][0]["title"] == "A partnership reshapes"
    assert D.build_detail("health", "chapter", SRC, TODAY)["ahead"] == []       # nothing for health -> empty, not invented


# ── hide when empty, never invent ────────────────────────────────────────────
@pytest.mark.parametrize("scale", SCALES)
@pytest.mark.parametrize("src", [{}, {"daily": None, "month": None, "year": None, "arc": None},
                                 {"daily": {}, "month": {}, "year": {}, "arc": {}},
                                 {"daily": {"fallback": True}, "month": "x", "year": [], "arc": 3}])
def test_nothing_from_the_engine_means_no_detail(scale, src):
    for topic in KEYS:
        assert D.build_detail(topic, scale, src, TODAY) is None


def test_jargon_strings_from_an_engine_are_dropped_not_shown():
    daily = {"do_today": ["pay the invoice while Jupiter transits your second house"], "wow": "Rahu moves through your seventh house today."}
    assert D.build_detail("money", "today", {"daily": daily}, TODAY) is None


def test_one_section_can_hide_while_others_show():
    daily = copy.deepcopy(DAILY)
    daily["wow"], daily["windows"] = "", []
    d = D.build_detail("money", "today", {"daily": daily}, TODAY)
    assert d["watch_for"] is None and d["best_times"] == [] and d["do"]


def test_domain_table_skips_unmapped_domains():
    assert D.topics_for("Travel & foreign") == () and D.topics_for("legal") == ()
    assert set(t for v in D.DOMAIN_TOPICS.values() for t in v) <= set(KEYS)
    assert set(t for v in D.CATEGORY_TOPICS.values() for t in v) <= set(KEYS)
    daily = copy.deepcopy(DAILY)
    daily["domains"] = [{"key": "travel", "state": "favorable", "state_label": "RISING", "line": "Travel is lit."}]
    assert D.build_detail("money", "today", {"daily": daily}, TODAY)["domain"] is None


# ── no jargon in anything new ────────────────────────────────────────────────
@pytest.mark.parametrize("scale", SCALES)
def test_no_jargon_in_any_detail_string(scale):
    for topic in KEYS:
        for s in _strings(D.build_detail(topic, scale, SRC, TODAY)):
            assert not _JARGON.search(s), (topic, scale, s)


def test_new_static_copy_is_complete_and_plain():
    for lang in LANGS:
        for tbl in (C.CHAPTER_LABEL, C.CHAPTER_LEAD, C.KEEP_SMALL):
            assert tbl[lang] and not _JARGON.search(tbl[lang]), (lang, tbl[lang])
        assert C.CHIP[lang]["chapter"] and not _JARGON.search(C.CHIP[lang]["chapter"])
        for sc in ("month", "year"):
            lead = C.SPAN_LEAD[lang][sc]
            assert not re.match(r"(this month|this year|este mes|este año|este mês|este ano|is mahine|is saal)", lead, re.I), lead
    assert C.SPAN_LEAD["en"]["month"] == "Over the next 30 days"
    assert C.SPAN_LEAD["en"]["year"] == "Over your year, to your birthday"


# ── Right now vs the day's own advice ────────────────────────────────────────
def _open_today(**kw):
    out = {"topic": "money", "scale": "today", "language": "en", "tone": "open",
           "claim": "Today, money matters have better backing than usual, so it is a good stretch to act on income, pricing and plans.",
           "your_move": "Act on one income or pricing decision today.", "detail": None}
    out.update(kw)
    return out


def test_caution_is_reconciled_with_an_open_window():
    d = D.build_detail("money", "today", SRC, TODAY)
    assert d["caution_note"] == DAILY["headline"]
    out = D.reconcile(_open_today(detail=d), DAILY, "en")
    assert out["claim"] == _open_today()["claim"] + " " + DAILY["headline"]    # the open-window headline stays, then the day's own caution
    assert out["your_move"] == "Act on one income or pricing decision today. But keep any bet small."
    assert out["detail"]["caution_note"] == DAILY["headline"]
    assert D.reconcile(out, DAILY, "en")["your_move"] == out["your_move"]      # idempotent


def test_caution_reaches_a_read_that_has_no_other_detail():
    out = D.reconcile(_open_today(detail=None), DAILY, "en")
    assert out["detail"] == {"caution_note": DAILY["headline"]}


@pytest.mark.parametrize("lang", LANGS)
def test_keep_small_is_added_in_every_language(lang):
    out = D.reconcile(_open_today(language=lang), DAILY, lang)
    assert out["your_move"].endswith(C.KEEP_SMALL[lang])


def test_no_caution_means_no_change():
    calm = copy.deepcopy(DAILY)
    calm["active_domains"] = [{"key": "speculation", "caution": False}]
    base = _open_today()
    assert D.reconcile(base, calm, "en") == base
    assert D.reconcile(base, None, "en") == base
    # a topic the risk advice does not inform is left alone
    health = _open_today(topic="health")
    assert D.reconcile(health, DAILY, "en") == health
    # only the Right-now read is reconciled, and only an open window needs the move softened
    month = _open_today(scale="month")
    assert D.reconcile(month, DAILY, "en") == month
    care = D.reconcile(_open_today(tone="care"), DAILY, "en")
    assert care["your_move"] == _open_today()["your_move"] and care["detail"]["caution_note"] == DAILY["headline"]


def test_a_caution_domain_state_is_its_own_note():
    daily = copy.deepcopy(DAILY)
    daily["active_domains"] = []
    daily["domains"][0] = {"key": "money", "state": "caution", "state_label": "CARE", "line": "Money needs care today — go slowly."}
    d = D.build_detail("money", "today", {"daily": daily}, TODAY)
    assert d["caution_note"] == "Money needs care today — go slowly." and d["avoid"][0] == d["caution_note"]


# ── the 30-day read includes today ───────────────────────────────────────────
class _Ctx:
    chart_id = "c"
    birth_date = "1990-10-15"
    dashas = {}
    time_quality = "exact"


def _lit(mode):
    return {"lit": True, "mode": mode, "score": 5.0, "n_signals": 2}


def test_fold_in_today_adds_a_window_open_today():
    opens, cares = [], []
    T.assess, orig = (lambda ctx, key, on, ev: _lit("open")), T.assess
    try:
        ctx = type("X", (), {"events": lambda self, a, b, c: []})()
        T._fold_in_today(ctx, "money", TODAY, opens, cares)
    finally:
        T.assess = orig
    assert cares == [] and len(opens) == 1 and opens[0]["start"] == opens[0]["end"] == TODAY


def test_fold_in_today_extends_a_window_that_starts_soon_and_skips_covered_days():
    ctx = type("X", (), {"events": lambda self, a, b, c: []})()
    orig = T.assess
    T.assess = lambda *a: _lit("open")
    try:
        soon = {"start": TODAY + timedelta(days=4), "end": TODAY + timedelta(days=9), "score": 3.0, "assessments": [_lit("open")]}
        T._fold_in_today(ctx, "money", TODAY, [soon], [])
        assert soon["start"] == TODAY
        covering = {"start": TODAY - timedelta(days=1), "end": TODAY + timedelta(days=2), "score": 3.0, "assessments": []}
        lst = [covering]
        T._fold_in_today(ctx, "money", TODAY, lst, [])
        assert lst == [covering] and covering["start"] == TODAY - timedelta(days=1)
        far = {"start": TODAY + timedelta(days=20), "end": TODAY + timedelta(days=25), "score": 3.0, "assessments": []}
        lst = [far]
        T._fold_in_today(ctx, "money", TODAY, lst, [])
        assert len(lst) == 2 and far["start"] == TODAY + timedelta(days=20)
    finally:
        T.assess = orig


def test_month_read_lists_a_window_open_today_instead_of_saying_nothing_sharp(monkeypatch):
    ctx = T.TopicContext("c", {"lagna": {"sign": "Aries"}}, {}, birth_date="1990-10-15")
    quiet = {"lit": False, "mode": "steady", "score": 0.0, "n_signals": 0, "dasha_kind": "none",
             "chara_confirm": False, "polarity": "neutral", "tone": 0, "first_date": "", "last_date": ""}
    monkeypatch.setattr(T, "_scan", lambda c, k, sc, per, today: [((TODAY, TODAY + timedelta(days=6)), quiet)])
    monkeypatch.setattr(T, "assess", lambda c, k, on, ev: dict(
        quiet, **_lit("open"), dasha_kind="core", chara_confirm=True, polarity="opportunity",
        first_date=on.isoformat(), last_date=on.isoformat()))
    monkeypatch.setattr(ctx, "events", lambda *a, **k: [], raising=False)
    r = T.read_topic(ctx, "money", "month", TODAY, "en", with_best_fit=False)
    assert r["tone"] == "open"
    assert r["best_window"]["start"] == TODAY.isoformat() and r["best_window"]["window_phase"] == "now"
    assert "nothing" not in r["claim"].lower()
    assert r["claim"].startswith("Over the next 30 days")


# ── labels ───────────────────────────────────────────────────────────────────
def _ctx(birth="1990-10-15", md=("2023-01-01", "2044-08-13")):
    rows = [{"level": "antardasha", "start_date": "2026-06-01", "end_date": "2029-04-25"},
            {"level": "mahadasha", "start_date": md[0], "end_date": md[1]}]
    return T.TopicContext("c", {"lagna": {"sign": "Aries"}}, {"vimsottari": rows}, birth_date=birth)


@pytest.mark.parametrize("lang,exp", [("en", "10/15/25 – 10/15/26"), ("es", "15/10/25 – 15/10/26"),
                                      ("pt", "15/10/25 – 15/10/26"), ("hinglish", "15/10/25 – 15/10/26")])
def test_year_chip_is_numeric_in_locale_order(lang, exp):
    assert T._period(_ctx(), "year", TODAY, lang)["chip"] == exp
    assert T._period(_ctx(), "year", TODAY, lang)["label"] == C.PERIOD_LABEL[lang]["year"]


def test_year_chip_uses_real_previous_and_next_birthdays():
    assert T._period(_ctx("1990-11-26"), "year", TODAY, "en")["chip"] == "11/26/25 – 11/26/26"
    assert T._period(_ctx("1990-11-26"), "year", TODAY, "es")["chip"] == "26/11/25 – 26/11/26"


@pytest.mark.parametrize("lang,chip", [("en", "Life chapter"), ("es", "Capítulo de vida"),
                                       ("pt", "Capítulo de vida"), ("hinglish", "Life chapter")])
def test_chapter_period_chip_and_label(lang, chip):
    p = T._period(_ctx(), "chapter", TODAY, lang)
    assert p["chip"] == chip and p["rung"] == "chapter"
    assert (p["start"], p["end"]) == (date(2023, 1, 1), date(2044, 8, 13))
    assert p["label"] == C.CHAPTER_LABEL[lang].format(end=C.month_year_short(date(2044, 8, 13), lang))
    assert p["label"].startswith({"en": "Your current life chapter · to", "es": "Tu capítulo de vida actual · hasta",
                                  "pt": "O seu capítulo de vida atual · até", "hinglish": "Aapka maujooda life chapter"}[lang])


def test_chapter_read_keeps_the_stretch_label_as_the_secondary_line():
    r = T.read_topic(_ctx(), "money", "chapter", TODAY, "en", with_best_fit=False)
    assert r["scale"] == "chapter" and r["period"]["rung"] == "chapter" and r["period"]["chip"] == "Life chapter"
    assert r["period"]["label"] == "Your current life chapter · to Aug 2044"
    assert r["period"]["stretch_label"].startswith("The next ") and "2029" in r["period"]["stretch_label"]
    assert r["claim"].startswith("Across your current life chapter")
    assert (r["period"]["start"], r["period"]["end"]) == ("2023-01-01", "2044-08-13")


def test_old_lead_words_are_gone_from_month_and_year_claims():
    for lang in LANGS:
        for sc in ("month", "year"):
            r = T.read_topic(_ctx(), "money", sc, TODAY, lang, with_best_fit=False)
            assert r["claim"].startswith(C.SPAN_LEAD[lang][sc])
    assert T.read_topic(_ctx(), "money", "month", TODAY, "en", with_best_fit=False)["claim"].startswith("Over the next 30 days")
    assert T.read_topic(_ctx(), "money", "year", TODAY, "en", with_best_fit=False)["claim"].startswith("Over your year, to your birthday")


# ── the route: cached under a salted key, sources loaded once per request ────
@pytest.fixture
def client(monkeypatch):
    import main
    from fastapi.testclient import TestClient
    import antar_engine.topic_engine as te
    te.cache_clear()
    monkeypatch.setattr(main, "_prac_local_date", lambda tz=None: TODAY)
    return TestClient(main.app), main, te


def _base(topic="money", scale="today", tone="open"):
    return {"chart_id": "c", "topic": topic, "scale": scale, "language": "en", "tone": tone, "label": "Money",
            "claim": "Today, a good stretch.", "your_move": "Act on one income decision today.",
            "period": {"start": TODAY.isoformat(), "end": TODAY.isoformat(), "label": "Today", "chip": "Right now", "rung": "now"},
            "best_window": None, "watch_window": None}


def test_route_attaches_detail_and_reconciles(client, monkeypatch):
    c, main, te = client
    calls = []
    monkeypatch.setattr(main, "_topic_read_compute", lambda chart, topic, scale, lang, tz: _base(topic, scale))

    async def src(name, chart, lang, today):
        calls.append(name)
        return copy.deepcopy(SRC[name])
    monkeypatch.setattr(main, "_topic_source", src)
    r = c.get("/api/v1/chart/c/topic-read?topic=money&scale=today&tz_offset=-240")
    assert r.status_code == 200
    body = r.json()
    assert body["detail"]["do"] and body["detail"]["caution_note"] == DAILY["headline"]
    assert body["your_move"].endswith("But keep any bet small.") and body["claim"] == "Today, a good stretch. " + DAILY["headline"]
    assert calls == ["daily"]
    c.get("/api/v1/chart/c/topic-read?topic=money&scale=today&tz_offset=-240")
    assert calls == ["daily"]                                                     # second hit is served from the cache
    assert any(k[:2] == ("topic-read", "v9-detail") for k in te._CACHE)           # version-salted key


@pytest.mark.parametrize("scale,need", [("month", "month"), ("year", "year"), ("season", "arc"), ("chapter", "arc")])
def test_route_loads_only_the_engine_a_scale_needs_and_accepts_chapter(client, monkeypatch, scale, need):
    c, main, te = client
    calls = []
    monkeypatch.setattr(main, "_topic_read_compute", lambda chart, topic, sc, lang, tz: _base(topic, sc))

    async def src(name, chart, lang, today):
        calls.append(name)
        return copy.deepcopy(SRC[name])
    monkeypatch.setattr(main, "_topic_source", src)
    r = c.get(f"/api/v1/chart/c/topic-read?topic=money&scale={scale}")
    assert r.status_code == 200 and r.json()["detail"] and calls == [need]
    assert c.get("/api/v1/chart/c/topic-read?topic=money&scale=decade").status_code == 422


def test_route_is_fail_open_when_every_source_is_down(client, monkeypatch):
    c, main, te = client
    monkeypatch.setattr(main, "_topic_read_compute", lambda chart, topic, scale, lang, tz: _base(topic, scale))

    async def boom(*a):
        raise RuntimeError("down")
    monkeypatch.setattr(main, "_topic_source", boom)
    r = c.get("/api/v1/chart/c/topic-read?topic=money&scale=today")
    assert r.status_code == 200 and r.json()["detail"] is None and r.json()["your_move"] == "Act on one income decision today."
    assert r.json()["claim"] == "Today, a good stretch."          # every existing field is still there


def test_one_source_load_serves_all_seven_topics(client, monkeypatch):
    c, main, te = client
    monkeypatch.setattr(main, "_topic_read_compute", lambda chart, topic, scale, lang, tz: _base(topic, scale))
    loads = []

    async def engine(**kw):
        loads.append(kw)
        return copy.deepcopy(DAILY)
    monkeypatch.setattr(main, "get_daily_signal_endpoint", engine)
    for k in KEYS:
        assert c.get(f"/api/v1/chart/c/topic-read?topic={k}&scale=today").status_code == 200
    assert len(loads) == 1 and loads[0]["date"] == TODAY.isoformat()


# ── the year claim names the year's own caution stretch ──────────────────────
def _year_out(tone="steady", lang="en", topic="money"):
    det = D.build_detail(topic, "year", SRC, TODAY)
    return {"topic": topic, "scale": "year", "language": lang, "tone": tone, "detail": det,
            "claim": "Over your year, to your birthday, nothing sharp is pulling on money, so keep your usual pace."}


def test_steady_year_claim_names_the_caution_month():
    out = D.reconcile_year(_year_out(), "en")
    assert out["claim"] == "Over your year, to your birthday, it is steady overall for money and income, with Nov 2026 the one stretch to watch."
    assert "nothing sharp" not in out["claim"]
    assert out["detail"]["caution_note"] == "Money comes under pressure — protect savings."


@pytest.mark.parametrize("lang", LANGS)
def test_year_claim_reconciles_in_every_language(lang):
    out = D.reconcile_year(_year_out(lang=lang), lang)
    assert "Nov 2026" in out["claim"] and out["claim"].startswith(C.SPAN_LEAD[lang]["year"])
    assert not _JARGON.search(out["claim"])


def test_open_year_keeps_its_claim_and_gains_a_watch_note():
    base = _year_out("open")
    out = D.reconcile_year(base, "en")
    assert out["claim"] == base["claim"] + " Watch Nov 2026."
    assert D.reconcile_year(out, "en")["claim"] == out["claim"]


def test_year_without_a_caution_is_untouched():
    base = _year_out(topic="career")
    assert D.reconcile_year(base, "en") == base
    other = dict(_year_out(), scale="month")
    assert D.reconcile_year(other, "en") == other


# ── the 30-day claim carries the month's own caution week ────────────────────
def _month_out(tone="open", lang="en", topic="money"):
    return {"topic": topic, "scale": "month", "language": lang, "tone": tone,
            "detail": D.build_detail(topic, "month", SRC, TODAY),
            "claim": "Over the next 30 days, money matters have better backing than usual, so it is a good stretch to act."}


def test_open_month_claim_gains_the_caution_week():
    base = _month_out()
    out = D.reconcile_month(base, "en")
    assert out["claim"] == base["claim"] + " " + MONTH["caution_week"]
    assert out["detail"]["caution_note"] == MONTH["caution_week"]
    assert D.reconcile_month(out, "en")["claim"] == out["claim"]               # idempotent


def test_steady_month_claim_is_replaced_not_contradicted():
    out = D.reconcile_month(_month_out("steady"), "en")
    assert out["claim"] == ("Over the next 30 days, it is steady overall for money and income, with one stretch to watch. "
                            + MONTH["caution_week"])
    assert "nothing sharp" not in out["claim"]


@pytest.mark.parametrize("lang", LANGS)
def test_month_claim_reconciles_in_every_language(lang):
    out = D.reconcile_month(_month_out("steady", lang), lang)
    assert out["claim"].startswith(C.SPAN_LEAD[lang]["month"]) and out["claim"].endswith(MONTH["caution_week"])
    assert not _JARGON.search(C.MONTH_CAUTION_CORE[lang])


def test_month_without_a_topic_caution_is_untouched():
    for topic in ("health", "love"):
        base = _month_out(topic=topic)
        assert D.reconcile_month(base, "en") == base
    other = dict(_month_out(), scale="year")
    assert D.reconcile_month(other, "en") == other


def test_steady_today_claim_is_replaced_by_the_caution():
    out = D.reconcile(_open_today(tone="steady", claim="Today, nothing sharp is pulling on money, so keep your usual pace."), DAILY, "en")
    assert out["claim"] == "Today, keep it quiet on money and income. " + DAILY["headline"]
    assert "nothing sharp" not in out["claim"]


@pytest.mark.parametrize("lang", LANGS)
def test_today_claim_carries_the_caution_in_every_language(lang):
    for tone in ("open", "steady"):
        out = D.reconcile(_open_today(tone=tone, language=lang), DAILY, lang)
        assert out["claim"].endswith(DAILY["headline"])
    assert not _JARGON.search(C.TODAY_CAUTION_CORE[lang])


def test_care_today_claim_is_left_alone():
    base = _open_today(tone="care")
    assert D.reconcile(base, DAILY, "en")["claim"] == base["claim"]
