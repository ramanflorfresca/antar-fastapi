"""antar_engine/kp/kp_hourly.py

KP HOURLY shadow — computed + stored, NEVER user-facing (KP's validation gate is closed; see kp_daily.py).

Today's "Best window" is the Abhijit muhurta and "Steer clear" is Rahu Kalam: the same for everyone at one
place. This computes the chart-specific alternative a KP reader would give — the Moon's SUB lord, which turns every
few hours — so the two can be compared against what actually happened before anything is shown:

    for each stretch of the local day: Moon's (star lord, sub lord)  ->  houses the sub lord signifies in THIS
    natal KP chart, weighted by KP significator level (L1 strongest)  ->  net = gain houses 2/10/11 minus loss
    houses 8/12  ->  lean (positive net >= 0.5, adverse net <= -0.5, else neutral). The raw net is stored so the cut
    can be tuned offline. Promotion requirement (owner): the user-facing best/avoid must be ONE tight stretch of about
1-2.5 hours (`kp_best_tight` / `kp_avoid_tight`), never the multi-hour runs.

then best = longest positive run in waking hours, avoid = longest adverse run, and the overlap with the current
Abhijit / Rahu windows is recorded so the comparison is one query. House sets match kp_daily.py (6 excluded: dual).
Never raises; any failure returns {available: False, reason}."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_POS_HOUSES = {2, 10, 11}
_NEG_HOUSES = {8, 12}
STEP_MIN = 10
WAKING = (6 * 60, 22 * 60)          # minutes from local midnight


def enabled() -> bool:
    """KP_HOURLY_SHADOW=off turns the shadow off (default on: it is computed and stored only)."""
    return os.getenv("KP_HOURLY_SHADOW", "on").strip().lower() not in ("off", "0", "false", "no")


_LEVEL_W = {"L1": 1.0, "L2": 0.75, "L3": 0.5, "L4": 0.25}     # KP: a planet in a house's strongest level counts most
LEAN_CUT = 0.5


def planet_house_strength(house_sig: dict) -> Dict[str, Dict[int, float]]:
    """{planet: {house: weight}} from the 4-level house significators (strongest level wins)."""
    out: Dict[str, Dict[int, float]] = {}
    for h in range(1, 13):
        for lvl, w in _LEVEL_W.items():
            for p in (house_sig.get(h, {}).get(lvl) or []):
                cur = out.setdefault(p, {})
                cur[h] = max(cur.get(h, 0.0), w)
    return out


def net_score(strength: Dict[int, float]) -> float:
    """Gain houses (2/10/11) minus loss houses (8/12), each weighted by its significator level."""
    return round(sum(w for h, w in (strength or {}).items() if h in _POS_HOUSES)
                 - sum(w for h, w in (strength or {}).items() if h in _NEG_HOUSES), 3)


def lean_for(net: float) -> str:
    return "positive" if net >= LEAN_CUT else ("adverse" if net <= -LEAN_CUT else "neutral")


def _moon_chain(jd_utc: float) -> Dict[str, str]:
    import swisseph as swe
    from . import kp_chart as K
    K._assert_kp_ayanamsa()
    lon = (swe.calc_ut(jd_utc, swe.MOON)[0][0] - swe.get_ayanamsa_ut(jd_utc)) % 360.0
    r = K.resolve_sublord(lon)
    return {"star_lord": r["star_lord"], "sub_lord": r["sub_lord"], "nakshatra": r["nakshatra"]}


def moon_sub_timeline(local_date: date, tz_hours: float, step_min: int = STEP_MIN) -> List[Dict[str, Any]]:
    """Segments of the local day: [{start_min, end_min, star_lord, sub_lord, nakshatra}] (minutes from local
    midnight), consecutive identical (star, sub) merged."""
    import swisseph as swe
    out: List[Dict[str, Any]] = []
    for m in range(0, 24 * 60, step_min):
        utc = datetime(local_date.year, local_date.month, local_date.day, tzinfo=timezone.utc) \
            + timedelta(minutes=m) - timedelta(hours=float(tz_hours))
        jd = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60.0)
        c = _moon_chain(jd)
        if out and out[-1]["star_lord"] == c["star_lord"] and out[-1]["sub_lord"] == c["sub_lord"]:
            out[-1]["end_min"] = m + step_min
        else:
            out.append({"start_min": m, "end_min": m + step_min, **c})
    return out


def _hhmm(m: int) -> str:
    m = max(0, min(24 * 60, int(m)))
    return f"{m // 60:02d}:{m % 60:02d}"


def _runs(segments: List[Dict[str, Any]], lean: str) -> List[Dict[str, Any]]:
    """Merge touching segments of one lean, clipped to waking hours."""
    runs: List[Dict[str, Any]] = []
    for s in segments:
        if s["lean"] != lean:
            continue
        a, b = max(s["start_min"], WAKING[0]), min(s["end_min"], WAKING[1])
        if b <= a:
            continue
        if runs and runs[-1]["end_min"] == a:
            runs[-1]["end_min"] = b
        else:
            runs.append({"start_min": a, "end_min": b})
    return runs


def relative_leans(segments: List[Dict[str, Any]]) -> None:
    """Second variant, chart-relative: within THIS day's waking-hour segments, `rel` is positive for the top
    quartile of net scores, adverse for the bottom quartile, else neutral (ties at the cut stay neutral). The
    absolute cut makes one chart look all-positive and another all-adverse; this one always ranks the day."""
    live = [x for x in segments if x["end_min"] > WAKING[0] and x["start_min"] < WAKING[1]]
    nets = sorted(x["net"] for x in live)
    if len(nets) < 3 or nets[0] == nets[-1]:
        for x in segments:
            x["rel"] = "neutral"
        return
    hi = nets[min(len(nets) - 1, int(round(0.75 * (len(nets) - 1))))]
    lo = nets[int(round(0.25 * (len(nets) - 1)))]
    for x in segments:
        x["rel"] = ("positive" if x["net"] >= hi and x["net"] > lo
                    else "adverse" if x["net"] <= lo and x["net"] < hi else "neutral")


MAX_WINDOW_MIN = 150          # PROMOTION REQUIREMENT (owner 2026-10-13): one best / one avoid stretch of ~1-2.5 h, not a day


def tight_window(segments: List[Dict[str, Any]], best: bool = True) -> Optional[Dict[str, int]]:
    """The single highest (best) or lowest (avoid) net sub-lord stretch within waking hours, clipped to at most
    MAX_WINDOW_MIN minutes (keeps the stretch's start). Returns None when the day is flat (no stretch stands out).
    This is the shape a promoted KP source must have; the longer absolute/relative runs stay for analysis only."""
    live = []
    for x in segments:
        a, b = max(x["start_min"], WAKING[0]), min(x["end_min"], WAKING[1])
        if b > a:
            live.append((a, b, x["net"]))
    if len(live) < 2:
        return None
    nets = [n for _, _, n in live]
    if max(nets) == min(nets):
        return None
    pick = max(live, key=lambda t: (t[2], -t[0])) if best else min(live, key=lambda t: (t[2], t[0]))
    a, b, _ = pick
    return {"start_min": a, "end_min": min(b, a + MAX_WINDOW_MIN)}


def _longest(runs):
    return max(runs, key=lambda r: r["end_min"] - r["start_min"]) if runs else None


def _clock_to_min(txt) -> Optional[int]:
    """'12:17 PM' / '4:54 PM' / '12:17' -> minutes from midnight."""
    if not txt:
        return None
    t = str(txt).strip().upper()
    pm, am = t.endswith("PM"), t.endswith("AM")
    t = t.replace("PM", "").replace("AM", "").strip()
    try:
        h, mm = t.split(":")[:2]
        h, mm = int(h), int(mm[:2])
    except (ValueError, IndexError):
        return None
    if pm and h < 12:
        h += 12
    if am and h == 12:
        h = 0
    return h * 60 + mm


def _span(txt):
    if not txt or "–" not in str(txt) and "-" not in str(txt):
        return None
    sep = "–" if "–" in str(txt) else "-"
    a, _, b = str(txt).partition(sep)
    x, y = _clock_to_min(a), _clock_to_min(b)
    return (x, y) if x is not None and y is not None and y > x else None


def _overlap(run, span) -> int:
    if not run or not span:
        return 0
    return max(0, min(run["end_min"], span[1]) - max(run["start_min"], span[0]))


def build(chart_record: dict, local_date: date, tz_hours: float,
          abhijit: str = "", rahu_kalam: str = "") -> Dict[str, Any]:
    """The shadow record for one chart-day."""
    try:
        from .kp_service import _build_chart
        from .kp_significators import build_significators
        chart = _build_chart(chart_record)
        if chart is None:
            return {"available": False, "reason": "missing birth data for KP chart"}
        house_sig, planet_sig = build_significators(chart)
        strength = planet_house_strength(house_sig)
        segs = moon_sub_timeline(local_date, tz_hours)
        for s in segs:
            houses = sorted(planet_sig.get(s["sub_lord"], []) or [])
            s["houses"] = houses
            s["net"] = net_score(strength.get(s["sub_lord"], {}))
            s["lean"] = lean_for(s["net"])
        relative_leans(segs)
        best = _longest(_runs(segs, "positive"))
        avoid = _longest(_runs(segs, "adverse"))
        tight_best, tight_avoid = tight_window(segs, True), tight_window(segs, False)
        for s in segs:                                   # relative variant reuses _runs through a shadow key
            s["_abs"], s["lean"] = s["lean"], s["rel"]
        best_rel = _longest(_runs(segs, "positive"))
        avoid_rel = _longest(_runs(segs, "adverse"))
        for s in segs:
            s["lean"] = s.pop("_abs")
        ab, rk = _span(abhijit), _span(rahu_kalam)
        return {
            "available": True, "version": "kp-hourly-3", "date": local_date.isoformat(), "tz_hours": tz_hours,
            "birth_time_ok": chart_record.get("needs_reconfirm") is not True,
            "segments": [{"from": _hhmm(s["start_min"]), "to": _hhmm(s["end_min"]), "star": s["star_lord"],
                          "sub": s["sub_lord"], "lean": s["lean"], "rel": s["rel"], "net": s["net"], "houses": s["houses"]} for s in segs],
            "kp_best": ({"from": _hhmm(best["start_min"]), "to": _hhmm(best["end_min"])} if best else None),
            "kp_avoid": ({"from": _hhmm(avoid["start_min"]), "to": _hhmm(avoid["end_min"])} if avoid else None),
            "kp_best_rel": ({"from": _hhmm(best_rel["start_min"]), "to": _hhmm(best_rel["end_min"])} if best_rel else None),
            "kp_avoid_rel": ({"from": _hhmm(avoid_rel["start_min"]), "to": _hhmm(avoid_rel["end_min"])} if avoid_rel else None),
            "kp_best_tight": ({"from": _hhmm(tight_best["start_min"]), "to": _hhmm(tight_best["end_min"])} if tight_best else None),
            "kp_avoid_tight": ({"from": _hhmm(tight_avoid["start_min"]), "to": _hhmm(tight_avoid["end_min"])} if tight_avoid else None),
            "current": {"best": abhijit or None, "avoid": rahu_kalam or None},
            "agreement": {"best_overlap_min": _overlap(best, ab), "avoid_overlap_min": _overlap(avoid, rk),
                          "best_len_min": (best["end_min"] - best["start_min"]) if best else 0,
                          "avoid_len_min": (avoid["end_min"] - avoid["start_min"]) if avoid else 0,
                          "best_rel_overlap_min": _overlap(best_rel, ab), "avoid_rel_overlap_min": _overlap(avoid_rel, rk),
                          "best_tight_overlap_min": _overlap(tight_best, ab), "avoid_tight_overlap_min": _overlap(tight_avoid, rk)},
        }
    except Exception as e:
        return {"available": False, "reason": f"kp hourly shadow error: {e}"[:180]}


_DONE: set = set()


def record(supabase, chart_id: str, payload: Dict[str, Any]) -> bool:
    """Upsert one row per chart-day into kp_hourly_shadow. Fail-open (a missing table is a no-op, logged once)."""
    try:
        if not payload.get("available"):
            return False
        key = (chart_id, payload["date"])
        if key in _DONE:
            return False
        supabase.table("kp_hourly_shadow").upsert(
            {"chart_id": chart_id, "local_date": payload["date"], "payload": payload},
            on_conflict="chart_id,local_date").execute()
        _DONE.add(key)
        return True
    except Exception as e:
        _DONE.add((chart_id, payload.get("date")))          # do not retry every request
        print(f"[kp-hourly] not stored (non-fatal): {str(e)[:120]}")
        return False
