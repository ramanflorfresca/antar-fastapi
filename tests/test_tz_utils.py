"""Guards for DST-correct IANA offset resolution (desh-kaal-patra timing fix)."""
from datetime import datetime
from antar_engine.tz_utils import iana_offset_hours


def test_denver_is_dst_correct():
    # Albuquerque/Denver: MST -7 in winter, MDT -6 in summer.
    assert iana_offset_hours("America/Denver", datetime(2026, 1, 12)) == -7.0
    assert iana_offset_hours("America/Denver", datetime(2026, 7, 12)) == -6.0


def test_eastern_differs_from_mountain_same_country():
    # Two US zones must NOT collapse to one country offset.
    jul = datetime(2026, 7, 12)
    assert iana_offset_hours("America/New_York", jul) == -4.0   # EDT
    assert iana_offset_hours("America/Los_Angeles", jul) == -7.0  # PDT
    assert iana_offset_hours("America/New_York", jul) != iana_offset_hours(
        "America/Los_Angeles", jul)


def test_half_hour_zone():
    assert iana_offset_hours("Asia/Kolkata") == 5.5


def test_unknown_id_returns_none():
    # A bare country code / junk must return None so callers fall back.
    assert iana_offset_hours("US") is None
    assert iana_offset_hours("") is None
    assert iana_offset_hours(None) is None
