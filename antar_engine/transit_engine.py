"""
transit_engine.py — Real-time transit computation using Swiss Ephemeris.

Computes where planets are in the sky RIGHT NOW and how they relate
to a user's natal chart positions. This is the "delivery boy" layer —
dashas open the window, transits deliver the event.
"""
import swisseph as swe
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Ayanamsa — must match what natal chart used (Lahiri)
swe.set_sid_mode(swe.SIDM_LAHIRI)

# Planet IDs in Swiss Ephemeris
SWE_PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
}

# Rahu = mean north node, Ketu = 180° opposite
SWE_RAHU = swe.MEAN_NODE

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Aspect orbs (degrees of tolerance)
ASPECT_ORBS = {
    "Sun": 15, "Moon": 12, "Mars": 8, "Mercury": 7,
    "Jupiter": 9, "Venus": 7, "Saturn": 9, "Rahu": 8, "Ketu": 8,
}

# Major aspect angles
ASPECTS = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    180: "opposition",
}


def get_current_transit_positions(date: datetime = None) -> Dict:
    # [lahiri-gate] get_current_transit_positions
    # V2.2 hard precondition for sidereal math. Soft mode so a
    # swisseph hiccup doesn't take /predict down.
    try:
        from antar_engine.lahiri_gate import ensure_lahiri_sid_mode
        ensure_lahiri_sid_mode()
    except Exception:
        pass
    """
    Compute sidereal positions of all planets for a given date/time.
    Returns dict: { "Sun": { "longitude": 45.23, "sign": "Taurus",
                              "sign_index": 1, "degree_in_sign": 15.23 }, ... }
    """
    if not date:
        date = datetime.utcnow()

    jd = swe.julday(date.year, date.month, date.day,
                     date.hour + date.minute / 60.0)

    positions = {}
    for name, pid in SWE_PLANETS.items():
        result = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL | swe.FLG_SPEED)
        lon = result[0][0]  # sidereal longitude
        sign_idx = int(lon / 30)
        deg_in_sign = lon % 30
        positions[name] = {
            "longitude": round(lon, 4),
            "sign": SIGNS[sign_idx],
            "sign_index": sign_idx,
            "degree_in_sign": round(deg_in_sign, 2),
            "speed": round(result[0][3], 4),  # daily speed
            "retrograde": result[0][3] < 0,
        }

    # Rahu (mean node)
    rahu_result = swe.calc_ut(jd, SWE_RAHU, swe.FLG_SIDEREAL)
    rahu_lon = rahu_result[0][0]
    rahu_sign_idx = int(rahu_lon / 30)
    positions["Rahu"] = {
        "longitude": round(rahu_lon, 4),
        "sign": SIGNS[rahu_sign_idx],
        "sign_index": rahu_sign_idx,
        "degree_in_sign": round(rahu_lon % 30, 2),
        "speed": round(rahu_result[0][3], 4),
        "retrograde": True,  # Rahu is always retrograde
    }

    # Ketu = 180° from Rahu
    ketu_lon = (rahu_lon + 180) % 360
    ketu_sign_idx = int(ketu_lon / 30)
    positions["Ketu"] = {
        "longitude": round(ketu_lon, 4),
        "sign": SIGNS[ketu_sign_idx],
        "sign_index": ketu_sign_idx,
        "degree_in_sign": round(ketu_lon % 30, 2),
        "speed": round(-rahu_result[0][3], 4),
        "retrograde": True,
    }

    return positions


