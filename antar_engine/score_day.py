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
# A day carrying a strong PUSH and a strong PULL in the same domain is not a
# quiet day. Summing them cancels to "steady", which is the most misleading
# thing the engine can say: the owner lost money on the night of 15 July and
# won it back before dawn on the 16th — one Vedic day, sunrise to sunrise —
# and the card read "money is quiet, no big moves needed". Both signals were
# real; the arithmetic destroyed them. Variance IS the prediction.
STATE_VOLATILE  = "volatile"

_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
_MALEFIC = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}

# Map natal house -> one of the five domain slots.
# A house rarely governs one area of life. Forcing a 1:1 map produced two
# demonstrable failures:
#
#   `people` drew from the 7th ALONE — one house out of twelve — so the
#   relationship domain sat STEADY on 27 of 28 measured chart-days while `mind`
#   drew from four houses and swamped everything.
#
#   The 5th mapped to `mind` only. In Jyotish the 5th IS speculation — the bet,
#   the punt, the position. So a speculative money loss could not reach the
#   money domain at all; the wiring made it unreachable.
#
# Weighted and multi-domain, following the classical groupings: wealth is
# 2/5/9/11, loss is 6/8/12, and the 8th and 12th are money houses (other
# people's money, and expenditure) as much as they are anything else.
_HOUSE_DOMAIN_WEIGHTS = {
    1:  {"body": 0.7, "mind": 0.3},
    2:  {"money": 1.0},
    3:  {"work": 0.7, "people": 0.3},          # siblings, peers, outreach
    4:  {"mind": 0.6, "body": 0.2, "people": 0.2},   # home, mother, peace
    5:  {"money": 0.5, "mind": 0.3, "people": 0.2},  # SPECULATION, children
    6:  {"body": 0.5, "work": 0.3, "money": 0.2},    # illness, service, debt
    7:  {"people": 0.8, "work": 0.2},          # partner, clients
    8:  {"money": 0.5, "body": 0.3, "mind": 0.2},    # sudden loss, others' money
    9:  {"mind": 0.7, "work": 0.3},
    10: {"work": 1.0},
    11: {"money": 0.6, "people": 0.4},         # gains AND friends
    12: {"money": 0.4, "mind": 0.4, "body": 0.2},    # expenditure, sleep
}

