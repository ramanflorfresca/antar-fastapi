"""[demo-mode 2026-10-05] The public demo chart must be usable (Ask, Today…) and
impossible to change. The backend has no per-user auth on chart_id, so these pin
the guard that makes a public chart safe."""
import asyncio
import json

import pytest

from antar_engine import demo_mode as dm

DEMO = "11111111-2222-3333-4444-555555555555"
OTHER = "99999999-8888-7777-6666-555555555555"


class _SB:
    """Minimal supabase stand-in: app_config.demo_chart_id → DEMO (or None)."""
    def __init__(self, value=DEMO, boom=False):
        self.value, self.boom = value, boom

    def table(self, name):
        return self

    def select(self, *_): return self
    def eq(self, *_): return self
    def limit(self, *_): return self

    def execute(self):
        if self.boom:
            raise RuntimeError("db down")

        class R:  # noqa
            data = [{"value": self.value}] if self.value else []
        return R()


@pytest.fixture(autouse=True)
def _fresh():
    dm._CACHE.update(id=None, at=0.0)
    dm._HITS.clear()
    yield


def test_route_policy():
    assert dm.route_allowed("GET", "/api/v1/anything")
    assert dm.route_allowed("POST", "/api/v1/ask")
    assert dm.route_allowed("POST", "/api/v1/ask/")                  # trailing slash
    for m in ("PUT", "PATCH", "DELETE"):
        assert not dm.route_allowed(m, "/api/v1/ask")
    for p in ("/api/v1/chart/create", "/api/v1/user/life-events", "/api/v1/places/saved",
              "/api/v1/messaging/whatsapp/connect", "/api/v1/subscription/cancel",
              "/api/v1/predict/daily-practice/complete", "/api/v1/predict/fulfill",
              "/api/v1/decisions", "/api/v1/something/brand-new"):
        assert not dm.route_allowed("POST", p), p                    # default-deny


def test_decide_only_touches_the_demo_chart():
    assert dm.decide("DELETE", "/api/v1/me/charts/x", False, "1.1.1.1") is None
    s, body = dm.decide("DELETE", "/api/v1/account/x", True, "1.1.1.1")
    assert s == 403 and body["demo"] is True and body["code"] == "DEMO_READ_ONLY"


def test_ask_is_rate_limited_per_ip_but_other_ips_are_not():
    for _ in range(3):
        assert dm.decide("POST", "/api/v1/ask", True, "9.9.9.9", limit=3) is None
    s, body = dm.decide("POST", "/api/v1/ask", True, "9.9.9.9", limit=3)
    assert s == 429 and body["code"] == "DEMO_RATE_LIMIT"
    assert dm.decide("POST", "/api/v1/ask", True, "8.8.8.8", limit=3) is None
    # compute-only routes are not metered
    for _ in range(10):
        assert dm.decide("POST", "/api/v1/predict/daily", True, "9.9.9.9", limit=3) is None


def test_config_lookup_fails_open_and_caches():
    assert dm.demo_chart_id(_SB(None), force=True) is None
    assert dm.demo_chart_id(_SB(DEMO), force=True) == DEMO
    # a read failure keeps the last known value instead of dropping the guard
    dm._CACHE["at"] = 0.0
    assert dm.demo_chart_id(_SB(boom=True)) == DEMO


# ── the middleware, end to end, on a tiny ASGI app ──
def _app():
    seen = {}

    async def app(scope, receive, send):
        body = b""
        while True:
            msg = await receive()
            body += msg.get("body", b"")
            if not msg.get("more_body"):
                break
        seen["body"] = body
        seen["hit"] = seen.get("hit", 0) + 1
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b'{"ok":true}'})

    return app, seen


def _call(mw, method, path, body=b"", query=b"", ip="7.7.7.7"):
    sent = []

    async def run():
        msgs = [{"type": "http.request", "body": body, "more_body": False}]

        async def receive():
            return msgs.pop(0) if msgs else {"type": "http.disconnect"}

        async def send(m):
            sent.append(m)
        scope = {"type": "http", "method": method, "path": path, "query_string": query,
                 "headers": [(b"x-forwarded-for", ip.encode())], "client": ("1.2.3.4", 1)}
        await mw(scope, receive, send)
    asyncio.run(run())
    status = sent[0]["status"]
    out = b"".join(m.get("body", b"") for m in sent[1:])
    return status, out


def test_middleware_blocks_writes_on_the_demo_chart_and_replays_the_body():
    app, seen = _app()
    mw = dm.DemoGuardMiddleware(app, lambda: _SB(DEMO))
    payload = json.dumps({"chart_id": DEMO, "question": "will I be ok?"}).encode()

    # allowed compute route: passes AND the app still receives the full body
    st, _ = _call(mw, "POST", "/api/v1/ask", payload)
    assert st == 200 and seen["body"] == payload

    # write routes: id in body / in path / in query → 403, app never called
    n = seen["hit"]
    assert _call(mw, "POST", "/api/v1/user/life-events", payload)[0] == 403
    assert _call(mw, "DELETE", f"/api/v1/account/{DEMO}")[0] == 403
    assert _call(mw, "PATCH", "/api/v1/me", b"", f"chart_id={DEMO}".encode())[0] == 403
    assert seen["hit"] == n


def test_middleware_leaves_everyone_else_alone():
    app, seen = _app()
    mw = dm.DemoGuardMiddleware(app, lambda: _SB(DEMO))
    other = json.dumps({"chart_id": OTHER}).encode()
    assert _call(mw, "POST", "/api/v1/user/life-events", other)[0] == 200
    assert _call(mw, "DELETE", f"/api/v1/account/{OTHER}")[0] == 200
    # non-API paths and "no demo configured" are untouched too
    assert _call(mw, "POST", "/health", json.dumps({"chart_id": DEMO}).encode())[0] == 200
    dm._CACHE.update(id=None, at=0.0)          # the id is cached ~30s; start clean
    off = dm.DemoGuardMiddleware(app, lambda: _SB(None))
    assert _call(off, "DELETE", f"/api/v1/account/{DEMO}")[0] == 200


def test_every_mutating_route_in_the_real_app_is_refused_unless_allow_listed():
    """A route added tomorrow must be blocked for the demo without anyone remembering,
    and the allow-list must name real routes (a typo would silently block Ask)."""
    import main
    mutating = {}
    for r in main.app.routes:
        for meth in (getattr(r, "methods", None) or ()):
            if meth in ("POST", "PUT", "PATCH", "DELETE"):
                mutating.setdefault(r.path, set()).add(meth)
    posts = {p for p, ms in mutating.items() if "POST" in ms}
    missing = sorted(dm._ALLOW_EXACT - posts)
    assert not missing, f"allow-list names routes that don't exist: {missing}"
    for path, ms in mutating.items():
        concrete = path.replace("{", "x").replace("}", "")      # {chart_id} → xchart_id
        for meth in ms:
            expected = meth == "POST" and path in dm._ALLOW_EXACT
            assert dm.route_allowed(meth, concrete) == expected, (meth, path)
