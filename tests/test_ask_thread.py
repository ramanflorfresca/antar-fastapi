from datetime import date

import pytest

from antar_engine import ask_thread as T

TODAY = date(2026, 10, 15)


def _m(i, q, ts, a="An answer.", nxt="A step."):
    return {"id": i, "question": q, "answer": a, "next": nxt, "domain": "general", "created_at": ts}


def test_day_dividers_labels_and_times_are_made_by_the_backend():
    msgs = [_m("1", "Q one", "2026-10-13T14:05:00+00:00"), _m("2", "Q two", "2026-10-13T18:30:00+00:00"),
            _m("3", "Q three", "2026-10-14T09:00:00+00:00"), _m("4", "Q four", "2026-10-15T02:25:23.9+00:00")]
    out = T.build(msgs, [], -240, TODAY, "en")                  # UTC-4: the 02:25 UTC message is still Oct 14 at 10:25 PM
    it = out["items"]
    assert [i["day_label"] for i in it] == ["Oct 13", "Oct 13", "Yesterday", "Yesterday"]
    assert [i["show_day_label"] for i in it] == [True, False, True, False]
    assert it[0]["time_label"] == "10:05 AM" and it[3]["time_label"] == "10:25 PM"
    assert "empty" not in out and out["title"] == "Ask Antar"


def test_the_local_day_follows_the_clients_timezone_minutes_or_hours():
    msgs = [_m("1", "Q", "2026-10-15T20:00:00+00:00")]
    assert T.build(msgs, [], 330, TODAY, "en")["items"][0]["day"] == "2026-10-16"        # IST (+5:30) is already the 16th
    assert T.build(msgs, [], -300, TODAY, "en")["items"][0]["day"] == "2026-10-15"
    assert T.offset_hours(330) == 5.5 and T.offset_hours(-5) == -5.0 and T.offset_hours(None) == 0.0


def test_a_check_in_arrives_as_a_message_from_antar_at_the_end_under_today():
    due = [{"claim_id": "c1", "text": "Did the deal close?", "topic": "money", "options": [{"value": "yes", "label": "Yes"}]}]
    out = T.build([_m("1", "Q", "2026-10-14T15:00:00+00:00")], due, 0, TODAY, "en")
    last = out["items"][-1]
    assert last["kind"] == "checkin" and last["claim_id"] == "c1" and last["day_label"] == "Today" and last["show_day_label"] is True
    assert last["options"][0]["value"] == "yes"


def test_an_empty_thread_has_a_welcome_and_three_fast_starters_in_each_language():
    en = T.build([], [], 0, TODAY, "en")
    assert en["items"] == [] and len(en["empty"]["starters"]) == 3 and "Ask me anything" in en["empty"]["title"]
    es = T.build([], [], 0, TODAY, "es")
    assert es["empty"]["title"].startswith("Pregúntame") and es["title"] == "Pregunta a Antar"
    from antar_engine import ask_chip
    assert ask_chip.chip_scope(en["empty"]["starters"][0]) == "today" and ask_chip.chip_scope(en["empty"]["starters"][2]) == "month"
    assert ask_chip.chip_scope(es["empty"]["starters"][0]) == "today"


def test_rows_with_no_usable_time_or_no_content_are_skipped_not_shown_blank():
    out = T.build([_m("1", "Q", "not a date"), {"id": "2", "created_at": "2026-10-14T10:00:00+00:00"}, _m("3", "Q3", "2026-10-14T10:00:00+00:00")], [], 0, TODAY, "en")
    assert [i["id"] for i in out["items"]] == ["3"]


def test_spanish_labels():
    out = T.build([_m("1", "P", "2026-10-13T14:05:00+00:00")], [], 0, TODAY, "es")
    assert out["items"][0]["day_label"] == "13 oct" and out["items"][0]["time_label"] == "14:05"
    assert T.day_label(date(2025, 12, 31), TODAY, "en") == "Dec 31, 2025"


# ── routes: owner only, confirm required, shape ──────────────────────────────────────────────────────────────────
@pytest.fixture()
def client(monkeypatch):
    import main
    from fastapi.testclient import TestClient
    state = {"owned": True, "deleted": []}

    async def _hist(chart_id, limit, before, language):
        return {"messages": [_m("1", "Q", "2026-10-14T15:00:00+00:00")], "has_more": False, "next_before": None}

    monkeypatch.setattr(main, "verify_token", lambda a: "u1")
    monkeypatch.setattr(main, "_oc_owned_chart", lambda u, c: state["owned"])
    monkeypatch.setattr(main, "ask_history", _hist)
    monkeypatch.setattr(main, "outcomes_due", lambda c, a: {"due": [{"claim_id": "c1", "text": "Did it hold?", "options": []}]})

    class _Q:
        def __init__(self): self.f = {}
        def select(self, *a, **k): return self
        def delete(self): state["deleted"].append(True); return self
        def eq(self, k, v): self.f[k] = v; return self
        def limit(self, n): return self
        def execute(self):
            class R: data = [{"id": "m1"}]
            return R()

    class _SB:
        def table(self, n): return _Q()

    monkeypatch.setattr(main, "supabase", _SB())
    return TestClient(main.app), state


def test_the_thread_route_returns_items_and_the_due_check_in(client):
    c, _ = client
    r = c.get("/api/v1/ask/thread/a4c9d57b-fb9c-4890-8fe7-4a9904f515ed?tz=-240&language=en", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    j = r.json()
    assert [i["kind"] for i in j["items"]] == ["exchange", "checkin"] and j["has_more"] is False and j["title"] == "Ask Antar"


def test_the_thread_is_owner_only(client):
    c, state = client
    state["owned"] = False
    cid = "a4c9d57b-fb9c-4890-8fe7-4a9904f515ed"
    h = {"Authorization": "Bearer x"}
    assert c.get(f"/api/v1/ask/thread/{cid}", headers=h).status_code == 403
    assert c.delete(f"/api/v1/ask/thread/{cid}/message/m1", headers=h).status_code == 403
    assert c.delete(f"/api/v1/ask/thread/{cid}?confirm=yes", headers=h).status_code == 403
    assert c.get(f"/api/v1/ask/thread/{cid}").status_code in (401, 403, 422)      # no token at all


def test_clearing_the_thread_needs_an_explicit_confirmation(client):
    c, state = client
    cid = "a4c9d57b-fb9c-4890-8fe7-4a9904f515ed"
    h = {"Authorization": "Bearer x"}
    assert c.delete(f"/api/v1/ask/thread/{cid}", headers=h).status_code == 400 and state["deleted"] == []
    r = c.delete(f"/api/v1/ask/thread/{cid}?confirm=yes", headers=h)
    assert r.status_code == 200 and r.json()["cleared"] is True and state["deleted"]
    assert c.delete(f"/api/v1/ask/thread/{cid}/message/m1", headers=h).json() == {"deleted": True, "message_id": "m1"}
