"""
Jaimini Chara Dasha Engine — Verified against Parasara Light
Antar AI · antar.world · Rewritten March 30, 2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALGORITHM — Verified against Parasara Light (all 12 signs ✅)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Duration = distance from sign to its Jaimini lord,
direction determined by QUADRANT of the dasha sign:

  Q1 (Aries=0, Taurus=1, Gemini=2)         → FORWARD  = (lord_sign - sign) % 12
  Q2 (Cancer=3, Leo=4, Virgo=5)             → BACKWARD = (sign - lord_sign) % 12
  Q3 (Libra=6, Scorpio=7, Sagittarius=8)   → FORWARD  = (lord_sign - sign) % 12
  Q4 (Capricorn=9, Aquarius=10, Pisces=11) → BACKWARD = (sign - lord_sign) % 12

  If result = 0 (lord in same sign): duration = 12

Jaimini lord assignments:
  Aquarius → Rahu  (not Saturn)
  Scorpio  → Mars  (not Ketu)
  All others: standard Parasara lords

NO CYCLING — Jaimini Chara Dasha runs once through 12 signs.
  (Yogini Dasha repeats; Chara Dasha does NOT.)

SEQUENCE: Even lagna → backward. Odd lagna → forward.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFICATION — Capricorn lagna, Nov 26 1974, New Delhi
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cap=7 Sag=2 Sco=11 Lib=1 Vir=11 Leo=9
Can=4 Gem=4 Tau=6  Ari=6 Pis=1  Aqu=3  — all match PL ✅
Current (Mar 2026): Taurus dasha (Nov 2023 – Nov 2029)
"""

from __future__ import annotations
import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

SIGN_NAMES = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces",
]
SIGN_INDEX = {name: idx for idx, name in enumerate(SIGN_NAMES)}

# Jaimini lords: Aquarius=Rahu, Scorpio=Mars, rest standard
JAIMINI_LORDS: dict[int, str] = {
    0:"Mars", 1:"Venus", 2:"Mercury", 3:"Moon", 4:"Sun", 5:"Mercury",
    6:"Venus", 7:"Mars", 8:"Jupiter", 9:"Saturn", 10:"Rahu", 11:"Jupiter",
}

# Q1(0-2) and Q3(6-8) use forward; Q2(3-5) and Q4(9-11) use backward
FORWARD_SIGNS  = {0, 1, 2, 6, 7, 8}
BACKWARD_SIGNS = {3, 4, 5, 9, 10, 11}

ODD_LAGNA_SIGNS  = {0, 2, 4, 6, 8, 10}   # forward sequence
EVEN_LAGNA_SIGNS = {1, 3, 5, 7, 9, 11}   # backward sequence


def compute_sign_duration(sign_idx: int, planet_sign: dict[str, int]) -> int:
    """Chara Dasha duration for one sign using quadrant-based direction rule."""
    lord      = JAIMINI_LORDS[sign_idx]
    lord_sign = planet_sign.get(lord)

    if lord_sign is None:
        logger.warning("Sign %s: lord %s missing from planet_sign — defaulting 1yr",
                       SIGN_NAMES[sign_idx], lord)
        return 1

    if sign_idx in FORWARD_SIGNS:
        duration = (lord_sign - sign_idx) % 12
    else:
        duration = (sign_idx - lord_sign) % 12

    return duration if duration != 0 else 12


def get_dasha_sequence(lagna_sign: int) -> list[int]:
    """12-sign sequence from lagna. Odd lagna=forward, Even lagna=backward."""
    if lagna_sign in ODD_LAGNA_SIGNS:
        return [(lagna_sign + i) % 12 for i in range(12)]
    else:
        return [(lagna_sign - i) % 12 for i in range(12)]


def compute_jaimini_dashas(
    lagna_sign: int,
    planet_sign: dict[str, int],
    birth_date: date,
) -> list[dict]:
    """
    Compute full Jaimini Chara Dasha timeline (12 signs, no cycling).

    Parameters
    ----------
    lagna_sign  : 0=Aries … 11=Pisces
    planet_sign : {planet_name: sign_index}  from build_planet_map()
    birth_date  : date of birth

    Returns list of dicts with sign, sign_index, duration_years, start_date, end_date.
    """
    try:
        from dateutil.relativedelta import relativedelta
    except ImportError:
        raise ImportError("pip install python-dateutil")

    sequence = get_dasha_sequence(lagna_sign)
    dashas, cursor = [], birth_date

    for sign_idx in sequence:
        duration = compute_sign_duration(sign_idx, planet_sign)
        end = cursor + relativedelta(years=duration)
        dashas.append({
            "sign":           SIGN_NAMES[sign_idx],
            "sign_index":     sign_idx,
            "duration_years": duration,
            "start_date":     cursor,
            "end_date":       end,
        })
        cursor = end

    return dashas


