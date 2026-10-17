"""[focus-why 2026-10-17] Why a window is strong for an area, in plain words, from the chapters that run over it."""
from datetime import date

from antar_engine import focus_why as fw, ritual_today as rt

TODAY = date(2026, 10, 17)
CH = [{"start": "2026-10-17", "end": "2027-01-07", "theme": "Ambition", "nature": "testing", "supports": True,
       "covers": "hunger, novelty, going beyond the usual; foreign things, technology, sudden rises",
       "watch": "obsession, illusion, over-reach, risky shortcuts", "helps": "checking facts, grounded advice, one step at a time"},
      {"start": "2027-01-07", "end": "2027-04-17", "theme": "Growth", "nature": "supportive", "supports": True,
       "covers": "wisdom, guidance, generosity; teachers, children, luck, long-term growth", "watch": "over-promising", "helps": "moderation"}]
BRING = [{"text": "This period is prosperous for you."}]
WIN = {"best": {"start": "2026-10-17", "end": "2027-01-16", "peaks": [{"start": "2026-10-17", "end": "2026-11-26"}]}}


def test_why_explains_the_cause_the_next_chapter_the_watch_and_the_peak():
    w = fw.build("Business and money", BRING, CH, WIN, "en", TODAY)
    assert w["headline"] == "This period is prosperous for you."
    b = " ".join(w["because"])
    assert "You are in an Ambition chapter until Jan 7, 2027. It is about hunger, novelty" in b
    assert "It works through the same part of your life as business and money, which is why this stretch lifts it." in b
    assert "From Jan 7, 2027, a Growth chapter takes over: wisdom, guidance" in b and "It keeps lifting business and money." in b
    assert "In this chapter, watch for obsession, illusion, over-reach, risky shortcuts. What helps: checking facts" in b
    assert w["peak"] == "The strongest stretch is Oct 17 to Nov 26."
    assert rt.jargon_leaks({"h": w["headline"], "b": w["because"], "p": w["peak"]}) == []


def test_a_chapter_that_works_against_the_area_says_so():
    ch = [dict(CH[0], supports=False)]
    assert "It works against business and money, so progress here asks for patience." in " ".join(fw.build("Business and money", BRING, ch, None, "en", TODAY)["because"])


def test_spanish_and_nothing_real():
    w = fw.build("Dinero", BRING, [dict(CH[0], covers="hambre y novedad", watch="obsesión", helps="verificar datos")], WIN, "es", TODAY)
    assert "Estás en un capítulo de Ambition hasta el 7 ene 2027. Trata de hambre y novedad." in " ".join(w["because"])
    assert w["peak"] == "El tramo más fuerte va del 17 oct al 26 nov."
    assert fw.build("Money", [], [], None, "en", TODAY) is None
    assert fw.build("Money", [], [dict(CH[0], end="2020-01-01")], None, "en", TODAY) is None


def test_focus_detail_carries_the_why_block():
    import inspect
    from antar_engine import focus_view
    assert '"why": why' in inspect.getsource(focus_view._detail)
