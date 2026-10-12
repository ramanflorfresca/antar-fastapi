from datetime import date, timedelta

from antar_engine import relationship_pattern as rp

BASE = {
    "Sun": {"sign": "Leo", "house": 5, "degree": 15.0, "longitude": 135.0},
    "Moon": {"sign": "Cancer", "house": 4, "degree": 25.0, "longitude": 115.0},
    "Mars": {"sign": "Aries", "house": 1, "degree": 22.0, "longitude": 22.0},
    "Mercury": {"sign": "Gemini", "house": 3, "degree": 18.0, "longitude": 78.0},
    "Jupiter": {"sign": "Sagittarius", "house": 9, "degree": 20.0, "longitude": 260.0},
    "Venus": {"sign": "Taurus", "house": 2, "degree": 12.0, "longitude": 42.0},
    "Saturn": {"sign": "Capricorn", "house": 10, "degree": 27.0, "longitude": 297.0},
    "Rahu": {"sign": "Pisces", "house": 12, "degree": 5.0, "longitude": 335.0},
    "Ketu": {"sign": "Virgo", "house": 6, "degree": 5.0, "longitude": 155.0},
}


def chart(**over):
    pl = {k: dict(v) for k, v in BASE.items()}
    for k, v in over.items():
        pl[k] = {**pl.get(k, {}), **v}
    return {"lagna": {"sign": "Aries"}, "planets": pl}


def dashas(md, ad, pd):
    s, e = (date.today() - timedelta(days=30)).isoformat(), (date.today() + timedelta(days=30)).isoformat()
    return {"vimsottari": [{"level": "mahadasha", "lord": md, "start_date": s, "end_date": e},
                           {"level": "antardasha", "lord": ad, "start_date": s, "end_date": e},
                           {"level": "pratyantardasha", "lord": pd, "start_date": s, "end_date": e}]}


def test_love_style_thresholds():
    assert rp._love_style(1.0, 1.0) == "balanced_strong"
    assert rp._love_style(-1.5, -1.5) == "thin_both"
    assert rp._love_style(1.0, -0.5) == "falls_in_easily"
    assert rp._love_style(-0.5, 1.0) == "slow_then_steady"
    assert rp._love_style(0.2, 0.0) == "balanced"
    assert rp._love_style(-1.0, -3.0) == "balanced"       # a big gap between two weak houses is not 'falls in easily'


def test_fifth_house_strong_seventh_weak_reads_falls_in_easily():
    # Sun (5th lord of an Aries chart is Sun) is strong in Leo; Venus (7th lord) debilitated in the 12th with Saturn on the 7th
    c = chart(Venus={"sign": "Virgo", "house": 6, "longitude": 170.0}, Saturn={"sign": "Libra", "house": 7, "longitude": 200.0},
              Jupiter={"sign": "Leo", "house": 5, "longitude": 130.0})
    a = rp.analyze_pattern(c, {})
    assert a["available"] and a["s5"] > a["s7"]
    assert a["love_style"] in ("falls_in_easily", "balanced")


def test_period_running_on_fifth_vs_seventh():
    c = chart()
    # Aries chart: 5th lord Sun (sits in the 5th), 7th lord Venus
    assert rp.analyze_pattern(c, dashas("Sun", "Sun", "Moon"))["running_on"] == "5th"
    assert rp.analyze_pattern(c, dashas("Venus", "Venus", "Moon"))["running_on"] == "7th"
    assert rp.analyze_pattern(c, dashas("Sun", "Venus", "Moon"))["running_on"] == "both"
    assert rp.analyze_pattern(c, dashas("Mercury", "Mercury", "Mercury"))["running_on"] == "neither"
    assert rp.analyze_pattern(c, {})["running_on"] is None


def test_running_text_separates_a_spark_from_commitment():
    c = chart()
    five = " ".join(rp.analyze_pattern(c, dashas("Sun", "Sun", "Moon"))["facts"])
    seven = " ".join(rp.analyze_pattern(c, dashas("Venus", "Venus", "Moon"))["facts"])
    assert "ROMANCE AND ATTRACTION" in five and "not proof of staying power" in five
    assert "COMMITMENT AND PARTNERSHIP" in seven


def test_venus_retrograde_is_framed_as_the_readers_pattern():
    c = chart(Venus={"is_retrograde": True})
    a = rp.analyze_pattern(c, {})
    assert a["venus"]["retrograde"] is True
    txt = " ".join(a["facts"])
    assert "REVISIT" in txt and "never a verdict on what any ex will do" in txt
    assert "REVISIT" not in " ".join(rp.analyze_pattern(chart(Venus={"is_retrograde": False}), {})["facts"])


def test_retrograde_is_derived_from_the_birth_moment_when_not_stored(monkeypatch):
    import antar_engine.antar_ephemeris as eph
    c = chart(Venus={"longitude": 100.0}); c["birth_jd"] = 2450000.0
    monkeypatch.setattr(eph, "planet_longitude", lambda p, jd: 99.5 + 22.0)       # sidereal = tropical - ayanamsa(22)
    monkeypatch.setattr(eph, "lahiri_ayanamsa", lambda jd: 22.0)
    assert rp.is_retrograde(c, "Venus") is True                                   # next-day longitude is lower
    monkeypatch.setattr(eph, "planet_longitude", lambda p, jd: 100.8 + 22.0)
    assert rp.is_retrograde(c, "Venus") is False
    assert rp.is_retrograde({"planets": {"Venus": {}}}, "Venus") is None


def test_moon_attachment_pattern_and_the_unloved_hedge():
    c = chart(Moon={"sign": "Scorpio", "house": 7}, Saturn={"sign": "Scorpio", "house": 7})
    a = rp.analyze_pattern(c, {})
    assert a["moon"]["pattern"] == "guarded" and a["moon"]["element"] == "water"
    txt = " ".join(a["facts"])
    assert "Feeling unloved while the bond is actually strong is usually this attachment pattern" in txt
    calm = " ".join(rp.analyze_pattern(chart(Moon={"sign": "Taurus", "house": 4}), {})["facts"])
    assert "Feeling unloved" not in calm


def test_facts_are_plain_language_and_never_claim_a_feeling():
    for c in (chart(), chart(Venus={"is_retrograde": True}), chart(Moon={"sign": "Scorpio", "house": 7}, Saturn={"sign": "Scorpio", "house": 7})):
        txt = " ".join(rp.analyze_pattern(c, dashas("Sun", "Venus", "Moon"))["facts"]).lower()
        for bad in ("dasha", "navamsa", "darakaraka", "upapada", "saturn", "rahu", "ketu", "mars", "capricorn", "he loves", "she loves", "doesn't love"):
            assert bad not in txt, bad
        assert "never says what another person feels" in txt


def test_fail_open():
    assert rp.analyze_pattern({}, {}) == {"available": False}
    assert rp.analyze_pattern(None, None) == {"available": False}
