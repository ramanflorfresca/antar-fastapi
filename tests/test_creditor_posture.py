"""Creditor posture: user vs the other side of a debt dispute (the 6th is THEM here)."""
import re
from pathlib import Path

import main
from antar_engine import debt as dbt, legal
from tests.test_immigration_debt import _chart

# Aries lagna: lagna lord Mars, 6th lord Mercury, 11th lord Saturn.
STRONG_USER = _chart("Aries", {"Mars": ("Capricorn", 10), "Jupiter": ("Aries", 1), "Moon": ("Cancer", 4),
                               "Mercury": ("Pisces", 12), "Saturn": ("Aquarius", 11), "Venus": ("Taurus", 2),
                               "Sun": ("Leo", 5), "Rahu": ("Gemini", 3), "Ketu": ("Sagittarius", 9)})
STRONG_CRED = _chart("Aries", {"Mars": ("Cancer", 4), "Mercury": ("Virgo", 6), "Saturn": ("Scorpio", 8),
                               "Jupiter": ("Taurus", 2), "Moon": ("Scorpio", 8), "Venus": ("Libra", 7),
                               "Sun": ("Leo", 5), "Rahu": ("Virgo", 6), "Ketu": ("Pisces", 12)})


def test_creditor_detector():
    for q in ("what should i expect for my case with my creditor?", "The debt collector keeps calling",
              "My lender wants to settle", "¿Qué hará mi acreedor?", "O credor vai me cobrar?"):
        assert dbt.is_creditor_q(q), q
    for q in ("Will I win my lawsuit?", "when will i pay off my debt?", "How is my love life?"):
        assert not dbt.is_creditor_q(q), q


def test_postures_follow_the_two_sides():
    u, c = dbt.analyze_creditor(STRONG_USER), dbt.analyze_creditor(STRONG_CRED)
    assert u["available"] and c["available"]
    assert u["user_score"] > c["user_score"] and c["creditor_score"] > u["creditor_score"]
    assert u["posture"] == "user_ahead" and c["posture"] == "creditor_ahead"
    assert dbt.analyze_creditor({})["available"] is False


def test_posture_phrases_are_postures_not_outcomes():
    for lang in ("en", "es", "pt"):
        for p in ("user_ahead", "creditor_ahead", "evenly_matched", "both_quiet"):
            t = dbt.creditor_posture_phrase(p, lang)
            assert t and t.endswith(".")
            assert not re.search(r"you will win|you will lose|ganar[aá]s|perder[aá]s|vai ganhar|vai perder", t, re.I)
    assert dbt.creditor_posture_phrase("nope", "en") == ""
    assert "settling or restructuring early" in dbt.creditor_posture_phrase("creditor_ahead", "en")


def test_verdicts_take_the_posture_as_base_line():
    p = dbt.creditor_posture_phrase("creditor_ahead", "en")
    assert legal.legal_verdict("favourable", True, 2028, "en", lead_override=p)["line"].startswith(p)
    assert "leans in your favour" not in legal.legal_verdict("favourable", True, 2028, "en", lead_override=p)["line"]
    assert dbt.debt_verdict("recoverable", 2028, None, "en", lead_override=p)["line"].startswith(p)
    assert "leans in your favour" in legal.legal_verdict("favourable", False, 2028, "en")["line"]   # unchanged


def test_main_creditor_lead_only_for_creditor_matters():
    assert main._creditor_lead(STRONG_CRED, "my case with my creditor", "en")
    assert main._creditor_lead(STRONG_CRED, "Will I win my lawsuit?", "en") == ""
    assert main._creditor_lead({}, "my creditor", "en") == ""


def test_wired_into_main():
    src = (Path(__file__).resolve().parent.parent / "main.py").read_text()
    for needle in ("lead_override=_creditor_lead(", "creditor posture lead", "CREDITOR MATTER",
                   "or _is_creditor_q(question)"):
        assert needle in src, needle
