"""
patch_pd_precision.py
=====================
Wires Pratyantardasha (PD) precision into dasha_event_mapper.py.

Changes:
  A. Insert Vimsottari constants + _compute_pds_for_ad() + _drill_to_pd() helpers
     BEFORE find_event_window().
  B. In find_event_window(), after selecting best AD candidate, call _drill_to_pd()
     and attach pd_lord / window_start / window_end / precision to the result.
  C. Update smoke-test print statements to display PD when present.
  D. Update format_for_prompt() to include PD info when available.

Landmark-based surgery only — no line numbers.
"""

import shutil
import sys

TARGET = "antar_engine/dasha_event_mapper.py"

# ── safety backup ─────────────────────────────────────────────────────────────
shutil.copy(TARGET, TARGET + ".bak")
with open(TARGET, "r") as fh:
    src = fh.read()

original = src  # keep for diff check

# ─────────────────────────────────────────────────────────────────────────────
# A. Insert constants + helpers BEFORE def find_event_window(
# ─────────────────────────────────────────────────────────────────────────────
HELPERS = '''
# ---------------------------------------------------------------------------
# Vimsottari dasha duration constants — used for PD computation
# ---------------------------------------------------------------------------
_VIMSOTTARI_YEARS = {
    'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7,
    'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17,
}
_DASHA_SEQUENCE = [
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury',
]


def _compute_pds_for_ad(ad_lord: str, ad_start: str, ad_end: str) -> list:
    """
    Compute Pratyantardasha sub-periods for an Antardasha using the
    Vimsottari proportional formula.  No DB access required.

    Returns list of {'lord': str, 'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}.
    Gracefully returns [] on any bad input.
    """
    from datetime import date, timedelta
    try:
        s = date.fromisoformat(str(ad_start)[:10])
        e = date.fromisoformat(str(ad_end)[:10])
    except (ValueError, TypeError):
        return []

    total_days = (e - s).days
    if total_days <= 0 or ad_lord not in _DASHA_SEQUENCE:
        return []

    start_idx = _DASHA_SEQUENCE.index(ad_lord)
    pds = []
    current = s
    for i in range(9):
        planet = _DASHA_SEQUENCE[(start_idx + i) % 9]
        pd_days = int(round((_VIMSOTTARI_YEARS[planet] / 120.0) * total_days))
        pd_end = min(current + timedelta(days=max(pd_days, 1)), e)
        pds.append({
            'lord':  planet,
            'start': current.isoformat(),
            'end':   pd_end.isoformat(),
        })
        current = pd_end
        if current >= e:
            break
    return pds


def _drill_to_pd(
    winning_ad: dict,
    rule_lords: list,
    event_date_str: str,
) -> Optional[dict]:
    """
    Given a winning AD dict and the event's priority lord list, find the
    tightest PD window.  Uses pre-attached 'pds' key if present; otherwise
    computes via _compute_pds_for_ad().

    Returns a PD dict {'lord', 'start', 'end'} or None (fall back to AD).
    """
    from datetime import datetime

    pds = winning_ad.get('pds') or []
    if not pds:
        ad_lord  = winning_ad.get('planet', winning_ad.get('planet_or_sign', ''))
        ad_start = str(winning_ad.get('start', winning_ad.get('start_date', '')))[:10]
        ad_end   = str(winning_ad.get('end',   winning_ad.get('end_date',   '')))[:10]
        pds = _compute_pds_for_ad(ad_lord, ad_start, ad_end)

    if not pds:
        return None

    karakas  = {'Jupiter', 'Venus', 'Moon'}
    rule_set = set(rule_lords)

    scored = []
    for pd in pds:
        score = 3 if pd['lord'] in rule_set else (1 if pd['lord'] in karakas else 0)
        scored.append((score, pd))

    try:
        ev_dt = datetime.fromisoformat(event_date_str)
        scored.sort(key=lambda x: (
            -x[0],
            abs((datetime.fromisoformat(x[1]['start']) - ev_dt).days),
        ))
    except (ValueError, TypeError):
        scored.sort(key=lambda x: -x[0])

    best_score, best_pd = scored[0]
    return best_pd if best_score > 0 else None


'''

ANCHOR_A = "def find_event_window("
assert ANCHOR_A in src, f"Anchor A not found: {ANCHOR_A!r}"
src = src.replace(ANCHOR_A, HELPERS + ANCHOR_A, 1)

