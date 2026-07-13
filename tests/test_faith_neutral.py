"""P3 — the daily giving-nudge must never assume a country's religion."""
from antar_engine.today_nudge import _GIVING_PLACE_BY_COUNTRY, _GIVING_PLACE_DEFAULT, _giving_place
from antar_engine.daily_prediction_engine import _faith_neutralize

_NAMED_HOUSES = ("church", "temple", "mosque", "gurdwara", "gurudwara",
                 "synagogue", "mandir", "masjid")


def test_no_named_house_of_worship_in_map():
    for cc, place in _GIVING_PLACE_BY_COUNTRY.items():
        low = place.lower()
        for h in _NAMED_HOUSES:
            assert h not in low, f"{cc} still names {h!r}: {place!r}"
    for h in _NAMED_HOUSES:
        assert h not in _GIVING_PLACE_DEFAULT.lower()


def test_giving_place_is_neutral():
    assert _giving_place("US") == "community kitchen or a place of worship"
    assert "gurdwara" not in _giving_place("IN")
    assert _giving_place("ZZ") == _GIVING_PLACE_DEFAULT      # unknown -> neutral default


def test_neutralize_scrubs_named_houses():
    assert "church" not in _faith_neutralize(
        "leave a donation at the church or community kitchen").lower()
    assert "gurdwara" not in _faith_neutralize("visit your gurdwara today").lower()
    assert "place of worship" in _faith_neutralize("donate at the temple").lower()


def test_neutralize_leaves_clean_text_untouched():
    s = "Share the credit and give to someone in need today."
    assert _faith_neutralize(s) == s
