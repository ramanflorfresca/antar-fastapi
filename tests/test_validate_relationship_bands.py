import importlib.util
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vrb", ROOT / "antar_research" / "validate_relationship_bands.py")
vrb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vrb)


def cohort(n, share_fragile, base, odds_ratio, seed=1, rodden="AA"):
    """Synthetic ever-married people with a PLANTED association (or none, odds_ratio=1)."""
    rng = random.Random(seed)
    odds = base / (1 - base) * odds_ratio
    p_frag = odds / (1 + odds)
    out = []
    for _ in range(n):
        frag = rng.random() < share_fragile
        broke = rng.random() < (p_frag if frag else base)
        score = (-2.0 if frag else 1.0) + rng.gauss(0, 1.0) - (0.7 if broke else 0)
        out.append({"band": "fragile" if frag else "mixed", "score": score, "sus_fragile": frag, "dk_bad": frag and rng.random() < .5,
                    "d9_weak": rng.random() < .3, "broke": broke, "rodden": rodden})
    return out


def test_a_planted_effect_in_an_adequate_cohort_passes():
    r = vrb.evaluate(cohort(400, 0.3, 0.30, 3.0, seed=2))
    assert r["verdict"] == "PASSES" and r["h1"]["p"] < 0.05 and r["h1"]["placebo_false_positive_rate"] <= 0.12


def test_no_effect_in_an_adequate_cohort_fails_instead_of_inventing_one():
    fails = sum(vrb.evaluate(cohort(400, 0.3, 0.30, 1.0, seed=s))["verdict"] == "FAILS" for s in range(5, 10))
    assert fails >= 4                                                           # a powered null is reported as a FAIL, not a pass


def test_a_tiny_cohort_is_not_testable_whatever_it_shows():
    for s in range(6):
        r = vrb.evaluate(cohort(11, 0.36, 0.40, 1.0, seed=s))
        assert r["verdict"] == "NOT TESTABLE", r
    # even a striking-looking 2x2 on 14 people is not evidence
    striking = [{"band": "fragile", "score": -3, "sus_fragile": True, "dk_bad": True, "d9_weak": True, "broke": True, "rodden": "AA"}] * 4 + \
               [{"band": "mixed", "score": 1, "sus_fragile": False, "dk_bad": False, "d9_weak": False, "broke": False, "rodden": "AA"}] * 10
    assert vrb.evaluate(striking)["verdict"] == "NOT TESTABLE"


def test_aa_a_scope_drops_the_unrated_charts():
    mixed = cohort(200, .3, .3, 3.0, seed=4, rodden="AA") + cohort(200, .3, .3, 1.0, seed=5, rodden="C")
    assert vrb.evaluate(mixed, aa_a_only=True)["n"] == 200 and vrb.evaluate(mixed)["n"] == 400


def test_no_variation_in_the_outcome_is_not_testable():
    r = vrb.evaluate([dict(x, broke=False) for x in cohort(100, .3, .3, 1.0)])
    assert r["verdict"] == "NOT TESTABLE" and "no variation" in r["reason"]


def test_report_has_the_verdict_the_table_and_the_power_and_no_identifiers():
    r = vrb.evaluate(cohort(400, 0.3, 0.30, 3.0, seed=2))
    md = vrb.report([("All charts", r)], "unit test")
    assert "**Verdict: PASSES**" in md and "| fragile band |" in md and "smallest odds ratio detectable" in md
    assert "Aggregates only" in md


