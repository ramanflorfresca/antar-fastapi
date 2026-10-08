"""Questions for you: selection, wording, routing, dedupe, route behaviour. Deterministic."""
import re
import sys
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from test_topic_engine import _JARGON, C, T  # noqa: E402

from antar_engine import suggested_questions as SQ  # noqa: E402

TODAY = date(2026, 10, 8)
CHART = "a4c9d57b-fb9c-4890-8fe7-4a9904f515ed"
LANGS = ("en", "es", "pt", "hinglish")
TOPICS = list(T.TOPIC_KEYS)


def d(n):
    return (TODAY + timedelta(days=n)).isoformat()


def _w(topic, kind, s, e):
    return {"topic": topic, "kind": kind, "start": d(s), "end": d(e)}


def feed():
    return {
        "now": [_w("career", "open", -3, 4), _w("money", "open", -1, 12), _w("peace", "care", -2, 6)],
        "next": [_w("love", "open", 20, 30), _w("health", "open", 100, 110), _w("family", "care", 30, 35)],
        "care": [_w("family", "care", 30, 35), _w("business", "care", 60, 65)],
    }


def build(f=None, rows=(), lang="en", limit=3, chart=CHART):
    return SQ.build(feed() if f is None else f, list(rows), chart, TODAY, lang, limit)


# ── selection ────────────────────────────────────────────────────────────────
def test_order_open_now_then_opening_soon_then_care():
    out = build()
    assert out["count"] == 3 == len(out["questions"])
    assert [(q["kind"], q["topic"]) for q in out["questions"]] == [
        ("open_now", "career"),          # closes soonest (4 days) of the open-now windows
        ("opening_soon", "love"),        # next window to open, inside 90 days
        ("care", "peace")]               # a care stretch already running leads the care slot
    q = out["questions"]
    assert q[0]["text"] == "Is this a good week to make my ask at work?"
    assert q[1]["text"] == "Is October a good time to take the next step in a close relationship?"
    assert q[2]["text"] == "What should I hold off on to protect my peace until Oct 14?"
    assert all(x["reason"] and set(x) == {"id", "topic", "text", "reason", "kind"} for x in q)


def test_windows_outside_the_ranges_are_not_picked_for_their_slot():
    f = {"now": [], "next": [_w("health", "open", 120, 130)], "care": [_w("business", "care", 60, 65)]}
    out = build(f)
    kinds = [x["kind"] for x in out["questions"]]
    assert "opening_soon" not in kinds[:1] and out["questions"][0]["kind"] != "care"
    # nothing qualifies by window, so it is all follow-up / evergreen
    assert set(kinds) == {"followup"} and out["count"] == 3


def test_one_question_per_topic_and_limit():
    f = {"now": [_w("money", "open", 0, 3), _w("money", "care", 0, 9)], "next": [_w("money", "open", 20, 25)],
         "care": [_w("money", "care", 30, 33)]}
    out = build(f, limit=5)
    topics = [q["topic"] for q in out["questions"]]
    assert len(topics) == len(set(topics)) == 5
    assert build(limit=1)["count"] == 1 and build(limit=99)["count"] == 5 and build(limit=0)["count"] >= 1


def test_the_soonest_closing_window_leads_and_a_blocked_topic_falls_to_the_next():
    rows = [{"question": "Is this a good week to make my ask at work?", "domain": "career"}]
    out = build(rows=rows)
    assert out["questions"][0]["topic"] == "money" and out["questions"][0]["kind"] == "open_now"


def test_never_repeats_a_question_in_the_last_20_history_rows_case_insensitive():
    base = build()["questions"]
    rows = [{"question": "  " + q["text"].upper() + " ", "domain": "general"} for q in base]
    out = build(rows=rows)
    asked = {q["text"].casefold() for q in base}
    assert all(q["text"].casefold() not in asked for q in out["questions"])
    assert out["count"] == 3
    # the 21st row no longer counts
    rows21 = [{"question": "x", "domain": "general"}] * 20 + [{"question": base[0]["text"], "domain": "general"}]
    assert build(rows=rows21)["questions"][0]["text"] == base[0]["text"]


