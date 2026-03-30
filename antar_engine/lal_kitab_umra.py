"""
antar_engine/lal_kitab_umra.py

Umra (Age Activation) — Lal Kitab tradition.
Each house becomes fully active at a specific age.
When a house activates, its natal planets deliver their full results.
This is why the same chart produces different outcomes at different ages.
"""

from datetime import date

# Umra activation table — house: list of activation ages
UMRA_TABLE = {
    1:  [1],
    2:  [2],
    3:  [3, 16],
    4:  [4],
    5:  [5, 15],
    6:  [6],
    7:  [7, 34],
    8:  [8, 36],
    9:  [9, 30],
    10: [10, 22, 48],
    11: [11, 54],
    12: [12, 60],
}

HOUSE_THEMES = {
    1:  "Self, personality, physical body, overall life direction",
    2:  "Wealth accumulation, family bonds, speech patterns",
    3:  "Courage, communication, siblings, short ventures",
    4:  "Home, mother, property, emotional foundation",
    5:  "Intelligence, children, creativity, past karma",
    6:  "Enemies, debts, disease, service, litigation",
    7:  "Marriage, partnerships, business deals, public life",
    8:  "Transformation, inheritance, hidden matters, longevity",
    9:  "Fortune, father, dharma, higher learning, spirituality",
    10: "Career peak, authority, public status, government",
    11: "Major gains, income surge, elder siblings, aspirations",
    12: "Foreign connections, spirituality, liberation, expenses",
}

ACTIVATION_URGENCY = {
    7:  "Marriage and partnership window — most critical activation",
    10: "Career peak window — major professional breakthrough possible",
    9:  "Fortune window — dharma and luck fully available",
    11: "Gains window — income and aspirations reach peak",
    8:  "Transformation window — deep change, inheritance possible",
    12: "Liberation window — foreign opportunities or spiritual shift",
}

WINDOW_YEARS = 3  # activation effect lasts this many years


def calculate_umra(birth_date: str, planets: dict) -> dict:
    """
    Calculate Umra age activation for a chart.
    Returns which houses are currently active, recently activated,
    or approaching activation — and what it means for this person.
    """
    try:
        born = date.fromisoformat(birth_date[:10])
        age  = (date.today() - born).days // 365
    except Exception:
        age = 35

    active_now    = []  # currently in activation window
    approaching   = []  # activates within next 3 years
    recently_done = []  # activated within past 2 years

    for house, ages in UMRA_TABLE.items():
        for activation_age in ages:
            years_since = age - activation_age
            years_until = activation_age - age

            if 0 <= years_since <= WINDOW_YEARS:
                # Currently active
                years_remaining = WINDOW_YEARS - years_since
                planets_in_house = [
                    p for p, d in planets.items()
                    if d.get("house") == house
                ]
                active_now.append({
                    "house":            house,
                    "activation_age":   activation_age,
                    "current_age":      age,
                    "years_remaining":  years_remaining,
                    "theme":            HOUSE_THEMES[house],
                    "urgency":          ACTIVATION_URGENCY.get(house, ""),
                    "planets_here":     planets_in_house,
                    "signal":           _build_signal(house, planets_in_house, age, activation_age),
                })

            elif 0 < years_until <= 3:
                # Approaching
                planets_in_house = [
                    p for p, d in planets.items()
                    if d.get("house") == house
                ]
                approaching.append({
                    "house":          house,
                    "activation_age": activation_age,
                    "years_until":    years_until,
                    "theme":          HOUSE_THEMES[house],
                    "planets_here":   planets_in_house,
                    "signal":         f"House {house} activates at age {activation_age} — prepare now",
                })

            elif -2 <= years_since < 0:
                # Just passed
                recently_done.append({
                    "house":          house,
                    "activation_age": activation_age,
                    "years_ago":      abs(years_since),
                    "theme":          HOUSE_THEMES[house],
                })

    return {
        "current_age":    age,
        "active_now":     active_now,
        "approaching":    approaching,
        "recently_done":  recently_done,
        "summary":        _build_summary(age, active_now, approaching),
    }


def _build_signal(house: int, planets: list, age: int, activation_age: int) -> str:
    theme = HOUSE_THEMES[house]
    urgency = ACTIVATION_URGENCY.get(house, "")
    if not planets:
        return f"House {house} active (age {activation_age}) — {theme}. No natal planets here — house lord's results deliver."
    planet_str = " + ".join(planets)
    base = f"House {house} active (age {activation_age}) — {planet_str} delivering results now. {theme}."
    if urgency:
        base += f" {urgency}."
    return base


def _build_summary(age: int, active_now: list, approaching: list) -> str:
    if not active_now and not approaching:
        return f"Age {age}: No major house activations currently. Results come through dasha timing."
    parts = []
    if active_now:
        houses = [str(a["house"]) for a in active_now]
        parts.append(f"Houses {', '.join(houses)} are delivering results NOW (Umra active)")
    if approaching:
        houses = [f"H{a['house']} at age {a['activation_age']}" for a in approaching]
        parts.append(f"Approaching activations: {', '.join(houses)}")
    return " | ".join(parts)


def build_umra_context_block(birth_date: str, planets: dict) -> str:
    """
    Format Umra analysis as LLM context block.
    Called from build_complete_context in chart_context_builder.py
    """
    umra = calculate_umra(birth_date, planets)
    age  = umra["current_age"]

    lines = [
        "UMRA — AGE ACTIVATION (Lal Kitab)",
        f"Current age: {age}",
        f"Summary: {umra['summary']}",
    ]

    if umra["active_now"]:
        lines.append("")
        lines.append("CURRENTLY ACTIVE HOUSES (peak results available now):")
        for a in umra["active_now"]:
            lines.append(f"  ★ House {a['house']} — {a['theme']}")
            lines.append(f"    {a['signal']}")
            if a["urgency"]:
                lines.append(f"    ⚡ {a['urgency']}")
            if a["planets_here"]:
                lines.append(f"    Planets delivering: {', '.join(a['planets_here'])}")
            lines.append(f"    Window: {a['years_remaining']} years remaining")

    if umra["approaching"]:
        lines.append("")
        lines.append("APPROACHING ACTIVATIONS (prepare now):")
        for a in umra["approaching"]:
            lines.append(f"  → House {a['house']} activates at age {a['activation_age']} ({a['years_until']}yr away)")
            lines.append(f"    {a['theme']}")
            if a["planets_here"]:
                lines.append(f"    Planets that will deliver: {', '.join(a['planets_here'])}")

    lines += [
        "",
        "UMRA RULES FOR PREDICTION:",
        "  • If house is NOT yet active — planet's results are PENDING, not failed",
        "  • If house IS active — this is the window, act now",
        "  • Dasha + Umra alignment = highest confidence prediction",
        "  • Always tell user if their question relates to an active or pending house",
    ]

    return "\n".join(lines)
