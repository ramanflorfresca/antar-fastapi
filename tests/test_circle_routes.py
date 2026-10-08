"""Circle HTTP contract, end to end against a fake database: auth, the three-state list, the
public landing, guest + signed-in accept, the shared page (privacy), sharing, leave, fail-open."""
import sys
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from circle_fakedb import DB  # noqa: E402
from test_circle import A, B, X, TODAY, seed  # noqa: E402

from antar_engine import chart_claim, topic_checkback as tcb


def d(n):
    return TODAY + timedelta(days=n)


WINS = {
    A: {"open": [{"start": d(2), "end": d(9), "confidence": "high"}], "care": [{"start": d(15), "end": d(18), "confidence": "medium"}]},
    B: {"open": [{"start": d(5), "end": d(12), "confidence": "medium"}], "care": []},
    X: {"open": [], "care": []},
}
AUTH = {"uA": {"Authorization": "Bearer uA"}, "uB": {"Authorization": "Bearer uB"}}


@pytest.fixture
def env(monkeypatch):
    import main
    db = seed()
    monkeypatch.setattr(main, "supabase", db)
    monkeypatch.setattr(main, "_st_identity", lambda a: ((a or "").replace("Bearer ", "") or None, None))
    monkeypatch.setattr(main, "_prac_local_date", lambda tz=None: TODAY)
    monkeypatch.setattr(tcb, "is_demo", lambda sb, cid: False)
    monkeypatch.setattr(main, "_compat_partner_allowed", lambda a, b: True)
    monkeypatch.setattr(main, "_network_today_glance",
                        lambda cid, lang="en": {"available": True, "band": "steady", "direction": "quiet",
                                                "one_line": "A steady day for them."})
    monkeypatch.setattr(main, "get_network", lambda cid, lang="en": {"people": []})

    def fake_windows(chart_id, scale, today):
        w = WINS[chart_id]
        return ({t: dict(w, period_end=d(29)) for t in ("money", "career", "love", "health", "business", "peace", "family")}, d(29))
    monkeypatch.setattr(main, "_circle_windows_for", fake_windows)
    return TestClient(main.app), db, main


def make_pair(c, db, share_day=False, relation="friend"):
    r = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": relation, "first_name": "Aarav"}, headers=AUTH["uA"])
    code = r.json()["link"].rsplit("/", 1)[1]
    a = c.post(f"/api/v1/circle/invite/{code}/accept", json={"chart_id": B, "share_day": share_day}, headers=AUTH["uB"])
    assert a.status_code == 200, a.text
    return code, a.json()


def test_create_invite_needs_the_owner_and_returns_a_link(env):
    c, db, _ = env
    body = {"chart_id": A, "relation": "friend", "first_name": "Aarav"}
    assert c.post("/api/v1/circle/invites", json=body).status_code == 401
    assert c.post("/api/v1/circle/invites", json=body, headers=AUTH["uB"]).status_code == 403
    r = c.post("/api/v1/circle/invites", json=body, headers=AUTH["uA"])
    j = r.json()
    assert r.status_code == 200 and set(j) == {"invite_id", "link", "expires_at"}
    assert j["link"].startswith("https://antar.world/c/")
    assert c.post("/api/v1/circle/invites", json=dict(body, relation="zzz"), headers=AUTH["uA"]).json()["detail"]["error"] == "unknown_relation"
    assert c.post("/api/v1/circle/invites", json=dict(body, first_name=" "), headers=AUTH["uA"]).status_code == 422
    dup = c.post("/api/v1/circle/invites", json=body, headers=AUTH["uA"])
    assert dup.status_code == 409 and dup.json()["detail"]["invite_id"] == j["invite_id"]


def test_demo_chart_cannot_invite(env, monkeypatch):
    c, db, _ = env
    monkeypatch.setattr(tcb, "is_demo", lambda sb, cid: cid == A)
    r = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "friend", "first_name": "Z"}, headers=AUTH["uA"])
    assert r.status_code == 403 and r.json()["detail"]["error"] == "demo_chart"


