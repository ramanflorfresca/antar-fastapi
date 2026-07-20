"""
Birth-time confidence — how much of a reading the stored birth time can carry.

[birth-time-confidence 2026-07-20]

Every house-based claim in the product rests on the ascendant, and the ascendant
moves roughly one sign every two hours. A user who typed "11:59" because they
only know they were born "around noon" can easily be one sign off, and when the
lagna moves a sign ALL TWELVE houses rotate — the 10th becomes the 9th, career
claims become father claims, and the reading is confidently wrong.

Nothing in the product asked about this, so a guessed time and a birth-certificate
time were treated identically.

Two independent things matter, and both are needed:

  1. What the USER says   — `birth_time_accuracy`: exact | approximate | unknown
  2. What the CHART says  — how many minutes of error it would actually take to
                            move the lagna into the next sign

(2) is the part worth computing rather than assuming. The common rule of thumb
("the ascendant moves ~1 degree per 4 minutes") is only true on average: near the
poles, and for signs of short ascension, the real figure can be several times
faster or slower. So instead of extrapolating from the degree, this module
re-computes the actual ascendant at offsets either side of the stored time and
finds where it genuinely changes sign.

A chart sitting mid-sign is robust to a sloppy time; a chart sitting 5 degrees
from the boundary is not. Those two deserve different confidence, even when the
user gives the same answer about how sure they are.
"""

from __future__ import annotations

from typing import Optional

# Only the ascendant is needed; keep the import local to avoid a hard dependency
# for callers that just want to render a stored result.
# calculate_lagna returns TROPICAL longitude; the charts are SIDEREAL (Lahiri).
# Both are needed — measuring the margin against the tropical boundary silently
# answers a different question. On a real chart the tropical ascendant was
# Aquarius 18.49deg while the sidereal one was Capricorn 24.69deg: 11.5deg from
# the next tropical boundary but only 5.3deg from the sidereal one, i.e. more
# than twice the apparent safety margin. Same conversion as
# antar_ephemeris line ~737: asc_sid = (asc_trop - ayanamsa) % 360.
try:
    from antar_engine.antar_ephemeris import (
        calculate_lagna, julian_day, lahiri_ayanamsa,
    )
except Exception:  # pragma: no cover - defensive
    calculate_lagna = None  # type: ignore
    julian_day = None       # type: ignore
    lahiri_ayanamsa = None  # type: ignore

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# Accepted values for the user-stated answer.
ACCURACY_EXACT       = "exact"        # from a birth certificate / hospital record
ACCURACY_APPROXIMATE = "approximate"  # "around noon", family memory
ACCURACY_UNKNOWN     = "unknown"      # genuinely no idea
VALID_ACCURACY = (ACCURACY_EXACT, ACCURACY_APPROXIMATE, ACCURACY_UNKNOWN)

# How much error each answer implies, in minutes. `unknown` is capped at 120
# rather than "the whole day" because beyond ~2 hours the lagna has certainly
# moved and there is nothing left to calibrate — the answer is simply "rectify".
ASSUMED_ERROR_MIN = {
    ACCURACY_EXACT:        2,
    ACCURACY_APPROXIMATE: 30,
    ACCURACY_UNKNOWN:    120,
}

# Search bound. Past two hours the ascendant has moved a full sign on any chart,
# so there is no point scanning further.
_MAX_SCAN_MIN = 120
_STEP_MIN     = 1


