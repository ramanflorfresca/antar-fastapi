import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from antar_engine import request_deadline as RD


def test_budgets():
    assert RD.budget_for("GET", "/api/v1/people/abc") == 8.0
    assert RD.budget_for("GET", "/api/v1/compatibility/session/abc") == 12.0
    assert RD.budget_for("GET", "/api/v1/compatibility/session/abc/agreement") == 8.0
    assert RD.budget_for("GET", "/api/v1/chart/abc/upcoming-themes") == 30.0
    assert RD.budget_for("GET", "/api/v1/chart/abc/identity") == 10.0
    assert RD.budget_for("GET", "/api/v1/whatever") == RD.DEFAULT_BUDGET
    assert RD.budget_for("POST", "/api/v1/ask") is None              # LLM / write paths are never cut off
    assert RD.budget_for("GET", "/health") is None
    assert RD.budget_for("GET", "/api/v1/something/stream") is None


def _app(monkeypatch, secs):
    monkeypatch.setattr(RD, "_BUDGETS", [(RD.re.compile(r"^/api/v1/slow$"), secs)])
    app = FastAPI()
    app.add_middleware(RD.DeadlineMiddleware)

    @app.get("/api/v1/slow")
    async def slow():
        await asyncio.sleep(1.0)
        return {"ok": True}

    @app.get("/api/v1/fast")
    async def fast():
        return {"ok": True}

    return TestClient(app)


def test_slow_get_returns_a_clear_504(monkeypatch):
    r = _app(monkeypatch, 0.2).get("/api/v1/slow")
    assert r.status_code == 504
    j = r.json()
    assert j["error"] == "timeout" and j["retry"] is True and j["path"] == "/api/v1/slow" and r.headers.get("retry-after") == "2"


def test_fast_get_and_off_switch(monkeypatch):
    assert _app(monkeypatch, 5).get("/api/v1/slow").status_code == 200
    assert _app(monkeypatch, 5).get("/api/v1/fast").status_code == 200
    monkeypatch.setenv("ANTAR_DEADLINES", "off")
    assert _app(monkeypatch, 0.1).get("/api/v1/slow").status_code == 200
