"""Immigration + debt engines: detectors, structure/lean reads, honest verdicts, wiring."""
import re
from pathlib import Path

from antar_engine import immigration as imm, debt as dbt


def _chart(lagna, planets):
    return {"lagna": {"sign": lagna},
            "planets": {p: {"sign": s, "house": h} for p, (s, h) in planets.items()}}


# Aries lagna: 4th lord Moon, 9th/12th lord Jupiter, 6th Mercury, 8th Mars.
STRONG = _chart("Aries", {"Moon": ("Pisces", 12), "Rahu": ("Pisces", 12), "Jupiter": ("Pisces", 12),
                          "Saturn": ("Sagittarius", 9), "Mars": ("Leo", 5), "Sun": ("Aries", 1),
                          "Mercury": ("Taurus", 2), "Venus": ("Gemini", 3), "Ketu": ("Virgo", 6)})
WEAK = _chart("Aries", {"Moon": ("Cancer", 4), "Jupiter": ("Cancer", 4), "Rahu": ("Gemini", 3),
                        "Saturn": ("Aquarius", 11), "Mars": ("Aries", 1), "Sun": ("Leo", 5),
                        "Mercury": ("Virgo", 6), "Venus": ("Taurus", 2), "Ketu": ("Sagittarius", 9)})
# Virgo lagna: 4th lord Jupiter in Leo = house 12 (a FIXED sign) -> settled pattern.
FIXED12 = _chart("Virgo", {"Jupiter": ("Leo", 12), "Moon": ("Virgo", 1), "Rahu": ("Leo", 12),
                           "Saturn": ("Libra", 2), "Mars": ("Aries", 8), "Sun": ("Cancer", 11),
                           "Mercury": ("Virgo", 1), "Venus": ("Leo", 12), "Ketu": ("Aquarius", 6)})


# ── immigration ──────────────────────────────────────────────────────────────
def test_immigration_detector():
    for q in ("Will my H-1B get approved?", "when will my green card come", "my visa keeps getting delayed",
              "¿Cuándo sale mi visa de residencia permanente?", "Quando sai meu visto?",
              "Should I settle abroad in canada", "my USCIS case is stuck", "EB-2 priority date"):
        assert imm.is_immigration_q(q), q
    for q in ("Should I pay my visa card bill?", "I want to visit my aunt in Delhi", "will it opt in",
              "How is my love life?", "", None):
        assert not imm.is_immigration_q(q), q


def test_structure_levels():
    assert imm.analyze_immigration(STRONG)["structure"]["level"] == "strong"
    assert imm.analyze_immigration(WEAK)["structure"]["level"] == "weak"
    assert imm.analyze_immigration({})["available"] is False


def test_settled_pattern_and_delay():
    a = imm.analyze_immigration(FIXED12)
    assert a["structure"]["nature"] == "settled"
    assert imm.analyze_immigration(STRONG)["delay"] is True      # Saturn in the 9th
    assert imm.analyze_immigration(WEAK)["delay"] is False


def test_phase_tone():
    # Aries: 9th/12th lord = Jupiter -> supportive; 6th lord Mercury / 8th lord Mars -> slow
    assert imm.immigration_phase(WEAK, "Jupiter-Jupiter") == "releasing"
    assert imm.immigration_phase(WEAK, "Mercury-Mars") == "slow"
    assert imm.immigration_phase(WEAK, "Venus-Sun") == "mixed"


def test_immigration_verdict_is_honest_in_all_languages():
    for lang in ("en", "es", "pt"):
        for level, phase in (("weak", "mixed"), ("strong", "slow"), ("strong", "releasing"), ("some", "mixed")):
            v = imm.immigration_verdict(level, phase, True, 2028, lang)
            assert v["available"] and v["band"] in ("MIXED", "WEAK")        # never FAVORABLE
            assert v["secondary_note"] and "2028" in v["window_range"]
            assert not re.search(r"\b(will be approved|you will get|guaranteed|garantizad|garantid)", v["line"], re.I)
    assert imm.immigration_verdict("weak", "mixed", False, None)["band"] == "WEAK"
    assert "delay, not a denial" in imm.immigration_verdict("strong", "slow", False, 2028)["line"]


def test_immigration_timing_never_raises_without_dashas():
    assert imm.immigration_timing(STRONG, {})["available"] in (True, False)


# ── debt ─────────────────────────────────────────────────────────────────────
def test_debt_detector():
    for q in ("Will I ever get out of debt?", "I owe my brother money", "creditors keep calling",
              "should I file for bankruptcy", "¿Cuándo salgo de mis deudas?", "Quando saio das dívidas?",
              "mera karz kab utrega", "can't pay my credit card balance"):
        assert dbt.is_debt_q(q), q
    for q in ("How is my power in the office?", "however it goes", "Should I raise funding for my startup?",
              "Is this a good time to get a bank loan for my business?", "How is my love life?", ""):
        assert not dbt.is_debt_q(q), q


def test_debt_lean_and_levels():
    # Aries: 2nd lord Venus, 6th Mercury, 11th Saturn, 12th Jupiter.
    heavy = _chart("Aries", {"Venus": ("Virgo", 6), "Saturn": ("Aries", 1), "Jupiter": ("Taurus", 2),
                             "Mercury": ("Scorpio", 8), "Mars": ("Pisces", 12), "Rahu": ("Taurus", 2),
                             "Sun": ("Libra", 7), "Moon": ("Pisces", 12), "Ketu": ("Scorpio", 8)})
    easy = _chart("Aries", {"Saturn": ("Libra", 7), "Jupiter": ("Aquarius", 11), "Venus": ("Taurus", 2),
                            "Mercury": ("Aries", 1), "Mars": ("Virgo", 6), "Rahu": ("Cancer", 4),
                            "Sun": ("Aries", 1), "Moon": ("Taurus", 2), "Ketu": ("Capricorn", 10)})
    h, e = dbt.analyze_debt(heavy), dbt.analyze_debt(easy)
    assert h["available"] and e["available"]
    assert h["pressure"]["score"] > e["pressure"]["score"]
    assert e["recovery"]["score"] > h["recovery"]["score"]
    assert h["lean"] in ("heavy", "contested") and e["lean"] == "recoverable"
    assert dbt.analyze_debt({})["available"] is False


def test_debt_verdict_is_honest_in_all_languages():
    for lang in ("en", "es", "pt"):
        for lean in ("recoverable", "contested", "heavy"):
            v = dbt.debt_verdict(lean, 2028, 2027, lang)
            assert v["available"] and v["band"] in ("MIXED", "WEAK") and v["secondary_note"]
            assert not re.search(r"debt-free by|libre de deudas en|livre das dívidas em", v["line"] + v["the_move"], re.I)
    assert dbt.debt_verdict("heavy", None)["band"] == "WEAK"
    assert "no single relief window" in dbt.debt_verdict("contested", None)["the_move"]


# ── wiring ───────────────────────────────────────────────────────────────────
def test_wired_into_main():
    src = (Path(__file__).resolve().parent.parent / "main.py").read_text()
    for needle in ("_is_immigration_q(request.question)", "_immigration_override",
                   "_is_debt_q(request.question)", "_ask_immigration_block", "_ask_debt_block"):
        assert needle in src, needle
    # the injected blocks reach BOTH narrator prompts, next to the legal block
    assert src.count('{_ask_immigration_block}') == 2 and src.count('{_ask_debt_block}') == 2
