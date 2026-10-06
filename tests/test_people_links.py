"""Relationship Integration Engine phase 1: people_links helpers, /api/v1/people
endpoints (against a fake DB, no network), resolver reading person_links, and the
backfill script. main.py is imported once; supabase / identity / compat are faked."""
import asyncio
import itertools
import os
import sys

import pytest
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from antar_engine import people_links as PL  # noqa: E402
from antar_engine.ask_subject import resolve_subject  # noqa: E402

_ids = itertools.count(1)


class _Q:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.op, self.filters, self.payload, self._range = "select", [], None, None

    def select(self, *a, **k): return self
    def limit(self, *a): return self
    def order(self, *a, **k): return self
    def single(self): return self
    def range(self, a, b): self._range = (a, b); return self
    def eq(self, c, v): self.filters.append(("eq", c, v)); return self
    def in_(self, c, v): self.filters.append(("in", c, list(v))); return self
    def ilike(self, c, v): return self
    def insert(self, p): self.op, self.payload = "insert", p; return self
    def update(self, p): self.op, self.payload = "update", p; return self
    def delete(self): self.op = "delete"; return self

    def _match(self, row):
        for kind, c, v in self.filters:
            if kind == "eq" and row.get(c) != v: return False
            if kind == "in" and row.get(c) not in v: return False
        return True

    def execute(self):
        rows = self.db.tables.setdefault(self.name, [])
        if self.op == "insert":
            ps = self.payload if isinstance(self.payload, list) else [self.payload]
            out = []
            for p in ps:
                r = dict(p)
                r.setdefault("id", f"{self.name[:2]}{next(_ids)}")
                if self.name == "person_links" and not r.get("ended_at") and any(
                        x["owner_chart_id"] == r["owner_chart_id"]
                        and x["person_chart_id"] == r["person_chart_id"]
                        and not x.get("ended_at") for x in rows):
                    raise RuntimeError("duplicate key person_links_current_uq")
                rows.append(r); out.append(dict(r))
            return type("R", (), {"data": out})()
        hit = [r for r in rows if self._match(r)]
        if self.op == "update":
            for r in hit: r.update(self.payload)
        elif self.op == "delete":
            self.db.tables[self.name] = [r for r in rows if r not in hit]
        data = [dict(r) for r in hit]
        if self._range:
            data = data[self._range[0]:self._range[1] + 1]
        return type("R", (), {"data": data})()


class FakeDB:
    def __init__(self, tables=None): self.tables = tables or {}
    def table(self, name): return _Q(self, name)
    def rows(self, t): return self.tables.get(t, [])


def _base_db():
    return FakeDB({"charts": [
        {"id": "OWN", "user_id": "u1", "name": "Raman", "first_name": "Raman"},
        {"id": "OTHER", "user_id": "u2", "name": "Eve", "first_name": "Eve"},
    ]})


# ── pure helpers ─────────────────────────────────────────────────────────────
def test_normalise_relation_enum():
    n = PL.normalise_relation
    assert n("son") == ("child", "son") and n("daughter") == ("child", "daughter")
    assert n("husband") == ("spouse", "husband") and n("wife") == ("spouse", "wife")
    assert n("girlfriend") == ("romantic", "girlfriend") and n("boyfriend") == ("romantic", "boyfriend")
    assert n("partner") == ("romantic", "partner")
    assert n("mother") == ("parent", "mother") and n("father") == ("parent", "father")
    assert n("brother") == ("sibling", "brother") and n("sister") == ("sibling", "sister")
    assert n("manager") == ("boss", "manager") and n("boss") == ("boss", "boss")
    assert n("employee") == ("employee", "employee") and n("report") == ("employee", "report")
    assert n("romantic", "girlfriend") == ("romantic", "girlfriend")
    assert n("child") == ("child", None) and n("cofounder") == ("cofounder", None)
    assert n("co-founder") == ("cofounder", None) and n("friend") == ("friend", None)
    assert n("boss-or-manager") == ("boss", None)
    assert n("nonsense") is None and n("") is None


