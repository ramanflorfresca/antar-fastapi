"""Founders' brief (cofounder / business lenses): descriptive only, deterministic, jargon-free, consent-gated."""
import json
import re
import sys
from datetime import date

import pytest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from antar_engine import circle_brief as CB  # noqa: E402

LANGS = ("en", "es", "pt", "hinglish")
TODAY = date(2026, 10, 7)
_JARGON = re.compile(
    r"\b(dasha|dasa|jaimini|vimsottari|malefic\w*|benefic\w*|transits?|karakas?|lagna|nakshatra|navamsa|kendra|"
    r"ascendant|houses?|d-?\d{1,2}|sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|yoga|"
    r"price|premium|subscribe\w*)\b", re.I)
_PREDICT = re.compile(r"\b(will (succeed|win|raise|fail|work)|guarantee\w*|you'll (raise|get funded)|lucky|destined)\b", re.I)


def prof(name, role, watch=(), shift=None, pace="steady"):
    return {"first_name": name, "role": role, "role_label": CB.ROLE_LABEL["en"][role], "role_line": CB.ROLE_LINE["en"][role],
            "pace": pace, "how_you_work": [], "strong_at": [], "watch_for": [{"title": w, "effect": ""} for w in watch],
            "watch_for_none": None if watch else "Nothing flagged in the chart.", "shift": shift}


def test_role_is_deterministic_from_pace_and_strength_labels():
    assert CB.role_of("fast", ["Raj"]) == "driver"
    assert CB.role_of("slow", ["Sasa", "Hamsa"]) == "anchor"
    assert CB.role_of("steady", []) == "steady"
    assert CB.role_of("fast", ["Hamsa", "Sasa", "Gajakesari"]) == "anchor"        # strengths outweigh a fast pace
    assert CB.role_of("slow", ["Ruchaka", "Raj", "Chandra-Mangala"]) == "driver"
    assert CB.role_of("fast", ["Sasa", "Hamsa"]) == CB.role_of("fast", ["Sasa", "Hamsa"])


def test_balance_by_role_pairing_and_lens_tail():
    d, a, s = prof("Raman", "driver"), prof("Andres", "anchor"), prof("Sam", "steady")
    b = CB.balance(a, d, "cofounder", "en")                                         # order of the two does not matter
    assert b["kind"] == "split" and "Raman sets the pace" in b["line"] and "Andres tests them" in b["line"]
    assert "equity" in b["tail"]
    assert "money terms" in CB.balance(d, a, "business", "en")["tail"]
    assert CB.balance(d, prof("Dee", "driver"), "cofounder")["kind"] == "two_drivers"
    assert CB.balance(a, prof("Ann", "anchor"), "cofounder")["kind"] == "two_anchors"
    assert CB.balance(d, s, "cofounder")["kind"] == "even"


def test_timing_uses_only_money_business_and_career_for_cofounders():
    def w(s, e, label="x"): return {"start": s, "end": e, "label": label, "days": 10}
    topics = [{"topic": "money", "label": "Money", "best": [], "care": [w("2026-11-07", "2026-12-06", "Nov 7 – Dec 6")]},
              {"topic": "love", "label": "Love", "best": [w("2026-10-10", "2026-10-20")], "care": []},
              {"topic": "career", "label": "Career", "best": [], "care": [w("2026-10-08", "2027-01-05", "Oct 8 – Jan 5")]},
              {"topic": "business", "label": "Business", "best": [w("2026-12-01", "2026-12-10", "Dec 1 – Dec 10")], "care": []}]
    co = CB.timing(topics, "cofounder", "en", TODAY)
    assert [x["topic"] for x in co["careful"]] == ["career", "money"] and [x["topic"] for x in co["shared_open"]] == ["business"]
    assert "business" in co["line"] and "Dec 1" in co["line"]
    bz = CB.timing(topics, "business", "en", TODAY)
    assert [x["topic"] for x in bz["careful"]] == ["money"]                          # no career for the business lens
    none = CB.timing([topics[0]], "business", "en", TODAY)
    assert none["shared_open"] == [] and "don't share an open window" in none["line"]


