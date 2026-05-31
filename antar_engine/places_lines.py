"""
antar_engine/places_lines.py
─────────────────────────────────────────────────────────────────────────────
PLACES (Astrocartography) — line projection math.  Phase 1.

Computes the geographic polylines where each natal planet sits on each of the
four chart angles (AC / MC / DC / IC) at the moment of birth.

Coordinate system
    SIDEREAL, Lahiri ayanamsa (Antar is sidereal Vedic, never tropical).
    Planet ecliptic longitudes are taken from the stored natal chart so the
    lines stay perfectly consistent with the rest of the engine; the local
    ASC / MC at each geographic point is computed with swe.houses_ex under
    FLG_SIDEREAL + SIDM_LAHIRI.

Output
    36 lines = 9 planets (Sun..Ketu) x 4 angles.
    Each line carries a 121-point polyline sampled at 1 deg latitude from
    -60 deg to +60 deg.  Each point is [lat, lon].

    MC line : longitude where the planet culminates (on the upper meridian).
              Latitude-independent -> vertical line (lon constant).
    IC line : MC longitude + 180 deg (lower meridian).  Vertical.
    AC line : longitude where the planet is rising.  Varies with latitude.
    DC line : longitude where the planet is setting.  Varies with latitude.

Beyond +-60 deg latitude the rising/setting math degrades, so we clip there.
"""

from __future__ import annotations

import math
from typing import Optional

try:
    import swisseph as swe
    _SWE_AVAILABLE = True
except Exception:                                       # pragma: no cover
    swe = None
    _SWE_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# 9-planet sidereal Vedic set (no Uranus / Neptune / Pluto).
PLANETS: list[str] = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter",
    "Venus", "Saturn", "Rahu", "Ketu",
]

ANGLES: list[str] = ["AC", "MC", "DC", "IC"]

# Swiss Ephemeris planet ids — used only as a fallback when the chart does not
# carry a stored longitude for a body.  Rahu uses the mean node (matches the
# rest of the Antar engine); Ketu is derived as Rahu + 180.
_PLANET_IDS = {
    "Sun":     0,   # swe.SUN
    "Moon":    1,   # swe.MOON
    "Mercury": 2,   # swe.MERCURY
    "Venus":   3,   # swe.VENUS
    "Mars":    4,   # swe.MARS
    "Jupiter": 5,   # swe.JUPITER
    "Saturn":  6,   # swe.SATURN
    "Rahu":    10,  # swe.MEAN_NODE
}

# Polyline sampling: 1 deg latitude resolution, -60 .. +60 -> 121 points.
LAT_MIN = -60.0
LAT_MAX = 60.0
LAT_STEP = 1.0
SAMPLE_LATITUDES: list[float] = [
    LAT_MIN + i * LAT_STEP for i in range(int((LAT_MAX - LAT_MIN) / LAT_STEP) + 1)
]  # 121 entries

# Longitude sweep resolution for root-finding the ASC/MC crossings.
_LON_STEP = 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Small angle helpers
# ─────────────────────────────────────────────────────────────────────────────

def _norm360(x: float) -> float:
    return x % 360.0


def _norm180(x: float) -> float:
    """Wrap a longitude into (-180, 180]."""
    x = (x + 180.0) % 360.0 - 180.0
    return 180.0 if x == -180.0 else x


def _ensure_swe_sidereal() -> None:
    swe.set_sid_mode(swe.SIDM_LAHIRI)


