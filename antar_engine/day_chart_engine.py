"""
antar_engine/day_chart_engine.py
================================
Phase 3 — Cast a Vedic dawn chart for a given date + location.

Uses Swiss Ephemeris with Lahiri ayanamsa.
Computes: sunrise time, lagna at dawn, all 9 planet positions in the
day chart, house placements from dawn lagna.

Called by: daily_transit_analyzer.py (Phase 3 integration)
"""
import logging
from datetime import datetime, timedelta, timezone as tz
from typing import Dict, Optional, Tuple

import swisseph as swe

logger = logging.getLogger("antar_engine.day_chart_engine")

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

# Planets: 7 classical + Rahu/Ketu
PLANET_IDS = {
    "Sun":     swe.SUN,
    "Moon":    swe.MOON,
    "Mars":    swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus":   swe.VENUS,
    "Saturn":  swe.SATURN,
    "Rahu":    swe.MEAN_NODE,
}

SWE_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

# Country → (lat, lon) for representative capital/major city
# Covers Antar's current user base + 50 common countries
COUNTRY_COORDS: Dict[str, Tuple[float, float]] = {
    # Americas
    "US": (38.9072, -77.0369),    # Washington DC
    "CA": (45.4215, -75.6972),    # Ottawa
    "MX": (19.4326, -99.1332),    # Mexico City
    "AR": (-34.6037, -58.3816),   # Buenos Aires
    "CO": (4.7110, -74.0721),     # Bogotá
    "BR": (-15.7801, -47.9292),   # Brasília
    "CL": (-33.4489, -70.6693),   # Santiago
    "PE": (-12.0464, -77.0428),   # Lima
    "EC": (-0.1807, -78.4678),    # Quito
    "PA": (8.9824, -79.5199),     # Panama City
    "VE": (10.4806, -66.9036),    # Caracas
    "UY": (-34.9011, -56.1645),   # Montevideo
    "PY": (-25.2637, -57.5759),   # Asunción
    "BO": (-16.5000, -68.1500),   # La Paz
    "CR": (9.9281, -84.0907),     # San José
    "GT": (14.6349, -90.5069),    # Guatemala City
    "CU": (23.1136, -82.3666),    # Havana
    "DO": (18.4861, -69.9312),    # Santo Domingo
    "PR": (18.4655, -66.1057),    # San Juan
    "JM": (18.1096, -77.2975),    # Kingston
    "TT": (10.6918, -61.2225),    # Port of Spain

    # Europe
    "GB": (51.5074, -0.1278),     # London
    "ES": (40.4168, -3.7038),     # Madrid
    "FR": (48.8566, 2.3522),      # Paris
    "DE": (52.5200, 13.4050),     # Berlin
    "IT": (41.9028, 12.4964),     # Rome
    "PT": (38.7223, -9.1393),     # Lisbon
    "NL": (52.3676, 4.9041),      # Amsterdam
    "CH": (46.9480, 7.4474),      # Bern
    "SE": (59.3293, 18.0686),     # Stockholm
    "NO": (59.9139, 10.7522),     # Oslo
    "DK": (55.6761, 12.5683),     # Copenhagen
    "FI": (60.1699, 24.9384),     # Helsinki
    "IE": (53.3498, -6.2603),     # Dublin
    "PL": (52.2297, 21.0122),     # Warsaw
    "AT": (48.2082, 16.3738),     # Vienna
    "BE": (50.8503, 4.3517),      # Brussels
    "GR": (37.9838, 23.7275),     # Athens
    "RO": (44.4268, 26.1025),     # Bucharest
    "CZ": (50.0755, 14.4378),     # Prague
    "HU": (47.4979, 19.0402),     # Budapest

    # Asia
    "IN": (28.6139, 77.2090),     # New Delhi
    "LK": (6.9271, 79.8612),      # Colombo
    "NP": (27.7172, 85.3240),     # Kathmandu
    "BD": (23.8103, 90.4125),     # Dhaka
    "PK": (33.6844, 73.0479),     # Islamabad
    "CN": (39.9042, 116.4074),    # Beijing
    "JP": (35.6762, 139.6503),    # Tokyo
    "KR": (37.5665, 126.9780),    # Seoul
    "TW": (25.0330, 121.5654),    # Taipei
    "TH": (13.7563, 100.5018),    # Bangkok
    "VN": (21.0278, 105.8342),    # Hanoi
    "MY": (3.1390, 101.6869),     # Kuala Lumpur
    "SG": (1.3521, 103.8198),     # Singapore
    "ID": (-6.2088, 106.8456),    # Jakarta
    "PH": (14.5995, 120.9842),    # Manila

    # Middle East
    "AE": (25.2048, 55.2708),     # Dubai
    "SA": (24.7136, 46.6753),     # Riyadh
    "IL": (31.7683, 35.2137),     # Jerusalem
    "TR": (39.9334, 32.8597),     # Ankara
    "QA": (25.2854, 51.5310),     # Doha
    "KW": (29.3759, 47.9774),     # Kuwait City
    "OM": (23.5880, 58.3829),     # Muscat
    "BH": (26.0667, 50.5577),     # Manama

    # Africa
    "ZA": (-33.9249, 18.4241),    # Cape Town
    "NG": (9.0765, 7.3986),       # Abuja
    "EG": (30.0444, 31.2357),     # Cairo
    "KE": (-1.2921, 36.8219),     # Nairobi
    "GH": (5.6037, -0.1870),      # Accra
    "ET": (9.0250, 38.7469),      # Addis Ababa
    "MA": (33.9716, -6.8498),     # Rabat
    "TN": (36.8065, 10.1815),     # Tunis

    # Oceania
    "AU": (-33.8688, 151.2093),   # Sydney
    "NZ": (-41.2866, 174.7756),   # Wellington
}

