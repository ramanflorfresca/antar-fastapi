"""Export de-identified WhatsApp conversations for model training — consented people only.

Usage:  railway run python scripts/export_wa_training.py                 # dry run: counts only
        railway run python scripts/export_wa_training.py --out data.jsonl  # writes JSONL

A message is exported only when ALL hold (see eligible()):
  * its number's link is `linked` with training_opt_in = true under the CURRENT consent version
    (messaging.can_train) — withdrawing, unlinking or a wording bump removes the person at once;
  * it was sent at/after training_opt_in_at — consent is never retroactive;
  * it is a real exchange (text or list), not a template, media or location;
  * it still has content after scrubbing (antar_engine.wa_scrub).
Output: one JSON object per conversation (messages split on a 6h gap) keyed by a one-way pseudonym
(HMAC of chart_id with EXPORT_PSEUDONYM_KEY) — never the chart id, number or name.
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from antar_engine import messaging as _msg  # noqa: E402
from antar_engine.wa_scrub import scrub  # noqa: E402

GAP_S = 6 * 3600
KINDS = ("text", "list")


def _ts(s: str) -> float:
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()


def eligible(msg: dict, link: dict) -> bool:
    if not _msg.can_train(link) or msg.get("kind") not in KINDS or not (msg.get("body") or "").strip():
        return False
    since = link.get("training_opt_in_at")
    return bool(since) and _ts(msg["created_at"]) >= _ts(since)


def pseudonym(chart_id: str, key: str) -> str:
    return hmac.new(key.encode(), str(chart_id).encode(), hashlib.sha256).hexdigest()[:16]


def conversations(rows: list, link: dict, names: list, key: str) -> list:
    """Eligible rows of ONE person → scrubbed conversations, oldest first."""
    out, cur, last = [], [], None
    for m in sorted((r for r in rows if eligible(r, link)), key=lambda r: r["created_at"]):
        body = scrub(m["body"], names)
        if not body:
            continue
        t = _ts(m["created_at"])
        if last is not None and t - last > GAP_S and cur:
            out.append(cur)
            cur = []
        last = t
        meta = m.get("meta") or {}
        cur.append({"role": "user" if m["direction"] == "in" else "assistant", "content": body,
                    "lang": m.get("lang"), "topic": meta.get("area"), "intent": meta.get("intent"),
                    "ts": m["created_at"]})
    if cur:
        out.append(cur)
    pid = pseudonym(link["chart_id"], key)
    return [{"person": pid, "country": rows[0].get("country"), "messages": c} for c in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"])
    key = os.getenv("EXPORT_PSEUDONYM_KEY")
    if a.out and not key:
        sys.exit("set EXPORT_PSEUDONYM_KEY (any long random secret) before writing an export")
    links = (sb.table("messaging_links").select("*").eq("channel", "whatsapp").eq("status", "linked")
             .eq("training_opt_in", True).eq("training_consent_version", _msg.WA_TRAINING_CONSENT_VERSION)
             .execute().data or [])
    n_conv = n_msg = 0
    fh = open(a.out, "w") if a.out else None
    for link in links:
        rows = (sb.table("wa_messages").select("*").eq("wa_number", link["channel_user_id"])
                .order("created_at").limit(20000).execute().data or [])
        chart = (sb.table("charts").select("name").eq("id", link["chart_id"]).limit(1).execute().data or [{}])[0]
        names = [p for p in str(chart.get("name") or "").split() if p]
        convs = conversations(rows, link, names + ([chart.get("name")] if chart.get("name") else []), key or "dry")
        for c in convs:
            n_conv += 1
            n_msg += len(c["messages"])
            if fh:
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"consented people: {len(links)} · conversations: {n_conv} · messages: {n_msg}"
          f"{'' if fh else '  (dry run — pass --out to write)'}")


if __name__ == "__main__":
    main()