def test_landing_is_public_and_minimal_and_404s_for_unknown(env):
    c, db, _ = env
    r = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "parent", "first_name": "Aarav", "language": "es"}, headers=AUTH["uA"])
    code = r.json()["link"].rsplit("/", 1)[1]
    g = c.get(f"/api/v1/circle/invite/{code}")
    assert g.status_code == 200
    assert set(g.json()) == {"inviter_first_name", "relation", "status", "language"}
    assert g.json()["language"] == "es" and g.json()["relation"]["label"] == "Hijo o hija"
    assert c.get("/api/v1/circle/invite/" + "Z" * 24).status_code == 404


def test_guest_invitee_accepts_with_the_claim_token_then_claims_later(env):
    c, db, main = env
    code = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "friend", "first_name": "Gita"}, headers=AUTH["uA"]).json()["link"].rsplit("/", 1)[1]
    assert c.post(f"/api/v1/circle/invite/{code}/accept", json={"chart_id": X}).status_code == 401
    assert c.post(f"/api/v1/circle/invite/{code}/accept", json={"chart_id": X, "claim_token": "wrong"}).status_code == 403
    tok = chart_claim.make_claim_token(X)
    ok = c.post(f"/api/v1/circle/invite/{code}/accept", json={"chart_id": X, "claim_token": tok, "share_day": True})
    assert ok.status_code == 200 and ok.json()["status"] == "accepted" and ok.json()["other_first_name"] == "Raman"
    again = c.post(f"/api/v1/circle/invite/{code}/accept", json={"chart_id": X, "claim_token": tok})
    assert again.status_code == 200 and again.json()["pair_id"] == ok.json()["pair_id"]
    # the guest can already see the shared page with the same token...
    pg = c.get(f"/api/v1/circle/{X}/pair/{A}", headers={"X-Claim-Token": tok})
    assert pg.status_code == 200
    # ...and a token does NOT open a chart that someone owns
    assert c.get(f"/api/v1/circle/{B}/pair/{A}", headers={"X-Claim-Token": chart_claim.make_claim_token(B)}).status_code in (401, 403)


def test_accept_errors_use_stable_codes(env):
    c, db, _ = env
    code, _ = make_pair(c, db)
    r = c.post(f"/api/v1/circle/invite/{code}/accept", json={"chart_id": X, "claim_token": chart_claim.make_claim_token(X)})
    assert r.status_code == 409 and r.json()["detail"]["error"] == "invite_used"
    code2 = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "friend", "first_name": "Me"}, headers=AUTH["uA"]).json()["link"].rsplit("/", 1)[1]
    r = c.post(f"/api/v1/circle/invite/{code2}/accept", json={"chart_id": A}, headers=AUTH["uA"])
    assert r.status_code == 409 and r.json()["detail"]["error"] == "cannot_invite_yourself"
    assert c.post(f"/api/v1/circle/invite/{'Z' * 24}/accept", json={"chart_id": B}, headers=AUTH["uB"]).status_code == 404
    assert c.post(f"/api/v1/circle/invite/{code2}/decline").json() == {"status": "ok"}
    assert c.post(f"/api/v1/circle/invite/{'Z' * 24}/decline").json() == {"status": "ok"}


