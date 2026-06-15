#!/usr/bin/env python3
"""
antar_research/practices_timeframe_qa.py  (READ-ONLY harness)
─────────────────────────────────────────────────────────────────────────────
QA for the Practices Tab timeframe-router (COWORK brief §6). Deterministic:
exercises the selection layer (merge_by_planet / select_practice_set /
_why_now / _stamp_timeframe_fields) with synthetic `actives` so the checks do
not depend on swisseph or Supabase. Run:

    source venv311/bin/activate
    python antar_research/practices_timeframe_qa.py

Checks:
  1. Same chart, different timeframes -> different LEAD practice.
  2. Two charts differ on their year/month lead planet.
  3. Every surfaced practice has a non-generic why_now + a timeframe_source.
  4. Natal baseline present but never the lead when a time-active practice exists.
  5. Merge case: a planet flagged by both natal and this-year shows once with
     both contributing_sources.
"""
import sys

from antar_engine import practice_composer as C
from antar_engine.practice_scopes import TIMEFRAME_BY_SCOPE

GENERIC = ("exceptionally strong", "in your chart right now", "this pattern is")


def _active(planet, scope, severity, why="x. y."):
    return {
        "planet": planet, "scope": scope, "severity": severity,
        "supporting_planets": [], "why_paragraph": why,
        "duration_label": "", "ttl_days": None,
        "timeframe_source": TIMEFRAME_BY_SCOPE.get(scope),
    }


def _lead_planet(actives):
    s = C.select_practice_set(actives)
    return (s["lead"] or {}).get("planet"), s


results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


# ── 1. Same chart, different timeframes -> different lead ────────────────────
# Year A: Mars sleeping this year (varshphal) + chronic natal Venus debil.
year_a = [_active("Venus", "natal_weakness", 0.80), _active("Mars", "varshphal_year", 0.75)]
# Year B (advance the solar year): no year signal; Saturn dasha now running.
year_b = [_active("Venus", "natal_weakness", 0.80), _active("Saturn", "dasha_period", 0.72)]
la, _ = _lead_planet(year_a)
lb, _ = _lead_planet(year_b)
check("1 lead changes with timeframe", la == "Mars" and lb == "Saturn",
      f"yearA lead={la} (expect Mars), yearB lead={lb} (expect Saturn)")

# ── 2. Two charts differ on year/month lead ─────────────────────────────────
chart_x = [_active("Jupiter", "varshphal_year", 0.66), _active("Sun", "natal_weakness", 0.7)]
chart_y = [_active("Mercury", "monthly_lk", 0.5), _active("Sun", "natal_weakness", 0.7)]
lx, _ = _lead_planet(chart_x)
ly, _ = _lead_planet(chart_y)
check("2 two charts differ on lead", lx == "Jupiter" and ly == "Mercury",
      f"chartX lead={lx} (expect Jupiter, this_year), chartY lead={ly} (expect Mercury, this_month)")

# ── 3. Every surfaced practice has non-generic why_now + timeframe_source ────
set3 = C.select_practice_set(year_a)
surfaced = [set3["lead"]] + set3["secondary"] + ([set3["baseline"]] if set3["baseline"] else [])
ok3 = True
bad = ""
for e in surfaced:
    st = C._stamp_timeframe_fields(dict(e), "en")
    wn = (st.get("why_now") or "").lower()
    if not st.get("timeframe_source") or not wn or any(g in wn for g in GENERIC):
        ok3 = False
        bad = f"{st.get('planet')}: why_now={st.get('why_now')!r} tf={st.get('timeframe_source')}"
        break
check("3 every practice has concrete why_now + timeframe_source", ok3, bad or f"{len(surfaced)} surfaced ok")

# ── 4. Natal baseline present but never lead when time-active exists ─────────
set4 = C.select_practice_set(year_a)
lead_tf = C._tf_of(set4["lead"])
baseline_present = set4["baseline"] is not None and C._tf_of(set4["baseline"]) == "natal_baseline"
check("4 natal baseline present, not lead", lead_tf != "natal_baseline" and baseline_present,
      f"lead_tf={lead_tf}, baseline={set4['baseline'] and set4['baseline'].get('planet')}")

# When ONLY natal fires, it is allowed to lead (background promoted).
only_natal = [_active("Venus", "natal_weakness", 0.8)]
sn = C.select_practice_set(only_natal)
check("4b natal may lead when nothing time-active",
      (sn["lead"] or {}).get("planet") == "Venus" and sn["baseline"] is None,
      f"lead={(sn['lead'] or {}).get('planet')}")

# ── 5. Merge: planet flagged by natal AND this-year -> one entry, both sources
merge_in = [_active("Mars", "natal_weakness", 0.8), _active("Mars", "varshphal_year", 0.75)]
merged = C.merge_by_planet(merge_in)
mars = [m for m in merged if m["planet"] == "Mars"]
ok5 = (len(merged) == 1 and len(mars) == 1
       and set(mars[0]["contributing_sources"]) == {"this_year", "natal_baseline"}
       and C._tf_of(mars[0]) == "this_year")          # primary = highest-priority layer
wn5 = C._why_now(mars[0], "en").lower()
ok5 = ok5 and ("lifelong" in wn5 and "this year" in wn5)   # merged-good-case narration
check("5 merge by planet keeps one entry w/ both sources", ok5,
      f"merged={len(merged)}, sources={mars[0]['contributing_sources'] if mars else None}, why_now={C._why_now(mars[0],'en') if mars else None!r}")

# ── summary ─────────────────────────────────────────────────────────────────
failed = [n for n, ok, _ in results if not ok]
print("\n" + ("ALL PASS" if not failed else f"{len(failed)} FAILED: {failed}"))
sys.exit(1 if failed else 0)
