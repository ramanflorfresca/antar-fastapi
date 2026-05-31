# Compatibility V2 — Handoff (Option A: 6-layer mapping on `Compatibility.py`)

**Status: BUILT — all modules compile, all offline checks green. Deploy + the 11 live curls are yours (build sandbox has no network egress).**

`Compatibility.py` (the 1024-line spine) is **not restructured** — only the Phase-1
Mula/Moola yoni fix remains. V2 adds sibling modules that map its output to the
6-layer contract and gate by reason/role, and rewires `/api/v1/compatibility/start`.

---

## Files

**New:** `antar_engine/compatibility_reasons.py` (taxonomy, weights, role modifiers, layer→source map, reasons directory)
**Edited:**
- `antar_engine/compatibility_layers.py` — `+compose_six_layers`, `+compose_compat_v2` (V2 path; the older Phase-1 `/api/v1/compat` helpers are left intact)
- `antar_engine/compatibility_templates.py` — `+`per-layer headlines, `+TEMPLATES` (reason,layer,tier) artifact (126), `+`V2 accessors
- `main.py` — via `patch_compat_v2.py`: request fields, identical-chart guard + reason/role resolution, `/start` V2 short-circuit, `GET /compatibility/reasons`, `/connections` read-time fields
- `antar_engine/Compatibility.py` — Mula yoni alias (already applied earlier; verified `_yoni_score(... Mula ...) == "Dog"`)

---

## How `/start` works now
1. Limit check → **identical-chart guard** (`chart_id_b == chart_id_a` → 400 "Cannot run compatibility against the same chart.").
2. Resolve reason: `compat_type` preferred, `mode` accepted as a **legacy alias** (logs a deprecation line), falls back to `compatibility_type`. Tolerant aliases (`boss`→`boss-or-manager`, etc.).
3. Role required + validated for `employee`/`boss-or-manager` (422 otherwise); ignored for the other 5. Direction locked from the reason (`user_senior` / `user_junior` / null).
4. Resolve/compute chart B (existing sub-chart machinery, unchanged), inject current-dasha strings, run `calculate_compatibility`.
5. `compose_compat_v2` → 6 layers (canonical order), per-reason weighted overall, badge, `passed`, headline, summary, watch_points, catalysts. Role modifiers applied to layer **scores** (capped 0-100).
6. Jargon-stripped (`apply_user_facing_strips`, `source="curated_static"` keeps planet actors), then es/pt translation of `headline`/`summary`/`detail`/`layer_label`.
7. Auto-saves the connection (V2 fields packed into `score_breakdown` JSONB — no schema change) and stores the session. `field_mode_layer` kept as decorative; `score_breakdown` kept for backward compat.

> The legacy LLM layer1/2/3 flow is left in place below the short-circuit (unreached).
> `/compatibility/continue` still works off the stored session (summary saved as `layer1_analysis`).

---

## Offline verification (sandbox — all green)
```
reasons directory: 7 entries, needs_role = [employee, boss-or-manager]   ✅
all 7 reason weights sum to 100                                          ✅
TEMPLATES artifact = 126 (7×6×3)                                         ✅
Mula nakshatra yoni = "Dog" (bug fixed)                                  ✅
compose across 7 reasons: 6 layers, canonical order, valid keys/scores   ✅
badge ∈ {FLOW,MIXED,STRAIN}; passed == (score>=65)                       ✅
reasons produce different overall scores (same charts)                   ✅
employee role modifiers shift layer scores (managerial public 79 vs finance 69; finance friction 100 vs managerial 82) ✅
direction lock: employee=user_senior, boss-or-manager=user_junior        ✅
jargon scan (Sanskrit + house numbers) on user-facing prose: clean       ✅
normalize_reason aliases (mode/boss) work                                ✅
all modules py_compile                                                   ✅
```
Not testable offline (no network/key, guarded): es/pt translation; live Supabase save/read.

---

