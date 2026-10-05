"""Voice gate keeps a real answer over one banned word (live 2026-10-03: an
empathetic 'I am unemployed… how do I get over this hurdle?' answer was thrown
away for 'chart' and replaced by 'The timing genuinely supports your work')."""
from dotenv import load_dotenv
load_dotenv()
import main
from antar_engine.narration_validator import validate_narration


def test_soft_repair_removes_chart_word_and_passes_the_gate():
    t = ("Harleen, I hear that you're stuck. Your chart shows caution and self-doubt braking hard. "
         "In your chart, motion itself breaks the freeze.")
    fixed = main._ask_soft_repair(t)
    assert "chart" not in fixed.lower()
    assert "Your timing shows caution" in fixed and "In your timing, motion" in fixed
    assert not [v for v in validate_narration(fixed, language="en") if "chart" in str(v)]


def test_keep_clean_sentences_drops_only_the_bad_one():
    bad = lambda t: ["x"] if "Saturn" in t else []
    t = ("I hear that you're stuck. Saturn is braking you hard. Start with one small, concrete "
         "thing this week. Motion itself breaks the freeze.")
    out = main._ask_keep_clean_sentences(t, bad)
    assert "Saturn" not in out and out.startswith("I hear that you're stuck.") and "Motion itself" in out


def test_keep_clean_sentences_gives_up_when_too_little_survives():
    bad = lambda t: ["x"] if "Saturn" in t or "Mars" in t else []
    assert main._ask_keep_clean_sentences("Saturn blocks you. Mars too. Fine.", bad) == ""


def test_career_practice_no_longer_assumes_a_hard_conversation():
    assert "hard conversation" not in main._ASK_PRACTICE_STEP["en"]["career"]


def test_next_step_cut_mid_question_is_trimmed_to_the_complete_part():
    t = ("Schedule one informational call this week with someone working in finance or law "
         "— ask how they got.")
    assert main._ask_repair_next(t) == ("Schedule one informational call this week with someone "
                                        "working in finance or law.")
    ok = "Message one former colleague and ask how they got started."
    assert main._ask_repair_next(ok) == ok


def test_placement_jargon_is_repaired_and_banned():
    from antar_engine.narration_validator import validate_narration
    t = "The reading also shows a straining placement that makes lenders harder to move right now."
    fixed = main._ask_soft_repair(t)
    assert "placement" not in fixed and "a strain in your timing" in fixed
    assert any("astro_technical" in str(v) for v in validate_narration("Mars is retrograde in a placement", language="en"))


def test_comparison_gets_fit_fields():
    from antar_engine import understand as u
    import json
    r = u.parse("x " + json.dumps({"intent": "which", "area": "career_job", "options": ["technology", "brokerage"],
                                    "confidence": 0.9}))
    b = u.comparison_block(r, "", fit_fields=["technology", "networks", "media"], profession="startup founder")
    assert "strongest fields for them: technology, networks, media" in b and "startup founder" in b
