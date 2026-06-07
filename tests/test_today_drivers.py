"""
tests/test_today_drivers.py — Fix #1: Today narration de-collapse.

summarize_drivers turns the engine's _debug_reasoning votes into jargon-free
per-domain driver conclusions for the narrator. Pure function — no ephemeris.
"""

from antar_engine.today_narration import (
    summarize_drivers, build_narration_system, _JARGON_RX,
)


def _debug():
    # shape produced by today_highlight.select_today_highlight()._debug_reasoning
    return {
        "votes": [
            "C:lk_amplify:money:+3.5",
            "C:lk_avoid:body:-3.5",
            "A:moon_house9:work:+3.2",
            "B:patra:money:+1.0",
        ],
        "net": {"money": 4.5, "work": 3.2, "body": -3.5,
                "relationships": 0.0, "mind": 0.0},
        "chosen": ["money", "work"],
    }


def test_drivers_built_for_chosen_only():
    out = summarize_drivers(_debug())
    domains = {d["domain"] for d in out}
    assert domains == {"money", "work"}          # body not chosen → excluded


def test_money_carries_chart_and_personal_reasons():
    out = {d["domain"]: d for d in summarize_drivers(_debug())}
    money = out["money"]
    assert money["signal"] == "amplified"
    # chart-specific reason ranks before personal-context reason
    assert money["reasons"][0] == "this area is specifically lit for you today"
    assert any("focused on right now" in r for r in money["reasons"])


def test_work_attention_reason():
    out = {d["domain"]: d for d in summarize_drivers(_debug())}
    assert out["work"]["reasons"] == [
        "this is where your attention naturally lands today"
    ]


def test_caution_signal_from_negative_net():
    dbg = _debug()
    dbg["chosen"] = ["body"]
    out = summarize_drivers(dbg)
    assert out[0]["domain"] == "body" and out[0]["signal"] == "caution"


def test_explicit_chosen_overrides_debug_chosen():
    out = summarize_drivers(_debug(), chosen=["work"])
    assert [d["domain"] for d in out] == ["work"]


def test_empty_or_malformed_debug_returns_empty():
    assert summarize_drivers(None) == []
    assert summarize_drivers({}) == []
    assert summarize_drivers({"chosen": []}) == []


def test_driver_reasons_are_jargon_free():
    for d in summarize_drivers(_debug()):
        for r in d["reasons"]:
            assert not _JARGON_RX.search(r), f"jargon leaked: {r}"


def test_drivers_reach_the_narration_payload():
    drivers = summarize_drivers(_debug())
    sys_prompt = build_narration_system(
        engine={"highlight_domains": ["money", "work"], "direction": "positive",
                "strength": "high", "todays_move": {}},
        nudge="send the invoice", first_name="Raman",
        lk_daily={}, date_str="2026-06-07", drivers=drivers,
    )
    assert '"drivers"' in sys_prompt
    assert "this area is specifically lit for you today" in sys_prompt
    # the grounding rule is present in the static instruction
    assert "GROUND every line in the \"drivers\" list" in sys_prompt
