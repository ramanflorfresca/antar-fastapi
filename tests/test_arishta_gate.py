"""Fear-or-reality gate, debt severity tier, immigration status-risk caution."""
import re
from pathlib import Path

from antar_engine import arishta_gate as ag, debt as dbt, immigration as imm, legal
from tests.test_immigration_debt import WEAK, STRONG, _chart

# Aries lagna: 6th lord Mercury, 8th lord Mars, 12th lord Jupiter.
HEAVY_DEBT = _chart("Aries", {"Venus": ("Virgo", 6), "Saturn": ("Aries", 1), "Jupiter": ("Taurus", 2),
                              "Mercury": ("Scorpio", 8), "Mars": ("Pisces", 12), "Rahu": ("Taurus", 2),
                              "Sun": ("Libra", 7), "Moon": ("Pisces", 12), "Ketu": ("Scorpio", 8)})


def test_gate_levels():
    assert ag.gate_level(WEAK, "Venus-Sun") == "none"          # 2nd/7th and 5th lords, none in 6/8/12
    assert ag.gate_level(WEAK, "Mercury-Venus") == "one"       # Mercury = 6th lord
    st = ag.dasha_stack(WEAK, "Mercury-Mars")                  # 6th lord + 8th lord
    assert st["level"] == "stack" and {6, 8} <= set(st["houses_hit"])
    assert ag.gate_level(WEAK, "") == "unknown" and ag.gate_level({}, "Mars-Sun") == "unknown"


def test_gate_note_only_for_known_none():
    for lang in ("en", "es", "pt"):
        for topic in ("debt", "legal"):
            assert ag.gate_note("none", topic, lang)
            assert not ag.gate_note("one", topic, lang) and not ag.gate_note("unknown", topic, lang)
    assert "worry" in ag.gate_note("none", "debt", "en")


def test_legal_and_debt_verdicts_carry_the_gate():
    assert "worry" in legal.legal_verdict("contested", False, 2028, "en", gate="none")["line"]
    assert "worry" not in legal.legal_verdict("contested", False, 2028, "en", gate="stack")["line"]
    assert "worry" in dbt.debt_verdict("contested", 2028, None, "en", gate="none")["line"]
    assert "worry" not in dbt.debt_verdict("contested", 2028, None, "en")["line"]


def test_debt_severity_tier():
    a = dbt.analyze_debt(HEAVY_DEBT)
    assert dbt.debt_severity(HEAVY_DEBT, "Mercury-Mars", a) is True      # 6th + 8th lords stacked
    assert dbt.debt_severity(HEAVY_DEBT, "Venus-Sun", a) is False        # nothing stacked
    assert dbt.debt_severity(HEAVY_DEBT, "Mercury-Sun", a) is False      # only one lord connected
    assert dbt.debt_severity({}, "Mercury-Mars", {}) is False
    for lang in ("en", "es", "pt"):
        v = dbt.debt_verdict("contested", 2028, 2027, lang, severe=True)
        assert v["band"] == "WEAK" and v["secondary_note"]
        # never a bankruptcy prediction, never shaming
        assert not re.search(r"bankrupt|quiebra|bancarrota|fal[eê]ncia", v["line"] + v["the_move"], re.I)
    assert "not a verdict on you" in dbt.debt_verdict("contested", None, None, "en", severe=True)["line"]


def test_gate_none_never_overrides_severity():
    v = dbt.debt_verdict("heavy", 2028, None, "en", gate="none", severe=True)
    assert "worry" not in v["line"] and v["band"] == "WEAK"


def test_immigration_status_risk():
    a = imm.analyze_immigration(WEAK)
    assert a["status_risk_natal"] is False
    assert imm.immigration_status_risk(WEAK, "Venus-Mercury", a) is True     # AD = 6th lord
    assert imm.immigration_status_risk(WEAK, "Venus-Sun", a) is False
    assert imm.immigration_status_risk(WEAK, "Venus-Jupiter", a) is False    # supportive lord
    # natal: 9th lord sent into the 6th
    bad9 = _chart("Aries", {"Jupiter": ("Virgo", 6), "Moon": ("Cancer", 4), "Saturn": ("Aquarius", 11),
                            "Rahu": ("Gemini", 3), "Mars": ("Aries", 1), "Sun": ("Leo", 5),
                            "Mercury": ("Virgo", 6), "Venus": ("Taurus", 2), "Ketu": ("Sagittarius", 9)})
    assert imm.analyze_immigration(bad9)["status_risk_natal"] is True
    assert imm.immigration_status_risk(STRONG, "Venus-Sun", imm.analyze_immigration(STRONG)) in (True, False)


def test_status_caution_text_is_a_caution_not_a_forecast():
    for lang in ("en", "es", "pt"):
        v = imm.immigration_verdict("some", "mixed", False, 2028, lang, status_risk=True)
        assert v["band"] in ("MIXED", "WEAK")
        assert not re.search(r"deport|detenci|detenç|expuls|will be (denied|removed)", v["line"], re.I)
    assert "spotless" in imm.immigration_verdict("some", "mixed", False, 2028, "en", status_risk=True)["line"]
    assert "spotless" not in imm.immigration_verdict("some", "mixed", False, 2028, "en")["line"]


def test_wired_into_main():
    src = (Path(__file__).resolve().parent.parent / "main.py").read_text()
    for needle in ("gate=_gl_fn(", "severe=_dsev_fn(", "status_risk=_isr_fn(",
                   "STATUS CAUTION", "SEVERITY: several pressure points"):
        assert needle in src, needle
