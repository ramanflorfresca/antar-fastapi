from datetime import date, datetime, timedelta

from antar_engine import relationship_timing as rt

# Aries lagna: 6th lord Mercury, 7th lord Venus, 8th lord Mars, 12th lord Jupiter, 5th lord Sun
BASE = {
    "Sun": {"sign": "Leo", "house": 5, "degree": 15.0}, "Moon": {"sign": "Cancer", "house": 4, "degree": 25.0},
    "Mars": {"sign": "Aries", "house": 1, "degree": 22.0}, "Mercury": {"sign": "Gemini", "house": 3, "degree": 18.0},
    "Jupiter": {"sign": "Sagittarius", "house": 9, "degree": 20.0}, "Venus": {"sign": "Taurus", "house": 2, "degree": 12.0},
    "Saturn": {"sign": "Capricorn", "house": 10, "degree": 27.0}, "Rahu": {"sign": "Pisces", "house": 12, "degree": 5.0},
    "Ketu": {"sign": "Virgo", "house": 6, "degree": 5.0}}
CH = {"lagna": {"sign": "Aries"}, "planets": BASE}
TODAY = date(2026, 10, 12)


def run(md, ad, pd="Moon"):
    return {"md": md, "ad": ad, "pd": pd}


def season(md, ad, pd="Moon"):
    return rt.classify_season(BASE, "Aries", run(md, ad, pd))["season"]


def test_two_different_strain_lords_are_an_ending_not_a_fight():
    # Mercury rules the 6th, Mars the 8th: neither rules or sits in the 7th
    assert season("Mercury", "Mars") == "ending"
    assert season("Mars", "Jupiter") == "ending"          # 8th + 12th


def test_the_partnership_house_beside_a_strain_period_is_friction():
    # Venus rules the 7th; Mercury rules the 6th (the doc's "7th-lord main period with a 6th-lord sub-period is a fight, not final")
    assert season("Venus", "Mercury") == "friction"
    assert season("Mercury", "Venus") == "friction"
    # two strain houses but one period is the 7th lord (Venus also rules 2nd, not strain; use Mars+Venus -> 8th + 7th)
    assert season("Mars", "Venus") == "friction"


def test_a_period_tied_to_the_partnership_house_with_no_strain_is_opening():
    assert season("Venus", "Saturn") == "opening"
    assert season("Saturn", "Venus") == "opening"


def test_strain_with_no_tie_to_the_partnership_house_is_quiet():
    assert season("Ketu", "Sun") == "quiet"                # no lordship; nothing core
    assert season("Sun", "Moon") == "quiet"


def test_season_text_separates_ending_from_friction():
    ending = rt._SEASON_TXT["ending"]; friction = rt._SEASON_TXT["friction"]
    assert "NOT A FIGHT" in ending and "do not hold out a reunion date" in ending
    assert "NOT A FINAL BREAK" in friction


def _rows():
    def r(level, lord, s, e):
        return {"level": level, "lord_or_sign": lord, "start_date": s, "end_date": e}
    return {"vimsottari": [
        r("antardasha", "Mercury", "2026-06-01", "2027-02-01"),      # strain lord, not tied: skipped
        r("antardasha", "Saturn", "2027-02-01", "2027-09-01"),       # not tied: skipped
        r("antardasha", "Venus", "2027-09-01", "2029-01-01"),        # 7th lord, not strain: the stretch
        r("pratyantardasha", "Venus", "2027-01-05", "2027-02-20"),
        r("pratyantardasha", "Venus", "2030-01-05", "2030-02-20")]}


def test_next_supported_stretch_uses_connection_and_skips_strain_lords():
    s = rt.next_supported_stretch(BASE, "Aries", _rows(), TODAY)
    assert s["ad"]["lord"] == "Venus" and s["ad"]["start"] == date(2027, 9, 1)
    assert s["pd"]["start"] == date(2027, 1, 5) and s["pd"]["end"] == date(2027, 2, 20)       # inside the coming year only


