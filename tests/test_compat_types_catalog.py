"""The relationship types the People "add a person" flow offers.

Covers: the public GET /api/v1/compatibility/types list, the seven newer ids
(mother, father, daughter, son, girlfriend, boyfriend, business_partner) each read by
an EXISTING type's engine, the employee `position`, the user-facing `compat_type_label` on the reads, and a
drift guard so the list, the engine tables, the wording and the languages cannot
fall apart. The original twelve types must read exactly as they did before: the
golden file was generated from the code on origin/main before any of this existed.
"""
import copy
import json
import os
import re

import pytest

from antar_engine import Compatibility as C
from antar_engine import compatibility_layers as CL
from antar_engine import compatibility_reasons as R
from antar_engine import compatibility_templates as T
from antar_engine import compatibility_types as CT
from antar_engine import people_links as PL

HERE = os.path.dirname(__file__)
ORIGINAL = ["romantic", "spouse", "business", "cofounder", "friend", "family", "sibling",
            "parent", "child", "advisor", "employee", "boss-or-manager"]
NEW = ["mother", "father", "daughter", "son", "girlfriend", "boyfriend", "business_partner", "husband", "wife"]
OWNER_FIRST = ["mother", "father", "daughter", "son", "girlfriend", "boyfriend", "husband", "wife",
               "employee", "business_partner", "cofounder", "friend"]
LANGS = ("en", "es", "pt", "hinglish")

# Words a reader should never meet in these strings.
JARGON = re.compile(
    r"\b(dasha|mahadasha|antardasha|nakshatra|kuta|koota|ashtakoot|nadi|bhakoot|yoni|gana|"
    r"varna|graha|maitri|navamsa|lagna|rashi|karaka|gochar|sade sati|vimshottari|vimsottari|"
    r"rahu|ketu|saturn|jupiter|venus|mars|mercury|astrolog\w*|horoscope|"
    r"\d+(st|nd|rd|th) house|house lord|d-?9|d-?10)\b", re.I)
MARRIAGE_WORDS = re.compile(r"\b(marriage|married|husband|wife|spouse|bride|groom)\b", re.I)
NON_ROMANTIC_WORDS = re.compile(r"\b(romantic|romance|attraction|intimacy|dating|couple)\b", re.I)


# ── helpers ──────────────────────────────────────────────────────────────────

