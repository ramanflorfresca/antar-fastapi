"""The check-in ping job no longer feeds pending_pings (the old Today Check-in card source) by default."""
import asyncio
import types
from datetime import datetime, timedelta

import pytest

import main


class _Q:
    def __init__(self, sb, name):
        self.sb, self.name, self.op, self.payload = sb, name, "select", None

    def select(self, *_a, **_k): return self
    def eq(self, *_a, **_k): return self
    def is_(self, *_a, **_k): return self
    def lte(self, *_a, **_k): return self
    def gte(self, *_a, **_k): return self
    def limit(self, *_a, **_k): return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def execute(self):
        self.sb.calls.append((self.name, self.op, self.payload))
        if self.name == "user_predictions" and self.op == "select":
            now = datetime.utcnow()
            return types.SimpleNamespace(data=[{
                "id": "p1", "user_id": "u1", "prediction_text": "You are in a high-energy action period.",
                "category": "current_chapter", "chart_id": "c1",
                "prediction_window_end": (now + timedelta(days=2)).isoformat()}])
        return types.SimpleNamespace(data=[])


class _SB:
    def __init__(self):
        self.calls = []
        self.auth = types.SimpleNamespace(admin=types.SimpleNamespace(
            get_user_by_id=lambda _u: types.SimpleNamespace(user=types.SimpleNamespace(email="a@b.c"))))

    def table(self, name): return _Q(self, name)


def _run(monkeypatch, enabled):
    sb = _SB()
    sent = []

    async def fake_send(**kw):
        sent.append(kw)
        return True
    monkeypatch.setattr(main, "supabase", sb)
    monkeypatch.setattr(main, "send_email", fake_send)
    now = datetime.utcnow()
    monkeypatch.setattr(main, "_tz_hours_by_chart", lambda ids: {"c1": float(8 - now.hour)})
    if enabled:
        monkeypatch.setenv("PENDING_PINGS_ENABLED", "on")
    else:
        monkeypatch.delenv("PENDING_PINGS_ENABLED", raising=False)
    asyncio.run(main._ping_checkin_job())
    return sb, sent


def test_default_is_off():
    assert main._pending_pings_enabled() is False


def test_job_skips_pending_pings_but_still_emails_and_marks_pinged(monkeypatch):
    sb, sent = _run(monkeypatch, enabled=False)
    assert not [c for c in sb.calls if c[0] == "pending_pings"]
    assert any(c[0] == "user_predictions" and c[1] == "update" and "pinged_at" in c[2] for c in sb.calls)
    assert len(sent) == 1


def test_switch_restores_the_insert(monkeypatch):
    sb, _ = _run(monkeypatch, enabled=True)
    ins = [c for c in sb.calls if c[0] == "pending_pings" and c[1] == "insert"]
    assert len(ins) == 1 and ins[0][2]["category"] == "current_chapter"
