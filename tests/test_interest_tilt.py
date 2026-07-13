"""Personalization-C: the daily interest tilt must read the real Ask history
(the `predictions` table) and map concerns onto coarse domains."""
from datetime import datetime, timezone
from antar_engine.patra_prior import _behavior_counts, _norm, BEHAVIOR_LOOKBACK_DAYS


class _FakeResult:
    def __init__(self, data): self.data = data


class _FakeQuery:
    def __init__(self, data): self._data = data
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def gte(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self): return _FakeResult(self._data)


class _FakeSB:
    def __init__(self, per_table): self._pt = per_table
    def table(self, name): return _FakeQuery(self._pt.get(name, []))


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def test_concern_maps_to_coarse_domain():
    assert _norm("finance") == "money"
    assert _norm("wealth") == "money"
    assert _norm("career") == "work"
    assert _norm("love") == "relationships"
    assert _norm("health") == "body"
    assert _norm("general") is None       # carries no interest signal


def test_behavior_counts_reads_predictions():
    sb = _FakeSB({"predictions": [
        {"concern": "finance", "created_at": _now_iso()},
        {"concern": "finance", "created_at": _now_iso()},
        {"concern": "career", "created_at": _now_iso()},
        {"concern": "general", "created_at": _now_iso()},  # dropped
    ]})
    counts = _behavior_counts("chart-x", sb)
    assert counts.get("money", 0) > counts.get("work", 0) > 0
    assert "mind" not in counts and "relationships" not in counts   # never asked


def test_empty_history_is_silent():
    assert _behavior_counts("chart-x", _FakeSB({"predictions": []})) == {}


def test_lookback_window_widened():
    # 30 days was too short for real (bursty) usage.
    assert BEHAVIOR_LOOKBACK_DAYS >= 180