def test_every_relation_maps_to_a_real_compat_type():
    from antar_engine import compatibility_reasons as R
    for rel in PL.RELATIONS:
        assert PL.relation_to_compat_type(rel) in R.REASON_DEFINITIONS


def test_compat_type_to_relation_backfill_map():
    f = PL.compat_type_to_relation
    assert f("marriage") == "spouse" and f("family") == "family" and f("partner") == "romantic"
    assert f("relationship") == "romantic" and f("cofounder") == "cofounder"
    assert f("boss-or-manager") == "boss" and f("business") == "business" and f(None) is None


def test_build_aliases_name_first_name_nicknames():
    a = PL.build_aliases("Amik Singh", ["Beta", "amik"])
    assert [x["alias"] for x in a] == ["Amik Singh", "Amik", "Beta"]
    assert [x["source"] for x in a] == ["name", "name", "user"]
    assert all(x["alias_norm"] for x in a)


# ── db helpers ───────────────────────────────────────────────────────────────
def test_change_relation_ends_old_row_and_inserts_current():
    db = FakeDB()
    link, _ = PL.create_link(db, "OWN", "P", "romantic", "girlfriend")
    new, changed = PL.change_relation(db, link["id"], "spouse", "wife")
    assert changed and new["relation"] == "spouse"
    rows = db.rows("person_links")
    old = [r for r in rows if r["id"] == link["id"]][0]
    assert old["ended_at"] and old["ended_reason"] == "changed"
    assert [r for r in rows if not r.get("ended_at")][0]["relation"] == "spouse"
    again, changed2 = PL.change_relation(db, new["id"], "spouse", "wife")
    assert not changed2 and len(db.rows("person_links")) == 2


# ── resolver ─────────────────────────────────────────────────────────────────
def _kids(son_g="male", dau_g="female"):
    return [
        {"chart_id_b": "S", "name_b": "Amik", "compat_type": "child", "relation": "child",
         "relation_detail": "son", "gender": son_g, "aliases": ["Amik", "Ami"]},
        {"chart_id_b": "D", "name_b": "Priya", "compat_type": "child", "relation": "child",
         "relation_detail": "daughter", "gender": dau_g, "aliases": ["Priya"]},
    ]


def test_two_children_my_son_resolves_only_the_son():
    r = resolve_subject("when will my son get married", "me", _kids())
    assert r["subject"] == "person" and r["person"]["chart_id"] == "S"
    r = resolve_subject("when will my daughter get married", "me", _kids())
    assert r["person"]["chart_id"] == "D"


def test_two_children_my_kid_clarifies():
    for q in ("how is my kid doing", "when will my child get married"):
        r = resolve_subject(q, "me", _kids())
        assert r["subject"] == "ambiguous" and len(r["candidates"]) == 2


def test_gender_comes_from_person_chart_when_detail_missing():
    ppl = _kids()
    for p in ppl:
        p.pop("relation_detail")
    r = resolve_subject("how is my son doing", "me", ppl)
    assert r["person"]["chart_id"] == "S"


def test_alias_nickname_resolves():
    ppl = _kids()
    ppl[0]["aliases"].append("Bunty")
    r = resolve_subject("how is Bunty doing", "me", ppl)
    assert r["subject"] == "person" and r["person"]["chart_id"] == "S"


def test_load_people_none_without_links_then_legacy_fallback():
    db = FakeDB({"charts": [], "chart_connections": [
        {"chart_id_a": "me", "chart_id_b": "K", "name_b": "Amik", "compat_type": "child"}]})
    assert PL.load_people_for_ask(db, "me") is None   # caller falls back to chart_connections
    import main
    old = main.supabase
    main.supabase = db
    try:
        ppl = main._ask_load_people_sync("me")
    finally:
        main.supabase = old
    assert [(p["chart_id_b"], p["name_b"], p["compat_type"]) for p in ppl] == [("K", "Amik", "child")]
    assert resolve_subject("when will my son get married", "me", ppl)["person"]["chart_id"] == "K"


