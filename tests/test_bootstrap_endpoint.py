"""/api/v1/bootstrap: one round trip, sections fail soft, missing chart 404s."""
import os
os.environ.setdefault("SUPABASE_URL", "http://localhost:1")
os.environ.setdefault("SUPABASE_KEY", "k")

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import main

CID = "e3a3dac7-cb91-468c-b9fe-51ff74ef1217"


def _stub(monkeypatch, **over):
    base = dict(
        get_chart=lambda c: {"id": c},
        get_entitlements_endpoint=lambda c: {"tier": "free"},
        get_subscription_status=lambda c: {"plan": "free"},
        get_streak_endpoint=lambda c, tz_offset=0: {"n": 1},
        get_prediction_accuracy_endpoint=lambda c, language="en": {"a": 1},
        get_pending_feedback_endpoint=lambda c, language="en": [],
    )
    base.update(over)
    for k, v in base.items():
        monkeypatch.setattr(main, k, v)


def test_all_sections(monkeypatch):
    _stub(monkeypatch)
    j = TestClient(main.app).get(f"/api/v1/bootstrap/{CID}").json()
    assert j["errors"] == [] and j["chart"]["id"] == CID and j["entitlements"]["tier"] == "free"


def test_section_failure_is_soft(monkeypatch):
    def boom(c):
        raise RuntimeError("x")
    _stub(monkeypatch, get_subscription_status=boom)
    r = TestClient(main.app).get(f"/api/v1/bootstrap/{CID}")
    assert r.status_code == 200 and r.json()["subscription"] is None
    assert r.json()["errors"] == ["subscription"]


def test_missing_chart_404(monkeypatch):
    def nf(c):
        raise HTTPException(status_code=404, detail="Chart not found")
    _stub(monkeypatch, get_chart=nf)
    assert TestClient(main.app).get(f"/api/v1/bootstrap/{CID}").status_code == 404
