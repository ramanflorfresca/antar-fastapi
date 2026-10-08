"""Live guard (skipped in CI): the Circle chapter line must match each chart's OWN chapter card for every real chart."""
import collections
from datetime import date

import pytest


@pytest.mark.live_db
def test_circle_chapter_matches_each_charts_own_card():
    import main
    from antar_engine import chart_identity as CI, circle_fit as F
    sb = main.supabase
    rows, off = [], 0
    while True:
        pg = sb.table("charts").select("id").is_("deleted_at", "null").not_.is_("chart_data", "null").range(off, off + 999).execute().data or []
        rows += pg
        off += 1000
        if len(pg) < 1000:
            break
    today, bad = date.today(), []
    for r in rows:
        vim = (main.get_dashas_for_chart(r["id"]) or {}).get("vimsottari") or []
        if not vim:
            continue
        se, ch = F.season_at({}, vim, today), CI._running_chapter(vim, today)
        if not se or se["md"] != ch.get("maha") or (se["ad"] and se["ad"] != ch.get("antar")):
            bad.append(r["id"][:8])
            continue
        d = F.describe(se, "en")
        assert d["label"] and "None" not in d["label"]
    assert not bad, f"charts whose Circle chapter differs from their own card: {bad}"
