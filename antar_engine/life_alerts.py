"""
antar_engine/life_alerts.py

Proactive life/financial alert builder — turns the (reactive) prediction engines
into a CALM feed of major upcoming turns the user should know about WITHOUT
asking. Each alert ships with its mitigation (a real remedy) — proactive
prediction + antidote in one card.

CALM policy (owner 2026-09-16): only MAJOR turns — a strong money window opening,
a lean/consolidate stretch beginning, an elevated-risk window, a relationship-
strain stretch, a mahadasha turn. Ranked, de-duplicated, honest (opportunity vs
caution, never alarm). NOT magnitude/tier (that class is falsified).

Rows match the existing `user_alerts` schema (alert_type/headline/body/urgency/
window_start/window_end/action_advice/remedy) so the existing alerts feed renders
them; `_alert_key` is a stable dedupe key the caller uses to avoid re-posting.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional


def _remedy_for(planet: str) -> str:
    """One plain, jargon-free remedy line for a planet (action + item + mantra)."""
    try:
        from antar_engine.practice_engine import REMEDIES, MANTRAS
        rem = (REMEDIES.get(planet, {}) or {}).get("GLOBAL") or {}
        act = rem.get("action", "")
        item = rem.get("item", "")
        man = (MANTRAS.get(planet, {}) or {}).get("sanskrit", "")
        parts = [p for p in (act, (item[:1].upper() + item[1:]) if item else "",
                             (f"Mantra: {man}" if man else "")) if p]
        return " · ".join(parts)
    except Exception:
        return ""


def _maha_rows(dashas):
    out = []
    for r in (dashas or {}).get("vimsottari", []) or []:
        if (r.get("level") or r.get("type")) == "mahadasha":
            try:
                s = datetime.strptime(str(r.get("start_date") or r.get("start"))[:10], "%Y-%m-%d").date()
                e = datetime.strptime(str(r.get("end_date") or r.get("end"))[:10], "%Y-%m-%d").date()
                out.append({"lord": r.get("lord_or_sign") or r.get("planet_or_sign"),
                            "start": s, "end": e})
            except Exception:
                continue
    out.sort(key=lambda x: x["start"])
    return out


def build_life_alerts(chart_data: dict, dashas: dict, birth_date: Optional[str] = None,
                      gender: Optional[str] = None, today: Optional[date] = None) -> list:
    """Return a CALM list of major upcoming-turn alerts (each with a remedy).
    Never raises."""
    today = today or date.today()
    alerts = []
    try:
        from antar_engine.business_timing import dasha_fortune
        bt = dasha_fortune(chart_data, dashas, today=today)
    except Exception:
        bt = {}

    # 1) WEALTH / STRONG BUILD WINDOW opening (opportunity)
    try:
        bw = (bt or {}).get("best_build_window")
        if bw:
            _s = datetime.strptime(bw["start"][:10], "%Y-%m-%d").date()
            if today <= _s <= today + timedelta(days=730):   # opening within 2y
                lord = bw.get("md_lord") or "Jupiter"
                alerts.append({
                    "alert_type": "wealth_window",
                    "headline": "A strong build-and-earn window is opening",
                    "body": ("Your chart's fortune turns supportive in this stretch — "
                             "the right window to push growth, raise, or expand, not to sit still."),
                    "urgency": "opportunity",
                    "window_start": bw["start"][:10], "window_end": bw["end"][:10],
                    "action_advice": "Line up your boldest money/business move for this window.",
                    "remedy": _remedy_for(lord),
                    "_alert_key": f"wealth_window:{bw['start'][:7]}",
                })
    except Exception:
        pass

    # 2) LEAN / CONSOLIDATE stretch beginning (caution)
    try:
        tp = (bt or {}).get("next_turning_point")
        if tp and tp.get("band") == "lean":
            _s = datetime.strptime(tp["starts"][:10], "%Y-%m-%d").date()
            if today <= _s <= today + timedelta(days=730):
                alerts.append({
                    "alert_type": "lean_stretch",
                    "headline": "A lean stretch is ahead — protect, don't over-extend",
                    "body": ("Fortune runs quieter in this period. It rewards consolidating, "
                             "clearing debt and guarding capital over big, capital-heavy bets."),
                    "urgency": "caution",
                    "window_start": tp["starts"][:10],
                    "window_end": (_s + timedelta(days=365)).isoformat(),
                    "action_advice": "Before it begins: build a cash buffer and avoid new heavy commitments.",
                    "remedy": _remedy_for("Saturn"),
                    "_alert_key": f"lean_stretch:{tp['starts'][:7]}",
                })
    except Exception:
        pass

    # 3) ELEVATED FINANCIAL-RISK signature (caution) — propensity, not a date
    try:
        from antar_engine.event_risk import bankruptcy_risk
        bk = bankruptcy_risk(chart_data)
        if bk.get("available") and bk.get("risk") == "elevated":
            alerts.append({
                "alert_type": "risk_window",
                "headline": "Your money base needs guarding right now",
                "body": ("The reserves-vs-obligations balance is stretched — worth "
                         "shoring up before any shock, not a prediction of ruin."),
                "urgency": "caution",
                "window_start": today.isoformat(),
                "window_end": (today + timedelta(days=180)).isoformat(),
                "action_advice": "Cut one recurring cost and rebuild a savings buffer this month.",
                "remedy": _remedy_for("Saturn"),
                "_alert_key": f"risk_window:{today.strftime('%Y-%m')}",
            })
    except Exception:
        pass

    # 4) RELATIONSHIP-STRAIN stretch (caution) — only when genuinely elevated
    try:
        from antar_engine.relationships import separation_timing, analyze_relationship
        _g = gender or "male"
        rel = analyze_relationship(chart_data, _g)
        if (rel.get("durability") or {}).get("level") in ("elevated", "moderate"):
            sep = separation_timing(chart_data, dashas, birth_date=birth_date, gender=_g)
            best = sep.get("best") if sep.get("available") else None
            if best and best.get("score", 0) >= 2.0:
                _yr = str(best.get("year") or best.get("window") or "")
                alerts.append({
                    "alert_type": "strain_window",
                    "headline": "A testing stretch for your relationship is ahead",
                    "body": ("A period that asks for extra care and honesty in your closest "
                             "bond — durability, not chemistry, is the work then. Not a doom date."),
                    "urgency": "caution",
                    "window_start": today.isoformat(),
                    "window_end": (today + timedelta(days=365)).isoformat(),
                    "action_advice": "Invest in steady attention and honest conversation now.",
                    "remedy": _remedy_for("Venus"),
                    "_alert_key": f"strain_window:{_yr or today.strftime('%Y')}",
                })
    except Exception:
        pass

    # 5) MAHADASHA TURN — a life chapter changing within ~18 months
    try:
        for m in _maha_rows(dashas):
            if today < m["start"] <= today + timedelta(days=540):
                alerts.append({
                    "alert_type": "dasha_turn",
                    "headline": "A new life chapter is about to begin",
                    "body": ("A major multi-year phase is turning over — the themes that carry "
                             "you shift. Worth preparing for the new season deliberately."),
                    "urgency": "opportunity",
                    "window_start": m["start"].isoformat(),
                    "window_end": m["end"].isoformat(),
                    "action_advice": "Name what you want this next chapter to build, before it starts.",
                    "remedy": _remedy_for(m["lord"]),
                    "_alert_key": f"dasha_turn:{m['start'][:7] if isinstance(m['start'], str) else m['start'].strftime('%Y-%m')}",
                })
                break
    except Exception:
        pass

    # rank: opportunities and cautions interleaved by soonest window
    def _rank(a):
        return a.get("window_start", "9999")
    alerts.sort(key=_rank)
    return alerts
