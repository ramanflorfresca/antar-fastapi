"""Relationship question audit — runs the 55 love/relationship/marriage questions
(tests/data/relationship_questions.py) through the real /ask and checks each answer against the
LANE it should be handled in (serve / pattern / reframe / people / decline). Same harness and stubs
as conversation_audit.py: nothing is sent or saved. Writes Antar.world/answer_audit/relq_<stamp>.md + .json.

    venv311/bin/python scripts/relationship_question_audit.py [--persona Raman] [--lane decline] [--ids 22,24] [--repeats 1]

Deterministic only (no judge): the point is to measure how Ask treats third-party questions today and to
give the relationship_season work a regression bar. Findings are CLASSES, fixed by root cause.
"""
import argparse, asyncio, builtins, contextvars, datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import conversation_audit as ca  # noqa: E402  (loads .env, imports main, defines ask/PERSONAS/turn_checks)
from tests.data.relationship_questions import QUESTIONS  # noqa: E402
from tests.data.relationship_lane_checks import lane_checks, template_reuse  # noqa: E402

main = ca.main
_CUR = contextvars.ContextVar("relq_buf", default=None)
_orig_print = builtins.print


def _print(*a, **k):   # capture the concern the pipeline settled on (same trick as routing_audit.py)
    buf = _CUR.get()
    if buf is not None:
        buf.append(" ".join(str(x) for x in a))
    _orig_print(*a, **k)
async def run(personas, items, repeats):
    async def nop(*a, **k):
        return None
    main._ask_persist = nop
    main._nlu_shadow = nop
    main._ask_harvest_stated = lambda *a, **k: None
    main._ask_recent_thread = ca._thread_for
    import antar_engine.outcomes as oc
    oc.record_claim = lambda *a, **k: None
    builtins.print = _print
    sem = asyncio.Semaphore(4)

    async def one(persona, item, rep):
        async with sem:
            buf = []
            _CUR.set(buf)
            try:
                p = await ca.ask(persona, item["q"], [])   # fresh thread per question
                m = re.findall(r"\[ask\] concern=(\w+)", "\n".join(buf))
                p["concern"] = m[-1] if m else None
            except Exception as e:
                return {"persona": persona["name"], "rep": rep, **item, "issues": ["ERROR"], "error": f"{type(e).__name__}: {e}"[:200]}
            return {"persona": persona["name"], "rep": rep, **item, "concern": p.get("concern"),
                    "verdict": p.get("verdict"), "timing": p.get("timing"), "reframed": p.get("reframed"), "people_pointer": p.get("people_pointer"), "needs_clarification": p.get("needs_clarification"),
                    "read": (p.get("read") or "").strip(), "next": (p.get("next") or "").strip(),
                    "issues": lane_checks(item, p)}
    return await asyncio.gather(*[one(pe, it, r) for pe in personas for it in items for r in range(repeats)])


def report(rows: list, stamp: str) -> str:
    for opening, ids in template_reuse(rows).items():
        for r in rows:
            _body = re.sub(r"^\s*(?:likely|probable|possible|yes|no|not yet|unlikely)\s*[—-][^.\n]*\.\s*", "", r.get("read") or "", flags=re.I)
            if r["id"] in ids and not (r.get("people_pointer") or r.get("needs_clarification")) and re.sub(r"\W+", " ", _body[:70].lower()).strip() == opening:
                r["issues"] = r["issues"] + ["TEMPLATE_REUSE"]
    n = len(rows)
    bad = [r for r in rows if r["issues"]]
    L = [f"# Relationship question audit {stamp}", "", f"{n} answers, {len(bad)} with findings "
         f"({100 * len(bad) // max(n, 1)}%).", "", "## By lane (answers / flagged)", "", "| lane | answers | flagged | top classes |", "|---|---|---|---|"]
    for lane in ("serve", "pattern", "reframe", "people", "decline"):
        rs = [r for r in rows if r["lane"] == lane]
        cls = {}
        for r in rs:
            for i in r["issues"]:
                cls[i] = cls.get(i, 0) + 1
        top = ", ".join(f"{k}×{v}" for k, v in sorted(cls.items(), key=lambda kv: -kv[1])[:4]) or "—"
        L.append(f"| {lane} | {len(rs)} | {sum(1 for r in rs if r['issues'])} | {top} |")
    L += ["", "## Classes (most frequent first)", ""]
    cls = {}
    for r in rows:
        for i in r["issues"]:
            cls.setdefault(i, []).append(r)
    for k, rs in sorted(cls.items(), key=lambda kv: -len(kv[1])):
        L.append(f"- **{k}** ×{len(rs)} — ids " + ", ".join(sorted({str(r['id']) for r in rs}, key=int)))
    L += ["", "## Flagged answers", ""]
    for r in sorted(bad, key=lambda r: (r["id"], r["persona"])):
        L += [f"### #{r['id']} [{r['lane']}] {r['q']}  — {r['persona']} (rep {r['rep']})", f"issues: {', '.join(r['issues'])} · concern: {r.get('concern')} · timing: {r.get('timing')}",
              "", "> " + (r.get("read") or r.get("error") or "")[:700].replace("\n", " "), ""]
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", action="append", help="default: Raman, Andres, Harleen")
    ap.add_argument("--lane")
    ap.add_argument("--ids", help="comma list of question ids")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--rescore", help="re-apply the checks to a saved relq_*.json (no LLM calls)")
    a = ap.parse_args()
    names = a.persona or ["Raman", "Andres", "Harleen"]
    ps = [p for p in ca.PERSONAS if p["name"] in names]
    ids = {int(x) for x in (a.ids or "").split(",") if x.strip()}
    items = [q for q in QUESTIONS if (not a.lane or q["lane"] == a.lane) and (not ids or q["id"] in ids)]
    if a.rescore:
        rows = json.load(open(a.rescore))
        for r in rows:
            r["issues"] = lane_checks(r, r)
    else:
        rows = asyncio.run(run(ps, items, a.repeats))
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M")
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Antar.world", "answer_audit")
    os.makedirs(outdir, exist_ok=True)
    json.dump(rows, open(os.path.join(outdir, f"relq_{stamp}.json"), "w"), ensure_ascii=False, indent=1)
    md = report(rows, stamp)
    path = os.path.join(outdir, f"relq_{stamp}.md")
    open(path, "w").write(md)
    print(md.split("## Flagged answers", 1)[0].strip())
    print(f"→ {path}")