def compute_transit_aspects(transit_positions: Dict, natal_positions: Dict) -> List[Dict]:
    """
    Find all aspects between current transiting planets and natal positions.
    Returns list of active aspects with orb and significance.
    """
    aspects = []

    for t_name, t_data in transit_positions.items():
        t_lon = t_data["longitude"]

        for n_name, n_data in natal_positions.items():
            if not isinstance(n_data, dict) or "longitude" not in n_data:
                continue

            n_lon = n_data["longitude"]

            # Calculate angular distance
            diff = abs(t_lon - n_lon)
            if diff > 180:
                diff = 360 - diff

            # Check each aspect angle
            for angle, aspect_name in ASPECTS.items():
                orb = ASPECT_ORBS.get(t_name, 8)
                if abs(diff - angle) <= orb:
                    strength = 1.0 - (abs(diff - angle) / orb)
                    aspects.append({
                        "transit_planet": t_name,
                        "natal_planet": n_name,
                        "aspect": aspect_name,
                        "exact_angle": round(diff, 2),
                        "orb": round(abs(diff - angle), 2),
                        "strength": round(strength, 2),
                        "transit_sign": t_data["sign"],
                        "natal_sign": n_data.get("sign", ""),
                        "natal_house": n_data.get("house", 0),
                        "transit_retrograde": t_data.get("retrograde", False),
                    })

    # Sort by strength (strongest first)
    aspects.sort(key=lambda x: -x["strength"])
    return aspects


def compute_transit_house_activation(transit_positions: Dict, natal_lagna_degree: float) -> Dict:
    """
    Determine which natal houses are activated by transiting planets.
    Returns dict: { 1: ["Jupiter"], 7: ["Saturn", "Rahu"], 10: ["Sun"] }
    """
    lagna_sign_idx = int(natal_lagna_degree / 30)
    house_activation = {i: [] for i in range(1, 13)}

    for name, data in transit_positions.items():
        t_sign_idx = data["sign_index"]
        # House = distance from lagna sign + 1
        house = ((t_sign_idx - lagna_sign_idx) % 12) + 1
        house_activation[house].append(name)

    # Remove empty houses
    return {h: planets for h, planets in house_activation.items() if planets}


def detect_major_transits(transit_positions: Dict, natal_positions: Dict,
                          natal_lagna_degree: float) -> List[Dict]:
    """
    Detect major life-affecting transits:
    - Saturn over natal Moon (Sade Sati)
    - Jupiter over natal lagna or 7th
    - Rahu/Ketu axis over natal Sun/Moon
    - Saturn return (Saturn over natal Saturn)
    """
    major = []
    lagna_sign_idx = int(natal_lagna_degree / 30)

    # Sade Sati check (Saturn within 1 sign of natal Moon)
    natal_moon = natal_positions.get("Moon", {})
    if natal_moon and isinstance(natal_moon, dict):
        moon_sign_idx = natal_moon.get("sign_index",
            SIGNS.index(natal_moon["sign"]) if natal_moon.get("sign") in SIGNS else -1)
        saturn_sign_idx = transit_positions.get("Saturn", {}).get("sign_index", -1)

        if moon_sign_idx >= 0 and saturn_sign_idx >= 0:
            dist = (saturn_sign_idx - moon_sign_idx) % 12
            if dist in (11, 0, 1):  # 12th, 1st, 2nd from Moon
                phase = {11: "rising", 0: "peak", 1: "setting"}[dist]
                major.append({
                    "type": "sade_sati",
                    "phase": phase,
                    "severity": "high" if dist == 0 else "moderate",
                    "description": f"Saturn transiting {'over' if dist == 0 else 'near'} your natal Moon — "
                                   f"emotional pressure and restructuring {'at peak' if dist == 0 else 'phase'}",
                    "affected_chakra": "Sacral",
                    "planet": "Saturn",
                })

    # Saturn return (Saturn over natal Saturn)
    natal_saturn = natal_positions.get("Saturn", {})
    if natal_saturn and isinstance(natal_saturn, dict):
        sat_natal_sign = natal_saturn.get("sign_index",
            SIGNS.index(natal_saturn["sign"]) if natal_saturn.get("sign") in SIGNS else -1)
        sat_transit_sign = transit_positions.get("Saturn", {}).get("sign_index", -1)
        if sat_natal_sign >= 0 and sat_natal_sign == sat_transit_sign:
            major.append({
                "type": "saturn_return",
                "severity": "high",
                "description": "Saturn returning to its natal position — major life restructuring cycle",
                "affected_chakra": "Third Eye",
                "planet": "Saturn",
            })

    # Jupiter over lagna (growth year)
    jup_sign = transit_positions.get("Jupiter", {}).get("sign_index", -1)
    if jup_sign == lagna_sign_idx:
        major.append({
            "type": "jupiter_lagna",
            "severity": "positive",
            "description": "Jupiter transiting your identity area — expansion, growth, new opportunities",
            "affected_chakra": "Crown",
            "planet": "Jupiter",
        })

    # Rahu/Ketu over natal Sun or Moon
    rahu_sign = transit_positions.get("Rahu", {}).get("sign_index", -1)
    ketu_sign = transit_positions.get("Ketu", {}).get("sign_index", -1)

    natal_sun = natal_positions.get("Sun", {})
    if natal_sun and isinstance(natal_sun, dict):
        sun_sign_idx = natal_sun.get("sign_index",
            SIGNS.index(natal_sun["sign"]) if natal_sun.get("sign") in SIGNS else -1)
        if rahu_sign == sun_sign_idx:
            major.append({
                "type": "rahu_sun",
                "severity": "high",
                "description": "Rahu transiting over natal Sun — identity crisis or breakthrough, ambition surge",
                "affected_chakra": "Solar Plexus",
                "planet": "Rahu",
            })
        if ketu_sign == sun_sign_idx:
            major.append({
                "type": "ketu_sun",
                "severity": "moderate",
                "description": "Ketu transiting over natal Sun — detachment from ego, spiritual growth",
                "affected_chakra": "Crown",
                "planet": "Ketu",
            })

    return major


