"""
Birth-time rectification — Phase A (back-calculation window). INTERNAL ONLY.

Not imported by any route, prompt or surface. It exists so we can answer, for a
chart whose birth time is uncertain: "given these dated life events, which
minutes of the day are dasha-legitimate?" — and, just as important, "how little
do the events actually narrow it down?".

Doctrine (from the platform rectification spec): dated events constrain the birth
moment; the birth moment must make every HARD dated event dasha-legitimate.
Houses are rooms, dasha is the clock. We never optimise for a "good" chart.

What Phase A does
  For every candidate birth minute in the source-quality window:
    1. sidereal lagna sign (whole-sign houses) and Moon longitude at that minute
    2. Vimshottari MD/AD at each anchor's date, from that Moon
    3. is the MD/AD lord inside the event's significator set (house lords of the
       lagna AT THAT MINUTE, natural karakas, Jaimini karakas)?
  A candidate survives only if EVERY hard anchor is explained. The surviving
  minutes, grouped into contiguous segments, are the window. If the anchors do
  not intersect we return a conflict report — never an average.

What Phase A does NOT do (Phase B, not built): navamsa / varshphal / countable
facts / KP layers, composite scoring, a single "best minute". It returns a window
and the conservative precision band the evidence can support, nothing finer.

Framework: whole-sign Parashari, explicit. No cusps, no KP sub-lords here.

Dasha arithmetic mirrors antar_engine/vimsottari.py (365.25-day years, balance
from the Moon's fraction of its nakshatra) so a window found here is the same
clock production uses. One known divergence: inside the FIRST (birth-balance)
mahadasha, production compresses antardashas into the remaining balance while
this module uses the classical full-length slices. Anchors in childhood only;
adult anchors are unaffected (see tests/test_rectify_window.py parity test).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from antar_engine.antar_ephemeris import (
    SIGNS, calculate_lagna, julian_day, lahiri_ayanamsa, planet_longitude,
    NAKSHATRA_LORDS, DASHA_YEARS, DASHA_ORDER,
)

# ── Inputs ────────────────────────────────────────────────────────────────────

# Starting half-window (minutes either side of the recorded time) by source.
SOURCE_HALF_WINDOW_MIN = {
    "hospital_record": 10,
    "family_memory": 30,
    "approximate": 60,
}

MIN_HARD_ANCHORS = 3

# Claimable precision floor by number of hard anchors (Phase A only: dasha
# consistency alone never supports better than navamsa level). The band we
# return is max(this floor, half-width of the surviving window).
BAND_FLOOR_MIN = {1: 30, 2: 20, 3: 13, 4: 13}
BAND_FLOOR_5PLUS_MIN = 5

TIER_HARD, TIER_SOFT, TIER_WEAK = "hard", "soft", "weak"

# Lords (planet owning each sign), sign index 0 = Aries.
SIGN_LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
              "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

# Event type → significators. `houses` are the PRIMARY houses (their lords count),
# `karakas` natural significators, `jaimini` keys into the 7-karaka scheme,
# `secondary_houses` / `secondary_karakas` count as significators too.
# Only events the spec names are here; anything else is reported as unsupported
# rather than guessed at.
EVENT_RULES = {
    "marriage": {
        "houses": [7], "karakas": ["Venus"], "jaimini": ["DK"],
        "secondary_houses": [2, 11], "secondary_karakas": ["Jupiter"],
    },
    "first_job": {
        "houses": [10], "karakas": ["Saturn", "Sun"], "jaimini": [],
        "secondary_houses": [6], "secondary_karakas": [],
    },
    "childbirth": {
        "houses": [5], "karakas": ["Jupiter"], "jaimini": ["PK"],
        "secondary_houses": [9], "secondary_karakas": [],
    },
    "property": {
        "houses": [4], "karakas": ["Mars", "Venus"], "jaimini": [],
        "secondary_houses": [11], "secondary_karakas": [],
    },
    "accident_surgery": {
        "houses": [8], "karakas": ["Mars"], "jaimini": [],
        "secondary_houses": [6], "secondary_karakas": ["Rahu"],
    },
    "death_father": {
        "houses": [9, 8], "karakas": ["Saturn"], "jaimini": [],
        "secondary_houses": [], "secondary_karakas": [],
    },
    "death_mother": {
        "houses": [4, 8], "karakas": ["Saturn"], "jaimini": [],
        "secondary_houses": [], "secondary_karakas": [],
    },
    "foreign_relocation": {
        "houses": [9, 12], "karakas": ["Rahu"], "jaimini": [],
        "secondary_houses": [3], "secondary_karakas": [],
    },
}

# Karaka order for Jaimini's 7-karaka scheme, highest degree-in-sign first.
_KARAKA_ORDER = ["AK", "AmK", "BK", "MK", "PK", "GK", "DK"]
_KARAKA_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

_YEAR_DAYS = 365.25
_NAK_SPAN = 360.0 / 27.0


# ── Event handling ────────────────────────────────────────────────────────────

def _parse_date_span(s: str) -> tuple[date, date]:
    """'YYYY-MM-DD' → (d, d); 'YYYY-MM' → whole month; 'YYYY' → whole year."""
    parts = [int(x) for x in s.split("-")]
    if len(parts) == 3:
        d = date(*parts)
        return d, d
    if len(parts) == 2:
        first = date(parts[0], parts[1], 1)
        nxt = date(parts[0] + (parts[1] == 12), parts[1] % 12 + 1, 1)
        return first, nxt - timedelta(days=1)
    return date(parts[0], 1, 1), date(parts[0], 12, 31)


def _sample_days(span: tuple[date, date], step: int = 4) -> list[date]:
    """Dates to test inside a month/year span (an anchor is explained if ANY
    day in its stated span is dasha-legitimate — the user's precision is the
    span, we do not pretend to know the day)."""
    lo, hi = span
    out, d = [], lo
    while d <= hi:
        out.append(d)
        d += timedelta(days=step)
    if out[-1] != hi:
        out.append(hi)
    return out


def normalise_events(events: list[dict]) -> dict:
    """Split caller events into usable anchors and a reasons-list of the rest.

    Event: {type, date, tier, id?, notes?}. `type` must be in EVENT_RULES to be
    usable; `tier` is hard/soft/weak. Only HARD events decide. A hard event whose
    date is year-only is demoted to soft (too wide to decide anything).
    """
    hard, soft, ignored = [], [], []
    for i, ev in enumerate(events):
        eid = ev.get("id") or f"{ev.get('type')}-{ev.get('date')}-{i}"
        etype, tier = ev.get("type"), ev.get("tier", TIER_WEAK)
        try:
            span = _parse_date_span(str(ev["date"]))
        except Exception:
            ignored.append({"id": eid, "reason": "unparseable date"})
            continue
        if etype not in EVENT_RULES:
            ignored.append({"id": eid, "reason": f"no significator rule for '{etype}'"})
            continue
        rec = {"id": eid, "type": etype, "span": span, "tier": tier}
        if tier == TIER_HARD and len(str(ev["date"]).split("-")) == 1:
            rec["tier"] = TIER_SOFT
            rec["demoted"] = "year-only date is too wide to be a hard anchor"
        (hard if rec["tier"] == TIER_HARD else soft).append(rec)
    return {"hard": hard, "soft": soft, "ignored": ignored}


# ── Chart pieces at one candidate minute ──────────────────────────────────────

def _sid(trop: float, jd: float) -> float:
    return (trop - lahiri_ayanamsa(jd)) % 360.0


def _lagna_sign_idx(jd: float, lat: float, lng: float) -> int:
    trop, _ = calculate_lagna(jd, lat, lng)
    return int(_sid(trop, jd) // 30) % 12


def _moon_sid(jd: float) -> float:
    return _sid(planet_longitude("Moon", jd), jd)


def _vimshottari_at(moon_lon: float, birth_jd: float, event_jd: float) -> tuple[str, str]:
    """(MD lord, AD lord) running at event_jd for a native born at birth_jd with
    the given sidereal Moon. Same arithmetic as antar_engine/vimsottari.py."""
    nak = int(moon_lon / _NAK_SPAN) % 27
    elapsed = (moon_lon - nak * _NAK_SPAN) / _NAK_SPAN
    start = DASHA_ORDER.index(NAKSHATRA_LORDS[nak])
    t = (event_jd - birth_jd) / _YEAR_DAYS          # years since birth
    # first MD runs only its remaining balance
    first_len = DASHA_YEARS[DASHA_ORDER[start]] * (1.0 - elapsed)
    md_start, i = 0.0, 0
    length = first_len
    while t >= md_start + length and i < 40:
        md_start += length
        i += 1
        length = float(DASHA_YEARS[DASHA_ORDER[(start + i) % 9]])
    md = DASHA_ORDER[(start + i) % 9]
    full = float(DASHA_YEARS[md])
    # Antardashas are proportional slices of the FULL mahadasha, beginning at its
    # true start (for the balance period that start precedes birth).
    true_md_start = md_start - (full - length) if i == 0 else md_start
    pos = t - true_md_start
    ad_idx = DASHA_ORDER.index(md)
    acc = 0.0
    for k in range(9):
        lord = DASHA_ORDER[(ad_idx + k) % 9]
        span = full * DASHA_YEARS[lord] / 120.0
        if pos < acc + span or k == 8:
            return md, lord
        acc += span
    return md, md  # unreachable


def _jaimini_karakas(planet_sid: dict[str, float]) -> dict[str, str]:
    """7-karaka scheme from degree-in-sign (Rahu/Ketu excluded)."""
    ranked = sorted(_KARAKA_PLANETS, key=lambda p: -(planet_sid[p] % 30.0))
    return dict(zip(_KARAKA_ORDER, ranked))


# Parashari graha drishti: house offsets counted from the planet's own sign
# (1 = same sign). Every planet sees the 7th; the three special aspects below.
_ASPECTS = {"Mars": (4, 7, 8), "Jupiter": (5, 7, 9), "Saturn": (3, 7, 10)}
_DEFAULT_ASPECT = (7,)

CONNECTION_STRICT = "strict"        # lords + karakas only (spec default)
CONNECTION_CONNECTED = "connected"  # + planets occupying / aspecting a primary house


def _connected_planets(house_sign: int, sign_of: dict[str, int]) -> set[str]:
    out = set()
    for p, sg in sign_of.items():
        if sg == house_sign:
            out.add(p)
            continue
        if p in ("Rahu", "Ketu"):
            offs = (7,)
        else:
            offs = _ASPECTS.get(p, _DEFAULT_ASPECT)
        if any((sg + o - 1) % 12 == house_sign for o in offs):
            out.add(p)
    return out


def _significators(rule: dict, lagna_idx: int, karakas: dict[str, str],
                   sign_of: Optional[dict[str, int]] = None,
                   connection: str = CONNECTION_STRICT) -> set[str]:
    def lord(h: int) -> str:
        return SIGN_LORDS[(lagna_idx + h - 1) % 12]
    s = {lord(h) for h in rule["houses"]} | set(rule["karakas"])
    s |= {karakas[k] for k in rule["jaimini"]}
    s |= {lord(h) for h in rule["secondary_houses"]} | set(rule["secondary_karakas"])
    if connection == CONNECTION_CONNECTED and sign_of:
        for h in rule["houses"]:
            s |= _connected_planets((lagna_idx + h - 1) % 12, sign_of)
    return s


def _anchor_score(rule, lagna_idx, karakas, birth_jd, moon_lon, days: list[date],
                  sign_of=None, connection: str = CONNECTION_STRICT) -> float:
    """1.0 full match (MD and AD both significators), 0.5 MD-only, else 0 — best
    over the sampled days of the anchor's stated span."""
    sig = _significators(rule, lagna_idx, karakas, sign_of, connection)
    best = 0.0
    for d in days:
        ejd = julian_day(d.year, d.month, d.day, 12.0 - 0.0)  # civil noon UT, day-level only
        md, ad = _vimshottari_at(moon_lon, birth_jd, ejd)
        sc = 1.0 if (md in sig and ad in sig) else (0.5 if md in sig else 0.0)
        if sc > best:
            best = sc
            if best == 1.0:
                break
    return best


