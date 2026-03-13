import swisseph as swe
import pytz
from datetime import datetime, timedelta
import os

# Initialize Swiss Ephemeris
script_dir = os.path.dirname(os.path.abspath(__file__))
ephe_path = os.path.join(script_dir, 'ephe')
swe.set_ephe_path(ephe_path)
swe.set_sid_mode(swe.SIDM_LAHIRI)  # Lahiri ayanamsa for sidereal

# Planet mappings (only classical planets; nodes handled separately)
PLANETS = {
    'Sun': swe.SUN,
    'Moon': swe.MOON,
    'Mars': swe.MARS,
    'Mercury': swe.MERCURY,
    'Jupiter': swe.JUPITER,
    'Venus': swe.VENUS,
    'Saturn': swe.SATURN,
}

# Sign names (0 = Aries, 1 = Taurus, ..., 11 = Pisces)
SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
         'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

# Traditional sign rulers (indexed by sign index 0-11)
SIGN_LORDS = [
    'Mars',      # Aries (0)
    'Venus',     # Taurus (1)
    'Mercury',   # Gemini (2)
    'Moon',      # Cancer (3)
    'Sun',       # Leo (4)
    'Mercury',   # Virgo (5)
    'Venus',     # Libra (6)
    'Mars',      # Scorpio (7)
    'Jupiter',   # Sagittarius (8)
    'Saturn',    # Capricorn (9)
    'Saturn',    # Aquarius (10)
    'Jupiter'    # Pisces (11)
]

# Sign types (0-based)
FIXED_SIGNS   = [1, 4, 7, 9, 10]   # Taurus, Leo, Scorpio, Capricorn, Aquarius
MOVABLE_SIGNS = [0, 3, 6]           # Aries, Cancer, Libra
DUAL_SIGNS    = [2, 5, 8, 11]       # Gemini, Virgo, Sagittarius, Pisces

NAKSHATRAS = [
    'Ashvini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
    'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni',
    'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha',
    'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha',
    'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati'
]

# Nakshatra lords in order (27 nakshatras)
NAKSHATRA_LORDS = [
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu',
    'Jupiter', 'Saturn', 'Mercury', 'Ketu', 'Venus', 'Sun',
    'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury',
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu',
    'Jupiter', 'Saturn', 'Mercury'
]

def julian_day(dt_utc):
    """Convert UTC datetime to Julian day number."""
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                      dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0)

def get_lagna(jd_utc, lat, lon):
    """Calculate sidereal ascendant (Lagna). Returns (sign_index, longitude_in_sign)."""
    cusps_trop, ascmc_trop = swe.houses(jd_utc, lat, lon, b'P')
    asc_tropical = ascmc_trop[0]
    ayanamsa = swe.get_ayanamsa(jd_utc)
    print(f"DEBUG: Ayanamsa = {ayanamsa:.4f}°")
    print(f"DEBUG: Tropical Ascendant = {asc_tropical:.4f}°")

    cusps, ascmc = swe.houses_ex(jd_utc, lat, lon, b'P', swe.FLG_SIDEREAL)
    asc_sidereal = ascmc[0]
    print(f"DEBUG: Sidereal Ascendant (houses_ex) = {asc_sidereal:.4f}°")
    sign_index = int(asc_sidereal / 30)
    lon_in_sign = asc_sidereal - sign_index * 30
    print(f"DEBUG: Sidereal Lagna = {SIGNS[sign_index]} at {lon_in_sign:.2f}°")
    return sign_index, lon_in_sign

def get_planet_longitude(jd_utc, planet):
    """Get sidereal longitude of a planet."""
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

    if planet == 'Rahu':
        lon, _ = swe.calc_ut(jd_utc, swe.TRUE_NODE, flags=flags)
        lon_deg = lon[0]
    elif planet == 'Ketu':
        lon_rahu, _ = swe.calc_ut(jd_utc, swe.TRUE_NODE, flags=flags)
        lon_deg = (lon_rahu[0] + 180) % 360
    else:
        lon, _ = swe.calc_ut(jd_utc, PLANETS[planet], flags=flags)
        lon_deg = lon[0]

    sign_index = int(lon_deg / 30)
    lon_in_sign = lon_deg - sign_index * 30

    nakshatra_deg = 360 / 27
    nakshatra_idx = int(lon_deg / nakshatra_deg)
    if nakshatra_idx >= 27:
        nakshatra_idx = 26
    nakshatra_lord = NAKSHATRA_LORDS[nakshatra_idx]
    nak_start = nakshatra_idx * nakshatra_deg
    nak_portion = (lon_deg - nak_start) / nakshatra_deg

    return lon_deg, sign_index, lon_in_sign, nakshatra_idx, nakshatra_lord, nak_portion


