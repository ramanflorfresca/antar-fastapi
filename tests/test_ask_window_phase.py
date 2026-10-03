"""[groundwork-tense 2026-10-02] Live: asked in Oct 2026, /ask said "Not yet — an
earlier opening Oct 2026 to lay groundwork", narrating the current month as if
it were ahead. _ask_window_phase decides now / past / future at month level."""
from datetime import date


def _m():
    from dotenv import load_dotenv
    load_dotenv()
    import main
    return main


def test_window_phase():
    m = _m()
    today = date(2026, 10, 2)
    assert m._ask_window_phase("Oct 2026", today) == "now"
    assert m._ask_window_phase("Sep 2026 – Nov 2026", today) == "now"
    assert m._ask_window_phase("Aug 2026", today) == "past"
    assert m._ask_window_phase("Nov 2026 – Jan 2027", today) == "future"
    assert m._ask_window_phase("soon", today) == ""
