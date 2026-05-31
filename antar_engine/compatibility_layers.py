"""
antar_engine/compatibility_layers.py

Phase-1 mapping layer for the 6-layer compatibility surface (POST /api/v1/compat).

Pure transformation: it takes the EXISTING structured engine output
(antar_engine.Compatibility.calculate_compatibility) and folds it into the
6-layer contract the frontend mock already expects. No new astrology beyond one
small cross-chart check (mutual 6/8), which uses only data already in the charts.

Layers (fixed order): soul, chemistry, public, lifepath, communication, friction.
All layers follow ONE convention: higher score = better = passed.
  passed = score >= 65
  badge  = FLOW (>=75) | MIXED (50-74) | STRAIN (<50)

NOTE on the friction layer: its sources are defined so that HIGHER = LESS friction
(mutual_6_8=90 when neither fires, nadi_dosha=100 when different, growth_areas
near 100 when few). The layer score is therefore the weighted average directly —
NOT 100 - avg. Inverting would make heavy friction render as FLOW/passed, which
contradicts the contract's own semantics ("80 = low friction = GOOD = passed").
See the Phase-1 handoff for the flagged spec inconsistency.
"""

from datetime import datetime, timezone

from antar_engine.Compatibility import SIGNS, SIGN_RULER
from antar_engine import compatibility_templates as TPL
from antar_engine import compatibility_synastry as SYN

VALID_REASONS = ("romantic", "business", "cofounder", "friend", "family",
                 "employee", "boss-or-manager")
ROLE_REQUIRED_REASONS = ("employee", "boss-or-manager")
VALID_ROLES = ("sales", "marketing", "finance", "managerial")

LAYER_ORDER = ["soul", "chemistry", "public", "lifepath", "communication", "friction"]

LAYER_DEFINITIONS = {
    "soul":          {"sources": ["d9_overall", "graha_maitri", "varna"],            "weights": [0.50, 0.35, 0.15]},
    "chemistry":     {"sources": ["yoni", "venus_compatibility", "mars_compatibility"], "weights": [0.40, 0.35, 0.25]},
    "public":        {"sources": ["house_7", "house_10", "house_11"],                "weights": [0.40, 0.40, 0.20]},
    "lifepath":      {"sources": ["dasha_timing", "bhakoot"],                         "weights": [0.70, 0.30]},
    "communication": {"sources": ["mercury_compatibility", "graha_maitri", "gana"],   "weights": [0.40, 0.30, 0.30]},
    "friction":      {"sources": ["mutual_6_8", "nadi_dosha", "growth_areas_count", "cross_aspect_harmony"], "weights": [0.35, 0.25, 0.15, 0.25]},
}

# Per-reason weighting of the 6 layers (sum to 1.0 each).
REASON_WEIGHTS = {
    "romantic":        {"soul": 0.20, "chemistry": 0.25, "public": 0.05, "lifepath": 0.20, "communication": 0.15, "friction": 0.15},
    "business":        {"soul": 0.10, "chemistry": 0.10, "public": 0.20, "lifepath": 0.20, "communication": 0.20, "friction": 0.20},
    "cofounder":       {"soul": 0.15, "chemistry": 0.10, "public": 0.20, "lifepath": 0.25, "communication": 0.15, "friction": 0.15},
    "friend":          {"soul": 0.20, "chemistry": 0.25, "public": 0.05, "lifepath": 0.15, "communication": 0.20, "friction": 0.15},
    "family":          {"soul": 0.25, "chemistry": 0.15, "public": 0.05, "lifepath": 0.15, "communication": 0.20, "friction": 0.20},
    "employee":        {"soul": 0.10, "chemistry": 0.15, "public": 0.20, "lifepath": 0.15, "communication": 0.20, "friction": 0.20},
    "boss-or-manager": {"soul": 0.10, "chemistry": 0.10, "public": 0.25, "lifepath": 0.15, "communication": 0.25, "friction": 0.15},
}

# Role modifiers (applied to employee + boss-or-manager weights, then renormalized).
ROLE_MODIFIERS = {
    "sales":      {"chemistry": +0.10, "communication": +0.05, "lifepath": -0.10, "friction": -0.05},
    "marketing":  {"communication": +0.10, "chemistry": +0.05, "soul": -0.05, "lifepath": -0.10},
    "finance":    {"friction": +0.10, "public": +0.05, "chemistry": -0.05, "soul": -0.10},
    "managerial": {"public": +0.10, "lifepath": +0.05, "chemistry": -0.05, "friction": -0.10},
}

