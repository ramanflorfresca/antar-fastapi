"""
antar_engine/places_concern.py
─────────────────────────────────────────────────────────────────────────────
PLACES — concern routing + city scoring.  Phase 1.

Given a chart and a concern, score cities by how strongly their location lights
up the concern's karaka lines and relocated houses, conditioned by each
planet's natal dignity.  Produces 0-100 scores, FLOW / MIXED / STRAIN tiers,
and the structured signals the template composer turns into prose.

NO verdicts.  NO house numbers leak here — houses are reduced to scores and to
domain-named signals; the composer never prints a number.
"""

from __future__ import annotations

from typing import Optional

from antar_engine.places_lines import (
    compute_all_lines, distance_city_to_line, PLANETS,
)
from antar_engine.places_conditions import compute_all_conditions

# ─────────────────────────────────────────────────────────────────────────────
# Concern routing  (LOCKED by contract)
# ─────────────────────────────────────────────────────────────────────────────

CONCERN_MAP: dict[str, dict] = {
    # [places-domain-screen] `houses` = supportive set (ranked on); `neg_houses`
    # = the dusthana set screened OUT for this domain. 6 is upachaya (positive)
    # for career/health; 12 is positive for peace — so the negative set is
    # domain-specific, not a fixed 6/8/12.
    "money":  {"karakas": ["Jupiter", "Venus", "Mercury"], "angles": ["MC", "AC"], "houses": [2, 11, 5, 9], "neg_houses": [6, 8, 12], "weights": {"karakas": 0.40, "angles": 0.35, "houses": 0.25}},
    "career": {"karakas": ["Sun", "Saturn", "Mercury"],    "angles": ["MC", "AC"], "houses": [10, 6, 1],    "neg_houses": [8, 12],    "weights": {"karakas": 0.45, "angles": 0.35, "houses": 0.20}},
    "love":   {"karakas": ["Venus", "Mars", "Moon"],       "angles": ["AC", "DC"], "houses": [7, 5, 11],    "neg_houses": [6, 8, 12], "weights": {"karakas": 0.40, "angles": 0.40, "houses": 0.20}},
    "health": {"karakas": ["Sun", "Mars", "Saturn"],       "angles": ["AC"],       "houses": [1, 6],        "neg_houses": [8, 12],    "weights": {"karakas": 0.45, "angles": 0.30, "houses": 0.25}},
    "peace":  {"karakas": ["Moon", "Jupiter", "Ketu"],     "angles": ["IC"],       "houses": [4, 12],       "neg_houses": [6, 8],     "weights": {"karakas": 0.50, "angles": 0.30, "houses": 0.20}},
    "family": {"karakas": ["Moon", "Sun", "Jupiter"],      "angles": ["IC", "AC"], "houses": [4, 9, 7],     "neg_houses": [6, 8, 12], "weights": {"karakas": 0.45, "angles": 0.30, "houses": 0.25}},
    # [places-business 2026-07-18] startup / venture — deliberately NOT the same
    # as "career" (employment + status). Trade and partnership (7) lead, with
    # profession (10), gains/network (11) and self-started enterprise (3).
    # Mercury = commerce, Mars = initiative, Jupiter = expansion. 6 is left OUT
    # of neg_houses on purpose: it is upachaya and reads as out-competing rivals.
    "business": {"karakas": ["Mercury", "Mars", "Jupiter"], "angles": ["MC", "AC"], "houses": [7, 10, 11, 3], "neg_houses": [8, 12], "weights": {"karakas": 0.40, "angles": 0.35, "houses": 0.25}},
}

# Legacy aliases accepted for one release, then drop. resolve_concern() maps
# these to the canonical key and logs a deprecation warning.
CONCERN_ALIASES = {"wealth": "money", "rest": "peace"}


def resolve_concern(concern):
    """Map a legacy alias to its canonical concern key (logging deprecation)."""
    if not concern:
        return concern
    canon = CONCERN_ALIASES.get(concern)
    if canon:
        import logging
        logging.getLogger(__name__).warning(
            f"[places] deprecated concern alias {concern!r} -> {canon!r}; update the client"
        )
        return canon
    return concern


VALID_CONCERNS = list(CONCERN_MAP.keys())

MALEFICS = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}

