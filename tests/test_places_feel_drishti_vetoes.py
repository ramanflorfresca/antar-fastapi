"""Nakshatra flavour, drishti and the extra veto flags (2026-10-12)."""
from antar_engine.places_composer import compose_watch_outs
from antar_engine.places_concern import relocation_veto_watch
from antar_engine.places_feel import relocated_feel, relocation_drishti


def _kinds(w):
    return [x["kind"] for x in w]


# ── feel ────────────────────────────────────────────────────────────────────
def test_feel_follows_nakshatra_ruler():
    assert "withdrawn" in relocated_feel({"relocated_lagna_longitude": 0.0})["text"]       # Ketu
    assert "warm, social" in relocated_feel({"relocated_lagna_longitude": 14.0})["text"]   # Venus
    assert "visible" in relocated_feel({"relocated_lagna_longitude": 27.0})["text"]        # Sun


def test_feel_none_without_degree_and_es_renders():
    assert relocated_feel({}) is None
    assert relocated_feel({"relocated_lagna_longitude": 14.0}, "es")["text"].startswith("En el día a día")


# ── drishti ─────────────────────────────────────────────────────────────────
def _ch(**signs):
    return {"planets": {p: {"sign_index": s} for p, s in signs.items()}}


RELOC = {"relocated_lagna_index": 0}      # love -> 7th house = Libra (index 6)


def test_supportive_aspect_onto_relocated_seventh():
    # Jupiter in Gemini(2) casts its 5th onto Libra; Venus in Aries(0) casts its 7th onto Libra
    d = relocation_drishti(_ch(Jupiter=2, Venus=0), RELOC, "love")
    assert d and d["polarity"] == "supportive"


def test_testing_aspect_onto_relocated_seventh():
    # Mars in Cancer(3) casts its 4th onto Libra; Saturn in Leo(4) casts its 3rd onto Libra
    d = relocation_drishti(_ch(Mars=3, Saturn=4), RELOC, "love")
    assert d and d["polarity"] == "testing"


def test_balanced_or_occupying_planets_give_nothing():
    assert relocation_drishti(_ch(Jupiter=2, Saturn=4), RELOC, "love") is None   # 1 vs 1
    assert relocation_drishti(_ch(Jupiter=6), RELOC, "love") is None            # occupant, not aspect
    assert relocation_drishti(_ch(Jupiter=2), RELOC, "money") is None           # no house for money
    assert relocation_drishti(_ch(Jupiter=2), {}, "love") is None


# ── extra vetoes ────────────────────────────────────────────────────────────
# Cancer lagna: lagna lord Moon, 8th lord Saturn, career lord (10th) Mars.
CH = {"lagna_sign": "Cancer",
      "planets": {"Moon": {"sign_index": 4}, "Mars": {"sign_index": 5}, "Saturn": {"sign_index": 8}}}
RELOC_V = {"relocated_lagna_index": 5}    # Moon (4) -> house 12; Mars (5) -> house 1


def _line(planet, angle, lat=10.0, lon=10.0):
    return {"planet": planet, "angle": angle, "polyline": [[lat, lon]]}


def test_lagna_stalled_when_lagna_lord_in_relocated_twelfth():
    assert "lagna_stalled" in _kinds(relocation_veto_watch(CH, "career", RELOC_V, {}, [], 0, 0))


def test_eighth_lord_on_any_close_angle():
    w = relocation_veto_watch(CH, "career", RELOC_V, {}, [_line("Saturn", "IC")], 10.0, 10.0)
    assert "eighth_lord_angle" in _kinds(w)
    w = relocation_veto_watch(CH, "career", RELOC_V, {}, [_line("Saturn", "IC", 10.0, 40.0)], 10.0, 10.0)
    assert "eighth_lord_angle" not in _kinds(w)


def test_node_on_ac_or_mc_only():
    assert "node_angle" in _kinds(relocation_veto_watch(CH, "career", RELOC_V, {}, [_line("Rahu", "MC")], 10.0, 10.0))
    assert "node_angle" not in _kinds(relocation_veto_watch(CH, "career", RELOC_V, {}, [_line("Rahu", "IC")], 10.0, 10.0))


def test_weak_love_karaka_on_dc_unless_rescued():
    line = [_line("Venus", "DC")]
    weak = {"Venus": {"condition": "debilitated", "cancelled": False}}
    saved = {"Venus": {"condition": "debilitated", "cancelled": True}}
    assert "dc_weak_karaka" in _kinds(relocation_veto_watch(CH, "love", RELOC_V, weak, line, 10.0, 10.0))
    assert "dc_weak_karaka" not in _kinds(relocation_veto_watch(CH, "love", RELOC_V, saved, line, 10.0, 10.0))
    assert "dc_weak_karaka" not in _kinds(relocation_veto_watch(CH, "career", RELOC_V, weak, line, 10.0, 10.0))


def test_new_watch_copy_renders_en_es():
    for kind in ("lagna_stalled", "eighth_lord_angle", "node_angle", "dc_weak_karaka"):
        w = [{"kind": kind, "planet": "Saturn"}]
        assert len(compose_watch_outs("love", w, "en")) == 1
        assert len(compose_watch_outs("love", w, "es")) == 1