def test_a_stretch_already_running_is_clipped_to_today():
    rows = {"vimsottari": [{"level": "antardasha", "lord_or_sign": "Venus", "start_date": "2026-01-01", "end_date": "2027-03-01"}]}
    s = rt.next_supported_stretch(BASE, "Aries", rows, TODAY)
    assert s["ad"]["start"] == TODAY


def test_no_connected_stretch_is_said_plainly():
    rows = {"vimsottari": [{"level": "antardasha", "lord_or_sign": "Saturn", "start_date": "2026-06-01", "end_date": "2028-01-01"},
                           {"level": "mahadasha", "lord_or_sign": "Saturn", "start_date": "2020-01-01", "end_date": "2039-01-01"}]}
    d = dict(rows); d["vimsottari"] = rows["vimsottari"] + [
        {"level": "antardasha", "lord_or_sign": "Saturn", "start_date": "2026-06-01", "end_date": "2028-01-01"}]
    a = rt.analyze_season(CH, _dashas_now("Saturn", "Saturn", "Saturn"), today=TODAY, with_transits=False)
    assert a["available"] and any("No sub-period in the next three years" in f for f in a["facts"])


def _dashas_now(md, ad, pd):
    s, e = (TODAY - timedelta(days=30)).isoformat(), (TODAY + timedelta(days=30)).isoformat()
    # the module reads "today" from date.today() for the running stack; build rows that bracket the real today too
    from datetime import date as D
    s2, e2 = (D.today() - timedelta(days=30)).isoformat(), (D.today() + timedelta(days=30)).isoformat()
    return {"vimsottari": [{"level": "mahadasha", "lord": md, "start_date": s2, "end_date": e2},
                           {"level": "antardasha", "lord": ad, "start_date": s2, "end_date": e2},
                           {"level": "pratyantardasha", "lord": pd, "start_date": s2, "end_date": e2}]}


def test_transits_use_planets_over_the_partnership_points_not_the_inner_inner_period():
    # Aries chart: 7th house sign Libra; 7th lord Venus natal sign Taurus; DK = lowest degree among Sun..Saturn = Venus (12.0)? Mercury 18... Venus 12 -> Taurus
    def signs(p, jd):
        # Moon sits in Libra for the first 2 days after `now` then moves on; Venus and Jupiter never touch the points
        day = jd - rt._jd(NOW)
        if p == "Moon":
            return "Libra" if 0.5 <= day < 2.5 else "Leo"
        return "Leo"
    NOW = datetime(2026, 10, 12, 0, 0)
    tr = rt.transit_windows(BASE, "Aries", NOW, sign_fn=signs)
    assert tr["Moon"]["next"][0] == date(2026, 10, 12) and tr["Moon"]["next"][1] == date(2026, 10, 14)
    assert tr["Venus"]["now"] is False and tr["Venus"]["next"] is None and tr["Jupiter"]["next"] is None


def test_no_sookshma_and_no_prediction_of_another_persons_move_in_the_facts():
    a = rt.analyze_season(CH, _dashas_now("Venus", "Saturn", "Moon"), today=TODAY, with_transits=False)
    txt = " ".join(a["facts"]).lower()
    assert "sookshma" not in txt and "sd lord" not in txt
    assert "never promise a date for what another person will do" in txt
    for bad in ("dasha", "navamsa", "saturn", "venus", "mercury", "mars"):
        assert bad not in txt, bad


def test_fail_open():
    assert rt.analyze_season({}, {}) == {"available": False}
    assert rt.analyze_season(CH, {}) == {"available": False}
    assert rt.analyze_season(None, None) == {"available": False}


def test_wired_after_the_foundation_layer_in_the_relationship_branch():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text()
    a, b, c = (src.index(t) for t in ("[rel-pattern 2026-10-12]", "[rel-foundation 2026-10-12]", "[rel-timing 2026-10-12]"))
    assert a < b < c < src.index('_rp.append("Close with ONE concrete, agency-oriented next step.")')
    assert "BOTH THE RUNNING PERIODS AND THE FOUNDATION POINT TO AN ENDING" in src
