"""antar_engine/personal_window.py

PERSONAL best / avoid window — SHADOW ONLY (computed and stored, never user-facing until it beats the generic pair).

Today's "best window" is the Abhijit muhurta and "steer clear" is Rahu Kalam: the same for everyone at one place, so
they are hidden (`home_generic_windows` off). Owner's rule: the replacement must come from the PANCHANG + YOUR CHART +
YOUR running SOOKSHMA dasha, and if it cannot be made to stand on that, drop it. This is that candidate:

    hora grid (sunrise→sunset, sunset→sunrise; Chaldean order from the weekday lord)
    each hora scores:
      chart      ruler is a functional benefic (+1) / malefic (-1) for THIS lagna
      period     the ruler IS the running antardasha (x0.5) / pratyantar (x0.75) / sookshma (x1.0) lord:
                 that lord's own hour amplifies it, with the sign of its function for this lagna
      panchang   Rahu Kalam / Yamaganda / Gulika overlap (-0.5 each, never a best window), Abhijit overlap (+0.5)
    best  = the top hora (+ an adjacent one if close) in waking hours, 1-2.5 h, score >= BEST_MIN, outside the kalas
    avoid = the bottom hora (+ adjacent), 1-2.5 h, score <= AVOID_MAX, not overlapping best
    flat day -> None for that side (an honest "nothing stands out" beats a made-up hour)

Exactly one best and one avoid, per the owner's day-prediction rule; the per-hora scores stay internal. Deterministic,
never raises; any failure returns {available: False, reason}."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
_DAY_LORD = {6: "Sun", 0: "Moon", 1: "Mars", 2: "Mercury", 3: "Jupiter", 4: "Venus", 5: "Saturn"}   # python weekday()
VIM_SEQ = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIM_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}

WAKING = (6 * 60, 22 * 60)            # local minutes
BEST_MIN = 1.5
AVOID_MAX = -1.5
MAX_WINDOW_MIN = 150
EXTEND_RATIO = 0.75
W_AD, W_PD, W_SD = 0.5, 0.75, 1.0
KALA_PENALTY = 0.5
ABHIJIT_BONUS = 0.5
VERSION = "personal-window-1"


# ── Vimshottari sub-division (pratyantar / sookshma) ─────────────────────────────────────────────────────────────
def subdivide(parent_lord: str, start: datetime, end: datetime, at: datetime) -> Optional[Tuple[str, datetime, datetime]]:
    """The child period (lord, start, end) of [start, end) that contains `at`; the same proportional split the
    Vimshottari tree uses at every level, beginning with the parent's own lord."""
    if parent_lord not in VIM_SEQ or not (start <= at < end):
        return None
    total = (end - start).total_seconds()
    i0 = VIM_SEQ.index(parent_lord)
    cur = start
    for k in range(9):
        lord = VIM_SEQ[(i0 + k) % 9]
        nxt = end if k == 8 else cur + timedelta(seconds=total * VIM_YEARS[lord] / 120.0)
        if cur <= at < nxt:
            return lord, cur, nxt
        cur = nxt
    return None


def running_stack(ad_lord: str, ad_start: datetime, ad_end: datetime, at: datetime) -> Dict[str, Optional[str]]:
    """{ad, pd, sd} lords running at `at` inside the antardasha [ad_start, ad_end)."""
    out: Dict[str, Optional[str]] = {"ad": ad_lord, "pd": None, "sd": None}
    pd = subdivide(ad_lord, ad_start, ad_end, at)
    if pd:
        out["pd"] = pd[0]
        sd = subdivide(pd[0], pd[1], pd[2], at)
        if sd:
            out["sd"] = sd[0]
    return out