_COMPAT_MAP = {"strong": 90, "moderate": 65, "challenging": 40}


# ── source resolution ───────────────────────────────────────────────────────

def _ashtakoot_pcts(engine_result: dict) -> dict:
    """name -> match_pct (0-100) for each Ashtakoot component."""
    out = {}
    for comp in engine_result.get("ashtakoot", {}).get("components", []):
        if isinstance(comp, dict) and comp.get("name"):
            out[comp["name"]] = comp
    return out


def _nadi_score(engine_result: dict) -> float:
    comp = _ashtakoot_pcts(engine_result).get("Nadi", {})
    # 100 when different Nadi (good), 30 when same (dosha present).
    return 30.0 if comp.get("nadi_dosha") else 100.0


def _house_score(engine_result: dict, house: int) -> float:
    """B-in-A house placement score; 50 when the house is unoccupied/absent."""
    hp = (engine_result.get("house_analysis", {})
                        .get("a_perspective", {})
                        .get("house_placements", {}) or {})
    cell = hp.get(str(house)) or hp.get(house)
    if isinstance(cell, dict) and isinstance(cell.get("score"), (int, float)):
        return float(cell["score"])
    return 50.0


def _mutual_6_8(chart_a: dict, chart_b: dict) -> float:
    """
    Cross-chart 6/8 detection: is A's lagna-lord sitting in B's 6th or 8th
    (and vice versa)? 0 if mutual, 60 if one-way, 90 if neither.
    Higher = less friction. Uses only whole-sign placement (no new astrology).
    """
    def lagna_idx(chart):
        lg = chart.get("lagna", {})
        sign = lg.get("sign", "Aries") if isinstance(lg, dict) else "Aries"
        return SIGNS.index(sign) if sign in SIGNS else 0

    def lord_house_in_other(owner, other):
        lg = owner.get("lagna", {})
        sign = lg.get("sign", "Aries") if isinstance(lg, dict) else "Aries"
        lord = SIGN_RULER.get(sign, "Sun")
        pdata = (other.get("planets", {}) or {}).get(lord, {})
        psign = pdata.get("sign", "")
        if psign not in SIGNS:
            return None
        return ((SIGNS.index(psign) - lagna_idx(other)) % 12) + 1

    a_in_b = lord_house_in_other(chart_a, chart_b)
    b_in_a = lord_house_in_other(chart_b, chart_a)
    a_hit = a_in_b in (6, 8)
    b_hit = b_in_a in (6, 8)
    if a_hit and b_hit:
        return 0.0
    if a_hit or b_hit:
        return 60.0
    return 90.0


def resolve_source(name: str, engine_result: dict, chart_a: dict, chart_b: dict) -> float:
    """Resolve a single source key into a 0-100 number."""
    ash = _ashtakoot_pcts(engine_result)
    d9 = engine_result.get("d9_navamsa", {})

    if name == "d9_overall":
        return float(d9.get("overall_score", 50))
    if name == "graha_maitri":
        return float(ash.get("Graha Maitri", {}).get("match_pct", 50))
    if name == "varna":
        return float(ash.get("Varna", {}).get("match_pct", 50))
    if name == "yoni":
        return float(ash.get("Yoni", {}).get("match_pct", 50))
    if name == "gana":
        return float(ash.get("Gana", {}).get("match_pct", 50))
    if name == "bhakoot":
        return float(ash.get("Bhakoot", {}).get("match_pct", 50))
    if name == "venus_compatibility":
        return float(_COMPAT_MAP.get(d9.get("venus_compatibility"), 50))
    if name == "mars_compatibility":
        return float(_COMPAT_MAP.get(d9.get("mars_compatibility"), 50))
    if name == "mercury_compatibility":
        # Phase 2: real Mercury-to-Mercury cross-compat (was a 50 stub).
        return SYN.mercury_cross_compat(chart_a, chart_b)["score"]
    if name == "house_7":
        return SYN.house_quality_score(chart_a, chart_b, 7)
    if name == "house_10":
        return SYN.house_quality_score(chart_a, chart_b, 10)   # Phase 2: real (engine never computed 10/11)
    if name == "house_11":
        return SYN.house_quality_score(chart_a, chart_b, 11)
    if name == "dasha_timing":
        return float(engine_result.get("dasha_timing", {}).get("score", 50))
    if name == "mutual_6_8":
        return _mutual_6_8(chart_a, chart_b)
    if name == "nadi_dosha":
        return _nadi_score(engine_result)
    if name == "growth_areas_count":
        n = len(engine_result.get("growth_areas", []) or [])
        return float(max(0, 100 - n * 15))
    if name == "cross_aspect_harmony":
        # Phase 2: cross-chart graha drishti to lagna/7th (benefic up, malefic down).
        return SYN.cross_aspect_harmony(chart_a, chart_b)["score"]
    return 50.0


