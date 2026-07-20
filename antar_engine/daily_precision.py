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


# ─────────────────────────────────────────────────────────────────────────────
# The five signals, shown
# ─────────────────────────────────────────────────────────────────────────────
# [signals 2026-07-20] The day's score was built from TWO inputs — tara and the
# Moon's house from lagna — and the card displayed NEITHER. That is why the read
# feels thinner than a competitor showing a fabricated "78%": they show one
# invented number, we showed none of the real ones.
#
# Lal Kitab and the running dasha were already loaded into daily_context and
# never consulted. This assembles all five into one honest breakdown, each row
# carrying what it is, which way it leans, and how hard it counts.
#
# Weights are PROVISIONAL engineering values, not doctrine — same footing as
# _TARA_SCORE_DELTA above. They are exposed so the reasoning is inspectable
# rather than asserted. A signal with no data returns available=False and is
# rendered as unknown, never as neutral: "we did not read this" and "this reads
# neutral" are different claims and collapsing them is how a fake precision
# starts.

# Natural benefic / malefic, used for the dasha lord's tilt.
_BENEFIC = {"Jupiter", "Venus", "Mercury", "Moon"}
_MALEFIC = {"Saturn", "Mars", "Sun", "Rahu", "Ketu"}


def _dir_from(delta: int) -> str:
    if delta >= 2:
        return "strong"
    if delta == 1:
        return "supportive"
    if delta == 0:
        return "neutral"
    if delta == -1:
        return "friction"
    return "adverse"


def build_day_signals(precision: dict,
                      dasha_md: str = "", dasha_ad: str = "", dasha_pd: str = "",
                      lk_sleeping: str = "",
                      moon_nakshatra: str = "",
                      lit_domain: str = "") -> list:
    """The five inputs behind the day's verdict, each scored and labelled.

    Returns a list of rows: key, label, value, direction, weight, available.
    Never raises; a signal that cannot be computed is marked unavailable rather
    than defaulted to zero.
    """
    p = precision or {}
    rows = []

    # 1. NAKSHATRA — the Moon's star and its count from the user's birth star.
    tq = p.get("tara_quality")
    rows.append({
        "key": "nakshatra",
        "label": "Moon's star",
        "value": f"{moon_nakshatra} · {p.get('tara')}" if p.get("tara") else (moon_nakshatra or ""),
        "direction": _dir_from(p.get("tara_score_delta", 0)) if tq else "unknown",
        "weight": int(p.get("tara_score_delta", 0) or 0),
        "available": bool(tq),
    })

    # 2. MOON PLACEMENT — which of the user's houses the Moon is transiting.
    h = p.get("moon_house_from_lagna")
    rows.append({
        "key": "moon_house",
        "label": "Moon is lighting",
        "value": lit_domain or p.get("lit_domain") or "",
        "direction": _dir_from(p.get("house_score_delta", 0)) if h else "unknown",
        "weight": int(p.get("house_score_delta", 0) or 0),
        "available": h is not None,
    })

    # 3. DASHA — the running period. The antardasha is the practical driver;
    #    the pratyantar is too fast to lead with but is shown when present.
    lord = (dasha_ad or dasha_md or "").strip().title()
    if lord and lord.lower() != "unknown":
        d = 1 if lord in _BENEFIC else (-1 if lord in _MALEFIC else 0)
        chain = " → ".join([x for x in (dasha_md, dasha_ad, dasha_pd)
                            if x and str(x).lower() != "unknown"])
        rows.append({
            "key": "dasha", "label": "Running period", "value": chain or lord,
            "direction": _dir_from(d), "weight": d, "available": True,
        })
    else:
        rows.append({"key": "dasha", "label": "Running period", "value": "",
                     "direction": "unknown", "weight": 0, "available": False})

    # 4. LAL KITAB — a sleeping planet is a real drag on the houses it rules.
    #    _extract_sleeping_planets returns the STRING "none detected" rather than
    #    an empty value when nothing is asleep, so a bare truthiness check scored
    #    a clean chart as friction and printed "none detected asleep". Test the
    #    sentinel, not the emptiness.
    _raw = (lk_sleeping or "").strip()
    _none = (not _raw) or _raw.lower() in ("none detected", "none", "n/a", "unknown")
    sleeping = "" if _none else _raw
    rows.append({
        "key": "lal_kitab", "label": "Lal Kitab",
        "value": f"{sleeping} asleep" if sleeping else "nothing asleep",
        "direction": "friction" if sleeping else "neutral",
        "weight": -1 if sleeping else 0,
        "available": True,
    })

    # 5. TRANSIT — the day's lit domain is the Moon's transit expressed as life
    #    area. Named separately because users read "transit" as a distinct idea.
    rows.append({
        "key": "transit", "label": "Today's transit",
        "value": lit_domain or p.get("lit_domain") or "",
        "direction": "supportive" if (p.get("house_score_delta", 0) or 0) > 0
                     else ("friction" if (p.get("house_score_delta", 0) or 0) < 0 else "neutral"),
        "weight": 0,      # already counted via moon_house; shown, not double-scored
        "available": bool(lit_domain or p.get("lit_domain")),
        "note": "counted once, with the Moon's placement",
    })
    return rows
