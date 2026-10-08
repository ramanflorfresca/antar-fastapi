"""Circle: invites, consent, pair layer, overlap windows, sharing, leave, check-backs, purge."""
import logging
import re
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from circle_fakedb import DB  # noqa: E402

from antar_engine import accuracy_board as ab
from antar_engine import circle as K
from antar_engine import circle_ask as CA
from antar_engine import circle_copy as CC
from antar_engine import circle_overlap as CO
from antar_engine import topic_checkback as tcb
from antar_engine import topic_copy as C

NOW = datetime(2026, 10, 7, 9, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 7)
LANGS = ("en", "es", "pt", "hinglish")
A, B, X = "a" * 8 + "-0000-0000-0000-000000000001", "b" * 8 + "-0000-0000-0000-000000000002", "c" * 8 + "-0000-0000-0000-000000000003"

_JARGON = re.compile(
    r"\b(dasha|dasa|mahadasha|antardasha|jaimini|vimsottari|chara|malefic\w*|benefic\w*|"
    r"transits?|gochar|karakas?|lagna|nakshatra|navamsa|kendra|trikona|ascendant|houses?|"
    r"d-?\d{1,2}|sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|kundli|horoscope|"
    r"aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces|"
    r"price|pricing|premium|subscribe\w*|\$)\b", re.I)


def seed(db=None, with_charts=True):
    db = db or DB()
    if with_charts:
        db.t["charts"] = [
            {"id": A, "user_id": "uA", "name": "Raman Singh", "first_name": "Raman", "language": "en", "deleted_at": None,
             "birth_date": "1980-01-01"},
            {"id": B, "user_id": "uB", "name": "Aarav Kumar", "first_name": "Aarav", "language": "en", "deleted_at": None,
             "birth_date": "1985-05-05"},
            {"id": X, "user_id": None, "name": "Guest Gita", "first_name": "Gita", "language": "es", "deleted_at": None},
        ]
    return db


@pytest.fixture(autouse=True)
def _no_demo(monkeypatch):
    monkeypatch.setattr(tcb, "is_demo", lambda sb, cid: False)


def invite(db, **kw):
    args = dict(chart_id=A, user_id="uA", relation="friend", first_name="Aarav", language="en")
    args.update(kw)
    return K.create_invite(db, args.pop("chart_id"), args.pop("user_id"), args.pop("relation"),
                           args.pop("first_name"), args.pop("language"), now=kw.get("now") or NOW, **{
                               k: v for k, v in args.items() if k in ("private_chart_id", "position")})


# ── tokens ───────────────────────────────────────────────────────────────────
def test_code_is_unguessable_hashed_at_rest_and_link_shaped():
    db = seed()
    out = invite(db)
    code = out["code"]
    assert len(code) >= 24 and K.code_ok(code) and out["link"] == "https://antar.world/c/" + code
    stored = db.rows("circle_invites")[0]
    assert code not in str(stored) and stored["token_hash"] == K.hash_code(code)
    assert len({K.new_code() for _ in range(200)}) == 200


def test_expiry_is_about_fourteen_days_and_expired_links_are_refused():
    db = seed()
    out = invite(db)
    assert datetime.fromisoformat(out["expires_at"]) - NOW == timedelta(days=14)
    later = NOW + timedelta(days=15)
    assert K.peek_invite(db, out["code"], later)["status"] == "expired"
    with pytest.raises(K.CircleError) as e:
        K.accept_invite(db, out["code"], B, now=later)
    assert e.value.code == "invite_expired" and e.value.status == 410
    assert db.rows("circle_pairs") == []


def test_single_use_second_chart_is_refused_same_chart_is_idempotent():
    db = seed()
    code = invite(db)["code"]
    first = K.accept_invite(db, code, B, now=NOW)
    again = K.accept_invite(db, code, B, now=NOW)                 # double tap
    assert first["pair_id"] == again["pair_id"] and len(db.rows("circle_pairs")) == 1
    with pytest.raises(K.CircleError) as e:
        K.accept_invite(db, code, X, now=NOW)
    assert e.value.code == "invite_used"
    assert K.peek_invite(db, code, NOW)["status"] == "used"