# ─────────────────────────────────────────────────────────────────────────────
# B. Drill to PD at the end of find_event_window() — replace the final
#    return-best block (unique: "best["event_type"] = event_type\n    return best")
# ─────────────────────────────────────────────────────────────────────────────
OLD_RETURN = \
    "    best[\"midpoint_year\"] = (best[\"start_year\"] + best[\"end_year\"]) // 2\n" \
    "    best[\"event_type\"] = event_type\n" \
    "    return best"

NEW_RETURN = \
    "    best[\"midpoint_year\"] = (best[\"start_year\"] + best[\"end_year\"]) // 2\n" \
    "    best[\"event_type\"] = event_type\n" \
    "\n" \
    "    # ── PD precision drill ────────────────────────────────────────────\n" \
    "    rule_lords = [p for p, _, _ in priority_list]\n" \
    "    _pd = _drill_to_pd(\n" \
    "        winning_ad={\n" \
    "            'planet': best['planet'],\n" \
    "            'start':  best['start'],\n" \
    "            'end':    best['end'],\n" \
    "        },\n" \
    "        rule_lords=rule_lords,\n" \
    "        event_date_str=f\"{best['midpoint_year']}-06-01\",\n" \
    "    )\n" \
    "    if _pd:\n" \
    "        best['pd_lord']      = _pd['lord']\n" \
    "        best['window_start'] = _pd['start']\n" \
    "        best['window_end']   = _pd['end']\n" \
    "        best['precision']    = 'PD'\n" \
    "    else:\n" \
    "        best['precision']    = 'AD'\n" \
    "        best['window_start'] = best['start']\n" \
    "        best['window_end']   = best['end']\n" \
    "\n" \
    "    return best"

assert OLD_RETURN in src, "Anchor B (return-best block) not found"
src = src.replace(OLD_RETURN, NEW_RETURN, 1)

# ─────────────────────────────────────────────────────────────────────────────
# C. Update format_for_prompt() to show PD when available
# ─────────────────────────────────────────────────────────────────────────────
OLD_FMT = \
    "            lines.append(\n" \
    "                f\"{label}: {w['parent_md']} MD + {w['planet']} AD \"\n" \
    "                f\"({w['start'][:7]} to {w['end'][:7]}) — {w['reason']}\"\n" \
    "            )"

NEW_FMT = \
    "            if w.get('pd_lord'):\n" \
    "                _win = f\"{w['window_start'][:7]} to {w['window_end'][:7]}\"\n" \
    "                lines.append(\n" \
    "                    f\"{label}: {w['parent_md']} MD + {w['planet']} AD\"\n" \
    "                    f\" + {w['pd_lord']} PD ({_win}) — {w['reason']}\"\n" \
    "                )\n" \
    "            else:\n" \
    "                lines.append(\n" \
    "                    f\"{label}: {w['parent_md']} MD + {w['planet']} AD \"\n" \
    "                    f\"({w['start'][:7]} to {w['end'][:7]}) — {w['reason']}\"\n" \
    "                )"

assert OLD_FMT in src, "Anchor C (format_for_prompt lines.append) not found"
src = src.replace(OLD_FMT, NEW_FMT, 1)

# ─────────────────────────────────────────────────────────────────────────────
# D-1..4. Smoke test print statements — use actual en-dash char (U+2013)
# ─────────────────────────────────────────────────────────────────────────────
DASH = "\u2013"  # actual en-dash character as it appears in the source file

# Test 1 (Raman) — unique context: Score: {correct}/
OLD_T1 = (
    f"        print(f\"  {{event:15s}}: {{w['parent_md']}} MD + {{w['planet']}} AD \"\n"
    f"              f\"({{w['start'][:7]}}{DASH}{{w['end'][:7]}})  actual={{actual_year}}  {{mark}}\")\n"
    f"    print(f\"  Score: {{correct}}/{{len(RAMAN_ACTUAL)}} = {{correct/len(RAMAN_ACTUAL)*100:.0f}}%\")"
)
NEW_T1 = (
    f"        _pd_sfx = (f\" + {{w['pd_lord']}} PD ({{w['window_start'][:7]}}{DASH}{{w['window_end'][:7]}})\"\n"
    f"                  if w.get('pd_lord') else \"\")\n"
    f"        print(f\"  {{event:15s}}: {{w['parent_md']}} MD + {{w['planet']}} AD{{_pd_sfx}} \"\n"
    f"              f\"({{w['start'][:7]}}{DASH}{{w['end'][:7]}})  actual={{actual_year}}  {{mark}}\")\n"
    f"    print(f\"  Score: {{correct}}/{{len(RAMAN_ACTUAL)}} = {{correct/len(RAMAN_ACTUAL)*100:.0f}}%\")"
)
assert OLD_T1 in src, f"Anchor D-1 (Test 1 print) not found\nExpected:\n{OLD_T1!r}"
src = src.replace(OLD_T1, NEW_T1, 1)