def _planet_longitudes(birth_jd: float, chart: Optional[dict]) -> dict[str, float]:
    """
    Sidereal ecliptic longitudes for the 9 bodies.

    Preference order:
      1. The stored natal chart (chart_data['planets'][P]['longitude']) so the
         lines match the chart the rest of Antar reasons about.
      2. Recompute with Swiss Ephemeris (sidereal Lahiri) as a fallback.
    """
    out: dict[str, float] = {}
    planets = (chart or {}).get("planets", {}) if chart else {}

    for name in PLANETS:
        lon = None
        p = planets.get(name)
        if isinstance(p, dict):
            lon = p.get("longitude")
            if lon is None:
                lon = p.get("lon")
        if lon is not None:
            try:
                out[name] = _norm360(float(lon))
                continue
            except (TypeError, ValueError):
                pass

        # Fallback: compute from ephemeris.
        if not _SWE_AVAILABLE or birth_jd is None:
            continue
        _ensure_swe_sidereal()
        flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
        if name == "Ketu":
            rahu = out.get("Rahu")
            if rahu is None:
                res = swe.calc_ut(birth_jd, _PLANET_IDS["Rahu"], flags)
                rahu = _norm360(res[0][0])
            out["Ketu"] = _norm360(rahu + 180.0)
        else:
            res = swe.calc_ut(birth_jd, _PLANET_IDS[name], flags)
            out[name] = _norm360(res[0][0])

    # Derive Ketu from Rahu if it is still missing.
    if "Ketu" not in out and "Rahu" in out:
        out["Ketu"] = _norm360(out["Rahu"] + 180.0)

    return out


# ─────────────────────────────────────────────────────────────────────────────
# Geographic ASC / MC sweep (the expensive part, done once)
# ─────────────────────────────────────────────────────────────────────────────

def _sweep_angles(birth_jd: float, lat: float) -> tuple[list[float], list[float], list[float]]:
    """
    For one geographic latitude, sweep geographic longitude across the globe
    and record the local sidereal ASC and MC ecliptic longitudes.

    Returns (lons, asc_vals, mc_vals) where lons spans -180..180 at _LON_STEP.
    """
    _ensure_swe_sidereal()
    lons: list[float] = []
    asc: list[float] = []
    mc: list[float] = []
    n = int(360.0 / _LON_STEP)
    for i in range(n + 1):
        geo_lon = -180.0 + i * _LON_STEP
        try:
            cusps, ascmc = swe.houses_ex(birth_jd, lat, geo_lon, b"P", swe.FLG_SIDEREAL)
        except Exception:
            continue
        lons.append(geo_lon)
        asc.append(_norm360(ascmc[0]))   # ascmc[0] = Ascendant
        mc.append(_norm360(ascmc[1]))    # ascmc[1] = MC
    return lons, asc, mc


def _crossing_longitude(lons: list[float], vals: list[float], target: float) -> Optional[float]:
    """
    Find the geographic longitude where ``vals`` (an angle in [0,360) that
    increases roughly monotonically across the longitude sweep) passes through
    ``target``.  Linear interpolation on the unwrapped series; returns a
    longitude in (-180, 180] or None if no clean crossing is found.
    """
    if len(lons) < 2:
        return None

    target = _norm360(target)
    best_lon = None
    for i in range(len(lons) - 1):
        a = vals[i]
        b = vals[i + 1]
        # Unwrap the step so we can detect a crossing across the 0/360 seam.
        d = b - a
        if d > 180.0:
            b -= 360.0
        elif d < -180.0:
            b += 360.0

        lo, hi = (a, b) if a <= b else (b, a)
        # Test the target at its base value and at +-360 to catch the seam.
        for t in (target, target - 360.0, target + 360.0):
            if lo <= t <= hi and hi != lo:
                frac = (t - a) / (b - a)
                lon = lons[i] + frac * (lons[i + 1] - lons[i])
                return _norm180(lon)
    return best_lon


# ─────────────────────────────────────────────────────────────────────────────
# Public: compute every line in one efficient pass
# ─────────────────────────────────────────────────────────────────────────────

