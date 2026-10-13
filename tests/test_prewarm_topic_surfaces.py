"""[home-speed 2026-10-12] The daily prewarm also warms the topic list and Questions for you."""
import asyncio

import pytest

import main


def _run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def test_warms_both_surfaces_with_minutes_not_hours(monkeypatch):
    monkeypatch.setenv("HOME_PREWARM_READS", "off")
    calls = []
    monkeypatch.setattr(main, "_topics_compute", lambda *a: calls.append(("topics", a)))
    monkeypatch.setattr(main, "_suggested_questions_compute", lambda *a: calls.append(("sq", a)))
    _run(main._prewarm_topic_surfaces("c1", -5.5, "es"))
    assert calls == [("topics", ("c1", "es", -330)), ("sq", ("c1", "es", -330, 3))]


def test_a_failing_surface_does_not_stop_the_other_or_raise(monkeypatch):
    monkeypatch.setenv("HOME_PREWARM_READS", "off")
    calls = []

    def boom(*a):
        raise RuntimeError("engine down")

    monkeypatch.setattr(main, "_topics_compute", boom)
    monkeypatch.setattr(main, "_suggested_questions_compute", lambda *a: calls.append(a))
    _run(main._prewarm_topic_surfaces("c1", None, "en"))
    assert calls == [("c1", "en", 0, 3)]          # unknown tz falls back to 0, second surface still ran


def test_prewarm_also_warms_the_monthly_and_annual_reads_and_survives_their_failure(monkeypatch):
    monkeypatch.delenv("HOME_PREWARM_READS", raising=False)
    calls = []
    monkeypatch.setattr(main, "_topics_compute", lambda *a: None)
    monkeypatch.setattr(main, "_suggested_questions_compute", lambda *a: None)

    async def month(**kw):
        calls.append(("month", kw))
        raise RuntimeError("llm down")            # a failing month must not stop the year

    async def year(**kw):
        calls.append(("year", kw))
        return {}
    monkeypatch.setattr(main, "get_monthly_deepdive", month)
    monkeypatch.setattr(main, "get_annual_plan", year)
    _run(main._prewarm_topic_surfaces("c1", None, "es"))
    assert [c[0] for c in calls] == ["month", "year"] and calls[0][1] == {"chart_id": "c1", "language": "es"}