def test_load_people_links_plus_unlinked_legacy_and_skips_ended():
    db = FakeDB({
        "charts": [{"id": "S", "name": "Amik", "gender": "male"},
                   {"id": "X", "name": "Old", "gender": None}],
        "person_links": [
            {"id": "l1", "owner_chart_id": "me", "person_chart_id": "S", "relation": "child",
             "relation_detail": "son", "ended_at": None},
            {"id": "l2", "owner_chart_id": "me", "person_chart_id": "X", "relation": "friend",
             "relation_detail": None, "ended_at": "2026-01-01"}],
        "person_aliases": [{"id": "a1", "owner_chart_id": "me", "person_chart_id": "S",
                            "alias": "Bunty", "alias_norm": "bunti", "source": "user"}],
        "chart_connections": [
            {"chart_id_a": "me", "chart_id_b": "X", "name_b": "Old", "compat_type": "friend"},
            {"chart_id_a": "me", "chart_id_b": "Z", "name_b": "Zed", "compat_type": "friend"}]})
    ppl = PL.load_people_for_ask(db, "me")
    ids = {p["chart_id_b"] for p in ppl}
    assert ids == {"S", "Z"}          # X has a link row (ended) so legacy X is NOT resurrected
    s = [p for p in ppl if p["chart_id_b"] == "S"][0]
    assert s["aliases"] == ["Bunty"] and s["gender"] == "male" and s["compat_type"] == "child"


# ── endpoints ────────────────────────────────────────────────────────────────
@pytest.fixture
def api(monkeypatch):
    import main
    db = _base_db()
    calls = []

    async def fake_compat(req, http_request=None):
        calls.append(req)
        cid = req.chart_id_b
        if not cid:  # create path: the real endpoint inserts the person chart
            existing = [c for c in db.rows("charts") if c.get("parent_chart_id") == req.chart_id_a
                        and c.get("name") == req.name_b and c.get("birth_date") == req.birth_date_b]
            if existing:
                cid = existing[0]["id"]
            else:
                cid = f"P{next(_ids)}"
                db.tables["charts"].append({
                    "id": cid, "user_id": None, "chart_type": "compatibility",
                    "parent_chart_id": req.chart_id_a, "name": req.name_b,
                    "birth_date": req.birth_date_b, "birth_time": req.birth_time_b,
                    "birth_city": req.birth_city_b, "gender": req.gender_b})
        score = 70 + len(calls)
        conns = db.tables.setdefault("chart_connections", [])
        conns[:] = [c for c in conns if not (c["chart_id_a"] == req.chart_id_a
                    and c["chart_id_b"] == cid and c["compat_type"] == req.compat_type)]
        conns.append({"chart_id_a": req.chart_id_a, "chart_id_b": cid, "name_b": req.name_b,
                      "compat_type": req.compat_type, "overall_score": score,
                      "verdict": "FLOW", "session_id": f"s{len(calls)}",
                      "score_breakdown": {"headline": f"h-{req.compat_type}"},
                      "updated_at": f"2026-10-06T00:00:{len(calls):02d}"})
        return {"score": score, "badge": "FLOW", "headline": f"h-{req.compat_type}",
                "compat_type": req.compat_type, "session_id": f"s{len(calls)}",
                "chart_id_b": cid}

    monkeypatch.setattr(main, "supabase", db)
    monkeypatch.setattr(main, "_st_identity",
                        lambda auth: (("u1", "a@b.c") if auth == "tok-u1"
                                      else ("u2", "e@b.c") if auth == "tok-u2" else (None, None)))
    monkeypatch.setattr(main, "compatibility_start", fake_compat)
    monkeypatch.setattr(main, "_purge_prashna_followups", lambda c: None)
    monkeypatch.setattr(main, "_purge_proxy_cache", lambda c: 0)
    monkeypatch.setattr(main, "_delete_rows_by", lambda t, c, v: None)
    return main, db, calls


