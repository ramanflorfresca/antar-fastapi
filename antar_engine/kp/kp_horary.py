"""
kp_horary.py  —  Agent 3: Horary (Prashna) + Ruling Planets — the Ask engine
============================================================================

Number horary (KP 1-249) + Ruling Planets, casting the chart for the MOMENT of
the question. Produces a verdict (via kp_significators) plus a TIMED window.

Isolated: builds on kp_chart only. Uses a compact, self-contained Vimsottari
dasha calculator so it never imports the Lahiri-side dasha modules.

----------------------------------------------------------------------------
AUDITABLE DOCTRINAL CHOICES
----------------------------------------------------------------------------
  NUMBER -> ASCENDANT
    The querent gives 1-249. That selects the Nth of the 249 KP sub segments
    (zodiacal order). The segment MIDPOINT becomes the ascendant longitude; its
    sub-lord is the ascendant cuspal sub-lord (the crux of number horary).

  CUSPS
    House cusps 2-12 are taken from a Placidus computation at the moment & place
    of judgment (their relative arcs), re-anchored so cusp-1 = the number-derived
    ascendant. This keeps the number's ascendant authoritative while preserving
    realistic Placidus cusp spacing for the moment. (Both the number-asc and the
    moment-asc are exposed for audit.)

  PLANETS
    Computed for the MOMENT of the question (KP ayanamsa, mean node).

  RULING PLANETS (RP) — the confirmation/timing set, from the MOMENT chart:
    day-lord (weekday) + Moon (sign-lord, star-lord, sub-lord)
    + Lagna (sign-lord, star-lord, sub-lord of the moment's real ascendant).
    A node joins the RP set if its star-lord is already an RP (standard).

  TIMING
    Vimsottari from the Moon. A favourable window = the next dasha sub-period
    ruled by a planet that is BOTH a significator of the matter's favourable
    houses AND a Ruling Planet. Falls back to the running pratyantar window if
    none is found in the horizon.
    DAYS_PER_YEAR = 365.25 (recorded so timing is reproducible).
"""

from datetime import datetime, timezone as _tz

import swisseph as swe

from .kp_chart import (
    compute_planets, resolve_sublord, _assert_kp_ayanamsa, _to_julian_day_utc,
    _house_of_longitude, _SUB_SEGMENTS, HSYS,
    VIM_ORDER, VIM_YEARS, NAK_SPAN, NAKSHATRA_LORDS,
)
from .kp_significators import verdict, build_significators, ALL_PLANETS

DAYS_PER_YEAR = 365.25
WEEKDAY_LORDS = {  # Python weekday(): Mon=0 .. Sun=6
    0: "Moon", 1: "Mars", 2: "Mercury", 3: "Jupiter",
    4: "Venus", 5: "Saturn", 6: "Sun",
}


# --------------------------------------------------------------------------
# number 1-249 -> ascendant longitude (segment midpoint)
# --------------------------------------------------------------------------
def number_to_ascendant(number):
    if not (1 <= int(number) <= 249):
        raise ValueError("KP horary number must be 1..249")
    seg = _SUB_SEGMENTS[int(number) - 1]
    mid = (seg["start"] + seg["end"]) / 2.0
    return mid, seg


# --------------------------------------------------------------------------
# Ruling Planets at a moment
# --------------------------------------------------------------------------
def ruling_planets(jd_utc, lat, lon, weekday_index):
    """
    Return {'day_lord', 'moon':{...}, 'lagna':{...}, 'set':[unique planets]}.
    weekday_index is the LOCAL weekday at the question moment (Mon=0..Sun=6),
    with the KP day boundary at local sunrise left to the caller; we accept the
    civil weekday for the foundation build (documented limitation).
    """
    _assert_kp_ayanamsa()
    cusps, ascmc = swe.houses_ex(jd_utc, float(lat), float(lon), HSYS,
                                 swe.FLG_SIDEREAL)
    lagna = resolve_sublord(ascmc[0] % 360.0)

    planets = compute_planets(jd_utc)
    moon = planets["Moon"]

    day_lord = WEEKDAY_LORDS[weekday_index % 7]
    rp_set = []
    for cand in (day_lord,
                 moon["sign_lord"], moon["star_lord"], moon["sub_lord"],
                 lagna["sign_lord"], lagna["star_lord"], lagna["sub_lord"]):
        if cand not in rp_set:
            rp_set.append(cand)

    # node joins if its star-lord is already an RP
    for node in ("Rahu", "Ketu"):
        if planets[node]["star_lord"] in rp_set and node not in rp_set:
            rp_set.append(node)

    return {
        "day_lord": day_lord,
        "moon": {"sign_lord": moon["sign_lord"], "star_lord": moon["star_lord"],
                 "sub_lord": moon["sub_lord"]},
        "lagna": {"sign_lord": lagna["sign_lord"], "star_lord": lagna["star_lord"],
                  "sub_lord": lagna["sub_lord"]},
        "set": rp_set,
    }


