"""[pair-view + working-agreement 2026-10-11] the redesigned connection screen's data, and the template working agreement."""
import asyncio
from datetime import date

import main
from antar_engine import pair_view as PV
from antar_engine import working_agreement as WA

TODAY = date(2026, 10, 11)


def _dashas(*lords):
    """AD rows at 0-6, 6-12 and 12-24 months from TODAY, one lord each."""
    rows = [{"level": "mahadasha", "lord_or_sign": "Rahu", "start_date": "2020-01-01", "end_date": "2036-01-01"}]
    spans = [("2026-09-01", "2027-02-28"), ("2027-03-01", "2027-10-31"), ("2027-11-01", "2029-06-30")]
    for lord, (s, e) in zip(lords, spans):
        rows.append({"level": "antardasha", "lord_or_sign": lord, "start_date": s, "end_date": e})
    return {"vimsottari": rows}


ROLES = {"kind": "partners", "you": {"leads": ["tech", "sales"]}, "other": {"leads": ["creative"]}, "shared": [], "contested": ["vision"],
         "gaps": ["ops"], "capacity": {"you": {"level": "capable"}, "other": {"level": "conditional"}, "solo": False}}
SESSION = {"name_b": "saransh Kumar", "compat_type": "cofounder", "roles": ROLES,
           "layers": [{"layer_key": "friction", "score": 79}, {"layer_key": "soul", "score": 57}, {"layer_key": "communication", "score": 23},
                      {"layer_key": "chemistry", "score": 40}, {"layer_key": "public", "score": 49}, {"layer_key": "lifepath", "score": 55}]}


# ---- pair view
def test_a_season_is_a_character_of_the_period_not_an_event():
    s = PV.seasons_for(_dashas("Rahu", "Rahu", "Saturn"), TODAY, "en")
    assert [x["label"] for x in s] == ["Push forward", "Push forward", "Build structure"] and [x["group"] for x in s] == ["out", "out", "in"]
    es = PV.seasons_for(_dashas("Saturn", "Jupiter", "Ketu"), TODAY, "es")
    assert [x["label"] for x in es] == ["Construir estructura", "Crecer y enseñar", "Soltar y afinar"]
    assert PV.seasons_for({}, TODAY) is None                                                          # no timing on file -> no seasons
    assert [x["label"] for x in PV.seasons_for(_dashas("Rahu", "Rahu"), TODAY)][2] == "Push forward"    # a missing sub-period falls back to the main period's lord


def test_sync_is_outward_versus_inward_and_the_summary_says_who_sets_the_pace():
    r = PV.build(SESSION, _dashas("Rahu", "Rahu", "Rahu"), _dashas("Saturn", "Saturn", "Rahu"), "en", TODAY)
    assert r["seasons"]["in_sync"] == [False, False, True]
    assert r["seasons"]["summary"] == "Your seasons differ at times. Name who sets the pace when they do."
    allout = PV.build(SESSION, _dashas("Rahu", "Rahu", "Rahu"), _dashas("Saturn", "Saturn", "Saturn"), "en", TODAY)
    assert allout["seasons"]["summary"] == "You are in a more outward season while saransh is in a more inward one. Decide early who sets the pace."
    flip = PV.build(SESSION, _dashas("Saturn", "Saturn", "Saturn"), _dashas("Rahu", "Rahu", "Rahu"), "en", TODAY)
    assert flip["seasons"]["summary"] == "saransh is in a more outward season while you are in a more inward one. Decide early who sets the pace."
    same = PV.build(SESSION, _dashas("Rahu", "Mars", "Sun"), _dashas("Rahu", "Mars", "Sun"), "en", TODAY)
    assert same["seasons"]["in_sync"] == [True, True, True] and "line up" in same["seasons"]["summary"]


def test_missing_timing_is_said_plainly_never_guessed():
    r = PV.build(SESSION, _dashas("Rahu", "Rahu", "Rahu"), {}, "en", TODAY)
    assert r["seasons"]["in_sync"] is None and r["seasons"]["other"] is None and "saransh" in r["seasons"]["summary"] and "not on file" in r["seasons"]["summary"]


