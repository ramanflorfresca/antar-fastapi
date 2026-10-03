"""Speculation & gambling answered like an astrologer (owner 2026-10-03)."""
from antar_engine import speculation_policy as sp


def test_states():
    assert sp.state({"score": 20, "gain_indicators": [], "risk_indicators": ["5th lord in 8"]}) == "losses"
    assert sp.state({"score": 30, "gain_indicators": [], "risk_indicators": []}) == "no"
    assert sp.state({"score": 70, "gain_indicators": ["a", "b"], "risk_indicators": []}, "SUPPORTED") == "open"
    assert sp.state({"score": 70, "gain_indicators": ["a", "b"], "risk_indicators": []}, "NOT_YET") == "later"
    assert sp.state({"score": 70, "gain_indicators": ["a"], "risk_indicators": []}, "SUPPORTED", "denied") == "no"


def test_gambling_gets_the_window_and_no_game_specific_answer():
    r = sp.lead("later", "Jun 2027 – Oct 2027", gambling=True)
    assert "but not yet" in r["read"] and "Jun 2027 – Oct 2027" in r["read"]
    assert "doesn't give casino, lottery or betting-specific answers" in r["read"]
    r = sp.lead("open", "Nov 2026 – Jan 2027", gambling=False, language="es")
    assert "abierta ahora — hasta Nov 2026 – Jan 2027" in r["read"]


def test_no_is_said_straight_and_replaces_a_contradicting_body():
    out = sp.merge("Your speculative potential is genuinely well-supported right now.",
                   sp.lead("losses")["read"], "losses")
    assert out.startswith("Your reading doesn't support speculation") and "well-supported" not in out


def test_policy_lines_are_the_whole_answer():
    assert sp.merge("Not yet — x. Ahora es un buen momento para probar suerte.", "LEAD.", "later") == "LEAD."


def test_natal_window_fallback():
    assert sp.natal_window({"best_periods": ["Current Jupiter AD — active speculation period"]}) == ("SUPPORTED", "")
    assert sp.natal_window({"best_periods": ["Venus AD 2027 — upcoming favorable period"]}) == ("NOT_YET", "2027")
    assert sp.natal_window({}) == ("", "")


def test_gambling_vs_plain_speculation():
    assert sp.is_gambling("Will I win at the casino tonight?") and sp.is_gambling("¿Ganaré la lotería?")
    assert sp.is_gambling("kya satta mein jeetunga")
    assert not sp.is_gambling("Will I win in speculation?") and not sp.is_gambling("When will I gain from stocks?")





def test_kp_combination():
    assert sp.combine("later", {"verdict": "no", "favour": [], "against": [8, 12]}) == "losses"
    assert sp.combine("open", {"verdict": "no", "favour": [], "against": [12]}) == "losses"
    assert sp.combine("no", {"verdict": "yes", "favour": [5, 11], "against": []}, "SUPPORTED") == "open"
    assert sp.combine("no", {"verdict": "yes", "favour": [5, 11], "against": []}, "NOT_YET") == "later"
    assert sp.combine("later", {"verdict": "conditional", "favour": [11], "against": [8]}) == "later"
    assert sp.combine("losses", {"verdict": "yes", "favour": [5], "against": []}) == "losses"
    assert sp.combine("later", None) == "later"