def test_donts_are_three_at_most_and_honest():
    careful = [{"range": "Nov 7 – Dec 6", "label": "Money"}]
    assert CB.donts(careful, [prof("A", "driver"), prof("B", "anchor")], "en")[0].startswith("Don't sign or commit big money during Nov 7")
    assert len(CB.donts(careful, [prof("A", "driver", watch=["x"])], "en")) == 3
    calm = CB.donts([], [prof("A", "anchor"), prof("B", "anchor")], "en")
    assert len(calm) == 2 and "Check the Windows tab" in calm[0] and "heat of the moment" not in " ".join(calm)


def test_build_shape_and_the_honesty_note_never_predicts():
    me, other = prof("Raman", "driver"), prof("Andres", "anchor", shift={"on": "2027-06-05", "label": "Jun 5, 2027", "to": "discipline and time"})
    b = CB.build(me, other, "cofounder", [], {"badge": "MIXED", "score": 58, "headline": "h"}, [{"area": "communication"}], "en", TODAY)
    assert set(b) == {"lens", "verdict", "phase", "fit", "people", "balance", "timing", "donts", "moves", "note"}
    assert [p["first_name"] for p in b["people"]] == ["Raman", "Andres"]
    assert b["timing"]["shifts"][0]["line"] == "Andres moves into a season of discipline and time on Jun 5, 2027."
    assert "does not predict funding" in b["note"]


def test_lens_for_is_cofounder_and_business_only():
    assert CB.lens_for("cofounder") == "cofounder" and CB.lens_for("business") == "business"
    for rel in ("friend", "spouse", "employee", "boss", "advisor", "parent", None):
        assert CB.lens_for(rel) is None


def test_all_copy_in_four_languages_without_jargon_or_predictions():
    def strings(x):
        if isinstance(x, str): yield x
        elif isinstance(x, dict):
            for v in x.values(): yield from strings(v)
    for table in CB.TEXTS:
        assert set(table) >= set(LANGS), table
        for s in strings(table):
            assert not _JARGON.search(s), s
    for t in (CB.PACE_LINE, CB.ROLE_LINE, CB.ROLE_LABEL, CB.MODE_LINE):
        for lang in LANGS:
            assert t[lang].keys() == t["en"].keys()
    for table in CB.TEXTS:
        if table is CB.NOTE:
            continue                                  # the disclaimer itself names what we do NOT claim
        for s in strings(table):
            assert not _PREDICT.search(s), s


# ── real charts ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def two():
    from test_topic_engine import _real_ctx
    return _real_ctx("1985-03-15", "08:30"), _real_ctx("1990-10-15", "14:10")


def test_profile_on_real_charts_is_deterministic_plain_and_shows_only_work_relevant_cautions(two):
    for lang in LANGS:
        for c in two:
            p1 = CB.profile(c.chart_data, c.dashas, "Raman", lang, TODAY)
            assert p1 == CB.profile(c.chart_data, c.dashas, "Raman", lang, TODAY)
            assert p1["role"] in ("driver", "anchor", "steady") and p1["how_you_work"]
            blob = json.dumps(p1, ensure_ascii=False)
            assert not _JARGON.search(blob), _JARGON.search(blob).group(0)
            assert "emotional support" not in blob.lower()
            for w in p1["watch_for"]:
                assert w["title"]
    p = CB.profile({"yogas": [{"name": "Kemadruma Yoga (Moon)", "strength": "strong"},
                              {"name": "Grahan Yoga (Sun-Rahu)", "strength": "moderate"}]}, {}, "X", "en", TODAY)
    assert [w["title"] for w in p["watch_for"]] == ["Watch pressured, ego-driven calls"] and p["watch_for_none"] is None
    q = CB.profile({"yogas": [{"name": "Kemadruma Yoga (Moon)", "strength": "strong"}]}, {}, "X", "en", TODAY)
    assert q["watch_for"] == [] and q["watch_for_none"] == "Nothing flagged in the chart."


# ── HTTP ─────────────────────────────────────────────────────────────────────
from test_circle_routes import AUTH, env, make_pair  # noqa: E402,F401
from test_circle import A, B  # noqa: E402,F401

