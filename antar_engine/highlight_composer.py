"""
highlight_composer.py — builds the Layer-2 `highlights` list for a surface.

Public API:
    build_highlights(scope, language, ctx) -> list[{domain, text, priority}]

`ctx` is a plain dict assembled by the calling endpoint from data it has ALREADY
computed deterministically (no new LLM call, no astrology re-derivation here):

    ctx = {
        "lk_daily":   <compute_lk_daily_diagnostic(...) result or {}>,
        "signal0":    <generate_weekly_signals(...)[0] or {}>,   # today's day signal
        "panchanga":  <format_daily_for_user(panchanga) or {}>,  # timing windows
        "dasha_md":   "Jupiter",   # current major-period lord  (or "")
        "dasha_ad":   "Saturn",    # current sub-period lord     (or "")
        "nakshatra_profile": {"energy":..., "aligned":[...], "friction":[...]} or {},
    }

Design guarantees:
  * Deterministic: every signal derives from a ctx condition, never invented.
  * Jargon-free: text comes from highlight_templates (already user-facing).
  * Safe: never raises — returns [] on any internal error so the endpoint is
    unaffected. Priorities are consecutive ints 1..N. Domains are from the
    locked enum. Count respects SCOPE_LIMITS / SCOPE_FLOOR.
  * Translation: text stays English here; the endpoint's @translate_response
    translates the `text` leaf for es/pt.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from antar_engine import highlight_templates as T


@dataclass
class Condition:
    domain: str
    text: str
    intensity: float = 1.0
    source: str = ""          # debugging only; not serialized
    _seen_key: str = ""       # dedupe key (domain is usually enough)


def _norm_lk_domains(values) -> List[str]:
    out = []
    if isinstance(values, list):
        for v in values:
            d = T.lk_micro_to_domain(v)
            if d in T.VALID_DOMAINS:
                out.append(d)
    return out


def _current_dasha_signature(ctx) -> List[Condition]:
    """Ground one MONEY/WORK/PEOPLE signal in the active life chapter (sub-period
    preferred, else major period)."""
    out = []
    for lord, intensity, src in ((ctx.get("dasha_ad"), 2.4, "dasha_ad"),
                                 (ctx.get("dasha_md"), 2.0, "dasha_md")):
        sig = T.DASHA_SIGNATURE.get((lord or "").strip().title())
        if sig:
            domain, text = sig
            out.append(Condition(domain=domain, text=text, intensity=intensity, source=src))
            break   # one chapter signal is enough; sub-period wins
    return out


def _detect_today(ctx) -> List[Condition]:
    conds: List[Condition] = []
    lk = ctx.get("lk_daily") or {}
    sig0 = ctx.get("signal0") or {}
    pan = ctx.get("panchanga") or {}
    prof = ctx.get("nakshatra_profile") or {}

    day_quality = (lk.get("day_quality_for_user") or "").strip().lower()
    amplified = _norm_lk_domains(lk.get("domains_amplified_today"))
    to_avoid = _norm_lk_domains(lk.get("domains_to_avoid_today"))

    # 1) OPENING / domain amplification (strongest signals on a good day)
    for d in amplified[:2]:
        text = T.AMPLIFIED_BY_DOMAIN.get(d) or T.AMPLIFIED_BY_DOMAIN["opportunity"]
        conds.append(Condition(domain=d, text=text, intensity=3.0, source="lk_amplified"))

    # 2) AVOID / domain caution
    for d in to_avoid[:2]:
        if d in T.AVOID_BY_DOMAIN:
            conds.append(Condition(domain="risk", text=T.AVOID_BY_DOMAIN[d],
                                    intensity=2.8, source="lk_avoid"))

    # 3) Active life-chapter (money/work/people grounding)
    conds += _current_dasha_signature(ctx)

    # 4) MIND from today's nakshatra energy
    energy = prof.get("energy") or ""
    if energy:
        conds.append(Condition(domain="mind", text=T.mind_from_energy(energy),
                               intensity=1.6, source="nakshatra_energy"))

    # 5) WORK/aligned action from nakshatra
    aligned = prof.get("aligned") or []
    if aligned:
        conds.append(Condition(domain="work", text=T.aligned_action(aligned[0]),
                               intensity=1.4, source="nakshatra_aligned"))

    # 6) BODY from chandra bala / energy
    chandra = sig0.get("chandra_bala") or ""
    conds.append(Condition(domain="body", text=T.body_from_chandra(chandra),
                           intensity=1.2, source="chandra_bala"))

    # 7) WATCH — friction day and/or active loose end
    if sig0.get("is_friction"):
        conds.append(Condition(domain="watch", text=T.watch_friction_day(),
                               intensity=2.2, source="is_friction"))
    if (lk.get("day_lord_status") or {}).get("rin_active"):
        conds.append(Condition(domain="watch", text=T.watch_debt_active(),
                               intensity=1.8, source="lk_rin"))

    # 8) TIMING — best window (abhijit / lucky hours) + avoid window (rahu kalam)
    best = pan.get("abhijit") or pan.get("abhijit_muhurta") or ""
    if not best:
        lucky = pan.get("lucky_hours")
        if isinstance(lucky, dict) and lucky:
            best = next(iter(lucky.values()))
        elif isinstance(lucky, list) and lucky:
            best = lucky[0]
    conds.append(Condition(domain="timing", text=T.best_window(best if isinstance(best, str) else ""),
                           intensity=2.6, source="best_window"))

    rahu = pan.get("rahu_kalam") or ""
    if rahu:
        conds.append(Condition(domain="timing", text=T.avoid_window(rahu),
                               intensity=2.1, source="avoid_window"))

    return conds


def _detect_tomorrow(ctx) -> List[Condition]:
    """Tomorrow == Today's machinery, more reserved: drop the lowest-intensity
    extras and soften 'today' to 'tomorrow' in the surfaced text."""
    conds = _detect_today(ctx)
    for c in conds:
        c.text = c.text.replace(" today", " tomorrow").replace("Today", "Tomorrow")
    return conds


def _detect_week(ctx) -> List[Condition]:
    """Week summary from the 7-day signal array.
    ctx["days"] = [{score, is_friction, weekday/day, iso_date, ...}, ...]
    """
    conds: List[Condition] = []
    days = ctx.get("days") or []
    rows = [d for d in days if isinstance(d, dict)]

    def _label(d):
        return (d.get("weekday") or d.get("day") or d.get("iso_date") or "").strip()

    if rows:
        # Peak day = highest score; watch day = friction flag or lowest score.
        scored = [(float(d.get("score", 0) or 0), d) for d in rows]
        peak = max(scored, key=lambda x: x[0])[1]
        conds.append(Condition(domain="timing", text=T.week_peak(_label(peak)),
                               intensity=3.0, source="week_peak"))

        watch = next((d for d in rows if d.get("is_friction")), None)
        if watch is None:
            watch = min(scored, key=lambda x: x[0])[1]
        if _label(watch) != _label(peak):
            conds.append(Condition(domain="watch", text=T.week_watch(_label(watch)),
                                   intensity=2.6, source="week_watch"))

        # Overall energy from mean score (scores are typically 0..10-ish).
        avg = sum(s for s, _ in scored) / max(1, len(scored))
        band = "high" if avg >= 6.5 else ("low" if avg <= 4.0 else "even")
        conds.append(Condition(domain="mind", text=T.WEEK_ENERGY[band],
                               intensity=1.8, source="week_energy"))

    # Active life-chapter steer.
    lord = ctx.get("dasha_ad") or ctx.get("dasha_md") or ""
    wc = T.week_chapter(lord)
    if wc:
        d, text = wc
        conds.append(Condition(domain=d, text=text, intensity=1.5, source="week_chapter"))
    return conds


def _detect_month(ctx) -> List[Condition]:
    """Month from energy_level + strong/weak planet lists + dasha chapter."""
    conds: List[Condition] = []
    energy = (ctx.get("energy_level") or "").strip().lower()
    if energy in T.MONTH_ENERGY:
        conds.append(Condition(domain="body" if energy in ("high", "low") else "mind",
                               text=T.MONTH_ENERGY[energy], intensity=2.2, source="month_energy"))

    seen_dom = set()
    for p in (ctx.get("strong_planets") or [])[:3]:
        d = T.planet_to_domain(p)
        if d in T.MONTH_STRONG_BY_DOMAIN and d not in seen_dom:
            seen_dom.add(d)
            conds.append(Condition(domain=d, text=T.MONTH_STRONG_BY_DOMAIN[d],
                                   intensity=2.8, source="month_strong"))
    for p in (ctx.get("weak_planets") or [])[:3]:
        d = T.planet_to_domain(p)
        if d in T.MONTH_WEAK_BY_DOMAIN:
            conds.append(Condition(domain="risk", text=T.MONTH_WEAK_BY_DOMAIN[d],
                                   intensity=2.5, source="month_weak"))

    lord = ctx.get("dasha_ad") or ctx.get("dasha_md") or ""
    sig = T.DASHA_SIGNATURE.get((lord or "").strip().title())
    if sig:
        d, text = sig
        text = text.replace(" today", " this month")
        conds.append(Condition(domain=d, text=text, intensity=1.6, source="month_chapter"))
    return conds


def _detect_year(ctx) -> List[Condition]:
    """Year from polarity + areas + current chapter + incoming dasha transition."""
    conds: List[Condition] = []
    pol = (ctx.get("polarity") or "").strip().lower()
    if pol in T.YEAR_POLARITY:
        dom = "opportunity" if pol == "positive" else ("risk" if pol == "negative" else "mind")
        conds.append(Condition(domain=dom, text=T.YEAR_POLARITY[pol],
                               intensity=2.4, source="year_polarity"))

    seen = set()
    for a in (ctx.get("areas") or [])[:4]:
        d = T.area_to_domain(a if isinstance(a, str) else (a.get("name") if isinstance(a, dict) else ""))
        if d in T.YEAR_AREA_BY_DOMAIN and d not in seen:
            seen.add(d)
            conds.append(Condition(domain=d, text=T.YEAR_AREA_BY_DOMAIN[d],
                                   intensity=2.7, source="year_area"))

    cc = T.year_chapter(ctx.get("dasha_md") or "")
    if cc:
        d, text = cc
        conds.append(Condition(domain=d, text=text, intensity=2.0, source="year_chapter"))

    if ctx.get("next_dasha_when") or ctx.get("next_dasha_lord"):
        conds.append(Condition(domain="timing", text=T.year_transition(ctx.get("next_dasha_when")),
                               intensity=2.1, source="year_transition"))
        nl = T.DASHA_SIGNATURE.get((ctx.get("next_dasha_lord") or "").strip().title())
        if nl:
            d, _t = nl
            conds.append(Condition(domain=d, text=T.YEAR_AREA_BY_DOMAIN.get(d, T.YEAR_AREA_BY_DOMAIN["work"]),
                                   intensity=1.4, source="year_incoming_domain"))
    return conds


def _detect_cycle(ctx) -> List[Condition]:
    """Cycle from current-phase + predicted events + next phase shift."""
    conds: List[Condition] = []
    phase = (ctx.get("phase") or "").strip().lower()
    if phase in T.CYCLE_PHASE:
        conds.append(Condition(domain="timing", text=T.CYCLE_PHASE[phase],
                               intensity=2.8, source="cycle_phase"))

    cc = T.cycle_chapter(ctx.get("dasha_md") or "")
    if cc:
        d, text = cc
        conds.append(Condition(domain=d, text=text, intensity=2.4, source="cycle_chapter"))

    for ev in (ctx.get("events") or [])[:4]:
        if not isinstance(ev, dict):
            continue
        dom = T.area_to_domain(ev.get("domain") or "")
        when = ev.get("window") or ev.get("predicted_window_start") or ev.get("when") or ""
        d, text = T.cycle_event(dom, str(when)[:10] if when else "")
        conds.append(Condition(domain=d, text=text, intensity=2.2, source="cycle_event"))

    if ctx.get("next_shift_when"):
        conds.append(Condition(domain="timing", text=T.cycle_next_shift(ctx.get("next_shift_when")),
                               intensity=1.8, source="cycle_next_shift"))
    return conds


def _dedupe_and_rank(conds: List[Condition], scope: str) -> List[Condition]:
    # Rank by intensity desc, stable.
    conds = [c for c in conds if c.domain in T.VALID_DOMAINS and (c.text or "").strip()]
    conds.sort(key=lambda c: c.intensity, reverse=True)

    # Light dedupe: avoid two identical texts; allow repeated domains (e.g. two
    # timing signals: best window + avoid window) since they carry distinct info.
    seen_text = set()
    deduped: List[Condition] = []
    for c in conds:
        key = c.text.strip().lower()
        if key in seen_text:
            continue
        seen_text.add(key)
        deduped.append(c)

    limit = T.SCOPE_LIMITS.get(scope, 6)
    return deduped[:limit]


def build_highlights(scope: str, language: str, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return [{domain, text, priority}, ...]. Never raises."""
    try:
        scope = (scope or "today").strip().lower()
        if scope == "today":
            conds = _detect_today(ctx)
        elif scope == "tomorrow":
            conds = _detect_tomorrow(ctx)
        elif scope == "week":
            conds = _detect_week(ctx)
        elif scope == "month":
            conds = _detect_month(ctx)
        elif scope == "year":
            conds = _detect_year(ctx)
        elif scope == "cycle":
            conds = _detect_cycle(ctx)
        else:
            return []

        conds = _dedupe_and_rank(conds, scope)

        # Respect the floor only when we genuinely have the data; if detection
        # produced fewer than the floor, return what's real rather than padding
        # with filler (anti-hallucination > hitting a count).
        out = []
        for i, c in enumerate(conds):
            out.append({"domain": c.domain, "text": c.text.strip(), "priority": i + 1})
        return out
    except Exception as e:  # pragma: no cover - defensive
        try:
            import logging
            logging.getLogger("highlight_composer").warning("build_highlights failed: %s", e)
        except Exception:
            pass
        return []