def test_resend_kills_the_old_code():
    db = seed()
    out = invite(db)
    new = K.resend_invite(db, A, out["invite_id"], NOW)
    assert new["code"] != out["code"] and new["invite_id"] == out["invite_id"]
    assert K.peek_invite(db, out["code"], NOW) is None
    assert K.peek_invite(db, new["code"], NOW)["status"] == "valid"
    with pytest.raises(K.CircleError):
        for _ in range(K.MAX_RESENDS + 1):
            K.resend_invite(db, A, out["invite_id"], NOW)
    assert K.resend_invite(db, B, out["invite_id"], NOW) is None   # not the inviter's


def test_cancel_kills_the_link_and_is_idempotent_and_owner_scoped():
    db = seed()
    out = invite(db)
    assert K.cancel_invite(db, B, out["invite_id"]) is False
    assert K.cancel_invite(db, A, out["invite_id"]) is True
    assert K.cancel_invite(db, A, out["invite_id"]) is False
    assert K.peek_invite(db, out["code"], NOW)["status"] == "expired"
    assert K.list_invites(db, A, NOW) == []


def test_malformed_codes_never_touch_the_store():
    db = seed()
    for bad in ("", "short", "a/b" * 10, "x" * 200, "has space " * 3):
        assert K.peek_invite(db, bad, NOW) is None
        assert K.decline_invite(db, bad) is True


def test_raw_code_is_redacted_from_access_logs():
    assert K.redact_path("/api/v1/circle/invite/SECRETCODE12345678/accept") == "/api/v1/circle/invite/<redacted>/accept"
    assert K.redact_path("/api/v1/circle/abc/pair/def") == "/api/v1/circle/abc/pair/def"
    K.install_access_log_redaction()
    K.install_access_log_redaction()
    lg = logging.getLogger("uvicorn.access")
    assert sum(isinstance(f, K._AccessLogRedactor) for f in lg.filters) == 1
    rec = logging.LogRecord("uvicorn.access", 20, "", 0, '%s - "%s %s HTTP/%s" %d',
                            ("1.2.3.4", "GET", "/api/v1/circle/invite/SECRETCODE12345678", "1.1", 200), None)
    for f in lg.filters:
        f.filter(rec)
    assert "SECRETCODE" not in rec.getMessage()


# ── consent ──────────────────────────────────────────────────────────────────
def test_an_invite_creates_nothing_about_the_invitee():
    db = seed()
    invite(db, first_name="Dinesh Kumar")
    assert db.rows("circle_pairs") == [] and db.rows("circle_sharing") == []
    inv = db.rows("circle_invites")[0]
    assert inv["invitee_first_name"] == "Dinesh" and inv["accepted_chart_id"] is None
    assert len(db.rows("charts")) == 3          # no chart was created or touched


def test_landing_exposes_only_four_fields():
    db = seed()
    code = invite(db, relation="parent")["code"]
    v = K.peek_invite(db, code, NOW)
    assert set(v) == {"inviter_first_name", "relation", "status", "language"}
    assert v["inviter_first_name"] == "Raman" and v["status"] == "valid"
    assert v["relation"]["key"] == "child"          # what the inviter is to the invitee
    blob = str(v)
    for secret in ("1980", "uA", A, "Singh", "birth"):
        assert secret not in blob


def test_decline_records_nothing_about_who_and_looks_like_silence_to_the_inviter():
    db = seed()
    out = invite(db)
    before = [dict(r) for r in db.rows("charts")]
    assert K.decline_invite(db, out["code"]) is True
    assert K.decline_invite(db, out["code"]) is True            # idempotent
    inv = db.rows("circle_invites")[0]
    assert inv["accepted_chart_id"] is None and inv["status"] == "declined"
    assert db.rows("charts") == before and db.rows("circle_pairs") == []
    shown = K.list_invites(db, A, NOW)
    assert [i["_status"] for i in shown] == ["pending"]          # not 'declined'
    assert K.list_invites(db, A, NOW + timedelta(days=15))[0]["_status"] == "expired"
    assert K.peek_invite(db, out["code"], NOW)["status"] == "used"
    with pytest.raises(K.CircleError):
        K.accept_invite(db, out["code"], B, now=NOW)


