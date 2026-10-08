"""Circle 'Our reading': second opt-in (both must be on), state machine, payload privacy, fail-open."""
import re
import sys

import pytest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from circle_fakedb import DB  # noqa: E402
from test_circle_routes import AUTH, env, make_pair  # noqa: E402,F401
from test_circle import A, B, X, seed  # noqa: E402,F401

from antar_engine import circle as K
from antar_engine import circle_reading as CR

_JARGON = re.compile(
    r"\b(dasha|dasa|mahadasha|antardasha|jaimini|vimsottari|chara|malefic\w*|benefic\w*|transits?|gochar|"
    r"karakas?|lagna|nakshatra|navamsa|kendra|trikona|ascendant|houses?|d-?\d{1,2}|"
    r"sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|aries|taurus|gemini|cancer|leo|virgo|libra|"
    r"scorpio|sagittarius|capricorn|aquarius|pisces)\b", re.I)


def test_state_machine_has_exactly_the_four_states():
    assert [CR.state_of(m, t) for m in (False, True) for t in (False, True)] == ["off", "they_on", "waiting", "on"]
    assert set(CR.STATES) == {"off", "waiting", "they_on", "on"}


def test_layer_status_uses_the_three_people_words():
    assert CR.layer_status({"passed": True, "score": 67}) == "flows"
    assert CR.layer_status({"passed": False, "score": 60}) == "needs_care"
    assert CR.layer_status({"passed": False, "score": 23}) == "friction"
    assert CR.layer_status({"passed": False, "score": None}) == "needs_care"


def test_switches_are_per_person_default_off_and_independent_of_share_day():
    db = seed()
    K.accept_invite(db, K.create_invite(db, A, "uA", "friend", "Aarav", "en")["code"], B)
    assert K.reading_state(db, A, B) == {"state": "off", "mine": False, "theirs": False}
    K.set_share(db, B, A, True)                                   # day sharing is a different switch
    assert K.reading_state(db, A, B)["state"] == "off"
    K.set_share_reading(db, A, B, True)
    assert K.reading_state(db, A, B)["state"] == "waiting" and K.reading_state(db, B, A)["state"] == "they_on"
    assert K.get_share(db, B, A) is True                          # share_day untouched by the reading switch
    K.set_share_reading(db, B, A, True)
    assert K.reading_state(db, A, B)["state"] == "on" and K.reading_state(db, B, A)["state"] == "on"
    K.set_share_reading(db, A, B, False)
    assert K.reading_state(db, A, B)["state"] == "they_on" and K.reading_state(db, B, A)["state"] == "waiting"
    assert K.get_share(db, A, B) is False


def test_a_no_is_invisible_it_reads_exactly_like_not_looked():
    db = seed()
    K.accept_invite(db, K.create_invite(db, A, "uA", "friend", "Aarav", "en")["code"], B)
    K.set_share_reading(db, B, A, True)
    K.set_share_reading(db, B, A, False)                          # turned on, then off
    seen_by_a = K.reading_state(db, A, B)
    assert seen_by_a == {"state": "off", "mine": False, "theirs": False}


def test_leave_wipes_both_switches():
    db = seed()
    K.accept_invite(db, K.create_invite(db, A, "uA", "friend", "Aarav", "en")["code"], B)
    K.set_share_reading(db, A, B, True)
    K.set_share_reading(db, B, A, True)
    K.leave(db, A, B)
    assert db.rows("circle_sharing") == []
    assert K.reading_state(db, A, B)["state"] == "off"


def test_missing_column_fails_open_and_does_not_break_share_day():
    db = seed()
    K.accept_invite(db, K.create_invite(db, A, "uA", "friend", "Aarav", "en")["code"], B)
    db.bad_cols.add(("circle_sharing", "share_reading"))          # migration not run yet
    assert K.get_share_reading(db, A, B) is False
    assert K.reading_state(db, A, B)["state"] == "off"
    assert K.set_share(db, A, B, True) is True and K.get_share(db, A, B) is True
    with pytest.raises(K.CircleUnavailable):
        K.set_share_reading(db, A, B, True)


def test_purge_removes_reading_switches_too():
    db = seed()
    K.accept_invite(db, K.create_invite(db, A, "uA", "friend", "Aarav", "en")["code"], B)
    K.set_share_reading(db, A, B, True)
    K.purge_chart(db, B)
    assert db.rows("circle_sharing") == [] and db.rows("circle_pairs") == []


# ── payload: the real engine on two real charts ──────────────────────────────
@pytest.fixture(scope="module")
def two_charts():
    from test_topic_engine import _real_ctx
    return _real_ctx("1985-03-15", "08:30"), _real_ctx("1990-10-15", "14:10")


def _build(main, a, b, reason="business", na="Raman", nb="Andres"):
    return main._circle_reading_build(a.chart_data, a.dashas, b.chart_data, b.dashas, "1985-03-15", "1990-10-15",
                                      "male", "male", reason, na, nb, "en")


