"""
antar_engine/monthly_v2.py — new /predict/monthly contract assembler
=====================================================================

Computes the Monthly brief's contract on top of the existing endpoint
output. The month IS the clamped integral of the daily series — every
field that quantifies the month derives from score_day across the
birth-anchored period, so day and month cannot disagree.

Contract:
  {
    "range": "JUN 10 – JUL 10",
    "period_start": "2026-06-10",
    "period_end":   "2026-07-10",            # closed anchor (display)
    "theme":        "...",                   # narrated from MD+AD+PD
    "energy_label": "Steady, building",      # enum-flavored
    "energy_pct":   64,                      # mean(score_day) over period
    "best_week":    {"start","end","label","line"},
    "caution_week": {"start","end","label","line"},
    "pins": [{"date","day_index","domain","text","tone"}, ...],
    "domains": [
      {"key":"career","name":"Career","trend":"rising|pressure|steady","line":"..."},
      ...   (always exactly 5: career / money / love / health / family)
    ]
  }

By construction:
  * best_week / caution_week date ranges are STRUCTURALLY inside the
    period — they come from rolling_window_extremes over the per-day
    series we computed for THIS period.
  * domains[] is always exactly 5 — one card per area, last-write-wins
    inside the composer.
  * energy_pct is the score_range mean — same scale as /daily strength.
"""
from __future__ import annotations

from datetime import date as _date, datetime as _dt, timedelta as _td
from typing import Any, Dict, List, Optional, Tuple


# ── Monthly contract domain palette (DIFFERENT from daily's 5) ──
# Daily uses Mind / Body / Work / Money / People.
# Monthly uses Career / Money / Love / Health / Family.
_MONTH_DOMAIN_ORDER = ("career", "money", "love", "health", "family")
_MONTH_DOMAIN_LABEL = {
    "career": "Career",
    "money":  "Money",
    "love":   "Love",
    "health": "Health",
    "family": "Family",
}

# How daily's domain_states roll up into the monthly palette.
# (daily_key -> monthly_key)
_DAILY_TO_MONTH_DOMAIN = {
    "work":   "career",
    "money":  "money",
    "people": "love",     # daily 'people' becomes monthly 'love'
    "body":   "health",
    "mind":   "family",   # mind feeds family/home life — best available mapping
}

# Trend enum from monthly brief.
_TREND_RISING   = "rising"
_TREND_PRESSURE = "pressure"
_TREND_STEADY   = "steady"

# Per-domain plain-language line per trend.
_MONTH_LINES = {
    _TREND_RISING: {
        "career": "Career is where the month rewards you — push the visible, high-stakes work.",
        "money":  "Money has momentum this month — chase what you're owed, send invoices.",
        "love":   "Relationships deepen this month — invest in the people who actually matter.",
        "health": "Your body holds up well this month — a good window to build a habit.",
        "family": "Home life feels warmer — give it deliberate time, not leftovers.",
    },
    _TREND_PRESSURE: {
        "career": "Career runs heavier this month — protect your energy, don't overcommit.",
        "money":  "Money runs tight this month — defer big purchases, keep a cushion.",
        "love":   "Relationships need patience this month — listen more, react less.",
        "health": "Your body needs more rest this month — don't push past warning signs.",
        "family": "Family life asks for attention — small frictions compound if ignored.",
    },
    _TREND_STEADY: {
        "career": "Career is steady — consistent effort outpaces any big bet.",
        "money":  "Money is quiet — no big moves, tend the cushion.",
        "love":   "Relationships are calm — short, warm touches are enough.",
        "health": "Body is steady — keep the habit, no heroics.",
        "family": "Family life is even — small, ordinary care holds it together.",
    },
}

_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
_MALEFIC = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}


# ── Helpers ─────────────────────────────────────────────────────────
def _coerce_date(x) -> Optional[_date]:
    if x is None:
        return None
    if isinstance(x, _date) and not isinstance(x, _dt):
        return x
    if isinstance(x, _dt):
        return x.date()
    if isinstance(x, str):
        try:
            return _date.fromisoformat(x[:10])
        except Exception:
            return None
    return None


