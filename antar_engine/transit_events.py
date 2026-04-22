"""
antar_engine/transit_events.py
==============================
Transit event engine — Day 2 of the Context-Packaging sprint.

Computes a deterministic list of transit events (sign ingresses,
nakshatra shifts, retrograde stations, natal aspect hits) for a
given natal chart over a date range.

Designed to be the single source of structured transit facts for:

  * monthly_deepdive.best_week / caution_week
  * monthly_deepdive.priority_actions (via natal-house aggregation)
  * annual_plan.peak_windows.<domain>.months
  * annual_plan.critical_dates

Pure compute — no LLM, no database, no HTTP.  Output is JSON-ready
dicts that slot directly into prompt context blocks.

Ayanamsa: Lahiri sidereal (``swe.SIDM_LAHIRI``) — matches
``transit_engine.py`` and the natal chart pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─── Swiss Ephemeris wiring ──────────────────────────────────────
try:
    import swisseph as swe
    _HAS_SWE = True
    swe.set_sid_mode(swe.SIDM_LAHIRI)
except Exception:   # pragma: no cover
    swe = None
    _HAS_SWE = False


# ─── Constants ──────────────────────────────────────────────────
SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
)

# Size of one nakshatra in degrees (13°20')
_NAK_DEG = 360.0 / 27.0

# Swiss Ephemeris planet IDs (populated only if swisseph is importable)
_PLANET_IDS: dict[str, int] = {}
_RAHU_ID: Optional[int] = None
if _HAS_SWE:
    _PLANET_IDS = {
        "Sun":     swe.SUN,
        "Moon":    swe.MOON,
        "Mars":    swe.MARS,
        "Mercury": swe.MERCURY,
        "Jupiter": swe.JUPITER,
        "Venus":   swe.VENUS,
        "Saturn":  swe.SATURN,
    }
    _RAHU_ID = swe.MEAN_NODE

# Default planet set for short ranges (monthly) vs long ranges (annual).
# Short range: everything moves slowly enough that all planet events matter.
# Long range: only slow planets (Mars, Jupiter, Saturn, Rahu, Ketu) because
# fast-planet ingresses (Moon daily, Mercury monthly) would drown out signal.
_SLOW_PLANETS = ("Mars", "Jupiter", "Saturn", "Rahu", "Ketu")
_ALL_PLANETS  = ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                 "Venus", "Saturn", "Rahu", "Ketu")

# Aspect angles (Vedic uses whole-sign aspects, but many engines also
# track classical conjunction/opposition/trine/square/sextile for events).
# We use tight orbs so the event list stays focused on meaningful hits.
_ASPECT_ANGLES: dict[str, int] = {
    "conjunction": 0,
    "sextile":     60,
    "square":      90,
    "trine":       120,
    "opposition":  180,
}

# Per-planet orb in degrees for aspect detection.  Slow planets get
# tighter orbs — they sit near an aspect for weeks otherwise.
_ASPECT_ORB: dict[str, float] = {
    "Sun":     2.0,
    "Moon":    3.0,
    "Mars":    1.5,
    "Mercury": 1.5,
    "Jupiter": 1.5,
    "Venus":   1.5,
    "Saturn":  1.0,
    "Rahu":    1.5,
    "Ketu":    1.5,
}


# ─── Data class ──────────────────────────────────────────────────
@dataclass
class TransitEvent:
    date:         str
    planet:       str
    event_type:   str
    detail:       str
    sign:         Optional[str] = None
    sign_prev:    Optional[str] = None
    nakshatra:    Optional[str] = None
    natal_house:  Optional[int] = None
    natal_target: Optional[str] = None
    aspect_kind:  Optional[str] = None
    orb:          Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ─── Helpers ────────────────────────────────────────────────────
def _julday(d: date) -> float:
    """Julian day at 00:00 UT on the given date."""
    return swe.julday(d.year, d.month, d.day, 0.0)


def _calc(planet: str, d: date) -> tuple[float, float]:
    """
    Return (sidereal_longitude_deg, speed_deg_per_day) for ``planet`` on date ``d``.

    Ketu is computed as Rahu + 180°.  Rahu uses mean node.
    """
    if not _HAS_SWE:
        raise RuntimeError(
            "swisseph not available — transit_events cannot compute positions"
        )
    jd = _julday(d)
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED

    if planet == "Ketu":
        rahu_lon, rahu_speed = _calc("Rahu", d)
        return ((rahu_lon + 180.0) % 360.0, rahu_speed)

    pid = _PLANET_IDS.get(planet)
    if pid is None and planet == "Rahu":
        pid = _RAHU_ID
    if pid is None:
        raise ValueError(f"Unknown planet: {planet}")

    res = swe.calc_ut(jd, pid, flags)
    lon   = float(res[0][0])
    speed = float(res[0][3])
    return (lon % 360.0, speed)


def _sign_of(lon: float) -> int:
    return int(lon // 30) % 12


def _nakshatra_of(lon: float) -> int:
    return int(lon // _NAK_DEG) % 27


def _natal_house_for(lon: float, lagna_sign_idx: int) -> int:
    """
    Whole-sign house of a transit planet given natal lagna.
    Returns 1-12.
    """
    sign_idx = _sign_of(lon)
    return ((sign_idx - lagna_sign_idx) % 12) + 1


def _aspect_orb(transit_lon: float, natal_lon: float, target_angle: int) -> float:
    """
    Absolute minimum orb to ``target_angle``, accounting for 360° wrap.
    Returns a non-negative number of degrees.
    """
    diff = (transit_lon - natal_lon) % 360.0
    # Distance to exact target (shortest way around the circle)
    d1 = abs(diff - target_angle)
    d2 = abs(diff - target_angle + 360.0)
    d3 = abs(diff - target_angle - 360.0)
    return min(d1, d2, d3)


def _extract_natal_positions(chart_data: dict) -> dict[str, float]:
    """
    Pull natal sidereal longitudes in degrees from chart_data.planets.
    Falls back to sign-midpoint if precise longitude is missing.
    Accepts either {planet: {longitude, sign}} or legacy {planet: {sign, degree_in_sign}}.
    """
    out: dict[str, float] = {}
    planets = chart_data.get("planets") or {}
    for name, p in planets.items():
        if not isinstance(p, dict):
            continue
        if p.get("longitude") is not None:
            out[name] = float(p["longitude"]) % 360.0
            continue
        # Reconstruct from sign + degree_in_sign if present
        sign_name = p.get("sign") or p.get("rashi")
        deg_in_sign = p.get("degree_in_sign") or p.get("degree") or 15.0
        if sign_name in SIGNS:
            sign_idx = SIGNS.index(sign_name)
            out[name] = (sign_idx * 30.0 + float(deg_in_sign)) % 360.0
    return out


def _extract_lagna_sign_idx(chart_data: dict) -> int:
    """Return the sign index (0-11) of the natal ascendant, defaulting to 0."""
    lagna = chart_data.get("lagna")
    if isinstance(lagna, dict):
        name = lagna.get("sign") or lagna.get("rashi")
        if name in SIGNS:
            return SIGNS.index(name)
    elif isinstance(lagna, str) and lagna in SIGNS:
        return SIGNS.index(lagna)
    # Fallback: derive from planets.Ascendant if present
    planets = chart_data.get("planets") or {}
    for key in ("Ascendant", "Lagna", "ASC"):
        p = planets.get(key)
        if isinstance(p, dict):
            name = p.get("sign") or p.get("rashi")
            if name in SIGNS:
                return SIGNS.index(name)
    return 0   # last-resort — lands transit houses against Aries


# ─── Public API ─────────────────────────────────────────────────
def compute_transit_events_in_range(
    chart_data: dict,
    start_date: date,
    end_date:   date,
    include_fast: Optional[bool] = None,
) -> list[dict]:
    """
    Compute a deterministic list of transit events between start_date
    and end_date (inclusive).

    ``include_fast`` controls whether Sun/Moon/Mercury/Venus are tracked.
    When None (default), auto-selects: True for ranges <= 40 days
    (monthly use case), False for longer ranges (annual).

    Returns a list of dicts sorted by date, each describing one event.
    Empty list if swisseph is not available or the range is invalid.
    """
    if not _HAS_SWE:
        logger.warning(
            "transit_events: swisseph not available — returning empty list"
        )
        return []

    if end_date < start_date:
        return []

    # Determine planet set
    span_days = (end_date - start_date).days
    if include_fast is None:
        include_fast = span_days <= 40
    planets = _ALL_PLANETS if include_fast else _SLOW_PLANETS

    # Chart-derived references
    natal_positions = _extract_natal_positions(chart_data)
    lagna_idx       = _extract_lagna_sign_idx(chart_data)

    events: list[TransitEvent] = []

    # Seed with previous-day state so we can detect transitions on day 0
    prev_state: dict[str, tuple[int, int, bool]] = {}
    seed_day = start_date - timedelta(days=1)
    for planet in planets:
        try:
            lon, speed = _calc(planet, seed_day)
        except Exception as err:
            logger.warning(f"transit_events: seed calc for {planet}: {err}")
            continue
        prev_state[planet] = (_sign_of(lon), _nakshatra_of(lon), speed < 0)

    # Track aspect-in-orb state so we emit 'aspect' events only on entry,
    # not every day the aspect lingers.
    aspect_active: dict[tuple[str, str, str], bool] = {}
    for planet in planets:
        try:
            lon, _ = _calc(planet, seed_day)
        except Exception:
            continue
        for natal_name, natal_lon in natal_positions.items():
            for kind, angle in _ASPECT_ANGLES.items():
                orb = _aspect_orb(lon, natal_lon, angle)
                aspect_active[(planet, natal_name, kind)] = (
                    orb <= _ASPECT_ORB.get(planet, 2.0)
                )

    # Day-by-day scan
    d = start_date
    while d <= end_date:
        for planet in planets:
            try:
                lon, speed = _calc(planet, d)
            except Exception as err:
                logger.warning(f"transit_events: calc {planet} {d}: {err}")
                continue

            sign_idx = _sign_of(lon)
            nak_idx  = _nakshatra_of(lon)
            retro    = (speed < 0) if planet != "Rahu" else True

            prev_sign, prev_nak, prev_retro = prev_state.get(
                planet, (sign_idx, nak_idx, retro)
            )

            nat_house = _natal_house_for(lon, lagna_idx)

            # Sign ingress
            if sign_idx != prev_sign:
                events.append(TransitEvent(
                    date=d.isoformat(),
                    planet=planet,
                    event_type="ingress",
                    detail=f"{planet} enters {SIGNS[sign_idx]}",
                    sign=SIGNS[sign_idx],
                    sign_prev=SIGNS[prev_sign],
                    natal_house=nat_house,
                ))

            # Nakshatra shift — emitted only for fast-range scans to keep
            # annual output manageable
            if include_fast and nak_idx != prev_nak:
                events.append(TransitEvent(
                    date=d.isoformat(),
                    planet=planet,
                    event_type="nakshatra_shift",
                    detail=f"{planet} enters nakshatra {NAKSHATRAS[nak_idx]}",
                    sign=SIGNS[sign_idx],
                    nakshatra=NAKSHATRAS[nak_idx],
                    natal_house=nat_house,
                ))

            # Retrograde stations (Rahu always retrograde; skip)
            if planet != "Rahu" and retro != prev_retro:
                events.append(TransitEvent(
                    date=d.isoformat(),
                    planet=planet,
                    event_type="retro_start" if retro else "retro_end",
                    detail=(
                        f"{planet} turns retrograde in {SIGNS[sign_idx]}"
                        if retro else
                        f"{planet} turns direct in {SIGNS[sign_idx]}"
                    ),
                    sign=SIGNS[sign_idx],
                    natal_house=nat_house,
                ))

            # Natal aspects — edge-triggered (fire on entry into orb)
            planet_orb = _ASPECT_ORB.get(planet, 2.0)
            for natal_name, natal_lon in natal_positions.items():
                for kind, angle in _ASPECT_ANGLES.items():
                    orb = _aspect_orb(lon, natal_lon, angle)
                    was_active = aspect_active.get(
                        (planet, natal_name, kind), False
                    )
                    is_active = orb <= planet_orb
                    if is_active and not was_active:
                        events.append(TransitEvent(
                            date=d.isoformat(),
                            planet=planet,
                            event_type="aspect",
                            detail=(
                                f"{planet} {kind} natal {natal_name} "
                                f"({orb:.1f}°)"
                            ),
                            sign=SIGNS[sign_idx],
                            natal_target=natal_name,
                            aspect_kind=kind,
                            orb=round(orb, 2),
                            natal_house=nat_house,
                        ))
                    aspect_active[(planet, natal_name, kind)] = is_active

            prev_state[planet] = (sign_idx, nak_idx, retro)

        d += timedelta(days=1)

    # Sort by date — primary key
    events.sort(key=lambda e: e.date)
    return [e.to_dict() for e in events]


# ─── Convenience: bucket events per week ────────────────────────
def bucket_events_by_week(
    events: list[dict],
    start_date: date,
) -> list[dict]:
    """
    Group a flat event list into Monday-start weeks.  Returns:
        [
          {
            "week_start": "2026-04-06",
            "week_end":   "2026-04-12",
            "week_label": "Week of April 6",
            "events":     [event_dict, ...],
          },
          ...
        ]

    Useful for feeding monthly_deepdive.best_week / caution_week.
    """
    if not events:
        return []

    # Anchor on the Monday of the week containing start_date
    anchor = start_date - timedelta(days=start_date.weekday())
    buckets: dict[str, dict] = {}

    for ev in events:
        try:
            ev_date = date.fromisoformat(ev["date"])
        except Exception:
            continue
        days_since_anchor = (ev_date - anchor).days
        week_idx = days_since_anchor // 7
        wk_start = anchor + timedelta(days=week_idx * 7)
        wk_end   = wk_start + timedelta(days=6)
        key = wk_start.isoformat()
        if key not in buckets:
            buckets[key] = {
                "week_start": key,
                "week_end":   wk_end.isoformat(),
                "week_label": f"Week of {wk_start.strftime('%B %-d')}",
                "events":     [],
            }
        buckets[key]["events"].append(ev)

    return [buckets[k] for k in sorted(buckets.keys())]


__all__ = [
    "compute_transit_events_in_range",
    "bucket_events_by_week",
    "TransitEvent",
    "SIGNS",
    "NAKSHATRAS",
]