def test_circle_list_shows_three_states_and_hides_a_decline(env):
    c, db, main = env
    main.get_network = lambda cid, lang="en": {"people": [
        {"connection_chart_id": "priv1", "name": "Dinesh Patel", "primary": {"compat_type": "friend", "score": 71, "session_id": "s1"},
         "today": {"available": False}, "note": "my note"},
        {"connection_chart_id": "priv2", "name": "Meera Rao", "primary": {"compat_type": "family"}, "today": {"available": False}, "note": ""}]}
    make_pair(c, db)
    sent = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "cofounder", "first_name": "Kumar", "private_chart_id": "priv2"}, headers=AUTH["uA"]).json()
    declined_code = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "friend", "first_name": "Sam"}, headers=AUTH["uA"]).json()["link"].rsplit("/", 1)[1]
    c.post(f"/api/v1/circle/invite/{declined_code}/decline")
    j = c.get(f"/api/v1/circle/{A}", headers=AUTH["uA"]).json()
    by = {(i["state"], i["first_name"]): i for i in j["circle"]}
    assert j["counts"] == {"in_circle": 1, "invite_sent": 2, "private": 1}
    assert by[("in_circle", "Aarav")]["compat_type_label"] and by[("in_circle", "Aarav")]["their_day"] == {"available": False, "shared": False}
    assert by[("invite_sent", "Kumar")]["status"] == "pending" and by[("invite_sent", "Kumar")]["invite_id"] == sent["invite_id"]
    assert by[("invite_sent", "Sam")]["status"] == "pending"                      # a decline looks like silence
    assert ("private", "Dinesh") in by and by[("private", "Dinesh")]["note"] == "my note"
    assert ("private", "Meera") not in by                                        # shown as the invite instead
    assert c.get(f"/api/v1/circle/{A}").status_code == 401
    assert c.get(f"/api/v1/circle/{A}", headers=AUTH["uB"]).status_code == 403


def test_cancel_and_resend_over_http(env):
    c, db, _ = env
    inv = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "friend", "first_name": "Aarav"}, headers=AUTH["uA"]).json()
    old = inv["link"].rsplit("/", 1)[1]
    new = c.post(f"/api/v1/circle/{A}/invites/{inv['invite_id']}/resend", headers=AUTH["uA"]).json()
    assert new["link"] != inv["link"] and c.get(f"/api/v1/circle/invite/{old}").status_code == 404
    assert c.post(f"/api/v1/circle/{A}/invites/{inv['invite_id']}/resend", headers=AUTH["uB"]).status_code == 403
    assert c.delete(f"/api/v1/circle/{A}/invites/{inv['invite_id']}", headers=AUTH["uA"]).json() == {"cancelled": True}
    assert c.get(f"/api/v1/circle/invite/{new['link'].rsplit('/', 1)[1]}").json()["status"] == "expired"


def test_both_sides_get_the_same_windows_and_only_the_pair_layer(env):
    c, db, _ = env
    make_pair(c, db)
    ja = c.get(f"/api/v1/circle/{A}/pair/{B}?language=en", headers=AUTH["uA"]).json()
    jb = c.get(f"/api/v1/circle/{B}/pair/{A}?language=en", headers=AUTH["uB"]).json()
    assert ja["topics"] == jb["topics"] and ja["headline"] == jb["headline"]
    t = next(x for x in ja["topics"] if x["topic"] == "money")
    assert [(w["start"], w["end"]) for w in t["best"]] == [(d(5).isoformat(), d(9).isoformat())]
    assert t["best"][0]["reasoning"]["confidence"]["level"] == "medium"
    assert [(w["start"], w["end"]) for w in t["care"]] == [(d(15).isoformat(), d(18).isoformat())]
    assert ja["other_first_name"] == "Aarav" and jb["other_first_name"] == "Raman"
    assert ja["relation"]["key"] == "friend" and len(ja["ask_chips"]) == 4 and "Aarav" in ja["ask_chips"][0]["text"]
    blob = str(ja) + str(jb)
    for forbidden in ("1980", "1985", "birth", "Singh", "Kumar", "uA", "uB", "my note", "session_id"):
        assert forbidden not in blob, forbidden
    assert set(ja) >= {"pair_id", "relation", "topics", "headline", "their_day", "ask_chips", "between_us", "my_sharing"}


