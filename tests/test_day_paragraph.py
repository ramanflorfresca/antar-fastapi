"""[day-paragraph 2026-10-15] Each day-map line becomes a 3-4 sentence paragraph from real reads only."""
import re

from antar_engine import day_paragraph as dp, ritual_today as rt

MONEY = ("Money moves your way today — income and what you're owed flow in, and the strength is real; spending just tends to creep up right "
         "alongside it. Take the inflow, but keep a light eye on the outflow.")
TRAVEL = "Getting around is bumpy today — small journeys tend to carry small setbacks."
MONTH = [{"key": "money", "label": "Money", "verdict": "steady"}, {"key": "health", "label": "Health", "verdict": "tough"}]
WIN = {"best": "12:29 PM – 1:17 PM", "avoid": "2:04 PM – 3:27 PM"}


def _s(t):
    return [x for x in re.split(r"(?<=[.!?])\s+", t.strip()) if x]


def test_opportunity_line_gets_month_context_and_the_best_window():
    out = dp.paragraphs([{"key": "money", "label": "Your wallet", "tone": "opportunity", "line": MONEY}], MONTH, WIN)
    p = out[0]["paragraph"]
    assert p.startswith("Money moves your way today")
    assert "A brighter day inside a steadier month for money" in p
    assert p.endswith("The best window to act on it is 12:29 PM – 1:17 PM.")


def test_risk_line_without_a_move_gets_the_band_move_and_the_avoid_window():
    out = dp.paragraphs([{"key": "travel", "label": "Getting around", "tone": "risk", "line": TRAVEL}], MONTH, WIN)
    p = out[0]["paragraph"]
    assert "Leave early and pad the schedule." in p and "Steer clear of 2:04 PM – 3:27 PM for anything final." in p
    assert len(_s(p)) >= 3


def test_move_already_in_the_line_is_not_repeated():
    out = dp.paragraphs([{"key": "money", "label": "Your wallet", "tone": "opportunity", "line": MONEY}], None, None)
    assert out[0]["paragraph"].lower().count("light eye on the outflow") == 1


def test_best_and_avoid_window_are_used_once_each():
    dm = [{"key": "money", "label": "Your wallet", "tone": "opportunity", "line": MONEY},
          {"key": "work", "label": "Work", "tone": "opportunity", "line": "Work runs well today."}]
    ps = [o["paragraph"] for o in dp.paragraphs(dm, MONTH, WIN)]
    assert sum("best window" in p for p in ps) == 1


def test_no_month_read_still_gives_a_paragraph_and_stays_plain():
    out = dp.paragraphs([{"key": "travel", "label": "Getting around", "tone": "risk", "line": TRAVEL}], None, None)
    assert len(_s(out[0]["paragraph"])) >= 2 and rt.jargon_leaks({"p": out[0]["paragraph"]}) == []


def test_spanish_templates():
    out = dp.paragraphs([{"key": "money", "label": "Dinero", "tone": "risk", "line": "Hoy el dinero aprieta."}],
                        [{"key": "money", "label": "Dinero", "verdict": "good"}], WIN, "es")
    assert "Un día más duro dentro de un buen mes para dinero" in out[0]["paragraph"]
