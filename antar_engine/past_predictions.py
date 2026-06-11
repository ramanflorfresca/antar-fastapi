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


# ── Astrologer-style verification questions (founder ask 2026-06-11) ─────────
# "Did you move between X and Y?" — phrased exactly the way an astrologer
# verifies a chart in person. Deterministic templates, no LLM, no jargon.
# {w} = human window label.
_QUESTION_TEMPLATES = {
    # [event-engine-v1 2026-06-11] admin validation panel only — these event
    # types never appear on user-facing forward surfaces (_SENSITIVE_EVENTS).
    "loss_of_father":
        "Did you lose your father, or face a serious crisis around him, "
        "between {w}?",
    "loss_of_mother":
        "Did you lose your mother, or face a serious crisis around her, "
        "between {w}?",
    "serious_partnership_began":
        "Did a serious relationship or partnership begin between {w}?",
    "serious_partnership_ended":
        "Did a relationship or close partnership end, or go through a "
        "serious rupture, between {w}?",
    "family_expansion_first":
        "Did your family grow — a child arriving, or someone new joining "
        "the household — between {w}?",
    "family_expansion_second":
        "Did your family grow again between {w}?",
    "major_relocation":
        "Did you move homes or cities between {w}?",
    "major_acquisition":
        "Did you acquire something significant — property, a vehicle, a "
        "major asset — between {w}?",
    "career_pivot":
        "Did you change jobs, or did your work direction shift, between {w}?",
    "professional_setback":
        "Did you face a serious setback or unusual pressure at work "
        "between {w}?",
    "financial_disruption":
        "Did money get unusually tight, or did a financial strain hit, "
        "between {w}?",
    "legal_entanglement":
        "Did a dispute, legal issue, or formal matter surface between {w}?",
}


def _fmt_window(ws: str, we: str) -> str:
    """'2025-06-17','2025-11-20' -> 'Jun – Nov 2025' (human, jargon-free)."""
    try:
        a = datetime.strptime(ws, "%Y-%m-%d")
        b = datetime.strptime(we, "%Y-%m-%d")
    except Exception:
        return f"{ws} and {we}"
    if (a.year, a.month) == (b.year, b.month):
        return a.strftime("%b %Y")
    if a.year == b.year:
        return f"{a.strftime('%b')} – {b.strftime('%b %Y')}"
    return f"{a.strftime('%b %Y')} – {b.strftime('%b %Y')}"


# ── Falsifiable probes (Cowork follow-up brief 2026-06-11) ───────────────────
# Per-domain, direction-aware, deterministic. The probe is the question an
# astrologer asks to confirm a past call: past-tense, interrogative, window
# baked in, concrete enough that "no" is a real answer. Never a Claude call.
_PROBE_TEMPLATES = {
    "Career": {
        "opening": ("Did you change jobs, get a title change, or take on a "
                    "visible new role between {w}?"),
        "watch":   ("Did you face a serious setback, role loss, or unusual "
                    "pressure at work between {w}?"),
    },
    "Business": {
        "opening": ("Did you start, close, or materially shift a business "
                    "or major deal between {w}?"),
        "watch":   ("Did a deal stall, a dispute surface, or money pressure "
                    "build in your business between {w}?"),
    },
    "Love": {
        "opening": ("Did a relationship begin, deepen, or end between {w}?"),
        "watch":   ("Did a relationship end or hit serious strain "
                    "between {w}?"),
    },
    "Health": {
        "opening": ("Did a significant health issue, recovery, or change in "
                    "vitality occur between {w}?"),
        "watch":   ("Did a significant health issue, recovery, or change in "
                    "vitality occur between {w}?"),
    },
    "Family": {
        "opening": ("Did you relocate your home, or was there a major family "
                    "event (birth, marriage, loss), between {w}?"),
        "watch":   ("Did you relocate your home, or was there a major family "
                    "event (birth, marriage, loss), between {w}?"),
    },
}


def _chip_probe(domain: str, direction: str, ws: str, we: str) -> str:
    """Deterministic falsifiable probe: domain template x direction x window."""
    w = _fmt_window(ws, we).replace(" – ", " and ")
    by_dir = _PROBE_TEMPLATES.get(domain) or _PROBE_TEMPLATES["Career"]
    tpl = by_dir.get(direction) or by_dir["opening"]
    p = tpl.format(w=w)
    if " and " not in w:  # single-month window — "between Jun 2025" reads off
        p = p.replace(f"between {w}", f"around {w}")
    return p


def _strip_gate(text: str) -> str:
    """Backstop: run user-facing strings through the central strip layer.
    Templates are jargon-free by construction, but the gate stays in the
    path (no house numbers / planets / Sanskrit / engine terms can leak)."""
    try:
        from antar_engine.output_strips import apply_user_facing_strips
        out = apply_user_facing_strips(text, 'en', field_type='plain')
        return out if isinstance(out, str) else text
    except Exception:
        return text


def _chip_question(chip: dict, ws: str, we: str, domain: str) -> str:
    # "between Oct and Dec 2025" for ranges, "around Jun 2025" when the
    # window sits inside a single month.
    w = _fmt_window(ws, we).replace(" – ", " and ")
    tpl = _QUESTION_TEMPLATES.get(chip.get("_event_type") or "")
    if tpl:
        q = tpl.format(w=w)
        if " and " not in w:
            q = q.replace(f"between {w}", f"around {w}")
        return q
    return (f"Around {w} — did anything significant shift in your "
            f"{domain.lower()} life?")


