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


@pytest.mark.live_db
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


def test_profile_pointer_clear_names_no_phantom_column(m):
    """profiles has no `chart_id` column (renamed to primary_chart_id). Clearing
    it returned PGRST204 in `partial_cascade` on every chart delete (seen live
    2026-10-03, chart ab780058)."""
    assert "chart_id" not in m._PROFILE_CHART_POINTER_COLS
    assert "primary_chart_id" in m._PROFILE_CHART_POINTER_COLS
    import inspect
    src = inspect.getsource(m.settings_charts_delete)
    assert '"primary_chart_id", "chart_id"' not in src


@pytest.mark.live_db
def test_profile_pointer_cols_are_real_columns(m):
    if not os.getenv("SUPABASE_URL"):
        pytest.skip("needs Supabase")
    bad = []
    for col in m._PROFILE_CHART_POINTER_COLS:
        try:
            m.supabase.table("profiles").select(col).limit(1).execute()
        except Exception as e:
            bad.append((col, str(e)[:60]))
    assert not bad, f"profiles pointer columns that do not exist: {bad}"


def test_static_reference_data_is_never_purged(m):
    """lal_kitab_remedies is a shared library of remedy text, not user data.
    Deleting a chart must not be able to touch it."""
    assert "lal_kitab_remedies" not in m._CHART_DERIVED_TABLES
    assert "lal_kitab_remedies" not in m._ACCOUNT_DELETE_TABLES


def test_no_duplicates_in_the_list(m):
    dupes = {t for t in m._CHART_DERIVED_TABLES
             if list(m._CHART_DERIVED_TABLES).count(t) > 1}
    assert not dupes, f"duplicated table names: {dupes}"


@pytest.mark.live_db
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


# ── Timeout-safe deletes ────────────────────────────────────────────────────
# A chart owns ~1,100 dasha_periods rows. Removing them in one statement came
# back 57014 "canceling statement due to statement timeout" against production,
# and because every cascade delete is wrapped in a try/except so it can never
# block a user-facing delete, the timeout just logged a warning and left the
# rows behind.


class _FakeTable:
    """Minimal stand-in for supabase.table(...) — records what it was asked."""

    def __init__(self, store, name):
        self.store, self.name = store, name
        self._op = None
        self._filters = []
        self._limit = None

    def delete(self):
        self._op = "delete"
        return self

    def select(self, _cols):
        self._op = "select"
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def in_(self, col, vals):
        self._filters.append(("in", col, list(vals)))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        rows = self.store["rows"]
        if self._op == "delete":
            kind, col, val = self._filters[-1]
            if kind == "eq":
                self.store["single_stmt_attempts"] += 1
                if self.store["timeout_single_stmt"]:
                    raise RuntimeError(
                        "{'message': 'canceling statement due to statement "
                        "timeout', 'code': '57014'}"
                    )
                self.store["rows"] = []
            else:
                self.store["batches"].append(len(val))
                self.store["rows"] = [r for r in rows if r["id"] not in set(val)]
            return type("R", (), {"data": []})()
        # select — PostgREST caps a page, and so does the caller
        page = self.store["rows"][: (self._limit or 1000)]
        return type("R", (), {"data": list(page)})()


def _fake_supabase(row_count, timeout_single_stmt):
    store = {
        "rows": [{"id": i} for i in range(row_count)],
        "batches": [],
        "single_stmt_attempts": 0,
        "timeout_single_stmt": timeout_single_stmt,
    }
    client = type("C", (), {"table": lambda self, n: _FakeTable(store, n)})()
    return client, store


def test_small_table_still_deletes_in_one_statement(m, monkeypatch):
    """The fast path must stay the default — 40-odd small tables would pay for
    an extra round trip each otherwise."""
    client, store = _fake_supabase(12, timeout_single_stmt=False)
    monkeypatch.setattr(m, "supabase", client)

    m._delete_rows_by("user_alerts", "chart_id", "cid")

    assert store["single_stmt_attempts"] == 1
    assert store["batches"] == []
    assert store["rows"] == []


def test_a_timeout_falls_back_to_batches_and_still_clears_the_table(m, monkeypatch):
    """1,119 rows is a real dasha_periods count. The batch pass must remove all
    of them, not the first page — PostgREST caps a select at 1000."""
    client, store = _fake_supabase(1119, timeout_single_stmt=True)
    monkeypatch.setattr(m, "supabase", client)

    m._delete_rows_by("dasha_periods", "chart_id", "cid")

    assert store["single_stmt_attempts"] == 1, "should try the cheap path first"
    assert store["rows"] == [], "every row must go, including past the 1000 cap"
    assert sum(store["batches"]) == 1119
    assert max(store["batches"]) <= m._DELETE_BATCH


def test_the_batch_pass_gives_up_loudly_rather_than_looping_forever(m, monkeypatch):
    """If rows keep reappearing, the caller must SEE it — silence here is the
    whole reason the timeout went unnoticed."""
    client, store = _fake_supabase(5, timeout_single_stmt=True)

    class _NeverDeletes(_FakeTable):
        def execute(self):
            if self._op == "delete" and self._filters[-1][0] == "in":
                return type("R", (), {"data": []})()   # accepts, removes nothing
            return super().execute()

    monkeypatch.setattr(
        m, "supabase", type("C", (), {"table": lambda s, n: _NeverDeletes(store, n)})()
    )
    with pytest.raises(RuntimeError, match="batched passes"):
        m._delete_rows_by("dasha_periods", "chart_id", "cid")
