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
    backed_by: List[str] = field(default_factory=list)  # which timing systems agreed
    confidence: str = ""      # high | medium | low (cycle scope only)
    # [hl-reconcile 2026-06-08] true-domain + valence enable the
    # contradiction-killer in _dedupe_and_rank. `domain` may be a
    # valence bucket (risk/opportunity) for legacy compatibility;
    # `true_domain` is the underlying life domain (work/money/...);
    # `valence` is positive/negative/neutral. Defaults preserve
    # behavior for any detector that hasn't been updated.
    true_domain: str = ""
    valence: str = "neutral"


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
        # [hl-reconcile] tag true_domain + positive valence
        conds.append(Condition(domain=d, text=text, intensity=3.0, source="lk_amplified",
                               true_domain=d, valence="positive"))

    # 2) AVOID / domain caution
    for d in to_avoid[:2]:
        if d in T.AVOID_BY_DOMAIN:
            # [hl-reconcile] keep true_domain=d so this dedupes against
            # the matching positive card on the same domain.
            conds.append(Condition(domain="risk", text=T.AVOID_BY_DOMAIN[d],
                                    intensity=2.8, source="lk_avoid",
                                    true_domain=d, valence="negative"))

    # 3) Active life-chapter (money/work/people grounding)
    conds += _current_dasha_signature(ctx)

    # 3b) Broaden domain coverage from the day-signal's own aligned/friction
    #     lines ("In career: …", "In finance: …") — same LK+transit+dasha
    #     synthesis Deep Read uses, so Today matches its breadth.
    _seen_amp = set()
    for line in (sig0.get("aligned_for") or [])[:3]:
        d = T.in_domain_from_prefix(line if isinstance(line, str) else "")
        if d in T.AMPLIFIED_BY_DOMAIN and d not in _seen_amp:
            _seen_amp.add(d)
            conds.append(Condition(domain=d, text=T.AMPLIFIED_BY_DOMAIN[d],
                                   intensity=2.7, source="aligned_for",
                                   true_domain=d, valence="positive"))
    for line in (sig0.get("friction_for") or [])[:2]:
        d = T.in_domain_from_prefix(line if isinstance(line, str) else "")
        if d in T.AVOID_BY_DOMAIN:
            conds.append(Condition(domain="risk", text=T.AVOID_BY_DOMAIN[d],
                                   intensity=2.5, source="friction_for",
                                   true_domain=d, valence="negative"))

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
    rahu = pan.get("rahu_kalam") or ""

    # [abhijit-overrides 2026-07-24] Route both ranges through the windows
    # resolver instead of rendering the raw panchanga values. This strip used to
    # print the untrimmed abhijit while windows[] printed a version trimmed to
    # clear rahu kalam — one payload, one day, two different "best window" start
    # times on screen. One resolver now owns the day's timing.
    if isinstance(best, str) or rahu:
        try:
            from antar_engine.today_windows import resolve_day_windows
            _rw = resolve_day_windows(best if isinstance(best, str) else "", rahu)
            if _rw.get("best"):
                best = _rw["best"]
            rahu = _rw.get("avoid", rahu)
        except Exception:
            pass   # fall back to the raw panchanga values

    conds.append(Condition(domain="timing", text=T.best_window(best if isinstance(best, str) else ""),
                           intensity=2.6, source="best_window"))

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


def _day_label(d):
    return (d.get("weekday") or d.get("day") or d.get("iso_date") or d.get("date") or "").strip()


def _day_friction(d):
    return bool(d.get("is_friction_day") if "is_friction_day" in d else d.get("is_friction"))


