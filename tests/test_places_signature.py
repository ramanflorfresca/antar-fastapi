"""Unit tests for the per-city 'what it's good for' signature."""
import json
from antar_engine.places_composer import compose_signature

_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
            "Rahu", "Ketu")


def test_line_based_signature_names_concern_and_energy():
    scored = {"_signals": [{"planet": "Venus", "angle": "AC", "strength": 0.9}]}
    sig = compose_signature("money", scored, "en")
    assert sig["best_for"] == "Money through relationships & taste"
    assert sig["from_line"] is True
    assert "how you show up" in sig["line"]


def test_axis_changes_where_it_lands():
    dc = compose_signature("love", {"_signals": [{"planet": "Venus", "angle": "DC"}]}, "en")
    ac = compose_signature("love", {"_signals": [{"planet": "Venus", "angle": "AC"}]}, "en")
    assert "partnerships" in dc["line"] and "how you show up" in ac["line"]


def test_house_fallback_when_no_line():
    scored = {"_signals": [], "_house_hits": [
        {"planet": "Jupiter", "house": 11, "is_karaka": True}]}
    sig = compose_signature("money", scored, "en")
    assert sig["from_line"] is False
    assert sig["best_for"] == "Money through growth & guidance"
    assert "background" in sig["line"]


def test_karaka_house_hit_preferred_over_nonkaraka():
    scored = {"_signals": [], "_house_hits": [
        {"planet": "Mars", "house": 11, "is_karaka": False},
        {"planet": "Venus", "house": 2, "is_karaka": True}]}
    sig = compose_signature("money", scored, "en")
    assert sig["best_for"] == "Money through relationships & taste"


def test_none_when_no_signal_or_hit():
    assert compose_signature("money", {"_signals": [], "_house_hits": []}, "en") is None
    assert compose_signature("money", {}, "en") is None


def test_no_planet_names_leak():
    for p in _PLANETS:
        sig = compose_signature("career", {"_signals": [{"planet": p, "angle": "MC"}]}, "en")
        blob = json.dumps(sig)
        for name in _PLANETS:
            assert name not in blob, f"{name} leaked for planet {p}: {blob}"