def _run(coro):
    return asyncio.run(coro)


def _create(main, name="Amik Singh", relation="son", gender=None, bd="2012-05-01", auth="tok-u1",
            **kw):
    body = main.PersonCreateRequest(owner_chart_id="OWN", name=name, relation=relation,
                                    gender=gender, birth_date=bd, birth_time="10:30",
                                    birth_city="Denver", birth_country="US", **kw)
    return _run(main.people_create(body, auth))


def test_create_person_makes_link_aliases_and_score(api):
    main, db, calls = api
    out = _create(main, aliases=["Bunty"])
    assert out["relation"] == "child" and out["relation_detail"] == "son"
    assert out["gender"] == "male" and out["name"] == "Amik Singh"
    assert out["score"]["score"] and out["score"]["compat_type"] == "child"
    assert calls[0].gender_b == "male" and calls[0].compat_type == "child"
    chart = [c for c in db.rows("charts") if c["id"] == out["person_chart_id"]][0]
    assert chart["user_id"] is None and chart["chart_type"] == "compatibility"
    assert chart["parent_chart_id"] == "OWN" and chart["gender"] == "male"
    links = db.rows("person_links")
    assert len(links) == 1 and not links[0].get("ended_at")
    assert {a["alias"] for a in db.rows("person_aliases")} == {"Amik Singh", "Amik", "Bunty"}
    # GET returns it with the latest score summary
    got = _run(main.people_list("OWN", "tok-u1"))
    assert got["count"] == 1 and got["people"][0]["score"]["headline"] == "h-child"


def test_create_rejects_unknown_relation_and_non_owner(api):
    main, db, _ = api
    with pytest.raises(HTTPException) as e:
        _create(main, relation="nemesis")
    assert e.value.status_code == 422
    with pytest.raises(HTTPException) as e:
        _create(main, auth="tok-u2")          # signed in, but does not own OWN
    assert e.value.status_code == 404
    with pytest.raises(HTTPException) as e:
        _create(main, auth=None)
    assert e.value.status_code == 401
    assert db.rows("person_links") == []


def test_non_owner_cannot_read_edit_change_or_delete(api):
    main, db, _ = api
    link_id = _create(main)["link_id"]
    for fn in (lambda: main.people_list("OWN", "tok-u2"),
               lambda: main.people_edit(link_id, main.PersonEditRequest(name="X"), "tok-u2"),
               lambda: main.people_change_relation(
                   link_id, main.PersonRelationRequest(relation="friend"), "tok-u2"),
               lambda: main.people_add_alias(link_id, main.PersonAliasRequest(alias="x"), "tok-u2"),
               lambda: main.people_remove(link_id, "tok-u2")):
        with pytest.raises(HTTPException) as e:
            _run(fn())
        assert e.value.status_code == 404
    assert len(db.rows("person_links")) == 1 and not db.rows("person_links")[0].get("ended_at")