def test_decline_of_an_unknown_or_expired_link_is_a_quiet_ok():
    db = seed()
    assert K.decline_invite(db, "Z" * 24) is True
    out = invite(db)
    assert K.decline_invite(db, out["code"]) is True


def test_nothing_is_shared_until_accept_and_accept_binds_only_the_invitees_own_chart():
    db = seed()
    code = invite(db, relation="employee")["code"]
    assert K.pair_for(db, A, B) is None
    res = K.accept_invite(db, code, B, share_day=False, now=NOW)
    p = db.rows("circle_pairs")[0]
    assert (p["chart_a"], p["chart_b"]) == (A, B)
    assert (p["relation_a_to_b"], p["relation_b_to_a"]) == ("employee", "boss")
    assert res["other_chart_id"] == A and res["other_first_name"] == "Raman"
    assert db.rows("circle_sharing") == []                       # day sharing defaults OFF


def test_abuse_cases():
    db = seed()
    code = invite(db)["code"]
    with pytest.raises(K.CircleError) as e:                       # inviting yourself
        K.accept_invite(db, code, A, now=NOW)
    assert e.value.code == "cannot_invite_yourself"
    db.t["charts"].append({"id": "own2", "user_id": "uA", "name": "Raman Two", "first_name": "Raman",
                           "deleted_at": None})
    with pytest.raises(K.CircleError) as e:                       # your own other chart
        K.accept_invite(db, code, "own2", now=NOW)
    assert e.value.code == "cannot_invite_yourself"
    with pytest.raises(K.CircleError) as e:
        K.accept_invite(db, code, "nope", now=NOW)
    assert e.value.code == "chart_not_found"
    assert db.rows("circle_pairs") == []
    K.accept_invite(db, code, B, now=NOW)
    # duplicate pair: a second invite accepted by the same person doesn't make a second pair
    code2 = invite(db, first_name="Aarav2")["code"]
    r = K.accept_invite(db, code2, B, now=NOW)
    assert len(db.rows("circle_pairs")) == 1 and r["other_chart_id"] == A


def test_accept_after_leave_does_not_resurrect_the_pair():
    db = seed()
    code = invite(db)["code"]
    K.accept_invite(db, code, B, now=NOW)
    K.leave(db, B, A)
    with pytest.raises(K.CircleError) as e:
        K.accept_invite(db, code, B, now=NOW)
    assert e.value.code == "invite_used" and db.rows("circle_pairs") == []


def test_demo_chart_can_neither_invite_nor_accept(monkeypatch):
    db = seed()
    code = invite(db)["code"]
    monkeypatch.setattr(tcb, "is_demo", lambda sb, cid: cid == B)
    with pytest.raises(K.CircleError) as e:
        K.accept_invite(db, code, B, now=NOW)
    assert e.value.code == "demo_chart" and db.rows("circle_pairs") == []


def test_rate_limits():
    db = seed()
    for i in range(K.MAX_PENDING_INVITES):
        invite(db, first_name=f"P{i}")
    with pytest.raises(K.CircleError) as e:
        invite(db, first_name="One More")
    assert e.value.code == "too_many_pending_invites" and e.value.status == 429
    db2 = seed()
    out = invite(db2, first_name="Sam")
    with pytest.raises(K.CircleError) as e:
        invite(db2, first_name="sam")
    assert e.value.code == "already_invited" and e.value.extra["invite_id"] == out["invite_id"]
    db3 = seed()
    for i in range(K.MAX_INVITES_PER_DAY):                        # cancelled ones still count for the day
        o = invite(db3, first_name=f"Q{i}")
        K.cancel_invite(db3, A, o["invite_id"])
    with pytest.raises(K.CircleError) as e:
        invite(db3, first_name="Late")
    assert e.value.code == "daily_invite_limit"


# ── overlap math ─────────────────────────────────────────────────────────────
def d(n):
    return date(2026, 10, 1) + timedelta(days=n - 1)


