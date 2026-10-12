"""Chandra gochar + daily double transit + day-lord ownership (confidence only)."""
import inspect
from datetime import date

from antar_engine import daily_precision as dp
from antar_engine.daily_convergence import daily_convergence
from antar_engine import daily_double_transit as ddt

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def test_chandra_table_parity_with_engine():
    from antar_engine.daily_prediction_engine import get_chandra_bala
    for h in range(1, 13):
        natal = "Aries"
        cur = SIGNS[(h - 1) % 12]
        eng = get_chandra_bala(natal, cur)["strength"]
        d = dp._CHANDRA_FAVOR[h]
        assert {"favorable": 1, "neutral": 0, "unfavorable": -1}[eng] == d, h


def test_moon_from_moon_and_agreement():
    assert dp.moon_house_from_moon("Cancer", "Aries") == 4
    assert dp.chandra_agreement(1, 1) == "agree"
    assert dp.chandra_agreement(1, -1) == "disagree"
    assert dp.chandra_agreement(0, -1) == "n/a"


def test_score_is_not_affected_by_new_fields():
    base = dp.compute_daily_precision("Rohini", "Leo", "Ashwini", "Cancer")
    new = dp.compute_daily_precision("Rohini", "Leo", "Ashwini", "Cancer",
                                     natal_moon_sign="Aries", weekday_index=0,
                                     dasha_ad="Moon")
    for k in ("tara_score_delta", "house_score_delta"):
        assert base[k] == new[k]
    assert dp.apply_precision_to_score(6, base) == dp.apply_precision_to_score(6, new)
    assert new["chandra_delta"] == -1 and new["day_owned_by"] == "ad"
    assert "apply" not in inspect.getsource(dp.apply_precision_to_score).replace("apply_precision", "") \
        or "chandra" not in inspect.getsource(dp.apply_precision_to_score)


def test_day_owner():
    assert dp.day_owned_by(3, "Venus", "Jupiter") == "pd"      # Thursday
    assert dp.day_owned_by(3, "Venus", "Mars") is None
    assert dp.day_owned_by(None, "Moon", "") is None


def _rows(tara, house, chandra=None, dt=None, nak_ok=True):
    return [
        {"key": "nakshatra", "available": nak_ok, "direction": tara},
        {"key": "moon_house", "available": True, "direction": house,
         "chandra_direction": chandra, "dt_direction": dt},
        {"key": "dasha", "available": True, "direction": "supportive"},
    ]


def test_legacy_rows_unchanged():
    out = daily_convergence(_rows("supportive", "supportive"), "supported", "positive")
    assert out["level"] == "high" and out["layers_read"] == 3


def test_disagreeing_house_counts_make_moon_axis_mixed():
    # lagna count says good, Chandra says bad -> house sub-axis neutral; tara carries
    a = daily_convergence(_rows("neutral", "supportive", chandra="friction"),
                          "supported", "positive")
    assert "the day's rhythm" not in a["aligned"]            # Moon axis netted 0
    assert "the day's rhythm" not in a["tension"]


def test_dt_never_adds_a_layer_and_cannot_raise_level():
    base = daily_convergence(_rows("neutral", "supportive"), "steady", "positive")
    dt = daily_convergence(_rows("neutral", "supportive", dt="supportive"), "steady", "positive")
    assert dt["layers_read"] == base["layers_read"]
    assert dt["level"] == base["level"]                       # named, not counted
    assert "the slow planets" in dt["aligned"]


def test_dt_can_break_a_moon_tie():
    # tara +, house - -> axis 0; DT + tips it positive
    tied = daily_convergence(_rows("supportive", "friction"), "supported", "positive")
    tipped = daily_convergence(_rows("supportive", "friction", dt="supportive"),
                               "supported", "positive")
    assert "the day's rhythm" not in tied["aligned"]
    assert "the day's rhythm" in tipped["aligned"]


CHART = {  # Aries lagna; Mars rules 1 & 8 -> houses 1, 8 (+ occupies 10th: Capricorn)
    "lagna": {"sign": "Aries", "sign_index": 0},
    "planets": {"Mars": {"sign": "Capricorn", "sign_index": 9},
                "Jupiter": {"sign": "Cancer", "sign_index": 3},
                "Moon": {"sign": "Taurus", "sign_index": 1}},
}


def test_lord_houses():
    assert ddt.lord_houses(CHART, "Mars") == {1, 8, 10}


def test_dt_needs_lit_house_in_lord_houses():
    pos = {"Saturn": 0, "Jupiter": 0, "Mars": 0, "Moon": 0}
    r = ddt.daily_double_transit(CHART, ["Mars"], 5, date(2026, 10, 12), positions=pos)
    assert r["available"] is False


def test_dt_fires_gives_polarity_by_house():
    # Moon frame: natal Moon Taurus(1); house 10 sign = Aquarius(10).
    # Jupiter occupies Aquarius; Saturn in Leo(4) aspects its 7th = Aquarius.
    pos = {"Saturn": 4, "Jupiter": 10, "Mars": 0, "Moon": 0}
    r = ddt.daily_double_transit(CHART, ["Mars"], 10, date(2026, 10, 12), positions=pos)
    assert r["available"] and r["verdict"] in ("likely", "fires") and r["polarity"] == 1
    r8 = ddt.daily_double_transit(CHART, ["Mars"], 8, date(2026, 10, 12), positions=pos)
    assert r8.get("polarity", -1) == -1 or r8["available"] is False
    p = {"moon_house_from_lagna": 10}
    ddt.attach_to_precision(p, CHART, ["Mars"], date(2026, 10, 12), positions=pos)
    assert p["dt_direction"] == "supportive"


def test_build_day_signals_carries_extras():
    pr = dp.compute_daily_precision("Rohini", "Leo", "Ashwini", "Cancer", natal_moon_sign="Aries")
    pr["dt_direction"] = "friction"
    rows = dp.build_day_signals(pr, "Jupiter", "Venus", "Mars")
    mh = [r for r in rows if r["key"] == "moon_house"][0]
    assert mh["chandra_direction"] and mh["dt_direction"] == "friction"
    assert len(rows) == 5                                     # no new visible row
