"""
antar_engine/score_day.py — single timing source of truth
==========================================================

`score_day(chart, date, location)` is the function the daily and monthly
endpoints both read from. By construction the two surfaces can no longer
disagree: the day shows the score and domain states for `date=today`; the
month is the rolling integral of the same per-day scores across
`[period_start, period_end]`.

Three layers feed one scalar (raw_score) and one 5-slot domain_states map:

  1. STRUCTURAL (slow)  — Vimshottari MD + AD + PD + SD lords
                          dignity-weighted by the natal house each lord
                          occupies. Sets the felt weather.

  2. TRANSIT (medium)   — planets transiting natal houses + classical
                          drishti aspects to natal points, bounded to
                          `date`. Reads transit_engine.get_full_transit_report.

  3. PANCHANGA (fast/   — Vara · Tithi · Nakshatra · Yoga · Karana at
     texture)             local sunrise for the user's `location`. The
                          Vedic day starts at sunrise, not midnight, so
                          location is required for correctness.

The NATAL-CONTAINER GATE intersects each layer's triggered houses with
the chart's natal promise (benefic/malefic occupancy). A layer can only
move a domain that the natal chart promises something in. No promise →
no contribution.

Domain slots are exactly five — `mind`, `body`, `work`, `money`, `people`.
Each gets one `state` (favorable | caution | steady). Last-write-wins
internally so the result is structurally "one card per slot".

Public API
----------
  score_day(chart, date, location)        -> dict (one day's read)
  score_range(chart, start, end, loc)     -> list[dict] (days inclusive)
  rolling_window_extremes(daily, days=7)  -> (best_iso, caution_iso)
                                             both guaranteed inside input.
"""
from __future__ import annotations

from datetime import date as _date, datetime as _dt, timedelta as _td
from typing import Optional, Dict, Any, List, Tuple


# ── Locked enums ──────────────────────────────────────────────────────
DOMAIN_SLOTS = ("mind", "body", "work", "money", "people")
STATE_FAVORABLE = "favorable"
STATE_CAUTION   = "caution"
STATE_STEADY    = "steady"

_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
_MALEFIC = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}

# Map natal house -> one of the five domain slots.
_HOUSE_TO_DOMAIN = {
    1: "body",  2: "money", 3: "work",  4: "mind",
    5: "mind",  6: "body",  7: "people", 8: "body",
    9: "mind", 10: "work", 11: "money", 12: "mind",
}

# Map planet -> domain slot. Used by the panchanga nakshatra-lord bias.
_PLANET_TO_DOMAIN = {
    "Sun":     "work", "Moon":    "mind",
    "Mercury": "work", "Mars":    "body",
    "Jupiter": "money","Venus":   "people",
    "Saturn":  "work", "Rahu":    "work",
    "Ketu":    "mind",
}


# ── Natal-container gate ──────────────────────────────────────────────
def _natal_promise(chart: dict) -> Dict[int, float]:
    """Per-house promise score from natal occupants.

    Benefic-occupied houses promise (positive); malefic-occupied houses
    drag (negative); empty houses are neutral. A house with promise <= -1.0
    is "blocked" — no transit hit on it will surface as a positive signal,
    per the natal-container rule.
    """
    promise = {h: 0.0 for h in range(1, 13)}
    planets = (chart or {}).get("planets", {}) or {}
    for pname, pdata in planets.items():
        if not isinstance(pdata, dict):
            continue
        h = pdata.get("house")
        if not isinstance(h, int) or not (1 <= h <= 12):
            continue
        if pname in _BENEFIC:
            promise[h] += 1.0
        elif pname in _MALEFIC:
            promise[h] -= 0.8
    return promise