def test_pair_page_is_404_for_strangers_and_before_accept(env):
    c, db, _ = env
    assert c.get(f"/api/v1/circle/{A}/pair/{B}", headers=AUTH["uA"]).json()["detail"]["error"] == "not_in_circle"
    c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "friend", "first_name": "Aarav"}, headers=AUTH["uA"])
    assert c.get(f"/api/v1/circle/{A}/pair/{B}", headers=AUTH["uA"]).status_code == 404
    make_pair(c, db, relation="business")
    assert c.get(f"/api/v1/circle/{A}/pair/{B}", headers=AUTH["uB"]).status_code == 403     # not B's call for A's chart
    assert c.get(f"/api/v1/circle/{A}/pair/{B}?scale=year", headers=AUTH["uA"]).status_code == 422


def test_their_day_only_with_opt_in_and_revocable(env):
    c, db, _ = env
    make_pair(c, db, share_day=False)
    day = lambda me, other, h: c.get(f"/api/v1/circle/{me}/pair/{other}", headers=h).json()["their_day"]
    assert day(A, B, AUTH["uA"]) == {"available": False, "shared": False}
    assert c.put(f"/api/v1/circle/{B}/sharing/{A}", json={"share_day": True}, headers=AUTH["uB"]).json() == {"share_day": True}
    seen = day(A, B, AUTH["uA"])
    assert seen["shared"] is True and seen["available"] is True and seen["one_line"]
    assert day(B, A, AUTH["uB"]) == {"available": False, "shared": False}                 # A never opted in
    mine = c.get(f"/api/v1/circle/{B}/pair/{A}", headers=AUTH["uB"]).json()["my_sharing"]
    assert mine == {"share_day": True}
    assert c.put(f"/api/v1/circle/{B}/sharing/{A}", json={"share_day": False}, headers=AUTH["uB"]).json() == {"share_day": False}
    assert day(A, B, AUTH["uA"]) == {"available": False, "shared": False}
    assert c.put(f"/api/v1/circle/{A}/sharing/{B}", json={"share_day": True}, headers=AUTH["uB"]).status_code == 403
    assert c.put(f"/api/v1/circle/{A}/sharing/{X}", json={"share_day": True}, headers=AUTH["uA"]).status_code == 404


def test_viewing_the_page_records_the_shared_windows_for_both(env):
    c, db, _ = env
    make_pair(c, db)
    c.get(f"/api/v1/circle/{A}/pair/{B}", headers=AUTH["uA"])
    claims = db.rows("prediction_claims")
    assert {x["chart_id"] for x in claims} == {A, B} and {x["source"] for x in claims} == {"circle_window"}


def test_between_us_is_the_inviters_own_private_read_and_never_the_invitees(env):
    c, db, _ = env
    db.t["compatibility_sessions"] = [{"id": "s9", "chart_id_a": A, "chart_id_b": "priv9", "score": 72,
                                       "compat_type": "friend", "created_at": "2026-09-01"}]
    code = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "friend", "first_name": "Aarav", "private_chart_id": "priv9"}, headers=AUTH["uA"]).json()["link"].rsplit("/", 1)[1]
    c.post(f"/api/v1/circle/invite/{code}/accept", json={"chart_id": B}, headers=AUTH["uB"])
    mine = c.get(f"/api/v1/circle/{A}/pair/{B}", headers=AUTH["uA"]).json()["between_us"]
    assert mine["available"] is True and mine["session_id"] == "s9" and mine["source"] == "your_notes"
    assert c.get(f"/api/v1/circle/{B}/pair/{A}", headers=AUTH["uB"]).json()["between_us"] == {"available": False}


