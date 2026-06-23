"""
kp_chart.py  —  Agent 1: KP chart computation (foundation)
==========================================================

A SECOND, ISOLATED chart computation alongside the existing Lahiri/whole-sign
chart. Nothing here imports or mutates antar_engine.chart. KP uses:

  * Placidus house cusps   (Swiss Ephemeris house system 'P')
  * KP-Old / Krishnamurti ayanamsa  (swe.SIDM_KRISHNAMURTI)
  * the 249-segment sub division (Vimsottari proportions)

----------------------------------------------------------------------------
AUDITABLE DOCTRINAL CHOICES (change here, nowhere else)
----------------------------------------------------------------------------
  KP_AYANAMSA = swe.SIDM_KRISHNAMURTI
      "KP-Old" — the ayanamsa K.S. Krishnamurti published and used. Default in
      mainstream KP software (KPStarOne etc.), so published reference charts
      match it. Runs ~6 arc-minutes off Lahiri — exactly enough to shift a few
      sub-lord boundaries near cusps, which is the part that matters. (The
      "KP-New / 154-CHL" variant is a minority academic correction with far
      less published-chart coverage to verify against.)

  KP_NODE = swe.MEAN_NODE
      KP charts conventionally use the MEAN node for Rahu/Ketu. (The Lahiri
      base chart in antar_engine.chart uses TRUE_NODE — deliberately NOT shared,
      so the two systems stay independent.) Flip to swe.TRUE_NODE here if a
      reference set demands it.

----------------------------------------------------------------------------
THE 249 SUB DIVISION (verified construction)
----------------------------------------------------------------------------
  243 nakshatra-sub cells (27 nakshatras x 9 subs, Vimsottari-proportioned)
  + 6 sign-boundary splits (sign cuts that fall strictly inside a sub:
    30, 90, 150, 210, 270, 330 deg)
  = 249 canonical KP segments.
  build_sub_table() asserts this count at import.

Output of compute_kp_chart(): a clean significator-ready structure — for every
cusp (1..12) and every planet, the (sign_lord, star_lord, sub_lord) triple,
plus Placidus house occupancy. Consumed by kp_significators (A2) and
kp_horary (A3). No narration, no jargon-stripping here — pure computation.
"""

import os
import bisect
from datetime import datetime, timedelta

import swisseph as swe
try:
    import pytz
except Exception:  # pragma: no cover
    pytz = None

# --------------------------------------------------------------------------
# Ephemeris init (KP lives in antar_engine/kp/, ephe is at antar_engine/ephe)
# --------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_EPHE_PATH = os.path.join(_THIS_DIR, os.pardir, "ephe")
if os.path.isdir(_EPHE_PATH):
    swe.set_ephe_path(_EPHE_PATH)

# Auditable choices (see module docstring)
KP_AYANAMSA = swe.SIDM_KRISHNAMURTI
KP_NODE = swe.MEAN_NODE
HSYS = b"P"  # Placidus

# --------------------------------------------------------------------------
# Static tables
# --------------------------------------------------------------------------
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

SIGN_LORDS = [
    "Mars",      # Aries
    "Venus",     # Taurus
    "Mercury",   # Gemini
    "Moon",      # Cancer
    "Sun",       # Leo
    "Mercury",   # Virgo
    "Venus",     # Libra
    "Mars",      # Scorpio
    "Jupiter",   # Sagittarius
    "Saturn",    # Capricorn
    "Saturn",    # Aquarius
    "Jupiter",   # Pisces
]

NAKSHATRAS = [
    "Ashvini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

# Vimsottari order + dasha years (drives the unequal sub widths)
VIMSOTTARI = [
    ("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10), ("Mars", 7),
    ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17),
]
VIM_ORDER = [p for p, _ in VIMSOTTARI]
VIM_YEARS = {p: y for p, y in VIMSOTTARI}
VIM_TOTAL = 120.0

# Nakshatra lords cycle the Vimsottari order, repeating every 9 nakshatras.
NAKSHATRA_LORDS = [VIM_ORDER[i % 9] for i in range(27)]

NAK_SPAN = 360.0 / 27.0          # 13deg 20'
SIGN_SPAN = 30.0

# Swiss Ephemeris planet ids for the 7 classical grahas
_SWE_PLANET = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN,
}
PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                "Saturn", "Rahu", "Ketu"]


