"""[area-paragraph 2026-10-15] Every area read carries a 2-3+ sentence paragraph made only from real lines, never empty or jargon."""
import re
from datetime import date

from antar_engine import area_paragraph as ap, period_view as pv, ritual_today as rt
from tests.test_period_view import _Ctx, _lib

STEPS = {"partnership": "Put time into the relationship.", "business": "Pitch and price up; keep costs flexible."}
BEST = {"label": "Oct 15 to Oct 21"}
AVOID = {"label": "Oct 1 to Oct 7"}


def _sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s]


def test_mixed_area_joins_support_and_catch_in_one_paragraph():
    dom = {"key": "money", "label": "Money", "tone": "mixed",
           "lines": [{"text": "This period is prosperous for you."}, {"text": "Money can slip away around travel."}]}
    p = ap.paragraph(dom, scope="month", relation="current", lang="en",
                     areas_by_key={"business": {"lean_in": [1]}}, area_keys=("money", "business"), turns=[], best=BEST, avoid=AVOID, steps=STEPS)
    assert p.startswith("Money is mixed this month, with an upside.")
    assert "The catch: money can slip away around travel." in p
    assert "Pitch and price up" in p and "Oct 15 to Oct 21" in p and len(_sentences(p)) >= 4


def test_quiet_area_still_gets_a_real_paragraph_from_the_window():
    dom = {"key": "career", "label": "Career", "tone": "quiet", "lines": [], "quiet": "Nothing pushes hard either way here."}
    p = ap.paragraph(dom, scope="month", relation="current", lang="en", areas_by_key={}, area_keys=("work",),
                     turns=[], best=BEST, avoid=AVOID, steps=STEPS)
    assert p.startswith("Career is steady this month.") and "steady, visible effort" in p and "Oct 15 to Oct 21" in p
    assert len(_sentences(p)) >= 3


def test_care_area_names_the_quieter_stretch():
    dom = {"key": "health", "label": "Health", "tone": "care", "lines": [{"text": "Energy runs low."}]}
    p = ap.paragraph(dom, scope="week", relation="next", lang="en", areas_by_key={}, area_keys=("health",), turns=[], best=BEST, avoid=AVOID, steps={})
    assert p.startswith("Health needs care next week.") and "The catch: energy runs low." in p and "Keep commitments light during Oct 1 to Oct 7." in p


def test_past_reads_past_tense_and_gives_no_instructions():
    dom = {"key": "love", "label": "Love", "tone": "good", "lines": [{"text": "Marriage was likely."}]}
    p = ap.paragraph(dom, scope="month", relation="past", lang="en", areas_by_key={"partnership": {"lean_in": [1]}},
                     area_keys=("love", "partnership"), turns=[], best=BEST, avoid=AVOID, steps=STEPS)
    assert p.startswith("Love went well last month.") and "Put time into" not in p and "The strongest stretch was Oct 15 to Oct 21." in p


def test_own_turn_is_named_with_its_date():
    dom = {"key": "love", "label": "Love", "tone": "good", "lines": [{"text": "Marriage is likely."}]}
    p = ap.paragraph(dom, scope="month", relation="current", lang="en", areas_by_key={}, area_keys=("partnership",),
                     turns=[{"area": "partnership", "label": "Oct 31", "text": "The extra lift behind your partnership area eases."}],
                     best=None, avoid=None, steps={})
    assert "On Oct 31: the extra lift behind your partnership area eases." in p


def test_spanish():
    dom = {"key": "career", "label": "Carrera", "tone": "quiet", "lines": []}
    p = ap.paragraph(dom, scope="month", relation="current", lang="es", areas_by_key={}, area_keys=("work",), turns=[], best=BEST, avoid=None, steps={})
    assert p.startswith("Carrera está estable este mes.") and "Oct 15 to Oct 21" in p


def test_period_build_attaches_a_paragraph_to_every_area_and_stays_plain():
    for scope in ("week", "month", "year"):
        o = pv.build(_Ctx(), _lib(), {"employed": True}, scope, 0, "en", today=date(2026, 10, 14))
        assert len(o["domains"]) == 5
        for d in o["domains"]:
            assert d["paragraph"] and len(_sentences(d["paragraph"])) >= 2, (scope, d["key"])
            assert rt.jargon_leaks({"p": d["paragraph"]}) == []