def test_tiles_and_lanes_come_from_the_reading():
    r = PV.build(SESSION, _dashas("Rahu", "Rahu", "Rahu"), _dashas("Saturn", "Saturn", "Rahu"), "en", TODAY)
    assert r["tiles"]["flows"] == {"state": "flows", "text": "Friction is low"} and r["tiles"]["open"] == {"n": 2, "text": "2 areas to decide"}
    assert r["tiles"]["care"]["areas"] == ["communication", "chemistry", "public"] and "communication and trust" in r["tiles"]["care"]["text"]
    owners = {l["lane"]: l["owner"] for l in r["lanes"]}
    assert owners == {"tech": "you", "ops": "open", "sales": "you", "vision": "open", "finance": "shared", "creative": "other"}
    hier = PV.build({**SESSION, "roles": {"kind": "hierarchy", "you": {}, "other": {}}}, _dashas("Rahu", "Rahu", "Rahu"), _dashas("Saturn", "Saturn", "Rahu"), "en", TODAY)
    assert hier["lanes"] == [] and hier["tiles"]["open"]["text"] == "Every area has an owner"


def test_pair_view_strings_have_no_chart_words():
    import re
    r = PV.build(SESSION, _dashas("Rahu", "Rahu", "Rahu"), _dashas("Saturn", "Saturn", "Rahu"), "en", TODAY)
    blob = str(r["tiles"]) + str(r["seasons"]["summary"]) + str([x["label"] for x in r["seasons"]["you"] + r["seasons"]["other"]])
    assert not re.search(r"(?i)\b(rahu|saturn|dasha|house|chart|planet|karaka)\b", blob)


# ---- working agreement
def _doc(kind="cofounder", lang="en", roles=ROLES):
    return WA.build(kind, roles, lang, {"a": "Raman", "b": "saransh"})


def test_only_partner_types_get_a_template_and_it_says_it_is_not_legal():
    assert _doc("cofounder") and _doc("business")
    for k in ("employee", "boss", "advisor", "friend", "", None):
        assert WA.build(k, ROLES) is None
    assert WA.build("cofounder", None) is None and WA.build("cofounder", {"kind": "hierarchy", "you": {}, "other": {}}) is None
    d = _doc()
    assert "not a legal agreement" in d["disclaimer"] and "not legal advice" in d["disclaimer"] and "template, not a legal agreement" in d["footer"]
    assert "not a legal agreement" in d["markdown"]


def test_everything_personal_or_legal_is_blank_and_names_are_only_hints():
    d = _doc()
    items = {it["key"]: it for s in d["sections"] for it in s["items"] if it.get("key")}
    for k in ("party_a_name", "party_a_id", "party_a_address", "party_b_name", "party_b_id", "party_b_address", "effective_date", "venture_name", "equity", "vesting",
              "pay", "expenses", "ip_owner", "confidentiality", "exit_terms", "review_date", "sig_a_sign", "sig_b_sign", "spend_limit", "hours_a", "hours_b"):
        assert items[k]["value"] == "", k
    assert d["name_hints"] == {"party_a": "Raman", "party_b": "saransh"}
    assert "Raman" not in d["markdown"] and "saransh" not in d["markdown"]            # the document itself carries no names
    assert d["markdown"].count("________") >= 20


def test_roles_and_responsibilities_are_filled_from_the_reading():
    d = _doc()
    roles = next(s for s in d["sections"] if s["id"] == "roles")["items"]
    a = [i for i in roles if i.get("type") == "clause" and i["id"].startswith("role_a_")]
    b = [i for i in roles if i.get("type") == "clause" and i["id"].startswith("role_b_")]
    assert [c["title"] for c in a] == ["technology & product", "sales & clients"] and [c["title"] for c in b] == ["creative & brand"]
    assert all(len(c["text"].split("\n")) == 3 and c["source"] == "reading" for c in a + b)
    owners = [i for i in roles if i.get("type") == "choice"]
    assert {i["key"] for i in owners} == {"owner_vision", "owner_ops"} and all(i["value"] == "" and "Shared" in i["options"] for i in owners)
    assert any(i.get("id") == "gaps" for i in roles)                                   # nobody owns operations: said, and left to assign


def test_a_solo_builder_adds_the_narrow_scope_clause():
    solo = {**ROLES, "capacity": {"solo": True}}
    d = _doc(roles=solo)
    assert any(i.get("id") == "solo" for s in d["sections"] for i in s["items"])
    assert not any(i.get("id") == "solo" for s in _doc()["sections"] for i in s["items"])


