"""antar_engine/dasha_heal.py

Rebuild the dasha_periods rows of a chart that has NONE, exactly as chart creation writes them.

Why: creation computes the dashas and inserts them inside try/except blocks that only print, so any failure there (the
person-chart normaliser bug fixed 2026-10-11 produced [] for every person added before it) left a chart with no rows,
and every dasha-aware surface then silently ran without a running period. This is the repair path:

  * `heal(supabase, chart_id)` — insert-only (NEVER deletes), and only when the chart has zero rows right now.
  * `schedule(supabase, chart_id)` — fire-and-forget on a daemon thread, once per chart per process, retried at most
    every RETRY_SECS after a failure; called from get_dashas_for_chart when a read finds no rows.

Row shape mirrors main._create_chart_for_user so the readers see no difference."""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, List, Optional

RETRY_SECS = 900.0
_LOCK = threading.Lock()
_INFLIGHT: set = set()
_NEXT_TRY: Dict[str, float] = {}
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn",
         "Aquarius", "Pisces"]


def _flat(raw) -> List[dict]:
    """The dasha modules return {mahadashas:[…], antardashas:[…]} or a flat list (Jaimini): one flat list."""
    if isinstance(raw, list):
        out = []
        for it in raw:
            if not isinstance(it, dict):
                continue
            lord = it.get("lord_or_sign", "") or it.get("lord", "") or it.get("sign", "") or it.get("planet_or_sign", "")
            out.append({"planet_or_sign": lord, "start_date": str(it.get("start_date", "") or it.get("start", ""))[:10],
                        "end_date": str(it.get("end_date", "") or it.get("end", ""))[:10],
                        "duration_years": it.get("duration_years", 0), "level": it.get("level", "mahadasha"),
                        "parent_lord": it.get("parent_lord", "")})
        return out
    if not isinstance(raw, dict):
        return []
    out = []
    for key, level in (("mahadashas", "mahadasha"), ("antardashas", "antardasha")):
        for p in raw.get(key, []):
            lord = p.get("lord", "") or p.get("sign", "") or p.get("lord_or_sign", "")
            out.append({"planet_or_sign": lord, "start_date": str(p.get("start_date", "") or "")[:10],
                        "end_date": str(p.get("end_date", "") or "")[:10], "duration_years": p.get("duration_years", 0),
                        "level": level, "parent_lord": p.get("parent_lord", "") if level == "antardasha" else ""})
    return out


def compute(chart_data: dict, birth_date: str) -> Dict[str, List[dict]]:
    """{system: flat periods}; a system that fails to compute is left empty (and logged), never raises."""
    from antar_engine import vimsottari, ashtottari
    out: Dict[str, List[dict]] = {"vimsottari": [], "jaimini": [], "ashtottari": []}
    bjd = (chart_data or {}).get("birth_jd")
    try:
        out["vimsottari"] = _flat(vimsottari.calculate_vimsottari_from_chart(chart_data, bjd))
    except Exception as e:
        print(f"[dasha-heal] vimsottari failed: {e}")
    try:
        import datetime as _dt
        from antar_engine import jaimini
        from antar_engine.jaimini import build_planet_map
        lagna = chart_data.get("lagna", {})
        lagna_sign = lagna.get("sign", "Aries") if isinstance(lagna, dict) else "Aries"
        idx = SIGNS.index(lagna_sign) if lagna_sign in SIGNS else 0
        longs = {p: (SIGNS.index(d.get("sign", "Aries")) * 30 + d.get("degree", 0))
                 for p, d in chart_data.get("planets", {}).items() if d.get("sign", "") in SIGNS}
        out["jaimini"] = _flat(jaimini.compute_jaimini_dashas(idx, build_planet_map(longs),
                                                              _dt.date.fromisoformat(str(birth_date)[:10])))
    except Exception as e:
        print(f"[dasha-heal] jaimini failed: {e}")
    try:
        out["ashtottari"] = _flat(ashtottari.calculate_ashtottari_from_chart(chart_data, bjd))
    except Exception as e:
        print(f"[dasha-heal] ashtottari failed: {e}")
    return out


def build_rows(chart_id: str, systems: Dict[str, List[dict]]) -> List[dict]:
    rows = []
    for system in ("vimsottari", "jaimini", "ashtottari"):
        for i, p in enumerate(systems.get(system) or []):
            level_name = p.get("level", "mahadasha")
            rows.append({
                "chart_id": chart_id, "system": system, "type": level_name,
                "level": 1 if level_name == "mahadasha" else (2 if level_name == "antardasha" else 3),
                "planet_or_sign": p.get("planet_or_sign", ""), "start_date": p.get("start_date", ""),
                "end_date": p.get("end_date", ""), "duration_years": p.get("duration_years", 0),
                "sequence": i, "parent_id": None,
                "metadata": {"parent_lord": p.get("parent_lord", ""), "type": level_name},
            })
    return rows


def _has_rows(supabase, chart_id: str) -> bool:
    return bool(supabase.table("dasha_periods").select("id").eq("chart_id", chart_id).limit(1).execute().data)


def heal(supabase, chart_id: str, dry_run: bool = False) -> int:
    """Insert the chart's dasha rows if it has none. Returns the number of rows inserted (or that would be)."""
    if _has_rows(supabase, chart_id):
        return 0
    res = supabase.table("charts").select("chart_data,birth_date").eq("id", chart_id).execute().data
    if not res:
        return 0
    cd = res[0].get("chart_data")
    if isinstance(cd, str):
        cd = json.loads(cd)
    if not isinstance(cd, dict) or not cd.get("planets"):
        return 0
    rows = build_rows(chart_id, compute(cd, res[0].get("birth_date") or ""))
    if not any(r["system"] == "vimsottari" for r in rows):
        return 0                                    # nothing trustworthy to store: leave the chart as it is
    if dry_run:
        return len(rows)
    if _has_rows(supabase, chart_id):               # another worker healed it while we computed
        return 0
    for i in range(0, len(rows), 100):
        supabase.table("dasha_periods").insert(rows[i:i + 100]).execute()
    try:
        from antar_engine import dasha_cache
        dasha_cache.invalidate(chart_id)
    except Exception:
        pass
    return len(rows)


def schedule(supabase, chart_id: str) -> bool:
    """Heal `chart_id` on a daemon thread. At most one attempt in flight per chart, and one per RETRY_SECS."""
    if not chart_id:
        return False
    with _LOCK:
        if chart_id in _INFLIGHT or time.monotonic() < _NEXT_TRY.get(chart_id, 0.0):
            return False
        _INFLIGHT.add(chart_id)
        _NEXT_TRY[chart_id] = time.monotonic() + RETRY_SECS

    def _run():
        try:
            n = heal(supabase, chart_id)
            print(f"[dasha-heal] chart={chart_id[:8]} inserted {n} rows")
        except Exception as e:
            print(f"[dasha-heal] chart={chart_id[:8]} failed (will retry later): {str(e)[:160]}")
        finally:
            with _LOCK:
                _INFLIGHT.discard(chart_id)

    threading.Thread(target=_run, name="dasha-heal", daemon=True).start()
    return True
