"""antar_engine/dasha_audit.py

Nightly audit: does every live chart still have the dasha rows every dasha-aware surface reads?

Why: creation swallowed dasha failures for months (13 charts ended with no rows, 6 early ones with no vimsottari antardasha,
most with no pratyantar level) and nothing noticed. Write failures now alert (dasha_heal.alert_failure); this catches what
fails WITHOUT an exception, and repairs what it finds with the same insert-only functions heal-on-read uses.

Per chart, three classes (each a limit-1 query, so cost is ~3 round trips per chart):
    no_rows  - no dasha_periods row at all                      -> dasha_heal.heal (all systems, 3 vimsottari levels)
    no_ad    - rows, but no vimsottari antardasha (level 2)     -> dasha_heal.heal -> complete_vimsottari
    no_pd    - antardashas but no pratyantar (level 3)          -> dasha_heal.backfill_pratyantars

Nightly it looks at charts created in the last RECENT_DAYS (where a creation failure shows up); on Sundays it checks them all.
Never raises. Alerts (log line always; webhook/email if configured): a warn when it found and fixed gaps, an error when a gap
is still there after the repair attempt."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

RECENT_DAYS = 14
MAX_REPAIRS = 25


def _any(supabase, chart_id: str, **flt) -> bool:
    q = supabase.table("dasha_periods").select("id").eq("chart_id", chart_id)
    for k, v in flt.items():
        q = q.eq(k, v)
    return bool(q.limit(1).execute().data)


def classify(supabase, chart_id: str) -> Optional[str]:
    if not _any(supabase, chart_id):
        return "no_rows"
    if not _any(supabase, chart_id, system="vimsottari", level=2):
        return "no_ad"
    if not _any(supabase, chart_id, system="vimsottari", level=3):
        return "no_pd"
    return None


def _chart_ids(supabase, since: Optional[datetime]) -> List[str]:
    out, o = [], 0
    while True:
        q = supabase.table("charts").select("id").is_("deleted_at", "null")
        if since is not None:
            q = q.gte("created_at", since.isoformat())
        r = q.order("id").range(o, o + 999).execute().data or []
        out += [x["id"] for x in r]
        if len(r) < 1000:
            return out
        o += 1000


def _repair(supabase, chart_id: str, cls: str) -> int:
    from antar_engine import dasha_heal as dh
    return dh.backfill_pratyantars(supabase, chart_id) if cls == "no_pd" else dh.heal(supabase, chart_id)


def audit(supabase, full: bool = False, repair: bool = True, max_repairs: int = MAX_REPAIRS,
          now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    try:
        ids = _chart_ids(supabase, None if full else now - timedelta(days=RECENT_DAYS))
    except Exception as e:
        return {"ok": False, "error": f"chart list failed: {str(e)[:160]}"}
    found: Dict[str, List[str]] = {"no_rows": [], "no_ad": [], "no_pd": []}
    errors = 0
    for cid in ids:
        try:
            cls = classify(supabase, cid)
        except Exception:
            errors += 1
            continue
        if cls:
            found[cls].append(cid)
    fixed: List[str] = []
    still: List[str] = []
    n_repairs = 0
    for cls, cids in found.items():
        for cid in cids:
            if not repair or n_repairs >= max_repairs:
                still.append(cid)
                continue
            n_repairs += 1
            try:
                _repair(supabase, cid, cls)
                (fixed if classify(supabase, cid) is None else still).append(cid)
            except Exception:
                still.append(cid)
    res = {"ok": True, "checked": len(ids), "full": full, "gaps": {k: len(v) for k, v in found.items()},
           "fixed": len(fixed), "still_broken": len(still), "errors": errors, "still_ids": still[:20]}
    total = sum(res["gaps"].values())
    try:
        from antar_engine.alerting import alert
        if still:
            alert("dasha_audit:unrepaired", f"{len(still)} of {len(ids)} charts still have dasha gaps after repair: "
                  f"{res['gaps']}", level="error", detail=",".join(c[:8] for c in still[:20]))
        elif total:
            alert("dasha_audit:repaired", f"found and repaired dasha gaps on {total} charts: {res['gaps']}", level="warn")
    except Exception:
        pass
    return res
