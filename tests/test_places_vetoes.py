"""Veto-layer watch-outs on the relocated chart (2026-10-12)."""
from antar_engine.places_concern import relocation_veto_watch
from antar_engine.places_composer import compose_watch_outs

# Aries lagna: career lord = Saturn (Aquarius, idx 10). Sun in Libra (idx 6).
CHART = {"lagna_sign": "Aries",
         "planets": {"Saturn": {"sign_index": 10}, "Sun": {"sign_index": 6},
                     "Moon": {"sign_index": 1}}}


def _kinds(w):
    return [x["kind"] for x in w]


def test_lord_stalled_when_concern_lord_in_relocated_twelfth():
    # relocated lagna Pisces(11): Saturn (10) -> house 12
    w = relocation_veto_watch(CHART, "career", {"relocated_lagna_index": 11}, {}, [], 0, 0)
    assert "lord_stalled" in _kinds(w)


def test_no_veto_when_lord_well_placed():
    # relocated lagna Aries(0): Saturn -> house 11
    w = relocation_veto_watch(CHART, "career", {"relocated_lagna_index": 0}, {}, [], 0, 0)
    assert w == []


def test_karaka_broken_needs_debilitated_and_dusthana():
    cond = {"Sun": {"condition": "debilitated"}}
    # lagna Pisces(11): Sun (6) -> house 8
    w = relocation_veto_watch(CHART, "career", {"relocated_lagna_index": 11}, cond, [], 0, 0)
    assert "karaka_broken" in _kinds(w)
    # same house but not debilitated -> no karaka veto
    w = relocation_veto_watch(CHART, "career", {"relocated_lagna_index": 11},
                              {"Sun": {"condition": "neutral"}}, [], 0, 0)
    assert "karaka_broken" not in _kinds(w)


def test_dasha_dusthana_uses_running_mahadasha_lord():
    w = relocation_veto_watch(CHART, "career", {"relocated_lagna_index": 11}, {}, [], 0, 0,
                              dasha_lords=[("Saturn", 1.0), ("Moon", 0.5)])
    assert "dasha_dusthana" in _kinds(w)
    w = relocation_veto_watch(CHART, "career", {"relocated_lagna_index": 0}, {}, [], 0, 0,
                              dasha_lords=[("Saturn", 1.0)])
    assert "dasha_dusthana" not in _kinds(w)


def test_dc_malefic_only_for_love_and_only_when_close():
    line = {"planet": "Saturn", "angle": "DC", "polyline": [[10.0, 10.0]]}
    reloc = {"relocated_lagna_index": 0}
    assert "dc_malefic" in _kinds(relocation_veto_watch(CHART, "love", reloc, {}, [line], 10.0, 10.0))
    assert "dc_malefic" not in _kinds(relocation_veto_watch(CHART, "career", reloc, {}, [line], 10.0, 10.0))
    assert "dc_malefic" not in _kinds(relocation_veto_watch(CHART, "love", reloc, {}, [line], 10.0, 40.0))


def test_unavailable_relocation_yields_nothing():
    assert relocation_veto_watch(CHART, "career", {}, {}, [], 0, 0) == []


def test_veto_copy_renders_en_es():
    w = [{"kind": "lord_stalled", "planet": "Saturn"}, {"kind": "dasha_dusthana", "planet": "Saturn"}]
    assert len(compose_watch_outs("career", w, "en")) == 2
    assert compose_watch_outs("career", w, "es")[0].startswith("La parte de tu carta")
