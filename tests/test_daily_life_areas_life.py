"""[ui-audit 2026-10-11] The Work lines must not assume a job for a reader who said they have none."""
from antar_engine.daily_life_areas import build_day_map

ACTIVE = [{"key": "work", "polarity": "opportunity", "tone": 0.9},
          {"key": "authority", "polarity": "opportunity", "tone": 0.6}]


def _lines(life):
    rows = build_day_map(ACTIVE, [], life)
    return {r["key"]: r["line"] for r in rows}


def test_default_and_employed_keep_the_job_wording():
    for life in (None, {}, {"career_stage": "job"}, {"career_stage": "running_business"}):
        assert "being noticed" in _lines(life)["work"], life


def test_jobless_reader_gets_job_search_wording():
    lines = _lines({"career_stage": "in_transition"})
    assert "roles and projects" in lines["work"]
    assert "being noticed" not in lines["work"] and "people above you" not in lines.get("authority", "")


def test_student_reader_gets_study_wording():
    lines = _lines({"career_stage": "studying"})
    assert "studies" in lines["work"]
    assert "being noticed" not in lines["work"]


def test_constraint_block_forbids_job_claims_for_jobless_reader():
    from antar_engine.life_context import life_constraint_block, resolve_life_facts
    life = resolve_life_facts({"life_work": "transition", "life_relationship": "single"})
    assert life["career_stage"] == "in_transition"
    block = life_constraint_block(life)
    assert "WITHOUT a job" in block and "NOT currently partnered" in block
    employed = life_constraint_block(resolve_life_facts({"life_work": "job"}))
    assert "WITHOUT a job" not in employed
