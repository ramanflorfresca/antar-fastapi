"""
Questions the KP Prashna classifier did not recognise (fell back to the generic
"will it happen" type), grouped by their leading words and counted — so missing
question types show up from real use, not from wrong answers.

    venv311/bin/python scripts/kp_unmapped_report.py            # last 30 days
    venv311/bin/python scripts/kp_unmapped_report.py --days 90

Reads prashna_log.breakdown.kp_prashna.generic (stored with every cast).
Prints questions only (no chart ids or names).
"""
import collections
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv  # noqa: E402
from supabase import create_client  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def _stem(q: str) -> str:
    words = re.findall(r"[a-záéíóúñãõç']+", (q or "").lower())
    skip = {"will", "i", "my", "me", "is", "do", "does", "should", "can", "the", "a", "an",
            "get", "be", "it", "this", "that", "in", "on", "next", "kya", "voy", "a", "vou"}
    core = [w for w in words if w not in skip]
    return " ".join(core[:3]) or "(empty)"


def main(days: int):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows, off = [], 0
    while True:
        page = (sb.table("prashna_log").select("created_at,question,breakdown")
                .gte("created_at", since).range(off, off + 999).execute().data) or []
        rows += page
        off += 1000
        if len(page) < 1000:
            break
    total = unmapped = 0
    groups = collections.defaultdict(list)
    for r in rows:
        b = r.get("breakdown")
        b = b if isinstance(b, dict) else json.loads(b or "{}")
        kp = b.get("kp_prashna") or {}
        if not kp:
            continue
        total += 1
        if kp.get("generic"):
            unmapped += 1
            groups[_stem(r.get("question"))].append((r.get("question") or "")[:100])
    print(f"KP casts in the last {days} days: {total} | not recognised: {unmapped}"
          + (f" ({100 * unmapped // total}%)" if total else ""))
    for stem, qs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"\n{len(qs):>3}  {stem}")
        for q in qs[:5]:
            print(f"       - {q}")


if __name__ == "__main__":
    d = 30
    if "--days" in sys.argv:
        d = int(sys.argv[sys.argv.index("--days") + 1])
    main(d)
