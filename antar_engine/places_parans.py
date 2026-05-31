"""
antar_engine/places_parans.py
─────────────────────────────────────────────────────────────────────────────
PLACES — paran detection.  Phase 2.

A paran is a latitude where two different planets' angle lines cross on the
world map — a point where both planetary currents are simultaneously angular.
These are the "extra-potent" spots of astrocartography.

We operate purely on the already-computed 121-point polylines (no new
ephemeris work): for each pair of lines belonging to *different* planets we
walk the shared latitude grid and find where their longitudes coincide.
"""

from __future__ import annotations

from typing import Optional

from antar_engine.places_lines import haversine_km


def _norm180(x: float) -> float:
    x = (x + 180.0) % 360.0 - 180.0
    return 180.0 if x == -180.0 else x


def _as_lat_lon_map(polyline: list) -> dict[float, float]:
    return {round(pt[0], 1): pt[1] for pt in polyline}


def compute_parans(
    all_lines: list[dict],
    conditions: Optional[dict] = None,
    max_results: int = 60,
) -> list[dict]:
    """
    Crossings between lines of different planets.

    Returns a list of:
        {
          "planet_a", "angle_a", "planet_b", "angle_b",
          "type": "MCxAC",  "lat", "lon",
          "polarity_a", "polarity_b"
        }
    sorted by closeness to the equator (lower |lat| = broadly more habitable).
    """
    conditions = conditions or {}
    maps = [(ln, _as_lat_lon_map(ln["polyline"])) for ln in all_lines]
    parans: list[dict] = []

    for i in range(len(maps)):
        ln_a, map_a = maps[i]
        for j in range(i + 1, len(maps)):
            ln_b, map_b = maps[j]
            if ln_a["planet"] == ln_b["planet"]:
                continue  # a planet crossing its own angles is not a paran

            # Shared, sorted latitude grid.
            lats = sorted(set(map_a) & set(map_b))
            prev_lat = None
            prev_diff = None
            for lat in lats:
                diff = _norm180(map_a[lat] - map_b[lat])
                if prev_diff is not None and prev_diff != 0.0 and diff != 0.0 and (prev_diff < 0) != (diff < 0):
                    # Sign change → crossing between prev_lat and lat.
                    span = diff - prev_diff
                    frac = (0.0 - prev_diff) / span if span else 0.5
                    cross_lat = prev_lat + frac * (lat - prev_lat)
                    # Longitude at the crossing (interpolate line A).
                    la = map_a[prev_lat]
                    lb = map_a[lat]
                    step = _norm180(lb - la)
                    cross_lon = _norm180(la + frac * step)
                    parans.append({
                        "planet_a": ln_a["planet"], "angle_a": ln_a["angle"],
                        "planet_b": ln_b["planet"], "angle_b": ln_b["angle"],
                        "type": f"{ln_a['angle']}x{ln_b['angle']}",
                        "lat": round(cross_lat, 2),
                        "lon": round(cross_lon, 2),
                        "polarity_a": conditions.get(ln_a["planet"], {}).get("polarity", "mixed"),
                        "polarity_b": conditions.get(ln_b["planet"], {}).get("polarity", "mixed"),
                    })
                prev_lat = lat
                prev_diff = diff

    parans.sort(key=lambda p: abs(p["lat"]))
    return parans[:max_results]


def parans_near_city(
    parans: list[dict],
    lat: float,
    lon: float,
    max_distance_km: float = 600.0,
) -> list[dict]:
    """Parans whose crossing point sits within max_distance_km of a city."""
    hits = []
    for p in parans:
        d = haversine_km(lat, lon, p["lat"], p["lon"])
        if d <= max_distance_km:
            q = dict(p)
            q["distance_km"] = round(d, 1)
            hits.append(q)
    hits.sort(key=lambda p: p["distance_km"])
    return hits