def run(a, b, c="high"):
    return {"start": d(a), "end": d(b), "confidence": c}


def test_best_is_the_intersection_of_both_open_runs_only():
    wa = {"open": [run(8, 14), run(20, 25)], "care": []}
    wb = {"open": [run(12, 18), run(24, 28, "low")], "care": []}
    sr = CO.shared_runs(wa, wb)
    assert [(s, e) for s, e, _ in sr["best"]] == [(d(12), d(14)), (d(24), d(25))]
    assert [c for *_, c in sr["best"]] == ["high", "low"]          # never surer than the weaker side
    for s, e, _ in sr["best"]:                                     # inside BOTH sides' runs
        assert any(r["start"] <= s and e <= r["end"] for r in wa["open"])
        assert any(r["start"] <= s and e <= r["end"] for r in wb["open"])


def test_no_overlap_says_so_and_invents_nothing():
    wa = {"open": [run(8, 10)], "care": []}
    wb = {"open": [run(15, 20)], "care": []}
    assert CO.shared_runs(wa, wb)["best"] == []
    tp = CO.build_topic("money", wa, wb, "month", "en")
    assert tp["has_overlap"] is False and tp["best"] == [] and tp["care"] == []
    assert "Nothing lines up" in tp["note"]
    page = CO.build_page({"money": wa}, {"money": wb}, "month", "en")
    assert page["headline"]["window"] is None and "No shared open window" in page["headline"]["text"]


def test_care_is_either_sides_care_run_and_best_never_sits_on_it():
    wa = {"open": [run(8, 14)], "care": [run(20, 22)]}
    wb = {"open": [run(10, 16)], "care": [run(21, 25, "medium")]}
    sr = CO.shared_runs(wa, wb)
    assert [(s, e) for s, e, _ in sr["care"]] == [(d(20), d(25))]
    for bs, be, _ in sr["best"]:
        for cs, ce, _ in sr["care"]:
            assert be < cs or ce < bs
    tp = CO.build_topic("love", wa, wb, "month", "en")
    assert tp["has_overlap"] and tp["note"] is None and tp["care"][0]["kind"] == "care"


def test_window_reasoning_has_the_topic_read_shape():
    tp = CO.build_topic("money", {"open": [run(8, 14)], "care": []}, {"open": [run(10, 20, "medium")], "care": []},
                        "season", "en")
    w = tp["best"][0]
    assert set(w["reasoning"]) == {"bullets", "based_on", "confidence"}
    assert set(w["reasoning"]["confidence"]) == {"level", "note"} and w["reasoning"]["confidence"]["level"] == "medium"
    assert all({"label", "view"} <= set(b) for b in w["reasoning"]["based_on"])
    assert (w["start"], w["end"], w["days"]) == ("2026-10-10", "2026-10-14", 5)


def test_windows_listed_are_capped_and_earliest_first():
    wa = {"open": [run(i * 3, i * 3 + 1) for i in range(1, 9)], "care": []}
    tp = CO.build_topic("money", wa, wa, "month", "en")
    assert len(tp["best"]) == CO.MAX_PER_KIND and tp["best"][0]["start"] < tp["best"][1]["start"]


# ── copy: languages, jargon ──────────────────────────────────────────────────
def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _strings(v)


def test_every_copy_table_covers_all_four_languages_and_is_jargon_free():
    for table in CC.TEXTS:
        if "en" in table:
            assert set(table) >= set(LANGS), table
        for s in _strings(table):
            assert not _JARGON.search(s), s
    for tbl in (CC.REL_NOUN, CC.BULLET, CC.CHIPS):
        for lang in LANGS:
            assert tbl[lang].keys() == tbl["en"].keys()
    for t in (CC.JOINT_QUESTION["best"], CC.JOINT_QUESTION["watch"]):
        assert set(t) == set(LANGS)


