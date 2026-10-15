"""Home calls /horizon, which awaits the monthly deep-dive and the annual plan. Both are `async def`, so a plain blocking database call
or a cold dasha fetch inside them freezes the WHOLE server (every other request waits) for its duration: a cold get_dashas_for_chart is
~4.7 s on a large chart. Those calls must run in a thread."""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "main.py"
HANDLERS = ("get_monthly_deepdive", "get_annual_plan")


def _body(name: str) -> str:
    src = SRC.read_text()
    i = src.index("async def " + name + "(")
    j = min(x for x in (src.find("\n@app.", i), src.find("\nasync def ", i + 10), src.find("\ndef ", i + 10)) if x > 0)
    return src[i:j]


def test_no_blocking_database_call_runs_on_the_event_loop_in_these_handlers():
    for name in HANDLERS:
        b = _body(name)
        # every `supabase.table(...)...execute()` chain must sit inside run_in_threadpool(lambda: ...)
        for m in re.finditer(r"supabase\.table\(", b):
            pre = b[max(0, m.start() - 40):m.start()]
            assert "run_in_threadpool(lambda:" in pre or "lambda:" in pre, f"{name}: a blocking database call is not offloaded: {b[m.start():m.start()+80]!r}"


def test_the_dasha_fetch_is_always_offloaded():
    for name in HANDLERS:
        b = _body(name)
        for m in re.finditer(r"get_dashas_for_chart\(", b):
            pre = b[max(0, m.start() - 60):m.start()]
            assert "lambda:" in pre or "run_in_threadpool(get_dashas_for_chart" in b[max(0, m.start() - 30):m.start() + 30], \
                f"{name}: get_dashas_for_chart runs on the event loop: {b[m.start()-40:m.start()+50]!r}"
        assert "run_in_threadpool(get_dashas_for_chart" in b or "run_in_threadpool(lambda: get_dashas_for_chart" in b


# ── second pass (found with a stall watchdog on a cold server, May the main thread never be held by our code) ───────
def _fn(name: str, kind: str = "def") -> str:
    src = SRC.read_text()
    i = src.index(f"{kind} {name}(")
    j = min(x for x in (src.find("\n@app.", i), src.find("\nasync def ", i + 10), src.find("\ndef ", i + 10)) if x > 0)
    return src[i:j]


def test_the_life_alert_sync_is_a_plain_function_called_in_a_thread():
    """_sync_life_alerts was `async def` with no await: all its database reads, the dasha fetch and the alert building ran ON the event
    loop, once per Home load (via /alerts) and once per WhatsApp send."""
    src = SRC.read_text()
    assert "\ndef _sync_life_alerts(chart_id: str):" in src and "async def _sync_life_alerts" not in src
    assert "await _sync_life_alerts(" not in src
    assert src.count("await run_in_threadpool(_sync_life_alerts,") == 2


def test_the_moment_location_lookup_does_not_query_on_the_event_loop():
    b = _fn("_resolve_current_moment_location", "async def")
    for m in re.finditer(r"supabase\.table\(", b):
        assert "run_in_threadpool(lambda:" in b[max(0, m.start() - 40):m.start()], b[m.start():m.start() + 80]


def test_the_monthly_cache_read_is_offloaded():
    b = _body("get_monthly_deepdive")
    assert "await run_in_threadpool(_md_read_cache," in b and "else _md_read_cache(" not in b
