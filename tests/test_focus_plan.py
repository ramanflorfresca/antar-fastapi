from datetime import date, datetime
from antar_engine import focus_plan as fp, focus_view as fv


class _P:
    def __init__(self, sign):
        self.sign = sign


class _Ctx:
    today = date(2026, 10, 14)
    lagna = 9                      # Capricorn
    planets = {"Rahu": _P(0), "Jupiter": _P(4), "Sun": _P(8)}
    vim = [{"level": "ad", "lord": "Rahu", "start": datetime(2026, 8, 13), "end": datetime(2029, 4, 25)}]


def test_area_houses_union():
    assert fp.area_houses(("money", "career")) >= {2, 11, 10}


def test_months_strip_marks_the_strongest_stretch_and_the_tone(monkeypatch):
    monkeypatch.setattr(fp.rr, "timeline", lambda ctx, s, m, l: [{"start": "2026-10-14", "end": "2026-12-31", "tone": "good"},
                                                                 {"start": "2026-12-14", "end": "2027-04-14", "tone": "bad"}])
    cells = fp.months_strip(_Ctx, ("money",), 6, "en", [{"start": "2026-10-14", "end": "2026-11-26"}])
    assert len(cells) == 6 and cells[0]["peak"] and cells[1]["peak"] and not cells[3]["peak"]
    assert cells[0]["tone"] == "good" and cells[1]["tone"] == "good" and cells[2]["tone"] == "mixed" and cells[3]["tone"] == "bad" and cells[4]["tone"] == "bad"


def test_chapters_are_dated_plain_and_say_whether_they_touch_the_topic():
    ch = fp.chapters(_Ctx, ("money",), 6, "en")
    assert ch and all(c["start"] <= c["end"] for c in ch) and all(c["theme"] for c in ch)
    assert ch[0]["start"] == "2026-10-14" and {"theme", "nature", "supports"} <= set(ch[0])


def test_turning_points_only_fire_when_membership_of_the_topic_changes(monkeypatch):
    calls = {}

    def fake(d):
        k = (d - _Ctx.today).days
        jup = 10 if k < 20 else 9 if k < 40 else 8       # houses 2 -> 1 -> 12 from Capricorn lagna (sign idx: lagna 9)
        return {"Jupiter": jup, "Saturn": 4, "Rahu": 0}
    monkeypatch.setattr(fp, "transit_signs", fake)
    out = fp.turning_points(_Ctx, "Money", ("money",), 3, "en")
    texts = [o["text"] for o in out]
    assert any("Growth and luck move into your money area" in t for t in texts) or any("eases" in t for t in texts)
    assert all(o["date"] > _Ctx.today.isoformat() for o in out)
    assert fp.turning_points(_Ctx, "X", ("nonexistent",), 3, "en") == []


def test_no_planet_or_method_words_in_plan_text():
    import re
    for lang in ("en", "es"):
        for t in fp.TXT[lang].values():
            assert not re.search(r"Jupiter|Saturn|Rahu|Júpiter|Saturno|planet|house|casa", t, re.I), t


def test_detail_carries_the_plan_block(monkeypatch):
    from tests.test_focus_view import _run2
    out = _run2(monkeypatch, {"employed": False}, area="money")
    plan = out["detail"]["plan"]
    assert plan is None or set(plan) == {"months", "chapters", "turns"}
    assert out["labels"]["plan_months"] == "Month by month" and out["labels"]["supports"] == "Touches this topic"