# --------------------------------------------------------------------------
# Cast the horary chart (number-anchored asc, moment cusps + planets)
# --------------------------------------------------------------------------
def cast_horary(number, moment_dt_local, lat, lon, tz_offset):
    """
    moment_dt_local: naive local datetime of the question.
    Returns a kp_chart-shaped dict (system='KP-horary') + 'ruling_planets' +
    'number'/'number_ascendant'.
    """
    bd = moment_dt_local.strftime("%Y-%m-%d")
    bt = moment_dt_local.strftime("%H:%M:%S")
    jd, _ = _to_julian_day_utc(bd, bt, tz_offset=tz_offset)

    asc_lon, seg = number_to_ascendant(number)

    _assert_kp_ayanamsa()
    m_cusps, m_ascmc = swe.houses_ex(jd, float(lat), float(lon), HSYS,
                                     swe.FLG_SIDEREAL)
    moment_asc = m_ascmc[0] % 360.0

    # re-anchor cusps: preserve moment inter-cusp arcs, set cusp1 = asc_lon.
    # pyswisseph cusps are 0-indexed: house h -> m_cusps[h-1], cusp1 = m_cusps[0].
    cusps = {}
    for h in range(1, 13):
        arc = (m_cusps[h - 1] - m_cusps[0]) % 360.0
        cl = (asc_lon + arc) % 360.0
        cusps[h] = resolve_sublord(cl)

    planets = compute_planets(jd)
    cusp_starts = {h: cusps[h]["longitude"] for h in range(1, 13)}
    for name, p in planets.items():
        p["house"] = _house_of_longitude(p["longitude"], cusp_starts)

    rp = ruling_planets(jd, lat, lon, moment_dt_local.weekday())

    return {
        "system": "KP-horary",
        "ayanamsa": "KP-Old (Krishnamurti)",
        "node": "mean",
        "house_system": "Placidus (number-anchored)",
        "number": int(number),
        "number_ascendant": {"longitude": asc_lon, **seg},
        "moment_ascendant_longitude": moment_asc,
        "birth_jd": jd,
        "ascendant": cusps[1],
        "cusps": cusps,
        "planets": planets,
        "ruling_planets": rp,
    }