# Karaka rank weights (1st karaka matters most).
_KARAKA_RANK_W = [1.0, 0.75, 0.55]
# [places-calibration 2026-07-12] Light rank taper for the best-line karaka
# score — the primary karaka on a line counts full; secondary/tertiary lines
# still count strongly (a real karaka line is a real signal regardless of rank).
_KARAKA_RANK_TAPER = [1.0, 0.9, 0.8]

# Proximity bands (km).
_STRONG_KM = 300.0
_MODERATE_KM = 700.0

# Tier thresholds on the 0-100 score.
# [places-calibration 2026-07-12] FLOW lowered 60 -> 55. The old 60 was set for
# the pre-calibration score range that maxed near 57 (so FLOW was unreachable);
# with the corrected range a cluster of genuinely-strong, on-a-good-line cities
# lands at 55-59 and should read as "clearly good", not "trade-offs". Validated
# across 4 charts: FLOW stays ~1% of cities (off-line cities score <35, nowhere
# near 55), so this surfaces real strengths without inflating weak charts.
_TIER_FLOW = 55
_TIER_STRAIN = 35

# [places-domain-screen] weight of the negative-house screen subtracted
# from the combined 0-1 score before scaling to 0-100.
_NEG_SCREEN_W = 0.35

# Result de-clustering (Fix B). Astrocartography lines are meridians/curves, so
# a naive top-N concentrates on whichever line threads the densest city region.
# Cap how many returned cities may share the same dominant line (planet+angle)
# or the same country, so the next-best lines surface. Caps are relaxed only if
# they would leave fewer than the requested count.
_MAX_PER_LINE = 2
_MAX_PER_COUNTRY = 2

# [places relevance gate 2026-06-21] Population floor so microstate capitals
# (Suva 77k, Funafuti 6k) can't top a ranking purely on a line crossing.
# Tunable; surfaced in the rank trace; relaxed automatically when too few
# cities qualify (e.g. a thin region_filter). Filters the pool only — it
# never changes how a city scores.
POPULATION_FLOOR = 500_000


def _karaka_score_from_norms(norm: dict, karakas: list) -> float:
    """[places-calibration 2026-07-12] Concern-karaka line support in [0,1].

    `norm` maps each karaka PRESENT near a line to its condition-weighted
    strength normalised to [0,1] (strength / max-condition 1.5). The strongest
    present karaka (rank-tapered) carries the score; extra karaka lines add a
    modest bonus. A single strong PRIMARY karaka line therefore reaches ~1.0 —
    the old all-three normaliser capped it near 0.44 and put FLOW out of reach."""
    best = 0.0
    for i, planet in enumerate(karakas):
        taper = _KARAKA_RANK_TAPER[i] if i < len(_KARAKA_RANK_TAPER) else 0.7
        best = max(best, taper * norm.get(planet, 0.0))
    extra = sum(sorted(norm.values(), reverse=True)[1:])  # non-dominant lines
    return min(1.0, best + 0.20 * extra)


def _angle_score_from_prox(best_prox_per_angle: dict) -> float:
    """[places-calibration 2026-07-12] Best relevant angle in [0,1], with a light
    bonus for covering more than one angle. Replaces the average, which halved a
    single strong angle line."""
    ap = list(best_prox_per_angle.values())
    if not ap:
        return 0.0
    return min(1.0, max(ap) + 0.15 * sum(sorted(ap, reverse=True)[1:]))


def _proximity(distance_km: float) -> float:
    """Graded proximity so distance variance reaches the score.

    1.0 on the line, falling continuously: strong band (<300km) tapers
    1.0 -> 0.70, moderate band (300-700km) tapers 0.70 -> 0.0, 0 beyond.
    (Previously a flat step returning 1.0 for every distance under 300km,
    which collapsed all near-line cities to one score.)"""
    if distance_km <= 0.0:
        return 1.0
    if distance_km < _STRONG_KM:
        return 1.0 - 0.30 * (distance_km / _STRONG_KM)
    if distance_km <= _MODERATE_KM:
        return 0.70 * (_MODERATE_KM - distance_km) / (_MODERATE_KM - _STRONG_KM)
    return 0.0


