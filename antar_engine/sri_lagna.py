"""
antar_engine/sri_lagna.py
Sri Lagna — the prosperity ascendant.                          2026-07-22

Sri is Lakshmi. The Sri Lagna is a Jaimini special ascendant marking where
wealth actually accumulates for a person, as distinct from the 2nd house (money
in hand) and the 11th (gains). It is read as a reference point in its own right:
its lord, its dispositor, and the houses counted FROM it.

    SL = Lagna° + ( Moon's traverse of its nakshatra as a fraction ) x 360°

The logic behind that formula is worth stating, because it is not arbitrary. The
Moon's position inside its nakshatra is the same quantity that seeds the
Vimshottari dasha balance at birth. Sri Lagna projects that same fraction onto
the whole zodiac and measures it from the ascendant — so it ties the person's
prosperity reference to the exact point their dasha sequence begins from.

WHY THIS IS WORTH ADDING. The money domain in this engine currently reads the
2nd, 5th, 8th, 11th and 12th plus a 5th-affliction rule, and catches 3 of 4
recorded money events. Sri Lagna is an INDEPENDENT wealth reference computed
from a different quantity entirely. Two systems agreeing on a money signal is
worth more than one system scoring higher — which is the same principle the
cycle module is built on.

The codebase already has Arudha Lagna and Upapada Lagna. Sri Lagna, Hora Lagna
and Ghati Lagna were absent. Only Sri Lagna is implemented here: it needs the
Moon and the ascendant alone, both of which are stored on every chart. Hora and
Ghati Lagna require the exact sunrise for the birth place, and half the charts
in this base have coordinates good enough for a lagna but not for a sunrise, so
computing them would produce a number that looks precise and is not.
"""

from typing import Dict, List, Optional

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

NAKSHATRA_ARC = 360.0 / 27.0        # 13 degrees 20 minutes


def _lagna_longitude(chart: dict) -> Optional[float]:
    lg = (chart or {}).get("lagna") or {}
    si, deg = lg.get("sign_index"), lg.get("degree")
    if isinstance(si, int) and isinstance(deg, (int, float)):
        return (si * 30.0) + float(deg)
    sign = lg.get("sign")
    if sign in SIGNS and isinstance(deg, (int, float)):
        return SIGNS.index(sign) * 30.0 + float(deg)
    return None


def _moon_longitude(chart: dict) -> Optional[float]:
    m = ((chart or {}).get("planets") or {}).get("Moon") or {}
    lon = m.get("longitude")
    if isinstance(lon, (int, float)):
        return float(lon) % 360.0
    si, deg = m.get("sign_index"), m.get("degree")
    if isinstance(si, int) and isinstance(deg, (int, float)):
        return (si * 30.0 + float(deg)) % 360.0
    return None