# --------------------------------------------------------------------------
# Compact, isolated Vimsottari dasha (Moon-based)
# --------------------------------------------------------------------------
def _vim_periods(moon_lon, ref_jd, depth=3, span_jd=None):
    """
    Yield (level, lord, start_jd, end_jd) for MD/AD/PD starting at ref_jd given
    the Moon longitude. depth: 1=MD,2=+AD,3=+PD. span_jd: stop after this many
    days past ref_jd (None = one full mahadasha chain pass).
    """
    nak_idx = int((moon_lon % 360.0) // NAK_SPAN)
    star_lord = NAKSHATRA_LORDS[nak_idx]
    portion = ((moon_lon % 360.0) - nak_idx * NAK_SPAN) / NAK_SPAN
    start_lord_idx = VIM_ORDER.index(star_lord)

    out = []
    md_start = ref_jd
    # first MD is the balance of the running mahadasha
    for k in range(9):
        lord = VIM_ORDER[(start_lord_idx + k) % 9]
        full_days = VIM_YEARS[lord] * DAYS_PER_YEAR
        md_days = full_days * (1.0 - portion) if k == 0 else full_days
        md_end = md_start + md_days
        out.append((1, lord, md_start, md_end))
        if depth >= 2:
            _expand_sub(out, lord, md_start, md_days, 2, depth)
        md_start = md_end
        if span_jd is not None and md_start - ref_jd > span_jd:
            break
    return out


def _expand_sub(out, parent_lord, parent_start, parent_days, level, depth):
    idx = VIM_ORDER.index(parent_lord)
    s = parent_start
    for k in range(9):
        lord = VIM_ORDER[(idx + k) % 9]
        days = parent_days * (VIM_YEARS[lord] / 120.0)
        e = s + days
        out.append((level, lord, s, e))
        if depth > level:
            _expand_sub(out, lord, s, days, level + 1, depth)
        s = e


def _jd_to_date(jd):
    y, m, d, h = swe.revjul(jd)
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


# --------------------------------------------------------------------------
# Timing: next favourable window
# --------------------------------------------------------------------------
def timed_window(chart, question_type, ruling, horizon_days=540, loss_house=None):
    """
    Find the next dasha sub-period (AD or PD) ruled by a planet that is BOTH a
    significator of the matter's favourable houses AND a Ruling Planet.
    Returns {start, end, basis} or a running-period fallback.
    """
    from .kp_significators import QUESTION_TYPES
    if question_type == "loss":
        favour = {(((loss_house - 1 + 11) % 12) + 1)} if loss_house else set()
    else:
        favour = set(QUESTION_TYPES.get(question_type, {}).get("favour", []))

    _, planet_sig = build_significators(chart)
    fav_significators = {p for p in ALL_PLANETS if favour & set(planet_sig.get(p, []))}
    rp_set = set(ruling.get("set", []))
    target_planets = fav_significators & rp_set

    moon_lon = chart["planets"]["Moon"]["longitude"]
    ref_jd = chart["birth_jd"]
    periods = _vim_periods(moon_lon, ref_jd, depth=3, span_jd=horizon_days)

    # prefer PD (level 3), then AD (level 2), that is a target planet
    for want_level in (3, 2):
        for level, lord, s, e in periods:
            if level == want_level and lord in target_planets:
                if s - ref_jd <= horizon_days:
                    return {"start": _jd_to_date(s), "end": _jd_to_date(e),
                            "basis": "favourable-significator + ruling-planet",
                            "ruler_ok": True}

    # fallback: the running pratyantar window
    running_pd = next((p for p in periods if p[0] == 3 and p[2] <= ref_jd < p[3]),
                      None)
    if running_pd:
        _, _, s, e = running_pd
        return {"start": _jd_to_date(s), "end": _jd_to_date(e),
                "basis": "running-period (no ruling-planet confirmation found)",
                "ruler_ok": False}
    return {"start": None, "end": None,
            "basis": "no window in horizon", "ruler_ok": False}


# --------------------------------------------------------------------------
# Public: answer a horary question
# --------------------------------------------------------------------------
def answer_horary(number, question_type, moment_dt_local, lat, lon, tz_offset,
                  loss_house=None, horizon_days=540):
    """
    Full Ask-engine result: verdict bundle + timed window + RP set.

    Returns:
      {
        "verdict": "yes"|"no"|"conditional",
        "confidence": 0-3,
        "drivers": [jargon-free, ...],
        "window": {start, end, basis, ruler_ok},
        "ruling_planets": {...},      # internal/audit
        "debug": {...}                # internal/audit
      }
    NOTE: still raw — user-facing strips + narration happen in A5 (post-gate).
    """
    chart = cast_horary(number, moment_dt_local, lat, lon, tz_offset)
    v = verdict(chart, question_type, loss_house=loss_house)
    win = timed_window(chart, question_type, chart["ruling_planets"],
                       horizon_days=horizon_days, loss_house=loss_house)
    return {
        "verdict": v["verdict"],
        "confidence": v["confidence"],
        "drivers": v["drivers"],
        "window": win,
        "ruling_planets": chart["ruling_planets"],
        "debug": {**v["debug"], "number": int(number),
                  "number_asc_sub_lord": chart["number_ascendant"]["sub_lord"]},
    }


if __name__ == "__main__":
    try:
        now = datetime(2026, 6, 23, 14, 30, 0)
        res = answer_horary(74, "gain", now, 28.6139, 77.2090, tz_offset=5.5)
        print("verdict:", res["verdict"], "conf:", res["confidence"])
        print("drivers:", res["drivers"])
        print("window:", res["window"])
        print("RP set:", res["ruling_planets"]["set"])
    except Exception as e:
        print(f"[ephemeris unavailable in this env: {e}]")
