"""
antar_engine/tara_bala.py
==========================
Tara Bala (Star Strength) — classical Vedic daily timing system.

Counts nakshatras from natal Moon nakshatra to today's transit Moon nakshatra.
The count modulo 9 gives the tara category, which determines whether the day
favors action, caution, or waiting.

Phase 2 of daily prediction engine.
Called by: daily_transit_analyzer.py
"""

from __future__ import annotations
from typing import Optional

# ── 27 Nakshatras in order ────────────────────────────────────────────────────

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

_NAK_INDEX = {n: i for i, n in enumerate(NAKSHATRAS)}

# ── 9 Tara Categories ────────────────────────────────────────────────────────

TARA_SEQUENCE = [
    {
        "name": "Janma",
        "quality": "caution",
        "advice": "Stay low, don't launch new initiatives. Self-awareness day.",
    },
    {
        "name": "Sampat",
        "quality": "favorable",
        "advice": "Gains, commerce, and financial moves are favored.",
    },
    {
        "name": "Vipat",
        "quality": "unfavorable",
        "advice": "Avoid risk. Delay important decisions if possible.",
    },
    {
        "name": "Kshema",
        "quality": "favorable",
        "advice": "Wellbeing, peace, and harmony prevail. Good for relationships.",
    },
    {
        "name": "Pratyari",
        "quality": "unfavorable",
        "advice": "Resistance is active. Wait — don't force outcomes today.",
    },
    {
        "name": "Sadhana",
        "quality": "favorable",
        "advice": "Achievement energy. Goals ripen — push toward what matters.",
    },
    {
        "name": "Naidhana",
        "quality": "cautious",
        "advice": "Endings and introspection. Wrap up, don't begin.",
    },
    {
        "name": "Mitra",
        "quality": "favorable",
        "advice": "Allies and partnerships are activated. Reach out.",
    },
    {
        "name": "Ati-Mitra",
        "quality": "very_favorable",
        "advice": "Best day for key moves. Maximum support from the stars.",
    },
]


def compute_tara_bala(natal_moon_nak: str, today_moon_nak: str) -> Optional[dict]:
    """
    Compute Tara Bala from natal Moon nakshatra to today's Moon nakshatra.

    Args:
        natal_moon_nak: Natal Moon nakshatra name (e.g., "Jyeshtha")
        today_moon_nak: Today's transit Moon nakshatra (e.g., "Pushya")

    Returns:
        dict with tara_index, tara_name, quality, advice, count
        or None if either nakshatra is unknown.
    """
    natal_idx = _NAK_INDEX.get(natal_moon_nak)
    today_idx = _NAK_INDEX.get(today_moon_nak)

    if natal_idx is None or today_idx is None:
        return None

    # Classical count: 1-based, from natal to today
    count = ((today_idx - natal_idx) % 27) + 1
    tara_index = (count - 1) % 9
    tara = TARA_SEQUENCE[tara_index]

    return {
        "tara_index": tara_index,
        "tara_name": tara["name"],
        "quality": tara["quality"],
        "advice": tara["advice"],
        "count": count,
    }


def find_next_favorable_tara(natal_moon_nak: str, today_moon_nak: str) -> dict:
    """
    Find the next favorable tara day after today.
    Returns the tara name, quality, and how many nakshatras away it is.
    Useful for "wait until X" advice on unfavorable days.
    """
    natal_idx = _NAK_INDEX.get(natal_moon_nak)
    today_idx = _NAK_INDEX.get(today_moon_nak)

    if natal_idx is None or today_idx is None:
        return {"tara_name": "unknown", "nakshatras_away": 0}

    # Check next nakshatras until we hit a favorable one
    favorable_qualities = {"favorable", "very_favorable"}
    for offset in range(1, 28):
        future_nak_idx = (today_idx + offset) % 27
        count = ((future_nak_idx - natal_idx) % 27) + 1
        tara_index = (count - 1) % 9
        tara = TARA_SEQUENCE[tara_index]

        if tara["quality"] in favorable_qualities:
            return {
                "tara_name": tara["name"],
                "quality": tara["quality"],
                "nakshatras_away": offset,
                "approx_days": round(offset * 0.99, 1),  # ~1 day per nakshatra
                "nakshatra": NAKSHATRAS[future_nak_idx],
            }

    return {"tara_name": "unknown", "nakshatras_away": 0}
