"""
prashna_intent.py — The "Telepathic Onboarding" Sensor
========================================================
Casts a Prashna (horary) chart at the exact moment of user signup,
maps the Prashna Lagna to the user's natal D-1 houses, and detects
the user's current mental frequency — WHY they opened the app.

Called from: POST /api/v1/chart/create (after chart computation)
Input: birth chart data + signup timestamp + signup location
Output: intent dict with domain, house, wow_line, detail
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

INTENT_MAP = {
    1: {
        "domain": "identity",
        "frequency": "Self / Identity / Health",
        "wow_line": (
            "You have synced today because your internal navigation feels off "
            "- you are looking for a total reset of your personal direction."
        ),
        "detail": (
            "Your mental frequency at the moment of signup was tuned to your "
            "1st house - the house of self, body, and identity. Something about "
            "who you are or how you show up in the world has reached a tipping point."
        ),
    },
    2: {
        "domain": "wealth",
        "frequency": "Liquid Assets / Family Wealth",
        "wow_line": (
            "You are not just curious - your internal wealth-meter is red-lining "
            "over a specific cash-flow or family asset decision."
        ),
        "detail": (
            "Your mental frequency was locked onto your 2nd house - money, family "
            "resources, and what you own. A specific financial pressure brought you here."
        ),
    },
    3: {
        "domain": "communication",
        "frequency": "Travel / Communication / Siblings",
        "wow_line": (
            "A specific short-circuit in your immediate network or a sudden urge "
            "to relocate has triggered this sync."
        ),
        "detail": (
            "Your signup moment activated your 3rd house - courage, siblings, short "
            "travel, and communication. Something in your immediate circle needs attention."
        ),
    },
    4: {
        "domain": "home",
        "frequency": "Home / Property / Peace",
        "wow_line": (
            "You are seeking an exit strategy for a situation at home or a property "
            "matter that has cost you your peace for weeks."
        ),
        "detail": (
            "Your mental frequency was tuned to your 4th house - home, property, "
            "mother, and inner peace. A domestic situation has reached its limit."
        ),
    },
    5: {
        "domain": "creativity",
        "frequency": "Children / Creativity / Speculation",
        "wow_line": (
            "A specific creative pulse or a concern regarding a child or legacy "
            "project has reached a tipping point today."
        ),
        "detail": (
            "Your signup activated your 5th house - children, creativity, romance, "
            "and speculation. Something about creation or legacy is demanding attention."
        ),
    },
    6: {
        "domain": "conflict",
        "frequency": "Health / Debts / Conflict",
        "wow_line": (
            "You have hit sync because a hidden friction - a legal matter, a health "
            "dip, or a debt - is demanding a tactical response."
        ),
        "detail": (
            "Your mental frequency activated your 6th house - enemies, debts, disease, "
            "and daily struggle. A conflict or health concern is the real trigger."
        ),
    },
    7: {
        "domain": "partnership",
        "frequency": "Partnership / Marriage / Divorce",
        "wow_line": (
            "Your internal frequency is tuned to a partnership. You are here to see "
            "if the contract you are in can survive the next shift."
        ),
        "detail": (
            "Your signup moment locked onto your 7th house - marriage, business partners, "
            "and all one-to-one relationships. A partnership is at a crossroads."
        ),
    },
    8: {
        "domain": "transformation",
        "frequency": "Crisis / Other Peoples Money / Hidden Matters",
        "wow_line": (
            "You are navigating a shadow zone. You have connected because of a sudden "
            "intensity regarding money you do not control or a secret pressure."
        ),
        "detail": (
            "Your mental frequency hit your 8th house - other peoples money, sudden "
            "events, hidden matters, and transformation. Something beneath the surface "
            "is driving this moment."
        ),
    },
    9: {
        "domain": "purpose",
        "frequency": "Purpose / Fortune / Long Travel",
        "wow_line": (
            "You have hit a crossroads regarding your higher purpose - you are looking "
            "for the road to the next version of yourself."
        ),
        "detail": (
            "Your signup activated your 9th house - fortune, father, long travel, and "
            "dharma. You are seeking meaning, not just answers."
        ),
    },
    10: {
        "domain": "career",
        "frequency": "Career / Authority / Power",
        "wow_line": (
            "Your authority engine is under extreme pressure. You are here to see if "
            "your professional position is still functional."
        ),
        "detail": (
            "Your mental frequency was locked onto your 10th house - career, public "
            "status, and authority. A professional situation has reached critical mass."
        ),
    },
    11: {
        "domain": "gains",
        "frequency": "Market Gains / Network / Friends",
        "wow_line": (
            "A specific expansion signal has reached you - you are looking for the "
            "green light on a major market move or network deal."
        ),
        "detail": (
            "Your signup activated your 11th house - gains, income, networks, and "
            "fulfilled desires. You sense an opportunity and need confirmation."
        ),
    },
    12: {
        "domain": "liberation",
        "frequency": "Loss / Isolation / Foreign Lands",
        "wow_line": (
            "You are feeling an internal leak. You have synced because of a fear of "
            "loss or a strong urge to escape to a foreign land."
        ),
        "detail": (
            "Your mental frequency hit your 12th house - expenses, isolation, foreign "
            "lands, and spiritual liberation. Something is draining you, or calling "
            "you elsewhere."
        ),
    },
}


def _sign_to_number(sign):
    sign_clean = sign.strip().capitalize()
    if sign_clean in SIGNS:
        return SIGNS.index(sign_clean) + 1
    return 0


def _house_from_lagna(lagna_sign, target_sign):
    lagna_num = _sign_to_number(lagna_sign)
    target_num = _sign_to_number(target_sign)
    if not lagna_num or not target_num:
        return 0
    house = ((target_num - lagna_num) % 12) + 1
    return house


def compute_prashna_lagna(timestamp, latitude, longitude):
    try:
        import swisseph as swe
        swe.set_sid_mode(swe.SIDM_LAHIRI)

        if timestamp.tzinfo:
            ts_utc = timestamp.astimezone(timezone.utc)
        else:
            ts_utc = timestamp

        jd = swe.julday(
            ts_utc.year, ts_utc.month, ts_utc.day,
            ts_utc.hour + ts_utc.minute / 60.0 + ts_utc.second / 3600.0
        )

        cusps, ascmc = swe.houses(jd, latitude, longitude, b'P')
        asc_tropical = ascmc[0]
        aya = swe.get_ayanamsa(jd)
        asc_sidereal = (asc_tropical - aya) % 360
        sign_index = int(asc_sidereal / 30)
        prashna_sign = SIGNS[sign_index]

        logger.info(f"Prashna Lagna: {prashna_sign} ({asc_sidereal:.2f}deg) at {ts_utc}")
        return prashna_sign

    except ImportError:
        logger.warning("swisseph not available - using rough Prashna calculation")
        hour = timestamp.hour + timestamp.minute / 60.0
        sign_index = int((hour / 2) % 12)
        return SIGNS[sign_index]

    except Exception as e:
        logger.error(f"Prashna Lagna computation failed: {e}")
        return None


def detect_signup_intent(birth_lagna, signup_timestamp, signup_lat, signup_lng, first_name=""):
    try:
        prashna_lagna = compute_prashna_lagna(
            timestamp=signup_timestamp,
            latitude=signup_lat,
            longitude=signup_lng,
        )

        if not prashna_lagna:
            return {"error": "Could not compute Prashna Lagna"}

        intent_house = _house_from_lagna(birth_lagna, prashna_lagna)

        if not intent_house or intent_house not in INTENT_MAP:
            return {"error": f"Invalid house mapping: {intent_house}"}

        intent = INTENT_MAP[intent_house].copy()
        name_prefix = f"{first_name}, " if first_name else ""
        intent["personalized_wow"] = name_prefix + intent["wow_line"]

        return {
            "prashna_lagna": prashna_lagna,
            "birth_lagna": birth_lagna,
            "intent_house": intent_house,
            "domain": intent["domain"],
            "frequency": intent["frequency"],
            "wow_line": intent["wow_line"],
            "detail": intent["detail"],
            "personalized_wow": intent["personalized_wow"],
        }

    except Exception as e:
        logger.error(f"Signup intent detection failed: {e}")
        return {"error": str(e)}


def format_intent_for_welcome(intent):
    if "error" in intent:
        return ""

    return (
        f"PRASHNA-INTENT DETECTION (The user's current mental frequency):\n"
        f"At the exact moment of signup, the Prashna Lagna was {intent['prashna_lagna']}.\n"
        f"This falls in the user's {intent['intent_house']}th house from birth Lagna ({intent['birth_lagna']}).\n"
        f"Detected frequency: {intent['frequency']}\n"
        f"The user is most likely here because of: {intent['detail']}\n"
        f"Use this to inform Signal 1 (The Intent) - tell them WHY they opened the app.\n"
        f"Do NOT mention Prashna or horary. Say 'our system detected' or 'your current frequency shows'.\n"
    )
