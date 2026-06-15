"""
antar_engine/practice_composer.py
─────────────────────────────────────────────────────────────────────────────
Practice redesign — priority selection + response composition.  Phase 1.

Takes the active negative remediations from practice_scopes, picks ONE as
today's priority (continuity over churn; then severity; then acuteness), and
assembles the response: full planet-coherent content for the priority, summary
lines for the rest, and the 7-chakra diagnostic.

Content coherence is guaranteed by construction: the priority's content is
pulled wholesale from practice_library[planet] — never mixed across planets.
"""

from __future__ import annotations

import os
from typing import Optional

from antar_engine.practice_library import (
    PRACTICE_LIBRARY, get_planet_content, personalize_gemstone, GEMSTONE_SCOPES,
    personalize_food, FOOD_SCOPES,
    personalize_remedy, YANTRA_SCOPES, DAAN_SCOPES, VRAT_SCOPES,
)
from antar_engine.practice_scopes import SCOPES
from antar_engine.practice_chakras import compute_chakra_states

# Shorter time-scale = more acute = wins ties.
_SCOPE_RANK = {"daily_transit": 0, "monthly_lk": 1, "varshphal_year": 2,
               "dasha_period": 3, "natal_weakness": 4}

# ── timeframe router (COWORK brief) ─────────────────────────────────────────
from antar_engine.practice_scopes import (
    TIMEFRAME_BY_SCOPE, CADENCE_BY_TIMEFRAME,
    TIMEFRAME_LEAD_PRIORITY, LEADABLE_TIMEFRAMES, _energy as _nrg_energy,
)

_TIMEFRAME_LABEL = {
    "this_year":      {"en": "This year",       "es": "Este año"},
    "this_month":     {"en": "This month",      "es": "Este mes"},
    "current_cycle":  {"en": "Current cycle",   "es": "Ciclo actual"},
    "natal_baseline": {"en": "Lifelong",        "es": "De por vida"},
    "today":          {"en": "Today",           "es": "Hoy"},
}


def _tf_of(entry: dict) -> str:
    return entry.get("timeframe_source") or TIMEFRAME_BY_SCOPE.get(entry.get("scope"), "natal_baseline")


def merge_by_planet(actives: list) -> list:
    """De-dupe actives by planet. Each merged entry keeps the contributing
    entry whose timeframe has the highest lead-priority as its primary, records
    every timeframe that flagged the planet in `contributing_sources`, and
    carries the max severity. This is the brief's 'good case' merge — a planet
    flagged by both natal and this-year shows once, tagged with both sources."""
    by_planet: dict = {}
    for e in actives or []:
        p = e.get("planet")
        if not p:
            continue
        by_planet.setdefault(p, []).append(e)
    merged = []
    for p, group in by_planet.items():
        primary = max(group, key=lambda e: (
            TIMEFRAME_LEAD_PRIORITY.get(_tf_of(e), 0), e.get("severity", 0.0)))
        sources = []
        for e in sorted(group, key=lambda e: -TIMEFRAME_LEAD_PRIORITY.get(_tf_of(e), 0)):
            tf = _tf_of(e)
            if tf not in sources:
                sources.append(tf)
        m = dict(primary)
        m["severity"] = max(e.get("severity", 0.0) for e in group)
        m["contributing_sources"] = sources
        merged.append(m)
    return merged


