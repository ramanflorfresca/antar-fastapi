"""'What to do': practical moves replace colour/weekday remedies on the relationship page."""
import re
import sys

import pytest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from antar_engine import circle_moves as CM  # noqa: E402

LANGS = ("en", "es", "pt", "hinglish")
_JARGON = re.compile(
    r"\b(dasha|dasa|jaimini|vimsottari|malefic\w*|benefic\w*|transits?|karakas?|lagna|nakshatra|navamsa|kendra|"
    r"ascendant|houses?|d-?\d{1,2}|sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|"
    r"wear|colou?rs?|colou?r|friday|wednesday|monday|tuesday|thursday|saturday|sunday|gemstone|mantra|remed\w*|"
    r"price|premium|subscribe\w*)\b", re.I)


def L(key, score, passed):
    return {"layer_key": key, "score": score, "passed": passed, "applicable": True}


LAYERS = [L("soul", 60, False), L("chemistry", 90, True), L("public", 61, False), L("lifepath", 67, True),
          L("communication", 23, False), L("friction", 84, True)]


def test_only_weak_areas_weakest_first_max_three():
    m = CM.moves_for(LAYERS, "business", "en")
    assert [x["area"] for x in m] == ["communication", "soul", "public"]
    assert m[0]["text"] == "Put decisions in writing: who decided what, and by when."
    assert all(set(x) == {"area", "area_label", "text"} for x in m)
    assert len(CM.moves_for([L(k, 10, False) for k in CM.AREAS], "friend", "en")) == 3


def test_everything_flowing_or_missing_gives_nothing():
    assert CM.moves_for([L(k, 90, True) for k in CM.AREAS], "friend") == []
    assert CM.moves_for(None, "friend") == [] and CM.moves_for([], "friend") == []
    assert CM.moves_for([{"layer_key": "soul"}, {"layer_key": "zzz", "score": 1, "passed": False}], "friend") == []
    assert CM.moves_for([dict(L("soul", 20, False), applicable=False)], "friend") == []


def test_work_vs_close_wording():
    assert CM.family("cofounder") == "work" and CM.family("boss-or-manager") == "work" and CM.family("advisor") == "work"
    assert CM.family("friend") == "close" and CM.family("spouse") == "close" and CM.family(None) == "close"
    w = CM.moves_for([L("communication", 20, False)], "advisor", "en")[0]["text"]
    c = CM.moves_for([L("communication", 20, False)], "spouse", "en")[0]["text"]
    assert w != c and "writing" in w and "plainly" in c


def test_accepts_the_joint_readings_shape_too():
    layers = [{"key": "soul", "score": 60, "status": "needs_care"}, {"key": "friction", "score": 84, "status": "flows"},
              {"key": "communication", "score": 23, "status": "friction"}]
    assert [m["area"] for m in CM.moves_for(layers, "friend", "es")] == ["communication", "soul"]


def test_every_language_has_every_line_and_no_remedy_or_jargon_words():
    for fam in ("work", "close"):
        for lang in LANGS:
            assert set(CM.MOVE[fam][lang]) == set(CM.AREAS)
    for lang in LANGS:
        assert set(CM.AREA_LABEL[lang]) == set(CM.AREAS)

    def strings(x):
        if isinstance(x, str):
            yield x
        elif isinstance(x, dict):
            for v in x.values():
                yield from strings(v)
    for t in CM.TEXTS:
        for s in strings(t):
            assert not _JARGON.search(s), s
    assert CM.moves_for(LAYERS, "friend", "hi")[0]["text"] == CM.moves_for(LAYERS, "friend", "en")[0]["text"]   # hindi -> English
    assert CM.moves_for(LAYERS, "friend", "es")[0]["text"].startswith("Cuando algo importa")
