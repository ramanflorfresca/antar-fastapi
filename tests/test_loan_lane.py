"""Loan-approval lane: detector boundaries, access lean, honest verdicts, wiring."""
import re
from pathlib import Path

import main
from antar_engine import loan
from tests.test_immigration_debt import _chart

# Aries lagna: 2nd lord Venus, 11th lord Saturn, 6th Mercury, 8th Mars, 12th Jupiter.
OPEN = _chart("Aries", {"Saturn": ("Libra", 7), "Jupiter": ("Aquarius", 11), "Venus": ("Taurus", 2),
                        "Mercury": ("Aries", 1), "Mars": ("Virgo", 6), "Rahu": ("Cancer", 4),
                        "Sun": ("Aries", 1), "Moon": ("Taurus", 2), "Ketu": ("Capricorn", 10)})
TIGHT = _chart("Aries", {"Venus": ("Virgo", 6), "Saturn": ("Scorpio", 8), "Jupiter": ("Pisces", 12),
                         "Mercury": ("Scorpio", 8), "Mars": ("Pisces", 12), "Rahu": ("Taurus", 2),
                         "Sun": ("Libra", 7), "Moon": ("Pisces", 12), "Ketu": ("Scorpio", 8)})


def test_loan_detector_boundaries():
    for q in ("Will I get approved for a mortgage?", "Can I get a loan this year?", "when will my loan be approved",
              "I want to borrow money for a car", "¿Me aprueben el préstamo?", "¿Puedo conseguir un préstamo?",
              "Vou conseguir um empréstimo?"):
        assert main._is_loan_q(q), q
    for q in ("when will i pay off my debt?", "will i be able to loan off?",          # payoff = debt lane
              "Is this a good time to get a bank loan for my business?",             # business funding path
              "Should I raise money from investors for my startup?", "How is my love life?", "Will I win my lawsuit?"):
        assert not main._is_loan_q(q), q


def test_access_levels_and_phase():
    o, t = loan.analyze_loan(OPEN), loan.analyze_loan(TIGHT)
    assert o["available"] and t["available"]
    assert o["access"]["score"] > t["access"]["score"]
    assert o["access"]["level"] == "open" and t["access"]["level"] == "tight"
    assert loan.analyze_loan({})["available"] is False
    # Aries: 2nd/11th lords Venus/Saturn + Jupiter/Venus are supportive; 6th/8th/12th lords Mercury/Mars strain
    assert loan.loan_phase(o, "Venus-Jupiter") == "supportive"
    assert loan.loan_phase(o, "Mercury-Mars") == "strained"
    assert loan.loan_phase(o, "Sun-Moon") == "mixed" and loan.loan_phase(None, "") == "mixed"


def test_verdict_and_lead_never_promise_approval():
    for lang in ("en", "es", "pt"):
        for level in ("open", "conditional", "tight"):
            v = loan.loan_verdict(level, "supportive", 2028, lang, caution="")
            assert v["available"] and v["band"] in ("MIXED", "WEAK") and v["secondary_note"]
            assert not re.search(r"will be approved|ser[aá] aprobad|ser[aá] aprovad|guarantee|garant", v["line"], re.I)
            lead = loan.loan_lead_phrase(level, lang)
            assert lead and lead.endswith(".") and not re.match(r"(?i)\s*(yes|likely|no|s[ií]|sim)\b", lead)
    assert loan.loan_verdict("tight", "mixed", None)["band"] == "WEAK"
    assert "no single window" in loan.loan_verdict("open", "mixed", None)["the_move"]
    assert "better for preparing" in loan.loan_verdict("open", "strained", 2028)["line"]


def test_timing_never_raises_without_dashas():
    assert loan.loan_timing(OPEN, {})["available"] in (True, False)


def test_wired_into_main():
    src = (Path(__file__).resolve().parent.parent / "main.py").read_text()
    for needle in ("_is_loan_q(request.question)", "_ask_loan_block", "_ask_loan_lead",
                   "or _is_debt_q(question) or _is_loan_q(question)"):
        assert needle in src, needle
    assert src.count('{_ask_loan_block}') == 2
