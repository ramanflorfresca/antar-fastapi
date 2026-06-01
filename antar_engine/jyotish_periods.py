"""
jyotish_periods.py — deterministic period boundaries + classical markers.

Pure functions (no ephemeris, no LLM, no DB) so they are fully unit-testable:

  month_period(birth_date, today)  -> (period_start_iso, period_end_iso)
      Birth-day-of-month -> next birth-day-of-month window (clamped for short
      months). This is the masik (monthly) boundary anchored on the birthday day.

  year_period(birth_date, today)   -> (start_iso, end_iso, method)
      Birthday anniversary window. method="birthday_anchor" — this is the
      Varshphal anniversary to within ~1 day of the exact solar-return instant.
      (A true ephemeris solar-return timestamp is a separate enhancement.)

  muntha_sign(lagna_sign, birth_date, today) -> sign name
      Classical Tajika Muntha: natal Lagna advanced one sign per completed year.

  naisargika_planet(age) -> planet
      Naisargika (natural maturity) active planet by age band.

  sign_lord(sign) -> planet            standard rulerships
  cycle_cross_check(vim_md_planet, chara_md_sign, age) -> dict
      2-of-3 agreement across Vimshottari MD lord, Chara MD sign-lord, and the
      Naisargika active planet. A cycle signal is emitted only when >= 2 agree.
"""
from datetime import date, timedelta

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

# Naisargika (natural maturity) active planet by age — per the locked spec.
_NAISARGIKA_BANDS = [
    (1, 4, "Moon"), (5, 15, "Mars"), (16, 31, "Mercury"), (32, 50, "Venus"),
    (51, 65, "Jupiter"), (66, 69, "Sun"), (70, 83, "Saturn"), (84, 95, "Rahu"),
]


def _parse(d):
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d)[:10])


def _clamp_day(year, month, day):
    """Return a valid date for (year, month, day), clamping day to month length."""
    if month > 12:
        year += (month - 1) // 12
        month = (month - 1) % 12 + 1
    d = day
    while d > 0:
        try:
            return date(year, month, d)
        except ValueError:
            d -= 1
    return date(year, month, 1)


def age_on(birth_date, today=None) -> int:
    b = _parse(birth_date)
    t = today or date.today()
    return (t.year - b.year) - (1 if (t.month, t.day) < (b.month, b.day) else 0)


def month_period(birth_date, today=None):
    """Birth-day-of-month -> next birth-day-of-month (ISO strings)."""
    b = _parse(birth_date)
    t = today or date.today()
    bd = b.day
    anchor_this = _clamp_day(t.year, t.month, bd)
    if t >= anchor_this:
        start = anchor_this
        end = _clamp_day(t.year, t.month + 1, bd) - timedelta(days=1)
    else:
        pm_year = t.year if t.month > 1 else t.year - 1
        pm_month = t.month - 1 if t.month > 1 else 12
        start = _clamp_day(pm_year, pm_month, bd)
        end = anchor_this - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def year_period(birth_date, today=None):
    """Birthday-anniversary window (Varshphal anniversary, ~1 day from the exact
    solar return). Returns (start_iso, end_iso, method)."""
    b = _parse(birth_date)
    t = today or date.today()
    bday_this = _clamp_day(t.year, b.month, b.day)
    if t >= bday_this:
        start = bday_this
        end = _clamp_day(t.year + 1, b.month, b.day) - timedelta(days=1)
    else:
        start = _clamp_day(t.year - 1, b.month, b.day)
        end = bday_this - timedelta(days=1)
    return start.isoformat(), end.isoformat(), "birthday_anchor"


def muntha_sign(lagna_sign, birth_date, today=None) -> str:
    """Tajika Muntha: natal Lagna sign advanced one sign per completed year."""
    try:
        idx = SIGNS.index((lagna_sign or "").strip().title())
    except ValueError:
        return ""
    a = age_on(birth_date, today)
    return SIGNS[(idx + a) % 12]


def naisargika_planet(age) -> str:
    try:
        a = int(age)
    except Exception:
        return ""
    for lo, hi, planet in _NAISARGIKA_BANDS:
        if lo <= a <= hi:
            return planet
    return "Ketu" if a >= 96 else ""


def sign_lord(sign) -> str:
    return SIGN_LORD.get((sign or "").strip().title(), "")


def cycle_cross_check(vim_md_planet, chara_md_sign, age) -> dict:
    """2-of-3 agreement across Vimshottari MD lord, Chara MD sign-lord, and the
    Naisargika active planet. Returns the agreed planet (if >=2 concur) and the
    breakdown so it's verifiable."""
    vim = (vim_md_planet or "").strip().title()
    chara_lord = sign_lord(chara_md_sign)
    nais = naisargika_planet(age)
    systems = {
        "vimshottari": vim or None,
        "chara": chara_lord or None,
        "naisargika": nais or None,
    }
    tally = {}
    for sysname, planet in systems.items():
        if planet:
            tally.setdefault(planet, []).append(sysname)
    agreed_planet, agreeing = None, []
    for planet, names in tally.items():
        if len(names) >= 2 and len(names) > len(agreeing):
            agreed_planet, agreeing = planet, names
    return {
        "systems": systems,
        "agreed_planet": agreed_planet,
        "agreeing_systems": agreeing,
        "agreement_count": len(agreeing),
    }