def test_hindi_and_unknown_languages_fall_back_to_english_never_half_translated():
    assert CC.lang_of("hi") == "en" and CC.lang_of("fr") == "en" and CC.lang_of(None) == "en"
    tp_hi = CO.build_topic("money", {"open": [run(8, 14)], "care": []}, {"open": [run(8, 14)], "care": []}, "month", CC.lang_of("hi"))
    assert tp_hi["best"][0]["reasoning"]["bullets"][0].startswith("You both")
    tp_es = CO.build_topic("money", {"open": [run(8, 14)], "care": []}, {"open": [run(8, 14)], "care": []}, "month", "es")
    assert tp_es["label"] == "Dinero" and tp_es["best"][0]["reasoning"]["bullets"][0].startswith("Los dos")


def test_generated_pages_are_jargon_free_in_every_language():
    wa = {t: {"open": [run(8, 14)], "care": [run(20, 22)]} for t in C.TOPIC_KEYS}
    for lang in LANGS:
        page = CO.build_page(wa, wa, "month", lang)
        for s in _strings(page):
            assert not _JARGON.search(s), (lang, s)


def test_relation_labels_reuse_the_reasons_directory():
    v = K.relation_view("child", "en")
    assert v["key"] == "child" and v["compat_type_label"] == "My child" and v["label"] == "Child"
    assert K.relation_view("advisor", "es")["label"] == "Asesor o mentor"
    assert K.normalise_relation("husband") == "spouse" and K.normalise_relation("zzz") is None
    assert CC.inverse_relation("boss") == "employee" and CC.inverse_relation("friend") == "friend"


# ── sharing + leave ──────────────────────────────────────────────────────────
def test_share_day_defaults_off_is_per_person_and_revocable():
    db = seed()
    K.accept_invite(db, invite(db)["code"], B, share_day=False, now=NOW)
    assert K.get_share(db, B, A) is False and K.get_share(db, A, B) is False
    K.set_share(db, B, A, True)
    assert K.get_share(db, B, A) is True and K.get_share(db, A, B) is False
    K.set_share(db, B, A, False)
    assert K.get_share(db, B, A) is False


def test_accept_with_share_day_records_only_the_invitees_choice():
    db = seed()
    K.accept_invite(db, invite(db)["code"], B, share_day=True, now=NOW)
    assert K.get_share(db, B, A) is True and K.get_share(db, A, B) is False


def test_leave_removes_the_pair_for_both_and_never_touches_charts():
    db = seed()
    K.accept_invite(db, invite(db)["code"], B, share_day=True, now=NOW)
    K.set_share(db, A, B, True)
    charts = [dict(c) for c in db.rows("charts")]
    assert K.leave(db, B, A) is True
    assert K.leave(db, B, A) is True                              # idempotent
    assert K.pair_for(db, A, B) is None and K.pair_for(db, B, A) is None
    assert K.list_pairs(db, A) == [] and K.list_pairs(db, B) == []
    assert db.rows("circle_sharing") == [] and db.rows("charts") == charts


# ── fail open without the tables ─────────────────────────────────────────────
def test_reads_fail_open_writes_say_unavailable_when_tables_are_missing():
    db = seed()
    db.missing = {"circle_invites", "circle_pairs", "circle_sharing"}
    assert K.list_invites(db, A) == [] and K.list_pairs(db, A) == []
    assert K.pair_for(db, A, B) is None and K.get_share(db, A, B) is False
    v = K.peek_invite(db, "Q" * 24, NOW)
    assert v["status"] == "expired" and v["inviter_first_name"] is None
    assert K.decline_invite(db, "Q" * 24) is True
    with pytest.raises(K.CircleUnavailable):
        invite(db)
    with pytest.raises(K.CircleUnavailable):
        K.accept_invite(db, "Q" * 24, B)
    assert K.purge_chart(db, A) == []


# ── purge ────────────────────────────────────────────────────────────────────
def test_purge_removes_invites_pairs_and_sharing_on_both_sides_and_spares_the_other_chart():
    db = seed()
    code = invite(db)["code"]
    K.accept_invite(db, code, B, share_day=True, now=NOW)
    K.set_share(db, A, B, True)
    invite(db, first_name="Pending")                                # a still-open invite from A
    db.t["circle_invites"].append({"id": "i9", "inviter_chart_id": X, "private_chart_id": B,
                                   "status": "pending", "token_hash": "h9"})
    assert K.purge_chart(db, B) == []
    assert db.rows("circle_pairs") == [] and db.rows("circle_sharing") == []
    assert all(i.get("accepted_chart_id") != B for i in db.rows("circle_invites"))
    assert next(i for i in db.rows("circle_invites") if i["id"] == "i9")["private_chart_id"] is None
    assert any(c["id"] == A for c in db.rows("charts"))             # A's chart untouched
    K.purge_chart(db, A)
    assert [i for i in db.rows("circle_invites") if i.get("inviter_chart_id") == A] == []


