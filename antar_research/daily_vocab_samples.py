"""
antar_research/daily_vocab_samples.py — sample/backtest harness for the
Concrete Daily Vocabulary Layer.

Read-only. Computes REAL transits (Swiss Ephemeris, Lahiri) via the SAME adapter
the prod pipeline uses (antar_engine.daily_vocab.adapter), so what you see here
is byte-for-byte what prod will emit. Makes NO writes, touches NO write path.

Usage:
    cd ~/antarai && source venv311/bin/activate
    python -m antar_research.daily_vocab_samples          # 5 sample days/chart
    python -m antar_research.daily_vocab_samples 30       # 30-day backtest sanity

The 5-day default is the review to eyeball before any frontend wiring.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from collections import Counter
from datetime import date, timedelta

from antar_engine.transit_events import _extract_lagna_sign_idx, SIGNS
from antar_engine.daily_vocab import public_view, populated_fields
from antar_engine.daily_vocab.adapter import build_concrete_for_chart

# Your chart (prefix — resolved via PostgREST `like`) + the canonical test chart.
CHARTS = {
    "Raman (you)":            "a4c9d57b",
    "Test chart (de0c6265)":  "de0c6265-96cc-41ba-a39c-e55868fa5806",
}


# ── data access (mirrors antar_research/lk_sleep_qa.py) ──────────────

def _env() -> dict:
    env = {}
    path = os.path.join(os.path.dirname(__file__), "..", ".env")
    for line in open(path):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v.strip().strip('"')
    return env


def _uuid_bounds(id_or_prefix: str):
    """Resolve a uuid prefix via a uuid RANGE (gte/lte). `id` is a uuid column,
    so LIKE doesn't apply (Postgres LIKE is text-only) — but uuid is orderable,
    so a padded-low / padded-high pair brackets every uuid with that prefix.
    A full uuid collapses to low == high (an exact match)."""
    hexs = id_or_prefix.replace("-", "").lower()
    low = hexs.ljust(32, "0")
    high = hexs.ljust(32, "f")
    fmt = lambda h: f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    return fmt(low), fmt(high)


def _fetch_chart(env: dict, id_or_prefix: str) -> dict:
    url = env.get("SUPABASE_URL")
    key = (env.get("SUPABASE_SERVICE_ROLE_KEY")
           or env.get("SUPABASE_KEY") or env.get("SUPABASE_ANON_KEY"))
    low, high = _uuid_bounds(id_or_prefix)
    q = (f"{url}/rest/v1/charts?id=gte.{low}&id=lte.{high}"
         f"&select=id,chart_data&limit=1")
    req = urllib.request.Request(
        q, headers={"apikey": key, "Authorization": "Bearer " + key})
    rows = json.load(urllib.request.urlopen(req, timeout=25))
    if not rows:
        raise SystemExit(f"  !! no chart matched id/prefix {id_or_prefix!r}")
    cd = rows[0]["chart_data"]
    if isinstance(cd, str):
        cd = json.loads(cd)
    return cd


# ── render ───────────────────────────────────────────────────────────

def _print_day(d: date, block: dict):
    fields = populated_fields(block)
    print(f"\n  {d.isoformat()} ({d.strftime('%a')})  —  {len(fields)} field(s)")
    pub = public_view(block)
    order = ["body_focus", "food_lean", "mood_tone", "romance_read",
             "favourable_direction", "lucky_color", "event_watch"]
    for k in order:
        v = pub.get(k)
        if isinstance(v, dict) and v.get("text"):
            conf = block["_debug"].get(k, {}).get("confidence")
            tier = f" [{v['tier']}]" if v.get("tier") else ""
            print(f"      • {k}{tier} ({conf}): {v['text']}")


def main():
    n_days = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    env = _env()
    print("=" * 74)
    print(f"Concrete Daily Vocabulary Layer — {n_days} day(s) per chart")
    print("=" * 74)

    for label, cid in CHARTS.items():
        cd = _fetch_chart(env, cid)
        lagna_idx = _extract_lagna_sign_idx(cd)
        print(f"\n################  {label}  (lagna {SIGNS[lagna_idx]})  ################")

        count_hist = Counter()
        event_days = 0
        confs_seen = set()
        today = date.today()
        for i in range(n_days):
            d = today - timedelta(days=i)
            block = build_concrete_for_chart(cd, on_date=d, language="en")
            _print_day(d, block)
            fields = populated_fields(block)
            count_hist[len(fields)] += 1
            if "event_watch" in fields:
                event_days += 1
            for dd in block["_debug"].values():
                confs_seen.add(dd["confidence"])

        print(f"\n  ── summary ({n_days} days) ──")
        print(f"     field-count distribution: {dict(sorted(count_hist.items()))}")
        print(f"     event_watch days: {event_days}/{n_days}")
        print(f"     distinct confidence values: {len(confs_seen)} "
              f"(min {min(confs_seen):.2f}, max {max(confs_seen):.2f})")


if __name__ == "__main__":
    main()