def _scrub(text: str, language: str, field_type: str = "plain") -> str:
    if not isinstance(text, str) or not text:
        return text
    try:
        from antar_engine.output_strips import apply_user_facing_strips
        return apply_user_facing_strips(text, language=(language or "en"),
                                        field_type=field_type)
    except Exception:
        return text


def _format_range_label(start: _date, end_inclusive: _date) -> str:
    """'JUN 10 – JUL 10' — uppercase 3-letter month + day, en-dash."""
    s = f"{start.strftime('%b').upper()} {start.day}"
    e = f"{end_inclusive.strftime('%b').upper()} {end_inclusive.day}"
    return f"{s} – {e}"


def _format_week_label(start: _date, end_inclusive: _date) -> str:
    """'Jun 17–23' — mixed-case short, no spaces around dash."""
    if start.month == end_inclusive.month:
        return f"{start.strftime('%b')} {start.day}–{end_inclusive.day}"
    return f"{start.strftime('%b')} {start.day} – {end_inclusive.strftime('%b')} {end_inclusive.day}"


# ── Theme from MD+AD+PD ─────────────────────────────────────────────
_LORD_THEME_FRAG = {
    "Jupiter": "the month favors growth, teaching and mentorship",
    "Venus":   "the month favors relationships and creative work",
    "Saturn":  "the month favors patient, structural effort",
    "Sun":     "the month favors visibility and ownership",
    "Moon":    "the month favors inward work and trust in your read",
    "Mars":    "the month favors directed action — one hard push, not many",
    "Mercury": "the month favors conversations, writing and deals",
    "Rahu":    "the month favors unconventional moves and unusual openings",
    "Ketu":    "the month favors release, simplification and letting go",
}


def _compose_theme(lords: Dict[str, Optional[str]], language: str) -> str:
    md = (lords or {}).get("md")
    ad = (lords or {}).get("ad")
    pd = (lords or {}).get("pd")
    # Pin theme to MD if present; nuance with AD; PD adds texture (still slow).
    parts = []
    base = _LORD_THEME_FRAG.get((md or "").strip().title())
    if base:
        parts.append(base.capitalize() + ".")
    if ad and isinstance(ad, str) and ad.strip().title() != (md or "").strip().title():
        nuance = _LORD_THEME_FRAG.get(ad.strip().title())
        if nuance:
            parts.append("Underneath, " + nuance + ".")
    if pd and isinstance(pd, str):
        pd_t = pd.strip().title()
        if pd_t and pd_t not in {(md or "").strip().title(),
                                  (ad or "").strip().title()}:
            tail = _LORD_THEME_FRAG.get(pd_t)
            if tail:
                parts.append("Short-term texture: " + tail + ".")
    if not parts:
        return _scrub("A steady month — small, consistent moves outpace big bets.",
                      language, "plain")
    return _scrub(" ".join(parts), language, "plain")


def _energy_label_from_pct(pct: int) -> str:
    if pct >= 78: return "Strong, expansive"
    if pct >= 65: return "Steady, building"
    if pct >= 50: return "Mixed, deliberate"
    if pct >= 35: return "Lower, protect"
    return "Heavy, contracting"