# ── Layer 1: structural (Vimshottari MD+AD+PD+SD) ─────────────────────
def _structural_layer(chart: dict, d: _date) -> Dict[str, Any]:
    """Vimshottari lord stack — weather/theme for the day."""
    out = {"lords": {"md": None, "ad": None, "pd": None, "sd": None},
           "score": 0.0,
           "domains": {dom: 0.0 for dom in DOMAIN_SLOTS}}
    birth_jd = (chart or {}).get("birth_jd")
    if birth_jd is None:
        return out
    try:
        from antar_engine.life_arc.phase_analyzer import get_current_vimsottari
        vim = get_current_vimsottari(chart, birth_jd,
                                     now=_dt(d.year, d.month, d.day, 12, 0, 0)) or {}
    except Exception:
        vim = {}
    lords = {
        "md": vim.get("md"), "ad": vim.get("ad"),
        "pd": vim.get("pd"), "sd": vim.get("sd"),
    }
    out["lords"] = lords

    # Per-level weight; deepest level (SD) lightest, MD heaviest.
    weights = {"md": 0.40, "ad": 0.30, "pd": 0.20, "sd": 0.10}
    promise = _natal_promise(chart)
    planets = (chart or {}).get("planets", {}) or {}
    layer_score = 0.0
    domain_bias = {dom: 0.0 for dom in DOMAIN_SLOTS}

    for lvl, w in weights.items():
        lord = lords.get(lvl)
        if not isinstance(lord, str) or not lord:
            continue
        lord_data = planets.get(lord) or {}
        h = lord_data.get("house") if isinstance(lord_data.get("house"), int) else None
        if h is None:
            continue
        # Lord's tone — benefic +, malefic −, others neutral.
        if lord in _BENEFIC:
            base = +1.0
        elif lord in _MALEFIC:
            base = -0.7
        else:
            base = 0.0
        # Natal house gates the bleed: promise > 0 amplifies, < 0 dampens.
        contrib = base * w * (1.0 + 0.2 * promise.get(h, 0.0))
        layer_score += contrib
        dom = _HOUSE_TO_DOMAIN.get(h, "work")
        domain_bias[dom] += contrib

    out["score"]   = layer_score
    out["domains"] = domain_bias
    return out


# ── Layer 2: transit (planets in sky vs natal) ────────────────────────
def _transit_layer(chart: dict, d: _date) -> Dict[str, Any]:
    """Transit planets + drishti aspects to natal points on `d`."""
    out = {"aspects": [], "score": 0.0,
           "domains": {dom: 0.0 for dom in DOMAIN_SLOTS}}
    try:
        from antar_engine.transit_engine import get_full_transit_report
        report = get_full_transit_report(chart,
                                         date=_dt(d.year, d.month, d.day, 12, 0, 0)) or {}
    except Exception:
        return out

    promise = _natal_promise(chart)
    layer_score = 0.0
    domain_bias = {dom: 0.0 for dom in DOMAIN_SLOTS}
    aspects_used = []

    for a in (report.get("top_aspects") or [])[:8]:
        tp = a.get("transit_planet")
        natal_house = a.get("natal_house")
        strength = a.get("strength") or 0.0
        try:
            strength = float(strength)
        except Exception:
            strength = 0.0
        if not isinstance(natal_house, int) or not (1 <= natal_house <= 12):
            continue
        # NATAL-CONTAINER GATE: if the natal house promises nothing
        # (or is heavily afflicted), suppress the transit signal.
        if promise.get(natal_house, 0.0) <= -1.0:
            continue
        # Strength may come 0..1 or 0..100 — normalise.
        if strength > 1.0:
            strength /= 100.0
        if tp in _BENEFIC:
            tone = +1.0
        elif tp in _MALEFIC:
            tone = -1.0
        else:
            tone = 0.0
        contrib = tone * strength * 0.6   # bounded transit weight
        layer_score += contrib
        dom = _HOUSE_TO_DOMAIN.get(natal_house, "work")
        domain_bias[dom] += contrib
        aspects_used.append(a)

    out["aspects"] = aspects_used
    out["score"]   = layer_score
    out["domains"] = domain_bias
    return out