STUB = {"score": 58, "badge": "MIXED", "headline": "h", "summary": "s", "watch_points": [], "catalysts": [],
        "confidence": None, "timing": None,
        "layers": [{"key": "communication", "label": "C", "score": 23, "status": "friction", "status_label": "Friction",
                    "headline": "h", "detail": "d"}]}
BRIEF = {"lens": "cofounder", "fit": {"badge": "MIXED"}, "people": [], "balance": {}, "timing": {}, "donts": [], "moves": [], "note": "n"}


def both_on(c):
    for me, other, who in ((A, B, "uA"), (B, A, "uB")):
        c.put(f"/api/v1/circle/{me}/sharing/{other}", json={"share_reading": True}, headers=AUTH[who])


def test_brief_only_for_cofounder_and_business_and_only_when_both_on(env, monkeypatch):
    c, db, main = env
    monkeypatch.setattr(main, "_circle_reading_compute", lambda *a: dict(STUB))
    monkeypatch.setattr(main, "_circle_brief_compute", lambda *a: dict(BRIEF))
    make_pair(c, db, relation="cofounder")
    off = c.get(f"/api/v1/circle/{A}/pair/{B}/reading", headers=AUTH["uA"]).json()
    assert off["state"] == "off" and off["reading"] is None                          # no brief before both opt in
    c.put(f"/api/v1/circle/{A}/sharing/{B}", json={"share_reading": True}, headers=AUTH["uA"])
    assert c.get(f"/api/v1/circle/{A}/pair/{B}/reading", headers=AUTH["uA"]).json()["reading"] is None
    c.put(f"/api/v1/circle/{B}/sharing/{A}", json={"share_reading": True}, headers=AUTH["uB"])
    r = c.get(f"/api/v1/circle/{A}/pair/{B}/reading", headers=AUTH["uA"]).json()["reading"]
    assert r["brief"]["lens"] == "cofounder" and r["moves"] is not None
    c.post(f"/api/v1/circle/{A}/pair/{B}/leave", headers=AUTH["uA"])


def test_other_relations_get_no_brief_and_a_failing_brief_never_breaks_the_reading(env, monkeypatch):
    c, db, main = env
    monkeypatch.setattr(main, "_circle_reading_compute", lambda *a: dict(STUB))
    monkeypatch.setattr(main, "_circle_brief_compute", lambda *a: dict(BRIEF))
    make_pair(c, db, relation="friend"); both_on(c)
    assert "brief" not in c.get(f"/api/v1/circle/{A}/pair/{B}/reading", headers=AUTH["uA"]).json()["reading"]
    c.post(f"/api/v1/circle/{A}/pair/{B}/leave", headers=AUTH["uA"])
    make_pair(c, db, relation="business"); both_on(c)
    def boom(*a): raise RuntimeError("down")
    monkeypatch.setattr(main, "_circle_brief_compute", boom)
    r = c.get(f"/api/v1/circle/{A}/pair/{B}/reading", headers=AUTH["uA"])
    assert r.status_code == 200 and r.json()["reading"]["score"] == 58 and "brief" not in r.json()["reading"]


def test_real_engine_brief_end_to_end_on_two_charts(env, monkeypatch, two):
    c, db, main = env
    a, b = two
    monkeypatch.setattr(main, "_circle_reading_compute", lambda *a_: dict(STUB))
    monkeypatch.setattr(main, "_topic_ctx_load", lambda cid: (a if cid == A else b, {}))
    monkeypatch.setattr(main, "get_dashas_for_chart", lambda cid: (a if cid == A else b).dashas)
    for cid, nm in ((A, "Raman"), (B, "Andres")):
        next(x for x in db.rows("charts") if x["id"] == cid)["chart_data"] = (a if cid == A else b).chart_data
    main._CIRCLE_WIN_CACHE.clear()
    make_pair(c, db, relation="cofounder"); both_on(c)
    r = c.get(f"/api/v1/circle/{A}/pair/{B}/reading?language=en", headers=AUTH["uA"]).json()["reading"]["brief"]
    assert [p["first_name"] for p in r["people"]] == ["Raman", "Aarav"] and r["balance"]["line"] and r["donts"]
    assert r["note"].startswith("This describes") and not _PREDICT.search(json.dumps({k: v for k, v in r.items() if k != "note"}))
