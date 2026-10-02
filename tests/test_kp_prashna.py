"""Ask → Yes/No on the KP Prashna engine (2026-10-02).

Spec: Antar.world/SPEC_ASK_YESNO_KP_PRASHNA.md. The pure pieces (question
routing, horizon, number, the lean rule table, the calibration marker and its
scorer) are tested without an ephemeris; the cast itself is tested only when
swisseph is installed.
"""
from datetime import date, datetime, timezone

import pytest

from antar_engine.kp.kp_prashna import (
    ASTROLOGER_SEAT, calibration_marker, classify_question, combine_lean,
    parse_horizon_days, resolve_number, score_yesno_calibration, verify_after,
    window_label, _parse_marker,
)
from antar_engine.prediction_tracker import _feedback_ui


@pytest.mark.parametrize("q,qt", [
    ("Will I get my funding in the next 30 days?", "gain"),
    ("Will the investor say yes?", "gain"),
    ("Will I get this job?", "job_new"),
    ("Will I land the job at Stripe?", "job_new"),
    ("Will I get a raise this year?", "promotion"),
    ("Will the deal close?", "deal_closes"),
    ("Will my divorce go through?", "loss"),
    ("Will I win the court case?", "litigation_win"),
    ("¿Me van a dar el trabajo este mes?", "job_new"),
    ("Vou conseguir o emprego?", "job_new"),
    ("Kya meri shaadi is saal hogi?", "marriage"),
    ("Kya funding milegi?", "gain"),
    ("Will my visa get approved?", "foreign_travel"),
    ("Will I move abroad this year?", "foreign_travel"),
    ("Will I pass the exam?", "education"),
    ("Will I get admission to Columbia?", "education"),
    ("Will we have a baby?", "childbirth"),
    ("Will my ex come back?", "reunion"),
    ("Will I find my lost ring?", "lost_found"),
    ("Will I buy a car?", "property"),
])
def test_routing(q, qt):
    assert classify_question(q)[0] == qt


def test_word_start_matching_not_substring():
    # "around" must not read as a funding "round"; "just in case" is not a lawsuit
    # — both fall to the KP generic, never to a named matter.
    assert classify_question("Should I travel around Europe?") == ("gain", None, True)
    assert classify_question("Is it worth keeping just in case?") == ("gain", None, True)


@pytest.mark.parametrize("q", [
    "Will I win at the casino tonight?", "Will my bet pay off?",
    "¿Voy a ganar la lotería?", "Kya satta lagega?",
])
def test_gambling_never_gets_a_kp_verdict(q):
    assert classify_question(q)[0] is None


def test_gambling_filter_does_not_eat_ordinary_words():
    assert classify_question("Will my job situation get better?")[0] == "job_new"
    assert classify_question("Will I get the interview slot?")[0] == "job_new"


def test_every_question_is_kp_generic_when_unnamed():
    # Owner, 2026-10-02: Prashna is KP end to end — nothing falls to classic.
    for q in ("Will it work out?", "Should I do it?", "Is this the right path?"):
        assert classify_question(q) == ("gain", None, True)
    assert classify_question("   ")[0] is None


def test_shown_window_is_horary_only():
    from antar_engine.kp.kp_prashna import shown_window
    w = {"start": "2026-10-10", "end": "2026-10-20", "label": "x", "ruler_ok": True}
    for lean in ("yes", "not_now", "conditional"):
        assert shown_window({"available": True, "lean": lean, "window": w}) == w
    assert shown_window({"available": True, "lean": "no", "window": w}) is None
    assert shown_window({"available": False}) is None


@pytest.mark.parametrize("q,days", [
    ("funding in the next 30 days?", 30),
    ("in 2 weeks", 14),
    ("in the next 3 months", 90),
    ("today?", 1),
    ("this month?", 31),
    ("¿este mes?", 31),
    ("próximos 10 días", 10),
    ("is saal hogi?", 365),
    ("will I get it?", None),
])
def test_horizon(q, days):
    assert parse_horizon_days(q) == days


def test_number_resolution():
    assert resolve_number(74, "") == 74
    assert resolve_number(None, "Will the deal close? number 112") == 112
    assert resolve_number(None, "número 9") == 9
    assert resolve_number(0, "") is None
    assert resolve_number(250, "") is None
    assert resolve_number(None, "will it close in 30 days") is None


