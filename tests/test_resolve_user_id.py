"""
Guards for entitlements._resolve_user_id.

It queried profiles.chart_id — a column that does not exist (renamed to
primary_chart_id) — and a bare except swallowed the 42703, so it ALWAYS
returned None: ask_usage never found a user's sibling rows and the
[lang-401] language fallback never resolved an owner.
"""
import os
import pytest
from dotenv import load_dotenv

from antar_engine.entitlements import _resolve_user_id

load_dotenv()


class _Q:
    def __init__(self, sb, table):
        self.sb, self.table, self.col = sb, table, None

    def select(self, *_):
        return self

    def eq(self, col, val):
        self.col, self.val = col, val
        return self

    def limit(self, *_):
        return self

    def execute(self):
        self.sb.calls.append((self.table, self.col))
        rows = self.sb.data.get((self.table, self.col))
        if isinstance(rows, Exception):
            raise rows
        return type("R", (), {"data": rows or []})()


class _SB:
    def __init__(self, data):
        self.data, self.calls = data, []

    def table(self, t):
        return _Q(self, t)


def test_resolves_from_charts_user_id():
    sb = _SB({("charts", "id"): [{"user_id": "u1"}]})
    assert _resolve_user_id("c1", sb) == "u1"
    assert sb.calls == [("charts", "id")]


def test_falls_back_to_profiles_primary_chart_id():
    sb = _SB({("charts", "id"): [{"user_id": None}],
              ("profiles", "primary_chart_id"): [{"user_id": "u2"}]})
    assert _resolve_user_id("c1", sb) == "u2"


def test_never_queries_the_nonexistent_profiles_chart_id():
    sb = _SB({})
    _resolve_user_id("c1", sb)
    assert ("profiles", "chart_id") not in sb.calls


def test_fail_open():
    boom = RuntimeError("42703")
    sb = _SB({("charts", "id"): boom, ("profiles", "primary_chart_id"): boom})
    assert _resolve_user_id("c1", sb) is None
    assert _resolve_user_id("", sb) is None


@pytest.mark.skipif(not os.getenv("SUPABASE_URL"), reason="needs Supabase")
def test_live_columns_are_real_and_resolve_an_owner():
    """The columns we query must exist (a 42703 is swallowed by fail-open,
    which is exactly how the original bug hid), and a real chart resolves."""
    import main
    sb = main.supabase
    sb.table("charts").select("user_id").eq("id", "00000000-0000-0000-0000-000000000000").limit(1).execute()
    sb.table("profiles").select("user_id").eq("primary_chart_id", "00000000-0000-0000-0000-000000000000").limit(1).execute()
    r = sb.table("charts").select("id,user_id").not_.is_("user_id", "null").limit(1).execute()
    if not r.data:
        pytest.skip("no owned charts")
    assert _resolve_user_id(r.data[0]["id"], sb) == r.data[0]["user_id"]
