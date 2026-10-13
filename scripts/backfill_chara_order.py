"""
scripts/backfill_chara_order.py
Regenerate stored Jaimini (chara) dasha rows for charts whose sequence ORDER the
2026-10-13 fix changes (K.N. Rao's 9th-house rule; sub-periods end on the MD sign).

Mahadasha order changes for lagnas Taurus, Gemini, Leo, Virgo, Scorpio, Sagittarius,
Aquarius, Pisces. Antardasha order changes for every lagna (own sign now last), so
all charts are compared; only those whose stored rows differ are rebuilt.


Touches only system='jaimini' rows. DRY RUN by default; pass --apply to write.
PROTECTED charts (delete blocked by a DB trigger) are reported and left alone.
Idempotent: a chart whose stored MD order already equals the fixed order is skipped.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
from supabase import create_client

from antar_engine.jaimini_engine import generate_dasha_rows
from scripts.backfill_chara_dasha import _build_planets


def run(dry_run: bool = True):
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    charts = (sb.table("charts").select("id,name,birth_date,chart_data")
              .is_("deleted_at", "null").execute().data)
    changed = same = protected = unfixable = 0
    for c in charts:
        cid = str(c["id"])
        cd = c.get("chart_data") or {}
        lag = (cd.get("lagna") or {}).get("sign_index")
        bd = str(c.get("birth_date") or cd.get("birth_date") or "")[:10]
        planets = _build_planets(cd)
        if not (isinstance(lag, int) and len(planets) >= 7 and bd):
            unfixable += 1
            continue
        rows = generate_dasha_rows(cid, lag, planets, datetime.fromisoformat(bd), num_cycles=2)
        old = (sb.table("dasha_periods").select("planet_or_sign,start_date,level")
               .eq("chart_id", cid).eq("system", "jaimini").execute().data or [])
        key = lambda rs: [(r["planet_or_sign"], str(r["start_date"])[:10], str(r["level"]))
                          for r in sorted(rs, key=lambda r: (str(r["start_date"]), str(r["level"])))]
        if key(old) == key(rows):
            same += 1
            continue
        if dry_run:
            print(f"  WOULD REBUILD {cid[:8]} lagna={lag} ({len(rows)} rows)")
            changed += 1
            continue
        try:
            sb.table("dasha_periods").delete().eq("chart_id", cid).eq("system", "jaimini").execute()
            for i in range(0, len(rows), 500):
                sb.table("dasha_periods").insert(rows[i:i + 500]).execute()
            changed += 1
        except Exception as e:
            if "protected" in str(e).lower():
                protected += 1
                print(f"  PROTECTED {cid[:8]} — left untouched")
            else:
                unfixable += 1
                print(f"  FAIL {cid[:8]} {e}")
    verb = "would rebuild" if dry_run else "rebuilt"
    print(f"\n{verb}={changed} unchanged={same} protected={protected} skipped={unfixable}")


if __name__ == "__main__":
    run(dry_run="--apply" not in sys.argv)