TODAY = date(2026, 10, 2)
WIN_LATE = {"start": "2026-12-01", "end": "2026-12-20", "ruler_ok": True}
WIN_SOON = {"start": "2026-10-10", "end": "2026-10-20", "ruler_ok": True}


@pytest.mark.parametrize("horary,natal,win,hz,lean", [
    ("no", "yes", WIN_SOON, None, "no"),           # natal never upgrades a no
    ("conditional", "yes", WIN_SOON, None, "conditional"),
    ("yes", "no", WIN_SOON, None, "conditional"),  # not promised → softened
    ("yes", None, WIN_SOON, None, "yes"),          # natal unknown → horary stands
    ("yes", "yes", WIN_LATE, 30, "not_now"),       # comes, later than asked
    ("yes", "yes", WIN_SOON, 30, "yes"),
    ("yes", "yes", {**WIN_LATE, "ruler_ok": False}, 30, "yes"),
])
def test_lean_table(horary, natal, win, hz, lean):
    assert combine_lean(horary, natal, win, hz, TODAY) == lean


def test_window_label():
    assert window_label("2026-10-04", "2026-10-10") == "Oct 4 – Oct 10, 2026"
    assert window_label("2026-12-28", "2027-01-05") == "Dec 28, 2026 – Jan 5, 2027"
    assert window_label(None, None) is None


def test_verify_after_uses_horizon_then_window_then_30d():
    now = datetime(2026, 10, 2, tzinfo=timezone.utc)
    assert verify_after({"horizon_days": 7}, now).date() == date(2026, 10, 9)
    assert verify_after({"window": {"end": "2026-10-20"}}, now).date() == date(2026, 10, 21)
    assert verify_after(None, now).date() == date(2026, 11, 1)
    assert verify_after({"horizon_days": 365}, now).date() == date(2027, 1, 30)  # clamp 120


def test_marker_roundtrip():
    kp = {"lean": "not_now", "confidence": 2, "natal": "yes", "question_type": "gain",
          "number": 74, "method": "kp_number", "horizon_days": 30,
          "window": {"start": "2026-12-01", "end": "2026-12-20"},
          "debug": {"horary_verdict": "yes"}}
    m = _parse_marker(calibration_marker(kp, "NO", "classic", "2026-10-02T15:30:00+00:00"))
    assert m["kp"] == "not_now" and m["tajik"] == "NO" and m["num"] == "74"
    assert m["win"] == "2026-12-01..2026-12-20" and m["engine"] == "classic"
    # an unmappable question still logs the classic verdict for the head-to-head
    assert _parse_marker(calibration_marker(None, "YES", "classic", "x"))["tajik"] == "YES"


class _FakeSB:
    def __init__(self, rows):
        self.rows = rows

    def table(self, _):
        return self

    def select(self, *_):
        return self

    def eq(self, *_):
        return self

    def execute(self):
        return type("R", (), {"data": self.rows})()


def _row(kp, tajik, status):
    return {"correlation_key": calibration_marker(
        {"lean": kp, "debug": {}}, tajik, "classic", "t"), "feedback_status": status}


def test_calibration_head_to_head():
    rows = [
        _row("yes", "NO", "yes"),          # KP hit, classic miss
        _row("no", "NO", "no"),            # both hit
        _row("not_now", "YES", "yes"),     # KP miss, classic hit
        _row("conditional", "YES", "no"),  # KP no claim, classic miss
        _row("yes", "YES", "pending"),     # unanswered → ignored
        {"correlation_key": "daily-2026-10-01", "feedback_status": "yes"},  # not ours
    ]
    r = score_yesno_calibration(_FakeSB(rows))
    assert r["answered"] == 4
    assert r["kp"] == {"n": 3, "hits": 2, "hit_rate": 0.667}
    assert r["classic"] == {"n": 4, "hits": 2, "hit_rate": 0.5}
    assert r["kp_conditional"] == 1 and r["kp_ready"] is False


def test_feedback_card_asks_did_it_happen():
    ui = _feedback_ui("yesno", "es")
    assert ui["style"] == "happened"
    assert [o["value"] for o in ui["options"]] == ["yes", "no"]
    assert _feedback_ui("career", "en")["style"] == "truth"   # unchanged


def test_seat_clock_is_dst_aware():
    from antar_engine.kp.kp_prashna import _seat_local
    assert _seat_local(datetime(2026, 7, 1, 16, tzinfo=timezone.utc))[1] == -4.0   # EDT
    assert _seat_local(datetime(2026, 12, 1, 17, tzinfo=timezone.utc)) == (
        datetime(2026, 12, 1, 12, 0), -5.0)                                          # EST


