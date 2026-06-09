"""
antar_engine/lahiri_gate.py
────────────────────────────
V2.2 hard precondition for any transit/divisional math.

swisseph defaults to TROPICAL. Without an explicit
`swe.set_sid_mode(swe.SIDM_LAHIRI)` every sidereal computation is
silently wrong by ~24°, which makes Layer 3 (transit scan) read the
wrong houses entirely.

Most call sites in the codebase do set it (day_chart_engine, transits,
vimsottari), but the precision-windows scoring path didn't have an
explicit precondition. This module gives you two helpers:

  - assert_lahiri_sid_mode() — HARD raises RuntimeError if Lahiri can't
    be set or the ayanamsa doesn't sanity-check. Use this in places
    where a wrong answer is worse than no answer.

  - ensure_lahiri_sid_mode() — SOFT returns bool. Sets SIDM_LAHIRI on
    swisseph and verifies the ayanamsa is in the expected 22-27° range
    for the current year. Use this in places where we want to log+skip
    on failure instead of crashing /predict.

Both are no-cost no-ops on subsequent calls — set_sid_mode is
idempotent in swisseph.
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def ensure_lahiri_sid_mode() -> bool:
    """Set SIDM_LAHIRI on swisseph and sanity-check the ayanamsa.
    Returns True on success. Never raises — logs and returns False on
    failure so callers can choose to skip scoring rather than crash."""
    try:
        import swisseph as swe
        from datetime import datetime
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        now = datetime.utcnow()
        jd = swe.julday(now.year, now.month, now.day, 0)
        ayan = float(swe.get_ayanamsa(jd))
        # Lahiri ayanamsa is ~24.2° in 2026. Bound at 22-27° rather
        # than exact-match so this works across years and is robust to
        # the ~50 arcsec/yr precession drift.
        if not (22.0 < ayan < 27.0):
            logger.warning(
                "[lahiri_gate] ayanamsa out of expected band: %.4f", ayan
            )
            return False
        return True
    except Exception as e:
        logger.warning("[lahiri_gate] ensure failed: %s", e)
        return False


def assert_lahiri_sid_mode() -> None:
    """HARD precondition: raises RuntimeError if Lahiri can't be
    established. Use only where computing on tropical longitudes would
    silently mis-read houses."""
    if not ensure_lahiri_sid_mode():
        raise RuntimeError(
            "Lahiri sidereal mode (SIDM_LAHIRI) could not be established. "
            "Transit/divisional math is unsafe — caller must abort."
        )
