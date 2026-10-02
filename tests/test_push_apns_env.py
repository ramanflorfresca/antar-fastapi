"""APNs environment handling (2026-10-02).

TestFlight / App Store builds register PRODUCTION tokens. The sender used to
default to the sandbox host, which answers a production token with
BadDeviceToken — and the dead-token prune then deleted it. Now: production by
default, and a BadDeviceToken is retried once on the other host before the
token is treated as dead.
"""
import asyncio

from antar_engine import push_sender as ps


class _Resp:
    def __init__(self, status, reason=""):
        self.status_code, self._reason = status, reason
        self.text = reason

    def json(self):
        return {"reason": self._reason}


def _fake_client(accepts):
    """accepts: {token: host that accepts it}; unknown tokens are Unregistered."""
    calls = []

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None, headers=None):
            host = url.split("/")[2]
            token = url.rsplit("/", 1)[1]
            calls.append((host, token))
            if token not in accepts:
                return _Resp(410, "Unregistered")
            return _Resp(200) if accepts[token] == host else _Resp(400, "BadDeviceToken")

    return _Client, calls


def _run(monkeypatch, accepts, tokens):
    client, calls = _fake_client(accepts)
    monkeypatch.setattr(ps.httpx, "AsyncClient", client)
    monkeypatch.setattr(ps, "_apns_provider_jwt", lambda: "jwt")
    rows = [{"token": t} for t in tokens]
    return asyncio.run(ps._send_apns(None, rows, "t", "b", {"type": "x"})), calls


def test_default_is_production():
    assert ps._APNS_HOST == "api.push.apple.com"
    assert ps._APNS_ALT_HOST == "api.sandbox.push.apple.com"


def test_production_token_sent_once(monkeypatch):
    (sent, failed, dead), calls = _run(monkeypatch, {"p": "api.push.apple.com"}, ["p"])
    assert (sent, failed, dead) == (1, 0, []) and calls == [("api.push.apple.com", "p")]


def test_sandbox_token_retried_not_pruned(monkeypatch):
    (sent, failed, dead), calls = _run(
        monkeypatch, {"s": "api.sandbox.push.apple.com"}, ["s"])
    assert (sent, failed, dead) == (1, 0, [])
    assert calls == [("api.push.apple.com", "s"), ("api.sandbox.push.apple.com", "s")]


def test_bad_on_both_hosts_is_dead(monkeypatch):
    (sent, failed, dead), _ = _run(monkeypatch, {"x": "nowhere.example"}, ["x"])
    assert (sent, failed, dead) == (0, 1, ["x"])


def test_unregistered_is_dead_without_retry(monkeypatch):
    (sent, failed, dead), calls = _run(monkeypatch, {}, ["gone"])
    assert dead == ["gone"] and len(calls) == 1


def test_mixed_batch(monkeypatch):
    (sent, failed, dead), _ = _run(
        monkeypatch,
        {"p": "api.push.apple.com", "s": "api.sandbox.push.apple.com"},
        ["p", "s", "gone"])
    assert (sent, failed, dead) == (2, 1, ["gone"])