# --------------------------------------------------------------------------
# Ayanamsa discipline: assert before EVERY ephemeris call (mirrors the Lahiri
# SIDM_LAHIRI assertion discipline in the base engine — a stray set_sid_mode
# from another module must never poison a KP cusp).
# --------------------------------------------------------------------------
def _assert_kp_ayanamsa():
    swe.set_sid_mode(KP_AYANAMSA)


# --------------------------------------------------------------------------
# The 249-segment sub table (built once, asserted, cached)
# --------------------------------------------------------------------------
def build_sub_table():
    """
    Deterministic KP sub division.

    Returns (boundaries, segments):
      boundaries : sorted list of segment start-longitudes (len == n+1, last = 360)
      segments   : list of dicts, one per segment, each:
                   {start, end, sign, sign_lord, nakshatra, star_lord, sub_lord}

    243 nakshatra-sub cells, then split at the 6 interior sign boundaries that
    fall inside a sub -> 249 segments. Count is asserted.
    """
    # 1) raw 243 sub cells (start lord = nakshatra lord, proceed in Vim order)
    raw = []  # (start, end, star_idx, sub_lord)
    for n in range(27):
        star_lord = NAKSHATRA_LORDS[n]
        start_idx = VIM_ORDER.index(star_lord)
        pos = n * NAK_SPAN
        for s in range(9):
            sub_lord = VIM_ORDER[(start_idx + s) % 9]
            width = VIM_YEARS[sub_lord] / VIM_TOTAL * NAK_SPAN
            seg_start = pos
            seg_end = pos + width
            raw.append((seg_start, seg_end, n, sub_lord))
            pos = seg_end

    # snap the final boundary to exactly 360 (float drift guard)
    raw[-1] = (raw[-1][0], 360.0, raw[-1][2], raw[-1][3])

    # 2) overlay interior sign boundaries (30..330); split any sub they cross
    sign_cuts = [k * SIGN_SPAN for k in range(1, 12)]
    segments = []
    EPS = 1e-7
    for seg_start, seg_end, star_idx, sub_lord in raw:
        cut_points = [c for c in sign_cuts if seg_start + EPS < c < seg_end - EPS]
        lefts = [seg_start] + cut_points
        rights = cut_points + [seg_end]
        for a, b in zip(lefts, rights):
            mid = (a + b) / 2.0
            sign_idx = int(mid // SIGN_SPAN)
            segments.append({
                "start": a,
                "end": b,
                "sign": SIGNS[sign_idx],
                "sign_lord": SIGN_LORDS[sign_idx],
                "nakshatra": NAKSHATRAS[star_idx],
                "star_lord": NAKSHATRA_LORDS[star_idx],
                "sub_lord": sub_lord,
            })

    assert len(segments) == 249, (
        f"KP sub table built {len(segments)} segments, expected 249 "
        "(243 sub cells + 6 interior sign-cut splits)"
    )
    boundaries = [s["start"] for s in segments] + [360.0]
    return boundaries, segments


_SUB_BOUNDARIES, _SUB_SEGMENTS = build_sub_table()


# --------------------------------------------------------------------------
# Core: resolve a longitude to its (sign-lord, star-lord, sub-lord) triple
# --------------------------------------------------------------------------
def resolve_sublord(longitude):
    """
    Map an absolute sidereal longitude (KP ayanamsa, 0-360) to its KP triple.

    Returns:
      {longitude, sign, sign_index, deg_in_sign, sign_lord,
       nakshatra, nakshatra_index, star_lord, sub_lord}
    """
    lon = float(longitude) % 360.0
    # segment via binary search on start-boundaries
    i = bisect.bisect_right(_SUB_BOUNDARIES, lon) - 1
    if i < 0:
        i = 0
    if i >= len(_SUB_SEGMENTS):
        i = len(_SUB_SEGMENTS) - 1
    seg = _SUB_SEGMENTS[i]

    sign_index = int(lon // SIGN_SPAN)
    nak_index = int(lon // NAK_SPAN)
    if nak_index >= 27:
        nak_index = 26
    return {
        "longitude": lon,
        "sign": SIGNS[sign_index],
        "sign_index": sign_index,
        "deg_in_sign": lon - sign_index * SIGN_SPAN,
        "sign_lord": SIGN_LORDS[sign_index],
        "nakshatra": NAKSHATRAS[nak_index],
        "nakshatra_index": nak_index,
        "star_lord": seg["star_lord"],
        "sub_lord": seg["sub_lord"],
    }


# --------------------------------------------------------------------------
# Time -> Julian Day (UTC). Accepts decimal tz offset OR IANA name.
# --------------------------------------------------------------------------
def _to_julian_day_utc(birth_date, birth_time, tz_offset=None, timezone=None):
    bt = str(birth_time or "").strip()
    dt_local = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt_local = datetime.strptime(f"{birth_date} {bt}", fmt)
            break
        except ValueError:
            continue
    if dt_local is None:
        raise ValueError(f"birth_time {bt!r} not parseable as HH:MM or HH:MM:SS")

    if tz_offset is None:
        if timezone is not None and pytz is not None:
            try:
                tz = pytz.timezone(timezone)
                tz_offset = tz.utcoffset(dt_local).total_seconds() / 3600.0
            except Exception:
                tz_offset = 5.5
        else:
            raise ValueError("need tz_offset (hours) or timezone (IANA name)")

    dt_utc = dt_local - timedelta(hours=float(tz_offset))
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                    dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0)
    return jd, tz_offset


# --------------------------------------------------------------------------
# Planet sidereal longitudes (KP ayanamsa, mean node)
# --------------------------------------------------------------------------
def compute_planets(jd_utc):
    """Return {planet: {longitude, speed, retrograde, ...triple}} for 9 grahas."""
    _assert_kp_ayanamsa()
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    out = {}

    # classical 7
    for name, pid in _SWE_PLANET.items():
        vals, _ = swe.calc_ut(jd_utc, pid, flags)
        lon, speed = vals[0], vals[3]
        triple = resolve_sublord(lon)
        triple.update({"speed": speed, "retrograde": speed < 0})
        out[name] = triple

    # nodes (mean) — Rahu, Ketu always 180 apart; nodes are perpetually retro
    vals, _ = swe.calc_ut(jd_utc, KP_NODE, flags)
    rahu_lon, node_speed = vals[0], vals[3]
    ketu_lon = (rahu_lon + 180.0) % 360.0
    for name, lon in (("Rahu", rahu_lon), ("Ketu", ketu_lon)):
        triple = resolve_sublord(lon)
        triple.update({"speed": node_speed, "retrograde": True})
        out[name] = triple
    return out


# --------------------------------------------------------------------------
# Placidus cusps (KP ayanamsa) + cuspal sub-lords
# --------------------------------------------------------------------------
def compute_cusps(jd_utc, lat, lon):
    """
    Return {1..12: {longitude, ...triple}} using Placidus cusps under KP ayanamsa.
    cusps[i] is the START longitude of house i (KP bhava-as-cusp convention).
    """
    _assert_kp_ayanamsa()
    cusps, ascmc = swe.houses_ex(jd_utc, float(lat), float(lon), HSYS,
                                 swe.FLG_SIDEREAL)
    # pyswisseph returns the 12 cusps 0-indexed: house h -> cusps[h-1].
    out = {}
    for h in range(1, 13):
        cl = cusps[h - 1] % 360.0
        triple = resolve_sublord(cl)
        out[h] = triple
    return out, ascmc


def _house_of_longitude(lon, cusp_starts):
    """
    Placidus house occupancy: house h spans [cusp h, cusp h+1).
    cusp_starts: dict {1..12: start_longitude}. Returns 1..12.
    """
    lon = float(lon) % 360.0
    for h in range(1, 13):
        a = cusp_starts[h] % 360.0
        b = cusp_starts[1 if h == 12 else h + 1] % 360.0
        if a <= b:
            if a <= lon < b:
                return h
        else:  # wrap across 0deg
            if lon >= a or lon < b:
                return h
    return 1


# --------------------------------------------------------------------------
# Public: full KP chart
# --------------------------------------------------------------------------
def compute_kp_chart(birth_date, birth_time, lat, lon,
                     tz_offset=None, timezone=None):
    """
    Build the isolated KP chart.

    Returns:
      {
        "system": "KP",
        "ayanamsa": "KP-Old (Krishnamurti)",
        "node": "mean",
        "birth_jd": <float>,
        "ascendant": {longitude, ...triple},     # 1st cusp (lagna)
        "cusps": {1..12: {longitude, sign, sign_lord, nakshatra, star_lord,
                          sub_lord, ...}},
        "planets": {name: {longitude, speed, retrograde, house, sign, sign_lord,
                           nakshatra, star_lord, sub_lord, ...}},
        "meta": {...}
      }

    `house` on each planet is Placidus occupancy (1..12). Everything is pure
    deterministic computation — significator logic lives in kp_significators.
    """
    jd, tz_used = _to_julian_day_utc(birth_date, birth_time, tz_offset, timezone)

    cusps, ascmc = compute_cusps(jd, lat, lon)
    planets = compute_planets(jd)

    cusp_starts = {h: cusps[h]["longitude"] for h in range(1, 13)}
    for name, p in planets.items():
        p["house"] = _house_of_longitude(p["longitude"], cusp_starts)

    return {
        "system": "KP",
        "ayanamsa": "KP-Old (Krishnamurti)",
        "ayanamsa_value": round(swe.get_ayanamsa_ut(jd), 6),
        "node": "mean",
        "house_system": "Placidus",
        "birth_jd": jd,
        "tz_offset": tz_used,
        "ascendant": cusps[1],
        "cusps": cusps,
        "planets": planets,
        "meta": {
            "birth_date": birth_date,
            "birth_time": birth_time,
            "lat": float(lat),
            "lon": float(lon),
            "sub_segments": 249,
        },
    }


# --------------------------------------------------------------------------
# Self-test (run directly; needs the Swiss Ephemeris environment)
# --------------------------------------------------------------------------
if __name__ == "__main__":
    # table integrity (no ephemeris needed)
    print(f"sub segments: {len(_SUB_SEGMENTS)} (expect 249)")
    widths = sum(s["end"] - s["start"] for s in _SUB_SEGMENTS)
    print(f"total span: {widths:.6f} (expect 360.0)")

    # spot-check a known longitude resolution
    t = resolve_sublord(0.0)  # 0deg Aries = Ashvini, star lord Ketu, first sub Ketu
    print("0deg Aries ->", t["sign"], t["sign_lord"], "|",
          t["nakshatra"], "star", t["star_lord"], "sub", t["sub_lord"])

    # full chart (Delhi sample)
    try:
        chart = compute_kp_chart("1974-11-26", "11:59", 28.6139, 77.2090,
                                 tz_offset=5.5)
        asc = chart["ascendant"]
        print(f"\nASC {asc['longitude']:.3f} {asc['sign']} | "
              f"sign-lord {asc['sign_lord']} star {asc['star_lord']} "
              f"sub {asc['sub_lord']}")
        print("Cuspal sub-lords:")
        for h in range(1, 13):
            c = chart["cusps"][h]
            print(f"  H{h:>2}: {c['longitude']:7.3f} {c['sign']:<11} "
                  f"sub={c['sub_lord']}")
        print("Planets:")
        for name in PLANET_ORDER:
            p = chart["planets"][name]
            r = "R" if p["retrograde"] else " "
            print(f"  {name:<8}{r} H{p['house']:>2} {p['sign']:<11} "
                  f"star={p['star_lord']:<8} sub={p['sub_lord']}")
    except Exception as e:
        print(f"[ephemeris unavailable in this env: {e}]")
