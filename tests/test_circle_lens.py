"""The lens framework: every relation type gets a brief with its own logic, copy and structures."""
import json
import re
import sys
from datetime import date

import pytest

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from antar_engine import circle_brief as CB  # noqa: E402
from antar_engine import circle_copy as CC  # noqa: E402
from antar_engine import circle_fit as F  # noqa: E402
from antar_engine import circle_lens as L  # noqa: E402
from antar_engine import people_links as PL  # noqa: E402

LANGS = ("en", "es", "pt", "hinglish")
TODAY = date(2026, 10, 8)
_JARGON = re.compile(
    r"\b(dasha|dasa|jaimini|vimsottari|parashar\w*|lords?|malefic\w*|benefic\w*|transits?|karakas?|lagna|nakshatras?|navamsa|"
    r"kendra|ascendant|houses?|\d+(st|nd|rd|th)|d-?\d{1,2}|sun|moon|mars|mercury|jupiter|venus|saturn|rahu|ketu|yoga|"
    r"price|premium|subscribe\w*)\b", re.I)
_PREDICT = re.compile(r"\b(will (succeed|win|raise|fail|work|last)|guarantee\w*|destined|doomed)\b", re.I)


def strings(x):
    if isinstance(x, str): yield x
    elif isinstance(x, dict):
        for v in x.values(): yield from strings(v)
    elif isinstance(x, (list, tuple)):
        for v in x: yield from strings(v)


def test_every_relation_type_has_a_lens_and_every_lens_a_family():
    assert set(L.LENSES) == set(PL.RELATIONS) | {"advisee"}              # advisee = the other side of advisor
    assert {L.LENSES[r]["family"] for r in L.LENSES} == {"work_partner", "work_hier", "counsel", "close"}
    assert L.LENSES["cofounder"]["family"] == L.LENSES["business"]["family"] == "work_partner"
    assert L.LENSES["employee"]["family"] == L.LENSES["boss"]["family"] == "work_hier"
    assert L.LENSES["advisor"]["family"] == L.LENSES["advisee"]["family"] == "counsel"
    for r in ("spouse", "romantic", "parent", "child", "sibling", "family", "friend"):
        assert L.LENSES[r]["family"] == "close"
    for r, spec in L.LENSES.items():
        assert spec["topics"] and spec["phase"] in ("work", "close")
        assert CB.lens_for(r) == r and CB.family_of(r) == spec["family"]
    assert CB.lens_for("zzz") is None and CB.lens_for(None) is None


def test_roles_follow_what_the_other_is_to_the_viewer():
    assert L.roles_for("child") == ("parent", "child")           # the viewer of a 'child' relation is the parent
    assert L.roles_for("parent") == ("child", "parent")
    assert L.roles_for("employee") == ("boss", "employee")
    assert L.roles_for("boss") == ("employee", "boss")
    assert L.roles_for("advisor") == ("advisee", "advisor") and L.roles_for("advisee") == ("advisor", "advisee")
    assert L.roles_for("friend") == ("friend", "friend") and L.roles_for("spouse") == ("spouse", "spouse")
    for r in tuple(PL.RELATIONS) + ("advisee",):
        for role in L.roles_for(r):
            if r not in ("cofounder", "business"):
                assert role in L.ROLE_SPEC, (r, role)


def test_bond_verdict_thresholds_and_families():
    v = lambda lens, a, b: L.bond_verdict(lens, a, b)["key"]
    assert v("friend", "strong", "strong") == "natural_fit" and v("friend", "strong", "steady") == "natural_fit"
    assert v("friend", "steady", "steady") == "workable_with_care" and v("friend", "strong", "strained") == "workable_with_care"
    assert v("friend", "strained", "steady") == "needs_patience" and v("friend", "strained", "strained") == "needs_patience"
    assert "working fit" in L.bond_verdict("employee", "strong", "strong")["line"]
    assert "counsel fit" in L.bond_verdict("advisor", "strong", "strong")["line"]
    assert "natural bond" in L.bond_verdict("spouse", "strong", "strong")["line"]
    assert L.bond_verdict("cofounder", "strong", "strong") is None and L.bond_verdict("zzz", "strong", "strong") is None
    assert L.bond_verdict("friend", None, None)["key"] == "workable_with_care"       # unknown reads as steady, never a harsh call
    assert (L.STRONG_MIN, L.STRAINED_MAX) == (2.0, -1.5)


