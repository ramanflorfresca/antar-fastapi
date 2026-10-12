"""The timing window must be a sub-period that touches the concern's own houses, not just the running PD."""
from antar_engine.event_narrator import _select_window


def _board(pd_connects):
    return {"vimshottari": {
        "pd": {"lord": "Venus", "start": "2026-07-26", "end": "2026-12-19", "connects_event": pd_connects,
               "upcoming": [{"lord": "Sun", "start": "2026-12-19", "end": "2027-02-01", "connects_event": False},
                            {"lord": "Mars", "start": "2027-04-15", "end": "2027-06-05", "connects_event": True}]},
        "ad": {"lord": "Rahu", "start": "2025-01-10", "end": "2027-06-05"}},
        "double_transit": {}}


def test_connecting_current_pd_is_used():
    w = _select_window("supported", _board(True))
    assert w["start"] == "2026-07-26"


def test_non_connecting_pd_moves_to_next_connecting_pd_in_the_ad():
    w = _select_window("supported", _board(False))
    assert w["start"] == "2027-04-15" and w["end"] == "2027-06-05"


def test_no_connecting_pd_left_falls_back_to_ad():
    b = _board(False)
    b["vimshottari"]["pd"]["upcoming"] = [{"lord": "Sun", "start": "2026-12-19", "end": "2027-02-01", "connects_event": False}]
    w = _select_window("supported", b)
    assert w["start"] == "2026-07-26"


def test_primary_house_period_is_preferred_over_a_shared_secondary_one():
    b = _board(True)
    b["vimshottari"]["pd"]["connects_primary"] = False           # current PD touches only a shared secondary house
    b["vimshottari"]["pd"]["upcoming"] = [
        {"lord": "Sun", "start": "2026-12-19", "end": "2027-02-01", "connects_event": True, "connects_primary": True},
        {"lord": "Mars", "start": "2027-04-15", "end": "2027-06-05", "connects_event": True, "connects_primary": False}]
    w = _select_window("supported", b)
    assert w["start"] == "2026-12-19"                              # the concern's own primary-house period wins


def test_promised_event_uses_the_primary_house_forming_window_first():
    b = {"vimshottari": {}, "double_transit": {
        "forming_windows": [{"start": "2026-11-01", "end": "2027-01-31"}],
        "forming_windows_primary": [{"start": "2027-07-01", "end": "2027-10-31"}]}}
    assert _select_window("promised_building", b)["start"] == "2027-07-01"
    b["double_transit"]["forming_windows_primary"] = []
    assert _select_window("promised_building", b)["start"] == "2026-11-01"      # falls back to the broad set