def test_edits_merge_over_the_template_and_clauses_can_be_rewritten():
    d = _doc()
    merged = WA.apply_values(d, {"party_a_name": "A. Founder", "cadence": "Fortnightly", "clause_text:dec_own": "Owners decide, and tell the other the same day.",
                                 "equity": "50/50, 4-year vest"})
    items = {it["key"]: it for s in merged["sections"] for it in s["items"] if it.get("key")}
    assert items["party_a_name"]["value"] == "A. Founder" and items["cadence"]["value"] == "Fortnightly" and items["equity"]["value"] == "50/50, 4-year vest"
    assert items["clause_text:dec_own"]["text"] == "Owners decide, and tell the other the same day." and items["clause_text:dec_own"]["edited"] is True
    assert "A. Founder" in merged["markdown"] and "Owners decide, and tell the other the same day." in merged["markdown"]
    assert WA.apply_values(d, {}) is d and WA.apply_values(d, None) is d


def test_values_are_cleaned_and_bounded():
    v = WA.clean_values({"party_a_name": "x" * 9000, "Bad Key!": "y", "ok_key": 5, "clause_text:a": "z"})
    assert list(v) == ["party_a_name", "clause_text:a"] and len(v["party_a_name"]) == 4000 and WA.clean_values("nope") == {}
    assert len(WA.clean_values({f"k{i}": "v" for i in range(500)})) == 200


def test_spanish_template_is_native_and_blank_in_the_same_places():
    d = _doc(lang="es")
    assert d["title"] == "Acuerdo de trabajo (plantilla)" and "no es un acuerdo legal" in d["disclaimer"].lower()
    for en in ("Party A", "Full name", "Roles and", "Equity", "Signature", "Review this"):
        assert en not in d["markdown"], en
    assert "Estructura de participación: ________" in d["markdown"] and "Lleva la hoja de ruta" in d["markdown"]


def test_markdown_is_well_formed():
    md = _doc()["markdown"]
    assert md.startswith("# Working agreement (template)") and md.rstrip().endswith("_A template, not a legal agreement. Have a lawyer review before relying on it._")
    assert "\n\n## 1. Parties\n" in md and "- Full name: ________" in md and "**technology & product**\n- Owns the product roadmap" in md


def test_storage_is_fail_open_and_keeps_the_edit_in_memory():
    class Boom:
        def table(self, n):
            raise RuntimeError("no table")
    WA._MEM.clear()
    assert WA.save_values(Boom(), "s1", "en", {"a": "b"}) is False
    assert WA.load_values(Boom(), "s1", "en") == {"a": "b"} and WA.load_values(Boom(), "s2", "en") == {}


def test_endpoints_return_the_template_merge_edits_and_404_other_types(monkeypatch):
    from fastapi import HTTPException

    async def fake_session(sid, lang="en"):
        return dict(SESSION, name_a="Raman", compat_type=("cofounder" if sid == "p" else "friend"), roles=(ROLES if sid == "p" else None))
    monkeypatch.setattr(main, "get_compatibility_session", fake_session)
    WA._MEM.clear()

    class Boom:
        def table(self, n):
            raise RuntimeError("no table")
    monkeypatch.setattr(main, "supabase", Boom())
    doc = asyncio.run(main.get_connection_agreement("p", "en"))
    assert doc["title"] == "Working agreement (template)"
    saved = asyncio.run(main.save_connection_agreement("p", main._AgreementSave(values={"equity": "TBD", "bad key": "x"}, language="en")))
    assert saved["saved"] is False
    items = {it["key"]: it for s in saved["sections"] for it in s["items"] if it.get("key")}
    assert items["equity"]["value"] == "TBD"
    md = asyncio.run(main.get_connection_agreement("p", "en", "markdown"))
    assert md.media_type.startswith("text/markdown") and b"TBD" in md.body and b"attachment" in md.headers["content-disposition"].encode()
    try:
        asyncio.run(main.get_connection_agreement("other", "en"))
        raise AssertionError("expected 404")
    except HTTPException as e:
        assert e.status_code == 404 and e.detail["error"] == "no_template"