def _band(distance_km: float) -> str:
    if distance_km < _STRONG_KM:
        return "strong"
    if distance_km <= _MODERATE_KM:
        return "moderate"
    return "ignored"


def filter_concern_lines(all_lines: list[dict], concern: str) -> list[dict]:
    """Subset of the 36 lines relevant to a concern (karaka planet x angle)."""
    cfg = CONCERN_MAP[concern]
    karakas, angles = set(cfg["karakas"]), set(cfg["angles"])
    return [
        ln for ln in all_lines
        if ln["planet"] in karakas and ln["angle"] in angles
    ]


def find_lines_near_city(
    all_lines: list[dict],
    lat: float,
    lon: float,
    max_distance_km: float = 700.0,
) -> list[dict]:
    """Every line (any planet/angle) passing within max_distance_km of a city."""
    hits = []
    for ln in all_lines:
        d = distance_city_to_line(lat, lon, ln["polyline"])
        if d <= max_distance_km:
            hits.append({
                "planet": ln["planet"],
                "angle": ln["angle"],
                "distance_km": round(d, 1),
                "band": _band(d),
            })
    hits.sort(key=lambda h: h["distance_km"])
    return hits


# ─────────────────────────────────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────────────────────────────────

def score_city_for_concern(
    chart: dict,
    city: dict,
    concern: str,
    *,
    all_lines: Optional[list[dict]] = None,
    conditions: Optional[dict] = None,
    relocation: Optional[dict] = None,
) -> dict:
    """
    Score one city for one concern.

    Returns a dict with public fields (score, tier, city) plus underscore-
    prefixed internal signal fields consumed by the composer and stripped
    before the response is emitted:
        _signals  — ranked karaka-line hits (planet, angle, distance, condition,
                    polarity, strength)
        _watch    — friction signals (debilitated/combust karaka on an angle;
                    malefic in a relocated hidden-cost / friction house)
        _relocation — relocated chart summary
    """
    if concern not in CONCERN_MAP:
        raise ValueError(f"unknown concern {concern!r}")

    cfg = CONCERN_MAP[concern]
    karakas = cfg["karakas"]
    angles = set(cfg["angles"])
    concern_houses = set(cfg["houses"])
    neg_houses = set(cfg.get("neg_houses", []))  # [places-domain-screen]
    w = cfg["weights"]

    if all_lines is None:
        all_lines = compute_all_lines(chart.get("birth_jd"), chart)
    if conditions is None:
        conditions = compute_all_conditions(chart)

    lat = float(city["lat"])
    lon = float(city["lon"])

    # ── 1-2. Karaka line proximity, condition-weighted ──────────────────────
    # Best line strength per karaka, plus per-angle best proximity.
    best_per_karaka: dict[str, dict] = {}
    best_prox_per_angle: dict[str, float] = {a: 0.0 for a in angles}
    signals: list[dict] = []

    for ln in all_lines:
        planet, angle = ln["planet"], ln["angle"]
        if planet not in karakas or angle not in angles:
            continue
        d = distance_city_to_line(lat, lon, ln["polyline"])
        prox = _proximity(d)
        if prox <= 0.0:
            continue
        cond = conditions.get(planet, {})
        cond_w = cond.get("weight", 0.9)
        polarity = cond.get("polarity", "mixed")
        strength = prox * cond_w
        sig = {
            "planet": planet, "angle": angle,
            "distance_km": round(d, 1), "band": _band(d),
            "condition": cond.get("condition", "neutral"),
            "polarity": polarity, "strength": round(strength, 3),
        }
        signals.append(sig)
        if planet not in best_per_karaka or strength > best_per_karaka[planet]["strength"]:
            best_per_karaka[planet] = sig
        if prox > best_prox_per_angle.get(angle, 0.0):
            best_prox_per_angle[angle] = prox

    # karaka_score — [places-calibration 2026-07-12] REWARD THE BEST LINE, don't
    # demand all three karakas converge. The old normaliser divided by the sum of
    # ALL karaka rank-weights x max condition, so a single strong line (the common
    # geographic reality) could never exceed ~0.44 even when exalted — which alone
    # capped FLOW out of reach for every chart. Now: the strongest present karaka
    # line (rank-tapered, normalised by max condition 1.5) carries the score, and
    # additional karaka lines add a modest bonus toward 1.0.
    norm = {p: min(1.0, best_per_karaka[p]["strength"] / 1.5) for p in best_per_karaka}
    karaka_score = _karaka_score_from_norms(norm, karakas)

    # angle_score — [places-calibration 2026-07-12] the BEST relevant angle, not
    # the average. Being strongly on one concern angle (e.g. the career MC line)
    # is a full angle signal; averaging across [MC, AC] halved it when only one
    # angle carried a line. A light bonus keeps two-angle coverage slightly ahead.
    angle_score = _angle_score_from_prox(best_prox_per_angle)

    # ── 3-4. Relocated house score ──────────────────────────────────────────
    if relocation is None:
        from antar_engine.places_relocation import compute_relocated_chart
        relocation = compute_relocated_chart(chart, lat, lon)

    reloc_idx = relocation.get("relocated_lagna_index")
    house_num = 0.0
    house_den = 0.0
    house_hits: list[dict] = []
    if reloc_idx is not None:
        for planet in PLANETS:
            rec = chart.get("planets", {}).get(planet)
            if not rec:
                continue
            psi = rec.get("sign_index")
            if psi is None and rec.get("longitude") is not None:
                psi = int((float(rec["longitude"]) % 360.0) // 30.0)
            if psi is None:
                continue
            reloc_house = ((int(psi) - int(reloc_idx)) % 12) + 1
            if reloc_house in concern_houses:
                cond = conditions.get(planet, {})
                cond_w = cond.get("weight", 0.9)
                is_karaka = planet in karakas
                weight = cond_w * (1.5 if is_karaka else 1.0)
                house_num += weight
                house_den += 1.5 * (1.5 if is_karaka else 1.0)
                house_hits.append({
                    "planet": planet, "house": reloc_house,
                    "condition": cond.get("condition", "neutral"),
                    "polarity": cond.get("polarity", "mixed"),
                    "is_karaka": is_karaka,
                })
    house_score = (house_num / house_den) if house_den else 0.0

    # ── 4b. Negative-house screen (dusthana dominance) ──────────────────────
    # [places-domain-screen] Count concern-relevant planets relocating into
    # the domain's malefic houses. A malefic there weighs more than a benefic.
    # When this negative pressure dominates the positive house support, the
    # place is SCREENED and can never rank FLOW for this domain.
    neg_num = 0.0
    neg_den = 0.0
    neg_hits: list[dict] = []
    if reloc_idx is not None and neg_houses:
        for planet in PLANETS:
            rec = chart.get("planets", {}).get(planet)
            if not rec:
                continue
            psi = rec.get("sign_index")
            if psi is None and rec.get("longitude") is not None:
                psi = int((float(rec["longitude"]) % 360.0) // 30.0)
            if psi is None:
                continue
            reloc_house = ((int(psi) - int(reloc_idx)) % 12) + 1
            if reloc_house in neg_houses:
                cond = conditions.get(planet, {})
                cond_w = cond.get("weight", 0.9)
                mw = 1.5 if planet in MALEFICS else 0.8
                neg_num += cond_w * mw
                neg_den += 1.5 * 1.5
                neg_hits.append({"planet": planet, "house": reloc_house,
                                 "is_malefic": planet in MALEFICS})
    neg_score = (neg_num / neg_den) if neg_den else 0.0
    screened = bool(neg_score >= 0.20 and neg_score > house_score)

    # ── 5. Weight-combine ───────────────────────────────────────────────────
    combined = (
        w["karakas"] * karaka_score
        + w["angles"] * angle_score
        + w["houses"] * house_score
        - _NEG_SCREEN_W * neg_score  # [places-domain-screen]
    )
    # Health favours slow-pace places (recovery / rest): LOW velocity lifts the
    # score, HIGH dampens it, MEDIUM is neutral. Concern-specific; others unchanged.
    if concern == "health":
        _vel = str(city.get("velocity") or "").upper()
        if _vel == "LOW":
            combined += 0.08
        elif _vel == "HIGH":
            combined -= 0.08
    score = int(round(max(0.0, min(1.0, combined)) * 100))
    # [places-domain-screen] hard screen-out: a dusthana-dominated place can
    # never rank as FLOW for this domain.
    if screened:
        score = min(score, _TIER_STRAIN - 1)

    # tier
    if score >= _TIER_FLOW:
        tier = "FLOW"
    elif score >= _TIER_STRAIN:
        tier = "MIXED"
    else:
        tier = "STRAIN"

    # ── 6. Watch-outs ───────────────────────────────────────────────────────
    watch: list[dict] = []
    for sig in signals:
        if sig["polarity"] == "friction" and sig["band"] in ("strong", "moderate"):
            watch.append({
                "kind": "friction_line",
                "planet": sig["planet"], "angle": sig["angle"],
                "condition": sig["condition"], "distance_km": sig["distance_km"],
            })
    for hit in house_hits:
        if hit["house"] in (8, 12) and hit["planet"] in MALEFICS:
            watch.append({
                "kind": "hidden_cost_house",
                "planet": hit["planet"], "house": hit["house"],
                "condition": hit["condition"],
            })

    signals.sort(key=lambda s: -s["strength"])

    return {
        "city": {
            "name": city.get("name"),
            "country": city.get("country"),
            "country_code": city.get("country_code"),
            "lat": lat, "lon": lon,
            "timezone": city.get("timezone"),
            "velocity": city.get("velocity"),
        },
        "score": score,
        "tier": tier,
        "_signals": signals,
        "_house_hits": house_hits,
        "_watch": watch,
        "_relocation": relocation,
        "_subscores": {
            "karaka": round(karaka_score, 3),
            "angle": round(angle_score, 3),
            "house": round(house_score, 3),
            "neg": round(neg_score, 3),
        },
        "screened": screened,
        "_neg_hits": neg_hits,
    }


def _dominant_line(s: dict):
    """The (planet, angle) of a scored city's strongest karaka-line hit, or None
    when the city lies off every concern line (signals empty)."""
    sig = s.get("_signals") or []
    return (sig[0]["planet"], sig[0]["angle"]) if sig else None


def _select_diverse(scored: list[dict], n: int) -> list[dict]:
    """Pick n cities from a score-sorted list, capping cities per dominant line
    and per country so one meridian can't fill every slot. Falls back to raw
    score order to complete the count if the caps are too tight. The returned
    set is re-sorted into score order for display."""
    picked: list[dict] = []
    deferred: list[dict] = []
    line_ct: dict = {}
    country_ct: dict = {}
    for s in scored:
        dl = _dominant_line(s)
        city = s.get("city", {}) or {}
        cc = city.get("country_code") or city.get("country")
        line_full = dl is not None and line_ct.get(dl, 0) >= _MAX_PER_LINE
        country_full = cc is not None and country_ct.get(cc, 0) >= _MAX_PER_COUNTRY
        if line_full or country_full:
            deferred.append(s)
            continue
        picked.append(s)
        if dl is not None:
            line_ct[dl] = line_ct.get(dl, 0) + 1
        if cc is not None:
            country_ct[cc] = country_ct.get(cc, 0) + 1
        if len(picked) >= n:
            break
    if len(picked) < n:
        for s in deferred:  # relax caps, still highest-score-first
            picked.append(s)
            if len(picked) >= n:
                break
    picked.sort(key=lambda s: (-s["score"], -(s["_signals"][0]["strength"] if s["_signals"] else 0)))
    return picked[:n]


def _apply_population_floor(pool: list, floor: int, min_keep: int):
    """Keep cities with population >= floor. If fewer than min_keep qualify,
    relax to the largest-by-population min_keep cities (still drops the
    microstates when bigger options exist) rather than returning a thin or
    empty list. Returns (filtered_pool, effective_floor, relaxed_bool)."""
    qualifying = [c for c in pool if (c.get("population") or 0) >= floor]
    if len(qualifying) >= min_keep:
        return qualifying, floor, False
    by_pop = sorted(pool, key=lambda c: -(c.get("population") or 0))
    relaxed = by_pop[: max(min_keep, len(qualifying))]
    eff_floor = (relaxed[-1].get("population") or 0) if relaxed else floor
    return relaxed, eff_floor, True


def rank_cities_for_concern(
    chart: dict,
    concern: str,
    cities: list[dict],
    region_filter: Optional[str] = None,
    top_n: int = 8,
    trace: Optional[dict] = None,
) -> list[dict]:
    """
    Score every city for a concern and return the top N (default 8, contract
    asks for 5-8).  region_filter matches the coarse region_group OR the fine
    region OR the country_code (case-insensitive).
    """
    all_lines = compute_all_lines(chart.get("birth_jd"), chart)
    conditions = compute_all_conditions(chart)

    pool = cities
    if region_filter:
        rf = region_filter.strip().lower()
        pool = [
            c for c in cities
            if rf in (
                str(c.get("region_group", "")).lower(),
                str(c.get("region", "")).lower(),
                str(c.get("country_code", "")).lower(),
                str(c.get("country", "")).lower(),
            )
        ]

    # [places relevance gate] drop cities below the population floor so a
    # line crossing over a microstate capital can't outrank real metros.
    _need = max(5, min(top_n, 8))
    _n_before = len(pool)
    pool, _applied_floor, _relaxed = _apply_population_floor(pool, POPULATION_FLOOR, _need)
    if trace is not None:
        trace["population_floor"] = POPULATION_FLOOR
        trace["applied_floor"] = _applied_floor
        trace["relaxed"] = _relaxed
        trace["n_pool_before_floor"] = _n_before
        trace["n_pool_after_floor"] = len(pool)

    scored = [
        score_city_for_concern(
            chart, c, concern,
            all_lines=all_lines, conditions=conditions,
        )
        for c in pool
    ]
    # Highest score first; break ties by stronger top signal then population.
    # [places-domain-screen] screened (dusthana-dominated) cities always
    # rank below clean ones, then by score, then by strongest signal.
    scored.sort(key=lambda s: (s.get("screened", False), -s["score"], -(s["_signals"][0]["strength"] if s["_signals"] else 0)))
    # De-cluster so one planetary line / country can't fill every slot (Fix B).
    return _select_diverse(scored, max(5, min(top_n, 8)))


_CHAPTER_NAME = {
    "en": {"foundation": "foundation", "ascending": "ascending",
           "consolidation": "consolidation", "culmination": "culmination", "wisdom": "wisdom"},
    "es": {"foundation": "cimientos", "ascending": "ascenso",
           "consolidation": "consolidación", "culmination": "culminación", "wisdom": "sabiduría"},
}


def compose_city_reasons(
    chart: dict,
    city: dict,
    concern: Optional[str],
    dasha_ctx: Optional[dict],
    age: Optional[int],
    *,
    scored: dict,
    relocation: dict,
    conditions: dict,
    language: str = "en",
) -> list[dict]:
    """
    Build the ordered 4-layer reasoning array for a city:
        [{"layer": "NATAL"|"DASHA"|"AGE"|"INTENT", "text": ...}]
    Layers with nothing salient are skipped (2-4 entries typical). When there
    is no concern the INTENT layer is omitted.
    """
    from antar_engine.places_composer import _lang, _domain, _planet, compose_primary_reason
    from antar_engine.places_templates import (
        _NATAL_FRAMES, _DASHA_FRAMES, _AGE_FRAMES, _PLACED_CLAUSE,
    )
    from antar_engine.places_intel import life_stage_for_age, velocity_match

    lang = _lang(language)
    reasons: list[dict] = []
    signals = scored.get("_signals", [])
    reloc_idx = relocation.get("relocated_lagna_index")
    has_concern = bool(concern and concern in CONCERN_MAP)
    domain = _domain(concern, lang) if has_concern else (
        "your life overall" if lang == "en" else "tu vida en general")

    def _reloc_house(planet: str) -> Optional[int]:
        rec = chart.get("planets", {}).get(planet)
        if not rec or reloc_idx is None:
            return None
        psi = rec.get("sign_index")
        if psi is None and rec.get("longitude") is not None:
            psi = int((float(rec["longitude"]) % 360.0) // 30.0)
        if psi is None:
            return None
        return ((int(psi) - int(reloc_idx)) % 12) + 1

    # ── NATAL ───────────────────────────────────────────────────────────────
    # Strongest karaka for the concern, or strongest planet overall (no concern).
    if has_concern:
        pool = [(k, conditions.get(k, {})) for k in CONCERN_MAP[concern]["karakas"] if k in conditions]
        concern_houses = set(CONCERN_MAP[concern]["houses"])
    else:
        pool = list(conditions.items())
        concern_houses = set()
    if pool:
        kp, meta = max(pool, key=lambda kc: kc[1].get("weight", 0.9))
        cond = meta.get("condition", "neutral")
        placed = _PLACED_CLAUSE[lang] if (_reloc_house(kp) in concern_houses) else ""
        frame = _NATAL_FRAMES[lang].get(cond)
        if frame:
            reasons.append({"layer": "NATAL", "text": frame.format(
                planet=_planet(kp, lang), domain=domain, placed=placed)})

    # ── DASHA ───────────────────────────────────────────────────────────────
    if dasha_ctx:
        within = dasha_ctx.get("within_12mo_transition")
        target = dasha_ctx.get("next_md_lord") if within else dasha_ctx.get("md_lord")
        if target:
            strong_planets = {s["planet"] for s in signals if s.get("band") in ("strong", "moderate")}
            houses_for_activation = (concern_houses | {1, 10}) if has_concern else {1, 10}
            activated = (target in strong_planets) or (_reloc_house(target) in houses_for_activation)
            kind = None
            if within and activated:
                kind = "upcoming"
            elif within and not activated:
                kind = "building"
            elif (not within) and activated:
                kind = "current"
            if kind:
                reasons.append({"layer": "DASHA", "text": _DASHA_FRAMES[lang][kind].format(
                    planet=_planet(target, lang))})

    # ── AGE ─────────────────────────────────────────────────────────────────
    if age is not None:
        chapter = life_stage_for_age(age)
        mk = velocity_match(chapter, city.get("velocity"))
        if chapter:
            reasons.append({"layer": "AGE", "text": _AGE_FRAMES[lang][mk].format(
                chapter=_CHAPTER_NAME[lang].get(chapter, chapter), city=city.get("name", ""))})

    # ── INTENT (only with a concern) ─────────────────────────────────────────
    if has_concern and signals:
        reasons.append({"layer": "INTENT", "text": compose_primary_reason(concern, signals[0], lang, tier=scored.get("tier"))})

    return reasons[:4]


def balanced_score(
    chart: dict,
    city: dict,
    *,
    all_lines: Optional[list[dict]] = None,
    conditions: Optional[dict] = None,
    relocation: Optional[dict] = None,
) -> dict:
    """
    Concern-agnostic score for the city drill-down when no concern is supplied.
    Averages the five concern scores so the tier reflects the city's overall
    texture rather than any single life area.
    """
    if all_lines is None:
        all_lines = compute_all_lines(chart.get("birth_jd"), chart)
    if conditions is None:
        conditions = compute_all_conditions(chart)
    if relocation is None:
        from antar_engine.places_relocation import compute_relocated_chart
        relocation = compute_relocated_chart(chart, float(city["lat"]), float(city["lon"]))

    per = {}
    agg_signals: list[dict] = []
    agg_watch: list[dict] = []
    total = 0
    for concern in VALID_CONCERNS:
        s = score_city_for_concern(
            chart, city, concern,
            all_lines=all_lines, conditions=conditions, relocation=relocation,
        )
        per[concern] = s["score"]
        total += s["score"]
        agg_signals.extend(s["_signals"])
        agg_watch.extend(s["_watch"])

    score = int(round(total / len(VALID_CONCERNS)))
    tier = "FLOW" if score >= _TIER_FLOW else ("MIXED" if score >= _TIER_STRAIN else "STRAIN")

    # De-dup signals, keep strongest.
    seen = {}
    for sig in agg_signals:
        k = (sig["planet"], sig["angle"])
        if k not in seen or sig["strength"] > seen[k]["strength"]:
            seen[k] = sig
    signals = sorted(seen.values(), key=lambda s: -s["strength"])

    return {
        "city": {
            "name": city.get("name"), "country": city.get("country"),
            "country_code": city.get("country_code"),
            "lat": float(city["lat"]), "lon": float(city["lon"]),
            "timezone": city.get("timezone"),
            "velocity": city.get("velocity"),
        },
        "score": score,
        "tier": tier,
        "_per_concern": per,
        "_signals": signals,
        "_watch": agg_watch,
        "_relocation": relocation,
    }
