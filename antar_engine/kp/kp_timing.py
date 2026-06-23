"""
kp_timing.py  —  Natal Vimsottari significator-period timing
============================================================

For DATED life events (not yes/no horary). KP doctrine: "the fruit of a house
is given during the conjoined dasha periods of the significators of that house."
We build the natal Vimsottari timeline from birth and check, at the date of a
known event, whether the running Mahadasha / Antardasha / Pratyantardasha lords
are significators of that event's favourable houses.

Used by kp_backtest's natal-timing gate AND (post-gate) by A5 intraday/timing.
Reuses kp_chart + kp_significators + the isolated Vimsottari calc in kp_horary.
Pure computation; no narration.

----------------------------------------------------------------------------
SIGNIFICATOR RULE (orthodox "strong" — the discriminating one)
----------------------------------------------------------------------------
The broad 4-level union makes almost every planet a significator of almost
every house (base rate ~0.9 -> no discrimination). The orthodox KP refinement,
used here as the DEFAULT, is Krishnamurti's primary tenet:

  A planet, in its dasha, delivers the houses of its STAR-LORD
  (the houses the star-lord OCCUPIES and OWNS), not the broad union.

On top of that:
  * NEGATION filter — a period lord counts for the matter only if it signifies
    the FAVOUR houses at least as much as the AGAINST (spoiler) houses.
  * CUSPAL-SUB-LORD gate — the sub-lord of the matter's primary cusp must itself
    be a net significator of the favour houses, else the matter is not promised.

`strong=False` falls back to the broad 4-level union (kept for comparison).

----------------------------------------------------------------------------
EVENT -> (PRIMARY CUSP, FAVOUR, AGAINST)
----------------------------------------------------------------------------
  marriage    cusp 7   favour {2,7,11}     against {1,6,10}
  childbirth  cusp 5   favour {2,5,11}     against {1,4,10}
  property    cusp 4   favour {4,11,12}    against {3,10}     (12=investment out)
  relocation  cusp 4   favour {3,4,12}     against {11}       (settling/away)
  job_change  cusp 6   favour {2,6,10,11}  against {5,9}      (5/9 = 12th-from-6/10)
  divorce     cusp 7   favour {1,6,10}     against {2,7,11}   (separative cluster)

  childbirth note: classical KP times the Nth child off the (5,7,9,...) chain
  (1st->5th, 2nd->7th). For the gate we score both births on the 5th cluster;
  the per-child house refinement is a documented follow-up.

STRICTNESS (reported separately so calibration is visible):
  'pd'     PD lord is a net significator                 (most permissive)
  'ad_pd'  AD and PD lords both net significators
  'any2'   >= 2 of {MD, AD, PD} net significators         (KP "conjoined")
"""

from .kp_chart import (  # noqa: F401  (compute_kp_chart re-exported for callers)
    compute_kp_chart, resolve_sublord, _assert_kp_ayanamsa,
)
from .kp_significators import build_significators, ALL_PLANETS, NODES

import swisseph as swe

# event -> primary cusp, favour houses, against (spoiler) houses
NATAL_EVENTS = {
    "marriage":   {"cusp": 7, "favour": {2, 7, 11},     "against": {1, 6, 10},
                   "label": "marriage"},
    "childbirth": {"cusp": 5, "favour": {2, 5, 11},     "against": {1, 4, 10},
                   "label": "child born"},
    "property":   {"cusp": 4, "favour": {4, 11, 12},    "against": {3, 10},
                   "label": "property bought"},
    "relocation": {"cusp": 4, "favour": {3, 4, 12},     "against": {11},
                   "label": "moved residence"},
    "job_change": {"cusp": 6, "favour": {2, 6, 10, 11}, "against": {5, 9},
                   "label": "job change"},
    "divorce":    {"cusp": 7, "favour": {1, 6, 10},     "against": {2, 7, 11},
                   "label": "divorce"},
    "separation": {"cusp": 7, "favour": {1, 6, 10},     "against": {2, 7, 11},
                   "label": "relationship ended"},
    "job_loss":   {"cusp": 10, "favour": {1, 5, 9},     "against": {2, 6, 10, 11},
                   "label": "job loss"},
    "business_start": {"cusp": 7, "favour": {2, 7, 10, 11}, "against": {5, 8, 12},
                       "label": "business started"},
    "speculation_loss": {"cusp": 5, "favour": {5, 8, 12}, "against": {2, 6, 11},
                         "label": "speculative loss"},
}

STRICTNESS = ("pd", "ad_pd", "any2")


# --------------------------------------------------------------------------
# House helpers
# --------------------------------------------------------------------------
def _occupied_house(chart, planet):
    return chart["planets"][planet].get("house")