def current_antardasha(dashas: dict, at: datetime) -> Optional[Tuple[str, datetime, datetime]]:
    """(lord, start, end) of the vimshottari antardasha containing `at`, from get_dashas_for_chart() output."""
    rows = (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []
    for r in rows:
        if str(r.get("level", "")).lower() not in ("antardasha", "antar", "ad", "2"):
            continue
        try:
            s = datetime.fromisoformat(str(r.get("start_date"))[:10])
            e = datetime.fromisoformat(str(r.get("end_date"))[:10])
        except Exception:
            continue
        lord = r.get("planet_or_sign") or r.get("lord_or_sign") or ""
        if s <= at < e + timedelta(days=1) and lord in VIM_SEQ:
            return lord, s, e + timedelta(days=1)
    return None


# ── hora grid + scoring ──────────────────────────────────────────────────────────────────────────────────────────
def hora_grid(local_date: date, sunrise_min: float, sunset_min: float) -> List[Dict[str, Any]]:
    """24 horas as local minutes from midnight (the night runs past 1440 into the next morning). Next sunrise is taken
    as today's + 24 h — a few minutes of drift at most, which a shadow comparison tolerates."""
    day = (sunset_min - sunrise_min) / 12.0
    night = (sunrise_min + 1440 - sunset_min) / 12.0
    i0 = CHALDEAN.index(_DAY_LORD[local_date.weekday()])
    out = []
    for k in range(24):
        if k < 12:
            s, e = sunrise_min + k * day, sunrise_min + (k + 1) * day
        else:
            s, e = sunset_min + (k - 12) * night, sunset_min + (k - 11) * night
        out.append({"ruler": CHALDEAN[(i0 + k) % 7], "start_min": s, "end_min": e, "is_day": k < 12})
    return out


def _fn(planet: str, lagna: str) -> int:
    from antar_engine.practice_engine import is_functional_benefic, is_functional_malefic
    return 1 if is_functional_benefic(planet, lagna) else (-1 if is_functional_malefic(planet, lagna) else 0)


def _ov(a0: float, a1: float, span: Optional[Tuple[int, int]]) -> float:
    if not span:
        return 0.0
    return max(0.0, min(a1, span[1]) - max(a0, span[0]))


def score_hora(h: Dict[str, Any], lagna: str, stack: Dict[str, Optional[str]], kalas: List[Optional[Tuple[int, int]]],
               abhijit: Optional[Tuple[int, int]]) -> Dict[str, Any]:
    r = h["ruler"]
    fn = _fn(r, lagna)
    parts = {"chart": float(fn), "period": 0.0, "panchang": 0.0}
    why: List[str] = []
    if fn:
        why.append(f"{r} is a functional {'benefic' if fn > 0 else 'malefic'} for this rising sign")
    for lvl, w in (("ad", W_AD), ("pd", W_PD), ("sd", W_SD)):
        if stack.get(lvl) == r:
            parts["period"] += w * (fn if fn else 0)
            why.append(f"its hour is your running {lvl.upper()} lord's")
    length = max(1.0, h["end_min"] - h["start_min"])
    in_kala = 0
    for span in kalas:
        if _ov(h["start_min"], h["end_min"], span) / length >= 0.5:
            parts["panchang"] -= KALA_PENALTY
            in_kala += 1
    if abhijit and _ov(h["start_min"], h["end_min"], abhijit) / length >= 0.5:
        parts["panchang"] += ABHIJIT_BONUS
    return {**h, "score": round(sum(parts.values()), 2), "parts": parts, "in_kala": in_kala, "why": why}


def _waking(h: Dict[str, Any]) -> bool:
    return h["start_min"] >= WAKING[0] and h["end_min"] <= WAKING[1]


def _extend(scored: List[Dict[str, Any]], i: int, best: bool) -> Tuple[float, float, List[int]]:
    """The hora at i, plus an adjacent waking hora scoring within EXTEND_RATIO of it, capped at MAX_WINDOW_MIN."""
    base = scored[i]
    lo, hi, idx = base["start_min"], base["end_min"], [i]
    ok = (lambda s: s["score"] >= EXTEND_RATIO * base["score"]) if best else (lambda s: s["score"] <= EXTEND_RATIO * base["score"])
    for j in (i + 1, i - 1):
        if 0 <= j < len(scored) and _waking(scored[j]) and ok(scored[j]) and not (best and scored[j]["in_kala"]):
            n_lo, n_hi = min(lo, scored[j]["start_min"]), max(hi, scored[j]["end_min"])
            if n_hi - n_lo <= MAX_WINDOW_MIN:
                lo, hi = n_lo, n_hi
                idx.append(j)
                break
    return lo, hi, idx


def _hhmm(m: float) -> str:
    m = int(round(m)) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def choose(scored: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    wk = [i for i, h in enumerate(scored) if _waking(h)]
    best = avoid = None
    cand = [i for i in wk if not scored[i]["in_kala"]]
    if cand:
        i = max(cand, key=lambda k: (scored[k]["score"], -scored[k]["start_min"]))
        if scored[i]["score"] >= BEST_MIN:
            lo, hi, idx = _extend(scored, i, True)
            best = {"start_min": lo, "end_min": hi, "from": _hhmm(lo), "to": _hhmm(hi), "score": scored[i]["score"],
                    "rulers": [scored[k]["ruler"] for k in sorted(idx)], "why": scored[i]["why"]}
    if wk:
        j = min(wk, key=lambda k: (scored[k]["score"], scored[k]["start_min"]))
        if scored[j]["score"] <= AVOID_MAX:
            lo, hi, idx = _extend(scored, j, False)
            if not (best and min(hi, best["end_min"]) > max(lo, best["start_min"])):
                avoid = {"start_min": lo, "end_min": hi, "from": _hhmm(lo), "to": _hhmm(hi), "score": scored[j]["score"],
                         "rulers": [scored[k]["ruler"] for k in sorted(idx)], "why": scored[j]["why"]}
    return best, avoid


def _span(txt) -> Optional[Tuple[int, int]]:
    from antar_engine.kp.kp_hourly import _span as _s
    return _s(txt)


def build(lagna: str, dashas: dict, local_date: date, tz_hours: float, sunrise_min: float, sunset_min: float,
          abhijit: str = "", rahu_kalam: str = "", yamaganda: str = "", gulika: str = "") -> Dict[str, Any]:
    """The shadow record for one chart-day. Times are local minutes from midnight; `tz_hours` converts them to UTC
    for the dasha lookup."""
    try:
        if not lagna:
            return {"available": False, "reason": "no rising sign"}
        grid = hora_grid(local_date, sunrise_min, sunset_min)
        kalas = [_span(rahu_kalam), _span(yamaganda), _span(gulika)]
        ab = _span(abhijit)
        base = datetime(local_date.year, local_date.month, local_date.day) - timedelta(hours=float(tz_hours))
        scored = []
        stacks = []
        for h in grid:
            at = base + timedelta(minutes=(h["start_min"] + h["end_min"]) / 2.0)
            cur = current_antardasha(dashas, at)
            st = running_stack(cur[0], cur[1], cur[2], at) if cur else {"ad": None, "pd": None, "sd": None}
            stacks.append(st)
            scored.append(score_hora(h, lagna, st, kalas, ab))
        best, avoid = choose(scored)
        mid = stacks[len(stacks) // 3] if stacks else {}
        return {
            "available": True, "version": VERSION, "date": local_date.isoformat(), "tz_hours": tz_hours, "lagna": lagna,
            "running": mid,
            "best": best, "avoid": avoid,
            "horas": [{"from": _hhmm(h["start_min"]), "to": _hhmm(h["end_min"]), "ruler": h["ruler"],
                       "score": h["score"], "parts": h["parts"]} for h in scored],
            "current": {"best": abhijit or None, "avoid": rahu_kalam or None},
            "agreement": {
                "best_overlap_min": int(_ov(best["start_min"], best["end_min"], ab)) if best else 0,
                "avoid_overlap_min": int(_ov(avoid["start_min"], avoid["end_min"], kalas[0])) if avoid else 0,
            },
        }
    except Exception as e:
        return {"available": False, "reason": f"personal window error: {e}"[:180]}


_DONE: set = set()


def enabled() -> bool:
    """PERSONAL_WINDOW_SHADOW=off turns the shadow off (default on: it is computed and stored only)."""
    import os
    return os.getenv("PERSONAL_WINDOW_SHADOW", "on").strip().lower() not in ("off", "0", "false", "no")


def record(supabase, chart_id: str, payload: Dict[str, Any]) -> bool:
    """Upsert one row per chart-day into personal_window_shadow. Fail-open: a missing table is a logged no-op."""
    try:
        if not payload.get("available"):
            return False
        key = (chart_id, payload["date"])
        if key in _DONE:
            return False
        _DONE.add(key)
        supabase.table("personal_window_shadow").upsert(
            {"chart_id": chart_id, "local_date": payload["date"], "payload": payload},
            on_conflict="chart_id,local_date").execute()
        return True
    except Exception as e:
        print(f"[personal-window] not stored (non-fatal): {str(e)[:120]}")
        return False
