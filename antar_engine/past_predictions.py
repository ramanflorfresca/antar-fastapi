"""
antar_engine/past_predictions.py
================================
Admin past-prediction validation harness (Cowork brief 2026-06-10).

Surfaces the most-recent CLOSED-window predictions for a chart by reusing the
existing forward-event engine (antar_engine/life_arc/forward_events.py —
DashaEventMapper + ECS merge). NO parallel engine: we call the same
build_forward_event_chips with a from_date in the past and select windows
where window_end < today.

Methodology: these are retrodictions — the engine computes each event
deterministically from chart + date. No outcome data feeds the engine, and
nothing in this module is outcome-aware.

prediction_id is a DETERMINISTIC stable hash of
chart_id + domain + window_start + window_end — the admin panel re-fetches
predictions and joins persisted marks on this id, so it must never vary
between calls for the same chart + window.

Admin-only — the main.py endpoints wrap this behind require_admin.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

# ── Domain mapping (brief vocabulary: Career / Business / Love / Health / Family) ──
_DOMAIN_BY_EVENT = {
    "career_pivot":              "Career",
    "professional_setback":      "Career",
    "financial_disruption":      "Business",
    "major_acquisition":         "Business",
    "legal_entanglement":        "Business",
    "serious_partnership_began": "Love",
    "serious_partnership_ended": "Love",
    "family_expansion_first":    "Family",
    "family_expansion_second":   "Family",
    "major_relocation":          "Family",
    "loss_of_mother":            "Health",   # excluded upstream (_SENSITIVE_EVENTS)
    "loss_of_father":            "Health",   # excluded upstream (_SENSITIVE_EVENTS)
}
_DOMAIN_BY_CATEGORY = {
    "WORK": "Career", "RELATIONSHIP": "Love", "FAMILY": "Family",
    "HEALTH": "Health", "RELOCATION": "Family",
}

# Challenging event types render as "watch"; everything else is "opening".
_WATCH_EVENTS = {
    "professional_setback", "financial_disruption",
    "legal_entanglement", "serious_partnership_ended",
}

# Lookback ladder (days). Widen until we have >= n closed windows.
_LOOKBACK_LADDER = (365, 730, 1095)


def _safe_json(v):
    """JSONB columns are sometimes stored as JSON strings — never assume dict."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return v if isinstance(v, dict) else {}


def make_prediction_id(chart_id: str, domain: str,
                       window_start: str, window_end: str) -> str:
    """Deterministic, stable across calls: hash of chart+domain+window only."""
    raw = f"{chart_id}|{domain}|{window_start}|{window_end}"
    return "pp_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _chip_domain(chip: dict) -> str:
    et = chip.get("_event_type") or ""
    if et in _DOMAIN_BY_EVENT:
        return _DOMAIN_BY_EVENT[et]
    return _DOMAIN_BY_CATEGORY.get(str(chip.get("category") or "").upper(), "Career")


def _chip_direction(chip: dict) -> str:
    return "watch" if (chip.get("_event_type") or "") in _WATCH_EVENTS else "opening"