# ── Layer 3: panchanga (five limbs at local sunrise) ──────────────────
def _panchanga_layer(chart: dict, d: _date, location: dict) -> Dict[str, Any]:
    out = {"score": 0.0, "domains": {dom: 0.0 for dom in DOMAIN_SLOTS},
           "panchanga": {}}
    location = location or {}
    lat = float(location.get("lat", 28.6))
    lng = float(location.get("lng", 77.2))
    tz_offset = location.get("tz_offset")
    try:
        from antar_engine.daily_panchanga import calculate_panchanga
        p = calculate_panchanga(lat=lat, lng=lng, tz_offset=tz_offset,
                                target_date=d) or {}
    except Exception:
        return out

    layer_score = 0.0
    domain_bias = {dom: 0.0 for dom in DOMAIN_SLOTS}

    # Tithi / Yoga / Karana qualities — read explicit fields when present.
    # Tithi is the strongest texture; karana = half-tithi so half-weight.
    def _q(key):
        v = p.get(key)
        if isinstance(v, str):
            v = v.strip().lower()
        return v or "neutral"

    if _q("tithi_quality") == "auspicious":   layer_score += 0.40
    elif _q("tithi_quality") == "inauspicious": layer_score -= 0.40
    if _q("yoga_quality")  == "auspicious":   layer_score += 0.30
    elif _q("yoga_quality")  == "inauspicious": layer_score -= 0.30
    if _q("karana_quality") == "auspicious":  layer_score += 0.15
    elif _q("karana_quality") == "inauspicious": layer_score -= 0.15

    # Nakshatra lord biases its planet's domain. Vara lord same idea —
    # lighter weight, doesn't compound with nakshatra if they coincide.
    nak_lord = p.get("nakshatra_lord")
    if isinstance(nak_lord, str) and nak_lord:
        dom = _PLANET_TO_DOMAIN.get(nak_lord)
        if dom:
            if nak_lord in _BENEFIC:
                domain_bias[dom] += 0.30
            elif nak_lord in _MALEFIC:
                domain_bias[dom] -= 0.30
    vara_lord = p.get("vara") or p.get("day_lord")
    if isinstance(vara_lord, str) and vara_lord and vara_lord != nak_lord:
        dom = _PLANET_TO_DOMAIN.get(vara_lord)
        if dom:
            if vara_lord in _BENEFIC:
                domain_bias[dom] += 0.15
            elif vara_lord in _MALEFIC:
                domain_bias[dom] -= 0.15

    out["score"]    = layer_score
    out["domains"]  = domain_bias
    out["panchanga"] = {
        "tithi":     p.get("tithi"),
        "nakshatra": p.get("nakshatra"),
        "yoga":      p.get("yoga"),
        "karana":    p.get("karana"),
        "vara":      vara_lord,
        "nakshatra_lord": nak_lord,
        "tithi_quality":  _q("tithi_quality"),
        "yoga_quality":   _q("yoga_quality"),
        "karana_quality": _q("karana_quality"),
        "sunrise": p.get("sunrise"),
        "sunset":  p.get("sunset"),
    }
    return out


# ── Aggregation helpers ───────────────────────────────────────────────
def _normalize_score(raw: float) -> int:
    """Map raw scorer sum into 0..100 with 50 as neutral.

    Raw range across the three layers is roughly [-3.0, +3.0]; ×12 + 50
    gives a usable spread without saturating either end on a typical day.
    """
    val = 50.0 + raw * 12.0
    return int(round(max(0.0, min(100.0, val))))


def _states_from_bias(bias: Dict[str, float]) -> Dict[str, str]:
    """Map per-slot bias into the contract's state enum."""
    out: Dict[str, str] = {}
    for dom in DOMAIN_SLOTS:
        v = bias.get(dom, 0.0)
        if v >= 0.25:
            out[dom] = STATE_FAVORABLE
        elif v <= -0.25:
            out[dom] = STATE_CAUTION
        else:
            out[dom] = STATE_STEADY
    return out