def test_change_relation_girlfriend_to_spouse_reruns_compat(api):
    main, db, calls = api
    out = _create(main, name="Leena Rao", relation="girlfriend")
    assert out["relation"] == "romantic" and out["relation_detail"] == "girlfriend"
    old_aliases = {a["alias"] for a in db.rows("person_aliases")}
    res = _run(main.people_change_relation(
        out["link_id"], main.PersonRelationRequest(relation="wife"), "tok-u1"))
    assert res["changed"] and res["relation"] == "spouse" and res["relation_detail"] == "wife"
    assert calls[-1].compat_type == "spouse" and calls[-1].chart_id_b == out["person_chart_id"]
    rows = db.rows("person_links")
    assert len(rows) == 2
    old = [r for r in rows if r["relation"] == "romantic"][0]
    assert old["ended_at"] and old["ended_reason"] == "changed"
    assert [r for r in rows if not r.get("ended_at")][0]["relation"] == "spouse"
    assert {a["alias"] for a in db.rows("person_aliases")} == old_aliases   # aliases persist
    # latest score only: GET returns the spouse score, never the romantic one
    got = _run(main.people_list("OWN", "tok-u1"))["people"]
    assert len(got) == 1 and got[0]["score"]["compat_type"] == "spouse"
    assert got[0]["score"]["headline"] == "h-spouse"
    # the ended link id is no longer addressable
    with pytest.raises(HTTPException):
        _run(main.people_change_relation(
            out["link_id"], main.PersonRelationRequest(relation="friend"), "tok-u1"))


def test_edit_birth_time_same_chart_no_duplicate(api, monkeypatch):
    main, db, calls = api
    out = _create(main)
    pid = out["person_chart_id"]
    recomputed = []

    async def fake_recompute(row, body):
        recomputed.append((row["id"], body.birth_time))
        db.tables["charts"] = [dict(c, birth_time=body.birth_time) if c["id"] == row["id"] else c
                               for c in db.rows("charts")]
        return {}
    monkeypatch.setattr(main, "_people_recompute_chart", fake_recompute)
    n_charts = len(db.rows("charts"))
    res = _run(main.people_edit(out["link_id"],
                                main.PersonEditRequest(birth_time="04:15"), "tok-u1"))
    assert res["recomputed"] and res["changed"]
    assert recomputed == [(pid, "04:15")]
    assert len(db.rows("charts")) == n_charts            # no duplicate chart
    assert res["person_chart_id"] == pid
    assert calls[-1].chart_id_b == pid                     # compat re-run on the SAME chart
    assert len(db.rows("person_links")) == 1


def test_edit_rename_resyncs_auto_aliases_keeps_nicknames(api):
    main, db, _ = api
    out = _create(main, aliases=["Bunty"])
    _run(main.people_edit(out["link_id"], main.PersonEditRequest(name="Amar Singh"), "tok-u1"))
    assert {a["alias"] for a in db.rows("person_aliases")} == {"Amar Singh", "Amar", "Bunty"}


def test_alias_add_delete(api):
    main, db, _ = api
    out = _create(main)
    res = _run(main.people_add_alias(out["link_id"], main.PersonAliasRequest(alias="Chhotu"), "tok-u1"))
    added = [a for a in res["aliases"] if a["alias"] == "Chhotu"][0]
    assert added["source"] == "user"
    _run(main.people_delete_alias(out["link_id"], added["id"], "tok-u1"))
    assert "Chhotu" not in {a["alias"] for a in db.rows("person_aliases")}
    with pytest.raises(HTTPException):
        _run(main.people_add_alias(out["link_id"], main.PersonAliasRequest(alias="  "), "tok-u1"))


def test_delete_purges_person_not_owner(api):
    main, db, _ = api
    out = _create(main)
    pid = out["person_chart_id"]
    res = _run(main.people_remove(out["link_id"], "tok-u1"))
    assert res["subchart_purged"] is True
    person = [c for c in db.rows("charts") if c["id"] == pid][0]
    assert person["deleted_at"] and person["name"] is None and person["birth_date"] is None
    owner = [c for c in db.rows("charts") if c["id"] == "OWN"][0]
    assert owner["name"] == "Raman" and not owner.get("deleted_at")
    assert db.rows("person_aliases") == []
    assert db.rows("chart_connections") == []
    link = db.rows("person_links")[0]
    assert link["ended_at"] and link["ended_reason"] == "removed"
    assert _run(main.people_list("OWN", "tok-u1"))["count"] == 0


