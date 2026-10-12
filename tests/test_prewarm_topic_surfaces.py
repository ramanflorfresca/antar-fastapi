"""[home-speed 2026-10-12] The daily prewarm also warms the topic list and Questions for you."""
import asyncio

import pytest

import main


def _run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def test_warms_both_surfaces_with_minutes_not_hours(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "_topics_compute", lambda *a: calls.append(("topics", a)))
    monkeypatch.setattr(main, "_suggested_questions_compute", lambda *a: calls.append(("sq", a)))
    _run(main._prewarm_topic_surfaces("c1", -5.5, "es"))
    assert calls == [("topics", ("c1", "es", -330)), ("sq", ("c1", "es", -330, 3))]


def test_a_failing_surface_does_not_stop_the_other_or_raise(monkeypatch):
    calls = []

    def boom(*a):
        raise RuntimeError("engine down")

    monkeypatch.setattr(main, "_topics_compute", boom)
    monkeypatch.setattr(main, "_suggested_questions_compute", lambda *a: calls.append(a))
    _run(main._prewarm_topic_surfaces("c1", None, "en"))
    assert calls == [("c1", "en", 0, 3)]          # unknown tz falls back to 0, second surface still ran
