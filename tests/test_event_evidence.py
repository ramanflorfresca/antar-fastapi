"""
tests/test_event_evidence.py — whole-board evidence block + Double Transit.

Phase 1 (founder rulings 2026-06-05): chara/karakas via jaimini_engine ONLY
(pure python — fully testable here); Vimshottari tree via the phase_analyzer
chain, which needs swisseph — on machines without it the block falls back
gracefully (PD/SD None + note) and these tests assert that contract instead.
Ephemeris paths (DT live positions, forming/mars windows, live PD/SD) are
exercised by the live /ask/evidence curl test.

Run: cd ~/antarai && source venv311/bin/activate && python -m pytest tests/test_event_evidence.py -q
"""

from datetime import date

import pytest

from antar_engine import double_transit as dt
from antar_engine.event_evidence import (
    build_whole_board, CONCERN_TO_EVENT, EVENT_MAP,
)

S = dt.SIGN_INDEX  # name → index

try:
    import swisseph  # noqa: F401
    HAVE_EPHEMERIS = True
except ImportError:
    HAVE_EPHEMERIS = False


# ── fixture chart: Capricorn lagna ───────────────────────────────────────────

def _chart():
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
BIRTH = "1990-02-10"
DT_POS = {"Saturn": S["Aries"], "Jupiter": S["Gemini"],
          "Mars": S["Cancer"], "Moon": S["Leo"]}


def _board(concern="property", chart=None, dashas=None):
    return build_whole_board(
        chart or _chart(), {}, dashas if dashas is not None else _dashas(),
        BIRTH, concern, current_date=TODAY, dt_positions=DT_POS,
    )


# ── Double Transit geometry ──────────────────────────────────────────────────

def test_jupiter_aspect_set():
    assert dt.aspected_signs("Jupiter", S["Cancer"]) == {S["Cancer"], S["Scorpio"], S["Capricorn"], S["Pisces"]}


def test_saturn_aspect_set():
    assert dt.aspected_signs("Saturn", S["Pisces"]) == {S["Pisces"], S["Taurus"], S["Virgo"], S["Sagittarius"]}


def test_default_planet_aspects_only_7th():
    assert dt.aspected_signs("Venus", 0) == {0, 6}


def test_double_transit_intersection():
    both = dt.aspected_signs("Jupiter", S["Cancer"]) & dt.aspected_signs("Saturn", S["Pisces"])
    assert both == {S["Pisces"]}


# ── targets: house + lord + lord's navamsa, per frame ───────────────────────

def test_targets_lagna_frame_4th_house():
    targets = dt.build_targets(_chart(), [4], "lagna")
    kinds = {(t["kind"], t["sign"]) for t in targets}
    assert ("house", "Aries") in kinds          # 4th from Capricorn
    assert ("lord_natal", "Libra") in kinds     # Mars sits in Libra


def test_targets_moon_frame_differs():
    kinds = {(t["kind"], t["sign"]) for t in dt.build_targets(_chart(), [4], "moon")}
    assert ("house", "Gemini") in kinds         # 4th from Pisces Moon
    assert ("lord_natal", "Libra") in kinds     # Mercury sits in Libra


def test_targets_include_lord_navamsa_when_d9_given():
    d9 = {"Mars": {"sign": "Leo", "sign_index": 4}}
    targets = dt.build_targets(_chart(), [4], "lagna", d9=d9)
    assert any(t["kind"] == "lord_navamsa" and t["sign"] == "Leo" for t in targets)


# ── verdict rule: moon primary, lagna confirm ────────────────────────────────

def _dt_verdict(positions, houses=(4,)):
    out = dt.dt_state_for_event(_chart(), list(houses), TODAY, positions=positions)
    return out["classical_verdict"], out


def test_verdict_fires_when_both_frames_hit():
    verdict, _ = _dt_verdict({"Saturn": S["Aries"], "Jupiter": S["Gemini"],
                              "Mars": 0, "Moon": 0})
    assert verdict == "fires"


def test_verdict_likely_when_moon_only():
    pos = {"Saturn": S["Gemini"], "Jupiter": S["Aquarius"], "Mars": 0, "Moon": 0}
    both = dt.aspected_signs("Saturn", pos["Saturn"]) & dt.aspected_signs("Jupiter", pos["Jupiter"])
    assert S["Gemini"] in both and S["Aries"] not in both and S["Libra"] not in both
    verdict, _ = _dt_verdict(pos)
    assert verdict == "likely"


def test_verdict_none_when_no_frame_hits():
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


# ── chara block: jaimini_engine ONLY, computed live ──────────────────────────

def test_chara_uses_jaimini_engine_and_matches_it():
    board = _board()
    chara = board["chara"]
    assert chara["source"] == "jaimini_engine live"
    assert chara.get("error") is None or "error" not in chara

    # cross-validate against jaimini_engine directly (same inputs)
    from antar_engine.jaimini_engine import calculate_jaimini_analysis
    ctx = calculate_jaimini_analysis(
        lagna_sign=9, planets_dict=_chart()["planets"],
        d9_planets_dict={}, birth_date_str=BIRTH,
        target_date_str=TODAY.isoformat(),
    )["context"]
    assert chara["md_sign"]["sign"] == ctx.current_md.sign_name
    if ctx.current_ad:
        assert chara["ad_sign"]["sign"] == ctx.current_ad.sign_name