def _sign_of(tropical_lon: float) -> str:
    return SIGNS[int(tropical_lon // 30) % 12]


def cusp_margin_minutes(jd_ut: float, lat: float, lng: float) -> Optional[dict]:
    """Minutes of birth-time error before the lagna changes sign.

    Walks outward from the stored moment in one-minute steps and reports the
    first offset in each direction where the ascendant lands in a different
    sign. Returns None when the ephemeris is unavailable or the inputs are
    unusable — callers must treat None as "unknown", never as "safe".
    """
    if calculate_lagna is None or lahiri_ayanamsa is None or jd_ut is None:
        return None

    def _sidereal_lon(jd: float) -> float:
        trop, _ = calculate_lagna(jd, lat, lng)
        return (trop - lahiri_ayanamsa(jd)) % 360.0

    try:
        base_lon  = _sidereal_lon(jd_ut)
        base_sign = _sign_of(base_lon)
    except Exception:
        return None

    day = 1.0 / (24.0 * 60.0)  # one minute in Julian days

    def _scan(direction: int) -> Optional[int]:
        for m in range(_STEP_MIN, _MAX_SCAN_MIN + 1, _STEP_MIN):
            try:
                lon = _sidereal_lon(jd_ut + direction * m * day)
            except Exception:
                return None
            if _sign_of(lon) != base_sign:
                return m
        return None  # stable across the whole scan window

    fwd  = _scan(+1)
    back = _scan(-1)
    known = [x for x in (fwd, back) if x is not None]
    margin = min(known) if known else None

    return {
        "lagna_sign":       base_sign,
        "degree_in_sign":   round(base_lon % 30.0, 2),
        "minutes_forward":  fwd,
        "minutes_backward": back,
        # None => the sign is stable for at least _MAX_SCAN_MIN either side
        "margin_minutes":   margin,
        "stable_window_min": _MAX_SCAN_MIN if margin is None else margin,
    }


def assess(accuracy: Optional[str], margin: Optional[dict]) -> dict:
    """Combine what the user said with what the chart says.

    `risk` is about the HOUSES specifically — whether house-based claims can be
    trusted — not about the reading as a whole. Dasha and transit survive a
    sloppy birth time far better than house cusps do, which is why the guidance
    below redirects rather than just lowering confidence everywhere.
    """
    acc = (accuracy or "").strip().lower()
    if acc not in VALID_ACCURACY:
        acc = ""  # never invent a confidence the user did not give

    assumed = ASSUMED_ERROR_MIN.get(acc)
    m = (margin or {}).get("margin_minutes") if margin else None

    # Unknown on either axis is NOT low risk. An unanswered question and a
    # confirmed-exact time must not collapse to the same verdict.
    if acc == ACCURACY_EXACT and (m is None or m > 5):
        risk = "low"
    elif not acc and m is not None and m <= 15:
        risk = "high"          # chart is on a knife-edge and we never asked
    elif not acc:
        risk = "unknown"
    elif assumed is not None and m is not None and assumed >= m:
        risk = "critical"      # stated error exceeds the distance to the cusp
    elif assumed is not None and m is not None and assumed >= m / 2:
        risk = "high"
    elif acc == ACCURACY_UNKNOWN:
        risk = "high"
    else:
        risk = "moderate" if acc == ACCURACY_APPROXIMATE else "low"

    return {
        "accuracy":        acc or None,
        "assumed_error_min": assumed,
        "margin_minutes":  m,
        "lagna_sign":      (margin or {}).get("lagna_sign"),
        "degree_in_sign":  (margin or {}).get("degree_in_sign"),
        "house_risk":      risk,
        "needs_rectification": risk in ("critical", "high"),
    }


def assess_chart_row(row: Optional[dict]) -> Optional[dict]:
    """Assess straight from a `charts` row. Returns None when the row lacks what
    is needed — callers must treat that as "no opinion", not as "time is fine".

    Deliberately works BEFORE `birth_time_accuracy` exists in the database: the
    cusp margin is a property of the chart alone, so a tight margin can be
    flagged today and simply gets sharper once the user answers the question.
    """
    if not row:
        return None
    try:
        bd = str(row.get("birth_date") or "")[:10]
        bt = str(row.get("birth_time") or "")[:8]
        lat = row.get("latitude")
        lng = row.get("longitude")
        if not bd or not bt or lat is None or lng is None:
            return None
        y, mo, d = (int(x) for x in bd.split("-"))
        parts = [int(x) for x in bt.split(":")[:3]] + [0, 0]
        hh, mm, ss = parts[0], parts[1], parts[2]

        # tz_offset is stored in HOURS east of UT on this table (e.g. 5.5 for IST).
        try:
            tz = float(row.get("timezone_offset") or 0.0)
        except (TypeError, ValueError):
            tz = 0.0

        h_ut = hh + mm / 60.0 + ss / 3600.0 - tz
        if julian_day is None:
            return None
        jd = julian_day(y, mo, d, h_ut)
        margin = cusp_margin_minutes(jd, float(lat), float(lng))
        if margin is None:
            return None
        return assess(row.get("birth_time_accuracy"), margin)
    except Exception:
        return None


# Prompt-side. Injected into the LLM context, never shown raw to the user.
_GUIDANCE = {
    "critical": (
        "BIRTH-TIME RISK: CRITICAL. The stated uncertainty is larger than the "
        "distance to the next rising sign, so the ascendant — and therefore ALL "
        "twelve houses — may be wrong by one sign. Do NOT make house-specific "
        "claims (\"your 10th house\", \"a 7th-house matter\"). Lean on dasha and "
        "transit, which survive a wrong birth time. Say plainly that the birth "
        "time needs confirming before house-level detail can be trusted."
    ),
    "high": (
        "BIRTH-TIME RISK: HIGH. The ascendant is close enough to a sign boundary "
        "that a modest error moves every house. Prefer dasha and transit "
        "reasoning. Use house language only where the same conclusion holds "
        "either side of the boundary, and stay non-committal on house-cusp "
        "detail."
    ),
    "moderate": (
        "BIRTH-TIME RISK: MODERATE. The birth time is approximate but the "
        "ascendant is not near a boundary, so house claims are usable. Keep "
        "degree-level or minute-level timing claims out."
    ),
    "unknown": (
        "BIRTH-TIME RISK: UNKNOWN — the user has not confirmed how accurate "
        "their birth time is. Treat house claims as provisional and do not "
        "present them with more certainty than dasha or transit claims."
    ),
    "low": "",
}


def confidence_prompt_block(assessment: dict) -> str:
    """Render as an LLM instruction block. Empty string when the time is sound,
    so a well-established chart carries no extra hedging."""
    if not assessment:
        return ""
    g = _GUIDANCE.get(assessment.get("house_risk") or "", "")
    if not g:
        return ""
    lines = ["=== BIRTH-TIME CONFIDENCE ==="]
    m = assessment.get("margin_minutes")
    if m is not None:
        lines.append(
            f"- Ascendant is {assessment.get('lagna_sign')} "
            f"{assessment.get('degree_in_sign')}deg; it changes sign with about "
            f"{m} minute(s) of birth-time error."
        )
    if assessment.get("assumed_error_min") is not None:
        lines.append(
            f"- User describes their birth time as '{assessment.get('accuracy')}' "
            f"(assume up to ~{assessment.get('assumed_error_min')} minutes of error)."
        )
    lines.append("- " + g)
    lines.append("=== END BIRTH-TIME CONFIDENCE ===")
    return "\n".join(lines)