def test_reading_payload_is_pair_level_jargon_free_and_deterministic(two_charts):
    import json
    import main
    a, b = two_charts
    r1, r2 = _build(main, a, b), _build(main, a, b)
    assert r1 == r2
    assert {"score", "badge", "headline", "summary", "layers", "watch_points", "confidence", "timing"} <= set(r1)
    assert len(r1["layers"]) >= 5 and {l["status"] for l in r1["layers"]} <= {"flows", "needs_care", "friction"}
    assert all(l["status_label"] for l in r1["layers"]) and 0 <= r1["score"] <= 100
    blob = json.dumps(r1)
    assert not _JARGON.search(blob), _JARGON.search(blob).group(0)
    for leak in ("1985", "1990", "08:30", "14:10", "birth", "latitude", "chart_id", "Aries", "lagna"):
        assert leak not in blob, leak
    assert "Raman" in blob and "Andres" in blob


def test_directional_relations_read_from_the_viewers_side(two_charts):
    import main
    a, b = two_charts
    as_boss = _build(main, a, b, reason="employee")
    as_report = _build(main, a, b, reason="boss-or-manager")
    assert as_boss["layers"] and as_report["layers"]              # both build; direction lives in the engine
    from antar_engine import people_links as PL
    assert CR.reason_for("boss", PL) == "boss-or-manager" and CR.reason_for("friend", PL) == "friend"


# ── HTTP ─────────────────────────────────────────────────────────────────────
STUB = {"score": 59, "badge": "MIXED", "headline": "h", "summary": "s", "layers": [], "watch_points": [],
        "catalysts": [], "confidence": None, "timing": None}


def put(c, me, other, body, who):
    return c.put(f"/api/v1/circle/{me}/sharing/{other}", json=body, headers=AUTH[who])


def get(c, me, other, who, **kw):
    return c.get(f"/api/v1/circle/{me}/pair/{other}/reading", headers=AUTH[who], **kw).json()


def test_reading_endpoint_shows_nothing_until_both_are_on(env, monkeypatch):
    c, db, main = env
    monkeypatch.setattr(main, "_circle_reading_compute", lambda *a: dict(STUB))
    make_pair(c, db)
    off = get(c, A, B, "uA")
    assert off["state"] == "off" and off["reading"] is None and off["other_first_name"] == "Aarav"
    assert put(c, A, B, {"share_reading": True}, "uA").json() == {"share_day": False, "share_reading": True}
    a_side, b_side = get(c, A, B, "uA"), get(c, B, A, "uB")
    assert (a_side["state"], a_side["reading"]) == ("waiting", None)
    assert (b_side["state"], b_side["reading"]) == ("they_on", None)
    assert b_side["theirs"] is True and a_side["theirs"] is False   # only a yes is visible
    put(c, B, A, {"share_reading": True}, "uB")
    both_a, both_b = get(c, A, B, "uA"), get(c, B, A, "uB")
    assert both_a["state"] == both_b["state"] == "on" and both_a["reading"]["score"] == 59
    put(c, B, A, {"share_reading": False}, "uB")                     # either side off -> gone for both
    assert get(c, A, B, "uA")["reading"] is None and get(c, B, A, "uB")["reading"] is None
    assert get(c, A, B, "uA")["state"] == "they_on" or get(c, A, B, "uA")["state"] == "waiting"


def test_reading_endpoint_is_owner_only_and_pair_only(env, monkeypatch):
    c, db, main = env
    monkeypatch.setattr(main, "_circle_reading_compute", lambda *a: dict(STUB))
    assert c.get(f"/api/v1/circle/{A}/pair/{B}/reading", headers=AUTH["uA"]).status_code == 404   # no pair yet
    make_pair(c, db)
    assert c.get(f"/api/v1/circle/{A}/pair/{B}/reading").status_code == 401
    assert c.get(f"/api/v1/circle/{A}/pair/{B}/reading", headers=AUTH["uB"]).status_code == 403
    assert c.get(f"/api/v1/circle/{A}/pair/{X}/reading", headers=AUTH["uA"]).status_code == 404


def test_put_sharing_stays_backward_compatible_and_validates(env):
    c, db, main = env
    make_pair(c, db)
    assert put(c, A, B, {"share_day": True}, "uA").json() == {"share_day": True, "share_reading": False}
    assert put(c, A, B, {}, "uA").status_code == 422
    assert put(c, A, B, {"share_day": False, "share_reading": True}, "uA").json() == {"share_day": False, "share_reading": True}
    assert put(c, A, X, {"share_reading": True}, "uA").status_code == 404


def test_pair_page_carries_the_reading_state_without_the_reading(env, monkeypatch):
    c, db, main = env
    monkeypatch.setattr(main, "_circle_reading_compute", lambda *a: (_ for _ in ()).throw(AssertionError("not on yet")))
    make_pair(c, db)
    put(c, B, A, {"share_reading": True}, "uB")
    page = c.get(f"/api/v1/circle/{A}/pair/{B}", headers=AUTH["uA"]).json()
    assert page["reading"] == {"state": "they_on", "mine": False, "theirs": True}
    assert page["my_sharing"] == {"share_day": False, "share_reading": False}
    assert "score" not in str(page["reading"])


