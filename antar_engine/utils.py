# utils.py

import swisseph as swe
from datetime import datetime, timedelta, timezone

import math

def normalize_angle(angle):
    """Normalize angle to 0-360 range."""
    return angle % 360

def sign_index_from_longitude(longitude):
    """Get sign index (0-11) from sidereal longitude."""
    return int(longitude / 30)

def degree_in_sign(longitude):
    """Get degrees within the sign (0-30)."""
    return longitude - sign_index_from_longitude(longitude) * 30

def nakshatra_index_from_longitude(longitude):
    """Get nakshatra index (0-26) from sidereal longitude."""
    nak_deg = 360 / 27
    return int(longitude / nak_deg)

def nakshatra_lord_from_index(nak_idx):
    """Get nakshatra lord planet name from index."""
    from constants import NAKSHATRA_LORDS
    return NAKSHATRA_LORDS[nak_idx % 27]

def get_dispositor(planet, planet_signs, sign_lords):
    """
    For a given planet (which could be Rahu or Ketu), return the sign
    occupied by its dispositor (the ruler of the sign where the planet sits).
    """
    node_sign = planet_signs[planet]
    dispositor = sign_lords[node_sign]
    return planet_signs[dispositor]

def zodiac_distance_inclusive(start, end, direction):
    """
    Inclusive distance: number of signs from start to end,
    including both start and end, following the given direction.
    If start == end, returns 1.
    """
    if start == end:
        return 1
    dist = 0
    current = start
    while True:
        dist += 1
        if current == end:
            break
        current = (current + direction) % 12
    return dist

def parse_birth_data(birth_date, birth_time, lat, lon, tz_offset):
    """Convert birth data to Julian day (UTC)."""
    dt_local = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    dt_utc = dt_local - timedelta(hours=tz_offset)
    jd_utc = julian_day(dt_utc)
    return jd_utc

def julian_day(dt_utc):
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                      dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0)

def datetime_from_jd(jd):
    y, m, d, h = swe.revjul(jd)
    # Create a naive datetime and then make it aware (UTC)
    dt = datetime(int(y), int(m), int(d)) + timedelta(hours=h)
    return dt.replace(tzinfo=timezone.utc)
