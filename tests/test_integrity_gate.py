"""Integrity gate — the last check on an Ask answer (2026-10-02).

Seeded with the real broken answers from the first WhatsApp sessions.
"""
import asyncio
import json

from antar_engine.integrity_gate import fragment_issues, run_gate, tidy, unsupported_dates

GROUND = ("KP ranked days: 2026-10-05 best, 2026-10-03 worst. "
          "Career window Nov 2026 – Jan 2027. Intraday close 22:47.")


def test_live_broken_answers_are_detected():
    assert fragment_issues(", Oct 5 is your least-strained day.")
    assert fragment_issues("Avoid, Oct 3 — the most pressured day.")
    assert fragment_issues("Hold any speculative move until, then keep it small.")
    assert fragment_issues("Raman, Oct 5 () is your day.")


def test_clean_answers_pass():
    for t in ("Monday, Oct 5 is your least-strained day. Avoid Saturday, Oct 3.",
              "Raman, tomorrow looks like a day to protect what you have.",
              "The strong career window is Nov 2026 – Jan 2027.",
              "Act before 22:47 tonight — keep it small, capped and simple."):
        assert fragment_issues(t) == [], t
        assert unsupported_dates(t, GROUND) == [], t


def test_invented_dates_are_flagged():
    assert unsupported_dates("Your best day is Oct 9.", GROUND) == ["md:10-09"]
    assert unsupported_dates("Things open on Dec 12.", GROUND) == []        # inside the window
    assert unsupported_dates("Act before 21:00.", GROUND) == ["t:21:00"]
    assert unsupported_dates("Big shift in Mar 2027.", GROUND) == ["ym:2027-03"]


def test_tidy_last_resort():
    assert tidy(", Oct 5 () is your day ,  really.") == "Oct 5 is your day, really."


def _rewriter(answer):
    calls = []

    async def rw(system, user):
        calls.append(json.loads(user))
        return json.dumps(answer)
    return rw, calls


def test_clean_fields_skip_the_model():
    rw, calls = _rewriter({})
    out, rep = asyncio.run(run_gate({"read": "Monday, Oct 5 is calm."}, GROUND, "en", rw))
    assert rep["action"] == "clean" and calls == [] and out["read"] == "Monday, Oct 5 is calm."


def test_good_rewrite_is_accepted():
    rw, calls = _rewriter({"read": "Monday, Oct 5 is your least-strained day this week.",
                           "next": "Hold any speculative move until Oct 5, then keep it small."})
    out, rep = asyncio.run(run_gate(
        {"read": ", Oct 5 is your least-strained day this week.",
         "next": "Hold any speculative move until, then keep it small."}, GROUND, "en", rw))
    assert rep["action"] == "rewritten"
    assert out["next"].startswith("Hold any speculative move until Oct 5")
    assert "md:10-05" in calls[0]["ALLOWED_DATES"]


def test_rewrite_that_drops_a_supported_date_is_rejected():
    rw, _ = _rewriter({"read": "Monday is your least-strained day this week."})
    out, rep = asyncio.run(run_gate({"read": ", Oct 5 is your least-strained day this week."},
                                    GROUND, "en", rw))
    assert rep["action"] == "tidied" and out["read"] == "Oct 5 is your least-strained day this week."


def test_rewrite_that_invents_a_date_is_rejected():
    rw, _ = _rewriter({"read": "Oct 9 is your least-strained day this week."})
    out, rep = asyncio.run(run_gate({"read": ", Oct 5 is your least-strained day this week."},
                                    GROUND, "en", rw))
    assert rep["action"] == "tidied" and "Oct 9" not in out["read"]


def test_rewrite_failing_the_voice_validator_is_rejected():
    rw, _ = _rewriter({"read": "Your chart says Oct 5 is your least-strained day this week."})
    out, rep = asyncio.run(run_gate(
        {"read": ", Oct 5 is your least-strained day this week."}, GROUND, "en", rw,
        validator=lambda *t: ["chart_word"] if any("chart" in x for x in t) else []))
    assert rep["action"] == "tidied" and "chart" not in out["read"]


def test_invented_date_gets_rewritten_out():
    rw, _ = _rewriter({"read": "Later this week is your least-strained stretch."})
    out, rep = asyncio.run(run_gate({"read": "Oct 9 is your least-strained stretch."},
                                    GROUND, "en", rw))
    assert rep["action"] == "rewritten" and "Oct 9" not in out["read"]


def test_model_error_never_blocks():
    async def boom(system, user):
        raise RuntimeError("down")
    out, rep = asyncio.run(run_gate({"read": "Avoid, Oct 3 today."}, GROUND, "en", boom))
    assert rep["action"] == "tidied" and out["read"]


def test_ordinary_sentence_endings_are_not_flagged():
    for t in ("None of these days is clearly better.", "It is time to move on.",
              "Rest the day after.", "Log in and look again."):
        assert fragment_issues(t) == [], t
