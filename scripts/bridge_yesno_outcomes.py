"""
Backfill: copy already-answered Yes/No check-backs (user_correlations, concern
yesno, feedback_status yes/no/partial) into prediction_outcomes. Idempotent
(outcomes upsert on claim_id). New answers are bridged live by
POST /api/v1/predictions/feedback.

    venv311/bin/python scripts/bridge_yesno_outcomes.py            # dry run
    venv311/bin/python scripts/bridge_yesno_outcomes.py --apply
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv  # noqa: E402
from supabase import create_client  # noqa: E402

from antar_engine.outcomes import (FEEDBACK_TO_OUTCOME, find_yesno_claim,  # noqa: E402
                                   record_outcome)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def main(apply: bool):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    rows = (sb.table("user_correlations").select("id,chart_id,created_at,feedback_status,feedback_note")
            .eq("concern", "yesno").in_("feedback_status", list(FEEDBACK_TO_OUTCOME))
            .limit(5000).execute().data) or []
    matched = unmatched = written = 0
    for r in rows:
        cid = find_yesno_claim(sb, r["chart_id"], r["created_at"])
        if not cid:
            unmatched += 1
            continue
        matched += 1
        if apply and record_outcome(sb, cid, FEEDBACK_TO_OUTCOME[r["feedback_status"]],
                                    r.get("feedback_note"), via="app"):
            written += 1
    print(f"answered Yes/No check-backs: {len(rows)} | matched to a claim: {matched} "
          f"| no claim (asked before the outcome loop): {unmatched}"
          + (f" | written: {written}" if apply else " | dry run — pass --apply"))


if __name__ == "__main__":
    main("--apply" in sys.argv)
