"""Routing audit — does every follow-up chip we OFFER land in its own topic?

[audit-wider 2026-10-05] A tapped suggestion is a question we wrote. If it routes to a
different topic ("When does my energy pick up?" → business window) the answer is wrong
before any wording matters. Runs each chip (every topic × lane × language) through the real
/ask (nothing sent or saved) and reads the topic the pipeline settled on from its own log.

    venv311/bin/python scripts/routing_audit.py [--out routing.json]
"""
import argparse, asyncio, builtins, contextvars, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import main  # noqa: E402
from antar_engine import ask_followups as af  # noqa: E402
from antar_engine import outcomes as oc  # noqa: E402

PERSONA = {"en": ("a4c9d57b-fb9c-4890-8fe7-4a9904f515ed", "en", -240), "es": ("216fd897-7d8a-4762-a945-25424bb7539a", "es", -300),
           "hi": ("9dff84f7-6171-4372-bdb6-1f266696816d", "hinglish", 330), "pt": ("a4c9d57b-fb9c-4890-8fe7-4a9904f515ed", "pt", -240)}
OK = {  # chip topic → acceptable concerns the pipeline may settle on
    "money": {"finance", "wealth", "funding", "loss", "loan"}, "funding": {"funding", "finance", "wealth", "business"},
    "career": {"career", "business", "startup", "sales", "education"}, "business": {"business", "career", "funding", "finance", "startup", "sales"},
    "love": {"love", "marriage", "reconciliation", "divorce"}, "family": {"family", "children"},
    "health": {"health", "general", "spiritual"}, "place": {"property", "foreign", "domestic_move", "foreign_move", "family", "general"},
    "speculation": {"speculation", "finance", "wealth", "funding", "general", "spiritual"},
    "spiritual": {"spiritual", "general"}, "choice": {"finance", "wealth", "career", "business", "general", "funding"},
}
_CUR = contextvars.ContextVar("cur", default=None)
_orig_print = builtins.print


def _print(*a, **k):
    buf = _CUR.get()
    if buf is not None:
        buf.append(" ".join(str(x) for x in a))
    _orig_print(*a, **k)


async def one(sem, lang, bucket, lane, q):
    persona = PERSONA[lang]
    async with sem:
        buf = []
        _CUR.set(buf)
        try:
            await main.ask_endpoint(main.AskRequest(question=q, chart_id=persona[0], language=persona[1], tz_offset=persona[2]))
        except Exception as e:
            buf.append(f"ERR {e}")
        txt = "\n".join(buf)
        m = re.findall(r"\[ask\] concern=(\w+)", txt)
        return {"lang": lang, "topic": bucket, "lane": lane, "q": q, "concern": (m[-1] if m else None),
                "ok": bool(m) and m[-1] in OK.get(bucket, {m[-1]}),
                "nlu": re.findall(r"\[ask\]\[nlu-concern\][^\n]*", txt)[:1]}


async def run():
    async def nop(*a, **k): return None
    main._ask_persist = nop; main._nlu_shadow = nop
    main._ask_harvest_stated = lambda *a, **k: None
    main._ask_recent_thread = lambda *a, **k: []
    oc.record_claim = lambda *a, **k: None
    builtins.print = _print
    sem = asyncio.Semaphore(6)
    jobs = []
    for lang, table in af._Q.items():
        for bucket, lanes in table.items():
            if bucket in ("day", "general"):
                continue
            for lane, q in lanes.items():
                jobs.append(one(sem, lang, bucket, lane, q))
    return await asyncio.gather(*jobs)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="routing.json")
    a = ap.parse_args()
    res = asyncio.run(run())
    builtins.print = _orig_print
    json.dump(res, open(a.out, "w"), ensure_ascii=False, indent=1)
    bad = [r for r in res if not r["ok"]]
    print(f"{len(res)} chips · {len(bad)} misrouted ({100*len(bad)//max(1,len(res))}%)")
    by = {}
    for r in bad:
        by.setdefault((r["lang"], r["topic"]), []).append(r)
    for (l, t), rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f"  {l}/{t}: {len(rs)}  → " + ", ".join(f"{r['concern']}" for r in rs))
    for r in bad:
        print(f"  ✗ [{r['lang']}/{r['topic']}/{r['lane']}] {r['q']}  →  {r['concern']}")