def compute_layer_score(engine_result: dict, key: str, chart_a: dict, chart_b: dict) -> int:
    spec = LAYER_DEFINITIONS[key]
    vals = [resolve_source(s, engine_result, chart_a, chart_b) for s in spec["sources"]]
    wsum = sum(w for w in spec["weights"])
    avg = sum(v * w for v, w in zip(vals, spec["weights"])) / (wsum or 1.0)
    # friction sources are already "higher = less friction" -> no inversion.
    return int(round(max(0, min(100, avg))))


def _badge(score: int) -> str:
    if score >= 75:
        return "FLOW"
    if score < 50:
        return "STRAIN"
    return "MIXED"


def _overall_tier(score: int) -> str:
    if score >= 75:
        return "FLOW"
    if score < 50:
        return "STRAIN"
    return "MIXED"


def _label(score: int) -> str:
    if score >= 85:
        return "Exceptional alignment"
    if score >= 70:
        return "Strong alignment"
    if score >= 55:
        return "Workable with care"
    if score >= 40:
        return "Significant friction"
    return "Hard mismatch"


def effective_weights(reason: str, role: str | None) -> dict:
    base = dict(REASON_WEIGHTS[reason])
    if reason in ROLE_REQUIRED_REASONS and role in ROLE_MODIFIERS:
        for layer, delta in ROLE_MODIFIERS[role].items():
            base[layer] = base.get(layer, 0.0) + delta
        # clamp negatives, then renormalize to sum 1.0
        base = {k: max(0.0, v) for k, v in base.items()}
        total = sum(base.values()) or 1.0
        base = {k: v / total for k, v in base.items()}
    return base


def build_layers(engine_result: dict, reason: str, role: str | None,
                 chart_a: dict, chart_b: dict, a_name: str, b_name: str) -> tuple:
    """Return (layers list, {key: score}). Always 6 layers in fixed order."""
    layers, scores = [], {}
    for key in LAYER_ORDER:
        score = compute_layer_score(engine_result, key, chart_a, chart_b)
        scores[key] = score
        badge = _badge(score)
        layers.append({
            "key": key,
            "name": TPL.LAYER_NAMES[key],
            "passed": score >= 65,
            "badge": badge,
            "line": TPL.get_line(reason, key, badge, role, a_name, b_name),
        })
    return layers, scores


def build_compat_response(
    engine_result: dict,
    reason: str,
    role: str | None,
    chart_a: dict,
    chart_b: dict,
    a_name: str,
    b_name: str,
    chart_a_id: str,
    chart_b_id,
    chart_b_label: str,
    language: str = "en",
    generated_at: str | None = None,
    strip_fn=None,
    deep_read_details: dict | None = None,
    lk_insights: list | None = None,
) -> dict:
    """
    Full English (untranslated) 6-layer response, jargon-stripped.
    Translation (es/pt) is applied by the endpoint after this returns.

    Phase 2:
      - deep_read_details {layer_key: paragraph} populates each layer's `detail`.
      - lk_insights (already gated/founder-confirmed upstream) attach as a
        top-level `lk_insights` list ONLY when non-empty (contract stays stable
        while the LK library is disabled).
    """
    layers, scores = build_layers(engine_result, reason, role, chart_a, chart_b, a_name, b_name)

    # Phase 2: attach deep_read prose to the reserved per-layer `detail` field.
    if deep_read_details:
        for layer in layers:
            d = deep_read_details.get(layer["key"])
            if isinstance(d, str) and d.strip():
                layer["detail"] = d.strip()

    weights = effective_weights(reason, role)
    overall = sum(scores[k] * weights.get(k, 0.0) for k in LAYER_ORDER)
    score = int(round(max(20, min(98, overall))))

    tier = _overall_tier(score)
    response = {
        "chart_a_id": chart_a_id,
        "chart_b_id": chart_b_id,
        "chart_b_label": chart_b_label,
        "reason": reason,
        "role": role,
        "language": language,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "score": score,
        "label": _label(score),
        "headline": TPL.get_headline(reason, tier, a_name, b_name),
        "detail": TPL.get_detail(reason, tier, a_name, b_name),
        "layers": layers,
    }

    # Strip user-facing strings (curated_static keeps planet actors). Single
    # enforcement point at the response boundary. Only user-facing fields.
    if strip_fn is not None:
        for f in ("headline", "detail", "label"):
            try:
                response[f] = strip_fn(response[f], "en", field_type="plain", source="curated_static")
            except Exception:
                pass
        for layer in response["layers"]:
            try:
                layer["line"] = strip_fn(layer["line"], "en", field_type="plain", source="curated_static")
                if layer.get("detail"):
                    layer["detail"] = strip_fn(layer["detail"], "en", field_type="plain", source="curated_static")
            except Exception:
                pass

    # Phase 2: attach gated LK insights only when present (disabled => no key).
    if lk_insights:
        response["lk_insights"] = lk_insights
    return response


