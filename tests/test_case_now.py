"""Moment (Prashna) chart read for a creditor matter: a 'right now' clause, never a verdict."""
import re
from datetime import datetime, timezone
from pathlib import Path

import main
from antar_engine import case_now as cn, debt as dbt
from tests.test_creditor_posture import STRONG_CRED


def test_moment_chart_is_a_valid_whole_sign_chart():
    cd = cn.moment_chart_data(datetime(2026, 10, 12, 21, 0, tzinfo=timezone.utc))
    assert cd["lagna"]["sign"]
    assert set(cd["planets"]) == {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"}
    assert all(1 <= p["house"] <= 12 for p in cd["planets"].values())
    # Rahu and Ketu are always opposite (6 houses apart)
    assert (cd["planets"]["Rahu"]["house"] - cd["planets"]["Ketu"]["house"]) % 12 == 6


def test_moment_chart_changes_with_time():
    a = cn.moment_chart_data(datetime(2026, 10, 12, 3, 0, tzinfo=timezone.utc))
    b = cn.moment_chart_data(datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc))
    assert a["lagna"]["sign"] != b["lagna"]["sign"]            # the ascendant turns ~every 2h


def test_creditor_now_reads_the_moment_with_the_same_posture_vocabulary():
    n = cn.creditor_now(datetime(2026, 10, 12, 21, 0, tzinfo=timezone.utc))
    assert n["available"] and n["posture"] in ("user_ahead", "creditor_ahead", "evenly_matched", "both_quiet")


def test_now_clause_agrees_or_differs_and_is_never_an_outcome():
    for lang in ("en", "es", "pt"):
        assert cn.now_clause("user_ahead", "user_ahead", lang)
        for now in ("user_ahead", "creditor_ahead", "evenly_matched", "both_quiet"):
            t = cn.now_clause("evenly_matched", now, lang)
            assert t.startswith(" ") and t.endswith(".")
            assert not re.search(r"you will win|you will lose|ganar[aá]s|perder[aá]s|vai ganhar|vai perder", t, re.I)
    assert cn.now_clause("user_ahead", None) == ""
    assert "holds right now" in cn.now_clause("user_ahead", "user_ahead", "en")
    assert "better hand" in cn.now_clause("creditor_ahead", "user_ahead", "en")


def test_creditor_lead_appends_the_now_clause_and_has_a_kill_switch(monkeypatch):
    on = main._creditor_lead(STRONG_CRED, "my case with my creditor", "en")
    natal = dbt.creditor_posture_phrase(dbt.analyze_creditor(STRONG_CRED)["posture"], "en")
    assert on.startswith(natal) and len(on) > len(natal) and "right now" in on.lower()
    monkeypatch.setenv("ASK_CASE_NOW", "off")
    assert main._creditor_lead(STRONG_CRED, "my case with my creditor", "en") == natal


def test_wired_into_main():
    src = (Path(__file__).resolve().parent.parent / "main.py").read_text()
    assert "from antar_engine.case_now import creditor_now, now_clause" in src
