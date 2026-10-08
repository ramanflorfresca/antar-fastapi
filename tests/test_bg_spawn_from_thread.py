"""Sync (threadpool) routes must be able to schedule background coroutines, and
every response carries X-Process-Ms."""
import os
os.environ.setdefault("SUPABASE_URL", "http://localhost:1")
os.environ.setdefault("SUPABASE_KEY", "k")

import threading
from fastapi.testclient import TestClient

import main

ran = threading.Event()


async def _job():
    ran.set()


@main.app.get("/_t/spawn")
def _spawn_route():  # sync def => threadpool, no running loop
    main._spawn_bg(_job(), "test")
    return {"ok": True}


def test_sync_route_can_spawn_background_work():
    with TestClient(main.app) as c:  # context manager runs lifespan => _MAIN_LOOP set
        r = c.get("/_t/spawn")
        assert r.status_code == 200
        assert ran.wait(3), "background coroutine never ran"
        assert "x-process-ms" in r.headers


def test_spawn_without_loop_does_not_leak_coroutine():
    main._MAIN_LOOP = None
    assert main._spawn_bg(_job(), "x") is None
