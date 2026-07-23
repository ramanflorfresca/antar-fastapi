"""
scripts/backfill_chara_dasha.py
Regenerate Jaimini (chara) dasha rows wherever the current period is unreadable.
Run 2026-07-23: 23 of 24 affected charts fixed; 1 protected chart left untouched.

WHY THIS WAS NEEDED. The Current Cycle's Jaimini moving-lagna layer needs the
chara sign running TODAY. Auditing all 93 live charts found 24 where that sign
could not be resolved, in three flavours:

  1. EMPTY SIGN (18 charts). A live mahadasha row covered today, but its
     planet_or_sign was an empty string. An older generation path had written
     the dates and never the sign, so `_period_lord` returned "" and the whole
     moving-lagna layer silently went dark.
  2. SINGLE CYCLE ELAPSED (3 charts). Only one 12-sign chara cycle was stored
     and it had already ended, so today fell past the last row and
     `_current_period` fell back to the BIRTH sign — reading the wrong decade.
  3. NO ROWS (3 charts). Incomplete/test charts with no chara dasha at all.

THE FIX. Regenerate through the production path — jaimini_engine.generate_dasha_rows
with num_cycles=2 — which writes 312 rows (24 mahadashas + their antardashas)
covering today and decades ahead, exactly as current onboarding does. New charts
are already generated this way; this only repairs the legacy rows.

SAFETY.
  - Touches ONLY system='jaimini' rows for an affected chart. Vimshottari and
    ashtottari are never read or written.
  - A chart is repaired only if it (a) currently lacks a non-empty chara MD sign
    spanning today and (b) has the lagna, planets and birth_date needed to
    recompute. Everything else is skipped, not guessed.
  - PROTECTED charts (a DB trigger blocks deletion) are respected: the script
    reports them and moves on rather than forcing past the guard. On 2026-07-23
    that left exactly one chart, a2b1178f, at the old data.

Idempotent: re-running skips every chart whose current chara sign already reads.
"""

import os
import sys
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
from supabase import create_client

from antar_engine.jaimini_engine import generate_dasha_rows, Planet

TODAY = date.today().isoformat()


def _build_planets(chart_data: dict) -> dict:
    planets = {}
    for name, d in (chart_data.get("planets") or {}).items():
        lon = d.get("longitude") if isinstance(d, dict) else None
        if not isinstance(lon, (int, float)):
            si, deg = d.get("sign_index"), d.get("degree")
            if isinstance(si, int) and isinstance(deg, (int, float)):
                lon = si * 30.0 + float(deg)
        if isinstance(lon, (int, float)):
            planets[name] = Planet(name=name, sign=int(lon // 30) % 12,
                                   degree=float(lon), degree_in_sign=float(lon) % 30)
    return planets


def _current_chara_sign_ok(jaimini_rows: list) -> bool:
    """True when a chara mahadasha row with a real sign covers today."""
    for r in jaimini_rows:
        if str(r.get("level")).lower() in ("mahadasha", "1", "md"):
            s = str(r.get("start_date"))[:10]
            e = str(r.get("end_date"))[:10]
            sign = (r.get("planet_or_sign") or r.get("lord_or_sign") or "").strip()
            if sign and s <= TODAY <= e:
                return True
    return False


def run(dry_run: bool = True):
    import main as M
    sb = create_client(os.environ["SUPABASE_URL"],
                       os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    charts = (sb.table("charts").select("id,name,protected,birth_date,chart_data")
              .is_("deleted_at", "null").execute().data)

    fixed = skipped_ok = protected = unfixable = 0
    for c in charts:
        cid = str(c["id"])
        cd = c.get("chart_data") or {}
        if _current_chara_sign_ok((M.get_dashas_for_chart(cid) or {}).get("jaimini") or []):
            skipped_ok += 1
            continue

        lag = (cd.get("lagna") or {}).get("sign_index")
        bd = str(c.get("birth_date") or cd.get("birth_date") or "")[:10]
        planets = _build_planets(cd)
        if not (isinstance(lag, int) and len(planets) >= 7 and bd):
            unfixable += 1
            print(f"  SKIP {cid[:8]} — missing lagna/planets/birth_date")
            continue

        rows = generate_dasha_rows(cid, lag, planets, datetime.fromisoformat(bd),
                                   num_cycles=2)
        if dry_run:
            live = [r for r in rows if r["level"] == 1
                    and r["start_date"][:10] <= TODAY <= r["end_date"][:10]]
            print(f"  WOULD FIX {cid[:8]} → {live[0]['planet_or_sign'] if live else '?'} "
                  f"({len(rows)} rows)")
            fixed += 1
            continue
        try:
            sb.table("dasha_periods").delete().eq("chart_id", cid).eq("system", "jaimini").execute()
            for i in range(0, len(rows), 500):
                sb.table("dasha_periods").insert(rows[i:i + 500]).execute()
            fixed += 1
        except Exception as e:
            if "protected" in str(e).lower():
                protected += 1
                print(f"  PROTECTED {cid[:8]} — left untouched (deletion blocked)")
            else:
                unfixable += 1
                print(f"  FAIL {cid[:8]} {e}")

    verb = "would fix" if dry_run else "fixed"
    print(f"\n{verb}={fixed}  already_ok={skipped_ok}  protected={protected}  "
          f"unfixable={unfixable}")


if __name__ == "__main__":
    run(dry_run="--apply" not in sys.argv)
