"""
antar_engine/rarity_engine.py

Rarity Signal Engine
──────────────────────────────────────────────────────────────────────
Detects genuinely rare configurations in a user's chart + current timing.
These are the moments that make users say "how did it know?"

WHAT THIS DOES:
  Scans the user's chart against current dasha + transits and flags
  configurations that happen once every 5–29 years. These become
  "Rare Signal" cards in the UI — gold glow, special treatment.

  The rarity signals are:

  1. Triple System Alignment
     All 3 dasha systems (Vimsottari + Jaimini + Ashtottari) pointing
     at the same theme simultaneously. Happens ~once every 5-8 years.

  2. Saturn Return (29 years)
     Saturn in the same sign as natal Saturn. Massive life restructuring.
     Happens once every 29 years — the most famous astrological milestone.

  3. Jupiter Return (12 years)
     Jupiter returns to natal position. Expansion, new 12-year cycle.

  4. Rahu/Ketu Axis Return (18 years)
     Nodal axis returns to natal position. Karmic completion + new direction.

  5. Mutual Dasha Lords
     Current MD and AD lords are in each other's signs natally.
     Amplifies both energies. Very rare and potent.

  6. Peak Yoga Activation
     A major natal yoga is being activated by ALL current dasha lords.
     Full flowering — not partial.

  7. Dasha Sandhi (Junction Point)
     User is within 3 months of a major Mahadasha change.
     The most turbulent and transformational window.
     "The old chapter is ending. The new has not yet begun."

  8. Vimshottari + Ashtottari Confluence
     Both systems simultaneously point to the same planet.
     Amplified single-planet energy. Very specific and precise.

  9. Atmakaraka Dasha
     The soul's core planet (Atmakaraka) is currently running as MD or AD.
     Profound identity-level work is happening. Once per lifetime for MD.

  10. Age-Based Planetary Milestones
     Saturn return (29/58), Jupiter return (24/36/48/60),
     Rahu/Ketu returns (18/37/56). Age triggers with life-stage context.

USAGE:
    from antar_engine.rarity_engine import detect_rarity_signals

    signals = detect_rarity_signals(
        chart_data=chart_data,
        dashas=dashas,
        current_transits=current_transits,
        user_birth_date="1990-06-15"
    )
    # Returns list of RaritySignal dicts, sorted by rarity (rarest first)
    # Each signal has: type, title, rarity_label, message, urgency, window

CRITICAL RULE:
  These signals must always be framed as GIFTS, not warnings.
  Even Saturn return. Even Ketu dasha. Even Sade Sati.
  The framing is: "This is rare. This is real. Here is the gift in it."
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional


# ── Sign reference ────────────────────────────────────────────────────────────

SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

SIGN_LORDS = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn","Pisces":"Jupiter"
}

OWN_SIGNS = {
    "Sun":["Leo"], "Moon":["Cancer"], "Mars":["Aries","Scorpio"],
    "Mercury":["Gemini","Virgo"], "Jupiter":["Sagittarius","Pisces"],
    "Venus":["Taurus","Libra"], "Saturn":["Capricorn","Aquarius"],
    "Rahu":["Aquarius","Gemini"], "Ketu":["Scorpio","Sagittarius"],
}

DASHA_ENERGY_SHORT = {
    "Sun":     "Identity & Purpose",
    "Moon":    "Emotional Depth",
    "Mars":    "Action & Courage",
    "Mercury": "Intellect & Communication",
    "Jupiter": "Expansive Growth",
    "Venus":   "Heart & Beauty",
    "Saturn":  "Clarifying Pressure",
    "Rahu":    "Hungry Becoming",
    "Ketu":    "Releasing & Liberation",
}

# Domain themes per planet — for triple alignment detection
PLANET_DOMAIN_THEMES = {
    "Sun":     {"career", "identity", "authority", "recognition"},
    "Moon":    {"emotions", "home", "family", "inner_life"},
    "Mars":    {"action", "property", "courage", "energy"},
    "Mercury": {"business", "communication", "intellect", "education"},
    "Jupiter": {"expansion", "wealth", "wisdom", "marriage", "children"},
    "Venus":   {"love", "beauty", "creativity", "luxury"},
    "Saturn":  {"karma", "discipline", "structure", "longevity"},
    "Rahu":    {"ambition", "foreign", "technology", "disruption"},
    "Ketu":    {"spirituality", "liberation", "past_life", "detachment"},
}


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:10], fmt[:10])
        except:
            continue
    return datetime.utcnow()

def _sign_idx(sign: str) -> int:
    try:
        return SIGNS.index(sign)
    except ValueError:
        return 0

def _lord(sign: str) -> str:
    return SIGN_LORDS.get(sign, sign)

def _current_period(periods: list, now: datetime) -> Optional[dict]:
    for p in periods:
        if _parse_dt(p["start"]) <= now <= _parse_dt(p["end"]):
            return p
    return periods[0] if periods else None

def _months_until(dt: datetime, now: datetime) -> int:
    return max(0, int((dt - now).days / 30))

def _months_since(dt: datetime, now: datetime) -> int:
    return max(0, int((now - dt).days / 30))

def _find_atmakaraka(chart_data: dict) -> str:
    """Planet with highest degree (0-30) in its sign, excluding nodes."""
    max_deg = -1
    atm = "Sun"
    for planet, data in chart_data.get("planets", {}).items():
        if planet in ("Rahu", "Ketu"):
            continue
        deg = float(data.get("degree", 0))
        if deg > max_deg:
            max_deg = deg
            atm = planet
    return atm

def _current_antardasha(periods: list, now: datetime) -> Optional[dict]:
    current_md = _current_period(periods, now)
    if not current_md:
        return None
    md_start = _parse_dt(current_md["start"])
    md_end   = _parse_dt(current_md["end"])
    sub = [
        p for p in periods
        if _parse_dt(p["start"]) >= md_start
        and _parse_dt(p["end"]) <= md_end
        and p["lord_or_sign"] != current_md["lord_or_sign"]
    ]
    for p in sub:
        if _parse_dt(p["start"]) <= now <= _parse_dt(p["end"]):
            return p
    return None


# ══════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL SIGNAL DETECTORS
# ══════════════════════════════════════════════════════════════════════════════

def _detect_triple_alignment(chart_data: dict, dashas: dict, now: datetime) -> Optional[dict]:
    """
    All 3 dasha systems pointing at the same theme simultaneously.
    Happens ~once every 5-8 years. One of the strongest signals in Vedic timing.
    """
    vim = dashas.get("vimsottari", [])
    jai = dashas.get("jaimini", [])
    ash = dashas.get("ashtottari", [])

    vm = _current_period(vim, now)
    jm = _current_period(jai, now)
    am = _current_period(ash, now)

    if not (vm and jm and am):
        return None

    # Get planet for each system
    vim_planet = vm["lord_or_sign"]
    jai_planet = _lord(jm["lord_or_sign"])  # Jaimini uses signs, get lord
    ash_planet = am["lord_or_sign"]

    # Get domain themes for each
    vim_themes = PLANET_DOMAIN_THEMES.get(vim_planet, set())
    jai_themes = PLANET_DOMAIN_THEMES.get(jai_planet, set())
    ash_themes = PLANET_DOMAIN_THEMES.get(ash_planet, set())

    # Find shared themes across all 3
    triple_overlap = vim_themes & jai_themes & ash_themes
    double_overlap = (vim_themes & jai_themes) | (vim_themes & ash_themes) | (jai_themes & ash_themes)

    if triple_overlap:
        theme = list(triple_overlap)[0].replace("_", " ")
        return {
            "type": "triple_system_alignment",
            "rarity": "once every 5–8 years",
            "rarity_score": 9,
            "title": "All Three Timing Systems Are Speaking the Same Language",
            "message": (
                f"Right now, all three of your timing blueprints are pointing at the same theme: "
                f"{theme}. This kind of triple alignment happens rarely — perhaps once or twice in a decade. "
                f"When the universe sends the same message through three different channels simultaneously, "
                f"it is not a coincidence. It is a directive. This is your window. "
                f"Whatever is calling you in the domain of {theme} — this is when to answer it."
            ),
            "what_to_do": f"Act with full intention on anything related to {theme}. This window has an end date.",
            "window": f"Active now across all three timing systems.",
            "urgency": "exceptional",
            "planets": [vim_planet, jai_planet, ash_planet],
        }

    if len(double_overlap) >= 3:
        # Two systems agree — still significant
        theme = list(double_overlap)[0].replace("_", " ")
        return {
            "type": "double_system_alignment",
            "rarity": "once every 2–3 years",
            "rarity_score": 6,
            "title": "Two Timing Systems Are Amplifying the Same Theme",
            "message": (
                f"Two of your three timing blueprints are both pointing at {theme} right now. "
                f"This double signal means the universe is being deliberate. "
                f"High-signal windows like this are worth your full attention."
            ),
            "what_to_do": f"Prioritize {theme} decisions and actions during this period.",
            "window": "Active now.",
            "urgency": "high",
            "planets": [vim_planet, jai_planet],
        }

    return None


def _detect_saturn_return(chart_data: dict, current_transits: list, user_birth_date: str, now: datetime) -> Optional[dict]:
    """
    Saturn in same sign as natal Saturn. Once every 29 years.
    The most significant life restructuring milestone in Vedic timing.
    """
    natal_saturn_sign = chart_data.get("planets", {}).get("Saturn", {}).get("sign")
    if not natal_saturn_sign:
        return None

    transit_map = _build_transit_map(current_transits)
    current_saturn_sign = transit_map.get("Saturn")

    if current_saturn_sign != natal_saturn_sign:
        return None

    # Calculate which Saturn return this is
    birth_dt = _parse_dt(user_birth_date)
    years_old = (now - birth_dt).days / 365.25

    return_number = "first" if years_old < 35 else "second"
    return_age = "29" if return_number == "first" else "58"

    return {
        "type": "saturn_return",
        "rarity": f"once every 29 years (your {return_number} Saturn return)",
        "rarity_score": 10,
        "title": f"Your {return_number.title()} Saturn Return Is Active",
        "message": (
            f"This happens once every 29 years — you are in one of the most significant "
            f"life restructuring periods that exists. Saturn has returned to the exact position "
            f"it held when you were born. It is asking one fundamental question: "
            f"what in your life is real, and what have you been maintaining out of habit, fear, or obligation? "
            f"What falls away now was never truly yours. What remains will define the next 29 years. "
            f"This is not a crisis. This is a calibration."
        ),
        "what_to_do": (
            "Get radically honest about your career, relationships, and life structure. "
            "Make the changes you have been avoiding. Saturn rewards courage and integrity right now."
        ),
        "window": "Saturn stays in a sign for 2.5 years — this restructuring window is still active.",
        "urgency": "very_high",
        "planets": ["Saturn"],
    }


def _detect_jupiter_return(chart_data: dict, current_transits: list, now: datetime) -> Optional[dict]:
    """
    Jupiter back in natal position. New 12-year expansion cycle begins.
    Once every 12 years.
    """
    natal_jupiter_sign = chart_data.get("planets", {}).get("Jupiter", {}).get("sign")
    if not natal_jupiter_sign:
        return None

    transit_map = _build_transit_map(current_transits)
    current_jupiter_sign = transit_map.get("Jupiter")

    if current_jupiter_sign != natal_jupiter_sign:
        return None

    return {
        "type": "jupiter_return",
        "rarity": "once every 12 years",
        "rarity_score": 8,
        "title": "A New 12-Year Expansion Cycle Is Beginning",
        "message": (
            "Jupiter has returned to the exact position it held when you were born. "
            "This happens once every 12 years and marks the beginning of a completely new "
            "growth cycle in your life. The seeds you plant right now — in career, relationships, "
            "wisdom, and wealth — will define the next 12 years. "
            "What do you most want to expand into? This is your moment to decide with clarity."
        ),
        "what_to_do": (
            "Plant seeds deliberately. Start the project, make the move, have the conversation "
            "you have been postponing. Jupiter is leaning toward yes for you right now."
        ),
        "window": "Jupiter stays in a sign for approximately 12 months. Act now.",
        "urgency": "high",
        "planets": ["Jupiter"],
    }


def _detect_rahu_ketu_return(chart_data: dict, current_transits: list, now: datetime) -> Optional[dict]:
    """
    Rahu/Ketu axis returning to natal position. Karmic completion.
    Once every 18 years.
    """
    natal_rahu_sign = chart_data.get("planets", {}).get("Rahu", {}).get("sign")
    if not natal_rahu_sign:
        return None

    transit_map = _build_transit_map(current_transits)
    current_rahu_sign = transit_map.get("Rahu")

    if current_rahu_sign != natal_rahu_sign:
        return None

    return {
        "type": "rahu_ketu_return",
        "rarity": "once every 18 years",
        "rarity_score": 9,
        "title": "A Major Karmic Completion Is Happening",
        "message": (
            "The karmic axis of your chart has returned to where it was when you were born. "
            "This happens once every 18 years and marks a profound moment of karmic completion — "
            "patterns that have been running for 18 years are now completing. "
            "Old themes, old relationships, old ambitions are either fulfilling or finally releasing. "
            "Simultaneously, a completely new karmic direction is opening. "
            "What you've been chasing and what you've been avoiding are both shifting. "
            "This is one of the most significant spiritual turning points in your life cycle."
        ),
        "what_to_do": (
            "Let go of what has completed. Embrace what is calling you forward. "
            "The direction that feels foreign or uncomfortable is often exactly right now."
        ),
        "window": "The nodal axis shifts every 18 months — the full return window lasts about 6 months.",
        "urgency": "very_high",
        "planets": ["Rahu", "Ketu"],
    }


def _detect_dasha_sandhi(dashas: dict, now: datetime) -> Optional[dict]:
    """
    Within 90 days of a major Mahadasha change.
    The most turbulent and transformational transition point.
    "Between chapters" — neither the old nor the new.
    """
    vim = dashas.get("vimsottari", [])
    current_md = _current_period(vim, now)
    if not current_md:
        return None

    md_end = _parse_dt(current_md["end"])
    months_to_end = _months_until(md_end, now)
    months_since_start = _months_since(_parse_dt(current_md["start"]), now)

    # Find next period
    next_md = None
    for p in vim:
        if _parse_dt(p["start"]) > now:
            next_md = p
            break

    # Entering sandhi (within 3 months of end)
    if 0 < months_to_end <= 3:
        next_planet = next_md["lord_or_sign"] if next_md else "a new cycle"
        next_energy = DASHA_ENERGY_SHORT.get(next_planet, next_planet)
        current_energy = DASHA_ENERGY_SHORT.get(current_md["lord_or_sign"], current_md["lord_or_sign"])

        return {
            "type": "dasha_sandhi_ending",
            "rarity": f"once every {int(current_md.get('duration', 7))}+ years",
            "rarity_score": 8,
            "title": "A Life Chapter Is Closing",
            "message": (
                f"You are in the final {months_to_end} months of your {current_energy} chapter — "
                f"one of the most significant transition windows in your timing blueprint. "
                f"The space between chapters is where the most profound clarification happens. "
                f"What does this chapter want you to complete before it closes? "
                f"In {months_to_end} months, a {next_energy} chapter begins — "
                f"a completely different energy and curriculum. "
                f"What you finish now, you carry forward transformed."
            ),
            "what_to_do": (
                f"Complete what is unfinished. Release what cannot come with you. "
                f"Prepare yourself for a {next_energy} period — what does that demand of you?"
            ),
            "window": f"This transition window closes in approximately {months_to_end} months.",
            "urgency": "very_high",
            "planets": [current_md["lord_or_sign"]],
        }

    # Just entered new chapter (within 3 months of start)
    if months_since_start <= 3 and next_md:
        current_energy = DASHA_ENERGY_SHORT.get(current_md["lord_or_sign"], current_md["lord_or_sign"])
        return {
            "type": "dasha_sandhi_opening",
            "rarity": f"once every {int(current_md.get('duration', 7))}+ years",
            "rarity_score": 7,
            "title": "A New Life Chapter Has Just Begun",
            "message": (
                f"You have just entered a new {current_energy} chapter — "
                f"it began only {months_since_start} months ago. "
                f"The opening of a new major life chapter is one of the most powerful "
                f"windows in your timing blueprint. The energy is fresh and the direction is forming. "
                f"What you build and begin right now carries unusual momentum. "
                f"The seeds of this chapter's entire arc are being planted right now."
            ),
            "what_to_do": (
                f"Be deliberate about what you are starting. "
                f"The patterns, relationships, and habits you establish in these opening months "
                f"will shape the entire chapter. Begin as you mean to continue."
            ),
            "window": f"The opening window of this chapter is active for the next {3 - months_since_start} months.",
            "urgency": "high",
            "planets": [current_md["lord_or_sign"]],
        }

    return None


def _detect_atmakaraka_dasha(chart_data: dict, dashas: dict, now: datetime) -> Optional[dict]:
    """
    Atmakaraka (soul planet) running as current Mahadasha or Antardasha.
    The deepest identity-level work. MD happens once per lifetime.
    """
    atmakaraka = _find_atmakaraka(chart_data)

    vim = dashas.get("vimsottari", [])
    current_md = _current_period(vim, now)
    current_ad = _current_antardasha(vim, now)

    if not current_md:
        return None

    md_planet = current_md["lord_or_sign"]
    ad_planet = current_ad["lord_or_sign"] if current_ad else None

    if md_planet == atmakaraka:
        atm_energy = DASHA_ENERGY_SHORT.get(atmakaraka, atmakaraka)
        return {
            "type": "atmakaraka_mahadasha",
            "rarity": "once in a lifetime (for the full Mahadasha)",
            "rarity_score": 10,
            "title": "Your Soul's Core Planet Is Running Your Life Right Now",
            "message": (
                f"Your Atmakaraka — the planet that carries your soul's deepest lesson — "
                f"is currently running as your primary life chapter. "
                f"This is the most profound identity-level period in your entire timing blueprint. "
                f"Every major theme of your life is crystallizing around {atm_energy}. "
                f"Who you truly are, beneath every role and every story, is being asked to emerge. "
                f"This is the chapter that defines the soul's purpose for this lifetime."
            ),
            "what_to_do": (
                "Ask yourself: What does my soul most want to express in this life? "
                "Not what others expect. Not what pays the bills. What is true. "
                "This chapter rewards radical authenticity above all else."
            ),
            "window": f"This chapter runs for the full {current_md.get('duration', 'several')} years.",
            "urgency": "very_high",
            "planets": [atmakaraka],
        }

    if ad_planet == atmakaraka:
        atm_energy = DASHA_ENERGY_SHORT.get(atmakaraka, atmakaraka)
        return {
            "type": "atmakaraka_antardasha",
            "rarity": "occurs periodically throughout life",
            "rarity_score": 7,
            "title": "Your Soul's Core Lesson Is the Active Sub-Theme",
            "message": (
                f"Your Atmakaraka — the planet carrying your soul's deepest work — "
                f"is the current sub-theme in your life chapter. "
                f"This is a concentrated period of soul-level clarity. "
                f"Questions about your true identity, purpose, and direction are surfacing with unusual intensity. "
                f"Pay attention to what your inner voice is saying during this time."
            ),
            "what_to_do": (
                "Journal. Meditate. Have the conversations that matter. "
                "Your intuition is particularly sharp right now."
            ),
            "window": "Active for the duration of the current sub-cycle.",
            "urgency": "high",
            "planets": [atmakaraka],
        }

    return None


def _detect_mutual_dasha_lords(chart_data: dict, dashas: dict, now: datetime) -> Optional[dict]:
    """
    Current MD and AD lords are in each other's signs natally (mutual reception/parivartana).
    Amplifies both energies. Creates a powerful exchange.
    """
    vim = dashas.get("vimsottari", [])
    current_md = _current_period(vim, now)
    current_ad = _current_antardasha(vim, now)

    if not (current_md and current_ad):
        return None

    md_planet = current_md["lord_or_sign"]
    ad_planet = current_ad["lord_or_sign"]

    if md_planet == ad_planet:
        return None

    # Get natal signs of each planet
    planets = chart_data.get("planets", {})
    md_natal_sign = planets.get(md_planet, {}).get("sign")
    ad_natal_sign = planets.get(ad_planet, {}).get("sign")

    if not (md_natal_sign and ad_natal_sign):
        return None

    # Check mutual reception: MD planet in AD planet's own sign, and vice versa
    md_in_ad_sign = md_natal_sign in OWN_SIGNS.get(ad_planet, [])
    ad_in_md_sign = ad_natal_sign in OWN_SIGNS.get(md_planet, [])

    if md_in_ad_sign and ad_in_md_sign:
        md_energy = DASHA_ENERGY_SHORT.get(md_planet, md_planet)
        ad_energy = DASHA_ENERGY_SHORT.get(ad_planet, ad_planet)

        return {
            "type": "mutual_dasha_lords",
            "rarity": "rare — fewer than 5% of dasha periods",
            "rarity_score": 8,
            "title": "Two Timing Energies Are in Perfect Exchange",
            "message": (
                f"Your current major chapter ({md_energy}) and sub-theme ({ad_energy}) "
                f"are in a rare mutual exchange — each one amplifying the other. "
                f"When two timing energies are in perfect reception like this, "
                f"both themes operate at full power simultaneously. "
                f"The qualities of {md_energy} and {ad_energy} are not just present — "
                f"they are feeding each other, creating an unusually potent period."
            ),
            "what_to_do": (
                f"Work with both energies consciously. "
                f"The intersection of {md_energy} and {ad_energy} "
                f"is where your most significant opportunities live right now."
            ),
            "window": "Active for the duration of the current sub-cycle.",
            "urgency": "high",
            "planets": [md_planet, ad_planet],
        }

    return None


def _detect_age_milestones(user_birth_date: str, now: datetime) -> Optional[dict]:
    """
    Age-based planetary milestones: Saturn returns (29, 58),
    Jupiter returns (24, 36, 48, 60), Rahu/Ketu returns (18, 37, 56).
    """
    birth_dt = _parse_dt(user_birth_date)
    age_years = (now - birth_dt).days / 365.25

    # Check within ±6 months of each milestone
    milestones = [
        (18,  "rahu_ketu", "Rahu/Ketu",   "Your first karmic axis return — the direction of your ambitions and your soul work shifts completely at 18.",
               "Let your authentic desires — not others' expectations — guide your next choices."),
        (24,  "jupiter",  "Jupiter",      "Your first Jupiter return — a new 12-year expansion cycle begins. Your worldview and opportunities expand.",
               "What do you most want to grow into in the next 12 years? Start building toward it now."),
        (29,  "saturn",   "Saturn",       "Your first Saturn return — the most famous life restructuring point. What is real stays. What isn't, goes.",
               "Make the changes you have been avoiding. Saturn rewards courage and honesty above all else."),
        (36,  "jupiter",  "Jupiter",      "Your second Jupiter return — a new cycle of expansion, wisdom, and opportunity opens.",
               "You are wiser than at 24. Use that wisdom to build something that matters."),
        (37,  "rahu_ketu","Rahu/Ketu",    "Your second nodal return — karmic patterns from your first 18 years are completing or evolving.",
               "What chapter of your life is completing? What new direction is calling you?"),
        (48,  "jupiter",  "Jupiter",      "Your fourth Jupiter return — the expansion of wisdom, legacy, and inner knowing peaks.",
               "What is your gift to the world? This is the time to offer it fully."),
        (56,  "rahu_ketu","Rahu/Ketu",    "Your third nodal return — a profound karmic completion. The soul's work of this lifetime crystallizes.",
               "What have you truly learned? What do you most want to pass forward?"),
        (58,  "saturn",   "Saturn",       "Your second Saturn return — a deep review of your entire life's structure and legacy.",
               "Strip away everything that isn't essential. What remains is who you truly are."),
        (60,  "jupiter",  "Jupiter",      "Your fifth Jupiter return — the Shastiabda Poorti. A full life cycle completed. Profound renewal.",
               "Celebrate what you have built. A new, lighter, wiser chapter is beginning."),
    ]

    for age, planet_type, planet_name, message, action in milestones:
        diff = abs(age_years - age)
        if diff <= 0.5:  # Within 6 months
            months_to = int((age - age_years) * 12) if age > age_years else 0
            timing = f"happening right now" if diff < 0.1 else f"within the next {months_to} months" if age > age_years else "just activated"

            return {
                "type": f"age_milestone_{planet_type}_{age}",
                "rarity": f"once at age {age}",
                "rarity_score": 9,
                "title": f"A Major Life Milestone: Your Age-{age} {planet_name} Activation",
                "message": (
                    f"You are at one of the most significant milestones in the human timing blueprint: "
                    f"your age-{age} {planet_name} activation. This is {timing}. "
                    f"{message}"
                ),
                "what_to_do": action,
                "window": f"This milestone window is active for approximately 12 months.",
                "urgency": "very_high",
                "planets": [planet_name.split("/")[0]],
            }

    return None


# ── Helper ────────────────────────────────────────────────────────────────────

def _build_transit_map(current_transits: list) -> dict:
    transit_map = {}
    for t in current_transits:
        if isinstance(t, dict):
            p = t.get("planet", t.get("name", ""))
            s = t.get("current_sign", t.get("sign", t.get("transit_sign", "")))
            if p and s:
                transit_map[p] = s
    return transit_map


# ══════════════════════════════════════════════════════════════════════════════
# MASTER DETECTOR — call this from main.py
# ══════════════════════════════════════════════════════════════════════════════

def detect_rarity_signals(
    chart_data: dict,
    dashas: dict,
    current_transits: list,
    user_birth_date: str,
) -> list[dict]:
    """
    Main entry point. Returns list of active rarity signals sorted by rarity_score.

    Usage in main.py /predict endpoint:
        from antar_engine.rarity_engine import detect_rarity_signals

        rarity_signals = detect_rarity_signals(
            chart_data=chart_data,
            dashas=dashas,
            current_transits=current_transits,
            user_birth_date=chart_record["birth_date"],
        )
        # Pass into prompt_builder and into the response

    Each signal dict has:
        type, rarity, rarity_score (1-10), title, message,
        what_to_do, window, urgency, planets
    """
    now = datetime.utcnow()
    signals = []

    detectors = [
        lambda: _detect_triple_alignment(chart_data, dashas, now),
        lambda: _detect_saturn_return(chart_data, current_transits, user_birth_date, now),
        lambda: _detect_jupiter_return(chart_data, current_transits, now),
        lambda: _detect_rahu_ketu_return(chart_data, current_transits, now),
        lambda: _detect_dasha_sandhi(dashas, now),
        lambda: _detect_atmakaraka_dasha(chart_data, dashas, now),
        lambda: _detect_mutual_dasha_lords(chart_data, dashas, now),
        lambda: _detect_age_milestones(user_birth_date, now),
    ]

    for detector in detectors:
        try:
            result = detector()
            if result:
                signals.append(result)
        except Exception as e:
            # Never let a failed detector break the prediction flow
            print(f"Rarity detector error: {e}")
            continue

    # Sort by rarity score (rarest first)
    signals.sort(key=lambda x: x.get("rarity_score", 0), reverse=True)

    return signals


def rarity_signals_to_context_block(signals: list[dict]) -> str:
    """
    Convert rarity signals into a clean context block for the LLM prompt.
    Injected into prompt_builder.py.
    """
    if not signals:
        return ""

    lines = ["═══ RARE TIMING SIGNALS (treat these as high-priority context) ═══"]

    for sig in signals[:2]:  # Max 2 rarity signals in any single prompt
        lines += [
            f"[RARE SIGNAL: {sig['title']}]",
            f"Rarity: {sig['rarity']}",
            f"Message: {sig['message']}",
            f"What to do: {sig['what_to_do']}",
            f"Window: {sig['window']}",
            "",
        ]

    lines.append("═══ END RARE SIGNALS ═══")
    return "\n".join(lines)
