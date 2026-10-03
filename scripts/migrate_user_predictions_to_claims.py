"""
Copy windowed user_predictions rows into prediction_claims (outcome loop, week 1).

user_predictions.fulfilled defaults to false and no one ever answered, so it is
NOT migrated as an outcome — every migrated claim starts unanswered.

    venv311/bin/python scripts/migrate_user_predictions_to_claims.py            # dry run
    venv311/bin/python scripts/migrate_user_predictions_to_claims.py --apply

Idempotent: claims upsert on dedupe_key.
"""
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv  # noqa: E402
from supabase import create_client  # noqa: E402

from antar_engine.outcomes import CHECKIN_DELAY_DAYS, record_claim  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def to_claim(r: dict):
    end = (r.get("prediction_window_end") or "")[:10]
    if not end:
        return None
    try:
        end_d = date.fromisoformat(end)
    except ValueError:
        return None
    start = (r.get("window_start") or "")[:10] or None
    topic = (r.get("category") or "general").lower()
    return {
        "chart_id": r["chart_id"], "source": "life_arc", "topic": topic,
        "claim_type": "window", "window_start": start, "window_end": end,
        "text_shown": (r.get("prediction_text") or "")[:500], "question": None,
        "language": "en", "channel": "app", "verdict": None,
        "confidence_word": str(r.get("confidence_layer") or "") or None,
        "engines": {"life_arc": {"category": r.get("category"),
                                 "confidence_score": r.get("confidence_score"),
                                 "user_prediction_id": r.get("id")}},
        "dedupe_key": f"{r['chart_id']}|{topic}|window|{start or ''}|{end}",
        "checkin_due_at": datetime.combine(end_d + timedelta(days=CHECKIN_DELAY_DAYS),
                                           datetime.min.time(), tzinfo=timezone.utc).isoformat(),
    }


def main(apply: bool):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    rows, off = [], 0
    while True:
        page = (sb.table("user_predictions").select("*").range(off, off + 999).execute().data) or []
        rows += page
        off += 1000
        if len(page) < 1000:
            break
    claims = [c for c in (to_claim(r) for r in rows) if c]
    print(f"user_predictions: {len(rows)} rows → {len(claims)} windowed claims")
    if not apply:
        print("dry run — pass --apply to write")
        return
    ok = sum(1 for c in claims if record_claim(sb, c))
    print(f"written/kept: {ok}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
