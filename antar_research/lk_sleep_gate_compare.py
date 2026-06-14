"""
antar_research/lk_sleep_gate_compare.py — read-only commit-2 preview.

Shows, per audit chart, how the sleeping-planet re-weight changes year-event
magnitudes and ordering — WITHOUT pushing. It pulls the LIVE /annual-plan
(events + lk_sleep_engine already shipped in commit-1), rebuilds the Varshphal
object locally, applies reweight_year_events, and prints before/after.

Usage:
    source venv311/bin/activate
    python -m antar_research.lk_sleep_gate_compare
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import date

from antar_engine.varshphal_chart import build_varshphal_chart
from antar_engine.lk_rules.sleeping import evaluate_sleeping_planets, reweight_year_events
from antar_engine.yearly_v2 import _DOMAIN_TO_NATAL_HOUSES, _YEAR_DOMAIN_LABEL

BASE = "https://antar-fastapi-production.up.railway.app"
CHARTS = {
    "Musk":   "761626dc-2c66-402d-aa3a-9b731df75078",
    "Raman":  "de0c6265-96cc-41ba-a39c-e55868fa5806",
    "Andres": "6ec6311c-d46e-4e97-a46c-859882071971",
}
_LBL2DOM = {v: k for k, v in _YEAR_DOMAIN_LABEL.items()}


def _env():
    env = {}
    for line in open(os.path.join(os.path.dirname(__file__), "..", ".env")):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v.strip().strip('"')
    return env


def _chart_data(env, cid):
    url = env.get("SUPABASE_URL")
    key = (env.get("SUPABASE_SERVICE_ROLE_KEY")
           or env.get("SUPABASE_KEY") or env.get("SUPABASE_ANON_KEY"))
    req = urllib.request.Request(
        f"{url}/rest/v1/charts?id=eq.{cid}"
        f"&select=chart_data,birth_date,needs_reconfirm",
        headers={"apikey": key, "Authorization": "Bearer " + key})
    row = json.load(urllib.request.urlopen(req, timeout=25))[0]
    cd = row["chart_data"]
    if isinstance(cd, str):
        cd = json.loads(cd)
    return cd, row["birth_date"], row.get("needs_reconfirm", False)


def _live_events(cid):
    req = urllib.request.Request(
        f"{BASE}/api/v1/annual-plan/{cid}?language=en")
    d = json.load(urllib.request.urlopen(req, timeout=40))
    return d.get("events", [])


def _label2houses(lbl):
    return _DOMAIN_TO_NATAL_HOUSES.get(_LBL2DOM.get(lbl, ""), [])


def main():
    env = _env()
    for nm, cid in CHARTS.items():
        cd, bd, needs_reconfirm = _chart_data(env, cid)
        vc = build_varshphal_chart(cd, bd, on_date=date.today(),
                                   lagna_verified=not bool(needs_reconfirm))
        sleep = evaluate_sleeping_planets(vc, cd)
        before = _live_events(cid)
        after = reweight_year_events(before, sleep, vc, _label2houses)

        print("=" * 72)
        print(f"{nm}  (age {vc['age']}, {vc['year_key']})")
        print(f"  annual_occupants: {vc['annual_occupants']}")
        b_order = [(e['date_label'], e['domain'], e['magnitude']) for e in before]
        a_order = [(e['date_label'], e['domain'], e['magnitude'],
                    e.get('lk_sleep_adj', {}).get('outcome')) for e in after]
        print(f"  BEFORE (gate off): {b_order or '—'}")
        print(f"  AFTER  (gate on):  {a_order or '—'}")
        adj = [e['lk_sleep_adj'] for e in after if e.get('lk_sleep_adj')]
        print(f"  adjustments: {adj or 'none'}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
