"""
antar_engine/lal_kitab_masik.py

Masik Phal (Monthly Chart) — Lal Kitab.
Rule: Take Varshphal (annual) house placements.
Each month after birthday, every planet advances +1 house.
Month 0 = birthday month = Varshphal placements.
Month 1 = +1 house for all planets. Month 11 = +11 houses.
"""

from datetime import date, datetime

HOUSE_THEMES = {
    1:  "Self, personality, body, overall direction",
    2:  "Wealth, family, speech, food",
    3:  "Courage, communication, siblings, travel",
    4:  "Home, mother, property, emotions",
    5:  "Intelligence, children, creativity, speculation",
    6:  "Enemies, debt, disease, service",
    7:  "Marriage, partnerships, business",
    8:  "Transformation, inheritance, hidden matters",
    9:  "Fortune, father, dharma, luck",
    10: "Career, authority, public status",
    11: "Gains, income, aspirations, elder siblings",
    12: "Expenses, foreign, spirituality, losses",
}

PLANET_NATURE = {
    "Sun":     "authority, soul, father",
    "Moon":    "mind, emotions, mother",
    "Mars":    "energy, courage, property",
    "Mercury": "intellect, business, communication",
    "Jupiter": "wisdom, wealth, children",
    "Venus":   "relationships, luxury, art",
    "Saturn":  "discipline, karma, longevity",
    "Rahu":    "ambition, foreign, technology",
    "Ketu":    "spirituality, past life, detachment",
}

# [strip-3surfaces 2026-06-09] Plain-English version of PLANET_NATURE.
# Used by downstream surfaces (home_composer Year `area.note`, etc.) so
# the user never sees the planet-trait shorthand ("energy", "discipline",
# "authority", "intellect") that the audit flagged as energy-prose.
# Map keeps the SAME triplet shape so first/second/third theme works.
PLANET_NATURE_PLAIN = {
    "Sun":     "vitality, leadership, recognition",
    "Moon":    "mood, family ties, daily rhythm",
    "Mars":    "initiative, courage, property",
    "Mercury": "clear thinking, trade, communication",
    "Jupiter": "perspective, money, growth",
    "Venus":   "partnership, beauty, refinement",
    "Saturn":  "patient build, structure, longevity",
    "Rahu":    "ambition, unconventional gains, tech",
    "Ketu":    "introspection, release, mastery",
}


POWERFUL_HOUSES = {9, 10, 11}   # planet here = strong positive month
DIFFICULT_HOUSES = {6, 8, 12}   # planet here = challenging month


