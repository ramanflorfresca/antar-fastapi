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
