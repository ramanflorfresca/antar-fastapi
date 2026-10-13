import asyncio

import pytest

import main
from antar_engine import horizon as H


def _run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def test_a_slow_source_returns_pending_fast_and_keeps_running_to_fill_its_cache():
    done = []

    async def slow():
        await asyncio.sleep(0.25)
        done.append(1)
        return {"ok": True}

    async def scenario():
        res, pending = await main._bounded_source(lambda: slow(), 0.05)
        assert (res, pending) == (None, True)
        assert done == []
        await asyncio.sleep(0.4)                       # the shielded task was not cancelled
        return list(done)
    assert _run(scenario()) == [1]


def test_a_fast_source_returns_its_result_and_an_error_still_propagates():
    async def fast():
        return {"x": 1}

    async def boom():
        raise RuntimeError("source down")

    async def scenario():
        assert await main._bounded_source(lambda: fast(), 1.0) == ({"x": 1}, False)
        with pytest.raises(RuntimeError):
            await main._bounded_source(lambda: boom(), 1.0)
    _run(scenario())


def test_horizon_empty_marks_pending_without_any_words():
    p = H._empty("month", "en", pending=True)
    assert p == {"version": "horizon-1", "scope": "month", "available": False, "pending": True, "label": "This month"}
    assert H._empty("year", "en")["pending"] is False and H.build_month({}, None, "en")["pending"] is False
