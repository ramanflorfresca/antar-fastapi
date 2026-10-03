"""Career clarify listens (live 2026-10-03: Harleen, between jobs, was asked what she does)."""
from dotenv import load_dotenv
load_dotenv()
import main


def test_between_jobs_is_a_known_situation_so_no_clarify():
    row = {"career_stage": "between_jobs", "profession": None, "life_work": None}
    q = "What type of work is best suited for me?"
    assert main._ask_known_current_role(row, q, []) == "between jobs, looking for the next role"
    assert not main._ask_needs_career_clarify(q, row, [])


def test_unknown_work_still_asks():
    row = {"career_stage": None, "profession": None, "life_work": None}
    assert main._ask_needs_career_clarify("What type of work is best suited for me?", row, [])


def test_clarify_text_never_says_chart():
    for lang in ("en", "es", "pt"):
        r = main._ask_career_clarify_payload(lang)["read"].lower()
        assert "chart" not in r and "carta" not in r, lang



def test_between_jobs_answers_drop_boss_and_promotion():
    from antar_engine import understand as u
    assert u.guard_answer("Your boss and colleagues will notice.", "q", None, unemployed=True) == \
        "People will notice."
    assert "Never invent their past" in u.guardrails_block()
    t = ("Think analyst, advisor, or specialist your boss and colleagues come to for answers. "
         "A promotion is not the goal now. Pick one area you know best.")
    out = u.guard_answer(t, "What work suits me?", None, unemployed=True)
    assert "boss" not in out and "colleagues" not in out and "promotion" not in out
    assert "specialist people come to" in out and "Pick one area" in out
    assert u.guard_answer(t, "q", None, unemployed=False) == t
    assert u.not_employed(None, "between_jobs") and not u.not_employed(None, "entrepreneur")



def test_laid_off_only_if_they_said_so():
    from antar_engine import understand as u
    t = "Harleen, being laid off is a hard stop — but it lifts."
    assert u.guard_answer(t, "What work suits me?", None, unemployed=True) == \
        "Harleen, being between jobs is a hard stop — but it lifts."
    assert u.guard_answer(t, "I was laid off, what work suits me?", None, unemployed=True) == t