def test_all_lens_copy_is_four_languages_plain_and_makes_no_prediction():
    def check(t):
        if isinstance(t, dict) and set(t) >= {"en"}:
            assert set(t) >= set(LANGS), t
    for t in L.TEXTS:
        check(t)
        for s in strings(t):
            assert not _JARGON.search(s), s
            assert not _PREDICT.search(s), s
    for d in (L.REASON, L.LEVEL_LABEL, L.VERDICT_TITLE, L.PHASE_CLOSE, L.CALL_CLOSE, L.DONT, L.PACE):
        for k, v in d.items():
            assert set(v) >= set(LANGS), k
    assert set(L.AREA) >= set(LANGS)                                   # AREA is keyed language first
    for lang in LANGS:
        assert set(L.AREA[lang]) == {s["area"] for s in L.ROLE_SPEC.values()}
    for fam in L.VERDICT_LINE.values():
        for k in L.VERDICT_TITLE:
            assert set(fam[k]) >= set(LANGS)


@pytest.fixture(scope="module")
def two():
    from test_topic_engine import _real_ctx
    return _real_ctx("1985-03-15", "08:30"), _real_ctx("1990-10-15", "14:10")


def test_bond_for_every_role_on_real_charts_is_deterministic_plain_and_neutral(two):
    for c in two:
        for role in L.ROLE_SPEC:
            b = L.bond_for(c.chart_data, role, "en")
            assert b == L.bond_for(c.chart_data, role, "en") and b["level"] in ("strong", "steady", "strained") and b["role"] == role
            for lang in LANGS:
                bl = L.bond_for(c.chart_data, role, lang)
                for line in [bl["label"]] + bl["reasons"]:
                    assert not _JARGON.search(line), line
                    assert not re.search(r"\b(you|your|tú|tu|você|aap)\b", line, re.I) or lang == "hinglish", line
    assert L.bond_for(two[0].chart_data, "cofounder") is None and L.bond_for({}, "friend")["level"] in ("steady", "strained", "strong")


def test_brief_for_every_relation_on_real_charts_in_every_language(two):
    a, b = two
    topics = []
    for rel in tuple(PL.RELATIONS) + ("advisee",):
        lens = CB.lens_for(rel)
        roles = (None, None) if CB.family_of(lens) == "work_partner" else L.roles_for(lens)
        for lang in LANGS:
            pa = CB.profile(a.chart_data, a.dashas, "Raman", lang, TODAY, bond_role=roles[0])
            pb = CB.profile(b.chart_data, b.dashas, "Andres", lang, TODAY, bond_role=roles[1])
            fam = "work" if L.LENSES[lens]["phase"] == "work" else "close"
            sa, sb = F.season_at(a.chart_data, a.dashas["vimsottari"], TODAY), F.season_at(b.chart_data, b.dashas["vimsottari"], TODAY)
            ph = F.phase(sa, sb, "Raman", "Andres", (a.chart_data, a.dashas["vimsottari"]), (b.chart_data, b.dashas["vimsottari"]), lang, TODAY, fam)
            br = CB.build(pa, pb, lens, topics, {"badge": "MIXED"}, [], lang, TODAY, ph)
            assert br["lens"] == lens and br["family"] == CB.family_of(lens) and br["verdict"]["title"] and br["verdict"]["line"]
            assert 1 <= len(br["donts"]) <= 3 and br["balance"]["line"] and br["timing"]["line"]
            if br["family"] == "work_partner":
                assert pa["role_label"] and pa["partnership"] and pa["bond"] is None
            else:
                assert pa["role_label"] is None and pa["partnership"] is None and pa["bond"]["label"]
                assert br["verdict"]["key"] in ("natural_fit", "workable_with_care", "needs_patience")
                assert br["balance"]["kind"].startswith("pace_") and br["balance"]["tail"] == ""
            blob = json.dumps({k: v for k, v in br.items() if k != "note"}, ensure_ascii=False)
            assert not _JARGON.search(blob), (rel, lang, _JARGON.search(blob).group(0))
            assert not re.search(r"\{[a-z_]+\}", blob), (rel, lang)               # no unfilled placeholder