def test_account_and_chart_delete_call_the_circle_purge():
    import inspect
    import main
    assert "_circle_purge(chart_id)" in inspect.getsource(main.settings_charts_delete)
    assert "_circle_purge(_cid)" in inspect.getsource(main.delete_account)


@pytest.mark.live_db
def test_live_schema_has_every_circle_column_the_code_uses():
    import main
    cols = {
        "circle_invites": "id,inviter_chart_id,inviter_user_id,token_hash,relation_type,position,invitee_first_name,"
                          "private_chart_id,language,status,resend_count,created_at,updated_at,expires_at,accepted_chart_id",
        "circle_pairs": "id,chart_a,chart_b,invite_id,relation_a_to_b,relation_b_to_a,status,created_at",
        "circle_sharing": "chart_id,other_chart_id,share_day,updated_at",
        "charts": "id,user_id,name,first_name,language_preference,language,deleted_at",
        "compatibility_sessions": "id,score,compat_type,created_at,chart_id_a,chart_id_b",
    }
    for t, c in cols.items():
        main.supabase.table(t).select(c).limit(1).execute()


@pytest.mark.live_db
def test_live_purge_leaves_nothing_behind():
    import main
    nope = "00000000-0000-0000-0000-000000000000"
    assert main._circle_purge(nope) == []


def test_sql_file_declares_every_column_the_code_writes():
    sql = open(__file__.rsplit("/", 2)[0] + "/sql_circle.sql").read()
    for col in ("inviter_chart_id", "inviter_user_id", "token_hash", "relation_type", "position",
                "invitee_first_name", "private_chart_id", "language", "status", "resend_count", "expires_at",
                "accepted_chart_id", "chart_a", "chart_b", "invite_id", "relation_a_to_b", "relation_b_to_a",
                "share_day", "other_chart_id", "updated_at"):
        assert re.search(r"\b" + col + r"\b", sql), col
    for tbl in ("circle_invites", "circle_pairs", "circle_sharing"):
        assert f"public.{tbl}" in sql and re.search(rf"alter table public\.{tbl}\s+enable row level security", sql)
    assert "unique index" in sql and "least(chart_a" in sql


# ── joint check-backs ────────────────────────────────────────────────────────
def _page(best=((8, 14),), care=()):
    wa = {t: {"open": [run(a, b) for a, b in best], "care": [run(a, b) for a, b in care],
              "period_end": d(36)} for t in ("money",)}
    return CO.build_page(wa, wa, "month", "en")


def test_every_shared_window_is_recorded_for_both_charts_and_for_neither_on_demo(monkeypatch):
    db = seed()
    pid = "pair-1"
    page = _page(best=((14, 20),), care=((25, 27),))
    n = CO.record_joint(db, (A, B), pid, page["topics"], "month", d(37), TODAY)
    claims = db.rows("prediction_claims")
    assert n == 4 and {c["chart_id"] for c in claims} == {A, B}
    assert {c["source"] for c in claims} == {"circle_window"}
    assert {c["engines"]["topic_read"]["kind"] for c in claims} == {"best", "watch"}
    one = next(c for c in claims if c["chart_id"] == A and c["engines"]["topic_read"]["kind"] == "best")
    assert one["checkin_due_at"].startswith("2026-10-21") and one["engines"]["topic_read"]["joint"] is True
    assert CO.record_joint(db, (A, B), pid, page["topics"], "month", d(37), TODAY) == 0       # idempotent
    other_pair = CO.record_joint(db, (A, X), "pair-2", page["topics"], "month", d(37), TODAY)
    assert other_pair == 4                                                                    # a different partner is its own claim
    db2 = seed()
    monkeypatch.setattr(tcb, "is_demo", lambda sb, cid: cid == B)
    CO.record_joint(db2, (A, B), pid, page["topics"], "month", d(37), TODAY)
    assert {c["chart_id"] for c in db2.rows("prediction_claims")} == {A}


