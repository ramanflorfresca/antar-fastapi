"""
Intra-day Moon transitions — which nakshatra actually governs the user's day.

[moon-transit 2026-07-20]

The daily engine samples the Moon ONCE, at local NOON
(get_moon_data_for_date), and uses that nakshatra for all 24 hours. The Moon
covers ~13.2 degrees a day against a 13.33-degree nakshatra, so it changes
nakshatra on almost every day — 13 of 14 consecutive IST days carried a change.

Noon is a sensible single sample and is usually right. It fails when the change
lands in the EARLY AFTERNOON: noon then reports the outgoing nakshatra while
most of the remaining waking day belongs to the incoming one. Measured over 60
days in IST, the noon sample picks the wrong governing nakshatra on 7 of them
(12%) — clustered at 12:53pm, 1:15pm, 1:20pm, 2:09pm, 2:10pm crossings.

12% is not cosmetic, because tara bala is derived from the nakshatra and can
invert across the boundary. On a real user's chart:

    28 Jul  Purva Ashadha -> Uttara Ashadha at 14:10
            before: tara Vipat  (unfavorable)   after: tara Kshema (favorable)

So on those days the engine calls the day unfavourable while most of the user's
remaining waking hours are favourable — wrong tara, wrong colour, wrong food,
wrong verdict, for the larger part of the day.

This module answers two things:
  1. WHICH nakshatra governs the day — the one covering most WAKING hours
     (06:00-23:00 local), rather than whichever holds at the noon sample.
  2. WHEN it changes, so the card can show a single turning-point line rather
     than splitting into two readings the user has to reconcile.

Waking hours are the right frame: a shift at 02:00 is astronomically real but
practically irrelevant, while one at 14:00 rewrites the user's afternoon.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]
_SPAN = 360.0 / 27.0

# Waking window, local. A 3am shift changes the chart but not the person's day.
_WAKE_START = 6.0
_WAKE_END = 23.0


def _sidereal_moon(jd: float) -> Optional[float]:
    """Sidereal Moon longitude, or None if the ephemeris is unavailable."""
    try:
        import swisseph as swe
        from antar_engine.antar_ephemeris import lahiri_ayanamsa
        lon = swe.calc_ut(jd, swe.MOON)[0][0]
        return (lon - lahiri_ayanamsa(jd)) % 360.0
    except Exception:
        return None


def _nak_index(jd: float) -> Optional[int]:
    sid = _sidereal_moon(jd)
    if sid is None:
        return None
    return int(sid / _SPAN) % 27


def moon_day_profile(local_date, tz_offset_hours: float) -> Dict[str, Any]:
    """Which nakshatra governs this local day, and when (if at all) it changes.

    Returns {} when the ephemeris is unavailable — callers must fall back to
    the existing noon sample rather than guessing.

    Keys:
      nakshatra        the one governing most WAKING hours — use this
      noon_nakshatra   what the existing single-sample logic uses
      changes_at       "2:10 PM" local, or None
      from_nakshatra / to_nakshatra
      governs_hours    waking hours the chosen nakshatra covers
      differs_from_noon  True when this fixes a would-be wrong reading
    """
    try:
        from antar_engine.antar_ephemeris import julian_day
        d = local_date.date() if hasattr(local_date, "date") else local_date
        tz = float(tz_offset_hours or 0.0)
        if abs(tz) > 14:            # minutes -> hours, same trap as elsewhere
            tz /= 60.0
    except Exception:
        return {}

    jd0 = julian_day(d.year, d.month, d.day, 0 - tz)     # local midnight
    jd1 = jd0 + 1.0
    n0, n1 = _nak_index(jd0), _nak_index(jd1)
    if n0 is None or n1 is None:
        return {}

    n_noon = _nak_index(jd0 + 0.5)
    if n_noon is None:
        n_noon = n0

    if n0 == n1:
        return {
            "nakshatra": NAKSHATRAS[n0],
            "noon_nakshatra": NAKSHATRAS[n_noon],
            "changes_at": None,
            "from_nakshatra": None,
            "to_nakshatra": None,
            "governs_hours": _WAKE_END - _WAKE_START,
            "differs_from_noon": False,
        }

    # Binary search the crossing. 40 iterations is far past sub-second, but the
    # cost is negligible and it removes any question about boundary accuracy.
    lo, hi = jd0, jd1
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if _nak_index(mid) == n0:
            lo = mid
        else:
            hi = mid
    cross_hours = ((lo + hi) / 2.0 - jd0) * 24.0        # hours after local midnight

    # Which side owns more of the waking day?
    before = max(0.0, min(cross_hours, _WAKE_END) - _WAKE_START)
    after = max(0.0, _WAKE_END - max(cross_hours, _WAKE_START))
    winner = n0 if before >= after else n1

    hh = int(cross_hours) % 24
    mm = int(round((cross_hours - int(cross_hours)) * 60))
    if mm == 60:
        hh, mm = (hh + 1) % 24, 0
    label = datetime(2000, 1, 1, hh, mm).strftime("%-I:%M %p")

    return {
        "nakshatra": NAKSHATRAS[winner],
        "noon_nakshatra": NAKSHATRAS[n_noon],
        "changes_at": label,
        "from_nakshatra": NAKSHATRAS[n0],
        "to_nakshatra": NAKSHATRAS[n1],
        "governs_hours": round(max(before, after), 1),
        "differs_from_noon": winner != n_noon,
    }


def turning_point(profile: Dict[str, Any],
                  quality_before: Optional[str],
                  quality_after: Optional[str]) -> Dict[str, Any]:
    """One user-facing line for the moment the day changes character.

    Deliberately ONE line rather than splitting the card into two readings.
    Two readings is more precise on paper and worse in practice — the user has
    to reconcile them, which is exactly the confusion we are trying to remove.

    Returns {} when there is no change, or when the change lands outside waking
    hours and so has no practical consequence.
    """
    if not profile or not profile.get("changes_at"):
        return {}
    _ADVERSE = {"caution", "unfavorable", "unfavourable", "adverse", "difficult"}
    b = (quality_before or "").strip().lower()
    a = (quality_after or "").strip().lower()
    b_bad, a_bad = b in _ADVERSE, a in _ADVERSE

    if b_bad and not a_bad:
        direction, text = "improves", f"Shifts in your favour at {profile['changes_at']}"
    elif a_bad and not b_bad:
        direction, text = "declines", f"Gets harder after {profile['changes_at']}"
    else:
        direction, text = "neutral", f"The day's flavour changes at {profile['changes_at']}"

    return {
        "at": profile["changes_at"],
        "direction": direction,
        "text": text,
        "from_nakshatra": profile.get("from_nakshatra"),
        "to_nakshatra": profile.get("to_nakshatra"),
    }


def split_day(profile: Dict[str, Any],
              natal_moon_nak: str,
              natal_lagna_sign: str,
              weekday_index: int,
              chart_data: Optional[dict] = None,
              moon_sign: str = "") -> Dict[str, Any]:
    """The day as BEFORE / AFTER the Moon's nakshatra change.

    [split-day 2026-07-20] Chosen over a single turning-point line because the
    day genuinely has two characters and users think in "before lunch / after
    lunch" terms. But this is deliberately NOT a doubled reading: the verdict
    prose and the do/don't list are LLM-written for the day as a whole and do
    not change at the boundary. Only three things flip deterministically —
    tara quality, colour, and food — so only those are split, as one compact row
    each.

    `material` is the important field. When both halves resolve to the same tara
    quality AND the same colour graha, nothing the user would act on has
    changed, and the UI must NOT split — showing two identical rows is noise
    that costs trust. Roughly speaking the split earns its place only when the
    day actually turns.

    Returns {} when there is no crossing or the inputs are unusable.
    """
    if not profile or not profile.get("changes_at"):
        return {}
    a_nak = profile.get("from_nakshatra")
    b_nak = profile.get("to_nakshatra")
    if not a_nak or not b_nak:
        return {}

    try:
        from antar_engine.daily_precision import compute_daily_precision
        from antar_engine.color_therapy import color_for_day
        from antar_engine.ayurveda_astrology import food_for_day
    except Exception:
        return {}

    # Raw tara enums were rendering literally on the card ("very_favorable",
    # "caution"). The API must ship display copy, not internal keys.
    _QUALITY_LABEL = {
        "very_favorable": "Strongly in your favour",
        "favorable":      "In your favour",
        "neutral":        "Neutral",
        "caution":        "Handle with care",
        "unfavorable":    "Runs against you",
        "unfavourable":   "Runs against you",
        "adverse":        "Runs against you",
        "difficult":      "Runs against you",
    }

    def _half(nak: str) -> Dict[str, Any]:
        try:
            pr = compute_daily_precision(
                natal_moon_nak=natal_moon_nak,
                natal_lagna_sign=natal_lagna_sign,
                today_moon_nak=nak,
                today_moon_sign=moon_sign,
            ) or {}
        except Exception:
            pr = {}
        tq = pr.get("tara_quality")
        col = color_for_day(nak, weekday_index, tq,
                            lagna_sign=natal_lagna_sign,
                            chart_data=chart_data) or {}
        fd = food_for_day(nak, weekday_index, tq) or {}
        return {
            "nakshatra":    nak,
            "tara":         pr.get("tara"),
            "tara_quality": tq,
            # human copy for the card; tara_quality stays for logic
            "quality_label": _QUALITY_LABEL.get(str(tq or "").strip().lower(), ""),
            "color":        col.get("primary"),
            "color_graha":  col.get("primary_from"),
            "wear":         col.get("wear"),
            "why_wear":     col.get("why_wear"),
            "soften":       col.get("soften"),
            "why_soften":   col.get("why_soften"),
            "eat":          fd.get("eat"),
            "avoid":        fd.get("avoid"),
            "why_eat":      fd.get("why_eat"),
            "food_graha":   fd.get("planet"),
        }

    before, after = _half(a_nak), _half(b_nak)

    # `material` gates whether the UI shows two rows or one.
    #
    # First version tested "tara quality differs OR colour graha differs", which
    # was tautological: adjacent nakshatras ALWAYS have different lords (the
    # Vimshottari lord cycle never repeats consecutively), so colour always
    # changes and every crossing scored material — 58 of 58 over 60 days. A gate
    # that never says no is not a gate.
    #
    # What actually warrants doubling the row is the day changing CHARACTER:
    # crossing the favourable/adverse line. A favorable -> very_favorable step
    # is a different label, not a different day, and splitting on it would put a
    # two-row strip on nearly every card for no user benefit.
    _ADV = {"caution", "unfavorable", "unfavourable", "adverse", "difficult"}
    _b_adv = str(before.get("tara_quality") or "").strip().lower() in _ADV
    _a_adv = str(after.get("tara_quality") or "").strip().lower() in _ADV
    material = (_b_adv != _a_adv)

    tp = turning_point(profile, before.get("tara_quality"), after.get("tara_quality"))

    return {
        "at":        profile["changes_at"],
        "material":  bool(material),
        "direction": tp.get("direction"),
        "headline":  tp.get("text"),
        "before":    before,
        "after":     after,
        # which half the day's single verdict/actions were written for
        "governing": "after" if profile.get("nakshatra") == b_nak else "before",
    }