def test_leave_removes_the_page_for_both_and_keeps_charts(env):
    c, db, _ = env
    make_pair(c, db, share_day=True)
    assert c.post(f"/api/v1/circle/{B}/pair/{A}/leave", headers=AUTH["uB"]).json() == {"left": True}
    assert c.post(f"/api/v1/circle/{B}/pair/{A}/leave", headers=AUTH["uB"]).json() == {"left": True}
    assert c.get(f"/api/v1/circle/{A}/pair/{B}", headers=AUTH["uA"]).status_code == 404
    assert c.get(f"/api/v1/circle/{B}/pair/{A}", headers=AUTH["uB"]).status_code == 404
    assert [i for i in c.get(f"/api/v1/circle/{A}", headers=AUTH["uA"]).json()["circle"] if i["state"] == "in_circle"] == []
    assert len(db.rows("charts")) == 3
    assert c.post(f"/api/v1/circle/{A}/pair/{B}/leave").status_code == 401


def test_a_deleted_partner_chart_drops_out_of_the_circle_quietly(env):
    c, db, _ = env
    make_pair(c, db)
    next(x for x in db.rows("charts") if x["id"] == B)["deleted_at"] = "2026-10-07"
    assert c.get(f"/api/v1/circle/{A}/pair/{B}", headers=AUTH["uA"]).status_code == 404
    assert c.get(f"/api/v1/circle/{A}", headers=AUTH["uA"]).json()["counts"]["in_circle"] == 0


def test_every_read_fails_open_when_the_tables_are_missing(env):
    c, db, _ = env
    db.missing = {"circle_invites", "circle_pairs", "circle_sharing"}
    j = c.get(f"/api/v1/circle/{A}", headers=AUTH["uA"])
    assert j.status_code == 200 and j.json()["circle"] == []
    assert c.get("/api/v1/circle/invite/" + "Z" * 24).json()["status"] == "expired"
    assert c.get(f"/api/v1/circle/{A}/pair/{B}", headers=AUTH["uA"]).status_code == 404
    assert c.post("/api/v1/circle/invite/" + "Z" * 24 + "/decline").status_code == 200
    r = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "friend", "first_name": "Z"}, headers=AUTH["uA"])
    assert r.status_code == 503 and r.json()["detail"]["error"] == "circle_unavailable"
    assert c.post(f"/api/v1/circle/{A}/pair/{B}/leave", headers=AUTH["uA"]).status_code == 503