def _detect_week(ctx) -> List[Condition]:
    """Week SUMMARY (aggregate) from the 7-day signal array.
    ctx["days"] = [{score, is_friction_day, day, windows, observa_hoy_domain, ...}, ...]
    """
    conds: List[Condition] = []
    rows = [d for d in (ctx.get("days") or []) if isinstance(d, dict)]
    if rows:
        scored = [(float(d.get("score", 0) or 0), d) for d in rows]
        peak = max(scored, key=lambda x: x[0])[1]
        conds.append(Condition(domain="timing", text=T.week_peak(_day_label(peak)),
                               intensity=3.0, source="week_peak"))

        # Best concrete window on the peak day (its "connection"/"peak" window).
        win = None
        for w in (peak.get("windows") or []):
            if isinstance(w, dict) and w.get("type") in ("connection", "peak"):
                win = w
                break
        if win:
            conds.append(Condition(domain="timing",
                                   text=T.week_peak_window(_day_label(peak), win.get("start", ""), win.get("end", "")),
                                   intensity=2.5, source="week_peak_window"))

        friction_rows = [d for d in rows if _day_friction(d)]
        watch = friction_rows[0] if friction_rows else min(scored, key=lambda x: x[0])[1]
        if _day_label(watch) != _day_label(peak):
            conds.append(Condition(domain="watch", text=T.week_watch(_day_label(watch)),
                                   intensity=2.6, source="week_watch"))
        if len(friction_rows) >= 4:
            conds.append(Condition(domain="watch", text=T.week_load(len(friction_rows)),
                                   intensity=2.3, source="week_load"))

        # Recurring domain across the week (observa_hoy_domain tally).
        tally = {}
        for d in rows:
            dom = T.area_to_domain(d.get("observa_hoy_domain") or "")
            if dom in T.WEEK_THEME_BY_DOMAIN:
                tally[dom] = tally.get(dom, 0) + 1
        if tally:
            top_dom = max(tally, key=tally.get)
            if tally[top_dom] >= 2:
                conds.append(Condition(domain=top_dom, text=T.WEEK_THEME_BY_DOMAIN[top_dom],
                                       intensity=2.0, source="week_theme"))

        avg = sum(s for s, _ in scored) / max(1, len(scored))
        band = "high" if avg >= 6.0 else ("low" if avg <= 3.5 else "even")
        conds.append(Condition(domain="mind", text=T.WEEK_ENERGY[band],
                               intensity=1.7, source="week_energy"))

    lord = ctx.get("dasha_ad") or ctx.get("dasha_md") or ""
    wc = T.week_chapter(lord)
    if wc:
        d, text = wc
        conds.append(Condition(domain=d, text=text, intensity=1.4, source="week_chapter"))
    return conds


def _detect_weekday(day) -> List[Condition]:
    """Per-day tile signals (4-5, lighter than Today). Consumes ONE day dict
    from daily-week days[]. Neutral framing (no 'today') since each is a named day."""
    conds: List[Condition] = []
    if not isinstance(day, dict):
        return conds
    verdict = (day.get("verdict_label") or "").strip().lower()
    dom = T.area_to_domain(day.get("observa_hoy_domain") or "")

    if dom in T.VALID_DOMAINS:
        if verdict == "good":
            txt = T.AMPLIFIED_BY_DOMAIN.get(dom) or T.AMPLIFIED_BY_DOMAIN["opportunity"]
            conds.append(Condition(domain=dom, text=txt.replace(" today", ""), intensity=2.6, source="wd_amp"))
        elif verdict == "caution":
            txt = T.AVOID_BY_DOMAIN.get(dom) or T.AVOID_BY_DOMAIN["work"]
            conds.append(Condition(domain="risk", text=txt.replace(" today", ""), intensity=2.6, source="wd_avoid",
                                   true_domain=dom, valence="negative"))
        elif dom in T.WEEK_THEME_BY_DOMAIN:
            conds.append(Condition(domain=dom, text=T.WEEK_THEME_BY_DOMAIN[dom], intensity=2.2, source="wd_theme"))

    win = None
    for w in (day.get("windows") or []):
        if isinstance(w, dict) and w.get("type") in ("connection", "peak"):
            win = w
            break
    if win:
        rng = f"{win.get('start', '')}–{win.get('end', '')}".strip("–")
        conds.append(Condition(domain="timing", text=T.best_window(rng), intensity=2.4, source="wd_window"))

    sc = day.get("score")
    if isinstance(sc, (int, float)):
        band = "strong" if sc >= 6 else ("weak" if sc <= 3 else "")
        conds.append(Condition(domain="body", text=T.body_from_chandra(band).replace(" today", ""),
                               intensity=1.6, source="wd_body"))

    if _day_friction(day):
        conds.append(Condition(domain="watch",
                               text="Friction runs through this day — leave buffer time and don't force outcomes.",
                               intensity=2.0, source="wd_friction"))
    elif verdict == "good":
        conds.append(Condition(domain="opportunity",
                               text="A clear day — use it for the move you've been holding back.",
                               intensity=2.0, source="wd_good"))
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
                                   intensity=2.8, source="month_strong",
                                   true_domain=d, valence="positive"))
    for p in (ctx.get("weak_planets") or [])[:3]:
        d = T.planet_to_domain(p)
        if d in T.MONTH_WEAK_BY_DOMAIN:
            conds.append(Condition(domain="risk", text=T.MONTH_WEAK_BY_DOMAIN[d],
                                   intensity=2.5, source="month_weak",
                                   true_domain=d, valence="negative"))

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

    # 2-of-3 timing-system convergence (Vimshottari + Chara + Naisargika).
    # Highest-priority cycle signal — fires only when >= 2 systems agree.
    xc = ctx.get("cross_check") or {}
    if xc.get("agreed_planet") and xc.get("agreement_count", 0) >= 2:
        d, text = T.cycle_convergence(xc["agreed_planet"], xc["agreement_count"])
        conds.append(Condition(domain=d, text=text, intensity=3.2, source="cycle_convergence", backed_by=list(xc.get("agreeing_systems") or []), confidence=("high" if xc.get("agreement_count", 0) >= 3 else "medium")))

    # Sade Sati — a genuine 7.5-year pressure cycle (top multi-year marker).
    ss = (ctx.get("sade_sati") or "").strip()
    if ss and ss.lower() not in ("none", "inactive", "not active", "n/a"):
        conds.append(Condition(domain="watch", text=T.cycle_sade_sati(ss),
                               intensity=3.0, source="cycle_sade_sati", backed_by=["transit"], confidence="low"))

    phase = (ctx.get("phase") or "").strip().lower()
    if phase in T.CYCLE_PHASE:
        conds.append(Condition(domain="timing", text=T.CYCLE_PHASE[phase],
                               intensity=2.7, source="cycle_phase", backed_by=["vimshottari"], confidence="low"))

    cc = T.cycle_chapter(ctx.get("dasha_md") or "")
    if cc:
        d, text = cc
        conds.append(Condition(domain=d, text=text, intensity=2.4, source="cycle_chapter", backed_by=["vimshottari"], confidence="low"))

    nxt = ctx.get("next_shift_when") or ctx.get("md_end_date") or ""
    if nxt:
        conds.append(Condition(domain="timing", text=T.cycle_next_shift(str(nxt)[:10]),
                               intensity=2.6, source="cycle_next_shift", backed_by=["vimshottari"], confidence="low"))

    for ev in (ctx.get("events") or [])[:3]:
        if not isinstance(ev, dict):
            continue
        dom = T.area_to_domain(ev.get("domain") or "")
        when = ev.get("window") or ev.get("predicted_window_start") or ev.get("when") or ""
        d, text = T.cycle_event(dom, str(when)[:10] if when else "")
        conds.append(Condition(domain=d, text=text, intensity=2.2, source="cycle_event", backed_by=["vimshottari"], confidence="low"))

    if (ctx.get("stuckness_count") or 0) >= 1:
        conds.append(Condition(domain="watch", text=T.cycle_stuckness(ctx.get("stuckness_count")),
                               intensity=1.9, source="cycle_stuckness", backed_by=["diagnostic"], confidence="low"))
    if (ctx.get("lean_count") or 0) >= 1:
        conds.append(Condition(domain="opportunity", text=T.cycle_lean(ctx.get("lean_count")),
                               intensity=1.7, source="cycle_lean", backed_by=["diagnostic"], confidence="low"))
    return conds