def test_running_on_and_season_at_use_the_period_at_the_event_date():
    rows = [{"level": "mahadasha", "lord": "Mercury", "start_date": "2000-01-01", "end_date": "2017-01-01"},
            {"level": "antardasha", "lord": "Mars", "start_date": "2010-01-01", "end_date": "2012-01-01"},
            {"level": "antardasha", "lord": "Venus", "start_date": "2012-01-01", "end_date": "2014-01-01"}]
    import datetime as dt
    assert vrb._running_on(rows, dt.date(2011, 6, 1)) == {"md": "Mercury", "ad": "Mars"}
    assert vrb._running_on(rows, dt.date(2013, 6, 1)) == {"md": "Mercury", "ad": "Venus"}
    pl = {"Sun": {"sign": "Leo", "house": 5, "degree": 15.0}, "Moon": {"sign": "Cancer", "house": 4, "degree": 25.0},
          "Mars": {"sign": "Aries", "house": 1, "degree": 22.0}, "Mercury": {"sign": "Gemini", "house": 3, "degree": 18.0},
          "Jupiter": {"sign": "Sagittarius", "house": 9, "degree": 20.0}, "Venus": {"sign": "Taurus", "house": 2, "degree": 12.0},
          "Saturn": {"sign": "Capricorn", "house": 10, "degree": 27.0}, "Rahu": {"sign": "Pisces", "house": 12, "degree": 5.0},
          "Ketu": {"sign": "Virgo", "house": 6, "degree": 5.0}}
    rec = {"chart": {"planets": pl, "lagna": {"sign": "Aries"}}, "dasha_rows": rows}
    assert vrb.season_at(rec, dt.date(2011, 6, 1)) == "ending"                # Aries chart: Mercury (6th) + Mars (8th)
    assert vrb.season_at(rec, dt.date(2013, 6, 1)) == "friction"              # Mercury (6th) beside Venus (the 7th lord)
    assert vrb.season_at(rec, dt.date(1990, 1, 1)) is None


def test_h4_finds_a_planted_timing_effect_and_stays_quiet_on_noise():
    import datetime as dt
    pl = {"Sun": {"sign": "Leo", "house": 5, "degree": 15.0}, "Moon": {"sign": "Cancer", "house": 4, "degree": 25.0},
          "Mars": {"sign": "Aries", "house": 1, "degree": 22.0}, "Mercury": {"sign": "Gemini", "house": 3, "degree": 18.0},
          "Jupiter": {"sign": "Sagittarius", "house": 9, "degree": 20.0}, "Venus": {"sign": "Taurus", "house": 2, "degree": 12.0},
          "Saturn": {"sign": "Capricorn", "house": 10, "degree": 27.0}, "Rahu": {"sign": "Pisces", "house": 12, "degree": 5.0},
          "Ketu": {"sign": "Virgo", "house": 6, "degree": 5.0}}
    # a lifetime that is 'quiet' (Saturn/Saturn) except one 2-year Mercury-Mars (ending) stretch, in which every divorce is placed
    rows = [{"level": "mahadasha", "lord": "Saturn", "start_date": "1980-01-01", "end_date": "2060-01-01"},
            {"level": "antardasha", "lord": "Saturn", "start_date": "1980-01-01", "end_date": "2060-01-01"}]
    def person(i, planted):
        rws = rows if not planted else [
            {"level": "mahadasha", "lord": "Mercury", "start_date": "2005-01-01", "end_date": "2007-01-01"},
            {"level": "antardasha", "lord": "Mars", "start_date": "2005-01-01", "end_date": "2007-01-01"},
            {"level": "mahadasha", "lord": "Saturn", "start_date": "1980-01-01", "end_date": "2005-01-01"},
            {"level": "antardasha", "lord": "Saturn", "start_date": "1980-01-01", "end_date": "2005-01-01"},
            {"level": "mahadasha", "lord": "Saturn", "start_date": "2007-01-01", "end_date": "2060-01-01"},
            {"level": "antardasha", "lord": "Saturn", "start_date": "2007-01-01", "end_date": "2060-01-01"}]
        return {"chart": {"planets": pl, "lagna": {"sign": "Aries"}}, "dasha_rows": rws, "birth": "1975-01-01",
                "divorces": ["2006-03-01"], "marriages": []}
    planted = vrb.h4([person(i, True) for i in range(12)], n_random=30, perms=800)["divorce -> ending/friction"]
    assert planted["n"] == 12 and planted["mean_diff"] > 0.8 and planted["p"] < 0.01
    noise = vrb.h4([person(i, False) for i in range(12)], n_random=30, perms=800)["divorce -> ending/friction"]
    assert abs(noise["mean_diff"]) < 0.01 and noise["p"] > 0.2
    assert vrb.h4([person(0, True)] * 3)["divorce -> ending/friction"]["p"] is None          # too few people: no p-value at all
