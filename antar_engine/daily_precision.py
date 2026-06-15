"""
antar_engine/daily_precision.py — chart-relative daily layer (Surface A, steps 1-3).

Turns two signals that already exist in the codebase into structured, scored,
fallback-safe output:

  L1 Tara Bala  — antar_engine.tara_bala.compute_tara_bala (canonical Navatara).
  L2 Moon-house — today's Moon sign counted from the natal lagna.

Both are PURE. This module surfaces them as fields, supplies score deltas, and
is consumed by daily_prediction_engine. The score blend is behind a kill switch
read by the caller (DAILY_PRECISION_SCORE).

SOURCE DISCIPLINE
  * Tara Bala quality is canonical (classical Navatara). Its mapping to a score
    delta is a PROVISIONAL engineering weight, not doctrine.
  * Moon house-from-lagna gives the LIT DOMAIN (canonical house meaning). The
    house *favorability* delta is INDICATIVE (true Chandra gochar is measured
    from the Moon, not the lagna) — kept small and flagged; never the lead claim.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from antar_engine.tara_bala import compute_tara_bala

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# PROVISIONAL engineering weights — tara quality -> score delta. Not doctrine.
_TARA_SCORE_DELTA = {
    "very_favorable": 2,
    "favorable": 1,
    "mixed": 0,
    "caution": -1,
    "cautious": -1,
    "unfavorable": -2,
}

# Canonical house meaning -> lit life-domain (safe to lead with).
_HOUSE_DOMAIN = {
    1: "self & vitality", 2: "money & voice", 3: "effort & communication",
    4: "home & peace", 5: "creativity & romance", 6: "work & health",
    7: "partnership", 8: "change & depth", 9: "fortune & travel",
    10: "career & visibility", 11: "gains & network", 12: "rest & retreat",
}

# INDICATIVE favorability (from lagna, not Moon) — small, flagged, never the lead.
_HOUSE_FAVOR = {
    1: 1, 2: 1, 3: 1, 4: 0, 5: 1, 6: -1,
    7: 0, 8: -1, 9: 1, 10: 1, 11: 1, 12: -1,
}

_SOURCE = ("Tara Bala: classical Navatara (tara_bala.compute_tara_bala); "
           "Moon-house: house-from-lagna [lit-domain canonical; "
           "favorability INDICATIVE]")


def _sign_index(name: str) -> int:
    try:
        return SIGNS.index((name or "").strip().title())
    except ValueError:
        return -1


def moon_house_from_lagna(today_moon_sign: str, natal_lagna_sign: str) -> Optional[int]:
    """Whole-sign house (1-12) of today's Moon counted from the natal lagna."""
    mi = _sign_index(today_moon_sign)
    li = _sign_index(natal_lagna_sign)
    if mi < 0 or li < 0:
        return None
    return (mi - li) % 12 + 1


def compute_daily_precision(natal_moon_nak: str, natal_lagna_sign: str,
                            today_moon_nak: str, today_moon_sign: str) -> Dict[str, Any]:
    """Return the chart-relative daily layer. Always returns a dict; individual
    fields are None when an input is missing (degrades gracefully)."""
    out: Dict[str, Any] = {
        "tara": None, "tara_quality": None, "tara_advice": None,
        "tara_score_delta": 0,
        "moon_house_from_lagna": None, "lit_domain": None,
        "house_score_delta": 0,
        "source": _SOURCE,
    }

    tb = compute_tara_bala(natal_moon_nak, today_moon_nak)
    if tb:
        out["tara"] = tb.get("tara_name")
        out["tara_quality"] = tb.get("quality")
        out["tara_advice"] = tb.get("advice")
        out["tara_score_delta"] = _TARA_SCORE_DELTA.get(tb.get("quality"), 0)

    h = moon_house_from_lagna(today_moon_sign, natal_lagna_sign)
    if h:
        out["moon_house_from_lagna"] = h
        out["lit_domain"] = _HOUSE_DOMAIN.get(h)
        out["house_score_delta"] = _HOUSE_FAVOR.get(h, 0)

    return out


def apply_precision_to_score(base_score: int, precision: Dict[str, Any]):
    """Blend tara + moon-house deltas into the base score. Returns
    (score, is_friction). Clamped 0-10. Used behind DAILY_PRECISION_SCORE."""
    if not precision:
        return base_score, base_score < 4
    s = int(base_score) + int(precision.get("tara_score_delta", 0)) \
        + int(precision.get("house_score_delta", 0))
    s = max(0, min(10, s))
    return s, s < 4


def precision_fields(precision: Dict[str, Any]) -> Dict[str, Any]:
    """The subset to merge into a day_result for the frontend (only non-null)."""
    if not precision:
        return {}
    keys = ("tara", "tara_quality", "tara_advice",
            "moon_house_from_lagna", "lit_domain", "source")
    return {k: precision[k] for k in keys if precision.get(k) is not None}


def strongest_signal_phrase(precision: Dict[str, Any]) -> Optional[str]:
    """A short, chart-relative line for the fallback `wow` — derived from the
    day's strongest precision signal. Jargon-free; no tara/house words leak.
    Returns None when there's nothing chart-specific to say."""
    if not precision:
        return None
    q = precision.get("tara_quality")
    domain = precision.get("lit_domain")
    if q in ("very_favorable", "favorable") and domain:
        return (f"A supportive window opens around {domain} today — "
                f"a good day to move one real step there.")
    if q in ("unfavorable", "caution", "cautious"):
        return ("Hold big launches today — better for review, repair, and "
                "tying off loose ends than for starting something new.")
    if domain:
        return f"Today leans toward {domain} — put your attention there."
    return None