# Approximate UTC offset from longitude (rough but usable for display)
def _approx_utc_offset(longitude: float) -> float:
    """Approximate UTC offset from longitude (hours)."""
    return round(longitude / 15.0)


# ─────────────────────────────────────────────────────────────────
# SUNRISE COMPUTATION (reuses hora_engine pattern)
# ─────────────────────────────────────────────────────────────────

def _compute_sunrise_jd(target_date: datetime, lat: float, lon: float) -> float:
    """
    Compute sunrise Julian Day for the given date and location.
    Returns JD of sunrise (UT).
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd_noon = swe.julday(target_date.year, target_date.month, target_date.day, 12.0)

    RISE_FLAG = swe.CALC_RISE
    GEO_FLAG = swe.BIT_DISC_CENTER

    rise_result = swe.rise_trans(
        jd_noon - 0.5,
        swe.SUN,
        RISE_FLAG | GEO_FLAG,
        [lon, lat, 0],
        0.0, 0.0,
        swe.FLG_SWIEPH,
    )
    return rise_result[1][0]


def _jd_to_datetime_utc(jd: float) -> datetime:
    """Convert Julian Day to datetime (UTC)."""
    y, m, d, h = swe.revjul(jd)
    hour = int(h)
    minute = int((h - hour) * 60)
    second = int(((h - hour) * 60 - minute) * 60)
    return datetime(y, m, d, hour, minute, second, tzinfo=tz.utc)


# ─────────────────────────────────────────────────────────────────
# LAGNA (ASCENDANT) COMPUTATION
# ─────────────────────────────────────────────────────────────────

def _compute_lagna(jd: float, lat: float, lon: float) -> dict:
    """
    Compute sidereal ascendant at a given Julian Day for a location.
    Returns {sign, sign_index, degree, nakshatra}.
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    # swe.houses_ex returns (cusps_tuple, ascmc_tuple)
    # cusps[0] is unused, cusps[1..12] are house cusps
    # ascmc[0] = ascendant longitude (tropical)
    cusps, ascmc = swe.houses_ex(jd, lat, lon, b'P')  # Placidus

    # Get ayanamsa for sidereal conversion
    ayanamsa = swe.get_ayanamsa_ut(jd)
    asc_sid = (ascmc[0] - ayanamsa) % 360

    sign_idx = int(asc_sid / 30)
    degree = asc_sid % 30
    nak_idx = int(asc_sid / (360 / 27))

    return {
        "sign": SIGNS[sign_idx],
        "sign_index": sign_idx,
        "degree": round(degree, 2),
        "nakshatra": NAKSHATRAS[nak_idx % 27],
        "longitude": round(asc_sid, 4),
    }


def _compute_house_cusps_sidereal(jd: float, lat: float, lon: float) -> list:
    """
    Compute 12 sidereal house cusps.
    Returns list of 12 dicts: [{sign, sign_index, degree}, ...]
    FIX 12: Guard against short cusp tuples from Swiss Ephemeris edge cases.
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    try:
        cusps, ascmc = swe.houses_ex(jd, lat, lon, b'P')
    except Exception as e:
        # Fallback: equal house system from ascendant
        print(f"[day-chart] houses_ex failed ({e}), using equal-house fallback")
        asc_result = swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)
        asc_lon = asc_result[0][0] if asc_result and asc_result[0] else 0.0
        return [
            {"house": i, "sign": SIGNS[int(((asc_lon + (i-1)*30) % 360) / 30)],
             "sign_index": int(((asc_lon + (i-1)*30) % 360) / 30),
             "degree": round(((asc_lon + (i-1)*30) % 360) % 30, 2)}
            for i in range(1, 13)
        ]

    ayanamsa = swe.get_ayanamsa_ut(jd)

    house_list = []
    for i in range(1, 13):
        if i >= len(cusps):
            # Edge case: cusp tuple shorter than expected — use previous cusp + 30°
            prev = cusps[i-1] if (i-1) < len(cusps) else 0.0
            cusp_val = prev + 30.0
        else:
            cusp_val = cusps[i]
        cusp_sid = (cusp_val - ayanamsa) % 360
        sign_idx = int(cusp_sid / 30)
        deg = cusp_sid % 30
        house_list.append({
            "house": i,
            "sign": SIGNS[sign_idx],
            "sign_index": sign_idx,
            "degree": round(deg, 2),
        })
    return house_list


# ─────────────────────────────────────────────────────────────────
# PLANET POSITION AT DAWN
# ─────────────────────────────────────────────────────────────────

def _compute_planet_position(jd: float, planet_id: int) -> dict:
    """
    Compute sidereal position of a planet at a given JD.
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    result = swe.calc_ut(jd, planet_id, SWE_FLAGS)
    lon = result[0][0]
    speed = result[0][3]

    sign_idx = int(lon / 30)
    deg_in_sign = lon % 30
    nak_idx = int(lon / (360 / 27))

    return {
        "sign": SIGNS[sign_idx],
        "sign_index": sign_idx,
        "degree": round(deg_in_sign, 2),
        "longitude": round(lon, 4),
        "nakshatra": NAKSHATRAS[nak_idx % 27],
        "speed": round(speed, 4),
        "retrograde": speed < 0,
    }