def _why_now(entry: dict, lang: str) -> str:
    """Concrete, timeframe-named reason. Never the generic 'exceptionally strong
    right now' filler. Uses the energy layer — no planet names leak."""
    tf = _tf_of(entry)
    e = _nrg_energy(entry.get("planet"), lang)
    E = (e[:1].upper() + e[1:]) if e else e
    srcs = entry.get("contributing_sources") or [tf]
    merged_with_natal = ("natal_baseline" in srcs and tf in LEADABLE_TIMEFRAMES)
    if lang == "es":
        if merged_with_natal:
            return (f"El trabajo de toda la vida con {e} es exactamente lo que "
                    f"este año te pide — por eso encabeza hoy.")
        return {
            "this_year":      f"Tu carta anual pone {e} en foco este año — es la ventana para trabajarla.",
            "this_month":     f"Este mes una presión pasajera cruza {e} — atiéndela ahora; cede al cambiar el mes.",
            "current_cycle":  f"Estás en un capítulo de vida construido sobre {e} — esta es la práctica que ese capítulo premia.",
            "natal_baseline": f"El trabajo de por vida con {e} — tu práctica de fondo, no atada a ninguna temporada.",
            "today":          f"Hoy algo presiona {e} — una pequeña práctica estabiliza el día.",
        }.get(tf, f"{E} pide atención constante.")
    if merged_with_natal:
        return (f"The lifelong work on {e} is exactly what this year asks for "
                f"— that's why it leads today.")
    return {
        "this_year":      f"Your annual chart puts {e} in focus this year — this is the window to work it.",
        "this_month":     f"This month a passing pressure crosses {e} — tend it now; it eases as the month turns.",
        "current_cycle":  f"You're in a life chapter built on {e} — this is the practice that chapter rewards.",
        "natal_baseline": f"The lifelong work on {e} — your steady background practice, not tied to any one season.",
        "today":          f"Today something presses on {e} — a small practice steadies the day.",
    }.get(tf, f"{E} wants steady attention.")


def _stamp_timeframe_fields(entry: dict, lang: str) -> dict:
    """Add timeframe_source / contributing_sources / why_now / cadence / source."""
    tf = _tf_of(entry)
    entry["timeframe_source"] = tf
    if "contributing_sources" not in entry:
        entry["contributing_sources"] = [tf]
    entry["why_now"] = _why_now(entry, lang)
    entry["cadence"] = CADENCE_BY_TIMEFRAME.get(tf, "daily_tunein")
    entry["timeframe_label"] = _TIMEFRAME_LABEL.get(tf, {}).get(lang, tf)
    entry["source"] = "selection: timeframe-router; content: existing LK remedy tables"
    return entry


def select_practice_set(actives: list, sticky_key=None, completed_today=None) -> dict:
    """Brief's prioritized selection. Returns {lead, secondary, baseline}.
      lead      — highest-priority *time-active leadable* layer (Year>Month>Cycle);
                  natal/today never lead when a leadable layer exists.
      secondary — up to 2 further merged entries (lead + baseline excluded).
      baseline  — the structurally-weakest natal entry, always present as
                  background, unless it merged INTO the lead.
    """
    completed_today = completed_today or {}
    merged = merge_by_planet(actives)
    if not merged:
        return {"lead": None, "secondary": [], "baseline": None}

    leadable = [m for m in merged if _tf_of(m) in LEADABLE_TIMEFRAMES]
    natal = [m for m in merged if _tf_of(m) == "natal_baseline"]

    lead = None
    if sticky_key:
        for m in leadable:
            if (m.get("planet"), m.get("scope")) == sticky_key and not completed_today.get(m.get("planet")):
                lead = m
                break
    if lead is None and leadable:
        lead = max(leadable, key=lambda m: (
            TIMEFRAME_LEAD_PRIORITY.get(_tf_of(m), 0), m.get("severity", 0.0)))
    if lead is None:
        # No time-active leadable layer -> natal baseline is promoted to lead.
        lead = max(merged, key=lambda m: m.get("severity", 0.0))

    baseline = None
    if natal:
        top_natal = max(natal, key=lambda m: m.get("severity", 0.0))
        if top_natal.get("planet") != (lead or {}).get("planet"):
            baseline = top_natal

    used = {(lead or {}).get("planet"), (baseline or {}).get("planet")}
    rest = [m for m in merged if m.get("planet") not in used]
    rest.sort(key=lambda m: (
        TIMEFRAME_LEAD_PRIORITY.get(_tf_of(m), 0), m.get("severity", 0.0)), reverse=True)
    secondary = rest[:2]
    return {"lead": lead, "secondary": secondary, "baseline": baseline}


def _router_enabled() -> bool:
    return os.getenv("PRACTICE_TIMEFRAME_ROUTER", "on").strip().lower() not in ("off", "0", "false")


def _lang(language: str) -> str:
    return "es" if str(language).lower().startswith("es") else "en"