def test_followup_from_recent_ask_history_then_evergreen():
    rows = [{"question": "When will my money situation ease?", "domain": "money", "created_at": "2026-10-07"}]
    out = build({"now": [], "next": [], "care": []}, rows)
    first = out["questions"][0]
    assert first["kind"] == "followup" and first["topic"] == "money" and first["text"].endswith("?")
    assert first["text"].casefold() != rows[0]["question"].casefold()
    assert "money" in first["reason"]
    assert out["count"] == 3 and len({q["topic"] for q in out["questions"]}) == 3


def test_ids_are_stable_per_chart_day_topic_kind():
    a, b = build()["questions"], build()["questions"]
    assert [q["id"] for q in a] == [q["id"] for q in b] and len({q["id"] for q in a}) == 3
    assert build(chart="other")["questions"][0]["id"] != a[0]["id"]
    tomorrow = SQ.build(feed(), [], CHART, TODAY + timedelta(days=1), "en", 3)["questions"]
    assert tomorrow[0]["id"] != a[0]["id"]


def test_no_feed_still_gives_evergreen_questions():
    out = SQ.build(None, [], CHART, TODAY, "en", 3)
    assert out["count"] == 3 and all(q["kind"] == "followup" for q in out["questions"])
    assert SQ.build({"garbage": 1, "now": [{"topic": "x"}]}, [], CHART, TODAY, "en", 3)["count"] == 3


# ── words ────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("lang", LANGS)
def test_four_languages(lang):
    out = build(lang=lang)
    assert out["count"] == 3
    for q in out["questions"]:
        assert q["text"].endswith("?") and "{" not in q["text"] + q["reason"] and q["reason"]
    en = build(lang="en")["questions"]
    if lang != "en":
        assert [q["text"] for q in out["questions"]] != [q["text"] for q in en]


def test_hindi_and_unknown_languages_fall_back_to_english():
    for raw in ("hi", "fr", None, ""):
        assert [q["text"] for q in SQ.build(feed(), [], CHART, TODAY, raw, 3)["questions"]] == \
            [q["text"] for q in build(lang="en")["questions"]]


def all_texts():
    """Every question text the tables can produce: (lang, topic, text)."""
    for lang in LANGS:
        for t in TOPICS:
            for do in SQ.DO[lang][t][:1]:
                yield lang, t, SQ.NOW_FRAME[lang].format(do=do)
            for m in C.FULL_MONTHS[lang]:
                yield lang, t, SQ.SOON_FRAME[lang].format(month=m, do=SQ.DO[lang][t][1])
            yield lang, t, SQ.CARE[lang][t].format(date=C.day_label(date(2026, 10, 24), lang))
            yield lang, t, SQ.EVERGREEN[lang][t]


def test_tables_are_complete():
    for lang in LANGS:
        assert set(SQ.DO[lang]) == set(SQ.CARE[lang]) == set(SQ.EVERGREEN[lang]) == set(TOPICS)
        assert all(len(v) == 2 and all(v) for v in SQ.DO[lang].values())
        assert set(SQ.REASON[lang]) == {"open_now", "opening_soon", "care", "followup", "evergreen"}


def test_every_phrase_routes_to_its_topic_or_nowhere_never_a_different_topic():
    wrong = []
    for lang, t, text in all_texts():
        got = C.topic_for_question(text)
        if got not in (t, None):
            wrong.append((lang, t, got, text))
    assert not wrong, wrong[:10]


def test_no_outcome_wording_anywhere():
    for lang, t, text in all_texts():
        assert not SQ.OUTCOME_WORDS.search(text), text
        assert not re.search(r"(?i)\b(will i|will my|am i going to|going to get|win|succeed|marry)\b", text), text
    for lang in LANGS:
        for s in SQ.REASON[lang].values():
            assert not SQ.OUTCOME_WORDS.search(s), s