# Test 2 (Andres) — unique context: first_child:
OLD_T2 = (
    f"        print(f\"  first_child: {{w['parent_md']}} MD + {{w['planet']}} AD \"\n"
    f"              f\"({{w['start'][:7]}}{DASH}{{w['end'][:7]}})  actual={{actual}}  {{mark}}\")"
)
NEW_T2 = (
    f"        _pd_sfx2 = (f\" + {{w['pd_lord']}} PD ({{w['window_start'][:7]}}{DASH}{{w['window_end'][:7]}})\"\n"
    f"                   if w.get('pd_lord') else \"\")\n"
    f"        print(f\"  first_child: {{w['parent_md']}} MD + {{w['planet']}} AD{{_pd_sfx2}} \"\n"
    f"              f\"({{w['start'][:7]}}{DASH}{{w['end'][:7]}})  actual={{actual}}  {{mark}}\")"
)
assert OLD_T2 in src, f"Anchor D-2 (Test 2 print) not found"
src = src.replace(OLD_T2, NEW_T2, 1)

# Test 4 (AT) — unique context: pct = at_correct
OLD_T4 = (
    f"        print(f\"  {{event:15s}}: {{w['parent_md']}} MD + {{w['planet']}} AD \"\n"
    f"              f\"({{w['start'][:7]}}{DASH}{{w['end'][:7]}})  actual={{actual_year}}  {{mark}}\")\n"
    f"    pct = at_correct / len(AT_ACTUALS) * 100"
)
NEW_T4 = (
    f"        _pd_sfx4 = (f\" + {{w['pd_lord']}} PD ({{w['window_start'][:7]}}{DASH}{{w['window_end'][:7]}})\"\n"
    f"                   if w.get('pd_lord') else \"\")\n"
    f"        print(f\"  {{event:15s}}: {{w['parent_md']}} MD + {{w['planet']}} AD{{_pd_sfx4}} \"\n"
    f"              f\"({{w['start'][:7]}}{DASH}{{w['end'][:7]}})  actual={{actual_year}}  {{mark}}\")\n"
    f"    pct = at_correct / len(AT_ACTUALS) * 100"
)
assert OLD_T4 in src, f"Anchor D-3 (Test 4 print) not found"
src = src.replace(OLD_T4, NEW_T4, 1)

# Test 5 (JS) — unique context: pct5 = js_correct
OLD_T5 = (
    f"        print(f\"  {{event:15s}}: {{w['parent_md']}} MD + {{w['planet']}} AD \"\n"
    f"              f\"({{w['start'][:7]}}{DASH}{{w['end'][:7]}})  actual={{actual_year}}  {{mark}}\")\n"
    f"    pct5 = js_correct / len(JS_ACTUALS) * 100"
)
NEW_T5 = (
    f"        _pd_sfx5 = (f\" + {{w['pd_lord']}} PD ({{w['window_start'][:7]}}{DASH}{{w['window_end'][:7]}})\"\n"
    f"                   if w.get('pd_lord') else \"\")\n"
    f"        print(f\"  {{event:15s}}: {{w['parent_md']}} MD + {{w['planet']}} AD{{_pd_sfx5}} \"\n"
    f"              f\"({{w['start'][:7]}}{DASH}{{w['end'][:7]}})  actual={{actual_year}}  {{mark}}\")\n"
    f"    pct5 = js_correct / len(JS_ACTUALS) * 100"
)
assert OLD_T5 in src, f"Anchor D-4 (Test 5 print) not found"
src = src.replace(OLD_T5, NEW_T5, 1)

# ─────────────────────────────────────────────────────────────────────────────
# Verify something actually changed
# ─────────────────────────────────────────────────────────────────────────────
assert src != original, "ERROR: patch made no changes — check all anchors"

with open(TARGET, "w") as fh:
    fh.write(src)

print(f"✅  patch_pd_precision.py applied to {TARGET}")
print(f"    Backup: {TARGET}.bak")
