"""
24-month deterministic event forecast for a stored chart: Rao Chara windows + Boney
confluence (composite_events) + Lal Kitab age layer and annual (varshphal) forecasts
with remedies. Pure function of chart data, dashas and `now`. No LLM, no accuracy gate;
every rule has a stable id for later feedback grading.
"""
from datetime import date, datetime
from typing import Dict, List, Optional

from antar_engine.jaimini_engine import Planet, SIGN_NAMES
from antar_engine.composite_events import composite_windows
from antar_engine.lal_kitab_events import lal_kitab_profile
from antar_engine.lk_annual_forecast import lk_annual_forecast
from antar_engine.d10_layer import d10_windows
from antar_engine.parashari_events import parashari_windows
from antar_engine.mandook_dasha import compute_mandook_dasha, mandook_current
from antar_engine.jaimini_rao_events import Chart as _JChart, rules_for_sign as _jrules

PLAIN = {"marriage": "Relationship / marriage", "children": "Children",
         "education": "Study and learning", "money": "Money / income", "career": "Career step"}
PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")


def _dt(v) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _planets(chart_data: dict) -> Dict[str, Planet]:
    out = {}
    for name, d in (chart_data.get("planets") or {}).items():
        if name not in PLANETS or not isinstance(d, dict):
            continue
        lon = d.get("longitude")
        if not isinstance(lon, (int, float)):
            si, deg = d.get("sign_index"), d.get("degree")
            if isinstance(si, int) and isinstance(deg, (int, float)):
                lon = si * 30.0 + float(deg) % 30
        if isinstance(lon, (int, float)):
            out[name] = Planet(name=name, sign=int(lon // 30) % 12, degree=float(lon),
                               degree_in_sign=float(lon) % 30,
                               retrograde=bool(d.get("retrograde")))
    return out


def _lagna(chart_data: dict):
    lg = chart_data.get("lagna") or {}
    si = lg.get("sign_index")
    if not isinstance(si, int):
        return None, None
    deg = lg.get("longitude")
    if not isinstance(deg, (int, float)):
        d = lg.get("degree")
        deg = si * 30.0 + float(d) % 30 if isinstance(d, (int, float)) else si * 30.0 + 15
    return si, float(deg)


def _vim_rows(rows) -> List[dict]:
    out = []
    for r in rows or []:
        s, e = _dt(r.get("start_date") or r.get("start")), _dt(r.get("end_date") or r.get("end"))
        lord = r.get("planet_or_sign") or r.get("lord_or_sign")
        if s and e and lord:
            out.append({"planet": lord, "start_date": s, "end_date": e})
    return out


_TIER_RANK = {"single": 0, "double": 1, "triple": 2}


def merge_spans(items: List[dict], key, tier_key=None) -> List[dict]:
    """Merge back-to-back windows (end == next start) of the same kind into one span.
    A span keeps the best tier / score seen, the members' count, and the union of rules."""
    out: List[dict] = []
    for it in sorted(items, key=lambda x: (key(x), x["start"])):
        prev = out[-1] if out else None
        if prev and key(prev) == key(it) and prev["end"] >= it["start"]:
            prev["end"] = max(prev["end"], it["end"])
            prev["windows"] += 1
            prev["rules"] = sorted(set(prev["rules"]) | set(it["rules"]))
            if tier_key == "tier":
                if _TIER_RANK[it["tier"]] > _TIER_RANK[prev["tier"]]:
                    prev["tier"] = it["tier"]
                    prev["peak"] = [it["start"], it["end"]]
            elif tier_key == "gain_score" and it["gain_score"] > prev["gain_score"]:
                prev["gain_score"] = it["gain_score"]
                prev["peak"] = [it["start"], it["end"]]
            prev["funding_signal"] = prev.get("funding_signal") or it.get("funding_signal")
        else:
            out.append({**it, "windows": 1, "rules": list(it["rules"]),
                        "peak": [it["start"], it["end"]]})
    return sorted(out, key=lambda x: x["start"])


def _vim_levelled(rows) -> List[dict]:
    out = []
    for r in rows or []:
        s, e = _dt(r.get("start_date") or r.get("start")), _dt(r.get("end_date") or r.get("end"))
        lord = r.get("planet_or_sign") or r.get("lord_or_sign")
        lvl = str(r.get("level") or r.get("type") or "")
        if s and e and lord:
            out.append({"planet": lord, "level": lvl, "start_date": s, "end_date": e})
    return out


def _parashari_block(lagna_sign, lagna_lon, planets, vim_rows, start, end) -> dict:
    """Selection rule: grade 'strong', or 'supported' when the Jupiter+Saturn double transit confirms."""
    ws = parashari_windows(lagna_sign, lagna_lon, planets, _vim_levelled(vim_rows), start, end)
    items = []
    for w in ws:
        for e in w["events"]:
            if e["grade"] == "strong" or (e["grade"] == "supported" and e["double_transit"]):
                items.append({"event": e["event"], "start": w["start"].date().isoformat(),
                              "end": w["end"].date().isoformat(), "rules": e["rules"],
                              "grade": e["grade"], "transit": bool(e["double_transit"]),
                              "md": w["md"], "ad": w["ad"], "tier": "double" if e["double_transit"] else "single"})
    cautions = [{"start": w["start"].date().isoformat(), "end": w["end"].date().isoformat(),
                 "rules": w["caution"]} for w in ws if w["caution"]]
    return {"spans": merge_spans(items, key=lambda x: x["event"]),
            "caution_spans": merge_spans(cautions, key=lambda x: "c")}


def _mandook_block(lagna_sign, lagna_lon, planets, bd, start, end) -> dict:
    """Rao's Mandook dasha as a third timing system. Only for charts that pass his kendra gate
    (about 17 percent). Same event rules as Chara are read on the Mandook sub-period sign; marriage
    also gets the 'major period is the 7th from the lagna' rule."""
    signs = {n: p.sign for n, p in planets.items()}
    periods = compute_mandook_dasha(lagna_sign, signs, bd, num_cycles=3)
    if periods is None:
        return {"applicable": False, "spans": [], "current": None}
    c = _JChart(lagna_sign, lagna_lon, planets)
    items = []
    for p in periods:
        for sub in p.subs:
            if sub.end < start or sub.start > end:
                continue
            r = _jrules(c, sub.sign)
            for ev in ("marriage", "career", "money"):
                rules = list(r[ev])
                if ev == "marriage" and p.sign == (lagna_sign + 6) % 12:
                    rules.append("MAR.mdk_major_is_7th_from_lagna")
                if len(rules) >= (3 if ev == "marriage" else 2):
                    items.append({"event": ev, "start": sub.start.date().isoformat(),
                                  "end": sub.end.date().isoformat(), "rules": rules})
    cur_p, cur_s = mandook_current(periods, start)
    cur = None
    if cur_p:
        cur = {"major": SIGN_NAMES[cur_p.sign], "sub": SIGN_NAMES[cur_s.sign] if cur_s else None}
    return {"applicable": True, "spans": merge_spans(items, key=lambda x: x["event"]), "current": cur}


def build_forecast(chart_data: dict, birth_date, vim_rows, today: Optional[date] = None,
                   months: int = 24, birth_time_accuracy: Optional[str] = None) -> dict:
    today = today or date.today()
    bd = _dt(birth_date)
    planets = _planets(chart_data)
    lagna_sign, lagna_lon = _lagna(chart_data)
    if not bd or lagna_sign is None or len(planets) < 9:
        return {"available": False, "reason": "incomplete chart data"}

    start = datetime(today.year, today.month, today.day)
    y, m = divmod(today.month - 1 + months, 12)
    end = datetime(today.year + y, m + 1, min(today.day, 28))

    windows = composite_windows(lagna_sign, lagna_lon, planets, bd, start, end,
                                vim_rows=_vim_rows(vim_rows))
    events = []
    for w in windows:
        for e in w["events"]:
            events.append({"event": e["event"], "label": PLAIN[e["event"]],
                           "start": w["start"].date().isoformat(), "end": w["end"].date().isoformat(),
                           "tier": e["tier"], "layers": e["layers"], "rules": e["rules"],
                           "major_sign": w["major"], "sub_sign": w["sub"],
                           "double_transit": e["double_transit"]})
    order = {"triple": 0, "double": 1, "single": 2}
    events.sort(key=lambda x: (order[x["tier"]], x["start"]))
    cautions = [{"start": w["start"].date().isoformat(), "end": w["end"].date().isoformat(),
                 "rules": w["cautions"]} for w in windows if w["cautions"]]

    age = (today - bd.date()).days // 365
    natal = {"planets": {p: {"house": pl.sign + 1} for p, pl in planets.items()}}
    lk_profile = lal_kitab_profile({p: pl.sign for p, pl in planets.items()}, age, horizon=2)
    annual = [lk_annual_forecast(natal, a, bd.date().isoformat(), today)
              for a in (age, age + 1)]
    d10 = d10_windows(lagna_sign, lagna_lon, planets, bd, start, end, vim_rows=_vim_rows(vim_rows))
    # Birth-time gate: the D-10 lagna flips if the time is off by a few minutes. A user-confirmed
    # 'exact' time (certificate) lifts the gate, except when the margin is inside ordinary
    # minute-rounding (< 1 minute), where even a certificate time cannot settle it.
    sens = d10["sensitivity"]
    exact = (birth_time_accuracy or "").lower() == "exact"
    sens["accuracy"] = birth_time_accuracy
    sens["gate"] = bool(sens["fragile"] and (not exact or sens["approx_minutes_of_birth_time"] < 1.0))
    for w in d10["windows"]:
        w["start"], w["end"] = w["start"].date().isoformat(), w["end"].date().isoformat()
    spans = merge_spans([e for e in events if e["tier"] != "single"], key=lambda x: (x["event"], x["tier"] == "triple"), tier_key="tier")
    d10["spans"] = merge_spans([{**w, "rules": w["rules"]} for w in d10["windows"] if w["gain_score"] >= 3],
                               key=lambda x: "gain", tier_key="gain_score")
    caution_spans = merge_spans([{**c_, "rules": c_["rules"]} for c_ in cautions], key=lambda x: "c")
    parashari = _parashari_block(lagna_sign, lagna_lon, planets, vim_rows, start, end)
    mandook = _mandook_block(lagna_sign, lagna_lon, planets, bd, start, end)
    return {"available": True, "mandook": mandook, "parashari": parashari, "event_spans": spans, "caution_spans": caution_spans, "d10": d10, "window": [start.date().isoformat(), end.date().isoformat()],
            "events": events, "cautions": cautions,
            "lal_kitab": {"profile": lk_profile, "annual": annual},
            "method": "Jaimini Chara (K.N. Rao) + composite confluence (Boney) + Lal Kitab",
            "note": "Rule-based tradition output; each rule id is graded by user feedback over time."}
