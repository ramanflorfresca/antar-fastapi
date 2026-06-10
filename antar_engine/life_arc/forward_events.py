"""
antar_engine/life_arc/forward_events.py
=======================================
Forward event chips for the Current Cycle tab (Cowork brief 2026-06-10).

Merges TWO timing sources into one chip list:
  1. DashaEventMapper (antar_engine/dasha_event_mapper.py) — 7 life events,
     validated 89% on past events, PD precision. Primary source.
  2. forward_cycle_engine gated ECS over EVENT_TAXONOMY — covers the
     work/money event types the mapper has no priority rules for
     (career_pivot, professional_setback, financial_disruption,
     legal_entanglement).

Conviction = LAYER CONVERGENCE (founder ruling 2026-06-10):
  layers counted per window: dasha priority match / significator linkage
  (D_gate on the period lord) / Lahiri-gated double transit.
  >=2 layers -> "medium", 1 layer -> "low".
  NEVER "high" until D9/D10 divisional charts ship.

Voice contract: titles come from event_taxonomy (planet-free, jargon-free,
one life-noun each). Internal keys are underscore-prefixed; the caller
strips them before the chip reaches the wire.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from antar_engine.dasha_event_mapper import find_future_windows
from antar_engine.life_arc.event_taxonomy import event_title, event_category
from antar_engine.life_arc.forward_cycle_engine import (
    d_gate, amplifier, varga_multiplier, _double_transit_score,
    _conviction, _window_label, _scrub_leaks, get_cycle_periods,
    _chara_rashi_lord,
)

# Never shown as forward chips — deeply sensitive. Same rule as the
# dashboard /upcoming-themes exclusion in main.py.
_SENSITIVE_EVENTS = {"loss_of_mother", "loss_of_father"}

# ECS-only work/money types (the mockup's job-change / debt chips —
# DashaEventMapper has no priority builders for these).
_ECS_EXTRA_EVENTS = ("career_pivot", "professional_setback",
                     "financial_disruption", "legal_entanglement")

_MIN_MAPPER_SCORE = 6        # find_future_windows floor for chip emission
_MAX_WINDOWS_PER_EVENT = 2   # keep top-2 scored windows per event type
_MAX_CHIPS = 8


def _domain(event_type: str) -> str:
    return (event_category(event_type) or "WORK").lower()


def _parse_d(s) -> datetime:
    return datetime.strptime(str(s)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _layers_conviction(n_layers: int) -> str:
    # Capped at medium until D9/D10 ship — never emit "high".
    return "medium" if n_layers >= 2 else "low"


def _status_excluded(event_type: str, marital_status: str,
                     children_status: str) -> bool:
    """Reality-check gating, mirrored from /upcoming-themes quality rules."""
    ms = (marital_status or "").lower().strip()
    cs = (children_status or "").lower().strip()
    if event_type == "family_expansion_first" and cs in (
            "has_children", "has_child", "one", "two", "three",
            "1", "2", "3", "4", "multiple"):
        return True
    if event_type == "serious_partnership_ended" and ms in (
            "single", "divorced", "separated", "never_married",
            "unmarried", "widowed"):
        return True
    return False


def _chip(event_type: str, start_dt: datetime, end_dt: datetime,
          layers: int) -> dict:
    title = _scrub_leaks(event_title(event_type))
    conviction = _layers_conviction(layers)
    if conviction == "high":  # hard guard — must never happen pre-D9/D10
        conviction = "medium"
    ws = start_dt.date().isoformat() if hasattr(start_dt, "date") else str(start_dt)[:10]
    we = end_dt.date().isoformat() if hasattr(end_dt, "date") else str(end_dt)[:10]
    return {
        "event_label": title,
        "title": title,                       # node-chip shape compat
        "domain": _domain(event_type),
        "category": event_category(event_type),
        "window_start": ws,
        "window_end": we,
        "window_label": _scrub_leaks(_window_label(start_dt, end_dt)),
        "window": {"start": ws, "end": we},   # timeline_builder compat
        "predicted_window_start": ws,         # highlight_composer compat
        "conviction": conviction,
        "layers_agreeing": layers,
        "source": "timing_convergence",
        "_event_type": event_type,            # internal — stripped by caller
    }


def build_forward_event_chips(chart_data: dict, birth_jd: float,
                              lagna: str, birth_year: int, ads: list,
                              from_date: Optional[str] = None,
                              to_date: Optional[str] = None,
                              birth_date_str: str = "",
                              marital_status: str = "",
                              children_status: str = "",
                              now: Optional[datetime] = None) -> List[dict]:
    """Returns chips sorted by window_start. Caller strips '_'-prefixed keys."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if not from_date:
        from_date = now.strftime("%Y-%m-%d")
    if not to_date:
        to_date = f"{now.year + 5}-01-01"

    chara_lord = _chara_rashi_lord(chart_data, birth_date_str or "1970-01-01", now)
    chips: List[dict] = []
    seen_types = set()

    # ── Source 1: DashaEventMapper forward windows (validated, PD-tight) ──
    try:
        natal_planets = (chart_data or {}).get("planets") or {}
        windows = find_future_windows(
            lagna, birth_year, ads,
            from_date=from_date, to_date=to_date,
            min_score=_MIN_MAPPER_SCORE, natal_planets=natal_planets,
        )
    except Exception as e:
        print(f"[forward_events] mapper failed (non-blocking): {e}")
        windows = []

    by_event: Dict[str, list] = {}
    for w in windows:
        et = w.get("event_type") or ""
        if et in _SENSITIVE_EVENTS:
            continue
        if _status_excluded(et, marital_status, children_status):
            continue
        by_event.setdefault(et, []).append(w)

    for et, ws_list in by_event.items():
        ws_list.sort(key=lambda w: -int(w.get("score", 0)))
        for w in ws_list[:_MAX_WINDOWS_PER_EVENT]:
            try:
                ws_dt = _parse_d(w["window_start"])
                we_dt = _parse_d(w["window_end"])
            except Exception:
                continue
            mid = (ws_dt + (we_dt - ws_dt) / 2).date()
            # Layer convergence: the mapper match itself IS the dasha layer.
            layers = 1
            try:
                if d_gate(w.get("planet") or "", et, chart_data, chara_lord) > 0:
                    layers += 1
            except Exception:
                pass
            try:
                if _double_transit_score(et, chart_data, mid) > 0:
                    layers += 1
            except Exception:
                pass
            chips.append(_chip(et, ws_dt, we_dt, layers))
            seen_types.add(et)

    # ── Source 2: ECS work/money extras over current + next AD ───────────
    try:
        periods = get_cycle_periods(chart_data, birth_jd, now) or {}
    except Exception:
        periods = {}
    for pkey in ("current_ad", "next_ad"):
        p = periods.get(pkey)
        if not p or not p.get("lord") or not p.get("start") or not p.get("end"):
            continue
        for et in _ECS_EXTRA_EVENTS:
            if et in seen_types:
                continue
            try:
                dg = d_gate(p["lord"], et, chart_data, chara_lord)
                if dg <= 0:
                    continue
                mid = (p["start"] + (p["end"] - p["start"]) / 2).date()
                amp = amplifier(p["lord"], et, chart_data, mid)
                ecs = dg * varga_multiplier(et, p["lord"], chart_data) * amp
                if _conviction(ecs) == "subtle":
                    continue
                layers = 2  # dasha period + significator linkage (D_gate > 0)
                if _double_transit_score(et, chart_data, mid) > 0:
                    layers += 1
                chips.append(_chip(et, p["start"], p["end"], layers))
                seen_types.add(et)
            except Exception:
                continue

    chips.sort(key=lambda c: c["window_start"])
    return chips[:_MAX_CHIPS]