def test_seat_is_edgewater():
    assert ASTROLOGER_SEAT["name"] == "Edgewater, NJ"
    assert ASTROLOGER_SEAT["tz"] == "America/New_York"


# ── ephemeris-backed (skipped where swisseph isn't installed) ───────────────
swe = pytest.importorskip("swisseph")


def _natal_record():
    from antar_engine.kp.kp_chart import compute_kp_chart
    n = compute_kp_chart("1974-11-26", "11:59", 28.6139, 77.2090, tz_offset=5.5)
    return {"chart_data": {"birth_jd": n["birth_jd"]},
            "latitude": 28.6139, "longitude": 77.2090}


NOW = datetime(2026, 10, 2, 15, 30, tzinfo=timezone.utc)


def test_cast_is_deterministic_and_well_formed():
    from antar_engine.kp.kp_prashna import kp_prashna
    q = "Will I get my funding in the next 30 days?"
    a = kp_prashna(_natal_record(), q, number=74, now_utc=NOW)
    b = kp_prashna(_natal_record(), q, number=74, now_utc=NOW)
    assert a["available"] and a == b
    assert a["method"] == "kp_number" and a["number"] == 74
    assert a["lean"] in ("yes", "not_now", "conditional", "no")
    assert a["verdict"] == ("YES" if a["lean"] == "yes" else "NO")
    assert 0 <= a["confidence"] <= 3 and a["horizon_days"] == 30


def test_number_changes_the_chart_moment_does_not_need_one():
    from antar_engine.kp.kp_prashna import kp_prashna
    q = "Will I get this job?"
    m = kp_prashna(_natal_record(), q, now_utc=NOW)
    assert m["available"] and m["method"] == "kp_moment" and m["number"] is None
    csls = {kp_prashna(_natal_record(), q, number=n, now_utc=NOW)["debug"]["csl"]
            for n in (1, 60, 120, 180, 249)}
    assert len(csls) > 1   # the number really fixes the ascendant


def test_needs_reconfirm_skips_natal_damper():
    from antar_engine.kp.kp_prashna import kp_prashna
    rec = {**_natal_record(), "needs_reconfirm": True}
    assert kp_prashna(rec, "Will I get this job?", number=10, now_utc=NOW)["natal"] is None


def test_unmappable_and_bad_input_never_raise():
    from antar_engine.kp.kp_prashna import kp_prashna
    assert kp_prashna({}, "", now_utc=NOW)["available"] is False
    assert kp_prashna({}, "Will I win at the casino?", now_utc=NOW)["available"] is False
    r = kp_prashna(None, "Will I get this job?", number=999, now_utc=NOW)
    assert r["available"] and r["number"] is None and r["natal"] is None


# ── Ask follow-up card: pending-feedback scoped to Yes/No ───────────────────
class _RecordingSB:
    def __init__(self, rows):
        self.rows, self.filters = rows, []

    def table(self, _):
        return self

    def select(self, *_):
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def lte(self, *_):
        return self

    def order(self, *_, **__):
        return self

    def limit(self, *_):
        return self

    def update(self, *_):
        return self

    def execute(self):
        rows = [r for r in self.rows
                if all(r.get(c) == v for c, v in self.filters if c == "concern")]
        return type("R", (), {"data": rows})()


def test_pending_feedback_concern_scope():
    from antar_engine.prediction_tracker import get_pending_feedback
    rows = [{"id": "a", "concern": "career", "show_after": "2026-01-01"},
            {"id": "b", "concern": "finance", "show_after": "2026-01-02"},
            {"id": "c", "concern": "health", "show_after": "2026-01-03"},
            {"id": "d", "concern": "yesno", "show_after": "2026-01-04"}]
    sb = _RecordingSB(rows)
    out = get_pending_feedback("chart", sb, concern="yesno")
    assert ("concern", "yesno") in sb.filters
    assert [r["id"] for r in out] == ["d"]
    assert out[0]["feedback_ui"]["style"] == "happened"
    # unscoped (Today) is unchanged: no concern filter applied
    sb2 = _RecordingSB(rows)
    get_pending_feedback("chart", sb2)
    assert not any(c == "concern" for c, _ in sb2.filters)
