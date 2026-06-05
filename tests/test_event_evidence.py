"""
tests/test_event_evidence.py — whole-board evidence block + Double Transit.

Pure-math tests: no ephemeris needed (DT positions injected). The ephemeris
paths (sidereal_sign_indices, dt_forming_windows, mars_trigger_windows) are
exercised by the live /ask/evidence curl test.

Run: cd ~/antarai && source venv311/bin/activate && python -m pytest tests/test_event_evidence.py -q
"""

from datetime import date

import pytest

from antar_engine import double_transit as dt
from antar_engine.event_evidence import (
    build_whole_board, _sub_periods, _karakas_by_degree_in_sign,
    CONCERN_TO_EVENT, EVENT_MAP,
)

S = dt.SIGN_INDEX  # name → index


# ── fixture chart: Capricorn lagna (matches jaimini.py's verified test) ──────

def _chart():
    # longitudes chosen so D1 signs match jaimini.py self-test placements
    def lng(sign_idx, deg):
        return sign_idx * 30.0 + deg

    P = {
        "Sun":     (7, 10.0),   # Scorpio
        "Moon":    (11, 5.0),   # Pisces
        "Mars":    (6, 28.0),   # Libra
        "Mercury": (6, 2.0),    # Libra
        "Jupiter": (10, 15.0),  # Aquarius
        "Venus":   (7, 22.0),   # Scorpio
        "Saturn":  (2, 19.0),   # Gemini
        "Rahu":    (7, 14.0),   # Scorpio
        "Ketu":    (1, 14.0),   # Taurus
    }
    lagna_idx = 9  # Capricorn
    planets = {}
    for p, (si, deg) in P.items():
        planets[p] = {
            "longitude": lng(si, deg),
            "sign": dt.SIGNS[si], "sign_index": si, "degree": deg,
            "house": (si - lagna_idx) % 12 + 1,
        }
    planets["Moon"]["nakshatra"] = "Uttara Bhadrapada"
    return {"lagna": {"sign": "Capricorn", "sign_index": 9, "degree": 12.0},
            "planets": planets}


def _dashas():
    return {
        "vimsottari": [
            {"level": "mahadasha", "planet_or_sign": "Saturn",
             "start_date": "2018-03-01", "end_date": "2037-03-01"},
            {"level": "antardasha", "planet_or_sign": "Venus",
             "start_date": "2025-01-10", "end_date": "2028-03-12"},
        ],
        "jaimini": [
            {"level": "mahadasha", "planet_or_sign": "Taurus",
             "start_date": "2023-11-01", "end_date": "2029-11-01"},
        ],
    }


TODAY = date(2026, 6, 5)


# ── Double Transit geometry ──────────────────────────────────────────────────

def test_jupiter_aspect_set():
    # Jupiter in Cancer (3): occupies 3, aspects 5th=Scorpio(7), 7th=Cap(9), 9th=Pisces(11)
    assert dt.aspected_signs("Jupiter", S["Cancer"]) == {S["Cancer"], S["Scorpio"], S["Capricorn"], S["Pisces"]}


def test_saturn_aspect_set():
    # Saturn in Pisces (11): occupies 11, 3rd=Taurus(1), 7th=Virgo(5), 10th=Sag(8)
    assert dt.aspected_signs("Saturn", S["Pisces"]) == {S["Pisces"], S["Taurus"], S["Virgo"], S["Sagittarius"]}


def test_default_planet_aspects_only_7th():
    assert dt.aspected_signs("Venus", 0) == {0, 6}


def test_double_transit_intersection():
    # Jupiter Cancer + Saturn Pisces → DT on Pisces only
    both = dt.aspected_signs("Jupiter", S["Cancer"]) & dt.aspected_signs("Saturn", S["Pisces"])
    assert both == {S["Pisces"]}


# ── targets: house + lord + lord's navamsa, per frame ───────────────────────

def test_targets_lagna_frame_4th_house():
    chart = _chart()
    targets = dt.build_targets(chart, [4], "lagna")
    kinds = {(t["kind"], t["sign"]) for t in targets}
    # 4th from Capricorn = Aries; lord Mars sits in Libra
    assert ("house", "Aries") in kinds
    assert ("lord_natal", "Libra") in kinds