def compute_past_predictions(chart_id: str, supabase, n: int = 3,
                             today: Optional[datetime] = None,
                             min_layers: int = 2,   # legacy, ignored (chips-era)
                             min_score: float = 6.0,
                             domains: tuple = ("Love", "Business", "Family")) -> dict:
    """
    Returns {"chart_id", "predictions": [...], "note": optional str}.
    Each prediction: prediction_id, domain, window_start, window_end,
    direction, event, mark=None (caller joins persisted marks).
    Raises ValueError("chart_not_found") / ValueError("no_chart_data").
    """
    # [event-engine-v1 2026-06-11] direct mapper + config-table gating.
    from antar_engine.dasha_event_mapper import find_future_windows
    from antar_engine.event_gating import (gate_windows, get_config,
                                           remap_to_delivery_window,
                                           event_min_score)
    from antar_engine.life_arc.event_taxonomy import event_title

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

    # ── [event-engine-v1 2026-06-11] direct mapper + age/stage gates ──────
    # find_future_windows IS the same validated engine; the chips layer is
    # forward-UI packaging (excludes loss_of_*, caps 8). Past validation is
    # admin-only, so sensitive events ARE probed — that is how an astrologer
    # builds trust ("did you lose your father between X and Y?").
    seen: dict = {}
    lookback_used = _LOOKBACK_LADDER[0]
    for lookback_days in _LOOKBACK_LADDER:
        lookback_used = lookback_days
        from_date = (now - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        try:
            wins = find_future_windows(
                lagna, birth_year, ads,
                from_date=from_date, to_date=today_str,
                min_score=3,  # raw floor; the real gate is gated_score below
                natal_planets=(chart_data.get("planets") or {}),
            )
        except Exception as e:
            print(f"[past_predictions] mapper failed ({lookback_days}d): {e}")
            wins = []

        gated = gate_windows(wins, birth_date_str, chart_record, supabase)

        _dl_cfg = get_config(supabase)
        for g in gated:
            # [delivery-bands 2026-06-11] remap PD-slice to the delivery band
            # of the qualifying AD (deterministic, config-driven; fixes the
            # measured 9-25mo early bias on commitment events).
            _dl_et = g.get("event_type") or ""
            ws, we_raw, _dl_remapped = remap_to_delivery_window(
                _dl_et, str(g.get("window_start"))[:10],
                str(g.get("window_end"))[:10], ads, _dl_cfg.get(_dl_et))
            # 30d backward pad: measured whisker-misses (events landing days
            # BEFORE the window opens — second-born -20d, residence -12d).
            # Forward slack comes from window_tolerance_days below.
            try:
                ws = (datetime.strptime(ws, "%Y-%m-%d")
                      - timedelta(days=30)).strftime("%Y-%m-%d")
            except Exception:
                pass
            # Early-bias fix: probe window = dasha window + forward tolerance
            # (events land up to one sub-period late — measured on 3 charts).
            try:
                tol = int(g.get("window_tolerance_days") or 60)
                we = (datetime.strptime(we_raw, "%Y-%m-%d")
                      + timedelta(days=tol)).strftime("%Y-%m-%d")
            except Exception:
                we = we_raw
            if not ws or not we or we >= today_str:
                continue  # closed windows only (tolerance-extended end in past)
            _dl_floor = event_min_score(_dl_cfg.get(_dl_et), _dl_et,
                                        float(min_score))
            if float(g.get("gated_score") or 0) < _dl_floor:
                continue
            domain = g.get("domain") or _DOMAIN_BY_EVENT.get(
                g.get("event_type") or "", "Career")
            if domains and domain not in domains:
                continue
            pid = make_prediction_id(chart_id, domain, ws, we)
            if pid in seen:
                continue
            et = g.get("event_type") or ""
            direction = g.get("direction") or (
                "watch" if et in _WATCH_EVENTS else "opening")
            title = ""
            try:
                title = event_title(et) or ""
            except Exception:
                pass
            chip_like = {"_event_type": et}
            seen[pid] = {
                "prediction_id": pid,
                "event_type": et,
                "domain": domain,
                "window_start": ws,
                "window_end": we,
                "direction": direction,
                "event": _strip_gate(title),
                "verdict": _strip_gate(title),
                "probe": _strip_gate(_chip_probe(domain, direction, ws, we)),
                "window_label": _fmt_window(ws, we),
                "question": _strip_gate(_chip_question(chip_like, ws, we, domain)),
                "score": int(g.get("score") or 0),
                "gated_score": float(g.get("gated_score") or 0),
                "age_at_window": g.get("age_at_window"),
                "delivery_remapped": bool(_dl_remapped),
                # conviction tiering from gated score (stored with marks for
                # later calibration — no curves yet, per brief)
                "conviction": ("medium" if float(g.get("gated_score") or 0) >= 10
                               else "low"),
                "mark": None,
            }
        if len(seen) >= n:
            break

    preds = sorted(seen.values(),
                   key=lambda p: (p["window_end"], p["gated_score"]),
                   reverse=True)[:n]
    out = {"chart_id": chart_id, "predictions": preds,
           "filters": {"min_score": float(min_score),
                       "domains": list(domains or []),
                       "gating": "age+stage (event_engine_config)"}}
    if not preds:
        out["note"] = (f"no closed windows passed the gates (gated_score >= "
                       f"{min_score}, domains {list(domains or [])}) in the "
                       f"last {lookback_used} days — not fabricating or "
                       "relaxing the gate silently.")
    return out