def _scope_label_i18n(scope, language):
    """3-language scope label (patch_language_fidelity). Falls back to SCOPES."""
    try:
        from antar_engine.i18n import scope_label as _sl
        return _sl(scope, language)
    except Exception:
        return SCOPES.get(scope, {}).get("label", scope)


def _months_suffix_i18n(ml, language):
    base = str(language).split("_")[0].split("-")[0].lower()
    if base in ("es", "pt"):
        return f" (~{ml} meses)"
    return f" (~{ml} months left)"


def select_today_priority(
    actives: list[dict],
    sticky_key: Optional[tuple] = None,
    completed_today: Optional[dict] = None,
) -> Optional[dict]:
    """
    Pick one remediation as today's priority.
      1. Continuity — if the previously-priority practice exists and is NOT
         completed today, it stays priority.
      2. Otherwise highest severity.
      3. Tiebreak — shorter time-scale (more acute) wins.
    """
    if not actives:
        return None
    completed_today = completed_today or {}
    if sticky_key:
        for e in actives:
            if (e["planet"], e["scope"]) == sticky_key and not completed_today.get(e["planet"]):
                return e
    return sorted(
        actives,
        key=lambda e: (-e.get("severity", 0), _SCOPE_RANK.get(e["scope"], 9)),
    )[0]


def _one_line(entry: dict, lang: str) -> str:
    why = entry.get("why_paragraph", "") or entry.get("trigger_detail", "")
    # First sentence.
    for sep in (". ", ". ", "."):
        if sep in why:
            return why.split(sep)[0].strip() + "."
    return why


def _months_left(md_ends: Optional[str], today) -> Optional[int]:
    if not md_ends:
        return None
    try:
        from datetime import datetime
        dt = datetime.strptime(md_ends, "%B %Y")
        return max(0, (dt.year - today.year) * 12 + (dt.month - today.month))
    except Exception:
        return None


def _fallback_priority(chart: dict, conditions: dict, language: str) -> Optional[dict]:
    """When nothing is firing, offer maintenance for the softest planet."""
    lang = _lang(language)
    present = [(p, m) for p, m in (conditions or {}).items() if p in PRACTICE_LIBRARY]
    if not present:
        return None
    p, m = min(present, key=lambda kc: kc[1].get("weight", 0.9))
    from antar_engine.practice_scopes import _energy as _nrg
    _e = _nrg(p, lang)
    why = (f"Nada urgente hoy. Una práctica suave de mantenimiento mantiene {_e} estable."
           if lang == "es" else
           f"Nothing urgent today. A gentle maintenance practice keeps {_e} steady.")
    return {
        "scope": "natal_weakness", "planet": p, "supporting_planets": [], "severity": 0.2,
        "trigger_detail": f"maintenance for {p}",
        "duration_label": ("Diario, continuo" if lang == "es" else "Daily, ongoing"),
        "ttl_days": None, "why_paragraph": why,
    }


def build_derivation_layers(actives: list, priority) -> dict:
    """Audit view of today_priority's derivation. Pure structured diagnostic
    data (no user-facing prose): which scopes fired, at what intensity, and
    which scope/planet was selected. Additive — changes no decision logic."""
    actives = actives or []

    def _sub(scope_name):
        hits = [e for e in actives if e.get("scope") == scope_name]
        if not hits:
            return {"fired": False, "intensity": 0.0, "planet": None, "count": 0}
        top = max(hits, key=lambda e: e.get("severity", 0.0))
        return {
            "fired": True,
            "intensity": round(float(top.get("severity", 0.0)), 2),
            "planet": top.get("planet"),
            "count": len(hits),
        }

    layers = {
        "natal_weakness": _sub("natal_weakness"),
        "dasha_period":   _sub("dasha_period"),
        "varshphal_year": _sub("varshphal_year"),
        "monthly_lk":     _sub("monthly_lk"),
        "daily_transit":  _sub("daily_transit"),
    }

    # lk_sleeping is a kind inside natal_weakness, not its own scope.
    sleeping = [e for e in actives
                if e.get("scope") == "natal_weakness"
                and "sleeping" in (e.get("trigger_detail") or "").lower()]
    if sleeping:
        top = max(sleeping, key=lambda e: e.get("severity", 0.0))
        layers["lk_sleeping"] = {
            "fired": True,
            "intensity": round(float(top.get("severity", 0.0)), 2),
            "planet": top.get("planet"),
            "count": len(sleeping),
        }
    else:
        layers["lk_sleeping"] = {"fired": False, "intensity": 0.0,
                                 "planet": None, "count": 0}

    selected = None
    if priority:
        selected = {
            "scope": priority.get("scope"),
            "planet": priority.get("planet"),
            "intensity": round(float(priority.get("severity", 0.0)), 2),
        }
    return {"selected": selected, "layers": layers}


