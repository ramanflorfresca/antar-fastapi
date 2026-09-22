"""
kp_moment.py — KP state of the MOON (star / sub / sub-sub lord) plus the
planetary HORA at an arbitrary instant, for the speculation-timing shadow
logger (see Antar.world/KP_SPECULATION_TIMING_STUDY.md, Appendix A).

Reuses kp_chart (KP / Krishnamurti ayanamsa) so this agrees, to the arc-second,
with the horary engine already in production. NOTHING here reads or exposes a
verdict — it is pure ephemeris state for the shadow log.

Primary use:
  kp_moment(dt_utc, lat, lon, tz_offset, md_lord, ad_lord) -> dict
  sub_lord_boundaries(dt_utc_start, dt_utc_end, lat, lon) -> [datetime,...]

Both ayanamsas are reported (KP primary, Lahiri cross-check) because the study
pre-registers KP but records Lahiri so a boundary-sensitive result can be
audited against ayanamsa choice.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

try:
    import swisseph as swe
    _HAS_SWE = True
except Exception:                       # pragma: no cover
    _HAS_SWE = False

from .kp_chart import (
    resolve_sublord, VIM_ORDER, VIM_YEARS, VIM_TOTAL, NAK_SPAN, KP_AYANAMSA,
)

# Chaldean order (slowest -> fastest) — the sequence planetary hours run in.
_CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
# Python weekday (Mon=0 .. Sun=6) -> the day-lord = FIRST hora at sunrise.
_WEEKDAY_LORD = {0: "Moon", 1: "Mars", 2: "Mercury", 3: "Jupiter",
                 4: "Venus", 5: "Saturn", 6: "Sun"}

_MALEFIC = {"Saturn", "Mars", "Rahu", "Ketu", "Sun"}   # sub-lord risk flag
_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}


def _jd_utc(dt_utc: datetime) -> float:
    d = dt_utc.astimezone(timezone.utc) if dt_utc.tzinfo else dt_utc.replace(tzinfo=timezone.utc)
    ut = d.hour + d.minute / 60.0 + d.second / 3600.0
    return swe.julday(d.year, d.month, d.day, ut)


def _moon_longitude(dt_utc: datetime, sidmode) -> float:
    swe.set_sid_mode(sidmode)
    jd = _jd_utc(dt_utc)
    lon = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0]
    return float(lon) % 360.0


def _lords_from_longitude(lon: float) -> dict:
    """star / sub / sub-sub lord for a sidereal longitude (nakshatra-based
    Vimshottari subdivision — matches the KP horary sub table for star+sub;
    sub-sub is the standard nested proportion)."""
    lon = float(lon) % 360.0
    nak = int(lon // NAK_SPAN) % 27
    star_lord = VIM_ORDER[nak % 9]
    pos = lon - nak * NAK_SPAN                      # 0 .. NAK_SPAN
    # sub
    acc = 0.0
    i0 = VIM_ORDER.index(star_lord)
    sub_lord, sub_a, sub_b = star_lord, 0.0, NAK_SPAN
    for k in range(9):
        p = VIM_ORDER[(i0 + k) % 9]
        w = VIM_YEARS[p] / VIM_TOTAL * NAK_SPAN
        if acc <= pos < acc + w:
            sub_lord, sub_a, sub_b = p, acc, acc + w
            break
        acc += w
    # sub-sub (nested proportion inside the sub segment, starting at sub_lord)
    span = sub_b - sub_a
    posin = pos - sub_a
    acc2 = 0.0
    j0 = VIM_ORDER.index(sub_lord)
    sub_sub = sub_lord
    for k in range(9):
        p = VIM_ORDER[(j0 + k) % 9]
        w = VIM_YEARS[p] / VIM_TOTAL * span
        if acc2 <= posin < acc2 + w:
            sub_sub = p
            break
        acc2 += w
    return {"star_lord": star_lord, "sub_lord": sub_lord, "sub_sub_lord": sub_sub}


# ── planetary hora ──────────────────────────────────────────────────────────
def _sun_event(y, m, d, lat, lng, tz_offset, rise=True):
    """NOAA sunrise/sunset in LOCAL decimal hours (pure-python, no swe dep)."""
    N = datetime(y, m, d).timetuple().tm_yday
    lngHour = lng / 15.0
    t = N + ((6 if rise else 18) - lngHour) / 24.0
    M = (0.9856 * t) - 3.289
    L = (M + 1.916 * math.sin(math.radians(M))
         + 0.020 * math.sin(math.radians(2 * M)) + 282.634) % 360
    RA = math.degrees(math.atan(0.91764 * math.tan(math.radians(L)))) % 360
    RA += (math.floor(L / 90) * 90 - math.floor(RA / 90) * 90)
    RA /= 15.0
    sinDec = 0.39782 * math.sin(math.radians(L))
    cosDec = math.cos(math.asin(sinDec))
    cosH = ((math.cos(math.radians(90.833)) - sinDec * math.sin(math.radians(lat)))
            / (cosDec * math.cos(math.radians(lat))))
    if cosH > 1 or cosH < -1:
        return None
    H = ((360 - math.degrees(math.acos(cosH))) / 15.0 if rise
         else math.degrees(math.acos(cosH)) / 15.0)
    T = H + RA - (0.06571 * t) - 6.622
    return ((T - lngHour) % 24 + tz_offset) % 24


def hora_at(dt_local: datetime, lat: float, lng: float, tz_offset: float) -> dict:
    """The planetary hour (hora) lord at a LOCAL datetime."""
    def sr_ss(day):
        return (_sun_event(day.year, day.month, day.day, lat, lng, tz_offset, True),
                _sun_event(day.year, day.month, day.day, lat, lng, tz_offset, False))
    hr = dt_local.hour + dt_local.minute / 60.0 + dt_local.second / 3600.0
    today = dt_local.date()
    sr, ss = sr_ss(dt_local)
    if sr is None or ss is None:
        return {"hora_lord": None}
    if hr >= sr:
        hora_day = today
    else:
        prev = dt_local - timedelta(days=1)
        hora_day = prev.date()
        sr, ss = sr_ss(prev)
    # sunrise of the NEXT calendar day for the night span
    nxt = datetime(hora_day.year, hora_day.month, hora_day.day) + timedelta(days=1)
    sr_next, _ = sr_ss(nxt)
    # position within day or night
    # normalize hr onto a continuous [sr, sr_next+24) axis
    hr_c = hr if hr >= sr else hr + 24.0
    ss_c = ss if ss >= sr else ss + 24.0
    srn_c = (sr_next + 24.0) if sr_next is not None else (sr + 24.0)
    day_lord = _WEEKDAY_LORD[datetime(hora_day.year, hora_day.month, hora_day.day).weekday()]
    start = _CHALDEAN.index(day_lord)
    if hr_c < ss_c:                                  # daytime hora
        length = (ss_c - sr) / 12.0
        k = int((hr_c - sr) / length) if length > 0 else 0
        k = min(max(k, 0), 11)
    else:                                            # night hora
        length = (srn_c - ss_c) / 12.0
        k = 12 + (int((hr_c - ss_c) / length) if length > 0 else 0)
        k = min(max(k, 12), 23)
    lord = _CHALDEAN[(start + k) % 7]
    return {"hora_lord": lord, "hora_index": k + 1, "day_lord": day_lord}


# ── public API ──────────────────────────────────────────────────────────────
def kp_moment(dt_utc: datetime, lat: float, lng: float, tz_offset: float = 0.0,
              md_lord: str = None, ad_lord: str = None) -> dict:
    """Full KP Moon state + hora at an instant. Shadow-log payload only."""
    if not _HAS_SWE:
        return {"available": False, "reason": "swisseph unavailable"}
    out = {"available": True, "moment_utc": dt_utc.astimezone(timezone.utc).isoformat()
           if dt_utc.tzinfo else dt_utc.replace(tzinfo=timezone.utc).isoformat()}
    for label, sidmode in (("kp", KP_AYANAMSA), ("lahiri", swe.SIDM_LAHIRI)):
        lon = _moon_longitude(dt_utc, sidmode)
        lords = _lords_from_longitude(lon)
        blk = {"moon_longitude": round(lon, 4), **lords}
        if label == "kp":
            # authoritative star/sub from the KP sub table (agrees with horary)
            try:
                r = resolve_sublord(lon)
                blk["star_lord"] = r["star_lord"]
                blk["sub_lord"] = r["sub_lord"]
                blk["moon_sign"] = r["sign"]
                blk["moon_nakshatra"] = r["nakshatra"]
            except Exception:
                pass
        out[label] = blk
    swe.set_sid_mode(KP_AYANAMSA)                     # leave engine in KP mode
    dt_local = (dt_utc + timedelta(hours=tz_offset)) if dt_utc.tzinfo is None \
        else (dt_utc.astimezone(timezone.utc).replace(tzinfo=None) + timedelta(hours=tz_offset))
    out["hora"] = hora_at(dt_local, lat, lng, tz_offset)
    # dasha context + the key study flag: is the mind's sub-lord the dasha lord?
    out["md_lord"] = md_lord
    out["ad_lord"] = ad_lord
    _sub = out.get("kp", {}).get("sub_lord")
    out["is_dasha_sub"] = bool(md_lord and _sub and _sub == md_lord)
    out["sub_polarity"] = ("malefic" if _sub in _MALEFIC
                           else "benefic" if _sub in _BENEFIC else None)
    return out


def sub_lord_boundaries(dt_utc_start: datetime, dt_utc_end: datetime,
                        step_minutes: int = 3) -> list:
    """Timestamps (UTC) inside [start, end] where the Moon's KP sub_lord changes.
    Drives the per-sub-window slicing of a logged session. Coarse-step scan
    (Moon ~0.5 deg/hr, sub segments >= ~0.83 deg, so a 3-min step never skips a
    segment); returns the change instants, refined to the minute by bisection."""
    if not _HAS_SWE or dt_utc_end <= dt_utc_start:
        return []
    swe.set_sid_mode(KP_AYANAMSA)

    def sub_at(dt):
        return _lords_from_longitude(_moon_longitude(dt, KP_AYANAMSA))["sub_lord"]

    bounds = []
    step = timedelta(minutes=max(1, step_minutes))
    t = dt_utc_start
    prev_sub = sub_at(t)
    while t < dt_utc_end:
        t2 = min(t + step, dt_utc_end)
        s2 = sub_at(t2)
        if s2 != prev_sub:
            lo, hi = t, t2                            # bisect to ~1 min
            for _ in range(6):
                mid = lo + (hi - lo) / 2
                if sub_at(mid) == prev_sub:
                    lo = mid
                else:
                    hi = mid
            bounds.append(hi.replace(second=0, microsecond=0))
            prev_sub = s2
        t = t2
    return bounds


def allocate_windows(session_start_utc: datetime, session_end_utc: datetime,
                     checkpoints: list, lat: float, lng: float,
                     tz_offset: float = 0.0, md_lord: str = None,
                     ad_lord: str = None) -> list:
    """Slice a logged session into KP sub-lord windows and allocate the P&L
    between consecutive balance checkpoints across the windows they span
    (pro-rata by minutes). `checkpoints` = [{'at': datetime_utc, 'balance': float}, ...]
    sorted; the first is the buy-in, the last the cash-out. Returns a list of
    window dicts ready for the speculation_windows table."""
    # 1) boundary times = session bounds + sub-lord changes + checkpoint times
    subchanges = sub_lord_boundaries(session_start_utc, session_end_utc)
    cps = sorted([c for c in (checkpoints or []) if c.get("at")], key=lambda c: c["at"])
    marks = sorted(set([session_start_utc, session_end_utc]
                       + subchanges + [c["at"] for c in cps]))
    marks = [m for m in marks if session_start_utc <= m <= session_end_utc]

    # 2) balance as a function of time, piecewise-linear between checkpoints
    def balance_at(t):
        if not cps:
            return None
        if t <= cps[0]["at"]:
            return cps[0]["balance"]
        if t >= cps[-1]["at"]:
            return cps[-1]["balance"]
        for a, b in zip(cps, cps[1:]):
            if a["at"] <= t <= b["at"]:
                span = (b["at"] - a["at"]).total_seconds() or 1.0
                frac = (t - a["at"]).total_seconds() / span
                return a["balance"] + frac * (b["balance"] - a["balance"])
        return cps[-1]["balance"]

    windows = []
    for a, b in zip(marks, marks[1:]):
        if b <= a:
            continue
        mid = a + (b - a) / 2
        km = kp_moment(mid, lat, lng, tz_offset, md_lord, ad_lord)
        ba, bb = balance_at(a), balance_at(b)
        net = (bb - ba) if (ba is not None and bb is not None) else None
        minutes = round((b - a).total_seconds() / 60.0, 2)
        kp = km.get("kp", {})
        windows.append({
            "window_start": a.astimezone(timezone.utc).isoformat() if a.tzinfo else a.replace(tzinfo=timezone.utc).isoformat(),
            "window_end": b.astimezone(timezone.utc).isoformat() if b.tzinfo else b.replace(tzinfo=timezone.utc).isoformat(),
            "minutes": minutes,
            "sub_lord": kp.get("sub_lord"),
            "star_lord": kp.get("star_lord"),
            "sub_sub_lord": kp.get("sub_sub_lord"),
            "hora_lord": (km.get("hora") or {}).get("hora_lord"),
            "moon_sign": kp.get("moon_sign"),
            "moon_nakshatra": kp.get("moon_nakshatra"),
            "md_lord": md_lord, "ad_lord": ad_lord,
            "is_dasha_sub": km.get("is_dasha_sub"),
            "sub_polarity": km.get("sub_polarity"),
            "lahiri_sub_lord": (km.get("lahiri") or {}).get("sub_lord"),
            "net_units": (round(net, 4) if net is not None else None),
            "net_per_min": (round(net / minutes, 4) if (net is not None and minutes) else None),
        })
    return windows