def _coerce_date(x) -> _date:
    if isinstance(x, _date) and not isinstance(x, _dt):
        return x
    if isinstance(x, _dt):
        return x.date()
    if isinstance(x, str):
        return _date.fromisoformat(x[:10])
    return _date.today()


# ── Public API ────────────────────────────────────────────────────────
def score_day(chart: dict, date_input, location: Optional[dict] = None) -> Dict[str, Any]:
    """Single source of timing truth.

    Returns:
        {
            "date":          ISO,
            "score":         int 0..100,
            "raw_score":     float (internal sum across layers),
            "domain_states": {mind, body, work, money, people} -> state,
            "domain_bias":   {mind, body, work, money, people} -> float,
            "layers":        {structural, transit, panchanga},
            "natal_promise": {1..12 -> float},
        }
    """
    d = _coerce_date(date_input)
    loc = location or {}

    structural = _structural_layer(chart, d)
    transit    = _transit_layer(chart, d)
    panchanga  = _panchanga_layer(chart, d, loc)

    raw = structural["score"] + transit["score"] + panchanga["score"]
    bias = {dom: 0.0 for dom in DOMAIN_SLOTS}
    for layer in (structural, transit, panchanga):
        for k, v in (layer.get("domains") or {}).items():
            if k in bias:
                bias[k] += v

    return {
        "date":          d.isoformat(),
        "score":         _normalize_score(raw),
        "raw_score":     raw,
        "domain_states": _states_from_bias(bias),
        "domain_bias":   bias,
        "layers": {
            "structural": structural,
            "transit":    transit,
            "panchanga":  panchanga,
        },
        "natal_promise": _natal_promise(chart),
    }


def score_range(chart: dict, start, end, location: Optional[dict] = None) -> List[Dict[str, Any]]:
    """Per-day scores across [start, end] inclusive.

    Each entry carries date + score + domain_states + raw_score so the
    monthly aggregator can compute rolling windows AND surface the same
    domain_states the daily endpoint shows.
    """
    s = _coerce_date(start); e = _coerce_date(end)
    out: List[Dict[str, Any]] = []
    if e < s:
        return out
    cur = s
    while cur <= e:
        sd = score_day(chart, cur, location)
        out.append({
            "date": cur.isoformat(),
            "score": sd["score"],
            "raw_score": sd["raw_score"],
            "domain_states": sd["domain_states"],
        })
        cur = cur + _td(days=1)
    return out


def rolling_window_extremes(daily_scores: List[Dict[str, Any]],
                            window_days: int = 7
                            ) -> Tuple[Optional[str], Optional[str]]:
    """Best / caution rolling-N-day windows over a per-day score list.

    Both returned dates are window-START dates and are guaranteed to lie
    inside the input range (the monthly clamp is structurally enforced by
    construction here — we never look outside `daily_scores`).
    """
    if not daily_scores:
        return (None, None)
    n = len(daily_scores)
    if n < window_days:
        # Whole range as a single window.
        return (daily_scores[0]["date"], daily_scores[0]["date"])

    cur = sum(d.get("raw_score", 0.0) for d in daily_scores[:window_days])
    best_sum, best_idx = cur, 0
    worst_sum, worst_idx = cur, 0
    for i in range(1, n - window_days + 1):
        cur += daily_scores[i + window_days - 1].get("raw_score", 0.0) \
             - daily_scores[i - 1].get("raw_score", 0.0)
        if cur > best_sum:
            best_sum, best_idx = cur, i
        if cur < worst_sum:
            worst_sum, worst_idx = cur, i
    return (daily_scores[best_idx]["date"], daily_scores[worst_idx]["date"])


__all__ = [
    "DOMAIN_SLOTS",
    "STATE_FAVORABLE", "STATE_CAUTION", "STATE_STEADY",
    "score_day", "score_range", "rolling_window_extremes",
]