def get_current_dasha(dashas: list[dict], as_of: Optional[date] = None) -> Optional[dict]:
    """Return the dasha active on as_of (defaults to today)."""
    ref = as_of or date.today()
    for d in dashas:
        if d["start_date"] <= ref < d["end_date"]:
            return d
    return dashas[-1] if dashas else None


def format_dasha_label(dasha: dict) -> str:
    return f"{dasha['sign']} Dasha ({dasha['start_date'].year}–{dasha['end_date'].year})"


def build_planet_map(planet_longitudes: dict[str, float]) -> dict[str, int]:
    """Convert sidereal longitudes (0-360°) to {planet: sign_index}."""
    lons = dict(planet_longitudes)
    if "Rahu" in lons and "Ketu" not in lons:
        lons["Ketu"] = (lons["Rahu"] + 180.0) % 360.0
    return {p: int(lon // 30) % 12 for p, lon in lons.items()}


def compute_jaimini_antardashas(md: dict, lagna_sign: int) -> list[dict]:
    """K.N. Rao Chara antardaśās (sub-signs) for one Mahādaśā sign.

    The MD span is split into 12 equal sub-periods that run in the SAME
    direction as the Mahādaśā sequence (backward for an even lagna, forward for
    an odd one). The antardaśā sequence starts one sign 'behind' the MD sign in
    the direction of travel — i.e. the sign the dasha entered the MD from:
        backward MD → start = (md_sign + 1) % 12
        forward  MD → start = (md_sign - 1) % 12

    VALIDATION (empirical): reproduced against a real Capricorn-lagna chart
    (Taurus MD 1974-anchored, Nov 2023–Nov 2029) — the AD active on 2026-07-22
    is Capricorn and the next is Sagittarius, matching the chart owner's own
    software. See tests/test_sri_lagna_chara.py.

    CAVEAT: published K.N. Rao antardaśā START conventions vary; this start-rule
    is validated on ONE chart (two ground-truth AD points). Cross-check against
    a second chart / Parasara Light before treating it as universal.

    Parameters
    ----------
    md         : one Mahādaśā dict from compute_jaimini_dashas()
                 (needs sign, sign_index, start_date, end_date)
    lagna_sign : 0=Aries … 11=Pisces — decides AD direction

    Returns list of 12 dicts: sign, sign_index, parent_sign, parent_sign_index,
    start_date, end_date, sequence (1-12).
    """
    from datetime import timedelta

    backward = lagna_sign in EVEN_LAGNA_SIGNS
    md_idx = md["sign_index"]
    start_idx = (md_idx + 1) % 12 if backward else (md_idx - 1) % 12

    seq = [(start_idx - i) % 12 if backward else (start_idx + i) % 12
           for i in range(12)]

    span_days = (md["end_date"] - md["start_date"]).days
    ads, cursor = [], md["start_date"]
    for n, s in enumerate(seq):
        # Proportional split keeps the last AD ending exactly on the MD end.
        end = md["start_date"] + timedelta(days=round(span_days * (n + 1) / 12))
        ads.append({
            "sign":              SIGN_NAMES[s],
            "sign_index":        s,
            "parent_sign":       md["sign"],
            "parent_sign_index": md_idx,
            "start_date":        cursor,
            "end_date":          end,
            "sequence":          n + 1,
        })
        cursor = end
    return ads


# ── Self-test ──────────────────────────────────────────────────────────────────
def _run_test():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    planet_sign = {
        "Sun":7, "Moon":11, "Mars":6, "Mercury":6, "Jupiter":10,
        "Venus":7, "Saturn":2, "Rahu":7, "Ketu":1,
    }
    lagna_sign = 9   # Capricorn
    birth      = date(1974, 11, 26)

    expected = {
        "Capricorn":7, "Sagittarius":2, "Scorpio":11, "Libra":1,
        "Virgo":11, "Leo":9, "Cancer":4, "Gemini":4,
        "Taurus":6, "Aries":6, "Pisces":1, "Aquarius":3,
    }

    print("\n" + "="*58)
    print("JAIMINI CHARA DASHA — Capricorn lagna, Nov 26 1974")
    print("="*58)
    print(f"{'Sign':<14} {'Calc':>5} {'PL':>5}  Status")
    print("-"*38)

    dashas  = compute_jaimini_dashas(lagna_sign, planet_sign, birth)
    current = get_current_dasha(dashas)
    ok_all  = True

    for d in dashas:
        s    = d["sign"]
        calc = d["duration_years"]
        pl   = expected.get(s, "?")
        ok   = calc == pl if pl != "?" else True
        if not ok: ok_all = False
        mark = "✅" if ok else f"❌ exp {pl}"
        active = "  ◀ ACTIVE" if d == current else ""
        print(f"{s:<14} {calc:>4}yr {str(pl):>4}  {mark}{active}")

    print("-"*38)
    print("✅ ALL PASS" if ok_all else "❌ FAILURES ABOVE")
    print(f"\nToday ({date.today()}): {format_dasha_label(current) if current else 'none'}")


if __name__ == "__main__":
    _run_test()
