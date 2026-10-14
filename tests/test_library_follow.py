from datetime import datetime, timezone
from antar_engine import outcomes as oc, public_view as pv

NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)


def test_library_is_checkable_and_quoted_in_the_checkin():
    assert "library" in oc.CHECKABLE_SOURCES
    claim = {"source": "library", "language": "en", "topic": "money", "text_shown": "Income opens up.", "claim_type": "window"}
    assert "Income opens up." in oc.checkin_text(claim)


def test_build_library_claim_keeps_rule_internal_and_dedupes_by_ref_and_window():
    ref = pv.ref_for("BK.BVJ1.13")
    c = oc.build_library_claim("c1", "BK.BVJ1.13", ref, "Partnership takes shape.", "2026-10-14", "2026-10-25", "love", "en", NOW)
    assert c["source"] == "library" and c["engines"] == {"rule": "BK.BVJ1.13"} and ref in c["dedupe_key"]
    assert c["window_end"] == "2026-10-25" and c["checkin_due_at"].startswith("2026-10-25T09")
    assert "BK.BVJ1" not in c["text_shown"]
    c2 = oc.build_library_claim("c1", "BK.BVJ1.13", ref, "Partnership takes shape.", "2026-10-14", "2026-10-25", "love", "en", NOW)
    assert c["dedupe_key"] == c2["dedupe_key"]


def test_missing_end_defaults_to_two_weeks_and_bad_input_is_refused():
    c = oc.build_library_claim("c1", "R", "ref", "Text.", "2026-10-14", None, None, "es", NOW)
    assert c["window_end"] == "2026-10-28" and c["language"] == "es" and c["topic"] == "other"
    assert oc.build_library_claim("c1", "R", "ref", "  ", None, None, None) is None
    assert oc.build_library_claim("c1", "R", "ref", "Text.", "not-a-date", None, None) is None


def test_past_window_is_due_immediately():
    c = oc.build_library_claim("c1", "R", "ref", "Text.", "2026-09-01", "2026-09-10", "money", "en", NOW)
    assert c["checkin_due_at"] == NOW.isoformat()
