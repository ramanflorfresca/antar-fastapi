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
    why = ("Nada urgente hoy. Una práctica suave de mantenimiento para {p} mantiene tu base estable."
           if lang == "es" else
           "Nothing urgent today. A gentle maintenance practice for {p} keeps your foundation steady.").format(p=p)
    return {
        "scope": "natal_weakness", "planet": p, "supporting_planets": [], "severity": 0.2,
        "trigger_detail": f"maintenance for {p}",
        "duration_label": ("Diario, continuo" if lang == "es" else "Daily, ongoing"),
        "ttl_days": None, "why_paragraph": why,
    }


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
) -> dict:
    lang = _lang(language)
    streaks = streaks or {}
    completed_today = completed_today or {}

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
            "duration_label": dur,
            "why": priority.get("why_paragraph", ""),
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
        active.append({
            "planet": p,
            "scope": scope,
            "scope_label": _scope_label_i18n(scope, language),
            "duration_label": dur,
            "one_line": _one_line(e, lang),
            "streak_days": int(st.get("days", 0)),
            "completed_today": bool(completed_today.get(p, False)),
        })

    # ── chakra diagnostic (priority planet drives "primary") ────────────────
    chakra_states = compute_chakra_states(
        chart, conditions=conditions,
        priority_planet=(priority["planet"] if priority else None),
        language=language,
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