def test_no_jargon_in_any_string():
    tables = (SQ.DO, SQ.NOW_FRAME, SQ.SOON_FRAME, SQ.CARE, SQ.EVERGREEN, SQ.REASON)
    from test_topic_engine import _strings
    for tbl in tables:
        for s in _strings(tbl, skip_mantra=False):
            assert not _JARGON.search(s), s
    for lang in LANGS:
        for q in build(lang=lang, limit=5)["questions"]:
            assert not _JARGON.search(q["text"]) and not _JARGON.search(q["reason"]), q
        assert not re.search(r"[$€₹]|\bprice plan|\bpremium|\bsubscri", " ".join(
            q["text"] for q in build(lang=lang)["questions"]), re.I)


# ── the route ────────────────────────────────────────────────────────────────
class _Chat:
    def __init__(self, rows):
        self.rows, self.fail = rows, False

    def table(self, name):
        assert name == "chat_messages"
        return self

    def select(self, *a):
        return self

    def eq(self, *a):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        if self.fail:
            raise RuntimeError("db down")
        return type("R", (), {"data": self.rows})()


@pytest.fixture
def env(monkeypatch):
    import main
    db = _Chat([])
    monkeypatch.setattr(main, "supabase", db)
    monkeypatch.setattr(main, "_prac_local_date", lambda tz=None: TODAY)
    T.cache_clear()
    return TestClient(main.app), db, main


URL = f"/api/v1/chart/{CHART}/suggested-questions"


def test_route_shape_and_cache(env, monkeypatch):
    cl, db, main = env
    calls = []
    monkeypatch.setattr(main, "_windows_compute", lambda *a: calls.append(a) or feed())
    r = cl.get(URL + "?language=en")
    assert r.status_code == 200 and r.json()["count"] == 3
    n = len(calls)
    # candidates are cached per (chart, language, day): a second call does not rebuild them
    real = SQ.window_candidates
    built = []
    monkeypatch.setattr(SQ, "window_candidates", lambda *a: built.append(a) or real(*a))
    assert cl.get(URL + "?language=en").json() == r.json() and not built
    assert cl.get(URL + "?language=es").json()["questions"][0]["text"].startswith("¿Es esta")
    assert len(built) == 1                                    # new language -> built once


def test_a_question_just_asked_drops_out_at_once(env, monkeypatch):
    cl, db, main = env
    monkeypatch.setattr(main, "_windows_compute", lambda *a: feed())
    first = cl.get(URL).json()["questions"][0]
    db.rows = [{"question": first["text"], "domain": "career", "created_at": "2026-10-08"}]
    again = cl.get(URL).json()["questions"]
    assert first["text"] not in [q["text"] for q in again]


def test_route_fails_open_on_engine_and_history_errors(env, monkeypatch):
    cl, db, main = env
    monkeypatch.setattr(main, "_windows_compute", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    db.fail = True
    r = cl.get(URL + "?language=pt")
    assert r.status_code == 200 and r.json()["count"] == 3
    assert all(q["kind"] == "followup" for q in r.json()["questions"])
    real = SQ.build
    monkeypatch.setattr(SQ, "build", lambda f, *a, **k: (_ for _ in ()).throw(RuntimeError("x")) if f else real(f, *a, **k))
    r = cl.get(URL)                                           # build fails once, the fallback still answers
    assert r.status_code == 200 and r.json()["count"] == 3


def test_unknown_chart_is_404(env, monkeypatch):
    cl, db, main = env
    monkeypatch.setattr(main, "_windows_compute", lambda *a: None)
    assert cl.get(URL).status_code == 404


def test_demo_chart_works_read_only(env, monkeypatch):
    cl, db, main = env
    monkeypatch.setattr(main, "_windows_compute", lambda *a: feed())
    r = cl.get(URL)                                           # no auth header, GET only
    assert r.status_code == 200 and r.json()["count"] == 3


def test_october_is_not_a_cto():
    """'cto' used to match inside 'October' and send any October question to career."""
    from antar_engine.astrological_rules import detect_concern
    assert detect_concern("Is October a good time to start a new health routine?") != "career"
    assert detect_concern("Our new CTO joined and I am anxious") == "career"