def test_delete_keeps_chart_when_another_owner_still_links_it(api):
    main, db, _ = api
    out = _create(main)
    db.tables["person_links"].append({"id": "lx", "owner_chart_id": "OTHERCHART",
                                      "person_chart_id": out["person_chart_id"],
                                      "relation": "friend", "ended_at": None})
    res = _run(main.people_remove(out["link_id"], "tok-u1"))
    assert res["subchart_purged"] is False
    person = [c for c in db.rows("charts") if c["id"] == out["person_chart_id"]][0]
    assert not person.get("deleted_at")


def test_endpoints_do_not_block_the_loop_and_use_real_columns():
    src = open(os.path.join(os.path.dirname(__file__), "..", "antar_engine", "people_links.py")).read()
    # columns that exist in Antar.world/SQL_person_links.sql + charts/chart_connections
    for col in ("owner_chart_id", "person_chart_id", "relation_detail", "ended_reason",
                "alias_norm", "overall_score", "score_breakdown"):
        assert col in src


# ── backfill script ──────────────────────────────────────────────────────────
def test_backfill_dry_run_apply_and_idempotent():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import backfill_person_links as B
    db = FakeDB({
        "charts": [{"id": "A", "name": "Raman"}, {"id": "P1", "name": "Amik Singh"},
                   {"id": "P2", "name": "Gone", "deleted_at": "2026-01-01"},
                   {"id": "P3", "name": "Leena"}],
        "chart_connections": [
            {"id": 1, "chart_id_a": "A", "chart_id_b": "P1", "name_b": "Amik Singh",
             "compat_type": "marriage", "created_at": "2026-01-01", "updated_at": "2026-01-02"},
            {"id": 2, "chart_id_a": "A", "chart_id_b": "P2", "name_b": "Gone",
             "compat_type": "friend", "created_at": "2026-01-01"},
            {"id": 3, "chart_id_a": "A", "chart_id_b": "A", "name_b": "Self",
             "compat_type": "friend", "created_at": "2026-01-01"},
            {"id": 4, "chart_id_a": "A", "chart_id_b": "P3", "name_b": "Leena",
             "compat_type": None, "created_at": "2026-02-01"},
            {"id": 5, "chart_id_a": "A", "chart_id_b": "P1", "name_b": "Amik Singh",
             "compat_type": "family", "created_at": "2025-01-01", "updated_at": "2025-01-02"}],
        "compatibility_sessions": [
            {"chart_id_a": "A", "chart_id_b": "P3", "compat_type": "partner",
             "created_at": "2026-02-01"}],
    })
    plan = B.main(False, sb=db)                      # dry run writes nothing
    assert db.rows("person_links") == [] and db.rows("person_aliases") == []
    acts = {(r["person"], r["compat_type"]): (r["action"], r["reason"]) for r in plan}
    assert acts[("P1", "marriage")][0] == "create"
    assert acts[("P1", "family")][0] == "skip" and "older connection" in acts[("P1", "family")][1]
    assert "deleted" in acts[("P2", "friend")][1] and "owner == person" in acts[("A", "friend")][1]
    assert acts[("P3", "partner")][0] == "create"          # type recovered from the session
    B.main(True, sb=db)
    links = {(l["person_chart_id"]): l for l in db.rows("person_links")}
    assert set(links) == {"P1", "P3"}
    assert links["P1"]["relation"] == "spouse" and links["P3"]["relation"] == "romantic"
    assert links["P1"]["started_at"] == "2026-01-01"
    assert {a["alias"] for a in db.rows("person_aliases")
            if a["person_chart_id"] == "P1"} == {"Amik Singh", "Amik"}
    n_links, n_alias = len(db.rows("person_links")), len(db.rows("person_aliases"))
    plan2 = B.main(True, sb=db)                       # second run creates nothing
    assert len(db.rows("person_links")) == n_links and len(db.rows("person_aliases")) == n_alias
    assert not [r for r in plan2 if r["action"] == "create"]