def test_windows_touching_the_moving_scan_edge_or_already_over_are_not_recorded():
    db = seed()
    page = _page(best=((30, 36),))
    assert CO.record_joint(db, (A, B), "p", page["topics"], "month", d(36), TODAY) == 0       # runs into the horizon
    old = _page(best=((1, 5),))
    assert CO.record_joint(db, (A, B), "p", old["topics"], "month", d(36), TODAY) == 0        # already over
    assert CO.record_joint(db, (A, B), "p", _page(best=((8, 14),))["topics"], "today", None, TODAY) == 0


def test_each_person_is_asked_separately_after_the_window_ends_and_answers_into_the_same_loop():
    db = seed()
    K.accept_invite(db, invite(db)["code"], B, now=NOW)
    page = _page(best=((14, 20),))
    CO.record_joint(db, (A, B), db.rows("circle_pairs")[0]["id"], page["topics"], "month", d(37), TODAY)
    before = datetime(2026, 10, 20, tzinfo=timezone.utc)
    after = datetime(2026, 10, 22, tzinfo=timezone.utc)
    assert tcb.due_items(db, A, "en", now=before) == []
    qa = tcb.due_items(db, A, "en", now=after)
    assert len(qa) == 1 and "shared" in qa[0]["question"] and "Oct 14" in qa[0]["question"]
    assert not _JARGON.search(qa[0]["question"])
    qb = tcb.due_items(db, B, "es", now=after)
    assert len(qb) == 1 and qb[0]["id"] != qa[0]["id"] and "compartida" in qb[0]["question"]
    assert tcb.record_answer(db, A, qa[0]["id"], "yes", after)["saved"] is True
    assert tcb.record_answer(db, B, qb[0]["id"], "no", after)["outcome"] == "no"
    with pytest.raises(tcb.UnknownCheckback):                      # another chart's claim
        tcb.record_answer(db, X, qa[0]["id"], "yes", after)
    assert tcb.due_items(db, A, "en", now=after) == []


def test_leaving_stops_the_shared_question_for_both():
    db = seed()
    K.accept_invite(db, invite(db)["code"], B, now=NOW)
    pid = db.rows("circle_pairs")[0]["id"]
    CO.record_joint(db, (A, B), pid, _page(best=((14, 20),))["topics"], "month", d(37), TODAY)
    after = datetime(2026, 10, 22, tzinfo=timezone.utc)
    assert len(tcb.due_items(db, B, "en", now=after, limit=3)) == 1
    K.leave(db, A, B)
    assert tcb.due_items(db, A, "en", now=after) == [] and tcb.due_items(db, B, "en", now=after) == []


def test_existing_topic_read_checkbacks_are_unaffected_by_the_circle_source():
    assert tcb.SOURCE == "topic_read" and tcb.SOURCE in tcb.SOURCES and tcb.CIRCLE_SOURCE in tcb.SOURCES


def _board_claim(i, chart, wid, outcome_for=None):
    return {"id": f"c{i}", "chart_id": chart, "source": "circle_window", "topic": "money", "window_start": "2026-10-14",
            "window_end": "2026-10-20", "checkin_due_at": "2026-10-21T00:00:00+00:00",
            "engines": {"topic_read": {"kind": "best", "scale": "month", "joint": True, "window_id": wid}}}


