"""A reader who is IN the relationship must never be told, from an unvalidated heuristic, that their own marriage is thin, ending, or
worth 'stopping waiting' on. Same signals, worded as tendencies to tend."""
from datetime import date, timedelta

from antar_engine import people_pointer as pp
from antar_engine import relationship_foundation as rf
from antar_engine import relationship_timing as rt

HARSH = ("thin", "fragile", "failing", "pulling away", "stop waiting", "reunion", "closure", "no window", "the marriage is ending", "give up",
         "weak", "doesn't love", "does not love")
SUS = {"level": "fragile"}
D9 = {"level": "weak"}


def test_foundation_wording_for_a_partnered_reader_has_no_verdicts():
    for band in ("fragile", "mixed", "sound"):
        for state in ("invested", "mixed", "detached", "burdened"):
            txt = " ".join(rf.foundation_facts(band, SUS, {"state": state}, D9, band == "fragile", partnered=True)).lower()
            # the instruction line itself NAMES the banned words so the model knows not to use them: strip it before checking
            body = txt.replace(txt[txt.index("this reader is partnered"):], "")
            for bad in HARSH:
                assert bad not in body, (band, state, bad)
            assert "protecting the bond" in txt and "never judge it" in txt
            assert "not yet validated" in txt


def test_unpartnered_wording_is_unchanged():
    txt = " ".join(rf.foundation_facts("fragile", SUS, {"state": "detached"}, D9, True, partnered=False))
    assert "FRAGILE FOUNDATION" in txt and "looks thin" in txt and "pulling away" in txt


def test_analyze_foundation_passes_the_flag_through():
    ch = {"lagna": {"sign": "Aries"}, "planets": {
        "Jupiter": {"sign": "Taurus", "house": 2, "degree": 20.0}, "Sun": {"sign": "Aquarius", "house": 11, "degree": 15.0},
        "Moon": {"sign": "Virgo", "house": 6, "degree": 25.0}, "Mars": {"sign": "Aries", "house": 1, "degree": 22.0},
        "Mercury": {"sign": "Gemini", "house": 3, "degree": 18.0}, "Venus": {"sign": "Virgo", "house": 6, "degree": 12.0},
        "Saturn": {"sign": "Leo", "house": 5, "degree": 27.0}, "Rahu": {"sign": "Leo", "house": 5, "degree": 5.0},
        "Ketu": {"sign": "Aquarius", "house": 11, "degree": 5.0}}}
    assert "FRAGILE FOUNDATION" in " ".join(rf.analyze_foundation(ch)["facts"])
    assert "THIS READER IS PARTNERED" in " ".join(rf.analyze_foundation(ch, partnered=True)["facts"])


def test_an_ending_season_is_not_said_to_a_partnered_reader():
    # Aries chart: Mercury rules the 6th, Mars the 8th -> an "ending" season for an unpartnered reader
    pl = {"Sun": {"sign": "Leo", "house": 5, "degree": 15.0}, "Moon": {"sign": "Cancer", "house": 4, "degree": 25.0},
          "Mars": {"sign": "Aries", "house": 1, "degree": 22.0}, "Mercury": {"sign": "Gemini", "house": 3, "degree": 18.0},
          "Jupiter": {"sign": "Sagittarius", "house": 9, "degree": 20.0}, "Venus": {"sign": "Taurus", "house": 2, "degree": 12.0},
          "Saturn": {"sign": "Capricorn", "house": 10, "degree": 27.0}, "Rahu": {"sign": "Pisces", "house": 12, "degree": 5.0},
          "Ketu": {"sign": "Virgo", "house": 6, "degree": 5.0}}
    ch = {"lagna": {"sign": "Aries"}, "planets": pl}
    s, e = (date.today() - timedelta(days=30)).isoformat(), (date.today() + timedelta(days=30)).isoformat()
    d = {"vimsottari": [{"level": "mahadasha", "lord": "Mercury", "start_date": s, "end_date": e},
                        {"level": "antardasha", "lord": "Mars", "start_date": s, "end_date": e},
                        {"level": "pratyantardasha", "lord": "Moon", "start_date": s, "end_date": e}]}
    solo = rt.analyze_season(ch, d, with_transits=False)
    wed = rt.analyze_season(ch, d, with_transits=False, partnered=True)
    assert solo["season"] == wed["season"] == "ending"                       # the SIGNAL is the same
    assert "ENDING SEASON" in solo["facts"][0] and "do not hold out a reunion date" in solo["facts"][0]
    assert "PARTNERED" in wed["facts"][0] and "NOT an ending" in wed["facts"][0]
    assert "ENDING SEASON" not in wed["facts"][0]