def test_reading_leave_and_fail_open(env, monkeypatch):
    c, db, main = env
    monkeypatch.setattr(main, "_circle_reading_compute", lambda *a: dict(STUB))
    make_pair(c, db)
    put(c, A, B, {"share_reading": True}, "uA"); put(c, B, A, {"share_reading": True}, "uB")
    assert get(c, A, B, "uA")["state"] == "on"
    c.post(f"/api/v1/circle/{A}/pair/{B}/leave", headers=AUTH["uA"])
    assert c.get(f"/api/v1/circle/{A}/pair/{B}/reading", headers=AUTH["uA"]).status_code == 404
    make_pair(c, db)                                                # a new pair starts from off
    assert get(c, A, B, "uA")["state"] == "off"
    db.bad_cols.add(("circle_sharing", "share_reading"))
    assert get(c, A, B, "uA")["state"] == "off"                    # column missing: fails open to off
    assert put(c, A, B, {"share_reading": True}, "uA").status_code == 503
    assert put(c, A, B, {"share_day": True}, "uA").json() == {"share_day": True, "share_reading": False}   # day switch unaffected
    assert c.get(f"/api/v1/circle/{A}/pair/{B}", headers=AUTH["uA"]).status_code == 200


def test_a_failed_compute_returns_state_on_with_no_reading_not_a_500(env, monkeypatch):
    c, db, main = env
    def boom(*a): raise RuntimeError("engine down")
    monkeypatch.setattr(main, "_circle_reading_compute", boom)
    make_pair(c, db)
    put(c, A, B, {"share_reading": True}, "uA"); put(c, B, A, {"share_reading": True}, "uB")
    r = c.get(f"/api/v1/circle/{A}/pair/{B}/reading", headers=AUTH["uA"])
    assert r.status_code == 200 and r.json()["state"] == "on" and r.json()["reading"] is None


def test_symmetrize_gives_both_people_the_same_numbers_and_rederives_status():
    from antar_engine import compatibility_reasons as R
    mk = lambda sc, l1, l2: {"score": sc, "badge": "X", "headline": "h", "layers": [
        {"key": "soul", "score": l1, "status": CR.layer_status({"passed": l1 >= 65, "score": l1}), "status_label": "Flows" if l1 >= 65 else "Needs care"},
        {"key": "comm", "score": l2, "status": "friction", "status_label": "Friction"}]}
    v, w = mk(63, 70, 30), mk(66, 62, 36)
    a = CR.symmetrize(v, w, R.LAYER_PASS_THRESHOLD, R.badge)
    b = CR.symmetrize(w, v, R.LAYER_PASS_THRESHOLD, R.badge)            # the other person's order
    assert a["score"] == b["score"] == 64 and a["badge"] == b["badge"]
    assert [l["score"] for l in a["layers"]] == [l["score"] for l in b["layers"]] == [66, 33]
    assert [l["status"] for l in a["layers"]] == [l["status"] for l in b["layers"]] == ["flows", "friction"]
    assert a["layers"][0]["status_label"] == "Flows" and v["score"] == 63        # input untouched


def test_real_charts_read_identically_from_either_side(two_charts):
    import main
    a, b = two_charts
    ra = main._circle_reading_build(a.chart_data, a.dashas, b.chart_data, b.dashas, "1985-03-15", "1990-10-15",
                                    "male", "female", "friend", "Raman", "Shashi", "en")
    rb = main._circle_reading_build(b.chart_data, b.dashas, a.chart_data, a.dashas, "1990-10-15", "1985-03-15",
                                    "female", "male", "friend", "Shashi", "Raman", "en")
    assert ra["score"] == rb["score"] and ra["badge"] == rb["badge"]
    assert [(l["key"], l["score"], l["status"]) for l in ra["layers"]] == [(l["key"], l["score"], l["status"]) for l in rb["layers"]]


def test_reading_endpoint_returns_practical_moves_in_the_viewers_language(env, monkeypatch):
    c, db, main = env
    stub = dict(STUB, layers=[
        {"key": "communication", "label": "Communication", "score": 23, "status": "friction", "status_label": "Friction",
         "headline": "h", "detail": "d"},
        {"key": "friction", "label": "Friction", "score": 84, "status": "flows", "status_label": "Flows",
         "headline": "h", "detail": "d"}])
    monkeypatch.setattr(main, "_circle_reading_compute", lambda *a: dict(stub))
    make_pair(c, db, relation="business")
    put(c, A, B, {"share_reading": True}, "uA"); put(c, B, A, {"share_reading": True}, "uB")
    r = c.get(f"/api/v1/circle/{A}/pair/{B}/reading?language=en", headers=AUTH["uA"]).json()["reading"]
    assert [m["area"] for m in r["moves"]] == ["communication"] and "writing" in r["moves"][0]["text"]
    es = c.get(f"/api/v1/circle/{A}/pair/{B}/reading?language=es", headers=AUTH["uA"]).json()["reading"]
    assert es["moves"][0]["text"].startswith("Dejen las decisiones por escrito") or es["moves"][0]["text"].startswith("Cuando")