def test_pair_page_survives_an_engine_failure_with_an_honest_empty_page(env, monkeypatch):
    c, db, main = env
    make_pair(c, db)
    monkeypatch.setattr(main, "_circle_windows_for", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    r = c.get(f"/api/v1/circle/{A}/pair/{B}", headers=AUTH["uA"])
    assert r.status_code == 200 and r.json()["topics"] == [] and r.json()["headline"]["window"] is None


def test_pair_aware_ask_answers_from_the_overlap_only_for_circle_members(env):
    c, db, main = env
    make_pair(c, db)
    out = main._ask_pair_answer("When should Aarav and I sign the contract?", A, "en", None)
    assert out and out["subject"]["pair"] is True and out["window"]["start"] == d(5).isoformat()
    assert main._ask_pair_answer("How is Aarav doing?", A, "en", None) is None
    assert main._ask_pair_answer("When should Dinesh and I sign?", A, "en", None) is None
    c.post(f"/api/v1/circle/{A}/pair/{B}/leave", headers=AUTH["uA"])
    assert main._ask_pair_answer("When should Aarav and I sign?", A, "en", None) is None


def test_real_engine_windows_are_cacheable_and_page_has_windows(env, monkeypatch):
    """Regression (found by the live end-to-end): the windows hold dates, and the topic engine's JSON
    cache choked on them, so the pair page silently fell back to an empty page in production."""
    c, db, main = env
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from test_topic_engine import _real_ctx
    monkeypatch.undo()                      # drop the faked _circle_windows_for from the fixture
    monkeypatch.setattr(main, "supabase", db)
    monkeypatch.setattr(main, "_topic_ctx_load", lambda cid: (_real_ctx("1990-10-15", "14:10"), {}))
    main._CIRCLE_WIN_CACHE.clear()
    w1 = main._circle_windows_for(A, "month", TODAY)
    w2 = main._circle_windows_for(A, "month", TODAY)
    assert w1 is w2 and set(w1[0]) >= {"money", "love"} and isinstance(w1[1], (date, type(None)))
    page = main._circle_pair_compute(A, B, "month", "en", TODAY)
    assert page is not None and len(page["topics"]) == 7           # same chart twice = everything overlaps

def test_unknown_and_foreign_charts_are_indistinguishable(env):
    c, db, _ = env
    ghost = "00000000-0000-0000-0000-000000000000"
    # no credentials: the same 401 whether or not the chart exists
    for cid in (A, ghost):
        r = c.get(f"/api/v1/circle/{cid}")
        assert r.status_code == 401 and r.json()["detail"]["error"] == "auth_required"
    # credentials for someone else: the same 403 for a real chart and a made-up one
    real = c.get(f"/api/v1/circle/{A}", headers=AUTH["uB"])
    fake = c.get(f"/api/v1/circle/{ghost}", headers=AUTH["uB"])
    assert real.status_code == fake.status_code == 403
    assert real.json() == fake.json()


def test_failed_pair_creation_gives_the_link_back(env, monkeypatch):
    c, db, _ = env
    r = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "friend", "first_name": "Aarav"}, headers=AUTH["uA"])
    code = r.json()["link"].rsplit("/", 1)[1]
    real_table = db.table

    def flaky(name):
        q = real_table(name)
        if name == "circle_pairs":
            orig = q.insert
            def boom(p):
                raise Exception("db hiccup")
            q.insert = boom
        return q
    monkeypatch.setattr(db, "table", flaky)
    bad = c.post(f"/api/v1/circle/invite/{code}/accept", json={"chart_id": B}, headers=AUTH["uB"])
    assert bad.status_code >= 500
    monkeypatch.setattr(db, "table", real_table)
    # the link is still good: the same person can try again
    ok = c.post(f"/api/v1/circle/invite/{code}/accept", json={"chart_id": B}, headers=AUTH["uB"])
    assert ok.status_code == 200, ok.text


def test_inviting_a_private_person_keeps_the_inviters_own_read_reachable(env):
    """Invite later (or invite while keeping the reading): the private read must not vanish from the list."""
    c, db, main = env
    main.get_network = lambda cid, lang="en": {"people": [
        {"connection_chart_id": "priv2", "name": "Saransh Rao", "primary": {"compat_type": "cofounder", "score": 64, "badge": "Mixed", "session_id": "s2"},
         "today": {"available": False}, "note": "met at the summit"}]}
    sent = c.post("/api/v1/circle/invites", json={"chart_id": A, "relation": "cofounder", "first_name": "Saransh", "private_chart_id": "priv2"}, headers=AUTH["uA"])
    assert sent.status_code == 200
    items = c.get(f"/api/v1/circle/{A}", headers=AUTH["uA"]).json()["circle"]
    inv = next(i for i in items if i["state"] == "invite_sent")
    assert inv["private_read"]["session_id"] == "s2" and inv["private_read"]["badge"] == "Mixed" and inv["private_read"]["note"] == "met at the summit"
    assert not [i for i in items if i["state"] == "private"]              # shown once, as the invite
    code = sent.json()["link"].rsplit("/", 1)[1]
    c.post(f"/api/v1/circle/invite/{code}/accept", json={"chart_id": B}, headers=AUTH["uB"])
    mine = next(i for i in c.get(f"/api/v1/circle/{A}", headers=AUTH["uA"]).json()["circle"] if i["state"] == "in_circle")
    assert mine["private_read"]["session_id"] == "s2"
    theirs = next(i for i in c.get(f"/api/v1/circle/{B}", headers=AUTH["uB"]).json()["circle"] if i["state"] == "in_circle")
    assert theirs["private_read"] is None                                  # never the invitee's side
    assert "met at the summit" not in str(c.get(f"/api/v1/circle/{B}/pair/{A}", headers=AUTH["uB"]).json())