def test_board_counts_a_shared_window_once_and_hides_rates_on_small_n():
    claims = [_board_claim(1, A, "w1"), _board_claim(2, B, "w1")]
    outs = [{"claim_id": "c1", "outcome": "yes", "answered_at": "2026-10-22"},
            {"claim_id": "c2", "outcome": "yes", "answered_at": "2026-10-23"}]
    b = ab.build(claims, outs)
    row = next(r for r in b["engines"] if r["engine"] == "circle_window:best")
    assert row["answered"] == 1 and row["claims"] == 1            # two people, ONE window
    assert row["small_n"] is True and row["hit_rate"] is None and row["status"] == "Too few answers"
    fa = next(r for r in b["final_answers"] if r["source"] == "circle_window")
    assert fa["small_n"] is True
    split = ab.build(claims, [dict(outs[0]), {"claim_id": "c2", "outcome": "no", "answered_at": "2026-10-23"}])
    assert next(r for r in split["engines"] if r["engine"] == "circle_window:best")["answered"] == 1
    assert ab._collapse_circle(claims, {"c1": outs[0], "c2": {"outcome": "no"}})[0]["id"] == "c1"
    only_unsure = ab.build(claims, [{"claim_id": "c1", "outcome": "not_sure", "answered_at": "2026-10-22"}])
    r2 = next(r for r in only_unsure["engines"] if r["engine"] == "circle_window:best")
    assert r2["answered"] == 0 and r2["not_sure"] == 1


def test_topic_read_rows_on_the_board_are_unchanged():
    c = {"id": "t1", "chart_id": A, "source": "topic_read", "topic": "money",
         "engines": {"topic_read": {"kind": "best", "scale": "month"}}, "window_end": "2026-10-20"}
    b = ab.build([c], [{"claim_id": "t1", "outcome": "yes", "answered_at": "2026-10-22"}])
    assert [r["engine"] for r in b["engines"]] == ["topic_read:best"]


# ── pair-aware Ask ───────────────────────────────────────────────────────────
PARTNERS = [{"chart_id": B, "name": "Aarav Kumar"}]


@pytest.mark.parametrize("q,topic", [
    ("When should Aarav and I sign the contract?", "business"),
    ("When is a good time for Aarav and me to talk about money?", "money"),
    ("¿Cuándo deberíamos Aarav y yo firmar algo?", "business"),
    ("Quando eu e Aarav devemos assinar algo?", "business"),
    ("Aarav aur main paise ki baat kab karein?", "money"),
])
def test_pair_question_is_detected_in_every_language(q, topic):
    hit = CA.detect(q, PARTNERS)
    assert hit and hit["partner"]["chart_id"] == B and hit["topic"] == topic


@pytest.mark.parametrize("q", [
    "How is Aarav doing?",                       # about them alone: today's person flow
    "When should I sign the contract?",           # about me
    "Should we sign? Dinesh said yes",            # a name that is not in the circle
    "When should Aarav and Kumar and I sign?" ,
    "",
])
def test_non_pair_questions_fall_through_untouched(q):
    ps = PARTNERS if "Dinesh" not in q and "Kumar" not in q else PARTNERS + [{"chart_id": X, "name": "Kumar"}]
    assert CA.detect(q, ps) is None


def test_private_people_never_take_the_pair_path():
    assert CA.detect("When should Aarav and I sign?", []) is None


def test_two_circle_members_with_the_same_first_name_are_not_guessed():
    ps = PARTNERS + [{"chart_id": X, "name": "Aarav Mehta"}]
    assert CA.detect("When should Aarav and I sign?", ps) is None


def test_pair_answer_uses_the_shared_window_or_says_none():
    page = _page(best=((14, 20),), care=((25, 27),))
    pages = {"month": {"topics": [dict(page["topics"][0], topic="business")]}, "season": {"topics": []}}
    out = CA.answer("Aarav", "business", pages, "en")
    assert "Oct 14 – Oct 20" in out["read"] and out["window"]["start"] == "2026-10-14" and "Oct 25" in out["read"]
    assert out["subject"]["pair"] is True and out["locked"] is False
    none = CA.answer("Aarav", "money", {"month": {"topics": [CO.build_topic("money", {"open": [run(8, 9)], "care": []},
                                                                           {"open": [run(15, 16)], "care": []}, "month", "en")]},
                                        "season": {"topics": []}}, "en")
    assert none["window"] is None and "won't invent" in none["read"]
    for lang in LANGS:
        assert not _JARGON.search(CA.answer("Aarav", "money", pages, lang)["read"])