def _owned_houses(chart, planet):
    """Houses whose cusp sign-lord is `planet` (nodes own no sign)."""
    if planet in NODES:
        return []
    return [h for h in range(1, 13)
            if chart["cusps"][h]["sign_lord"] == planet]


def _houses_of(chart, x):
    """Houses a planet 'stands for' by position + ownership (node agency added)."""
    hs = set()
    oh = _occupied_house(chart, x)
    if oh:
        hs.add(oh)
    hs |= set(_owned_houses(chart, x))
    if x in NODES:  # node also carries its dispositor's owned houses
        disp = chart["planets"][x]["sign_lord"]
        hs |= set(_owned_houses(chart, disp))
    return hs


def _sig_houses_strong(chart, planet):
    """
    Houses `planet` signifies = houses of its STAR-LORD (strongest, the
    discriminating link) PLUS the planet's OWN occupied + owned houses. This is
    the classic KP significator set for a planet; dropping the self-houses
    (star-lord only) wrongly strips a planet from a matter it directly owns or
    occupies (e.g. Venus from the 4th/home). The base-rate inflator we removed
    was the L1 'planets in the star of occupants' explosion — NOT self-houses.
    """
    sl = chart["planets"][planet]["star_lord"]
    return _houses_of(chart, sl) | _houses_of(chart, planet)


# --------------------------------------------------------------------------
# Significators
# --------------------------------------------------------------------------
def _net_positive(chart, planet, favour, against, strong=True):
    """True if `planet` is a net significator of favour (favour-hits >= against)."""
    if strong:
        hs = _sig_houses_strong(chart, planet)
    else:
        _, planet_sig = build_significators(chart)
        hs = set(planet_sig.get(planet, []))
    fav = favour & hs
    agn = against & hs
    return bool(fav) and (len(fav) >= len(agn))


def event_significators(chart, event_type, loss_house=None, strong=True):
    """Return (net_significator_set, favour_houses, against_houses, primary_cusp)."""
    if event_type == "loss" and loss_house is not None:
        favour = {(((loss_house - 1 + 11) % 12) + 1)}
        against = {loss_house}
        cusp = loss_house
    else:
        spec = NATAL_EVENTS.get(event_type)
        if spec is None:
            raise ValueError(f"unknown natal event_type {event_type!r}; "
                             f"known: {sorted(NATAL_EVENTS)} or 'loss'")
        favour, against, cusp = set(spec["favour"]), set(spec["against"]), spec["cusp"]
    sigs = {p for p in ALL_PLANETS
            if _net_positive(chart, p, favour, against, strong=strong)}
    return sigs, favour, against, cusp


def csl_gate(chart, event_type, loss_house=None, strong=True):
    """The matter's primary cuspal sub-lord must be a net significator of favour."""
    sigs, favour, against, cusp = event_significators(
        chart, event_type, loss_house, strong=strong)
    csl = chart["cusps"][cusp]["sub_lord"]
    return csl in sigs, csl


# --------------------------------------------------------------------------
# Vimsottari timeline
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Transit confirmation  (the base-rate collapser)
# --------------------------------------------------------------------------
# KP: the dasha says WHICH YEARS; transit of the slow planets over the stars/
# signs of the significators says WHICH MONTHS. We require Jupiter OR Saturn to
# transit a significator's star or sign, AND the Sun (the monthly trigger) to
# transit a significator's star. That conjunction is rare -> low base rate.
_TRANSIT_PLANETS = (("Sun", swe.SUN), ("Jupiter", swe.JUPITER),
                    ("Saturn", swe.SATURN))


def _transit_triples(jd):
    _assert_kp_ayanamsa()
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    out = {}
    for name, pid in _TRANSIT_PLANETS:
        vals, _ = swe.calc_ut(jd, pid, flags)
        out[name] = resolve_sublord(vals[0] % 360.0)
    return out


def transit_gate(jd, sigs):
    """
    True if a slow planet (Jupiter/Saturn) AND the Sun are transiting the star
    or sign of a significator. Returns (ok, detail).
    """
    tr = _transit_triples(jd)

    def agree(t):
        return (t["star_lord"] in sigs) or (t["sign_lord"] in sigs)

    jup, sat, sun = agree(tr["Jupiter"]), agree(tr["Saturn"]), agree(tr["Sun"])
    ok = (jup or sat) and sun
    return ok, {"jupiter": jup, "saturn": sat, "sun": sun}


def _combined_pass(periods, sigs, jd, strictness, require_transit):
    if not _passes(*lords_at(periods, jd), sigs, strictness):
        return False
    if require_transit:
        ok, _ = transit_gate(jd, sigs)
        if not ok:
            return False
    return True