def _house_from_lagna(planet_sign_index: int, lagna_sign_index: int) -> int:
    """Compute house number from lagna. House 1 = lagna sign."""
    return ((planet_sign_index - lagna_sign_index) % 12) + 1


# ─────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────

async def cast_day_chart(
    target_date: datetime,
    latitude: float,
    longitude: float,
) -> dict:
    """
    Cast a Vedic chart for dawn at the given location.
    Uses Swiss Ephemeris with Lahiri ayanamsa.

    Args:
        target_date: date/datetime for the day to chart
        latitude: geographic latitude
        longitude: geographic longitude

    Returns:
        {
            "dawn_time_utc": ISO string,
            "dawn_time_local_approx": ISO string,
            "lagna": {sign, sign_index, degree, nakshatra},
            "planets": {
                "Sun": {sign, degree, house, nakshatra, retrograde, ...},
                ...
            },
            "houses": [...12 house cusps...],
        }
    """
    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI)

        # Compute sunrise
        sunrise_jd = _compute_sunrise_jd(target_date, latitude, longitude)
        dawn_utc = _jd_to_datetime_utc(sunrise_jd)

        # Approximate local time
        utc_offset = _approx_utc_offset(longitude)
        dawn_local = dawn_utc + timedelta(hours=utc_offset)

        # Compute lagna at sunrise
        lagna = _compute_lagna(sunrise_jd, latitude, longitude)
        lagna_sign_idx = lagna["sign_index"]

        # Compute house cusps
        houses = _compute_house_cusps_sidereal(sunrise_jd, latitude, longitude)

        # Compute all planet positions at sunrise
        planets = {}
        for planet_name, planet_id in PLANET_IDS.items():
            pos = _compute_planet_position(sunrise_jd, planet_id)
            pos["house"] = _house_from_lagna(pos["sign_index"], lagna_sign_idx)
            planets[planet_name] = pos

        # Ketu = Rahu + 180°
        rahu_lon = planets["Rahu"]["longitude"]
        ketu_lon = (rahu_lon + 180) % 360
        ketu_sign_idx = int(ketu_lon / 30)
        ketu_deg = ketu_lon % 30
        ketu_nak_idx = int(ketu_lon / (360 / 27))
        planets["Ketu"] = {
            "sign": SIGNS[ketu_sign_idx],
            "sign_index": ketu_sign_idx,
            "degree": round(ketu_deg, 2),
            "longitude": round(ketu_lon, 4),
            "nakshatra": NAKSHATRAS[ketu_nak_idx % 27],
            "speed": 0.0,
            "retrograde": True,
            "house": _house_from_lagna(ketu_sign_idx, lagna_sign_idx),
        }

        return {
            "dawn_time_utc": dawn_utc.isoformat(),
            "dawn_time_local_approx": dawn_local.isoformat(),
            "lagna": lagna,
            "planets": planets,
            "houses": houses,
        }

    except Exception as e:
        logger.error(f"[day-chart] cast_day_chart failed: {e}", exc_info=True)
        return {}


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def get_country_coords(country_code: str) -> Optional[Tuple[float, float]]:
    """
    Get (lat, lon) for a country code.
    Returns None if country not in map.
    """
    return COUNTRY_COORDS.get(country_code.upper()) if country_code else None


def format_day_chart_for_prompt(day_chart: dict) -> str:
    """
    Format day chart into a text block for LLM prompt injection.
    """
    if not day_chart:
        return ""

    lagna = day_chart.get("lagna", {})
    planets = day_chart.get("planets", {})

    lines = [
        f"DAY CHART (sunrise chart at user's location):",
        f"  Dawn lagna: {lagna.get('sign', '?')} {lagna.get('degree', 0):.1f}° ({lagna.get('nakshatra', '?')})",
        f"  Dawn time (UTC): {day_chart.get('dawn_time_utc', '?')}",
        "",
        "  Today's planet positions (day chart):",
    ]

    for planet_name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        p = planets.get(planet_name, {})
        if p:
            retro = " [R]" if p.get("retrograde") else ""
            lines.append(
                f"    {planet_name}: {p.get('sign', '?')} {p.get('degree', 0):.1f}°{retro} "
                f"→ H{p.get('house', '?')} ({p.get('nakshatra', '?')})"
            )

    return "\n".join(lines)
