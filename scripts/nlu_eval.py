"""Run the understanding layer against tests/fixtures/nlu_golden.jsonl (live model).

    venv311/bin/python scripts/nlu_eval.py

Reports per-field accuracy and every miss. Not part of CI (needs the API key).
Gate for NLU_MODE=primary: area >= 95%, language >= 99%, safety flags 100%.
"""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import main  # noqa: E402

GOLD = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "nlu_golden.jsonl")


async def run():
    rows = [json.loads(l) for l in open(GOLD) if l.strip()]
    tot, ok, misses = {}, {}, []
    for r in rows:
        u = await main._nlu_read(r["q"], None)
        if not u:
            misses.append((r["q"], "NO READING", None)); continue
        for f, want in r.items():
            if f == "q":
                continue
            got = u.get(f)
            good = got in want if isinstance(want, list) else got == want
            tot[f] = tot.get(f, 0) + 1
            ok[f] = ok.get(f, 0) + (1 if good else 0)
            if not good:
                misses.append((r["q"][:70], f, f"want {want} got {got}"))
    for f in sorted(tot):
        print(f"{f:14s} {ok[f]}/{tot[f]}  ({100*ok[f]/tot[f]:.0f}%)")
    print(f"\n{len(misses)} misses:")
    for m in misses:
        print("  -", m)

asyncio.run(run())
