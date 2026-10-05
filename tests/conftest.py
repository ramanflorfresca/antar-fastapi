"""Suite-wide guards.

The WhatsApp consent gate reads `wa_policy_acceptances`. With a real `.env` present that is the LIVE
table, so a test that forgets to stub the gate passes or fails depending on whose machine runs it
(CI has no credentials, so it only ever saw the lookup fail open). Any real-client access to that
table now fails loudly — stub `messaging.policy_state` (see `_Conv` / `stub_policy`) instead.
"""
import pytest

_GUARDED_TABLES = {"wa_policy_acceptances"}


class RealPolicyTableAccess(BaseException):
    """BaseException so the handler's `except Exception` fail-open can't swallow it."""


@pytest.fixture(autouse=True)
def _no_live_wa_policy_table(monkeypatch):
    try:
        from supabase import Client
    except Exception:       # supabase not importable → nothing real to guard
        return
    real_table = Client.table

    def guarded(self, name, *a, **k):
        if name in _GUARDED_TABLES:
            raise RealPolicyTableAccess(
                f"test reached the real Supabase table {name!r}; stub messaging.policy_state/policy_accepted")
        return real_table(self, name, *a, **k)
    monkeypatch.setattr(Client, "table", guarded)