def _detect_deepread(ctx) -> List[Condition]:
    """Deep Read: migrate the FOUNDATION/RELATIONSHIPS/EXPANSION/INNER prose
    themes into one concise signal each, plus WHEN/hora windows.
    ctx["themes"] = [{key, tone, ...}, ...]   (deep_read.py theme objects)
    ctx["panchanga"] = {abhijit, rahu_kalam, lucky_hours}
    """
    conds: List[Condition] = []
    for t in (ctx.get("themes") or []):
        if not isinstance(t, dict):
            continue
        sig = T.theme_signal(t.get("key"), t.get("tone"))
        if not sig or not sig[1]:
            continue
        domain, text = sig
        inten = 2.6 if domain == "risk" else 2.4
        conds.append(Condition(domain=domain, text=text, intensity=inten, source="deep_theme"))

    # WHEN / hora — best window + window to avoid.
    pan = ctx.get("panchanga") or {}
    best = pan.get("abhijit") or pan.get("abhijit_muhurta") or ""
    if not best:
        lucky = pan.get("lucky_hours")
        if isinstance(lucky, dict) and lucky:
            best = next(iter(lucky.values()))
        elif isinstance(lucky, list) and lucky:
            best = lucky[0]
    conds.append(Condition(domain="timing", text=T.best_window(best if isinstance(best, str) else ""),
                           intensity=2.7, source="deep_best_window"))
    rahu = pan.get("rahu_kalam") or ""
    if rahu:
        conds.append(Condition(domain="timing", text=T.avoid_window(rahu),
                               intensity=2.2, source="deep_avoid_window"))

    # Active life-chapter steer (low priority backstop so we never look thin).
    lord = ctx.get("dasha_ad") or ctx.get("dasha_md") or ""
    sig = T.DASHA_SIGNATURE.get((lord or "").strip().title())
    if sig:
        d, text = sig
        conds.append(Condition(domain=d, text=text, intensity=1.3, source="deep_chapter"))
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

    # [hl-reconcile 2026-06-08 group] One card per true_domain.
    # Previously the dedupe operated only on text, so the same true
    # domain (e.g. 'work') could ship as one positive card AND one
    # 'risk' card with opposite advice. We now group by true_domain
    # and keep the highest-intensity condition in each group.
    # Detectors that left true_domain blank fall back to `domain`
    # so legacy items (pure timing/chapter) keep their behavior.
    # `timing` and `watch` groups are NOT collapsed — multiple
    # timing/watch signals carry distinct info (best vs avoid window,
    # different watch areas).
    _NON_COLLAPSING = {"timing", "watch"}
    grouped: List[Condition] = []
    seen_group_key = set()
    for c in deduped:
        gk = (c.true_domain or c.domain or "").strip().lower()
        if not gk or gk in _NON_COLLAPSING:
            grouped.append(c)
            continue
        if gk in seen_group_key:
            # Already kept a higher-intensity card for this domain;
            # drop the contradictory / weaker one.
            continue
        seen_group_key.add(gk)
        # Surface the true_domain as the card's domain so the frontend
        # palette reflects the underlying life area, not the valence
        # bucket. Keep 'opportunity'/'risk' only when true_domain was
        # left blank (purely valenced signal, no underlying domain).
        if c.true_domain and c.true_domain in T.VALID_DOMAINS:
            c.domain = c.true_domain
        grouped.append(c)

    limit = T.SCOPE_LIMITS.get(scope, 6)
    return grouped[:limit]


