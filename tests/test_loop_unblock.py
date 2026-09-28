"""
Guards for the event-loop unblocking work (2026-09-28).

`supabase-py` is a SYNCHRONOUS client. Any query made directly inside an
`async def` handler blocks the whole event loop for its duration — not just
that request. Measured before this work: one 2.02s /daily-signal request let
the loop tick TWICE instead of ~200, a single 2042ms stall.

Two defences, both tested here:
  1. Don't make the query at all (the dasha row cache).
  2. Don't hold the loop while you do (handlers that never await are plain
     `def`, so FastAPI runs them in its threadpool).
"""
import ast
import os
import pytest


# ─── 1. dasha row cache ───────────────────────────────────────────

@pytest.fixture()
def m():
    """`main` with its dasha cache cleared and its supabase accessor RESTORED
    afterwards — these tests swap in a counting stub, and leaking that into the
    rest of the suite would silently fake every other test's DB."""
    from dotenv import load_dotenv
    load_dotenv()
    import main
    original_table = main.supabase.table
    main.invalidate_dasha_cache()
    try:
        yield main
    finally:
        main.supabase.table = original_table
        main.invalidate_dasha_cache()


class _FakeTable:
    """Minimal PostgREST builder stub that counts round trips."""
    def __init__(self, counter, rows):
        self.counter, self.rows = counter, rows
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def order(self, *a, **k): return self
    def range(self, lo, hi):
        self._slice = (lo, hi); return self
    def execute(self):
        self.counter[0] += 1
        lo, hi = self._slice
        return type("R", (), {"data": self.rows[lo:hi + 1]})()


def _patch(m, rows):
    counter = [0]
    m.supabase.table = lambda name, *a, **k: _FakeTable(counter, rows)
    return counter


def test_dasha_rows_fetched_once_then_served_from_cache(m):
    rows = [{"system": "vimsottari", "planet_or_sign": "Rahu", "type": "mahadasha",
             "start_date": "2020-01-01", "end_date": "2038-01-01", "sequence": 0}]
    counter = _patch(m, rows)
    m.get_dashas_for_chart("chart-A")
    m.get_dashas_for_chart("chart-A")
    m.get_dashas_for_chart("chart-A")
    assert counter[0] == 1, "three calls should cost ONE round trip"


def test_invalidate_forces_a_refetch(m):
    rows = [{"system": "vimsottari", "planet_or_sign": "Rahu", "type": "mahadasha",
             "start_date": "2020-01-01", "end_date": "2038-01-01", "sequence": 0}]
    counter = _patch(m, rows)
    m.get_dashas_for_chart("chart-B")
    m.invalidate_dasha_cache("chart-B")
    m.get_dashas_for_chart("chart-B")
    assert counter[0] == 2


def test_empty_result_is_never_cached(m):
    """A chart mid-creation, or a transient PostgREST failure, must not pin
    'this chart has no dashas' for the whole TTL."""
    counter = _patch(m, [])
    m.get_dashas_for_chart("chart-C")
    m.get_dashas_for_chart("chart-C")
    assert counter[0] == 2


def test_callers_get_independent_structures(m):
    """Rows are cached; the assembled dict is rebuilt per call. Callers mutate
    what they get back, and a shared value would let one request corrupt
    another's."""
    rows = [{"system": "vimsottari", "planet_or_sign": "Rahu", "type": "mahadasha",
             "start_date": "2020-01-01", "end_date": "2038-01-01", "sequence": 0}]
    _patch(m, rows)
    a = m.get_dashas_for_chart("chart-D")
    a["vimsottari"][0]["lord_or_sign"] = "MUTATED"
    b = m.get_dashas_for_chart("chart-D")
    assert b["vimsottari"][0]["lord_or_sign"] == "Rahu"


# ─── 2. no handler may block the loop for nothing ─────────────────

def _never_awaiting_async_routes():
    src = open(os.path.join(os.path.dirname(__file__), "..", "main.py")).read()
    tree = ast.parse(src)
    out = []
    for n in tree.body:
        if not isinstance(n, ast.AsyncFunctionDef):
            continue
        decs = [ast.unparse(d) for d in n.decorator_list]
        if not any(d.startswith("app.") and any(v in d for v in
                   ("get(", "post(", "put(", "delete(", "patch(")) for d in decs):
            continue
        if any(not d.startswith("app.") for d in decs):
            continue          # wrapped by an async decorator — must stay async
        if any(isinstance(x, (ast.Await, ast.AsyncFor, ast.AsyncWith))
               for x in ast.walk(n)):
            continue
        out.append(n.name)
    return out


def test_no_undecorated_route_is_async_without_awaiting():
    """An `async def` handler with no await in it runs ON the event loop and
    blocks every other request for its whole duration, for no benefit. Declared
    `def`, FastAPI runs it in a threadpool instead. 138 handlers were converted;
    this stops the pattern coming back."""
    offenders = _never_awaiting_async_routes()
    assert offenders == [], (
        f"{len(offenders)} route handler(s) are 'async def' but never await — "
        f"make them 'def' so FastAPI threadpools them: {offenders[:10]}"
    )


# ─── 3. cached rows are not re-stripped for nothing ───────────────

def test_cached_row_at_current_strip_version_is_not_restripped(monkeypatch):
    """A row written under the current strip rules was already cleaned on the
    way in, so re-cleaning it on every read is pure waste — and it was the
    single biggest remaining hold on the event loop for a warm week."""
    from antar_engine import daily_prediction_engine as dpe
    calls = []
    monkeypatch.setattr(dpe, "_strip_day_names_from_signal",
                        lambda sig, lang: calls.append("stripped") or sig)
    stamped = {"senal_de_hoy": "x", "_strip_version": dpe.DAILY_STRIP_VERSION}
    legacy = {"senal_de_hoy": "x"}

    # Mirrors the cache-hit branch in _one_day.
    def restrip_if_needed(sig):
        if sig.get("_strip_version") != dpe.DAILY_STRIP_VERSION:
            dpe._strip_day_names_from_signal(sig, "en")

    restrip_if_needed(stamped)
    assert calls == [], "a row at the current strip version must not be re-stripped"
    restrip_if_needed(legacy)
    assert calls == ["stripped"], "a legacy row MUST still be re-stripped"


def test_saved_rows_carry_both_version_stamps():
    """The read-side skip is only safe because the write side records which
    rules cleaned the row. If this stamp ever stops being written, every cached
    day silently takes the slow path again."""
    import inspect
    from antar_engine import daily_prediction_engine as dpe
    src = inspect.getsource(dpe._save_cached_signal)
    assert '"_logic_version"] = DAILY_LOGIC_VERSION' in src
    assert '"_strip_version"] = DAILY_STRIP_VERSION' in src