def get_full_transit_report(chart_data: Dict, date: datetime = None) -> Dict:
    # [lahiri-gate] get_full_transit_report
    try:
        from antar_engine.lahiri_gate import ensure_lahiri_sid_mode
        ensure_lahiri_sid_mode()
    except Exception:
        pass
    """
    Complete transit analysis for a chart.
    Returns aspects, house activation, and major transit events.
    """
    natal_planets = chart_data.get("planets", {})
    lagna = chart_data.get("lagna", {})
    lagna_degree = lagna.get("degree", 0) if isinstance(lagna, dict) else 0

    transit_pos = get_current_transit_positions(date)
    aspects = compute_transit_aspects(transit_pos, natal_planets)
    houses = compute_transit_house_activation(transit_pos, lagna_degree)
    major = detect_major_transits(transit_pos, natal_planets, lagna_degree)

    # Top 5 strongest aspects
    top_aspects = aspects[:5]

    # Summary: which life areas are most activated
    HOUSE_LABELS = {
        1: "identity", 2: "wealth", 3: "courage", 4: "home",
        5: "creativity", 6: "work", 7: "partnerships", 8: "transformation",
        9: "luck", 10: "career", 11: "gains", 12: "foreign",
    }

    activated_areas = []
    for h, planets in houses.items():
        if any(p in ("Jupiter", "Saturn", "Rahu", "Ketu") for p in planets):
            activated_areas.append({
                "house": h,
                "area": HOUSE_LABELS.get(h, f"house {h}"),
                "planets": planets,
            })

    return {
        "date": (date or datetime.utcnow()).strftime("%Y-%m-%d"),
        "transit_positions": transit_pos,
        "top_aspects": top_aspects,
        "house_activation": houses,
        "major_transits": major,
        "activated_areas": activated_areas,
    }


def format_transit_for_prompt(transit_report: Dict) -> str:
    """
    Format transit data as a context block for Claude/DeepSeek prompts.
    """
    lines = ["CURRENT TRANSITS (live sky positions vs your natal chart):"]

    for aspect in transit_report.get("top_aspects", [])[:5]:
        tp = aspect["transit_planet"]
        np = aspect["natal_planet"]
        asp = aspect["aspect"]
        strength = aspect["strength"]
        lines.append(f"  {tp} in sky is in {asp} with your natal {np} "
                     f"(strength: {strength:.0%}, house {aspect.get('natal_house', '?')})")

    for mt in transit_report.get("major_transits", []):
        lines.append(f"  ** MAJOR: {mt['description']}")

    areas = transit_report.get("activated_areas", [])
    if areas:
        area_str = ", ".join(f"{a['area']} ({'+'.join(a['planets'])})" for a in areas[:4])
        lines.append(f"  Active life areas today: {area_str}")

    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════════════