def compute_all_lines(birth_jd: float, chart: Optional[dict] = None) -> list[dict]:
    """
    Compute all 36 astrocartography lines for a birth moment.

    Returns a list of dicts, each:
        {
          "planet":   "Saturn",
          "angle":    "MC",
          "polyline": [[lat, lon], ...]   # 121 points
        }

    The natal-condition / colour layer is attached elsewhere
    (places_conditions + the endpoint), keeping this module purely geometric.
    """
    if not _SWE_AVAILABLE or birth_jd is None:
        return []

    plon = _planet_longitudes(birth_jd, chart)

    # MC longitudes are latitude-independent; resolve each once at the equator.
    eq_lons, eq_asc, eq_mc = _sweep_angles(birth_jd, 0.0)
    mc_longitude: dict[str, float] = {}
    for name in PLANETS:
        if name not in plon:
            continue
        mc_lon = _crossing_longitude(eq_lons, eq_mc, plon[name])
        if mc_lon is not None:
            mc_longitude[name] = mc_lon

    # AC / DC vary with latitude — one longitude sweep per sampled latitude
    # serves all nine planets for both rising and setting.
    ac_points: dict[str, list[list[float]]] = {name: [] for name in PLANETS}
    dc_points: dict[str, list[list[float]]] = {name: [] for name in PLANETS}

    for lat in SAMPLE_LATITUDES:
        lons, asc, _mc = _sweep_angles(birth_jd, lat)
        if not lons:
            continue
        for name in PLANETS:
            if name not in plon:
                continue
            p = plon[name]
            ac_lon = _crossing_longitude(lons, asc, p)              # rising
            dc_lon = _crossing_longitude(lons, asc, p + 180.0)      # setting (desc = asc+180)
            if ac_lon is not None:
                ac_points[name].append([round(lat, 1), round(ac_lon, 3)])
            if dc_lon is not None:
                dc_points[name].append([round(lat, 1), round(dc_lon, 3)])

    lines: list[dict] = []
    for name in PLANETS:
        if name not in plon:
            continue

        # MC — vertical polyline at the resolved longitude.
        mc_lon = mc_longitude.get(name)
        if mc_lon is not None:
            lines.append({
                "planet": name,
                "angle": "MC",
                "polyline": [[round(lat, 1), round(mc_lon, 3)] for lat in SAMPLE_LATITUDES],
            })
            # IC — opposite meridian.
            ic_lon = _norm180(mc_lon + 180.0)
            lines.append({
                "planet": name,
                "angle": "IC",
                "polyline": [[round(lat, 1), round(ic_lon, 3)] for lat in SAMPLE_LATITUDES],
            })

        # AC — rising curve.
        if ac_points[name]:
            lines.append({
                "planet": name,
                "angle": "AC",
                "polyline": ac_points[name],
            })
        # DC — setting curve.
        if dc_points[name]:
            lines.append({
                "planet": name,
                "angle": "DC",
                "polyline": dc_points[name],
            })

    return lines


def compute_astrocartography_line(
    planet: str,
    angle: str,
    birth_jd: float,
    sample_latitudes: Optional[list[float]] = None,
    chart: Optional[dict] = None,
) -> list[tuple[float, float]]:
    """
    Contract-shaped single-line accessor (see PLACES_API_Contract).

    Returns ~121 (lat, lon) points spanning -60 .. +60 latitude for one
    planet/angle.  Internally delegates to compute_all_lines and filters, so
    callers that need many lines should prefer compute_all_lines directly.
    """
    angle = angle.upper()
    for ln in compute_all_lines(birth_jd, chart):
        if ln["planet"] == planet and ln["angle"] == angle:
            pts = ln["polyline"]
            if sample_latitudes is not None:
                wanted = {round(float(l), 1) for l in sample_latitudes}
                pts = [p for p in pts if round(p[0], 1) in wanted]
            return [(p[0], p[1]) for p in pts]
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Distance helpers (used by concern scoring + city drill-down)
# ─────────────────────────────────────────────────────────────────────────────

_EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def distance_city_to_line(city_lat: float, city_lon: float, polyline: list) -> float:
    """
    Shortest distance (km) from a city to a line's polyline.

    The polyline is sampled at 1 deg latitude; we measure to the vertex nearest
    the city's own latitude band, then to its immediate neighbours, which is an
    excellent approximation for near-vertical (MC/IC) and gently curved
    (AC/DC) lines at the ranges we care about (<700 km).
    """
    if not polyline:
        return float("inf")
    best = float("inf")
    # Find the vertices whose latitude brackets the city.
    for pt in polyline:
        plat, plon = pt[0], pt[1]
        if abs(plat - city_lat) <= 2.0:                 # only nearby latitude bands
            d = haversine_km(city_lat, city_lon, plat, plon)
            if d < best:
                best = d
    if best == float("inf"):
        # City latitude outside the sampled band — fall back to nearest vertex.
        for pt in polyline:
            d = haversine_km(city_lat, city_lon, pt[0], pt[1])
            if d < best:
                best = d
    return best
