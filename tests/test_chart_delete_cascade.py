"""
Guards for the chart-delete cascade.

Deleting a chart must take its derived data with it. The list had been
maintained by hand in TWO places — settings_charts_delete and delete_account —
and they drifted 26 tables apart. Production carried 149 orphan rows from
charts that no longer existed, including the users' own questions
(intent_classify_log) and 99 user_preferences rows.
"""
import os
import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="module")
def m():
    import main
    return main


def test_both_delete_paths_share_one_list(m):
    """The drift was the root cause, so the two paths must not diverge again:
    an account delete is the chart cascade PLUS billing."""
    assert set(m._CHART_DERIVED_TABLES) <= set(m._ACCOUNT_DELETE_TABLES)
    assert set(m._ACCOUNT_DELETE_TABLES) - set(m._CHART_DERIVED_TABLES) == set(
        m._ACCOUNT_ONLY_TABLES
    )


def test_billing_is_never_in_a_single_chart_delete(m):
    """A subscription belongs to the account, not one of its charts, and
    dropping the usage counters would let a free-tier quota be reset by
    deleting and recreating a chart."""
    for t in ("subscriptions", "usage_tracking", "compat_slot_purchases", "ask_usage"):
        assert t not in m._CHART_DERIVED_TABLES, f"{t} must not be purged per-chart"


def test_tables_that_previously_leaked_are_covered(m):
    """Every one of these was found holding orphan rows in production."""
    # prediction_accuracy is deliberately absent — it is a VIEW over
    # prediction_accuracy_marks, so its rows go when the marks do.
    for t in ("user_preferences", "intent_classify_log", "user_correlations",
              "prediction_accuracy_marks", "translation_cache", "year_narration_cache",
              "practice_log", "verification_ratings",
              # user content the old list missed entirely
              "conversations", "device_tokens", "signature_question_log",
              "places_saved_cities"):
        assert t in m._CHART_DERIVED_TABLES, f"{t} would leak on chart delete"


def test_every_entry_is_a_real_chart_keyed_deletable_table(m):
    """Three classes of junk were in the list, each failing silently on every
    single delete and filling the response's `partial_cascade` with noise that
    hid real failures:

      - `prediction_accuracy` — a VIEW over prediction_accuracy_marks; a delete
        on it can never succeed.
      - practice_completions / practice_sessions / past_event_feedback — tables
        that do not exist in the schema at all.
      - lal_kitab_remedies (a static remedy library), life_events and
        user_actions (user_id-keyed), prashna_followups (session_id-keyed) —
        real tables with no chart_id column.
    """
    pytest.importorskip("dotenv")
    if not os.getenv("SUPABASE_URL"):
        pytest.skip("needs Supabase")
    nope = "00000000-0000-0000-0000-000000000000"
    bad = []
    for t in list(m._CHART_DERIVED_TABLES) + list(m._ACCOUNT_ONLY_TABLES):
        try:
            m.supabase.table(t).delete().eq("chart_id", nope).execute()
        except Exception as e:
            bad.append((t, str(e)[:60]))
    assert not bad, f"cascade entries that can never delete: {bad}"


def test_static_reference_data_is_never_purged(m):
    """lal_kitab_remedies is a shared library of remedy text, not user data.
    Deleting a chart must not be able to touch it."""
    assert "lal_kitab_remedies" not in m._CHART_DERIVED_TABLES
    assert "lal_kitab_remedies" not in m._ACCOUNT_DELETE_TABLES


def test_no_duplicates_in_the_list(m):
    dupes = {t for t in m._CHART_DERIVED_TABLES
             if list(m._CHART_DERIVED_TABLES).count(t) > 1}
    assert not dupes, f"duplicated table names: {dupes}"


@pytest.mark.skipif(not os.getenv("SUPABASE_URL"), reason="needs Supabase")
def test_no_chart_keyed_table_is_missing_from_the_cascade(m):
    """The real guard: ask the SCHEMA which tables carry a chart_id and assert
    the cascade covers them. A new chart-keyed table fails here until it is
    registered, which is the failure mode that produced this bug."""
    import re
    src = open(os.path.join(os.path.dirname(__file__), "..", "main.py")).read()
    referenced = sorted(set(re.findall(r'\.table\("([a-z_]+)"\)', src)))
    known = set(m._CHART_DERIVED_TABLES) | set(m._ACCOUNT_ONLY_TABLES)
    # tables the cascade deliberately never touches (not chart-scoped, or
    # shared rows handled by their own PII-stripping pass)
    exempt = {"charts", "profiles", "proxy_cache", "compatibility_sessions",
              "chart_connections", "messages", "account_deletions", "app_config",
              "daily_signals_cache_table", "support_logs",
              # a VIEW over prediction_accuracy_marks — it carries a chart_id
              # but cannot be deleted from, and empties when the marks do
              "prediction_accuracy"}
    missing = []
    for t in referenced:
        if t in known or t in exempt:
            continue
        try:
            m.supabase.table(t).select("chart_id").limit(1).execute()
        except Exception:
            continue          # no chart_id column, or table absent
        missing.append(t)
    assert not missing, (
        "chart-keyed tables missing from the delete cascade — they will leak "
        f"when a chart is deleted: {missing}"
    )