def test_close_lenses_use_their_own_phase_wording_and_call_titles(two):
    a, b = two
    sa = F.season_at(a.chart_data, a.dashas["vimsottari"], TODAY)
    clouded = {"md": "Jupiter", "ad": "Rahu", "md_start": date(2011, 6, 5), "md_end": date(2027, 6, 5), "ad_start": date(2025, 1, 10),
               "ends": date(2027, 6, 5), "pos": "last", "next_md": "Saturn", "tone": "clouded", "heavy": True}
    ok = dict(clouded, ad="Venus", tone="favorable", heavy=False)
    rows = [{"level": "antardasha", "lord_or_sign": "Venus", "start_date": "2026-01-01", "end_date": "2031-01-01"}]
    close = F.phase(clouded, ok, "Andres", "Sam", ({}, rows), ({}, rows), "en", TODAY, "close")
    work = F.phase(clouded, ok, "Andres", "Sam", ({}, rows), ({}, rows), "en", TODAY, "work")
    assert close["call_title"] == "A delicate time" and "Avoid big decisions about this relationship" in close["line"]
    assert work["call_title"] == "Not now" and "formalizing" in work["line"]
    assert close["call"] == work["call"] == "not_now"
    assert F.phase(ok, ok, "A", "B", ({}, rows), ({}, rows), "es", TODAY, "close")["call_title"] == "Un momento tranquilo"


def test_timing_uses_each_lens_own_topics_and_dont_lines_by_family():
    w = lambda s, e: {"start": s, "end": e, "label": "x", "days": 5}
    topics = [{"topic": t, "label": t.title(), "best": [], "care": [w("2026-11-01", "2026-11-09")]} for t in ("money", "love", "family", "career", "peace", "business", "health")]
    seen = lambda lens: {x["topic"] for x in CB.timing(topics, lens, "en", TODAY)["careful"]}
    assert seen("spouse") <= {"love", "family", "money"} and "business" not in seen("spouse")
    assert seen("friend") <= {"peace", "love"} and seen("employee") <= {"career", "money"}
    prof = lambda: {"watch_for": [], "role": "anchor"}
    care = [{"range": "Nov 1 – Nov 9", "label": "Love"}]
    assert CB.donts(care, [prof(), prof()], "en", "spouse")[0].startswith("Avoid big conversations or decisions about this relationship during Nov 1")
    assert "Don't keep score" in CB.donts(care, [prof(), prof()], "en", "friend")[-1]
    assert "Take the advice" in CB.donts(care, [prof(), prof()], "en", "advisor")[-1] or "decide for yourself" in CB.donts(care, [prof(), prof()], "en", "advisor")[-1]
    assert "scope or reporting" in CB.donts(care, [prof(), prof()], "en", "employee")[-1]
    assert CB.donts(care, [prof(), prof()], "en", "cofounder")[-1].startswith("Don't split by title")


def test_a_mixed_area_is_said_once_not_as_strong_and_strained(two, monkeypatch):
    from antar_engine import career_mode as CM
    chart = two[0].chart_data
    calls = iter([2.0, 0.0])                          # house 1 lord strong, house 2 lord neutral
    monkeypatch.setattr(CM, "_strength", lambda c, p: 2.0 if p in ("Sun", "Saturn") else 0.0)
    monkeypatch.setattr(CM, "_house_of", lambda c, p: 8 if p == CM._lord_of(c, 11) else 1)
    b = L.bond_for(chart, "boss", "en")
    joined = " ".join(b["reasons"])
    assert not ("strong here" in joined and "carry strain" in joined)


def test_the_advisee_side_reads_end_to_end():
    """Found by the live run: Andres is the advisee in a pair where Raman invited him as an advisor; that side
    returned no reading at all because the engine has no 'advisee' reason."""
    from antar_engine import circle_reading as CR
    assert CR.reason_for("advisee", PL) == CR.reason_for("advisor", PL) == "advisor"
    assert CB.lens_for("advisee") == "advisee" and CB.family_of("advisee") == "counsel"