def test_targets_moon_frame_differs():
    chart = _chart()
    t_moon = dt.build_targets(chart, [4], "moon")
    # 4th from Pisces Moon = Gemini; lord Mercury sits in Libra
    kinds = {(t["kind"], t["sign"]) for t in t_moon}
    assert ("house", "Gemini") in kinds
    assert ("lord_natal", "Libra") in kinds


def test_targets_include_lord_navamsa_when_d9_given():
    chart = _chart()
    d9 = {"Mars": {"sign": "Leo", "sign_index": 4}}
    targets = dt.build_targets(chart, [4], "lagna", d9=d9)
    assert any(t["kind"] == "lord_navamsa" and t["sign"] == "Leo" for t in targets)


# ── verdict rule: moon primary, lagna confirm ────────────────────────────────

def _dt_verdict(positions, houses=(4,)):
    out = dt.dt_state_for_event(_chart(), list(houses), TODAY, positions=positions)
    return out["classical_verdict"], out


def test_verdict_fires_when_both_frames_hit():
    # Lord of 4th-from-lagna (Mars) and of 4th-from-moon (Mercury) both sit in
    # Libra → DT on Libra hits BOTH frames via lord_natal.
    # Jupiter in Gemini aspects Libra (5th); Saturn in Aries aspects Libra (7th).
    verdict, _ = _dt_verdict({"Saturn": S["Aries"], "Jupiter": S["Gemini"],
                              "Mars": 0, "Moon": 0})
    assert verdict == "fires"


def test_verdict_likely_when_moon_only():
    # DT on Gemini (4th-from-Moon house sign): Jupiter in Aquarius aspects
    # Gemini (5th); Saturn in Gemini occupies it. Lagna-frame targets
    # (Aries house / Libra lord / —) must NOT be in both sets.
    pos = {"Saturn": S["Gemini"], "Jupiter": S["Aquarius"], "Mars": 0, "Moon": 0}
    both = dt.aspected_signs("Saturn", pos["Saturn"]) & dt.aspected_signs("Jupiter", pos["Jupiter"])
    assert S["Gemini"] in both and S["Aries"] not in both and S["Libra"] not in both
    verdict, _ = _dt_verdict(pos)
    assert verdict == "likely"


def test_verdict_none_when_no_frame_hits():
    # DT lands on Virgo only (not a target for house 4 in either frame):
    # Saturn in Pisces aspects Virgo (7th); Jupiter in Capricorn aspects
    # Virgo (9th). Shared set = {Virgo, Pisces}… Pisces is moon-frame? 4th
    # house from Pisces is Gemini; lord positions in Libra. Pisces is not a
    # target for house 4. Confirm no target overlap.
    pos = {"Saturn": S["Pisces"], "Jupiter": S["Capricorn"], "Mars": 0, "Moon": 0}
    both = dt.aspected_signs("Saturn", pos["Saturn"]) & dt.aspected_signs("Jupiter", pos["Jupiter"])
    targets_l = {t["sign_index"] for t in dt.build_targets(_chart(), [4], "lagna")}
    targets_m = {t["sign_index"] for t in dt.build_targets(_chart(), [4], "moon")}
    if both & (targets_l | targets_m):
        pytest.skip("position pick overlaps targets — adjust fixture")
    verdict, _ = _dt_verdict(pos)
    assert verdict == "none"


def test_functional_pair_reported():
    out = dt.dt_state_for_event(
        _chart(), [4], TODAY,
        functional_pair=("Mars", "Saturn"),
        positions={"Saturn": S["Aries"], "Jupiter": S["Gemini"],
                   "Mars": S["Gemini"], "Moon": 0},
    )
    assert out.get("functional", {}).get("pair") == ["Mars", "Saturn"]
    assert out["functional"]["verdict"] in ("fires", "likely", "weak", "none")


# ── PD/SD subdivision ────────────────────────────────────────────────────────

def test_sub_periods_cover_parent_span_and_start_with_parent_lord():
    s, e = date(2025, 1, 10), date(2028, 3, 12)
    pds = _sub_periods("Venus", s, e)
    assert len(pds) == 9
    assert pds[0]["lord"] == "Venus"
    assert pds[0]["start"] == s and pds[-1]["end"] == e
    for a, b in zip(pds, pds[1:]):
        assert a["end"] == b["start"]


def test_sub_periods_proportional():
    s, e = date(2020, 1, 1), date(2030, 1, 1)   # 10y span
    pds = _sub_periods("Sun", s, e)
    sun = next(p for p in pds if p["lord"] == "Sun")
    # Sun share = 6/120 of 10y ≈ 0.5y ≈ 183d
    assert abs((sun["end"] - sun["start"]).days - 182.6) < 3


