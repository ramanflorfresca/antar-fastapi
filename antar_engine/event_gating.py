"""
antar_engine/event_gating.py
============================
Age-plausibility + life-stage gating for the named life-event engine
(Cowork brief 2026-06-11).

Config lives in the `event_engine_config` Supabase table so the founder can
tune house mappings / age bands / tolerances WITHOUT a code change. This
module carries an identical hardcoded fallback (used when the table is
missing, unreadable, or a row is absent).

Gating contract:
  final_score = mapper_score * age_plausibility(age_at_window) * stage_factor
  - age curve is a soft trapezoid (rise → peak → fade), never a hard cliff
    inside the band; 0.0 outside.
  - stage rules are HARD gates but fire only on KNOWN stage data. Missing /
    "unknown" marital or kids status -> factor 1.0 (never suppress on
    ignorance — the absence of onboarding stage data must not silence the
    engine, it just loses disambiguation power).

Kill switch: env EVENT_GATING=off bypasses everything (returns inputs as-is).

NOTHING here is outcome-aware: gates read chart + onboarding stage fields
only, never validation marks.
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Optional

# ── Hardcoded fallback — MUST mirror sql_event_engine_config.sql seeds ──────
# (event_type → domain, houses CSV, karaka, direction, rise, p1, p2, fade,
#  stage_rule, tolerance_days)  — DRAFT values, founder tunes in the table.
_FALLBACK = {
    "career_pivot":              ("Career",   "6,10,11", "Sun",     "opening", 18, 20, 62, 66, None,                           60),
    "professional_setback":      ("Career",   "6,8,10",  "Saturn",  "watch",   18, 20, 62, 66, None,                           60),
    "financial_disruption":      ("Business", "2,6,8",   "Saturn",  "watch",   22, 26, 60, 68, None,                           60),
    "legal_entanglement":        ("Business", "6,8,12",  "Mars",    "watch",   22, 26, 60, 70, None,                           60),
    "major_acquisition":         ("Business", "4,2,11",  "Venus",   "opening", 21, 25, 65, 75, None,                           60),
    "serious_partnership_began": ("Love",     "7,2,5",   "Venus",   "opening", 18, 22, 35, 45, "suppress_if_married",          90),
    "serious_partnership_ended": ("Love",     "7,6,8",   "Saturn",  "watch",   24, 28, 55, 62, "requires_prior_partnership",   90),
    "family_expansion_first":    ("Family",   "5,9",     "Jupiter", "opening", 20, 24, 42, 48, "requires_partnership_fertile", 90),
    "family_expansion_second":   ("Family",   "5,9",     "Jupiter", "opening", 22, 26, 44, 50, "requires_partnership_fertile", 90),
    "major_relocation":          ("Family",   "4,3,12",  "Rahu",    "opening", 16, 18, 70, 80, None,                           60),
    "loss_of_father":            ("Family",   "9,8",     "Sun",     "watch",   30, 40, 70, 80, None,                           90),
    "loss_of_mother":            ("Family",   "4,8",     "Moon",    "watch",   35, 45, 75, 85, None,                           90),
    "business_start":            ("Business", "3,7,10,11", "Mercury", "opening", 22, 25, 55, 62, None,                         60),
}

# ── [delivery-bands 2026-06-11] PD-delivery rule, AI-derived offline from the
# 3-chart / 11-event ground-truth set; runs DETERMINISTICALLY. Externally-
# confirmed events deliver at 0.38–0.89 through the qualifying AD (median
# ≈0.6); self-initiated beginnings fire at the opening (≤0.05). NULL = event
# lands on time, keep the raw mapper window. Fractions of the AD span.
# CALIBRATION-SET DRAFT — re-tune on a fresh chart set.
_DELIVERY_FALLBACK = {
    "serious_partnership_began": (0.45, 0.20),
    "serious_partnership_ended": (0.63, 0.20),
    "family_expansion_first":    (0.70, 0.20),
    "family_expansion_second":   (0.70, 0.20),
    "career_pivot":              (0.75, 0.20),
    "loss_of_father":            (0.50, 0.20),
    "loss_of_mother":            (0.50, 0.20),
    "major_relocation":          (0.62, 0.20),
    "business_start":            (0.10, 0.12),
}
_MIN_SCORE_FALLBACK = {"major_relocation": 4.0}


def delivery_params(cfg_row, event_type: str):
    """(center, halfwidth) or (None, None). DB row wins, fallback otherwise."""
    if cfg_row and cfg_row.get("delivery_center") is not None:
        return (float(cfg_row["delivery_center"]),
                float(cfg_row.get("delivery_halfwidth") or 0.20))
    return _DELIVERY_FALLBACK.get(event_type, (None, None))


def event_min_score(cfg_row, event_type: str, default: float = 6.0) -> float:
    if cfg_row and cfg_row.get("min_score") is not None:
        return float(cfg_row["min_score"])
    return float(_MIN_SCORE_FALLBACK.get(event_type, default))


def remap_to_delivery_window(event_type: str, window_start: str,
                             window_end: str, ads: list,
                             cfg_row=None) -> tuple:
    """
    Remap a mapper PD-slice window to the delivery band of its parent AD.
    Returns (start_iso, end_iso, remapped_bool). Deterministic.
    Raw window kept when: no band configured, parent AD not found, or
    AD span < 180d (already precise).
    """
    from datetime import datetime as _dt, timedelta as _td
    center, halfw = delivery_params(cfg_row, event_type)
    if center is None:
        return window_start, window_end, False
    try:
        ws = _dt.strptime(str(window_start)[:10], "%Y-%m-%d")
        we = _dt.strptime(str(window_end)[:10], "%Y-%m-%d")
    except Exception:
        return window_start, window_end, False
    parent = None
    for a in ads or []:
        try:
            s = _dt.strptime(str(a.get("start_date"))[:10], "%Y-%m-%d")
            e = _dt.strptime(str(a.get("end_date"))[:10], "%Y-%m-%d")
        except Exception:
            continue
        if s <= ws and we <= e:
            if parent is None or (e - s) < (parent[1] - parent[0]):
                parent = (s, e)
    if not parent:
        return window_start, window_end, False
    span = (parent[1] - parent[0]).days
    if span < 180:
        return window_start, window_end, False
    mid = parent[0] + _td(days=span * center)
    hw = max(45, min(int(span * halfw), 135))  # falsifiable: ≤270d total
    lo = max(parent[0], mid - _td(days=hw))
    hi = min(parent[1], mid + _td(days=hw))
    return lo.strftime("%Y-%m-%d"), hi.strftime("%Y-%m-%d"), True

_CACHE: dict = {"rows": None, "at": 0.0}
_CACHE_TTL_SECS = 300


def _row_from_fallback(et: str) -> Optional[dict]:
    f = _FALLBACK.get(et)
    if not f:
        return None
    return {"event_type": et, "domain": f[0], "houses": f[1], "karaka": f[2],
            "direction": f[3], "age_rise": f[4], "age_peak_start": f[5],
            "age_peak_end": f[6], "age_fade": f[7], "stage_rule": f[8],
            "window_tolerance_days": f[9], "enabled": True, "draft": True}


def get_config(supabase=None) -> dict:
    """event_type -> config row. DB-first with 5-min cache, fallback merge."""
    rows = {et: _row_from_fallback(et) for et in _FALLBACK}
    if supabase is None:
        return rows
    now = time.time()
    if _CACHE["rows"] is not None and now - _CACHE["at"] < _CACHE_TTL_SECS:
        rows.update(_CACHE["rows"])
        return rows
    try:
        r = supabase.table("event_engine_config").select("*").execute()
        db = {x["event_type"]: x for x in (r.data or []) if x.get("enabled", True)}
        _CACHE["rows"] = db
        _CACHE["at"] = now
        rows.update(db)
    except Exception as e:
        print(f"[event_gating] config table unreadable (fallback in use): {e}")
    return rows


def gating_enabled() -> bool:
    return os.getenv("EVENT_GATING", "on").strip().lower() not in ("off", "0", "false")


def age_plausibility(cfg_row: Optional[dict], age: float) -> float:
    """Soft trapezoid. 1.0 when no curve configured (unknown event types)."""
    if not cfg_row:
        return 1.0
    try:
        r, p1, p2, f = (float(cfg_row["age_rise"]), float(cfg_row["age_peak_start"]),
                        float(cfg_row["age_peak_end"]), float(cfg_row["age_fade"]))
    except Exception:
        return 1.0
    if age < r or age > f:
        return 0.0
    if age < p1:
        return (age - r) / max(p1 - r, 1e-9)
    if age > p2:
        return (f - age) / max(f - p2, 1e-9)
    return 1.0


def _stage_facts(chart_record: dict) -> dict:
    """Normalize onboarding stage fields. 'unknown'/None -> not known."""
    cr = chart_record or {}
    ms = str(cr.get("marital_status") or "").strip().lower()
    lr = str(cr.get("life_relationship") or "").strip().lower()
    ks = str(cr.get("children_status") or "").strip().lower()
    lk = str(cr.get("life_kids") or "").strip().lower()
    married_now = ms in ("married", "remarried") or lr in ("married", "remarried")
    ever_partnered = married_now or ms in ("divorced", "separated", "widowed") \
        or lr in ("divorced", "separated", "widowed", "partnered", "in_relationship",
                  "live_in", "living_together")
    known_single_never = ms in ("single", "never_married", "unmarried") and not ever_partnered
    return {
        "marital_known": ms not in ("", "unknown") or lr not in ("", "unknown"),
        "married_now": married_now,
        "ever_partnered": ever_partnered,
        "known_single_never": known_single_never,
        "has_children": ks.startswith("has_") or ks in ("one", "two", "three") or
                        lk in ("yes", "has_kids", "one", "two", "three", "multiple"),
    }


def stage_factor(cfg_row: Optional[dict], chart_record: dict,
                 age_at_window: float) -> float:
    """Hard stage gates — fire ONLY on known stage data, else neutral 1.0."""
    rule = (cfg_row or {}).get("stage_rule")
    if not rule:
        return 1.0
    s = _stage_facts(chart_record)
    if not s["marital_known"]:
        return 1.0  # never suppress on ignorance
    if rule == "requires_prior_partnership":
        return 1.0 if s["ever_partnered"] else 0.0
    if rule == "suppress_if_married":
        # first-marriage event suppressed for someone already married NOW
        # only when the window is in the present/future; past windows may BE
        # the marriage itself — handled by caller passing window-relative age.
        return 0.15 if s["married_now"] else 1.0
    if rule == "requires_partnership_fertile":
        if s["known_single_never"]:
            return 0.0
        return 1.0
    return 1.0


def gate_windows(windows: list, birth_date_str: str, chart_record: dict,
                 supabase=None, min_factor: float = 0.25) -> list:
    """
    Apply age+stage gating to mapper windows (find_future_windows dicts).
    Returns gated copies with: gated_score, age_at_window, age_factor,
    stage_factor, domain, direction, window_tolerance_days attached.
    Windows whose combined factor < min_factor are dropped.
    With EVENT_GATING=off, returns windows annotated but ungated.
    """
    cfg = get_config(supabase)
    try:
        bdt = datetime.strptime(str(birth_date_str)[:10], "%Y-%m-%d")
    except Exception:
        bdt = None
    out = []
    on = gating_enabled()
    for w in windows:
        et = w.get("event_type") or ""
        row = cfg.get(et)
        try:
            ws = datetime.strptime(str(w.get("window_start"))[:10], "%Y-%m-%d")
            age = (ws - bdt).days / 365.25 if bdt else -1.0
        except Exception:
            age = -1.0
        af = age_plausibility(row, age) if age >= 0 else 1.0
        sf = stage_factor(row, chart_record, age)
        factor = af * sf
        g = dict(w)
        g["age_at_window"] = round(age, 1)
        g["age_factor"] = round(af, 2)
        g["stage_factor"] = round(sf, 2)
        g["gated_score"] = round(float(w.get("score") or 0) * factor, 1)
        g["domain"] = (row or {}).get("domain")
        g["direction"] = (row or {}).get("direction")
        g["window_tolerance_days"] = int((row or {}).get("window_tolerance_days") or 60)
        if (not on) or factor >= min_factor:
            out.append(g)
    return out