def _months_since_birthday(birth_date: str) -> int:
    try:
        born  = date.fromisoformat(birth_date[:10])
        today = date.today()
        # Birthday this year
        try:
            birthday_this_year = born.replace(year=today.year)
        except ValueError:
            birthday_this_year = born.replace(year=today.year, day=28)
        if birthday_this_year > today:
            birthday_this_year = born.replace(year=today.year - 1)
        delta = (today - birthday_this_year).days
        return (delta // 30) % 12
    except Exception:
        return 0


def calculate_masik_phal(birth_date: str, planets: dict) -> dict:
    """
    Calculate current month's Masik Phal from birth_date and planets dict.
    No DB needed — pure calculation.
    """
    try:
        born = date.fromisoformat(birth_date[:10])
        age  = (date.today() - born).days // 365
    except Exception:
        age = 35

    month_offset = _months_since_birthday(birth_date)

    # Step 1 — get natal house positions
    natal_houses = {
        p: d.get("house", 1)
        for p, d in planets.items()
    }

    # Step 2 — Varshphal: apply annual cycle rotation based on age
    # Rule: running_year = age + 1, natal house → annual house via mod
    running_year = max(1, min(120, age + 1))
    varshphal = {
        p: ((h - 1 + (running_year - 1)) % 12) + 1
        for p, h in natal_houses.items()
        if 1 <= h <= 12
    }

    # Step 3 — Masik Phal: advance by month_offset
    masik = {
        p: ((h - 1 + month_offset) % 12) + 1
        for p, h in varshphal.items()
    }

    # Step 4 — analyse this month
    strong_planets  = []
    weak_planets    = []
    neutral_planets = []

    for planet, house in masik.items():
        nature = PLANET_NATURE.get(planet, "")
        theme  = HOUSE_THEMES.get(house, "")
        entry  = {
            "planet":  planet,
            "house":   house,
            "theme":   theme,
            "nature":  nature,
            "signal":  f"{planet} in house {house} — {theme}",
        }
        if house in POWERFUL_HOUSES:
            strong_planets.append(entry)
        elif house in DIFFICULT_HOUSES:
            weak_planets.append(entry)
        else:
            neutral_planets.append(entry)

    # Month name
    try:
        born       = date.fromisoformat(birth_date[:10])
        today      = date.today()
        try:
            bday_this_year = born.replace(year=today.year)
        except ValueError:
            bday_this_year = born.replace(year=today.year, day=28)
        if bday_this_year > today:
            bday_this_year = born.replace(year=today.year - 1)
        from dateutil.relativedelta import relativedelta
        month_start = bday_this_year + relativedelta(months=month_offset)
        month_name  = month_start.strftime("%B %Y")
    except Exception:
        month_name = f"Month {month_offset + 1}"

    return {
        "month_offset":    month_offset,
        "month_name":      month_name,
        "month_number":    month_offset + 1,
        "age":             age,
        "masik_placements": masik,
        "strong_planets":  strong_planets,
        "weak_planets":    weak_planets,
        "neutral_planets": neutral_planets,
        "summary":         _build_summary(month_name, strong_planets, weak_planets),
    }


def _build_summary(month_name: str, strong: list, weak: list) -> str:
    parts = []
    if strong:
        planets = ", ".join(p["planet"] for p in strong)
        parts.append(f"{planets} strong this month")
    if weak:
        planets = ", ".join(p["planet"] for p in weak)
        parts.append(f"{planets} under pressure this month")
    if not parts:
        return f"{month_name}: Neutral month — steady energy across all areas"
    return f"{month_name}: " + " | ".join(parts)


def build_masik_context_block(birth_date: str, planets: dict) -> str:
    """
    Format Masik Phal as LLM context block.
    """
    m   = calculate_masik_phal(birth_date, planets)

    lines = [
        "MASIK PHAL — MONTHLY CHART (Lal Kitab)",
        f"Current month: {m['month_name']} (month {m['month_number']} of annual cycle)",
        f"Summary: {m['summary']}",
    ]

    if m["strong_planets"]:
        lines.append("")
        lines.append("STRONG PLANETS THIS MONTH (houses 9/10/11 — peak results):")
        for p in m["strong_planets"]:
            lines.append(f"  ✓ {p['planet']} in house {p['house']} — {p['theme']}")
            lines.append(f"    {p['nature']} energy is fully available this month")

    if m["weak_planets"]:
        lines.append("")
        lines.append("CHALLENGED PLANETS THIS MONTH (houses 6/8/12 — apply remedies):")
        for p in m["weak_planets"]:
            lines.append(f"  ⚠ {p['planet']} in house {p['house']} — {p['theme']}")
            lines.append(f"    {p['nature']} area needs extra care this month")

    if m["neutral_planets"]:
        lines.append("")
        lines.append("NEUTRAL PLANETS THIS MONTH:")
        for p in m["neutral_planets"]:
            lines.append(f"  • {p['planet']} in house {p['house']} — {p['theme']}")

    lines += [
        "",
        "MASIK PHAL RULES FOR PREDICTION:",
        "  • Strong planet this month = act NOW in that planet's domain",
        "  • Weak planet this month = avoid major decisions in that domain",
        "  • Monthly chart overlays annual chart — both must agree for high confidence",
        "  • If Dasha + Varshphal + Masik all agree = highest confidence signal",
    ]

    return "\n".join(lines)