def compose_practice_response(
    chart: dict,
    actives: list[dict],
    *,
    chart_id: str,
    user_name: Optional[str],
    user_age: Optional[int],
    language: str,
    today_str: str,
    today_date,
    conditions: dict,
    streaks: Optional[dict] = None,            # {planet: {"days": int, "best": int}}
    completed_today: Optional[dict] = None,    # {planet: bool}
    sticky_key: Optional[tuple] = None,
    generated_at: Optional[str] = None,
    # [chakra-2axis] forwarded to compute_chakra_states
    ashtakavarga: Optional[dict] = None,
    dashas: Optional[dict] = None,
    lk_data: Optional[dict] = None,
    transits: Optional[dict] = None,
) -> dict:
    lang = _lang(language)
    streaks = streaks or {}
    completed_today = completed_today or {}

    if _router_enabled():
        _set = select_practice_set(actives, sticky_key, completed_today)
        priority = _set["lead"] or _fallback_priority(chart, conditions, language)
        # secondary entries first, natal baseline appended last as background.
        others = list(_set["secondary"])
        if _set["baseline"] is not None:
            others.append(_set["baseline"])
    else:
        priority = select_today_priority(actives, sticky_key, completed_today) \
            or _fallback_priority(chart, conditions, language)
        others = [e for e in actives if priority is None or
                  (e["planet"], e["scope"]) != (priority["planet"], priority["scope"])]

    # ── today_priority (full, single-planet content) ────────────────────────
    today_priority = None
    if priority:
        pl = priority["planet"]
        content = get_planet_content(pl, language)
        st = streaks.get(pl, {})
        scope = priority["scope"]
        dur = priority.get("duration_label", SCOPES.get(scope, {}).get("label", ""))
        if scope == "dasha_period" and priority.get("_md_ends"):
            ml = _months_left(priority["_md_ends"], today_date)
            if ml is not None:
                dur += _months_suffix_i18n(ml, language)
        today_priority = {
            "planet": pl,
            "scope": scope,
            "scope_label": _scope_label_i18n(scope, language),
            "timeframe_source": _tf_of(priority),
            "timeframe_label": _TIMEFRAME_LABEL.get(_tf_of(priority), {}).get(lang, _tf_of(priority)),
            "contributing_sources": priority.get("contributing_sources", [_tf_of(priority)]),
            "cadence": CADENCE_BY_TIMEFRAME.get(_tf_of(priority), "daily_tunein"),
            "duration_label": dur,
            "why": priority.get("why_paragraph", ""),
            "why_now": _why_now(priority, lang),
            "source": "selection: timeframe-router; content: existing LK remedy tables",
            "streak_days": int(st.get("days", 0)),
            "streak_best": int(st.get("best", st.get("days", 0))),
            "completed_today": bool(completed_today.get(pl, False)),
            "mantra": content.get("mantra"),
            "body": content.get("body"),
            "breath": content.get("breath"),
            "daily_action": content.get("daily_action"),
            "affirmation": content.get("affirmation"),
            "chakras_to_balance": content.get("chakras_balanced"),
            "why_this_works": content.get("why_this_works"),
        }
        # [gemstone] Advanced permanent-wear remedy. Only durable scopes get a
        # stone; transient triggers (daily_transit / monthly_lk) return null so
        # the frontend renders its empty state.
        today_priority["gemstone"] = (
            personalize_gemstone(pl, scope, language, chart=chart, conditions=conditions)
            if scope in GEMSTONE_SCOPES else None
        )
        # [food] Ayurveda Ahar — daily dietary remedy. Same durable-scope gate
        # as the gemstone; transient triggers (daily_transit / monthly_lk) -> null.
        today_priority["food"] = (
            personalize_food(pl, scope, language, chart=chart, conditions=conditions)
            if scope in FOOD_SCOPES else None
        )
        # [remedy3] Yantra / Daan / Vrat — per-remedy scope gates. Yantra and
        # vrat are durable-only; daan additionally fires on monthly_lk. Out of
        # scope -> null.
        today_priority["yantra"] = (
            personalize_remedy("yantra", pl, scope, language, chart=chart, conditions=conditions)
            if scope in YANTRA_SCOPES else None
        )
        today_priority["daan"] = (
            personalize_remedy("daan", pl, scope, language, chart=chart, conditions=conditions)
            if scope in DAAN_SCOPES else None
        )
        today_priority["vrat"] = (
            personalize_remedy("vrat", pl, scope, language, chart=chart, conditions=conditions)
            if scope in VRAT_SCOPES else None
        )
        # Auditability — which scopes fired and which was chosen.
        today_priority["derivation_layers"] = build_derivation_layers(actives, priority)

    # ── active (summaries only) ─────────────────────────────────────────────
    active = []
    for e in others:
        p = e["planet"]
        st = streaks.get(p, {})
        scope = e["scope"]
        dur = e.get("duration_label", "")
        if scope == "dasha_period" and e.get("_md_ends"):
            ml = _months_left(e["_md_ends"], today_date)
            if ml is not None:
                dur += _months_suffix_i18n(ml, language)
        active.append(_stamp_timeframe_fields({
            "planet": p,
            "scope": scope,
            "scope_label": _scope_label_i18n(scope, language),
            "duration_label": dur,
            "one_line": _one_line(e, lang),
            "streak_days": int(st.get("days", 0)),
            "completed_today": bool(completed_today.get(p, False)),
            "contributing_sources": e.get("contributing_sources", [_tf_of(e)]),
        }, lang))

    # ── chakra diagnostic (priority planet drives "primary") ────────────────
    chakra_states = compute_chakra_states(
        chart, conditions=conditions,
        priority_planet=(priority["planet"] if priority else None),
        language=language,
        ashtakavarga=ashtakavarga,
        dashas=dashas,
        lk_data=lk_data,
        transits=transits,
    )

    return {
        "chart_id": chart_id,
        "user_name": user_name,
        "user_age": user_age,
        "current_date": today_str,
        "language": language,
        "generated_at": generated_at,
        "today_priority": today_priority,
        "active": active,
        "chakra_states": chakra_states,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Streak math (pure; DB rows passed in by the endpoint)
# ─────────────────────────────────────────────────────────────────────────────

def compute_streak(local_dates: list, today) -> int:
    """
    Consecutive-day streak ending today or yesterday from a list of ISO
    local_date strings (or date objects) for one (chart, planet).
    """
    from datetime import timedelta, date as _date
    dates = set()
    for d in local_dates:
        if isinstance(d, str):
            dates.add(d[:10])
        elif isinstance(d, _date):
            dates.add(d.isoformat())
    if not dates:
        return 0
    check = today
    if check.isoformat() not in dates:
        check = today - timedelta(days=1)
        if check.isoformat() not in dates:
            return 0
    streak = 0
    while check.isoformat() in dates:
        streak += 1
        check -= timedelta(days=1)
    return streak


def compute_best_streak(local_dates: list) -> int:
    """Longest consecutive-day run ever, from a list of ISO local_date strings."""
    from datetime import date as _date
    days = sorted({(d[:10] if isinstance(d, str) else d.isoformat()) for d in local_dates})
    if not days:
        return 0
    best = run = 1
    prev = _date.fromisoformat(days[0])
    for d in days[1:]:
        cur = _date.fromisoformat(d)
        run = run + 1 if (cur - prev).days == 1 else 1
        best = max(best, run)
        prev = cur
    return best
