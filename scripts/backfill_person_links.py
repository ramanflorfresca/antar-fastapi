"""
Backfill person_links + person_aliases from chart_connections (Relationship Integration
Engine, phase 1 - Antar.world/SPEC_relationship_integration_engine.md section 6).

  owner  = chart_connections.chart_id_a
  person = chart_connections.chart_id_b
  relation = compat_type (the connection's, else the pair's latest compatibility_sessions row)
             marriage->spouse, partner->romantic, family->family, others keep
  started_at = chart_connections.created_at
  aliases = name_b + first name

Idempotent: a pair that already has a CURRENT link is skipped, existing aliases are not
re-inserted, so a second run creates nothing. DRY RUN by default.

    venv311/bin/python scripts/backfill_person_links.py            # dry run
    venv311/bin/python scripts/backfill_person_links.py --apply
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv  # noqa: E402

from antar_engine import people_links as PL  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv("/Users/ramandeepsinghchadha/antarai/.env")


def _rows(res):
    return list(getattr(res, "data", None) or [])


def _fetch_all(sb, table, cols, page=1000):
    out, start = [], 0
    while True:
        chunk = _rows(sb.table(table).select(cols).range(start, start + page - 1).execute())
        out += chunk
        if len(chunk) < page:
            return out
        start += page


def _charts_by_id(sb, ids):
    out, ids = {}, sorted(ids)
    for i in range(0, len(ids), 100):
        for r in _rows(sb.table("charts").select("id,name,first_name,deleted_at")
                       .in_("id", ids[i:i + 100]).execute()):
            out[r["id"]] = r
    return out


def build_plan(sb):
    """-> list of dicts {owner, person, name, compat_type, relation, started_at, action, reason}.
    action: 'create' | 'skip'."""
    conns = _fetch_all(sb, "chart_connections",
                       "id,chart_id_a,chart_id_b,name_b,compat_type,created_at,updated_at")
    sessions = _fetch_all(sb, "compatibility_sessions",
                          "chart_id_a,chart_id_b,compat_type,created_at")
    links = _fetch_all(sb, "person_links", "owner_chart_id,person_chart_id,ended_at")
    have_current = {(l["owner_chart_id"], l["person_chart_id"]) for l in links if not l.get("ended_at")}
    sess_type = {}
    for s in sorted(sessions, key=lambda s: str(s.get("created_at") or "")):
        if s.get("compat_type"):
            sess_type[(s["chart_id_a"], s["chart_id_b"])] = s["compat_type"]
    chart_ids = {c["chart_id_a"] for c in conns if c.get("chart_id_a")} | \
                {c["chart_id_b"] for c in conns if c.get("chart_id_b")}
    charts = _charts_by_id(sb, chart_ids)

    plan, seen = [], {}
    # newest connection per pair wins (it is the current relation); older types are skipped
    for c in sorted(conns, key=lambda c: str(c.get("updated_at") or c.get("created_at") or ""),
                    reverse=True):
        a, b = c.get("chart_id_a"), c.get("chart_id_b")
        ctype = c.get("compat_type") or sess_type.get((a, b))
        row = {"owner": a, "person": b, "name": (c.get("name_b") or "").strip(),
               "compat_type": ctype, "relation": PL.compat_type_to_relation(ctype),
               "started_at": c.get("created_at"), "action": "skip", "reason": ""}
        plan.append(row)
        if not a or not b:
            row["reason"] = "missing chart id"
        elif a == b:
            row["reason"] = "owner == person"
        elif a not in charts or charts[a].get("deleted_at"):
            row["reason"] = "owner chart missing/deleted"
        elif b not in charts or charts[b].get("deleted_at"):
            row["reason"] = "person chart missing/deleted"
        elif (a, b) in have_current:
            row["reason"] = "current link already exists"
        elif (a, b) in seen:
            row["reason"] = f"older connection for same pair (kept newest: {seen[(a, b)]})"
        elif not row["relation"]:
            row["reason"] = f"unmappable compat_type {ctype!r}"
        else:
            row["action"] = "create"
            if not row["name"]:
                ch = charts[b]
                row["name"] = (ch.get("name") or ch.get("first_name") or "").strip()
            seen[(a, b)] = ctype
    return plan


def alias_gap(sb, plan):
    """Aliases the already-linked pairs in this plan are missing (idempotent top-up)."""
    return [r for r in plan if r["action"] == "skip" and r["reason"] == "current link already exists"
            and r["name"]]


def apply_plan(sb, plan):
    created = aliases = 0
    gap = {id(r) for r in alias_gap(sb, plan)}
    for r in plan:
        if r["action"] == "create":
            row = {"owner_chart_id": r["owner"], "person_chart_id": r["person"],
                   "relation": r["relation"]}
            if r.get("started_at"):
                row["started_at"] = r["started_at"]
            sb.table("person_links").insert(row).execute()
            created += 1
            target = r
        elif id(r) in gap:
            target = r
        else:
            continue
        if target["name"]:
            aliases += len(PL.add_aliases(sb, target["owner"], target["person"],
                                          PL.build_aliases(target["name"])))
    return created, aliases


def main(apply: bool, sb=None):
    if sb is None:
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    plan = build_plan(sb)
    n_create = sum(1 for r in plan if r["action"] == "create")
    print(f"{'APPLY' if apply else 'DRY RUN'}: {len(plan)} chart_connections rows | "
          f"to create: {n_create} | skipped: {len(plan) - n_create}")
    print(f"{'action':7} {'owner':9} {'person':9} {'name':18} {'compat_type':16} {'relation':10} reason")
    for r in plan:
        print(f"{r['action']:7} {str(r['owner'])[:8]:9} {str(r['person'])[:8]:9} "
              f"{(r['name'] or '-')[:17]:18} {str(r['compat_type'])[:15]:16} "
              f"{str(r['relation'])[:9]:10} {r['reason']}")
    if apply:
        created, aliases = apply_plan(sb, plan)
        print(f"created {created} person_links, {aliases} person_aliases")
    else:
        print("dry run - pass --apply to write")
    return plan


if __name__ == "__main__":
    main("--apply" in sys.argv)