def test_the_both_layers_agree_message_is_not_sent_to_a_partnered_reader():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text()
    assert '_sn["season"] == "ending" and _fband == "fragile" and _partnered is not True' in src
    assert "analyze_foundation(chart_data, partnered=(_partnered is True))" in src


def test_people_pointer_is_soft_with_a_partnered_reader_in_every_language():
    ch = {"lagna": {"sign": "Aries"}, "planets": {
        "Jupiter": {"sign": "Taurus", "house": 2, "degree": 20.0}, "Sun": {"sign": "Aquarius", "house": 11, "degree": 15.0},
        "Moon": {"sign": "Virgo", "house": 6, "degree": 25.0}, "Mars": {"sign": "Aries", "house": 1, "degree": 22.0},
        "Mercury": {"sign": "Gemini", "house": 3, "degree": 18.0}, "Venus": {"sign": "Virgo", "house": 6, "degree": 12.0},
        "Saturn": {"sign": "Leo", "house": 5, "degree": 27.0}, "Rahu": {"sign": "Leo", "house": 5, "degree": 5.0},
        "Ketu": {"sign": "Aquarius", "house": 11, "degree": 5.0}}}
    assert rf.analyze_foundation(ch)["foundation"]["band"] == "fragile"
    s, e = (date.today() - timedelta(days=30)).isoformat(), (date.today() + timedelta(days=30)).isoformat()
    quiet = {"vimsottari": [{"level": "mahadasha", "lord": "Mercury", "start_date": s, "end_date": e},
                            {"level": "antardasha", "lord": "Mercury", "start_date": s, "end_date": e},
                            {"level": "pratyantardasha", "lord": "Mercury", "start_date": s, "end_date": e}]}
    for lang in ("en", "es", "pt", "hinglish"):
        solo = pp.partner_payload("Dana", lang, ch, ch, quiet, "state", partnered=False)["read"]
        wed = pp.partner_payload("Dana", lang, ch, ch, quiet, "state", partnered=True)
        assert solo != wed["read"]
        assert pp._T[lang]["verdict_stop"] not in wed["read"] and pp._T[lang]["side"]["fragile"] not in wed["read"]
        assert pp._T[lang]["verdict_care"] in wed["read"] and pp._T[lang]["side_care"] in wed["read"]
        assert wed["next"] == pp._T[lang]["next_care"]
        miss = pp.missing_payload(lang, ch, "compat", partnered=True)["read"]
        assert pp._T[lang]["side"]["fragile"] not in miss and pp._T[lang]["side_care"] in miss
    en = pp.partner_payload("Dana", "en", ch, ch, quiet, "state", partnered=True)["read"].lower()
    for bad in ("stop waiting", "thin", "decide what you want for yourself"):
        assert bad not in en


def test_is_partnered():
    assert pp.is_partnered("married") and pp.is_partnered("Partnered") and pp.is_partnered("in a relationship")
    assert pp.is_partnered("single", {"compat_type": "spouse"}) and pp.is_partnered("", {"relation": "wife"})
    assert not pp.is_partnered("divorced") and not pp.is_partnered("single") and not pp.is_partnered(None)
    assert not pp.is_partnered("separated", {"compat_type": "romantic"})