def sri_lagna(chart: dict) -> Dict:
    """The Sri Lagna point, its sign, its house from the lagna, and its lord."""
    lag = _lagna_longitude(chart)
    moon = _moon_longitude(chart)
    if lag is None or moon is None:
        return {"available": False}

    # Fraction of its nakshatra the Moon has covered — the same quantity that
    # seeds the Vimshottari balance at birth.
    traversed = (moon % NAKSHATRA_ARC) / NAKSHATRA_ARC
    sl_lon = (lag + traversed * 360.0) % 360.0

    sl_sign_idx = int(sl_lon // 30) % 12
    lagna_idx = int(lag // 30) % 12
    house_from_lagna = ((sl_sign_idx - lagna_idx) % 12) + 1
    lord = SIGN_LORD[sl_sign_idx]

    return {
        "available": True,
        "longitude": round(sl_lon, 4),
        "sign": SIGNS[sl_sign_idx],
        "sign_index": sl_sign_idx,
        "degree": round(sl_lon % 30, 2),
        "house_from_lagna": house_from_lagna,
        "lord": lord,
        "nakshatra_fraction": round(traversed, 4),
    }


def houses_from_sri_lagna(chart: dict) -> Dict[int, str]:
    """Where each planet sits COUNTED FROM the Sri Lagna.

    This is the point of having the reference at all: a planet in the 11th from
    Sri Lagna relates to gains differently than one in the 11th from the birth
    ascendant, because the two are measured from different origins.
    """
    sl = sri_lagna(chart)
    if not sl.get("available"):
        return {}
    base = sl["sign_index"]
    out = {}
    for p, d in ((chart or {}).get("planets") or {}).items():
        si = d.get("sign_index") if isinstance(d, dict) else None
        if isinstance(si, int):
            out[p] = ((si - base) % 12) + 1
    return out


def sri_lagna_wealth_reading(chart: dict) -> Dict:
    """A prosperity read from Sri Lagna, with its reasons named.

    Deliberately narrow. It reports the strength of the reference and its lord,
    and which planets sit on the wealth houses counted FROM it. It does not
    predict an amount or a date — Sri Lagna marks where wealth accumulates, not
    when it arrives.
    """
    sl = sri_lagna(chart)
    if not sl.get("available"):
        return {"available": False}

    from_sl = houses_from_sri_lagna(chart)
    benefics = {"Jupiter", "Venus", "Mercury", "Moon"}
    malefics = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}

    score, notes = 0.0, []

    # The 2nd and 11th FROM Sri Lagna are its wealth houses.
    for p, h in from_sl.items():
        if h in (2, 11):
            if p in benefics:
                score += 0.8
                notes.append(f"{p} sits in the {h}th from Sri Lagna — a benefic on "
                             f"the prosperity reference's own wealth house.")
            elif p in malefics:
                score -= 0.5
                notes.append(f"{p} sits in the {h}th from Sri Lagna — pressure on "
                             f"the wealth the reference is meant to hold.")
        elif h in (6, 8, 12) and p in benefics:
            score -= 0.3
            notes.append(f"{p} falls in the {h}th from Sri Lagna — its benefit "
                         f"leaks rather than accumulates.")

    try:
        from antar_engine.planet_significations import contextual_strength
        lord_pts = float((contextual_strength(sl["lord"], chart) or {}).get("points") or 0.0)
    except Exception:
        lord_pts = 0.0
    score += lord_pts * 0.5
    notes.append(f"Sri Lagna falls in {sl['sign']}, so its lord is {sl['lord']} "
                 f"({lord_pts:+.1f}) — the planet that governs how prosperity "
                 f"actually reaches this person.")

    band = ("accumulates" if score >= 1.5 else
            "holds" if score >= 0 else "leaks")

    return {
        "available": True,
        "sri_lagna": sl,
        "score": round(score, 2),
        "band": band,
        "notes": notes,
        "lord_strength": round(lord_pts, 2),
    }


# Activation types when a Chara antardaśā sign lands on a house counted FROM the
# Sri Lagna. Strength is a 0-1 weight for the forward wealth-ignition vote.
_SL_ACTIVATION = {
    1:  ("ignition",     1.0),   # the Sri Lagna sign itself — direct activation
    2:  ("accumulation", 0.7),   # 2nd from SL — the reference's dhana house
    11: ("gains",        0.7),   # 11th from SL — its gains house
    5:  ("fortune",      0.5),   # trine from SL — dharma/luck
    9:  ("fortune",      0.5),   # trine from SL — dharma/luck
}


def sri_lagna_activation_windows(chart: dict, chara_antardashas: List[dict],
                                 as_of=None) -> List[Dict]:
    """Forward Chara antardaśā windows that ACTIVATE the Sri Lagna for wealth.

    Given the antardaśā (sub-sign) timeline of the CURRENT Chara Mahādaśā (from
    jaimini.compute_jaimini_antardashas), return the sub-windows whose sign
    energises the Sri Lagna — its own sign (ignition), its 2nd/11th (dhana/gains),
    its trines (fortune), or the sign occupied by its lord (lord). These are the
    Jaimini half of the wealth-ignition signal; the caller cross-checks them
    against Vimśottari favourability before emitting a forecast.

    Each returned dict: start_date, end_date, sign, sign_index, activation,
    strength (0-1), house_from_sri_lagna, sri_lagna_sign, sri_lagna_lord.
    Only windows ending on/after `as_of` (default: today) are returned.
    """
    import datetime as _dt

    sl = sri_lagna(chart)
    if not sl.get("available") or not chara_antardashas:
        return []

    ref = as_of or _dt.date.today()
    if isinstance(ref, _dt.datetime):
        ref = ref.date()

    sl_idx = sl["sign_index"]
    lord = sl["lord"]
    lord_sign_idx = None
    ld = ((chart or {}).get("planets") or {}).get(lord) or {}
    if isinstance(ld.get("sign_index"), int):
        lord_sign_idx = ld["sign_index"] % 12

    out: List[Dict] = []
    for ad in chara_antardashas:
        end = ad.get("end_date")
        if end is None:
            continue
        if isinstance(end, _dt.datetime):
            end = end.date()
        if end < ref:
            continue

        ad_idx = ad["sign_index"]
        house = ((ad_idx - sl_idx) % 12) + 1
        activation, strength = _SL_ACTIVATION.get(house, (None, 0.0))

        # The sign holding the Sri Lagna lord also activates the reference, even
        # when it is not one of the wealth/trine houses above.
        if activation is None and lord_sign_idx is not None and ad_idx == lord_sign_idx:
            activation, strength = ("lord", 0.6)

        if activation is None:
            continue

        out.append({
            "start_date":           ad.get("start_date"),
            "end_date":             ad.get("end_date"),
            "sign":                 ad["sign"],
            "sign_index":           ad_idx,
            "activation":           activation,
            "strength":             strength,
            "house_from_sri_lagna": house,
            "sri_lagna_sign":       sl["sign"],
            "sri_lagna_lord":       lord,
        })

    out.sort(key=lambda w: str(w.get("start_date")))
    return out