# [rao-double-transit 2026-06-10] Stage-3 trigger layer — K.N. Rao double transit
# -----------------------------------------------------------------------------
# Dashas open the window (Stage 2); the double transit selects WHICH window
# delivered (Stage 3). An event fires only where transiting Jupiter AND Saturn
# both influence the event house / its lord (sign-level graha drishti).
# Sources: K.N. Rao double-transit research; "Ups and Downs in Career"; the
# 100-chart/100-navamsha marriage study. Pure functions — wired only by the
# event_convergence resolver, never directly by endpoints.
# ═════════════════════════════════════════════════════════════════════════════

# Sign-level graha drishti as 0-indexed sign offsets from the planet's sign.
# Jupiter: own + 5th + 7th + 9th. Saturn: own + 3rd + 7th + 10th.
# Mars (fine pass only): own + 4th + 7th + 8th.
GRAHA_DRISHTI_OFFSETS = {
    "Jupiter": (0, 4, 6, 8),
    "Saturn":  (0, 2, 6, 9),
    "Mars":    (0, 3, 6, 7),
}

_SWE_CHRONO_IDS = {
    "Jupiter": swe.JUPITER,
    "Saturn":  swe.SATURN,
    "Mars":    swe.MARS,
    "Moon":    swe.MOON,
}

# chronology cache: key -> {planet: [segment, ...]}
_CHRONO_CACHE: Dict = {}
_CHRONO_CACHE_MAX = 8


def graha_drishti_signs(planet: str, sign_index: int) -> frozenset:
    """Set of 0-indexed sign indices influenced by `planet` sitting in
    `sign_index` (occupation counts as influence). Unknown planet -> own+7th."""
    offsets = GRAHA_DRISHTI_OFFSETS.get(planet, (0, 6))
    return frozenset((sign_index + o) % 12 for o in offsets)


def _default_position_fn(jd: float, planet: str) -> float:
    """Sidereal longitude via Swiss Ephemeris (Lahiri). Raises on failure."""
    try:
        from antar_engine.lahiri_gate import ensure_lahiri_sid_mode
        ensure_lahiri_sid_mode()
    except Exception:
        pass
    pid = _SWE_CHRONO_IDS.get(planet)
    if pid is None:
        raise ValueError(f"unsupported chronology planet: {planet}")
    return swe.calc_ut(jd, pid, swe.FLG_SIDEREAL)[0][0]


def _date_to_jd(d: datetime) -> float:
    return swe.julday(d.year, d.month, d.day, 12.0)  # noon UT — sign-level