# ── Phase A ───────────────────────────────────────────────────────────────────

def _band_floor(n_hard: int) -> int:
    return BAND_FLOOR_5PLUS_MIN if n_hard >= 5 else BAND_FLOOR_MIN.get(n_hard, 30)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def phase_a(birth: dict, events: list[dict], *, step_min: int = 1,
            half_window_min: Optional[int] = None,
            connection: str = CONNECTION_STRICT) -> dict:
    """Back-calculate the dasha-legitimate birth window.

    birth: {date 'YYYY-MM-DD', time 'HH:MM' (local), lat, lng, tz_offset(hours),
            source: hospital_record|family_memory|approximate}
    events: see normalise_events.

    Returns a dict with `status`:
      coarse_only  — fewer than MIN_HARD_ANCHORS hard anchors; only the
                     source-quality window is returned, no narrowing claimed
      conflict     — no minute explains every hard anchor; per-anchor feasible
                     sets and the pairwise empties are reported, nothing averaged
      window       — contiguous segments in which every hard anchor is explained,
                     with the (conservative) claimable band
    """
    src = birth.get("source", "approximate")
    half = half_window_min or SOURCE_HALF_WINDOW_MIN.get(src, 60)
    base = datetime.strptime(f"{birth['date']} {birth['time']}", "%Y-%m-%d %H:%M")
    lat, lng, tz = birth["lat"], birth["lng"], birth["tz_offset"]
    norm = normalise_events(events)
    hard = norm["hard"]
    out = {
        "framework": "whole-sign Parashari, Vimshottari",
        "significator_mode": connection,
        "recorded_time": _fmt(base), "source": src, "search_half_window_min": half,
        "hard_anchor_count": len(hard), "soft_anchor_count": len(norm["soft"]),
        "ignored_events": norm["ignored"],
        "demoted_events": [h for h in norm["soft"] if h.get("demoted")],
    }
    if len(hard) < MIN_HARD_ANCHORS:
        out.update(status="coarse_only",
                   window={"from": _fmt(base - timedelta(minutes=half)),
                           "to": _fmt(base + timedelta(minutes=half))},
                   reason=f"need >= {MIN_HARD_ANCHORS} hard anchors, have {len(hard)}; "
                          "no narrowing is claimed")
        return out

    # per-anchor sampled days, computed once
    days = {a["id"]: _sample_days(a["span"]) for a in hard}
    feasible: dict[str, list[int]] = {a["id"]: [] for a in hard}   # minute offsets
    half_ok: dict[str, list[int]] = {a["id"]: [] for a in hard}
    survivors: list[int] = []
    lagna_by_off: dict[int, int] = {}

    # Slow planets move < 0.1 degree inside a +-60 min window: compute once at the
    # recorded moment. Only the Moon (and the lagna) are recomputed per minute.
    jd0 = julian_day(base.year, base.month, base.day, base.hour + base.minute / 60.0 - tz)
    slow_sid = {p: _sid(planet_longitude(p, jd0), jd0) for p in _KARAKA_PLANETS if p != "Moon"}
    rahu0 = _sid(planet_longitude("Rahu", jd0), jd0)
    slow_sign = {p: int(v // 30) % 12 for p, v in slow_sid.items()}
    slow_sign["Rahu"], slow_sign["Ketu"] = int(rahu0 // 30) % 12, int(((rahu0 + 180) % 360) // 30) % 12

    for off in range(-half, half + 1, step_min):
        t = base + timedelta(minutes=off)
        ut = t.hour + t.minute / 60.0 - tz
        jd = julian_day(t.year, t.month, t.day, ut)
        lagna_idx = _lagna_sign_idx(jd, lat, lng)
        lagna_by_off[off] = lagna_idx
        moon = _moon_sid(jd)
        psid = dict(slow_sid)
        psid["Moon"] = moon
        karakas = _jaimini_karakas(psid)
        sign_of = dict(slow_sign)
        sign_of["Moon"] = int(moon // 30) % 12
        full_all = True
        for a in hard:
            sc = _anchor_score(EVENT_RULES[a["type"]], lagna_idx, karakas, jd, moon, days[a["id"]],
                              sign_of, connection)
            if sc == 1.0:
                feasible[a["id"]].append(off)
            if sc >= 0.5:
                half_ok[a["id"]].append(off)
            full_all = full_all and sc == 1.0
        if full_all:
            survivors.append(off)

    out["per_anchor"] = [{
        "id": a["id"], "type": a["type"],
        "explained_minutes": len(feasible[a["id"]]),
        "half_or_better_minutes": len(half_ok[a["id"]]),
        "of": len(range(-half, half + 1, step_min)),
        "segments": _segments(feasible[a["id"]], base, step_min),
    } for a in hard]
    out["lagna_signs_in_window"] = sorted({SIGNS[i] for i in lagna_by_off.values()})

    if not survivors:
        # Never average. Say which anchors cannot coexist.
        pair_empty = []
        for i in range(len(hard)):
            for j in range(i + 1, len(hard)):
                a, b = hard[i]["id"], hard[j]["id"]
                if not set(feasible[a]) & set(feasible[b]):
                    pair_empty.append([a, b])
        out.update(status="conflict", window=None, conflicting_pairs=pair_empty,
                   unexplainable_alone=[a["id"] for a in hard if not feasible[a["id"]]],
                   reason="no minute in the source window explains every hard anchor")
        return out

    segs = _segments(survivors, base, step_min)
    width = (survivors[-1] - survivors[0]) / 2.0
    floor = _band_floor(len(hard))
    out.update(
        status="window",
        window={"segments": segs, "from": segs[0]["from"], "to": segs[-1]["to"],
                "surviving_minutes": len(survivors),
                "of": len(range(-half, half + 1, step_min)),
                "narrowing_pct": round(100 * (1 - len(survivors) /
                                        len(range(-half, half + 1, step_min))), 1)},
        claimable_band_min=max(floor, round(width)),
        band_note=("Phase A is dasha-consistency only; the band is floored at "
                   f"+-{floor} min for {len(hard)} hard anchors."),
        validation_clause=("Working window only. Confirm against the next two "
                           "significant events; if they land in impossible "
                           "dashas, reopen."),
    )
    return out


def _segments(offsets: list[int], base: datetime, step: int) -> list[dict]:
    segs, start, prev = [], None, None
    for o in offsets:
        if start is None:
            start = prev = o
        elif o - prev <= step:
            prev = o
        else:
            segs.append((start, prev))
            start = prev = o
    if start is not None:
        segs.append((start, prev))
    return [{"from": _fmt(base + timedelta(minutes=a)),
             "to": _fmt(base + timedelta(minutes=b)),
             "minutes": b - a + step} for a, b in segs]