def _chart(moon_sign="Aries", nak="Ashwini", lagna="Aries", shift=0):
    planets = {}
    for i, p in enumerate(["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]):
        planets[p] = {"sign": C.SIGNS[(i * 3 + shift) % 12], "house": ((i + shift) % 12) + 1,
                      "longitude": i * 31.0 + shift, "nakshatra": "Rohini"}
    planets["Moon"] = {"sign": moon_sign, "house": 1, "longitude": C.SIGNS.index(moon_sign) * 30 + 5.0,
                       "nakshatra": nak}
    return {"planets": planets, "lagna": {"sign": lagna}, "current_dasha": "Jupiter-Venus"}


PAIRS = [
    (_chart("Aries", "Ashwini", "Aries"), _chart("Gemini", "Ardra", "Leo", 1)),
    (_chart("Taurus", "Rohini", "Virgo", 2), _chart("Scorpio", "Anuradha", "Pisces", 3)),
    (_chart("Cancer", "Pushya", "Libra", 4), _chart("Cancer", "Ashlesha", "Cancer", 5)),
]


def _role(reason):
    return "sales" if R.REASON_DEFINITIONS[reason]["needs_role"] else None


def _read(reason, ca, cb, a="Asha", b="Ravi"):
    raw = C.calculate_compatibility(ca, cb, a, b, compatibility_type=R.engine_reason(reason))
    return CL.compose_compat_v2(raw, ca, cb, reason, _role(reason), a_name=a, b_name=b)


def _jsonable(x):
    return json.loads(json.dumps(x, default=list, sort_keys=True))


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    import main
    return TestClient(main.app, raise_server_exceptions=False)


# ── 1. the original twelve read exactly as before ────────────────────────────

@pytest.fixture(scope="module")
def golden():
    with open(os.path.join(HERE, "fixtures", "compat_original_types_golden.json")) as f:
        return json.load(f)


@pytest.mark.parametrize("reason", ORIGINAL)
def test_original_type_reads_exactly_as_before(reason, golden):
    g = golden["reasons"][reason]
    runs = []
    for ca, cb in PAIRS:
        v = _read(reason, ca, cb)
        runs.append(_jsonable({k: v.get(k) for k in ("score", "badge", "headline", "summary", "watch_points",
                                                    "catalysts", "direction", "passed")}
                              | {"layers": [(l["layer_key"], l["layer_label"], l["score"],
                                             l["weight_in_this_reason"], l["headline"], l["detail"])
                                            for l in v["layers"]]}))
    assert runs == g["runs"]
    assert _jsonable(R.REASON_WEIGHTS[reason]) == g["weights"]
    assert _jsonable({k: [list(x) for x in v] for k, v in R.sources_for_reason(reason).items()}) == g["sources"]
    assert _jsonable(R.REASON_DEFINITIONS[reason]) == g["definition"]
    assert _jsonable(T._HEADLINES.get(reason)) == g["headline"]
    assert _jsonable(T._DETAILS.get(reason)) == g["detail"]


def test_original_types_keep_their_order_and_picker_entries(golden):
    assert [r for r in R.VALID_REASONS if r in ORIGINAL] == golden["valid_original_order"]
    for lang in LANGS:
        now = {e["key"]: e for e in R.reasons_directory(lang)["reasons"] if e["key"] in ORIGINAL}
        assert _jsonable(now) == golden["directory"][lang], lang


def test_original_forward_dasha_specs_unchanged(golden):
    import main
    for k, v in golden["fwd_spec"].items():
        assert _jsonable(main._FWD_REL_SPEC[k]) == v, k


# ── 2. GET /api/v1/compatibility/types ───────────────────────────────────────

def test_types_endpoint_is_public_and_ordered(client):
    import main
    route = next(r for r in main.app.routes if getattr(r, "path", "") == "/api/v1/compatibility/types")
    assert "GET" in route.methods
    assert not any(p.name.lower() == "authorization" for p in route.dependant.header_params)
    r = client.get("/api/v1/compatibility/types?language=en")
    assert r.status_code == 200
    body = r.json()
    types = body["types"]
    assert body["count"] == len(types) == len(CT.TYPE_ORDER)
    assert [t["id"] for t in types] == list(CT.TYPE_ORDER)
    for t in types:
        assert set(t) == {"id", "label", "group", "group_label", "romantic", "needs_role", "needs_position"}
        assert t["label"] and t["group"] and isinstance(t["romantic"], bool)
    # the owner's eleven choices come first, in this order; legacy types follow
    assert [t["id"] for t in types[:12]] == OWNER_FIRST
    assert "business" not in [t["id"] for t in types]       # business_partner is its twin


def test_romantic_role_and_position_flags(client):
    types = client.get("/api/v1/compatibility/types").json()["types"]
    assert {t["id"] for t in types if t["romantic"]} == {"girlfriend", "boyfriend", "husband", "wife", "spouse", "romantic"}
    assert {t["id"] for t in types if t["needs_role"]} == {"employee", "boss-or-manager"}
    assert {t["id"] for t in types if t["needs_position"]} == {"employee"}


@pytest.mark.parametrize("lang,sample", [
    ("en", {"spouse": "My husband or wife", "mother": "My mother", "boyfriend": "My boyfriend"}),
    ("es", {"spouse": "Mi esposo o esposa", "mother": "Mi madre", "girlfriend": "Mi novia"}),
    ("pt", {"spouse": "Meu marido ou esposa", "son": "Meu filho", "business_partner": "Sócio ou sócia de negócios"}),
    ("hinglish", {"spouse": "Mere pati ya patni", "friend": "Dost", "father": "Mere papa"}),
])
def test_labels_in_each_language(client, lang, sample):
    got = {t["id"]: t["label"] for t in client.get(f"/api/v1/compatibility/types?language={lang}").json()["types"]}
    for k, v in sample.items():
        assert got[k] == v


@pytest.mark.parametrize("lang", ["hi", "fr", "xx", "", "hi-IN"])
def test_hindi_and_unknown_languages_fall_back_to_english(client, lang):
    en = client.get("/api/v1/compatibility/types?language=en").json()
    other = client.get("/api/v1/compatibility/types", params={"language": lang}).json()
    assert other == en


def test_regional_tags_resolve(client):
    es = client.get("/api/v1/compatibility/types?language=es").json()
    assert client.get("/api/v1/compatibility/types?language=es-AR").json() == es
    assert client.get("/api/v1/compatibility/types?language=PT_br").json() == \
        client.get("/api/v1/compatibility/types?language=pt").json()


def test_guest_accept_language_picks_spanish_only_when_no_param(client):
    es = client.get("/api/v1/compatibility/types?language=es").json()
    assert client.get("/api/v1/compatibility/types", headers={"Accept-Language": "es-CO,es;q=0.9"}).json() == es
    en = client.get("/api/v1/compatibility/types?language=en").json()
    # an explicit language wins over the browser header
    assert client.get("/api/v1/compatibility/types?language=en",
                      headers={"Accept-Language": "es-CO"}).json() == en


# ── 3. drift guard ───────────────────────────────────────────────────────────

def _listed_ids(client):
    return [t["id"] for t in client.get("/api/v1/compatibility/types").json()["types"]]


def test_every_listed_type_is_one_the_backend_can_compute(client):
    import main
    ids = _listed_ids(client)
    assert len(ids) == len(set(ids))
    assert set(ids) == set(R.VALID_REASONS) - set(CT.NOT_LISTED), "list and engine disagree"
    directory = {e["key"]: e for e in R.reasons_directory("en")["reasons"]}
    for tid in ids:
        assert R.resolve_reason(tid) == tid                                   # accepted by the add endpoint's validator
        assert tid in R.REASON_DEFINITIONS and tid in R.REASON_WEIGHTS
        assert sum(R.REASON_WEIGHTS[tid].values()) == 100
        assert tid in main._FWD_REL_SPEC                                      # forward-timing houses
        assert tid in T.reasons_with_templates(), f"{tid}: no authored wording"
        assert tid in directory and directory[tid]["question"] and directory[tid]["sublabel"]
        assert R.engine_reason(tid) in R.REASON_WEIGHTS


def test_every_listed_type_has_a_label_in_every_language(client):
    for lang in LANGS:
        got = client.get(f"/api/v1/compatibility/types?language={lang}").json()["types"]
        for t in got:
            assert t["label"].strip() and t["label"] != t["id"], (lang, t)
            assert not JARGON.search(t["label"]), (lang, t["label"])
    for tid in CT.TYPE_ORDER:
        assert tid in R._HINGLISH_LABELS, tid
        assert tid in R._REASON_I18N["es"]["label"] and tid in R._REASON_I18N["pt"]["label"], tid
    # Spanish / Portuguese are real translations, not the English string
    for tid in CT.TYPE_ORDER:
        if tid in ("cofounder",):                   # genuinely the same word
            continue
        assert R.label_for(tid, "es") != R.label_for(tid, "en"), tid
        assert R.label_for(tid, "pt") != R.label_for(tid, "en"), tid


@pytest.mark.parametrize("tid", list(CT.TYPE_ORDER))
def test_start_endpoint_accepts_every_listed_type(client, monkeypatch, tid):
    """The type check is the first thing /start does; a listed id must get past it
    (the stubbed database then stops the call, which is all this test needs)."""
    import main

    class _Stop:
        def table(self, *a, **k):
            raise RuntimeError("stop here: past the type check")

    monkeypatch.setattr(main, "supabase", _Stop())
    body = {"chart_id_a": "a", "chart_id_b": "b", "compat_type": tid}
    if tid == "employee":
        body["position"] = "CTO"                  # a position stands in for the role
    elif R.REASON_DEFINITIONS[tid]["needs_role"]:
        body["role"] = "managerial"
    r = client.post("/api/v1/compatibility/start", json=body)
    assert r.status_code != 422, (tid, r.text)


def test_people_endpoint_accepts_every_listed_type():
    """POST /people maps every listed id onto a relation the database allows (its CHECK
    lists only the original twelve) and reads back as the id or its engine twin."""
    for tid in CT.TYPE_ORDER:
        rel = PL.normalise_relation(tid)
        assert rel, tid
        relation, detail = rel
        assert relation in PL.RELATIONS, (tid, relation)
        assert PL.relation_to_compat_type(relation, detail) in (tid, R.engine_reason(tid)), (tid, relation, detail)


def test_business_partner_survives_storage():
    assert PL.normalise_relation("business_partner") == ("business", "business_partner")
    assert PL.normalise_relation("business partner") == ("business", None)       # older word unchanged
    assert PL.relation_to_compat_type("business", "business_partner") == "business_partner"
    assert PL.relation_to_compat_type("business", None) == "business"
    assert PL.relation_to_compat_type("boss", None) == "boss-or-manager"
    assert PL.normalise_relation("mother") == ("parent", "mother")                # unchanged


def test_ask_resolver_knows_the_new_types():
    from antar_engine import ask_subject as AS
    for tid in NEW:
        assert tid in AS._COMPAT_GROUPS, tid
    people = [{"chart_id_b": "c1", "name_b": "Dev", "compat_type": "mother"}]
    out = AS.resolve_subject("how is my mother doing", "me", people)
    assert out["subject"] == "person" and out["person"]["chart_id"] == "c1", out


# ── 4. each newer type is a normal session result on an existing engine ──────

SAME_NUMBERS = ["mother", "father", "daughter", "son", "business_partner", "husband", "wife"]
DATING = ["girlfriend", "boyfriend"]


@pytest.mark.parametrize("tid", NEW)
def test_new_type_uses_its_base_engine(tid):
    base = R.engine_reason(tid)
    assert base != tid and base in ORIGINAL
    assert R.REASON_WEIGHTS[tid] == R.REASON_WEIGHTS[base]
    assert R.REASON_DEFINITIONS[tid]["needs_role"] is False
    import main
    if tid in DATING:
        # same houses and planets as "romantic", minus the separation-timing penalty
        assert {k: v for k, v in main._FWD_REL_SPEC[tid].items() if k != "sep"} == \
               {k: v for k, v in main._FWD_REL_SPEC["romantic"].items() if k != "sep"}
        assert main._FWD_REL_SPEC[tid]["sep"] is False
    else:
        assert main._FWD_REL_SPEC[tid] is main._FWD_REL_SPEC[base]
        assert R.sources_for_reason(tid) == R.sources_for_reason(base)


def test_groups_match_the_owner_headings(client):
    types = {t["id"]: t for t in client.get("/api/v1/compatibility/types").json()["types"]}
    assert {types[i]["group"] for i in ("mother", "father")} == {"parent"}
    assert {types[i]["group"] for i in ("son", "daughter")} == {"kids"}
    assert {types[i]["group"] for i in ("husband", "wife", "spouse")} == {"spouse"}
    es = {t["id"]: t for t in client.get("/api/v1/compatibility/types?language=es").json()["types"]}
    assert types["son"]["group_label"] == "Kids" and es["son"]["group_label"] == "Hijos"


def test_marriage_factors_only_for_spouse_and_the_older_romantic():
    assert {r for r in R.VALID_REASONS if R.uses_marriage_kutas(r)} == {"romantic", "spouse", "husband", "wife"}
    for tid in [t for t in NEW if t not in ("husband", "wife")] + ["employee", "friend", "cofounder", "business_partner"]:
        names = {n for layer in R.sources_for_reason(tid).values() for n, _ in layer}
        assert not names & set(R.MARRIAGE_ONLY_SOURCES), tid
    names = {n for layer in R.sources_for_reason("spouse").values() for n, _ in layer}
    assert set(R.MARRIAGE_ONLY_SOURCES) <= names


@pytest.mark.parametrize("tid", NEW)
def test_new_type_produces_a_normal_session_result(tid):
    base = R.engine_reason(tid)
    for ca, cb in PAIRS:
        v, vb = _read(tid, ca, cb), _read(base, ca, cb)
        assert isinstance(v["score"], int) and 0 <= v["score"] <= 100
        assert v["badge"] in ("FLOW", "MIXED", "STRAIN") and v["badge"] == R.badge(v["score"])
        assert [l["layer_key"] for l in v["layers"]] == list(R.LAYER_ORDER)
        assert [l["weight_in_this_reason"] for l in v["layers"]] == [l["weight_in_this_reason"] for l in vb["layers"]]
        assert v["headline"] and v["summary"] and all(l["detail"] and l["headline"] for l in v["layers"])
        if tid in SAME_NUMBERS:                     # same engine => same numbers as the base type
            assert v["score"] == vb["score"] and v["badge"] == vb["badge"]
            assert [l["score"] for l in v["layers"]] == [l["score"] for l in vb["layers"]]


@pytest.mark.parametrize("tid", NEW)
def test_new_type_has_no_marriage_only_factors(tid):
    if tid in ("husband", "wife"):
        pytest.skip("husband / wife are the spouse (marriage) reading")
    assert not R.uses_marriage_kutas(tid)
    # a Nadi / Moon-sign difference between the two people must not move the score
    a = _chart("Aries", "Ashwini")
    same, diff = _chart("Gemini", "Ardra"), _chart("Gemini", "Bharani")
    diff["planets"]["Moon"]["sign"] = same["planets"]["Moon"]["sign"]
    assert _read(tid, a, same)["score"] == _read(tid, a, diff)["score"]
    text = " ".join(T.get_line(tid, l, b, None, "Asha", "Ravi") for l in T.LAYER_ORDER for b in T.BADGES)
    text += " ".join(T.v2_overall(tid, b, "Asha", "Ravi")[i] for b in T.BADGES for i in (0, 1))
    assert not MARRIAGE_WORDS.search(text), MARRIAGE_WORDS.search(text)
    if tid not in DATING:
        assert not NON_ROMANTIC_WORDS.search(text), NON_ROMANTIC_WORDS.search(text)


@pytest.mark.parametrize("tid", ["spouse", "husband", "wife"])
def test_spouse_still_uses_marriage_factors(tid):
    a = _chart("Aries", "Ashwini")
    same, diff = _chart("Gemini", "Ardra"), _chart("Gemini", "Bharani")
    diff["planets"]["Moon"]["sign"] = same["planets"]["Moon"]["sign"]
    assert _read(tid, a, same)["score"] != _read(tid, a, diff)["score"]


def test_family_wording_names_the_person():
    for tid, word in (("mother", "mother"), ("father", "father"), ("daughter", "daughter"), ("son", "son")):
        assert f"your {word}" in T.get_line(tid, "soul", "FLOW", None, "Asha", "Ravi")
    assert "your parent" not in " ".join(T._BASE_LINES["mother"]["soul"].values())


@pytest.mark.parametrize("tid", NEW)
def test_new_type_wording_is_complete_and_calm(tid):
    assert tid in T.reasons_with_templates()
    allc = " ".join(list(T._HEADLINES[tid].values()) + list(T._DETAILS[tid].values()) +
                    [x for lay in T._BASE_LINES[tid].values() for x in lay.values()])
    assert not re.search(r"\b(guarantee\w*|certain(ly)?|definitely|always works|will never|destined|doomed)\b", allc, re.I)


# ── employee position ────────────────────────────────────────────────────────

def test_position_is_cleaned_and_capped():
    import main
    c = main._clean_position
    assert c("  CTO  ") == "CTO" and c("sales   manager") == "sales manager"
    assert c("x" * 100) == "x" * 60 and len(c("y " * 50)) <= 60
    assert c("") is None and c("   ") is None and c(None) is None
    assert "\n" not in c("head\nof ops") and c("a\x00b") == "a b"
    req = main.CompatibilityStartRequest(chart_id_a="a", position="  Assistant ")
    assert req.position == "Assistant"
    assert main.CompatibilityStartRequest(chart_id_a="a", position="z" * 300).position == "z" * 60
    assert main.CompatibilityStartRequest(chart_id_a="a").position is None


def test_position_changes_wording_only_and_only_for_an_employee():
    import main
    base = "A solid pairing."
    assert main._apply_position(base, "Ravi", "employee", "CTO") == "Here Ravi is read as your CTO. A solid pairing."
    assert main._apply_position(base, "Ravi", "employee", None) == base
    assert main._apply_position(base, "Ravi", "friend", "CTO") == base
    # scoring never sees the position: the engine has no position input at all
    import inspect
    assert "position" not in inspect.signature(CL.compose_compat_v2).parameters
    assert "position" not in inspect.signature(C.calculate_compatibility).parameters


def test_employee_with_a_position_needs_no_separate_role(client, monkeypatch):
    import main

    class _Stop:
        def table(self, *a, **k):
            raise RuntimeError("stop here: past validation")

    monkeypatch.setattr(main, "supabase", _Stop())
    base = {"chart_id_a": "a", "chart_id_b": "b", "compat_type": "employee"}
    r = client.post("/api/v1/compatibility/start", json=base)
    assert r.status_code == 422 and r.json()["detail"]["error"] == "role_required"      # as before
    r = client.post("/api/v1/compatibility/start", json={**base, "position": "sales manager"})
    assert r.status_code != 422


def test_jargon_guard_on_every_new_string():
    strings = []
    for tid in NEW:
        strings += list(T._HEADLINES[tid].values()) + list(T._DETAILS[tid].values())
        strings += [x for lay in T._BASE_LINES[tid].values() for x in lay.values()]
        strings.append(R.REASON_DEFINITIONS[tid]["label"])
        strings.append(R._HINGLISH_LABELS[tid])
        for lang in ("es", "pt"):
            strings += [R._REASON_I18N[lang][g][tid] for g in ("label", "question", "sublabel")]
        en = {e["key"]: e for e in R.reasons_directory("en")["reasons"]}[tid]
        strings += [en["label"], en["question"], en["sublabel"]]
    strings += [R._HINGLISH_LABELS[t] for t in CT.TYPE_ORDER]
    for lang in LANGS:
        strings += [t["label"] for t in CT.types_directory(lang)]
    assert len(strings) > 100
    for s in strings:
        assert not JARGON.search(s), s


# ── 5. compat_type_label on the reads ────────────────────────────────────────

def test_label_for_handles_every_stored_value():
    assert R.label_for("advisor", "en") == "Advisor or mentor"
    assert R.label_for("Advisor", "es") == "Asesor o mentor"
    assert R.label_for("boss-or-manager", "pt") == "Alguém a quem eu reporto"
    # legacy values already in the database
    assert R.label_for("relationship", "en") == "Romantic partner"
    assert R.label_for("marriage", "en") == "My husband or wife"
    assert R.label_for("mentor", "es") == "Asesor o mentor"
    # Hindi falls back to English, Hinglish is its own
    assert R.label_for("friend", "hi") == "Friend"
    assert R.label_for("friend", "hinglish") == "Dost"
    # unknown / empty never leaks an id with hyphens or underscores
    assert R.label_for("some_new-type", "en") == "Some new type"
    assert R.label_for(None, "en") == ""
    assert R.label_for("", "es") == ""


class _Rows:
    """Fluent stand-in for a supabase query: any chain ends in the same rows."""
    def __init__(self, rows):
        self.data = rows

    def __getattr__(self, name):
        return lambda *a, **k: self

    def execute(self):
        return self


class _FakeSB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _Rows(self.tables.get(name, []))


def test_network_returns_a_label_next_to_the_type(monkeypatch):
    import main
    sessions = [
        {"id": "s1", "chart_id_b": "p1", "name_b": "Dev", "compat_type": "employee", "score": 80, "created_at": "2026-10-01"},
        {"id": "s2", "chart_id_b": "p1", "name_b": "Dev", "compat_type": "friend", "score": 55, "created_at": "2026-09-01"},
        {"id": "s3", "chart_id_b": "p2", "name_b": "Asha", "compat_type": "relationship", "score": 40, "created_at": "2026-08-01"},
    ]
    monkeypatch.setattr(main, "supabase", _FakeSB({"compatibility_sessions": sessions, "chart_connections": [
        {"session_id": "s1", "score_breakdown": {"position": "CTO"}}]}))
    monkeypatch.setattr(main, "_network_today_glance", lambda cid, lang: {"available": True})
    monkeypatch.setattr(main, "_connection_notes_bulk", lambda a, ids: {})
    en = main.get_network("chart-a", "en")
    p1, p2 = en["people"]
    # existing fields untouched, label added beside them
    assert p1["primary"]["compat_type"] == "employee" and p1["primary"]["compat_type_label"] == "Someone reporting to me"
    assert p1["primary"]["position"] == "CTO" and "position" not in p1["relationships"][1]
    assert [r["compat_type_label"] for r in p1["relationships"]] == ["Someone reporting to me", "Friend"]
    assert "position" not in p2["primary"]
    assert p1["primary"]["score"] == 80 and p1["primary"]["badge"] == "FLOW"
    assert p2["primary"]["compat_type"] == "relationship"
    assert p2["primary"]["compat_type_label"] == "Romantic partner"
    es = main.get_network("chart-a", "es")["people"]
    assert es[0]["primary"]["compat_type_label"] == "Alguien que me reporta"
    hg = main.get_network("chart-a", "hinglish")["people"]
    assert hg[0]["relationships"][1]["compat_type_label"] == "Dost"
    hi = main.get_network("chart-a", "hi")["people"]
    assert hi[0]["primary"]["compat_type_label"] == "Someone reporting to me"
    assert set(en["people"][0]) >= {"connection_chart_id", "name", "relationships", "primary", "today", "note"}


def test_session_reads_return_a_label(monkeypatch):
    import asyncio
    import main
    row = {"id": "s1", "chart_id_a": "a", "chart_id_b": None, "name_a": "Asha", "name_b": "Dev",
           "compat_type": "mother", "score": 70, "current_layer": 1, "created_at": "2026-10-01",
           "has_time_a": True, "has_time_b": True}
    monkeypatch.setattr(main, "supabase", _FakeSB({"compatibility_sessions": [row], "chart_connections": [
        {"session_id": "s1", "score_breakdown": {"position": "Assistant"}}]}))
    monkeypatch.setattr(main, "_connection_note_get", lambda a, b: {"note": ""})
    out = asyncio.run(main.get_compatibility_session("s1", "es"))
    assert out["compat_type"] == "mother" and out["compat_type_label"] == "Mi madre"
    assert out["position"] == "Assistant"
    lst = main.list_compatibility_sessions("a", "pt")["sessions"]
    assert lst[0]["compat_type"] == "mother" and lst[0]["compat_type_label"] == "Minha mãe"
    assert lst[0]["position"] == "Assistant"
    assert main.list_compatibility_sessions("a")["sessions"][0]["compat_type_label"] == "My mother"
