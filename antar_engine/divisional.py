# divisional.py
from antar_engine import constants

SIGNS = constants.SIGNS  # 0‑based list for output

def divisional_longitude_1based(longitude, div):
    """
    Convert a sidereal longitude to its 1‑based sign index in a divisional chart.
    div: divisional number (e.g., 9 for Navamsa, 10 for Dasamsa)
    Returns: (div_sign_1based, div_longitude_in_sign)
    """
    part_length = 30.0 / div
    sign_1based = int(longitude / 30) + 1               # 1‑based sign (1=Aries, 12=Pisces)
    deg_in_sign = longitude - (sign_1based - 1) * 30    # degrees within the sign
    part = int(deg_in_sign / part_length)               # part number (0 to div-1)

    # 1‑based divisional sign index
    div_sign_1based = ((sign_1based - 1) * div + part) % 12 + 1
    # Longitude within the divisional sign (0‑30)
    div_deg = (deg_in_sign % part_length) * (12 / div)
    return div_sign_1based, div_deg

def calculate_divisional_chart(chart, div):
    """
    Given a chart dictionary (from chart.calculate_chart), return a new chart
    with planets and lagna in the divisional chart of order 'div'.
    Uses the 1‑based harmonic formula for all divisional charts.
    Returns dict with 'lagna' and 'planets' (both using 0‑based sign indices for consistency).
    """
    # Lagna
    lagna_lon = chart['lagna']['sign_index'] * 30 + chart['lagna']['degree']
    div_lagna_1based, div_lagna_deg = divisional_longitude_1based(lagna_lon, div)
    div_lagna_sign_0based = div_lagna_1based - 1

    div_chart = {
        'lagna': {
            'sign': SIGNS[div_lagna_sign_0based],
            'sign_index': div_lagna_sign_0based,
            'degree': div_lagna_deg
        },
        'planets': {}
    }

    # Planets
    for planet, data in chart['planets'].items():
        lon = data['longitude']
        div_sign_1based, div_deg = divisional_longitude_1based(lon, div)
        div_sign_0based = div_sign_1based - 1
        div_chart['planets'][planet] = {
            'longitude': lon,
            'sign': SIGNS[div_sign_0based],
            'sign_index': div_sign_0based,
            'degree': div_deg
        }
    return div_chart