# Kept for callers that still want a single dominant slot.
_HOUSE_TO_DOMAIN = {
    h: max(w.items(), key=lambda kv: kv[1])[0]
    for h, w in _HOUSE_DOMAIN_WEIGHTS.items()
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
    # [dasha-layer-dead 2026-07-22] This passed a NAIVE datetime while the
    # dasha periods carry tzinfo, so every call raised
    #     TypeError: can't compare offset-naive and offset-aware datetimes
    # which the bare except swallowed into vim = {}. Lords came back all None,
    # the layer scored 0.0, and its domain bias was 0.0 — for every chart, on
    # every day, since it was written. The running dasha is the single most
    # important timing factor in Vedic astrology and it has been contributing
    # nothing to the daily score.
    #
    # Try aware first, fall back to naive, so it works whichever shape a given
    # chart's periods carry instead of silently going dark again.
    vim = {}
    try:
        from antar_engine.life_arc.phase_analyzer import get_current_vimsottari
        from datetime import timezone as _tz
        try:
            vim = get_current_vimsottari(
                chart, birth_jd,
                now=_dt(d.year, d.month, d.day, 12, 0, 0, tzinfo=_tz.utc)) or {}
        except TypeError:
            vim = get_current_vimsottari(
                chart, birth_jd, now=_dt(d.year, d.month, d.day, 12, 0, 0)) or {}
    except Exception as _e:
        import logging as _l
        _l.getLogger("antar.score_day").warning(
            f"[score_day] vimsottari unavailable, dasha layer inert: {_e}")
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
        for dom, wgt in _HOUSE_DOMAIN_WEIGHTS.get(h, {"work": 1.0}).items():
            domain_bias[dom] += contrib * wgt

        # What the lord RULES, not only where it sits. A dasha lord owning the
        # 6th, 8th or 12th delivers loss results from wherever it stands; one
        # owning the 2nd or 11th delivers gain. Reading occupancy alone missed
        # this entirely.
        for rh in _houses_ruled(chart, lord):
            if rh in _LOSS_HOUSES:
                domain_bias["money"] -= 0.35 * w
                if rh == 6:
                    domain_bias["body"] -= 0.20 * w
            elif rh in _WEALTH_HOUSES:
                domain_bias["money"] += 0.30 * w

    out["score"]   = layer_score
    out["domains"] = domain_bias
    return out


# ── House rulership ───────────────────────────────────────────────────
_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
          "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
_SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
              "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

# The classical loss set and wealth set. A dasha lord RULING these delivers
# their results wherever it happens to sit — which the occupancy-only reading
# could not see at all.
_LOSS_HOUSES = (6, 8, 12)
_WEALTH_HOUSES = (2, 11)
_SPECULATION_HOUSE = 5


def _lagna_index(chart: dict) -> Optional[int]:
    lg = (chart or {}).get("lagna") or {}
    i = lg.get("sign_index")
    if isinstance(i, int) and 0 <= i <= 11:
        return i
    try:
        return _SIGNS.index(lg.get("sign"))
    except Exception:
        return None


def _houses_ruled_by(chart: dict, house: int) -> List[str]:
    """Which planet(s) lord a given house for this chart."""
    li = _lagna_index(chart)
    if li is None:
        return []
    return [_SIGN_LORD[(li + house - 1) % 12]]


def _houses_ruled(chart: dict, planet: str) -> List[int]:
    """Houses (1..12) whose sign this planet lords, counted from the lagna."""
    li = _lagna_index(chart)
    if li is None or not planet:
        return []
    out = []
    for h in range(1, 13):
        if _SIGN_LORD[(li + h - 1) % 12] == planet:
            out.append(h)
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
        # Planet nature alone is not the signal. This scored a Venus OPPOSITION
        # identically to a Venus trine, because both are Venus — so a day
        # carrying Venus opposite natal Jupiter on the 2nd at 0.1 degrees, and
        # Venus square natal Venus on the 11th, was reported as "money carries
        # tailwind, chase what you're owed". The aspect decides HOW the energy
        # arrives; a benefic by hard aspect is still friction, and every
        # tradition treats square and opposition as hard.
        if tp in _BENEFIC:
            planet_tone = +1.0
        elif tp in _MALEFIC:
            planet_tone = -1.0
        else:
            planet_tone = 0.0
        _asp = str(a.get("aspect") or "").strip().lower()
        harmony = {
            "trine": 1.0, "sextile": 0.7,
            "conjunction": 0.0,          # planet nature decides a conjunction
            "square": -0.8, "opposition": -1.0,
        }.get(_asp, 0.0)
        # Harmony leads, planet nature colours it. A benefic trine is fully
        # supportive; a benefic opposition is net friction; a malefic trine is
        # workable rather than harmful.
        tone = 0.7 * harmony + 0.3 * planet_tone
        # ASHTAKAVARGA — the classical filter for judging a transit. The same
        # planet crossing a sign with 7 bindus and one with 1 bindu are not the
        # same event: the first delivers, the second is largely inert. score_day
        # used NO ashtakavarga at all, so every transit was weighted purely on
        # aspect and planet nature, as if the natal chart had no opinion about
        # where that planet is standing. This is also what ties the transit back
        # to D-1: bindus are computed from the natal chart itself.
        av_mult = 1.0
        av_bindus = None
        try:
            from antar_engine.ashtakavarga import get_transit_strength
            tsi = a.get("transit_sign_index")
            if tsi is None:
                tsign = a.get("transit_sign")
                tsi = _SIGNS.index(tsign) if tsign in _SIGNS else None
            if tsi is not None:
                av = get_transit_strength(tp, int(tsi), chart) or {}
                av_mult = float(av.get("multiplier") or 1.0)
                av_bindus = av.get("bindus")
                a["av_bindus"] = av_bindus
                a["av_label"] = av.get("label")
        except Exception:
            av_mult = 1.0

        contrib = tone * strength * 0.6 * av_mult   # bounded transit weight
        layer_score += contrib
        for dom, wgt in _HOUSE_DOMAIN_WEIGHTS.get(natal_house, {"work": 1.0}).items():
            domain_bias[dom] += contrib * wgt

        # SPECULATION IS EXPOSURE, NOT INCOME. The 5th is the bet — the punt,
        # the position, the table. Money that arrives through it is money that
        # was first put AT RISK, so the 5th under any hard aspect reads as
        # exposure rather than gain. A benefic making the hard aspect is the
        # more dangerous case, not the safer one: it is what makes the bet feel
        # like a good idea. This is deliberately asymmetric — a supported 5th
        # adds nothing extra, because the upside is already counted above.
        # Affliction of the 5th, or of its LORD, is the speculation signature.
        # Two corrections to the first version of this rule:
        #
        #   A conjunction scored harmony 0.0, so `harmony < 0` never fired for a
        #   MALEFIC conjunct the 5th — which is the textbook affliction, not an
        #   edge case. Mars conjunct the 5th on 2 bindus is precisely "impulsive
        #   bet, no protection".
        #
        #   A house is afflicted through its LORD as much as through itself. The
        #   5th lord under a hard aspect to any money house carries the same
        #   meaning as a malefic sitting on the 5th.
        #
        # Weighted by how little ashtakavarga support the sign carries: low
        # bindus is where a malefic does real damage.
        _malefic_conj = (_asp == "conjunction" and tp in _MALEFIC)
        _fifth_lords = _houses_ruled_by(chart, _SPECULATION_HOUSE)
        _lord_hit = (tp in _fifth_lords or a.get("natal_planet") in _fifth_lords)
        if natal_house == _SPECULATION_HOUSE and (harmony < 0 or _malefic_conj):
            _sev = harmony if harmony < 0 else -1.0
            _thin = 1.0 + (0.5 if (av_bindus is not None and av_bindus <= 3) else 0.0)
            domain_bias["money"] += _sev * strength * 0.45 * _thin
        elif _lord_hit and harmony < 0 and natal_house in (2, 5, 8, 11, 12):
            domain_bias["money"] += harmony * strength * 0.35
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
    """Absolute bucketing. Kept for callers that want the raw reading."""
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


def _states_relative(today: Dict[str, float],
                     window: List[Dict[str, float]]) -> Dict[str, str]:
    """State of each domain TODAY, judged against this chart's own baseline.

    Absolute thresholds froze domains. The dasha stack contributes the same
    number every day for weeks, so if that constant alone cleared -0.25 the
    domain read CARE every single day — one chart returned money=CARE and
    mind=CARE on all fourteen days measured. A warning that never turns off is
    indistinguishable from no warning, and worse: the user acts on it once,
    sees nothing, and stops believing the card.

    So the question is no longer "is this number negative" but "is today
    unusual FOR THIS PERSON". The constant sits in both today's value and the
    window mean, and cancels. What survives is the part that actually moves —
    which is the part a daily reading is supposed to be about. It also makes
    every day distinct, because no two days carry the same transit arithmetic.

    Thresholds are in standard deviations of the chart's own 31-day spread:
    beyond 0.75 sigma is a real departure, and roughly a fifth of days qualify
    in each direction — close to how often something is actually worth saying.
    """
    out: Dict[str, str] = {}
    for dom in DOMAIN_SLOTS:
        vals = [w.get(dom, 0.0) for w in window] or [0.0]
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        sd = var ** 0.5
        v = today.get(dom, 0.0)
        if sd < 1e-6:
            # Genuinely flat for this chart across the window: nothing to say.
            out[dom] = STATE_STEADY
            continue
        z = (v - mean) / sd
        if z >= 0.75:
            out[dom] = STATE_FAVORABLE
        elif z <= -0.75:
            out[dom] = STATE_CAUTION
        else:
            out[dom] = STATE_STEADY
    return out


def _mark_volatile(states: Dict[str, str], push: Dict[str, float],
                   pull: Dict[str, float], window: List[Dict[str, float]]) -> Dict[str, str]:
    """Flag domains pulled hard in BOTH directions on the same day.

    Net bias hides this completely. A day with a strong affliction and a strong
    support nets to zero and reports "steady" — the one answer that is certainly
    wrong, because something IS going to happen, it simply could go either way.

    For money that distinction is the whole point: on a volatile day the correct
    advice is not "no big moves needed", it is "do not put money at risk today,
    because today is exactly when it cuts both ways".

    Threshold is scaled to the chart's own spread so it means the same thing for
    a busy chart and a quiet one.
    """
    out = dict(states)
    for dom in DOMAIN_SLOTS:
        vals = [w.get(dom, 0.0) for w in window] or [0.0]
        mean = sum(vals) / len(vals)
        sd = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
        if sd < 1e-6:
            continue
        p, q = push.get(dom, 0.0), abs(pull.get(dom, 0.0))
        # Both sides must be substantial in their own right, and comparable to
        # each other — one big signal with a rounding error is not volatility.
        # 0.6 sigma chosen by FIRING RATE, not by fitting a known day: measured
        # over 240 chart-days it flags 7.9% — roughly one day a fortnight, which
        # is what "today cuts both ways" should cost. 0.5 gives 10.4% (too
        # chatty for a special call), 0.8 gives 4.2% (too rare to be useful).
        if p >= 0.6 * sd and q >= 0.6 * sd and min(p, q) >= 0.45 * max(p, q):
            out[dom] = STATE_VOLATILE
    return out


def _coerce_date(x) -> _date:
    if isinstance(x, _date) and not isinstance(x, _dt):
        return x
    if isinstance(x, _dt):
        return x.date()
    if isinstance(x, str):
        return _date.fromisoformat(x[:10])
    return _date.today()


# Bias-only computation + cache, so the 31-day baseline window does not cost 31
# full score_day passes. Keyed on the chart's own geometry rather than identity,
# because callers rebuild the dict each request.
_BIAS_CACHE: Dict[tuple, Dict[str, float]] = {}
_BIAS_CACHE_MAX = 20000


def _chart_key(chart: dict) -> str:
    lg = (chart or {}).get("lagna") or {}
    pl = (chart or {}).get("planets") or {}
    sun = (pl.get("Sun") or {}).get("longitude")
    moon = (pl.get("Moon") or {}).get("longitude")
    return f"{lg.get('sign')}|{round(float(lg.get('degree') or 0), 3)}|{sun}|{moon}"


def _bias_for(chart: dict, d: _date, loc: dict) -> Dict[str, float]:
    ck = (_chart_key(chart), d.isoformat(),
          round(float((loc or {}).get("lat") or 0), 2),
          round(float((loc or {}).get("lng") or 0), 2))
    hit = _BIAS_CACHE.get(ck)
    if hit is not None:
        return hit
    bias = {dom: 0.0 for dom in DOMAIN_SLOTS}
    for layer in (_structural_layer(chart, d),
                  _transit_layer(chart, d),
                  _panchanga_layer(chart, d, loc)):
        for k, v in (layer.get("domains") or {}).items():
            if k in bias:
                bias[k] += v
    if len(_BIAS_CACHE) > _BIAS_CACHE_MAX:
        _BIAS_CACHE.clear()
    _BIAS_CACHE[ck] = bias
    return bias


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
    push = {dom: 0.0 for dom in DOMAIN_SLOTS}   # sum of supportive signals
    pull = {dom: 0.0 for dom in DOMAIN_SLOTS}   # sum of afflicting signals
    for layer in (structural, transit, panchanga):
        for k, v in (layer.get("domains") or {}).items():
            if k in bias:
                bias[k] += v
                if v >= 0:
                    push[k] += v
                else:
                    pull[k] += v

    # Judge each domain against this chart's own 31-day spread, so a constant
    # dasha contribution cannot pin a domain to CARE forever and every day
    # differs from its neighbours.
    try:
        window = [_bias_for(chart, d + _td(days=k), loc) for k in range(-15, 16)]
        states = _states_relative(bias, window)
        states = _mark_volatile(states, push, pull, window)
    except Exception:
        states = _states_from_bias(bias)

    return {
        "date":          d.isoformat(),
        "score":         _normalize_score(raw),
        "raw_score":     raw,
        "domain_states": states,
        "domain_states_absolute": _states_from_bias(bias),
        "domain_bias":   bias,
        "domain_push":   push,
        "domain_pull":   pull,
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