def compute_past_predictions(chart_id: str, supabase, n: int = 3,
                             today: Optional[datetime] = None,
                             min_layers: int = 2,
                             domains: tuple = ("Love", "Business", "Family")) -> dict:
    """
    Returns {"chart_id", "predictions": [...], "note": optional str}.
    Each prediction: prediction_id, domain, window_start, window_end,
    direction, event, mark=None (caller joins persisted marks).
    Raises ValueError("chart_not_found") / ValueError("no_chart_data").
    """
    from antar_engine.life_arc.forward_events import build_forward_event_chips

    now = today or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # ── Chart fetch (same fields the /life-arc forward-chips block uses) ──
    cr = supabase.table("charts").select("*").eq("id", chart_id).execute()
    if not cr.data:
        raise ValueError("chart_not_found")
    chart_record = cr.data[0]
    chart_data = _safe_json(chart_record.get("chart_data"))
    if not chart_data:
        raise ValueError("no_chart_data")

    birth_date_str = str(chart_record.get("birth_date")
                         or chart_data.get("birth_date") or "")[:10]
    birth_jd = chart_data.get("birth_jd")
    if not birth_jd and birth_date_str:
        try:
            from antar_engine import utils as _pp_utils
            p = birth_date_str.split("-")
            birth_jd = _pp_utils.julian_day(
                datetime(int(p[0]), int(p[1]), int(p[2])))
        except Exception:
            birth_jd = 0.0

    lagna_raw = chart_data.get("lagna") or {}
    lagna = ((lagna_raw.get("sign") if isinstance(lagna_raw, dict) else lagna_raw)
             or chart_record.get("lagna_sign") or "")
    birth_year = int(birth_date_str[:4]) if birth_date_str[:4].isdigit() else 1980

    ads_res = supabase.table("dasha_periods") \
        .select("planet_or_sign,start_date,end_date,level,type,metadata") \
        .eq("chart_id", chart_id) \
        .eq("system", "vimsottari") \
        .order("start_date") \
        .execute()
    ads = [r for r in (ads_res.data or [])
           if r.get("level") == 2
           or str(r.get("type", "")).lower() in ("antardasha", "ad", "2")]

    if not ads or not lagna:
        return {"chart_id": chart_id, "predictions": [],
                "note": ("engine inputs missing for this chart "
                         f"(ads={len(ads)}, lagna={'set' if lagna else 'missing'}) "
                         "— cannot compute closed windows; not fabricating.")}

    # ── Reuse the forward-event engine over PAST date ranges ─────────────
    # Same engine, same scoring — only the scan range differs. Widen the
    # lookback until >= n closed windows or the ladder is exhausted.
    seen: dict = {}        # prediction_id -> prediction (dedupe across ladder)
    lookback_used = _LOOKBACK_LADDER[0]
    for lookback_days in _LOOKBACK_LADDER:
        lookback_used = lookback_days
        from_date = (now - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        try:
            chips = build_forward_event_chips(
                chart_data=chart_data,
                birth_jd=birth_jd or 0.0,
                lagna=lagna,
                birth_year=birth_year,
                ads=ads,
                from_date=from_date,
                to_date=today_str,
                birth_date_str=birth_date_str,
                marital_status=str(chart_record.get("marital_status") or ""),
                children_status=str(chart_record.get("children_status") or ""),
                now=now,
            )
        except Exception as e:
            print(f"[past_predictions] engine failed ({lookback_days}d): {e}")
            chips = []

        for c in chips:
            we = str(c.get("window_end") or "")[:10]
            ws = str(c.get("window_start") or "")[:10]
            if not we or not ws or we >= today_str:
                continue  # closed windows only — window_end strictly in the past
            domain = _chip_domain(c)
            # High-probability gate (founder ruling 2026-06-11): only windows
            # where >=min_layers timing layers agree (dasha / significator /
            # double transit). 2+ layers == the engine's "medium" — its max
            # pre-D9/D10. Domain gate: only what onboarding can verify.
            if domains and domain not in domains:
                continue
            if int(c.get("layers_agreeing") or 0) < int(min_layers or 0):
                continue
            pid = make_prediction_id(chart_id, domain, ws, we)
            if pid in seen:
                continue
            seen[pid] = {
                "prediction_id": pid,
                "domain": domain,
                "window_start": ws,
                "window_end": we,
                "direction": _chip_direction(c),
                # Same user-facing sentence the Cycle surface shows (planet-free,
                # jargon-free title from event_taxonomy via the engine's scrub).
                "event": c.get("event_label") or c.get("title") or "",
                "conviction": c.get("conviction"),
                "layers_agreeing": int(c.get("layers_agreeing") or 0),
                "mark": None,
            }
        if len(seen) >= n:
            break

    preds = sorted(seen.values(), key=lambda p: p["window_end"], reverse=True)[:n]
    out = {"chart_id": chart_id, "predictions": preds,
           "filters": {"min_layers": int(min_layers or 0),
                       "domains": list(domains or [])}}
    if not preds:
        out["note"] = (f"no closed windows passed the high-probability gate "
                       f"(>= {min_layers} layers, domains {list(domains or [])}) "
                       f"in the last {lookback_used} days — "
                       "not fabricating or relaxing the gate silently.")
    return out