# ── raw chart-B resolution (no UUID) ────────────────────────────────────────

def _current_dasha_from_vim(vim_rows: list) -> str:
    """Pure mirror of main._current_dasha_str over normalized vim rows."""
    now = datetime.utcnow()
    md = ad = None
    for row in vim_rows:
        lord = row.get("lord_or_sign") or row.get("planet_or_sign", "")
        level = row.get("level") or row.get("type", "mahadasha")
        s_str = row.get("start_date") or row.get("start", "")
        e_str = row.get("end_date") or row.get("end", "")
        if not s_str or not e_str:
            continue
        try:
            s = datetime.strptime(str(s_str)[:10], "%Y-%m-%d")
            e = datetime.strptime(str(e_str)[:10], "%Y-%m-%d")
            if s <= now <= e:
                if level == "mahadasha":
                    md = lord
                elif level in ("antardasha", "antar"):
                    ad = lord
        except Exception:
            continue
    if md and ad:
        return f"{md}-{ad}"
    if md:
        return md
    for row in vim_rows:
        if (row.get("level") or row.get("type", "")) == "mahadasha":
            return row.get("lord_or_sign") or row.get("planet_or_sign", "Unknown")
    return "Unknown"


def build_chart_from_raw(name: str, date: str, time: str, lat: float, lon: float, tz: str) -> dict:
    """
    Compute a chart from raw birth data and inject chart['current_dasha']
    (the string the structured engine's dasha_timing parser expects). Lazy
    imports keep module import cheap and avoid circular imports with main.
    """
    from antar_engine.chart import calculate_chart
    chart = calculate_chart(
        birth_date=date,
        birth_time=time or "12:00",
        lat=lat, lng=lon,
        timezone=tz or "UTC",
    )
    vim_rows = []
    try:
        from antar_engine import vimsottari as _vim
        raw = _vim.calculate_vimsottari_from_chart(chart, chart.get("birth_jd"))
        for p in raw:
            if isinstance(p, dict) and "sub" in p:
                sd = str(p.get("start_date", "") or p.get("start", ""))[:10]
                ed = str(p.get("end_date", "") or p.get("end", ""))[:10]
                vim_rows.append({"lord_or_sign": p.get("lord", ""), "start_date": sd,
                                 "end_date": ed, "level": "mahadasha"})
                for s in p.get("sub", []):
                    ssd = str(s.get("start_date", "") or s.get("start", ""))[:10]
                    sed = str(s.get("end_date", "") or s.get("end", ""))[:10]
                    vim_rows.append({"lord_or_sign": s.get("lord", ""), "start_date": ssd,
                                     "end_date": sed, "level": "antardasha"})
            elif isinstance(p, dict):
                sd = str(p.get("start_date", "") or p.get("start", ""))[:10]
                ed = str(p.get("end_date", "") or p.get("end", ""))[:10]
                vim_rows.append({"lord_or_sign": p.get("lord", "") or p.get("lord_or_sign", ""),
                                 "start_date": sd, "end_date": ed,
                                 "level": p.get("level", "mahadasha")})
    except Exception as e:
        print(f"[compat-layers] raw vimsottari non-fatal: {e}")
    chart["current_dasha"] = _current_dasha_from_vim(vim_rows)
    return chart