# ── Aggregation across the per-day score series ─────────────────────
def _aggregate_domains(series: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Roll up daily domain_states into the 5-slot monthly palette.

    Trend rule:
      favorable_count - caution_count  >  +n  -> rising
      caution_count   - favorable_count > +n  -> pressure
      else                                    -> steady
    n = 25% of the day count so trend reflects a real majority, not noise.
    """
    if not series:
        return {k: _TREND_STEADY for k in _MONTH_DOMAIN_ORDER}
    counts = {k: {"fav": 0, "cau": 0} for k in _MONTH_DOMAIN_ORDER}
    n = len(series)
    for entry in series:
        states = (entry.get("domain_states") or {})
        for d_key, d_state in states.items():
            m_key = _DAILY_TO_MONTH_DOMAIN.get(d_key)
            if not m_key:
                continue
            if d_state == "favorable":
                counts[m_key]["fav"] += 1
            elif d_state == "caution":
                counts[m_key]["cau"] += 1
    threshold = max(1, n // 4)   # 25% of days
    out: Dict[str, str] = {}
    for m_key in _MONTH_DOMAIN_ORDER:
        f = counts[m_key]["fav"]
        c = counts[m_key]["cau"]
        if f - c >= threshold:
            out[m_key] = _TREND_RISING
        elif c - f >= threshold:
            out[m_key] = _TREND_PRESSURE
        else:
            out[m_key] = _TREND_STEADY
    return out


def _domains_v2(series: List[Dict[str, Any]], language: str
                ) -> List[Dict[str, Any]]:
    """Always exactly 5 entries, one per slot, in canonical order."""
    trends = _aggregate_domains(series)
    out: List[Dict[str, Any]] = []
    for key in _MONTH_DOMAIN_ORDER:
        trend = trends.get(key, _TREND_STEADY)
        line  = _MONTH_LINES.get(trend, _MONTH_LINES[_TREND_STEADY])\
                            .get(key, "Steady month for this area.")
        out.append({
            "key":   key,
            "name":  _MONTH_DOMAIN_LABEL[key],
            "trend": trend,
            "line":  _scrub(line, language, "plain"),
        })
    return out


# ── Best/caution week from rolling 7-day score_range extremes ───────
def _week_object(series: List[Dict[str, Any]], window_start_iso: str,
                 period_start: _date, period_end_exclusive: _date,
                 polarity: str, language: str) -> Dict[str, Any]:
    """Build a {start,end,label,line} from a per-day series anchor.
    polarity = 'best' or 'caution'."""
    if not window_start_iso:
        return {}
    try:
        s = _date.fromisoformat(window_start_iso)
    except Exception:
        return {}
    # 7-day window, clamped to the period end.
    e = s + _td(days=6)
    if e >= period_end_exclusive:
        e = period_end_exclusive - _td(days=1)
    if s < period_start:
        s = period_start
    label = _format_week_label(s, e)
    if polarity == "best":
        line = ("The week's strongest stretch — schedule what matters most then.")
    else:
        line = ("The week's friction point — keep your calendar loose, plan margin.")
    return {
        "start": s.isoformat(),
        "end":   e.isoformat(),
        "label": label,
        "line":  _scrub(line, language, "plain"),
    }


# ── Pins (dated actions) from the per-day series + panchanga texture ─
def _pins_from_series(series: List[Dict[str, Any]], domains_v2: List[Dict[str, Any]],
                      period_start: _date, language: str,
                      max_pins: int = 4) -> List[Dict[str, Any]]:
    """Pick up to N dated pins:
      - one 'do' pin on the highest-score day, tagged to its strongest favorable domain
      - one 'hold' pin on the lowest-score day, tagged to its strongest caution domain
      - additional pins on lunar texture days surfaced in score_day.layers.panchanga
    Each pin carries date, day_index (0-based offset from period_start), domain, text, tone.
    """
    pins: List[Dict[str, Any]] = []
    if not series:
        return pins

    # Domain that's trending most strongly in either direction this month.
    top_rising   = next((d["key"] for d in domains_v2 if d["trend"] == _TREND_RISING), "career")
    top_pressure = next((d["key"] for d in domains_v2 if d["trend"] == _TREND_PRESSURE), "money")

    # Sort by raw_score; pick the extremes (avoid same day collisions).
    by_score = sorted(series, key=lambda x: x.get("raw_score", 0.0))
    worst = by_score[0]
    best  = by_score[-1]

    def _idx(d_iso: str) -> int:
        try:
            d = _date.fromisoformat(d_iso)
            return max(0, (d - period_start).days)
        except Exception:
            return 0

    do_text = {
        "career": "Schedule the visible career move",
        "money":  "Send the invoice, ask for the raise",
        "love":   "Make the warm, deliberate gesture",
        "health": "Book the health check",
        "family": "Plan the unrushed family time",
    }.get(top_rising, "Push the thing that matters")

    hold_text = {
        "career": "Hold big career commitments",
        "money":  "Hold big purchases",
        "love":   "Postpone hard conversations",
        "health": "Don't push past warning signs",
        "family": "Hold off on contentious topics",
    }.get(top_pressure, "Hold big moves")

    pins.append({
        "date":      best.get("date"),
        "day_index": _idx(best.get("date", "")),
        "domain":    top_rising,
        "text":      _scrub(do_text, language, "plain"),
        "tone":      "do",
    })
    if worst.get("date") != best.get("date"):
        pins.append({
            "date":      worst.get("date"),
            "day_index": _idx(worst.get("date", "")),
            "domain":    top_pressure,
            "text":      _scrub(hold_text, language, "plain"),
            "tone":      "hold",
        })

    return pins[:max_pins]


# ── Public API ──────────────────────────────────────────────────────
def compose_monthly_contract(chart_record: Dict[str, Any],
                             legacy_response: Dict[str, Any],
                             language: str = "en"
                             ) -> Dict[str, Any]:
    """
    Build the monthly brief's contract on top of the existing endpoint.

    Pulls the per-day series from `legacy_response._debug_reasoning.score_day_series`
    (populated by patch_monthly_uses_score_day). Falls back to an empty
    series — the resulting contract still ships, just with steady trends
    and no pins, never crashing.
    """
    language = (language or "en").split("-")[0].lower()
    if language not in ("en", "es", "pt"):
        language = "en"

    out: Dict[str, Any] = {}

    # 1. Period boundaries (closed-anchor display).
    ps_iso = legacy_response.get("period_start")
    pe_iso = legacy_response.get("period_end")
    ps = _coerce_date(ps_iso)
    pe = _coerce_date(pe_iso)
    if ps and pe and pe > ps:
        out["range"]        = _format_range_label(ps, pe)
        out["period_start"] = ps.isoformat()
        out["period_end"]   = pe.isoformat()
    else:
        # Defensive fallback — never crash the response.
        out["range"]        = legacy_response.get("range", "")
        out["period_start"] = ps_iso or ""
        out["period_end"]   = pe_iso or ""

    # 2. Per-day series + extremes (already computed by the monthly wire).
    dbg = (legacy_response.get("_debug_reasoning") or {})
    series: List[Dict[str, Any]] = dbg.get("score_day_series") or []
    best_iso: Optional[str] = dbg.get("score_day_best")
    caution_iso: Optional[str] = dbg.get("score_day_caution")

    # 3. energy_pct + energy_label from the same series.
    if series:
        avg = sum(int(x.get("score", 50)) for x in series) / max(1, len(series))
        out["energy_pct"] = int(round(avg))
    else:
        out["energy_pct"] = 50
    out["energy_label"] = _scrub(_energy_label_from_pct(out["energy_pct"]),
                                  language, "plain")

    # 4. Theme — narrated from MD+AD+PD lords reported by score_day's
    #    structural layer (in the first day's debug if available).
    lords = (((series[0] or {}).get("layers") if series else None) or {})
    structural = lords.get("structural") if isinstance(lords, dict) else None
    md_ad_pd = (structural or {}).get("lords") if isinstance(structural, dict) else None
    if not md_ad_pd:
        # Try the legacy chart fallback.
        md_ad_pd = {
            "md": legacy_response.get("current_dasha"),
            "ad": None, "pd": None,
        }
    out["theme"] = _compose_theme(md_ad_pd, language)

    # 5. best_week / caution_week as objects.
    if ps and pe and pe > ps:
        period_end_exclusive = pe + _td(days=1) if (pe and series and
                                                    _date.fromisoformat(series[-1]["date"]) == pe) else pe
        # If period_end is the closed anchor (e.g. Jul 10) the series ends
        # at Jul 9 — clamp window ends at series tail, not anchor.
        last_series = _date.fromisoformat(series[-1]["date"]) if series else pe
        period_end_clamp_exclusive = last_series + _td(days=1)
        out["best_week"] = _week_object(series, best_iso, ps,
                                        period_end_clamp_exclusive,
                                        "best", language) or {}
        out["caution_week"] = _week_object(series, caution_iso, ps,
                                            period_end_clamp_exclusive,
                                            "caution", language) or {}
    else:
        out["best_week"] = {}
        out["caution_week"] = {}

    # 6. domains[] always exactly 5.
    out["domains"] = _domains_v2(series, language)

    # 7. pins[]
    out["pins"] = _pins_from_series(series, out["domains"], ps or _date.today(),
                                    language)

    return out


__all__ = ["compose_monthly_contract"]
