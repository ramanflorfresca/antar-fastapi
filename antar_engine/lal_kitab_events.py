"""
Deterministic Lal Kitab layer (Roop Chand Joshi tradition; the two D.P.B. books in the
owner's library). No LLM. Lal Kitab uses a FIXED frame: Aries is house 1, Taurus 2, ...
Pisces 12 (house = sign number), regardless of the lagna.

What it computes, per the books (rule ids tagged for later feedback grading):
  - dormant houses: empty AND not sighted; sighting 1-7 and 4-10 full, 3-11 and 5-9 half,
    2-9 and 5-12 quarter, earlier house to later only, houses 7-12 cast nothing
  - dormant-house wake-up: the house's activation planet (1 Mars, 2 Moon, 3 Mercury,
    4 Moon, 5 Sun, 6 Rahu, 7 Venus, 8 Moon, 9 Jupiter, 10 Saturn, 11 Jupiter, 12 Ketu)
    reaches its maturity age
  - planet maturity windows: result starts at the planet's age and runs the same number
    of years again (Jupiter 16, Sun 22, Moon 24, Venus 25, Mars 28, Mercury 17,
    Saturn 36, Rahu 42, Ketu 48: the ages in Roop Chand's own text)
  - explicit age triggers the books state for a planet in a house
  - blind planets, and a gambling/speculation tendency flag (the books give a register,
    not a method: tendency only, no win/loss call)
Distinct from lal_kitab_umra.py (house activation ages), which is left untouched.
"""
from typing import Dict, List

SIGN_HOUSE = lambda sign_idx: sign_idx + 1

MATURITY = {"Jupiter": 16, "Sun": 22, "Moon": 24, "Venus": 25, "Mars": 28,
            "Mercury": 17, "Saturn": 36, "Rahu": 42, "Ketu": 48}
ACTIVATION_PLANET = {1: "Mars", 2: "Moon", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Rahu",
                     7: "Venus", 8: "Moon", 9: "Jupiter", 10: "Saturn", 11: "Jupiter",
                     12: "Ketu"}
SIGHT = {1: {7: 1.0}, 4: {10: 1.0}, 3: {11: 0.5}, 5: {9: 0.5, 12: 0.25}, 2: {9: 0.25}}

# (planet, house): (age, sign, text) — stated explicitly in the books (ledger section 2)
AGE_TRIGGERS = {
    ("Moon", 10): (43, "+", "unforeseen gain"),
    ("Mars", 2): (12, "-", "money ruin"),
    ("Mars", 11): (54, "+", "good money"),
    ("Mercury", 11): (45, "+", "gains"),
    ("Mercury", 8): (14, "-", "big loss"),
    ("Jupiter", 2): (39, "+", "big money"),
    ("Jupiter", 12): (25, "-", "big expenditure"),
    ("Rahu", 8): (28, "+", "sudden money"),
    ("Venus", 1): (25, "-", "age to avoid for marriage"),
}

LOSS_PRONE = {("Rahu", 2), ("Rahu", 7), ("Rahu", 8), ("Ketu", 2), ("Moon", 8), ("Saturn", 9),
              ("Mars", 5), ("Mercury", 2), ("Mercury", 12)}
GAIN_LEANING = {("Jupiter", 4), ("Jupiter", 5), ("Sun", 5), ("Venus", 5)}


def lal_kitab_profile(planet_signs: Dict[str, int], age: int, horizon: int = 3) -> dict:
    """planet_signs: {'Sun': 0..11 sidereal sign index, ...} for the 9 grahas."""
    house = {p: SIGN_HOUSE(s) for p, s in planet_signs.items()}
    occupied = {h for h in house.values()}

    sighted = set()
    for p, h in house.items():
        for tgt in SIGHT.get(h, {}):
            sighted.add(tgt)

    dormant = [h for h in range(1, 13) if h not in occupied and h not in sighted]

    wake = []
    for h in dormant:
        ap = ACTIVATION_PLANET[h]
        a = MATURITY[ap]
        if age - 1 <= a <= age + horizon:
            wake.append({"rule": "LK.dormant_house_wakes_at_activation_planet_age",
                         "house": h, "planet": ap, "age": a})

    windows = []
    for p, a in MATURITY.items():
        if a <= age < 2 * a:
            windows.append({"rule": "LK.planet_maturity_window_active", "planet": p,
                            "house": house[p], "from_age": a, "to_age": 2 * a})
        elif age < a <= age + horizon:
            windows.append({"rule": "LK.planet_maturity_window_opening", "planet": p,
                            "house": house[p], "from_age": a, "to_age": 2 * a})

    triggers = []
    for (p, h), (a, sign, txt) in AGE_TRIGGERS.items():
        if house.get(p) == h and age - 1 <= a <= age + horizon:
            triggers.append({"rule": f"LK.age_trigger_{p}_{h}", "age": a, "sign": sign, "what": txt})

    tens = [p for p, h in house.items() if h == 10]
    blind = []
    if len(tens) >= 2:
        blind.append({"rule": "LK.blind_planets_two_in_10th", "planets": tens})
    if house.get("Sun") == 4 and house.get("Saturn") == 7:
        blind.append({"rule": "LK.night_blind_sun4_saturn7"})

    loss = sorted(f"{p} in {h}" for p, h in house.items() if (p, h) in LOSS_PRONE)
    gain = sorted(f"{p} in {h}" for p, h in house.items() if (p, h) in GAIN_LEANING)
    spec = ("mixed" if loss and gain else "loss-prone" if loss else
            "gain-leaning" if gain else "none")

    return {"age": age, "houses": house, "dormant_houses": dormant, "wake_ups": wake,
            "maturity_windows": windows, "age_triggers": triggers, "blind": blind,
            "speculation_tendency": {"flag": spec, "loss_placements": loss, "gain_placements": gain}}
