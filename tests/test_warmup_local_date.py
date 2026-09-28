"""
Guard for the warm-up probe's notion of "today".

/api/v1/warmup/status counts cached rows for a chart's LOCAL date, and the
first-run progress screen polls it until today_ready flips true. If the probe
computes a different date than the daily engine, it counts rows that were never
written and the screen hangs at "not ready" forever.

That is exactly what shipped on 2026-09-28: the probe passed a country NAME
("India") into _COUNTRY_TZ_OFFSETS, which is keyed by ISO CODE ("IN"), missed,
and fell back to UTC. Live India chart: probe said 2026-09-28, the engine had
written 2026-09-29.
"""
import re
import os
import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="module")
def m():
    import main
    return main


def _warmup_code() -> str:
    """warmup_status's source with comments stripped — the prose explaining the
    old bug naturally mentions the very call the tests forbid."""
    src = open(os.path.join(os.path.dirname(__file__), "..", "main.py")).read()
    body = src[src.index("async def warmup_status("):]
    if "\n@app." in body:
        body = body[:body.index("\n@app.")]
    return "\n".join(re.sub(r"#.*$", "", ln) for ln in body.split("\n"))


def test_country_offsets_are_keyed_by_iso_code_not_name(m):
    """The bug in one assertion: the table speaks codes, not names."""
    t = m._COUNTRY_TZ_OFFSETS
    assert t.get("IN") == 5.5, "expected the ISO code 'IN' to carry India's offset"
    assert "INDIA" not in t, (
        "the offsets table is keyed by ISO code; a country NAME must never be "
        "used to look it up"
    )


def test_warmup_resolves_today_the_same_way_daily_signal_does(m):
    """Both must derive the local date from the geocoded IANA offset, falling
    back to the RAW country code — never a name, never bare UTC."""
    body = _warmup_code()

    assert "_resolve_current_moment_location" in body, (
        "warmup_status must resolve the current-location timezone like "
        "/daily-signal, or the two disagree about what day it is"
    )
    assert "_iana_offset_hours" in body
    assert "_get_local_start_date(tz_offset=" in body, (
        "warmup_status must pass an explicit tz_offset; passing current_country "
        "routes through a name/code lookup that silently falls back to UTC"
    )
    assert "_country_name(" not in body, (
        "_country_name() yields a display NAME; _COUNTRY_TZ_OFFSETS is keyed by "
        "ISO CODE, so this lookup misses and the probe falls back to UTC"
    )


def test_warmup_keeps_its_db_calls_off_the_event_loop(m):
    """It is polled every few seconds while the progress screen is up, so its
    synchronous supabase calls must not run on the loop."""
    body = _warmup_code()
    for frag in ('supabase.table("charts")',
                 'supabase.table("daily_signals_cache")',
                 "_daily_surface_get"):
        idx = body.index(frag)
        window = body[max(0, idx - 260):idx]
        assert "run_in_threadpool" in window, f"{frag} is not offloaded"
