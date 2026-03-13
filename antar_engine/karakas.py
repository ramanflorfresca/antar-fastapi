# karakas.py
from . import constants

def get_atmakaraka(chart_data):
    """Return the Atmakaraka (planet with highest longitude)."""
    planets = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
    karakas = []
    for p in planets:
        lon = chart_data['planets'][p]['longitude']
        karakas.append((p, lon))
    karakas.sort(key=lambda x: x[1], reverse=True)
    if karakas:
        p, lon = karakas[0]
        return {
            'planet': p,
            'longitude': lon,
            'sign': chart_data['planets'][p]['sign'],
            'degree': chart_data['planets'][p]['degree']
        }
    return None

def get_all_karakas(chart_data):
    """Return all seven karakas in order (1=Atmakaraka, ..., 7=Darakaraka)."""
    planets = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
    karakas = []
    for p in planets:
        lon = chart_data['planets'][p]['longitude']
        karakas.append((p, lon, chart_data['planets'][p]['sign'], chart_data['planets'][p]['degree']))
    karakas.sort(key=lambda x: x[1], reverse=True)
    result = []
    for i, (p, lon, sign, deg) in enumerate(karakas):
        result.append({
            'rank': i+1,
            'name': constants.KARAKA_NAMES.get(i+1, f'Karaka {i+1}'),
            'planet': p,
            'sign': sign,
            'degree': deg
        })
    return result

def psychological_profile(chart_data):
    """Generate a short psychological summary based on karakas."""
    karakas = get_all_karakas(chart_data)
    if not karakas:
        return ""
    ak = karakas[0]  # Atmakaraka
    amk = karakas[1] if len(karakas) > 1 else None
    dk = karakas[6] if len(karakas) > 6 else None

    lines = []
    lines.append(f"Your soul's indicator (Atmakaraka) is {ak['planet']} in {ak['sign']}, suggesting a core drive for {ak['sign']}‑like qualities.")
    if amk:
        lines.append(f"Your career signature (Amatyakaraka) is {amk['planet']} in {amk['sign']}, influencing your professional path.")
    if dk:
        lines.append(f"Your relationship marker (Darakaraka) is {dk['planet']} in {dk['sign']}, shaping your partnerships.")
    return "\n".join(lines)
