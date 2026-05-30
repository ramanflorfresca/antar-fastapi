"""
antar_engine/daily_polarity_log.py

Daily server-side writer for the `chart_daily_headlines` table — the rolling
polarity log that the circuit breaker and crisis floor read from.

Runs for ALL charts every day, decoupled from user requests. This is the whole
point of the crisis floor: a withdrawn user (who stops opening the app) must
still accumulate heavy-day counts, or the floor never fires for the person who
most needs it. So this is hung off a daily cron, NOT the Today endpoint.

Hooked into the APScheduler in main.py via `_daily_polarity_log_job` (see the
patch). Each chart is wrapped in try/except — one chart's failure never aborts
the batch, and a write failure is logged, never surfaced to a user.

Verify on Mac (needs swisseph + Supabase + lk_conditions.py):
    python -c "from antar_engine.daily_polarity_log import run_daily_polarity_log; \
               import main; run_daily_polarity_log(main.supabase)"
"""
from __future__ import annotations
import json
from datetime import date


def _safe_json(v):
    """chart_data may be a JSON string, not native JSONB (project rule 8)."""
    if isinstance(v, str):
        try:
            p = json.loads(v)
            return p if isinstance(p, dict) else {}
        except Exception:
            return {}
    return v if isinstance(v, dict) else {}


def _current_md_lord(supabase, chart_id: str, today_str: str):
    try:
        r = (supabase.table("dasha_periods")
             .select("planet_or_sign")
             .eq("chart_id", chart_id).eq("system", "vimsottari").eq("level", 1)
             .lte("start_date", today_str).gte("end_date", today_str)
             .limit(1).execute())
        if r.data:
            return r.data[0].get("planet_or_sign")
    except Exception as e:
        print(f"[polarity_log] dasha lookup {chart_id[:8]}…: {e}")
    return None


def compute_headline(chart_data: dict, md_lord: str):
    """
    Return (condition_id, polarity) for today, or None if the conditions
    library isn't shipped yet (caller skips writing).
    """
    try:
        from antar_engine.lk_conditions import LK_CONDITIONS
    except Exception:
        return None  # dict not deployed yet
    from antar_engine.transits_engine import calculate_current_transits
    from antar_engine.lk_trigger import matches_trigger
    from antar_engine.composition import pick_headline_and_modifiers

    transits = (calculate_current_transits(chart_data) or {}).get("current_transits", [])
    dasha = {"md_lord": md_lord}

    fired = []
    for cid, cond in LK_CONDITIONS.items():
        try:
            if matches_trigger(cond["trigger"], chart_data, transits, dasha):
                fired.append({**cond, "id": cid})
        except Exception as e:
            print(f"[polarity_log] trigger {cid}: {e}")

    headline, _ = pick_headline_and_modifiers(fired, md_lord)
    if headline is None:
        return ("flat_day", "flat")
    return (headline.get("id"), headline["precedence"]["polarity"])


def run_daily_polarity_log(supabase, today: date | None = None, batch: int = 1000) -> dict:
    """
    Iterate active charts, compute today's headline condition_id + polarity,
    upsert one row per (chart_id, date) into chart_daily_headlines.
    Returns a small summary dict for cron logging.
    """
    today = today or date.today()
    today_str = str(today)
    written = skipped = errored = 0

    try:
        charts = (supabase.table("charts")
                  .select("id, chart_data")
                  .limit(batch).execute()).data or []
    except Exception as e:
        print(f"[polarity_log] FATAL chart fetch: {e}")
        return {"written": 0, "errored": 0, "fatal": str(e)}

    for row in charts:
        chart_id = row.get("id")
        try:
            chart_data = _safe_json(row.get("chart_data"))
            if not chart_data.get("planets"):
                skipped += 1
                continue
            md_lord = _current_md_lord(supabase, chart_id, today_str)
            result = compute_headline(chart_data, md_lord)
            if result is None:
                skipped += 1  # lk_conditions not shipped yet
                continue
            condition_id, polarity = result
            # upsert on (chart_id, date) — wrapped so a write failure is non-fatal
            try:
                supabase.table("chart_daily_headlines").upsert({
                    "chart_id": chart_id,
                    "date": today_str,
                    "condition_id": condition_id,
                    "polarity": polarity,
                }, on_conflict="chart_id,date").execute()
                written += 1
            except Exception as e:
                errored += 1
                print(f"[polarity_log] write {chart_id[:8]}…: {e}")
        except Exception as e:
            errored += 1
            print(f"[polarity_log] chart {str(chart_id)[:8]}…: {e}")

    summary = {"date": today_str, "written": written, "skipped": skipped, "errored": errored}
    print(f"[polarity_log] {summary}")
    return summary
