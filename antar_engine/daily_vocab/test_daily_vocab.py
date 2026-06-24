"""
Synthetic unit tests for the Concrete Daily Vocabulary Layer.

NO Swiss Ephemeris required — feeds synthetic primitives so the mapping +
conviction logic is fully testable in CI / sandbox. Run:

    cd ~/antarai && source venv311/bin/activate
    python -m pytest antar_engine/daily_vocab/test_daily_vocab.py -q
    # or, without pytest:
    python antar_engine/daily_vocab/test_daily_vocab.py
"""

from __future__ import annotations

import re

from antar_engine.daily_vocab import (
    compute_concrete_block, public_view, populated_fields,
)
from antar_engine.daily_vocab.conviction import CONF_CEIL

# ── fixtures ─────────────────────────────────────────────────────────

BUSY = dict(
    today_moon_sign="Cancer",
    today_moon_nak="Pushya",
    natal_moon_sign="Cancer",        # matches -> at-home rhythm
    natal_lagna_sign="Aries",
    weekday="Friday",                # Venus day -> romance signal
    tithi_quality="auspicious",
    precision={"tara_quality": "favorable", "lit_domain": "money & voice",
               "moon_house_from_lagna": 4},
    transit_contacts=[
        {"planet": "Sun", "house": 1, "aspect_to_natal": "conjunction",
         "orb": 0.8, "target_house": 4},        # fast malefic exact -> body (today)
        {"planet": "Saturn", "house": 10, "aspect_to_natal": "conjunction",
         "orb": 1.0, "target_house": 10},       # slow standing -> background only
        {"planet": "Venus", "house": 7, "aspect_to_natal": "trine",
         "orb": 2.0, "target_house": 7},        # romance reinforce
    ],
    best_window="8:00–9:20 AM",
    steer_clear_window="4:40–6:00 PM",
)

QUIET = dict(
    today_moon_sign="Gemini",
    today_moon_nak="Mrigashira",
    natal_moon_sign="Leo",
    natal_lagna_sign="Virgo",
    weekday="Wednesday",
    tithi_quality="neutral",
    precision={"tara_quality": "mixed"},
    transit_contacts=[],             # nothing pulling
    best_window=None,
    steer_clear_window=None,
)

EVENT = dict(
    today_moon_sign="Scorpio",
    today_moon_nak="Jyeshtha",
    natal_moon_sign="Taurus",
    natal_lagna_sign="Aries",
    weekday="Tuesday",               # Mars day
    tithi_quality="inauspicious",
    precision={"tara_quality": "unfavorable"},
    transit_contacts=[
        {"planet": "Mars", "house": 3, "aspect_to_natal": "square",
         "orb": 1.2, "target_house": 3},        # mars hard + 3rd (driving)
        {"planet": "Saturn", "house": 6, "aspect_to_natal": "opposition",
         "orb": 2.0, "target_house": 6},         # saturn hard + 6th dusthana
    ],
)

# Jargon that must NEVER appear in a user-facing text field.
_PLANETS = r"\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\b"
_SIGNS = (r"\b(Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|"
          r"Sagittarius|Capricorn|Aquarius|Pisces)\b")
_NAKS = (r"\b(Ashwini|Bharani|Krittika|Rohini|Mrigashira|Ardra|Punarvasu|"
         r"Pushya|Ashlesha|Magha|Phalguni|Hasta|Chitra|Swati|Vishakha|"
         r"Anuradha|Jyeshtha|Mula|Ashadha|Shravana|Dhanishta|Shatabhisha|"
         r"Bhadrapada|Revati|nakshatra|tithi|tara|karana|dasha|graha|house)\b")
_JARGON = re.compile("|".join([_PLANETS, _SIGNS, _NAKS]), re.IGNORECASE)
_TEMPLATE = re.compile(r"[{}]|\bNone\b|%\d|\bhouse \d|\b(1st|2nd|3rd|4th|5th|"
                       r"6th|7th|8th|9th|10th|11th|12th) house\b", re.IGNORECASE)


def _texts(block):
    out = []
    for k, v in public_view(block).items():
        if isinstance(v, dict) and v.get("text"):
            out.append((k, v["text"]))
    return out


def test_conviction_varies_and_is_capped():
    b = compute_concrete_block(**BUSY)
    confs = [d["confidence"] for d in b["_debug"].values()]
    assert len(set(confs)) > 1, "confidence must vary across fields"
    assert max(confs) <= CONF_CEIL, f"confidence saturated above {CONF_CEIL}"
    assert all(c != 0.92 for c in confs), "0.92 saturation antipattern present"


def test_busy_day_surfaces_4_to_6():
    b = compute_concrete_block(**BUSY)
    n = len(populated_fields(b))
    assert 4 <= n <= 6, f"busy day should surface 4-6 Tier-A/B fields, got {n}"


def test_quiet_day_surfaces_fewer():
    q = compute_concrete_block(**QUIET)
    busy = compute_concrete_block(**BUSY)
    nq, nb = len(populated_fields(q)), len(populated_fields(busy))
    assert nq < nb, f"quiet ({nq}) should surface fewer than busy ({nb})"
    # A quiet day = just the daily baseline (food/mood/color/direction); the
    # conditional fields (body/romance/event) are exactly what a busy day adds.
    assert set(populated_fields(q)) == {
        "food_lean", "mood_tone", "lucky_color", "favourable_direction"}, \
        f"quiet day should be baseline-only, got {populated_fields(q)}"
    for conditional in ("body_focus", "romance_read", "event_watch"):
        assert conditional not in populated_fields(q)


def test_event_watch_gated_and_soft():
    # Quiet + busy(non-converging) days: no event_watch.
    assert "event_watch" not in public_view(compute_concrete_block(**QUIET))
    assert "event_watch" not in public_view(compute_concrete_block(**BUSY))
    # Converging-malefic day: event_watch present and SOFT.
    e = public_view(compute_concrete_block(**EVENT))
    assert "event_watch" in e, "converging malefics should trigger a soft watch"
    txt = e["event_watch"]["text"].lower()
    assert "unhurried" in txt
    assert "you will" not in txt and "will happen" not in txt
    assert e["event_watch"]["tier"] == "watch"


def test_no_jargon_anywhere():
    for fx in (BUSY, QUIET, EVENT):
        b = compute_concrete_block(**fx)
        for field, txt in _texts(b):
            assert not _JARGON.search(txt), f"jargon leak in {field}: {txt!r}"
            assert not _TEMPLATE.search(txt), f"template/house leak in {field}: {txt!r}"


def test_schema_shape():
    b = public_view(compute_concrete_block(**BUSY))
    assert b["body_focus"]["tier"] == "soft"
    # windows reused as plain strings
    assert b["best_window"] == "8:00–9:20 AM"
    assert b["steer_clear_window"] == "4:40–6:00 PM"
    # every surfaced text field is a {"text": ...} dict
    for k in ("food_lean", "mood_tone"):
        assert isinstance(b[k], dict) and "text" in b[k]


def test_normalizers():
    from antar_engine.daily_vocab.tables import norm_nakshatra
    assert norm_nakshatra("Ashvini") == "Ashwini"
    assert norm_nakshatra("purva ashada") == "Purva Ashadha"
    assert norm_nakshatra("Pushya") == "Pushya"
    assert norm_nakshatra("garbage") is None


def test_debug_is_internal_only():
    b = compute_concrete_block(**BUSY)
    assert "_debug" in b
    assert "_debug" not in public_view(b)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} passed")