## Decisions & deviations (flagged)
- **Jargon strip uses `output_strips.apply_user_facing_strips`** (the project's single enforcement point), not `plain_english._strip_jargon`. Both scrub Sanskrit + house numbers; templates are authored jargon-free, and `curated_static` preserves planet names as actors (Path B). Verified clean.
- **`/start` is short-circuited, not rewritten** — safest for a production endpoint. Legacy code stays valid but unreached.
- **Cross-chart graha drishti is excluded from V2 friction** (per your "out of scope"). V2 friction = mutual 6/8 + Nadi + growth-areas (3 classical sources). The `cross_aspect_harmony` function from the earlier Phase-2 build still exists but is not used by the V2 surface.
- **watch_points / catalysts** are reused layer prose; as bare list strings they are **not** translated in es/pt (the layer `detail` they mirror *is* translated). Easy follow-up if needed.
- The earlier `/api/v1/compat` endpoint and its Phase-1 `REASON_WEIGHTS` still exist and coexist; **V2 uses the locked weights in `compatibility_reasons.py`**. Frontend should target `/api/v1/compatibility/start` per this spec.
- Templates: 126 `(reason,layer,tier)` + 18 per-layer headlines + 21 overall headlines + 21 details + 18 generic fallbacks. Gaps fall back gracefully (no crash).

---

## Deploy (source files only — never patch scripts / .bak)
```bash
cd ~/antarai && source venv311/bin/activate
git add main.py \
        antar_engine/compatibility_reasons.py \
        antar_engine/compatibility_layers.py \
        antar_engine/compatibility_templates.py \
        antar_engine/Compatibility.py \
        COMPAT_V2_HANDOFF.md
git commit -m "feat: Compatibility V2 — 6-layer /start, 7 reasons + 4 roles, reasons dir, connections fields, Mula fix"
git push origin main
```

## Live verification (run after deploy)
```bash
BASE="https://antar-fastapi-production.up.railway.app"
A="de02bb52-d43a-4b09-be25-b45a07bfbf8a"; B="6ec6311c-d46e-4e97-a46c-859882071971"

# 1 reasons dir
curl -s "$BASE/api/v1/compatibility/reasons" | jq '.reasons|length'            # 7
curl -s "$BASE/api/v1/compatibility/reasons" | jq '.reasons[]|select(.needs_role).key'  # employee, boss-or-manager

# 2 cofounder (no role) — 6 layers
curl -s -X POST "$BASE/api/v1/compatibility/start" -H "Content-Type: application/json" -d '{
 "chart_id_a":"'$A'","name_b":"Andres","birth_date_b":"1990-01-15","birth_time_b":"10:30",
 "birth_city_b":"Bogotá","birth_country_b":"CO","compat_type":"cofounder","language":"en"}' \
 | jq '{score,badge,passed,headline,layer_count:(.layers|length)}'

# 3 canonical order
curl -s ... | jq '.layers|map(.layer_key)'   # ["soul","chemistry","public","lifepath","communication","friction"]

# 4 employee + role
curl -s ... -d '{...,"compat_type":"employee","role":"sales"}' | jq '.direction,.role'   # "user_senior","sales"
# 5 boss-or-manager
curl -s ... -d '{...,"compat_type":"boss-or-manager","role":"managerial"}' | jq '.direction'  # "user_junior"
# 6 reason w/o role
curl -s ... -d '{...,"compat_type":"romantic"}' | jq '.role,.direction'   # null,null
# 7 identical-chart guard
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$BASE/api/v1/compatibility/start" -d '{"chart_id_a":"'$A'","chart_id_b":"'$A'","compat_type":"friend"}'  # 400
# 8 connections new fields
curl -s "$BASE/api/v1/connections/$A" | jq '.connections[0]|{compat_type,badge,passed,headline,layer_scores}'
# 9 no house numbers
curl -s ... | jq -r '..|strings' | grep -E "[0-9]+(st|nd|rd|th) house" && echo LEAK || echo clean
# 10 no Sanskrit
curl -s ... | jq -r '.headline,.summary,.layers[].detail' | grep -iE "atmakaraka|bhakoot|graha maitri|antardasha|mahadasha|nadi" && echo LEAK || echo clean
# 11 employee requires role -> 422
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$BASE/api/v1/compatibility/start" -d '{"chart_id_a":"'$A'","name_b":"X","birth_date_b":"1990-01-15","compat_type":"employee"}'  # 422
```

---

## Out of scope (Phase 2, not built here)
LLM `deep_read` per-layer synthesis · cross-chart graha drishti · LK cross-conditions (`lk_cross_conditions.py`, already a separate gated draft) · per-language template variants · layer editing · side-by-side compare.
