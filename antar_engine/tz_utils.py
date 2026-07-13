"""
antar_engine/tz_utils.py
========================
Timezone helpers for sunrise-anchored daily timing.

[desh-kaal-patra 2026-07-12] The daily engine needs the UTC offset of the user's
CURRENT city, DST-correct — not a fixed per-country integer. Given an IANA zone
id (e.g. "America/Denver") this returns the offset in hours for a given date,
honouring daylight saving.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional


def iana_offset_hours(tz_id, on_date: Optional[datetime] = None) -> Optional[float]:
    """UTC offset in hours for an IANA timezone id, DST-correct for on_date
    (default: today, UTC). Returns None when tz_id isn't a resolvable IANA id
    (so callers can fall back). E.g. "America/Denver" -> -6.0 in July (MDT),
    -7.0 in January (MST); "Asia/Kolkata" -> 5.5."""
    if not tz_id or "/" not in str(tz_id):
        return None
    try:
        from zoneinfo import ZoneInfo
        d = on_date if on_date is not None else datetime.utcnow()
        naive_noon = datetime(d.year, d.month, d.day, 12, 0, 0)
        off = ZoneInfo(str(tz_id)).utcoffset(naive_noon)
        return round(off.total_seconds() / 3600.0, 2) if off is not None else None
    except Exception:
        return None
