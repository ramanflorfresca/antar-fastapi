import base64
import json
import time

import pytest
from fastapi import HTTPException

import main


def _jwt(exp):
    seg = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{seg({'alg': 'none'})}.{seg({'exp': exp})}.sig"


class _Auth:
    def __init__(self, ok=True):
        self.calls, self.ok = 0, ok

    def get_user(self, token):
        self.calls += 1
        if not self.ok:
            raise Exception("bad token")

        class U:
            class user:
                id = "user-1"
        return U()


@pytest.fixture()
def auth(monkeypatch):
    a = _Auth()
    monkeypatch.setattr(main.supabase, "auth", a, raising=False)
    main._TOKEN_CACHE.clear()
    return a


def test_a_verified_token_is_checked_with_supabase_once_not_on_every_request(auth):
    t = _jwt(time.time() + 3600)
    assert [main.verify_token("Bearer " + t) for _ in range(5)] == ["user-1"] * 5
    assert auth.calls == 1


def test_different_tokens_are_checked_separately(auth):
    main.verify_token("Bearer " + _jwt(time.time() + 3600))
    main.verify_token("Bearer " + _jwt(time.time() + 7200))
    assert auth.calls == 2


def test_a_failure_is_never_remembered(auth):
    auth.ok = False
    t = _jwt(time.time() + 3600)
    for _ in range(3):
        with pytest.raises(HTTPException) as e:
            main.verify_token("Bearer " + t)
        assert e.value.status_code == 401
    assert auth.calls == 3 and not main._TOKEN_CACHE


def test_the_cache_never_outlives_the_tokens_own_expiry(auth):
    t = _jwt(time.time() + 20)                      # 20 s left: remembered for at most ~15 s
    main.verify_token("Bearer " + t)
    exp_at = list(main._TOKEN_CACHE.values())[0][1]
    assert exp_at <= time.time() + 16
    main._TOKEN_CACHE.clear()
    main.verify_token("Bearer " + _jwt(time.time() + 3))   # about to expire: not remembered at all
    assert not main._TOKEN_CACHE


def test_an_expired_entry_is_checked_again(auth):
    t = _jwt(time.time() + 3600)
    main.verify_token("Bearer " + t)
    k = next(iter(main._TOKEN_CACHE))
    main._TOKEN_CACHE[k] = ("user-1", time.time() - 1)
    main.verify_token("Bearer " + t)
    assert auth.calls == 2


def test_a_malformed_header_is_still_refused(auth):
    with pytest.raises(HTTPException) as e:
        main.verify_token("Token abc")
    assert e.value.status_code == 401 and auth.calls == 0


def test_the_cache_is_bounded(auth, monkeypatch):
    monkeypatch.setattr(main, "_TOKEN_CACHE_MAX", 10)
    for i in range(30):
        main.verify_token("Bearer " + _jwt(time.time() + 3600 + i))
    assert len(main._TOKEN_CACHE) <= 11
