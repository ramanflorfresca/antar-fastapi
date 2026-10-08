"""Sync (threadpool) routes must be able to schedule background coroutines, and
every response carries X-Process-Ms.

Deliberately does NOT run the app lifespan via `with TestClient(...)`: that binds
module-level async state to a loop that is then closed, which broke an unrelated
later test (test_whatsapp_channel) in the full suite."""
import os
os.environ.setdefault("SUPABASE_URL", "http://localhost:1")
os.environ.setdefault("SUPABASE_KEY", "k")

import asyncio
import threading

from fastapi.testclient import TestClient

import main


def test_spawn_from_a_loopless_thread_runs_on_the_server_loop(monkeypatch):
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    t.start()
    ran = threading.Event()
    seen = {}

    async def job():
        seen["loop"] = asyncio.get_running_loop()
        ran.set()

    monkeypatch.setattr(main, "_MAIN_LOOP", loop)
    try:
        # this thread has no running loop, exactly like a sync FastAPI route
        assert main._spawn_bg(job(), "test") is None
        assert ran.wait(3), "background coroutine never ran"
        assert seen["loop"] is loop
    finally:
        loop.call_soon_threadsafe(loop.stop)
        t.join(3)
        loop.close()


def test_spawn_without_loop_does_not_leak_coroutine(monkeypatch):
    monkeypatch.setattr(main, "_MAIN_LOOP", None)

    async def job():
        pass
    assert main._spawn_bg(job(), "x") is None


def test_responses_carry_process_time_header():
    r = TestClient(main.app).get("/health")
    assert "x-process-ms" in r.headers
