"""[ui-audit 2026-10-11] A reader between jobs must not be told to donate money."""
import importlib
import sys
import types


def _fn():
    # main.py is huge; load only the helper by exec'ing its source segment
    src = open("main.py").read()
    start = src.index("_FIN_HARDSHIP_MARKERS = (")
    end = src.index("# [i18n-drift 2026-09-21]")
    ns = {}
    exec(src[start:end], ns)
    return ns["_can_give_money_now"]


def test_jobless_reader_cannot_give_money():
    f = _fn()
    assert f(None, {"life_work": "transition"}) is False
    assert f("stable", {"career_stage": "unemployed"}) is False


def test_others_keep_default_behaviour():
    f = _fn()
    assert f(None) is True
    assert f(None, {"life_work": "job"}) is True
    assert f("no income", {"life_work": "job"}) is False