def test_karakas_seven_scheme_degree_in_sign():
    ks = _board()["chara"]["karakas"]
    assert len(ks) == 7
    abbrs = [k["abbr"] for k in ks]
    assert abbrs[0] == "AK" and "AmK" in abbrs and "DK" in abbrs
    # Mars 28° is the highest degree-in-sign → AK
    assert ks[0]["planet"] == "Mars"
    # placed in the MD-rotated chart with dignity + tags
    for k in ks:
        assert 1 <= k["house_from_md_lagna"] <= 12
        assert k["dignity"] in ("exalted", "own", "debilitated", "neutral")


def test_chara_rotation_and_db_crosscheck():
    chara = _board()["chara"]
    rot = chara["rotated_houses"]
    assert set(rot.keys()) == set(range(1, 13))
    md_sign = chara["md_sign"]["sign"]
    assert rot[1]["sign"] == md_sign
    # occupants preserved across the rotation (whole-chart rule)
    all_occ = [p for h in rot.values() for p in h["occupants"]]
    assert sorted(all_occ) == sorted(_chart()["planets"].keys())
    # DB cross-check fact present (fixture has a jaimini MD row)
    assert chara["db_md_row_sign"] == "Taurus"
    assert isinstance(chara["db_md_agrees"], bool)


def test_chara_never_reads_jsonb_snapshot():
    # poisoned snapshot: if the block read jaimini_data.current_md it would
    # report this absurd sign — staleness rule says it must not.
    poisoned = {"current_md": {"sign_name": "POISON", "sign": 0},
                "current_ad": {"sign_name": "POISON", "sign": 0}}
    board = build_whole_board(_chart(), poisoned, _dashas(), BIRTH, "property",
                              current_date=TODAY, dt_positions=DT_POS)
    assert board["chara"]["md_sign"]["sign"] != "POISON"


def test_moving_lagna_and_supporting_structures_present():
    chara = _board()["chara"]
    assert isinstance(chara["moving_lagna"], dict) and chara["moving_lagna"]
    assert chara["arudha_lagna"]["sign"] in dt.SIGNS
    assert chara["upapada_lagna"]["sign"] in dt.SIGNS
    assert chara["karakamsa"]["sign"] in dt.SIGNS


# ── vimshottari block: phase_analyzer chain with graceful fallback ──────────

def test_vim_md_ad_present_with_profiles():
    vim = _board()["vimshottari"]
    assert vim["md"]["lord"] == "Saturn"
    assert vim["ad"]["lord"] == "Venus"
    prof = vim["md"]["profile"]
    assert prof["house_from_lagna"] == 6          # Saturn in Gemini from Cap
    assert set(prof["owns_houses"]) == {1, 2}


def test_vim_pd_sd_or_note():
    board = _board()
    vim = board["vimshottari"]
    if HAVE_EPHEMERIS:
        assert vim["pd"] is not None and vim["sd"] is not None
        assert vim["pd"]["lord"] in ("Sun", "Moon", "Mars", "Mercury",
                                     "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
    else:
        # graceful contract: PD/SD None + auditable note
        assert vim["pd"] is None
        assert any("PD/SD unavailable" in n for n in board["notes"])


# ── whole board ──────────────────────────────────────────────────────────────

def test_board_assembles_and_serializes():
    board = _board()
    assert board["generated"]["event"] == "relocation"
    assert board["generated"]["event_houses"] == [4, 3, 12]
    assert set(board["houses_from_lagna"].keys()) == set(range(1, 13))
    assert board["houses_from_lagna"][4]["event_house"] is True
    assert board["double_transit"]["classical_verdict"] in ("fires", "likely", "weak", "none")
    pvt = board["promise_vs_trigger"]
    assert set(pvt) >= {"dasha_promise", "dt_trigger", "varshphal_gate_open", "rule"}
    assert "annual_moves" in board["varshphal"]
    import json
    json.dumps(board)


def test_scope_notes_recorded():
    notes = " | ".join(_board(concern="health")["notes"])
    assert "D30" in notes                 # simplified Trimshamsha flagged
    assert "lower-confidence" in notes    # health flagged
    assert "MEAN_NODE" in notes           # node discrepancy on record


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


# ── yoga key-casing fix (swept into Phase 1) ─────────────────────────────────

def test_yoga_detector_receives_both_key_cases():
    from antar_engine.yoga_engine import detect_yogas_for_question, DOMAIN_DETECTORS
    seen = {}

    def spy(chart_data, d_charts):
        seen["keys"] = set(d_charts.keys())
        return []

    DOMAIN_DETECTORS["_spy_"] = spy
    try:
        detect_yogas_for_question("_spy_", _chart(), {"d2": {"x": 1}, "d9": {}})
    finally:
        del DOMAIN_DETECTORS["_spy_"]
    assert {"d2", "D2", "d9", "D9"} <= seen["keys"]
