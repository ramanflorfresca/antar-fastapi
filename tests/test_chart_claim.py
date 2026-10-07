"""Guest chart claim: the token gate and the /chart/claim endpoint contract."""
import pytest
from fastapi import HTTPException

from antar_engine import chart_claim as cc


def test_token_is_stable_and_chart_specific():
    assert cc.make_claim_token("c1") == cc.make_claim_token("c1")
    assert cc.make_claim_token("c1") != cc.make_claim_token("c2")


def test_token_rejects_wrong_empty_and_other_chart():
    t = cc.make_claim_token("c1")
    assert cc.claim_token_ok("c1", t)
    assert not cc.claim_token_ok("c2", t)
    assert not cc.claim_token_ok("c1", "")
    assert not cc.claim_token_ok("", t)
    assert not cc.claim_token_ok("c1", t[:-1] + ("0" if t[-1] != "0" else "1"))


def test_secret_env_changes_token(monkeypatch):
    a = cc.make_claim_token("c1")
    monkeypatch.setenv("CHART_CLAIM_SECRET", "other")
    assert cc.make_claim_token("c1") != a


# ── endpoint ──────────────────────────────────────────────────────

class _Res:
    def __init__(self, data): self.data = data


class _Q:
    def __init__(self, db, name):
        self.db, self.name, self.f, self.op, self.payload = db, name, [], "select", None
    def select(self, *a, **k): return self
    def update(self, p): self.op, self.payload = "update", p; return self
    def eq(self, k, v): self.f.append((k, v, "eq")); return self
    def is_(self, k, v): self.f.append((k, None if v == "null" else v, "is")); return self
    def limit(self, n): return self
    def _match(self, r): return all(r.get(k) == v for k, v, _ in self.f)
    def execute(self):
        rows = self.db[self.name]
        hit = [r for r in rows if self._match(r)]
        if self.op == "update":
            for r in hit: r.update(self.payload)
            return _Res([dict(r) for r in hit])
        return _Res([dict(r) for r in hit])


class _DB:
    def __init__(self, charts, profiles=None):
        self.t = {"charts": charts, "profiles": profiles if profiles is not None else []}
    def table(self, n): return _Q(self.t, n)


@pytest.fixture
def api(monkeypatch):
    import main
    def setup(charts, user="u1"):
        db = _DB(charts, [{"user_id": user, "primary_chart_id": None}])
        monkeypatch.setattr(main, "supabase", db)
        monkeypatch.setattr(main, "verify_token", lambda a: user)
        return main, db
    return setup


def _claim(main, cid, token):
    return main.claim_guest_chart(main.ChartClaimRequest(chart_id=cid, claim_token=token), authorization="Bearer x")


def test_claims_unowned_chart_as_primary(api):
    main, db = api([{"id": "c1", "user_id": None, "deleted_at": None, "chart_type": "primary"}])
    out = _claim(main, "c1", cc.make_claim_token("c1"))
    assert out["status"] == "claimed" and out["chart_type"] == "primary"
    assert db.t["charts"][0]["user_id"] == "u1"
    assert db.t["profiles"][0]["primary_chart_id"] == "c1"


def test_second_chart_is_secondary_and_keeps_primary(api):
    main, db = api([
        {"id": "old", "user_id": "u1", "deleted_at": None, "chart_type": "primary"},
        {"id": "c1", "user_id": None, "deleted_at": None, "chart_type": "primary"},
    ])
    out = _claim(main, "c1", cc.make_claim_token("c1"))
    assert out["chart_type"] == "secondary"
    assert db.t["profiles"][0]["primary_chart_id"] is None


def test_wrong_token_is_403_and_chart_untouched(api):
    main, db = api([{"id": "c1", "user_id": None, "deleted_at": None}])
    with pytest.raises(HTTPException) as e:
        _claim(main, "c1", "nope")
    assert e.value.status_code == 403 and db.t["charts"][0]["user_id"] is None


def test_other_users_chart_is_409(api):
    main, db = api([{"id": "c1", "user_id": "someone-else", "deleted_at": None}])
    with pytest.raises(HTTPException) as e:
        _claim(main, "c1", cc.make_claim_token("c1"))
    assert e.value.status_code == 409 and db.t["charts"][0]["user_id"] == "someone-else"


def test_reclaim_by_same_user_is_idempotent(api):
    main, _ = api([{"id": "c1", "user_id": "u1", "deleted_at": None}])
    assert _claim(main, "c1", cc.make_claim_token("c1"))["status"] == "already_yours"


def test_missing_chart_is_404(api):
    main, _ = api([])
    with pytest.raises(HTTPException) as e:
        _claim(main, "c1", cc.make_claim_token("c1"))
    assert e.value.status_code == 404
