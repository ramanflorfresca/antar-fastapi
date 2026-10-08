"""Shared test guards.

[ci-full-suite 2026-10-05] A handful of tests check the LIVE schema — that a
column the code SELECTs really exists, that every table in the delete cascade is
really deletable, that /ask answers for a real chart row. They are among the
most valuable tests here, because the bugs they catch (a phantom column turning
a lookup into a constant, a chart-keyed table missing from the PII purge) are
silent in production.

They cannot run against a placeholder database. They used to skip on
`not SUPABASE_URL`, which a CI placeholder satisfies — so they RAN in CI and
failed, which is why the full suite was never wired into CI at all.

Mark such a test `@pytest.mark.live_db`. It is skipped whenever
ANTAR_SKIP_LIVE_DB_TESTS is set (CI does) or SUPABASE_URL is absent, and runs
normally on a developer machine with a real .env.
"""
import os

import pytest

try:  # the test modules each call load_dotenv(), but that runs AFTER this file —
    from dotenv import load_dotenv   # without it a developer's live_db tests
    load_dotenv()                    # would silently skip on a real machine.
except Exception:
    pass

_SKIP = os.getenv("ANTAR_SKIP_LIVE_DB_TESTS", "").strip().lower() in ("1", "true", "yes")
HAVE_LIVE_DB = bool(os.getenv("SUPABASE_URL")) and not _SKIP


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live_db: needs a real Supabase; skipped when ANTAR_SKIP_LIVE_DB_TESTS=1")


def pytest_collection_modifyitems(config, items):
    if HAVE_LIVE_DB:
        return
    skip = pytest.mark.skip(reason="needs a live Supabase (ANTAR_SKIP_LIVE_DB_TESTS is set)")
    for item in items:
        if "live_db" in item.keywords:
            item.add_marker(skip)


# ── [wa-consent-hermetic 2026-10-05] never touch the live WhatsApp consent table ──
# With a real .env that table is the LIVE one, so a test that forgets to stub the consent gate would
# pass/fail by machine (CI has no creds and only ever saw the lookup fail open). Stub
# messaging.policy_state / policy_accepted instead (see `_Conv` in test_whatsapp_channel.py).

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


# ── [wa-log-hermetic 2026-10-08] never let a unit test write WhatsApp message rows to a REAL database ──
# wa_log.record() is fire-and-forget on a thread pool, so a test that drives the WhatsApp handlers wrote its fake traffic
# (+919812345678 "When will I change jobs?", ...) into the live `wa_messages` table whenever the run had the real .env
# loaded (a developer machine without placeholder env): 134 such rows were found in production, polluting the training
# export and the support view. Every test now gets a pool that drops the writes; a test that wants to see them replaces
# `wa_log._write` itself (monkeypatch), which still works.
@pytest.fixture(autouse=True)
def _no_live_wa_log_writes(monkeypatch):
    try:
        from antar_engine import wa_log
    except Exception:
        return

    class _Drop:
        def submit(self, *a, **k):
            return None

    monkeypatch.setattr(wa_log, "_pool", _Drop())