# ── karaka ranking (degree-in-sign, classical) ───────────────────────────────

def test_karaka_ranking_by_degree_in_sign():
    ks = _karakas_by_degree_in_sign(_chart()["planets"])
    assert ks[0]["planet"] == "Mars" and ks[0]["name"] == "Atmakaraka"   # 28°
    assert ks[1]["planet"] == "Venus"                                    # 22°
    assert ks[-1]["planet"] == "Mercury"                                 # 2°
    assert len(ks) == 7


# ── whole board ──────────────────────────────────────────────────────────────

def test_board_assembles_without_ephemeris():
    board = build_whole_board(
        _chart(), {}, _dashas(), "1990-02-10", "property",
        current_date=TODAY,
        dt_positions={"Saturn": S["Aries"], "Jupiter": S["Gemini"],
                      "Mars": S["Cancer"], "Moon": S["Leo"]},
    )
    assert board["generated"]["event"] == "relocation"
    assert board["generated"]["event_houses"] == [4, 3, 12]
    # all 12 houses visible with lord + occupants (whole-chart rule)
    assert set(board["houses_from_lagna"].keys()) == set(range(1, 13))
    assert board["houses_from_lagna"][4]["event_house"] is True
    # dasha tree: MD/AD from rows, PD/SD computed
    assert board["vimshottari"]["md"]["lord"] == "Saturn"
    assert board["vimshottari"]["ad"]["lord"] == "Venus"
    assert board["vimshottari"]["pd"]["lord"] in dt.SIGN_LORDS.values() or \
        board["vimshottari"]["pd"]["lord"] in ("Rahu", "Ketu")
    assert board["vimshottari"]["sd"] is not None
    # chara rotated to MD sign Taurus
    assert board["chara"]["md_sign"]["sign"] == "Taurus"
    rot = board["chara"]["rotated_houses"]
    assert rot[1]["sign"] == "Taurus"
    # Moon in Pisces = 11th from Taurus
    assert "Moon" in rot[11]["occupants"]
    # karakas placed in rotated chart with dignity
    amk = next(k for k in board["chara"]["karakas"] if k["abbr"] == "AmK")
    assert amk["house_from_md_lagna"] is not None and amk["dignity"]
    # varshphal gate present with per-planet moves
    assert "annual_moves" in board["varshphal"]
    assert isinstance(board["varshphal"]["gate_open"], bool)
    # DT present with verdict
    assert board["double_transit"]["classical_verdict"] in ("fires", "likely", "weak", "none")
    # promise vs trigger mechanical rule stated
    pvt = board["promise_vs_trigger"]
    assert set(pvt) >= {"dasha_promise", "dt_trigger", "varshphal_gate_open", "rule"}
    # JSON-serializable
    import json
    json.dumps(board)


def test_board_md_lord_profile_reads_whole_chart():
    board = build_whole_board(
        _chart(), {}, _dashas(), "1990-02-10", "finance",
        current_date=TODAY,
        dt_positions={"Saturn": 0, "Jupiter": 4, "Mars": 2, "Moon": 6},
    )
    prof = board["vimshottari"]["md"]["profile"]
    # Saturn in Gemini = house 6 from Capricorn; owns 1 (Cap) and 2 (Aqu)
    assert prof["house_from_lagna"] == 6
    assert set(prof["owns_houses"]) == {1, 2}
    assert "dusthana" in prof["house_tags"] or "upachaya" in prof["house_tags"]


def test_concern_alias_covers_detect_concern_vocab():
    for c in ("finance", "funding", "wealth", "career", "marriage", "love",
              "health", "legal", "property", "foreign", "general"):
        assert CONCERN_TO_EVENT[c] in EVENT_MAP


def test_event_map_matches_spec_table():
    assert EVENT_MAP["funding"]["houses"] == [11, 2, 8, 6]
    assert EVENT_MAP["marriage"]["houses"] == [7, 2]
    assert EVENT_MAP["career"]["houses"] == [10, 6, 11]
    assert EVENT_MAP["health"]["houses"] == [1, 6, 8]
    assert EVENT_MAP["litigation"]["houses"] == [6, 8, 12]
    assert EVENT_MAP["relocation"]["houses"] == [4, 3, 12]