def _iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def build_transit_chronology(
    start_date: str,
    end_date: str,
    planets: Tuple[str, ...] = ("Jupiter", "Saturn"),
    step_days: int = 5,
    position_fn=None,
) -> Dict[str, List[Dict]]:
    """
    Precompute the sidereal sign occupancy timeline for slow planets across
    [start_date, end_date]. Returns:
        { "Jupiter": [ {"sign_index": 7, "start": "1990-01-01",
                        "end": "1990-08-14"}, ... ], ... }
    Segments are contiguous and day-resolution (boundaries bisected).
    Retrograde sign re-entries shorter than `step_days` may be folded into
    the surrounding segment — irrelevant at sign-level prediction.

    position_fn(jd, planet) -> sidereal longitude; injectable for tests.
    Cached per (planets, start, end, step) — build once at engine init,
    NEVER inside a per-candidate scoring loop.
    """
    key = (tuple(planets), str(start_date)[:10], str(end_date)[:10],
           int(step_days), position_fn is None)
    if key in _CHRONO_CACHE:
        return _CHRONO_CACHE[key]

    pf = position_fn or _default_position_fn
    try:
        s = datetime.strptime(str(start_date)[:10], "%Y-%m-%d")
        e = datetime.strptime(str(end_date)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return {p: [] for p in planets}
    if e <= s:
        return {p: [] for p in planets}

    out: Dict[str, List[Dict]] = {}
    for planet in planets:
        segments: List[Dict] = []
        cur = s
        try:
            cur_sign = int(pf(_date_to_jd(cur), planet) / 30) % 12
        except Exception:
            out[planet] = []
            continue
        seg_start = cur
        while cur < e:
            nxt = min(cur + timedelta(days=step_days), e)
            try:
                nxt_sign = int(pf(_date_to_jd(nxt), planet) / 30) % 12
            except Exception:
                nxt_sign = cur_sign
            if nxt_sign != cur_sign:
                # bisect the boundary to 1-day resolution
                lo, hi = cur, nxt
                while (hi - lo).days > 1:
                    mid = lo + (hi - lo) / 2
                    mid = datetime(mid.year, mid.month, mid.day)
                    if mid <= lo:
                        break
                    try:
                        mid_sign = int(pf(_date_to_jd(mid), planet) / 30) % 12
                    except Exception:
                        break
                    if mid_sign == cur_sign:
                        lo = mid
                    else:
                        hi = mid
                segments.append({"sign_index": cur_sign,
                                 "start": _iso(seg_start), "end": _iso(hi)})
                seg_start = hi
                cur_sign = nxt_sign
            cur = nxt
        segments.append({"sign_index": cur_sign,
                         "start": _iso(seg_start), "end": _iso(e)})
        out[planet] = segments

    if len(_CHRONO_CACHE) >= _CHRONO_CACHE_MAX:
        _CHRONO_CACHE.pop(next(iter(_CHRONO_CACHE)))
    _CHRONO_CACHE[key] = out
    return out


def sign_on_date(chronology: Dict, planet: str, date_iso: str) -> Optional[int]:
    """Sign index of `planet` on `date_iso` from a prebuilt chronology.
    None when the date falls outside the chronology span."""
    d = str(date_iso)[:10]
    for seg in chronology.get(planet, []):
        if seg["start"] <= d < seg["end"] or (seg["end"] == d == seg["start"]):
            return seg["sign_index"]
    # inclusive right edge of the final segment
    segs = chronology.get(planet, [])
    if segs and segs[-1]["start"] <= d <= segs[-1]["end"]:
        return segs[-1]["sign_index"]
    return None


def event_transit_targets(
    event_houses: List[int],
    lagna_sign_index: Optional[int],
    moon_sign_index: Optional[int],
    lord_sign_index: Optional[int] = None,
    d9_lord_sign_index: Optional[int] = None,
) -> Dict:
    """
    Build the Stage-3 target-sign set for an event:
      - event house sign judged from Lagna AND from Moon (Rao: never Moon-only,
        never Lagna-only — both reference points),
      - the event-house lord's natal sign,
      - the lord's D9 sign (marriage/children — Rao's navamsha research).
    Returns {"targets": set[int], "labels": {sign_index: [reason, ...]}}.
    """
    targets: set = set()
    labels: Dict[int, List[str]] = {}

    def _add(si, label):
        if si is None:
            return
        si = int(si) % 12
        targets.add(si)
        labels.setdefault(si, []).append(label)

    for h in event_houses or []:
        try:
            h = int(h)
        except (TypeError, ValueError):
            continue
        if lagna_sign_index is not None:
            _add((int(lagna_sign_index) + h - 1) % 12, f"house_{h}_from_lagna")
        if moon_sign_index is not None:
            _add((int(moon_sign_index) + h - 1) % 12, f"house_{h}_from_moon")
    _add(lord_sign_index, "event_lord_sign")
    _add(d9_lord_sign_index, "event_lord_d9_sign")
    return {"targets": targets, "labels": labels}


def double_transit_on_date(
    target_signs,
    date_iso: str,
    chronology: Dict,
    jupiter_solo: bool = False,
    saturn_solo: bool = False,
    require_jupiter_on: Optional[int] = None,
) -> Dict:
    """
    K.N. Rao double-transit check for one date.
      active = Jupiter influences a target AND Saturn influences a target.
    Functional-significator rule: when Jupiter (or Saturn) IS the chart's
    9th/10th lord, pass jupiter_solo / saturn_solo — that planet's influence
    alone qualifies. Auspicious refinement: require_jupiter_on = the event-
    house lord's sign; Jupiter must influence it (marriage/childbirth).
    Returns a trace dict (admin lock-trace shape — full jargon, never stripped).
    """
    tset = set(int(t) % 12 for t in (target_signs or []))
    j_sign = sign_on_date(chronology, "Jupiter", date_iso)
    s_sign = sign_on_date(chronology, "Saturn", date_iso)
    j_set = graha_drishti_signs("Jupiter", j_sign) if j_sign is not None else frozenset()
    s_set = graha_drishti_signs("Saturn", s_sign) if s_sign is not None else frozenset()
    j_hits = sorted(tset & j_set)
    s_hits = sorted(tset & s_set)
    active = bool(j_hits) and bool(s_hits)
    if not active:
        if jupiter_solo and j_hits:
            active = True
        if saturn_solo and s_hits:
            active = True
    if active and require_jupiter_on is not None:
        if int(require_jupiter_on) % 12 not in j_set:
            active = False
    return {
        "active": active,
        "jupiter_sign": j_sign,
        "saturn_sign": s_sign,
        "jupiter_targets_hit": j_hits,
        "saturn_targets_hit": s_hits,
        "jupiter_solo": jupiter_solo,
        "saturn_solo": saturn_solo,
        "jupiter_on_lord_required": require_jupiter_on is not None,
    }


def double_transit_windows(
    target_signs,
    chronology: Dict,
    from_date: str,
    to_date: str,
    jupiter_solo: bool = False,
    saturn_solo: bool = False,
    require_jupiter_on: Optional[int] = None,
    merge_gap_days: int = 0,
) -> List[Dict]:
    """
    All sub-intervals of [from_date, to_date] where the double transit is
    active on `target_signs`. Interval-intersection over the prebuilt
    chronology — NO per-day ephemeris calls. Adjacent qualifying intervals
    separated by <= merge_gap_days are merged.
    Returns [{"start", "end", "trace": <double_transit_on_date dict>}].
    """
    f = str(from_date)[:10]
    t = str(to_date)[:10]
    if not f or not t or t < f:
        return []
    # candidate boundary dates: union of segment edges within span
    edges = {f, t}
    for planet in ("Jupiter", "Saturn"):
        for seg in chronology.get(planet, []):
            for d in (seg["start"], seg["end"]):
                if f <= d <= t:
                    edges.add(d)
    cut = sorted(edges)
    windows: List[Dict] = []
    for i in range(len(cut) - 1):
        a, b = cut[i], cut[i + 1]
        if a == b:
            continue
        trace = double_transit_on_date(
            target_signs, a, chronology,
            jupiter_solo=jupiter_solo, saturn_solo=saturn_solo,
            require_jupiter_on=require_jupiter_on,
        )
        if not trace["active"]:
            continue
        if windows and _days_between(windows[-1]["end"], a) <= max(merge_gap_days, 0):
            windows[-1]["end"] = b
        else:
            windows.append({"start": a, "end": b, "trace": trace})
    return windows


def _days_between(a_iso: str, b_iso: str) -> int:
    try:
        a = datetime.strptime(a_iso[:10], "%Y-%m-%d")
        b = datetime.strptime(b_iso[:10], "%Y-%m-%d")
        return abs((b - a).days)
    except (ValueError, TypeError):
        return 10 ** 6


def mars_fine_windows(
    target_signs,
    from_date: str,
    to_date: str,
    position_fn=None,
    step_days: int = 3,
) -> List[Dict]:
    """
    Optional month-level fine trigger: sub-intervals inside a qualifying
    double-transit window where transiting MARS also influences a target.
    Build a Mars chronology only for the (short) window — cheap.
    """
    chrono = build_transit_chronology(
        from_date, to_date, planets=("Mars",), step_days=step_days,
        position_fn=position_fn,
    )
    tset = set(int(t) % 12 for t in (target_signs or []))
    out = []
    for seg in chrono.get("Mars", []):
        if graha_drishti_signs("Mars", seg["sign_index"]) & tset:
            out.append({"start": seg["start"], "end": seg["end"],
                        "mars_sign": seg["sign_index"]})
    return out


def _double_transit_smoke():
    """Synthetic-ephemeris test (runs without swisseph data): a fake provider
    moves Jupiter 1 sign/360d and Saturn 1 sign/900d; verifies segmentation,
    aspect math, and window intersection. Then, if real ephemeris available,
    spot-checks two known sidereal sign placements."""
    base = datetime(2000, 1, 1)

    def fake_pf(jd, planet):
        days = jd - swe.julday(2000, 1, 1, 12.0)
        rate = {"Jupiter": 30.0 / 360.0, "Saturn": 30.0 / 900.0,
                "Mars": 30.0 / 45.0}[planet]
        return (days * rate) % 360.0

    chrono = build_transit_chronology("2000-01-01", "2010-01-01",
                                      position_fn=fake_pf, step_days=5)
    js, ss = chrono["Jupiter"], chrono["Saturn"]
    assert len(js) >= 10, f"Jupiter segments {len(js)}"
    assert len(ss) >= 4, f"Saturn segments {len(ss)}"
    for segs in (js, ss):
        for i in range(len(segs) - 1):
            assert segs[i]["end"] == segs[i + 1]["start"], "non-contiguous"
            assert 0 <= segs[i]["sign_index"] <= 11
    # Jupiter sign changes ≈ every 360d
    d0 = datetime.strptime(js[0]["end"], "%Y-%m-%d")
    assert abs((d0 - base).days - 360) <= 6, f"Jup boundary {js[0]['end']}"
    # aspect sets
    assert graha_drishti_signs("Jupiter", 0) == frozenset({0, 4, 6, 8})
    assert graha_drishti_signs("Saturn", 0) == frozenset({0, 2, 6, 9})
    assert graha_drishti_signs("Mars", 0) == frozenset({0, 3, 6, 7})
    # on 2000-01-02 both at sign 0: targets {6} (7th from both) must be active
    tr = double_transit_on_date({6}, "2000-01-02", chrono)
    assert tr["active"], tr
    # target {1} — Jupiter at 0 doesn't aspect 1, Saturn doesn't either
    tr2 = double_transit_on_date({1}, "2000-01-02", chrono)
    assert not tr2["active"], tr2
    # solo rule: jupiter_solo qualifies on a Jupiter-only hit
    tr3 = double_transit_on_date({4}, "2000-01-02", chrono)          # Jup 5th
    assert not tr3["active"]
    tr4 = double_transit_on_date({4}, "2000-01-02", chrono, jupiter_solo=True)
    assert tr4["active"]
    # auspicious refinement: require Jupiter on sign 1 (not aspected) kills it
    tr5 = double_transit_on_date({6}, "2000-01-02", chrono,
                                 require_jupiter_on=1)
    assert not tr5["active"]
    # window intersection returns bounded, ordered windows
    wins = double_transit_windows({6}, chrono, "2000-01-01", "2005-01-01")
    assert wins and all(w["start"] < w["end"] for w in wins)
    for i in range(len(wins) - 1):
        assert wins[i]["end"] <= wins[i + 1]["start"]
    # event_transit_targets: both frames + lord + D9
    et = event_transit_targets([7], 0, 3, lord_sign_index=5,
                               d9_lord_sign_index=9)
    assert et["targets"] == {6, 9, 5}, et
    assert "house_7_from_lagna" in et["labels"][6]
    assert "house_7_from_moon" in et["labels"][9]
    print("[double-transit smoke] synthetic ephemeris: ALL PASS")

    # real-ephemeris spot checks (skipped cleanly if ephemeris unavailable)
    try:
        real = build_transit_chronology("2019-01-01", "2021-06-01")
        if not real.get("Saturn") or not real.get("Jupiter"):
            raise RuntimeError("empty chronology — ephemeris unavailable")
        sat_2020_03 = sign_on_date(real, "Saturn", "2020-03-15")
        jup_2020_01 = sign_on_date(real, "Jupiter", "2020-01-15")
        # Sidereal (Lahiri): Saturn entered Capricorn (9) late Jan 2020;
        # Jupiter in Sagittarius (8) in Jan 2020.
        assert sat_2020_03 == 9, f"Saturn 2020-03 sign {sat_2020_03} != 9"
        assert jup_2020_01 == 8, f"Jupiter 2020-01 sign {jup_2020_01} != 8"
        print("[double-transit smoke] real ephemeris spot-checks: PASS")
    except AssertionError:
        raise
    except Exception as e:
        print(f"[double-transit smoke] real ephemeris unavailable here ({e}) "
              "— synthetic suite passed; run on a machine with swisseph.")


if __name__ == "__main__" and "--double-transit-smoke" in __import__("sys").argv:
    _double_transit_smoke()
