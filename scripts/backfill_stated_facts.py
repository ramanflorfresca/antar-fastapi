"""Backfill life facts people STATED in past Ask questions into EMPTY chart fields.

[stated-facts backfill 2026-10-03] Owner: "this logic needs to be applicable to
all profiles, all messages, all users". The understanding layer now saves what
people say about themselves (work status, past work, how they earn, relationship,
children) — but only from new messages. This reads each user's past questions
that contain a self-statement, runs the same evidence-checked understanding on
them, and writes ONLY into fields that are still empty (a deliberate value
always wins; the latest statement wins between messages).

    venv311/bin/python scripts/backfill_stated_facts.py            # dry run
    venv311/bin/python scripts/backfill_stated_facts.py --apply    # write
    venv311/bin/python scripts/backfill_stated_facts.py -v         # show every stated fact
"""
import asyncio, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import main  # noqa: E402
from antar_engine import profile_harvest as ph  # noqa: E402

SELF = re.compile(r"(?i)\b(i am|i'm|im|i was|i work|i worked|my (job|business|wife|husband|partner|kids?|"
                  r"children|son|daughter|boss|company|startup)|i (have|had|lost|run|own|earn)|we (have|are|just)|"
                  r"soy|estoy|trabajo|tengo|mi (esposa|esposo|negocio|trabajo)|eu sou|estou|trabalho|tenho|"
                  r"meu|minha|main\b|mera|meri)\b")
FIELDS = "id,user_id,name,career_stage,profession,life_work,marital_status,children_status"


async def run(apply: bool):
    sb = main.supabase
    charts = {c["id"]: c for c in sb.table("charts").select(FIELDS).is_("deleted_at", "null")
              .not_.is_("user_id", "null").execute().data}
    rows, off = [], 0
    while True:
        b = sb.table("chat_messages").select("chart_id,question,created_at").order("created_at") \
            .range(off, off + 999).execute().data or []
        rows += b
        off += 1000
        if len(b) < 1000:
            break
    plan = {}
    todo = [r for r in rows if r["chart_id"] in charts and SELF.search((r.get("question") or "").strip())]
    print(f"questions: {len(rows)} | self-statements on account charts: {len(todo)}")
    for r in rows:
        c = charts.get(r["chart_id"])
        q = (r.get("question") or "").strip()
        if not c or not SELF.search(q):
            continue
        u = await main._nlu_read(q, None)
        if not u:
            print("   (no reading)", q[:60])
            continue
        sf = {k: v for k, v in (u.get("stated_facts") or {}).items() if v}
        if sf and "-v" in sys.argv:
            print(f"   [{c['id'][:8]}] {q[:70]!r} -> {sf}")
        row = dict(c, **{k: v["value"] for k, v in plan.get(c["id"], {}).items()})
        captured = []
        ph_apply = ph.apply_harvest
        ph.apply_harvest = lambda s, cid, facts: captured.append(facts) or {}
        try:
            main._ask_harvest_stated(c["id"], dict(c), u)      # empty-only, evidence-checked
        finally:
            ph.apply_harvest = ph_apply
        for facts in captured:
            for k, v in facts.items():
                plan.setdefault(c["id"], {})[k] = dict(v, said=q[:90])   # latest wins
    for cid, facts in plan.items():
        print(f"\n{charts[cid].get('name') or '(unnamed)'} [{cid[:8]}]")
        for k, v in facts.items():
            print(f"   {k:16s} ← {v['value']!r}   (said: \"{v['said']}\")")
        if apply:
            res = ph.apply_harvest(sb, cid, {k: {"value": v["value"], "evidence": "backfill"} for k, v in facts.items()})
            print("   written:", res.get("written"), "skipped:", res.get("skipped"))
    print(f"\n{'APPLIED' if apply else 'DRY RUN'}: {len(plan)} charts, "
          f"{sum(len(f) for f in plan.values())} fields")


asyncio.run(run("--apply" in sys.argv))
