"""Karakas rank by degree WITHIN the sign, not absolute longitude."""
from antar_engine.karakas import get_atmakaraka, get_all_karakas


def _chart(lons):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
             "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    return {"planets": {p: {"longitude": l, "sign": signs[int(l // 30)],
                            "degree": l % 30} for p, l in lons.items()}}


LONS = {"Sun": 29.5, "Moon": 40.0, "Mars": 70.0, "Mercury": 100.0,
        "Jupiter": 130.0, "Venus": 160.0, "Saturn": 350.0}


def test_atmakaraka_is_highest_in_sign_degree():
    # Saturn has the largest absolute longitude (350) but only 20 deg in Pisces.
    assert get_atmakaraka(_chart(LONS))["planet"] == "Sun"


def test_all_karakas_order_and_darakaraka():
    ks = get_all_karakas(_chart(LONS))
    assert [k["planet"] for k in ks][0] == "Sun"
    assert ks[0]["name"] == "Atmakaraka" and ks[1]["name"] == "Amatyakaraka"
    assert ks[1]["planet"] == "Saturn"          # 20 deg
    assert ks[-1]["planet"] == "Moon"           # 10 deg (lowest, ties broken stably)
    degs = [k["degree"] for k in ks]
    assert degs == sorted(degs, reverse=True)