# [highlight-reconcile 2026-07-19] Highlights and the body of the reading are
# built by two engines that never spoke to each other. Highlights come from the
# dasha lord plus the strong/weak planet lists; the overview and the actions come
# from the transit house tally. On a real reading that produced, side by side:
#
#     HIGHLIGHT: "Money runs tight this month — defer big purchases"
#     ACTION:    "Push for that payout or raise before June 30"
#
# Both are defensible in isolation — a weak Venus and a live 11th house are not
# the same claim — but printed together they read as the engine contradicting
# itself, which costs more trust than either line earns.
#
# The transit tally is the more specific signal (it names houses and drives the
# actions the user actually follows), so where the two disagree the generic
# canned highlight is the one that goes. We DROP rather than rewrite: silence
# beats a sentence no evidence supports, consistent with the anti-hallucination
# rule below.
#
# Only confident domain pairs are mapped. 'mind' and 'opportunity' have no clean
# transit counterpart, so they are never dropped — a wrong mapping would suppress
# a true highlight, which is the worse error.
_HL_DOMAIN_TO_TRANSIT = {
    "money":         "wealth",
    "work":          "career",
    "body":          "health",
    "relationships": "relationships",
}

# Same threshold the monthly ACTIVATE/AVOID split uses, so a domain cannot be
# labelled "lean in" there and contradicted here (or vice versa).
_TONE_CONTRADICTION = 0.5


def _reconcile_with_transits(conds: List[Condition], ctx: Dict[str, Any]) -> List[Condition]:
    """Drop highlights whose valence contradicts the transit tone for the same
    domain. Fail-open: no tally, unmapped domain, or no valence -> keep."""
    tally = ctx.get("domain_tone")
    if not isinstance(tally, dict) or not tally:
        return conds
    kept: List[Condition] = []
    for c in conds:
        dom = getattr(c, "true_domain", None) or c.domain
        val = (getattr(c, "valence", "") or "").strip().lower()
        t_dom = _HL_DOMAIN_TO_TRANSIT.get(dom)
        if not t_dom or val not in ("positive", "negative"):
            kept.append(c)
            continue
        try:
            tone = float((tally.get(t_dom) or {}).get("tone") or 0.0)
        except (TypeError, ValueError):
            kept.append(c)
            continue
        contradicted = (
            (val == "positive" and tone <= -_TONE_CONTRADICTION) or
            (val == "negative" and tone >= _TONE_CONTRADICTION)
        )
        if not contradicted:
            kept.append(c)
    return kept


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
        elif scope == "weekday":
            conds = _detect_weekday(ctx)
        elif scope == "month":
            conds = _detect_month(ctx)
        elif scope == "year":
            conds = _detect_year(ctx)
        elif scope == "cycle":
            conds = _detect_cycle(ctx)
        elif scope in ("deep", "deepread", "day-deep"):
            conds = _detect_deepread(ctx)
        else:
            return []

        conds = _dedupe_and_rank(conds, scope)
        conds = _reconcile_with_transits(conds, ctx)

        # Respect the floor only when we genuinely have the data; if detection
        # produced fewer than the floor, return what's real rather than padding
        # with filler (anti-hallucination > hitting a count).
        out = []
        for i, c in enumerate(conds):
            item = {"domain": c.domain, "text": c.text.strip(), "priority": i + 1}
            if c.backed_by:
                item["backed_by"] = list(c.backed_by)
            if c.confidence:
                item["confidence"] = c.confidence
            out.append(item)
        return out
    except Exception as e:  # pragma: no cover - defensive
        try:
            import logging
            logging.getLogger("highlight_composer").warning("build_highlights failed: %s", e)
        except Exception:
            pass
        return []