def _date_to_jd(date_str):
    """'YYYY', 'YYYY-MM', or 'YYYY-MM-DD' -> Julian Day (UT, midday)."""
    parts = str(date_str).split("-")
    y = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 7
    d = int(parts[2]) if len(parts) > 2 else 15
    return swe.julday(y, m, d, 12.0)


def build_timeline(chart, through_jd):
    from .kp_horary import _vim_periods
    moon_lon = chart["planets"]["Moon"]["longitude"]
    birth_jd = chart["birth_jd"]
    span = max(through_jd - birth_jd + 400.0, 400.0)
    return _vim_periods(moon_lon, birth_jd, depth=3, span_jd=span)


def lords_at(periods, jd):
    md = ad = pd = None
    for level, lord, s, e in periods:
        if s <= jd < e:
            if level == 1:
                md = lord
            elif level == 2:
                ad = lord
            elif level == 3:
                pd = lord
    return md, ad, pd


def _passes(md, ad, pd, sigs, strictness):
    md_ok, ad_ok, pd_ok = (md in sigs), (ad in sigs), (pd in sigs)
    flags = [x in sigs for x in (md, ad, pd) if x is not None]
    if strictness == "pd":
        return pd_ok
    if strictness == "ad_pd":
        return ad_ok and pd_ok
    if strictness == "any2":
        return sum(flags) >= 2
    raise ValueError(strictness)


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------
def score_event(chart, event_type, actual_date, loss_house=None,
                tolerance_months=3, strong=True, require_csl=True,
                require_transit=True):
    """
    Score one dated event. hit = within +-tolerance_months there is a day where
    the dasha strictness holds AND (if require_transit) the transit gate fires,
    AND (if require_csl) the cuspal-sub-lord gate passes.
    """
    sigs, favour, against, cusp = event_significators(
        chart, event_type, loss_house, strong=strong)
    gate_ok, csl = csl_gate(chart, event_type, loss_house, strong=strong)

    actual_jd = _date_to_jd(actual_date)
    through = actual_jd + tolerance_months * 30.5 + 400.0
    periods = build_timeline(chart, through)
    md, ad, pd = lords_at(periods, actual_jd)

    tol_days = tolerance_months * 30.5
    hits = {}
    for strict in STRICTNESS:
        ok = False
        j = actual_jd - tol_days
        while j <= actual_jd + tol_days:
            if _combined_pass(periods, sigs, j, strict, require_transit):
                ok = True
                break
            j += 3.0  # 3-day step: Sun changes star ~every 13 days
        if require_csl:
            ok = ok and gate_ok
        hits[strict] = ok

    return {
        "event_type": event_type,
        "actual_date": actual_date,
        "favour_houses": sorted(favour),
        "against_houses": sorted(against),
        "primary_cusp": cusp,
        "cuspal_sub_lord": csl,
        "csl_gate_pass": gate_ok,
        "significators": sorted(sigs),
        "at_date": {"MD": md, "AD": ad, "PD": pd},
        "md_is_sig": md in sigs, "ad_is_sig": ad in sigs, "pd_is_sig": pd in sigs,
        "hits": hits,
    }


def next_window(chart, event_type, from_jd, loss_house=None, strictness="ad_pd",
                horizon_days=900, require_transit=True):
    """
    Forward-looking: the next date range (from `from_jd`) where the dasha
    strictness AND transit gate hold for this matter. Returns (start_jd, end_jd)
    or (None, None) if none within horizon. Used to answer 'when' on Ask.
    """
    sigs, _, _, _ = event_significators(chart, event_type, loss_house, strong=True)
    periods = build_timeline(chart, from_jd + horizon_days + 400.0)
    j = from_jd
    start = None
    while j <= from_jd + horizon_days:
        if _combined_pass(periods, sigs, j, strictness, require_transit):
            if start is None:
                start = j
            end = j
        elif start is not None:
            return start, end + 3.0
        j += 3.0
    if start is not None:
        return start, min(end + 3.0, from_jd + horizon_days)
    return None, None


def base_rate(chart, event_type, through_jd, loss_house=None, strictness="pd",
              strong=True, require_transit=True):
    """
    Fraction of MONTHS (birth..through) where the dasha strictness AND (if
    require_transit) the transit gate both hold. The number a real hit-rate must
    beat. Monthly sampling is uniform across the dasha+transit conjunction.
    """
    sigs, _, _, _ = event_significators(chart, event_type, loss_house, strong=strong)
    periods = build_timeline(chart, through_jd)
    birth_jd = chart["birth_jd"]
    if through_jd - birth_jd <= 0:
        return None
    months = 0
    passed = 0
    j = birth_jd
    while j <= through_jd:
        months += 1
        if _combined_pass(periods, sigs, j, strictness, require_transit):
            passed += 1
        j += 30.4375
    return (passed / months) if months else None
