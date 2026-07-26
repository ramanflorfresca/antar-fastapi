"""
Yogini Dasha calculation module.
Date: 2026-07-26

An 8-fold, 36-year nakshatra-based conditional daśā (Moon-star driven, same
family as Vimśottarī and Aśtottarī). Eight Yoginīs, each ruled by a graha,
run in a fixed order with durations 1..8 years:

    Maṅgalā(Moon,1) Piṅgalā(Sun,2) Dhānyā(Jupiter,3) Bhrāmarī(Mars,4)
    Bhadrikā(Mercury,5) Ulkā(Saturn,6) Siddhā(Venus,7) Saṅkaṭā(Rahu,8)   = 36y

Ketu is excluded. The starting Yoginī is (janma-nakshatra-number + 3) mod 8,
counting the nakshatra 1-based from Aśvinī; chart_data carries a 0-based
nakshatra_index, so the rule here is (index + 4) mod 8. Antardaśās run the same
eight in order from the running Yoginī, each proportional: sub_years*maha_years/36.

Mirrors ashtottari.py's interface exactly — calculate_yogini_from_chart(
chart_data, birth_jd) returns {'mahadashas': [...], 'antardashas': [...]} with
lord / start_date / end_date / duration_years (+ parent_lord on antars) — so it
drops straight into update_all_dashas.py and dasha_periods (system='yogini').
"""

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from . import utils

# Order 1..8: (Yoginī name, graha lord, years)
YOGINI_SEQUENCE = [
    ("Mangala",  "Moon",    1),
    ("Pingala",  "Sun",     2),
    ("Dhanya",   "Jupiter", 3),
    ("Bhramari", "Mars",    4),
    ("Bhadrika", "Mercury", 5),
    ("Ulka",     "Saturn",  6),
    ("Siddha",   "Venus",   7),
    ("Sankata",  "Rahu",    8),
]
YOGINI_TOTAL = sum(y[2] for y in YOGINI_SEQUENCE)  # 36


def start_index(moon_nakshatra_idx: int) -> int:
    """0-based index into YOGINI_SEQUENCE for the birth Yoginī.

    Classical rule (nakshatra_number + 3) mod 8, 1-based from Aśvinī; with the
    0-based nakshatra_index stored on the chart that is (idx + 4) mod 8, mapping
    a 0 remainder back to the 8th (Saṅkaṭā).
    """
    r = (int(moon_nakshatra_idx) + 4) % 8
    return (r - 1) if r != 0 else 7


def _antardashas(maha_lord: str, start_dt, end_dt):
    """The 8 sub-periods of a mahadaśā, in order from the mahadaśā's own Yoginī,
    lengths proportional to each Yoginī's years. Uses the mahadaśā's real
    wall-clock span so the antars tile it exactly (no drift)."""
    lords = [y[1] for y in YOGINI_SEQUENCE]
    start_idx = lords.index(maha_lord)
    total_seconds = (end_dt - start_dt).total_seconds()
    maha_years = total_seconds / (365.25 * 86400)
    out = []
    cur = start_dt
    for i in range(8):
        name, lord, yrs = YOGINI_SEQUENCE[(start_idx + i) % 8]
        ad_years = (yrs / YOGINI_TOTAL) * maha_years
        ad_seconds = total_seconds * (yrs / YOGINI_TOTAL)
        ad_end = cur + timedelta(seconds=ad_seconds)
        out.append({
            "yogini": name,
            "lord": lord,
            "start_datetime": cur,
            "end_datetime": ad_end,
            "duration_years": ad_years,
            "parent_lord": maha_lord,
        })
        cur = ad_end
    return out


def calculate_yogini_from_chart(chart_data: dict, birth_jd: float, cycles: int = 3) -> dict:
    """Full Yoginī mahadaśās + antardaśās from birth.

    `cycles` = how many 36-year rounds to project (3 → 108 years, covers a life).
    Returns {'mahadashas': [...], 'antardashas': [...]}; each item carries lord,
    start_date, end_date (ISO), duration_years — matching ashtottari.py.
    """
    moon = chart_data["planets"]["Moon"]
    idx = moon.get("nakshatra_index")
    if idx is None:
        moon_long = moon["longitude"]
        idx = int(moon_long / (360 / 27))
        idx = min(idx, 26)
        portion = (moon_long - idx * (360 / 27)) / (360 / 27)
    else:
        portion = moon.get("nakshatra_portion", 0.5)

    si = start_index(idx)
    birth_dt = utils.datetime_from_jd(birth_jd)

    mahadashas = []
    cur = birth_dt
    n_periods = 8 * cycles
    for k in range(n_periods):
        name, lord, yrs = YOGINI_SEQUENCE[(si + k) % 8]
        # Balance the FIRST Yoginī by the unelapsed fraction of the birth star.
        eff_years = yrs * (1 - portion) if k == 0 else yrs
        yint = int(eff_years)
        frac = eff_years - yint
        end = cur + relativedelta(years=yint) + timedelta(days=frac * 365.25)
        mahadashas.append({
            "yogini": name,
            "lord": lord,
            "start_datetime": cur,
            "end_datetime": end,
            "duration_years": eff_years,
        })
        cur = end

    antardashas = []
    for md in mahadashas:
        antardashas.extend(_antardashas(md["lord"], md["start_datetime"], md["end_datetime"]))

    for row in mahadashas + antardashas:
        row["start_date"] = row["start_datetime"].isoformat()
        row["end_date"] = row["end_datetime"].isoformat()

    return {"mahadashas": mahadashas, "antardashas": antardashas}


calculate = calculate_yogini_from_chart