def _tz_name_to_offset(timezone: str) -> float:
    """IANA timezone name → UTC offset in decimal hours."""
    try:
        tz  = pytz.timezone(timezone)
        now = datetime.utcnow()
        return tz.utcoffset(now).total_seconds() / 3600.0
    except Exception:
        return 5.5   # IST fallback


def _calculate_chart_raw(birth_date, birth_time, lat, lon, tz_offset):
    """
    Core chart calculation — original logic, untouched.
    Returns chart_data enriched with:
      • planets[*]['house']  — Whole Sign house (1-12) relative to lagna
      • birth_jd             — Julian Day of birth (needed by dasha modules)
    """
    dt_local = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    dt_utc   = dt_local - timedelta(hours=tz_offset)
    jd_utc   = julian_day(dt_utc)

    # Lagna
    lagna_sign, lagna_deg = get_lagna(jd_utc, lat, lon)
    chart = {
        'lagna': {
            'sign':       SIGNS[lagna_sign],
            'sign_index': lagna_sign,
            'degree':     lagna_deg,
        },
        'planets':  {},
        'birth_jd': jd_utc,   # ← dasha modules need this
    }

    # All planets (including nodes)
    all_planets = list(PLANETS.keys()) + ['Rahu', 'Ketu']
    for planet in all_planets:
        lon_deg, sign_idx, lon_in_sign, nak_idx, nak_lord, nak_portion = \
            get_planet_longitude(jd_utc, planet)

        house = ((sign_idx - lagna_sign) % 12) + 1   # ← Whole Sign house

        chart['planets'][planet] = {
            'longitude':        lon_deg,
            'sign':             SIGNS[sign_idx],
            'sign_index':       sign_idx,
            'degree':           lon_in_sign,
            'house':            house,          # ← was missing
            'nakshatra':        NAKSHATRAS[nak_idx],
            'nakshatra_index':  nak_idx,
            'nakshatra_lord':   nak_lord,
            'nakshatra_portion': nak_portion,
        }
    return chart


def calculate_chart(
    birth_date: str,
    birth_time: str,
    lat: float,
    lon: float = None,
    tz_offset: float = None,
    lng: float = None,
    timezone: str = None,
    ayanamsa: str = "lahiri",   # accepted for API compat; Lahiri set via swe.set_sid_mode above
) -> dict:
    """
    Unified calculate_chart() accepting EITHER calling convention:
      • original : calculate_chart(birth_date, birth_time, lat, lon, tz_offset)
      • main.py  : calculate_chart(birth_date, birth_time, lat, lng, timezone, ayanamsa)

    Returns chart_data with:
      • lagna  { sign, sign_index, degree }
      • planets[name] { longitude, sign, sign_index, degree, house,
                        nakshatra, nakshatra_index, nakshatra_lord, nakshatra_portion }
      • birth_jd  (Julian Day — required by vimsottari/jaimini/ashtottari)
    """
    resolved_lon = lon if lon is not None else lng
    if resolved_lon is None:
        raise ValueError("calculate_chart() requires either 'lon' or 'lng'")

    if tz_offset is not None:
        resolved_offset = tz_offset
    elif timezone is not None:
        resolved_offset = _tz_name_to_offset(timezone)
    else:
        raise ValueError("calculate_chart() requires either 'tz_offset' or 'timezone'")

    return _calculate_chart_raw(birth_date, birth_time, lat, resolved_lon, resolved_offset)


# Example usage
if __name__ == "__main__":
    test_chart = calculate_chart(
        birth_date='1974-11-26',
        birth_time='11:59',
        lat=28.6139,
        lon=77.2090,
        tz_offset=5.5
    )
    print("Lagna:", test_chart['lagna']['sign'], test_chart['lagna']['degree'])
    print("birth_jd:", test_chart['birth_jd'])
    for p, d in test_chart['planets'].items():
        print(f"{p}: H{d['house']} {d['sign']} {d['degree']:.2f}° ({d['nakshatra']})")
