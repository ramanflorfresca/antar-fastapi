# Compatibility 6-Layer Surface — Phase 1 Handoff

**Status: PHASE 1 BUILT — compiles + all offline checks green. Live curls + deploy pending (no network egress from the build sandbox; commands below for you to run).**

Phase 1 = the structural surface only. LK cross-conditions, `deep_read` LLM
synthesis, Mercury cross-compat, real house-quality, and graha-drishti aspects
are Phase 2 (not built here, by design).

---

## Files touched

**New (ship as files):**
- `antar_engine/compatibility_layers.py` — the mapping layer (engine output → 6-layer contract), reason + role gating, `mutual_6_8`, raw chart-B resolution.
- `antar_engine/compatibility_templates.py` — Phase-1 prose (counts below).

**Modified in place (via `patch_compat_endpoint.py`):**
- `main.py` — new `POST /api/v1/compat` endpoint; existing `POST /api/v1/compatibility` now passes `language` and runs the jargon strip on its output (shape unchanged).
- `antar_engine/Compatibility.py` — `Mula` yoni alias added next to `Moola` (launch-blocker fix).
- `antar_engine/compatibility_session_engine.py` — `EMPLOYEE_ROLE_LENS` reconciled from the old 7 roles to the locked 4 (`sales/marketing/finance/managerial`).

**Not touched (deliberately):** `AntarCompat.jsx` — frontend wiring is the Lovable prompt's job. ⚠️ It still lists the old 7 employee roles; the Lovable prompt must update it to the locked 4 and point the verdict view at `POST /api/v1/compat`.

---

## Template coverage (authored)

```
base_lines        : 90   (5 reasons × 6 layers × 3 badges)   ✅ mandatory set complete
new_role_lines    : 36   (employee + boss-or-manager, managerial role × 6 × 3)
headlines         : 21   (7 reasons × 3 tiers)
details           : 21   (7 reasons × 3 tiers)
generic_fallback  : 18   (6 layers × 3 badges — last-resort, never crash)
```
`sales / marketing / finance` lines fall back to the `managerial` set until authored (per the prompt). Total authored line/headline/detail strings: **168** (+18 fallback) — exceeds the "138 in Phase 1" target.

---

## Offline verification (ran in the build sandbox — all green)

| Check | Result |
|---|---|
| All 5 modules `py_compile` | ✅ COMPILE_OK |
| Mula nakshatra yoni (via `_yoni_score`) | ✅ `"Dog"` (was defaulting to `"Horse"`) |
| Response shape = documented contract (12 top keys) | ✅ exact |
| `layers` always 6, fixed order soul→friction | ✅ |
| Each layer keys = `{key,name,passed,badge,line}` | ✅ |
| `badge ∈ {FLOW,MIXED,STRAIN}`, `passed` = score≥65 | ✅ |
| 7 reasons → 7 distinct headlines | ✅ 7/7 |
| `employee` role changes overall score | ✅ sales 76 / marketing 76 / finance 78 / managerial 75 |
| role weights renormalize to 1.0 after modifiers | ✅ |
| jargon scan (Sanskrit / house numbers) on business response | ✅ clean |
| `mutual_6_8` cross-chart logic | ✅ 90 (neither fires) |
| 422 gating: employee w/o role → 422; romantic w/o role → 200 | ✅ |

---

## ⚠️ Three spec items I had to resolve (flagging, per "flag + default + continue")

1. **Friction-layer inversion contradiction.** The spec defines the friction
   sources as *higher = less friction* (`mutual_6_8=90` when neither fires,
   `nadi_dosha=100` when different, `growth_areas≈100` when few) **and** says
   `friction_score = 100 - weighted_avg`. Applying that inversion makes heavy
   friction render as FLOW/passed — the opposite of the spec's own parenthetical
   ("80 = low friction = GOOD = passed"). **Default applied: no inversion** — the
   friction layer score is the weighted average directly, so all 6 layers share
   one convention (higher = better = passed). If you actually want sources to mean
   "friction amount" and then invert, flip the three source polarities instead.

2. **Verification #10 (`from antar_engine.Compatibility import YONI_MAP`) can't
   work** — `YONI_MAP` is a function-local dict inside `_yoni_score`, not
   module-level. Hoisting it would be a restructure (prohibited). The Mula fix is
   in place and verified through `_yoni_score(...)` output instead:
   ```bash
   python -c "from antar_engine.Compatibility import _yoni_score; \
   print(_yoni_score({'planets':{'Moon':{'nakshatra':'Mula'}}}, \
                     {'planets':{'Moon':{'nakshatra':'Mula'}}})['a_value'])"
   # -> Dog   (not 'Horse')
   ```

3. **Layer badges are reason-independent by design.** A layer's score comes from
   the chart astrology (fixed `LAYER_DEFINITIONS` sources), so the same chart pair
   yields the same per-layer badges across reasons. The **reason** changes the
   overall `score`, `label`, `headline`, `detail`, and **each layer's prose
   `line`** (templates are reason-specific). So responses are meaningfully
   different per reason (verification #4's headline check passes 7/7), but if you
   expected per-layer *badges* to also shift by reason, that would require
   reason-specific layer sources — a Phase 2 design change, not a Phase 1 bug.

Minor: `public` layer leans on `house_10`/`house_11`, which the current engine
never computes (only houses 1/5/7/9) — they default to 50 as the spec allows.
Real house-10/11 quality is Phase 2. Same for `mercury_compatibility` (→50).

---

## Behavior notes

- **Rate limit (30/user/day) and the response cache are in-process** (per worker,
  reset on deploy). Matches "cache for the local day"; the cache key includes both
  charts' current dasha string, so it busts automatically on a dasha boundary. If
  you need durable cross-worker limits, move these to Supabase in a follow-up.
- **Translation**: `headline`, `detail`, layer `line`, plus `label` and layer
  `name` are translated for `es`/`pt` via the existing `translate_dict` layer
  (same one behind `@translate_response`), cached per content hash. English is an
  untouched passthrough.
- **Existing `POST /api/v1/compatibility`**: same Ashtakoot tree as before, now
  with user-facing strings jargon-stripped (`source="curated_static"`). Shape
  unchanged — safe for any existing consumer.

---

## Deploy (source files only — never the patch script or .bak)

```bash
cd ~/antarai && source venv311/bin/activate
git add main.py \
        antar_engine/Compatibility.py \
        antar_engine/compatibility_session_engine.py \
        antar_engine/compatibility_layers.py \
        antar_engine/compatibility_templates.py \
        COMPAT_PHASE1_HANDOFF.md
git commit -m "feat: 6-layer /api/v1/compat surface + reason/role gating, jargon strip, Mula fix"
git push origin main
# Railway auto-deploys on push. Watch logs.
```

---

## Live verification (run after deploy — sandbox had no egress, so these are for you)

```bash
ANDRES_ID="6ec6311c-XXXX-XXXX-XXXX-XXXXXXXXXXXX"   # full UUID
BASE="https://antar-fastapi-production.up.railway.app"
A="de02bb52-d43a-4b09-be25-b45a07bfbf8a"

# 1. 6-layer contract
curl -s -X POST "$BASE/api/v1/compat" -H "Content-Type: application/json" \
  -d "{\"chart_a_id\":\"$A\",\"chart_b\":{\"chart_id\":\"$ANDRES_ID\"},\"reason\":\"business\",\"language\":\"en\",\"tz_offset\":-300}" | jq

# 2. layers length + order
curl -s -X POST "$BASE/api/v1/compat" -H "Content-Type: application/json" \
  -d "{\"chart_a_id\":\"$A\",\"chart_b\":{\"chart_id\":\"$ANDRES_ID\"},\"reason\":\"business\"}" | jq '.layers|length, [.layers[].key]'
# Expect: 6, ["soul","chemistry","public","lifepath","communication","friction"]

# 3. layer keys (no detail in Phase 1)
curl -s ... | jq '.layers[0]|keys'   # ["badge","key","line","name","passed"]

# 4. reason → different headlines
for r in romantic business cofounder friend family; do
  curl -s -X POST "$BASE/api/v1/compat" -H "Content-Type: application/json" \
    -d "{\"chart_a_id\":\"$A\",\"chart_b\":{\"chart_id\":\"$ANDRES_ID\"},\"reason\":\"$r\"}" | jq -r '.headline'; done

# 5. employee requires role
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$BASE/api/v1/compat" -H "Content-Type: application/json" \
  -d "{\"chart_a_id\":\"$A\",\"chart_b\":{\"chart_id\":\"$ANDRES_ID\"},\"reason\":\"employee\",\"role\":null}"   # 422
curl -s -X POST "$BASE/api/v1/compat" -H "Content-Type: application/json" \
  -d "{\"chart_a_id\":\"$A\",\"chart_b\":{\"chart_id\":\"$ANDRES_ID\"},\"reason\":\"employee\",\"role\":\"sales\"}" | jq '[.layers[].badge]'

# 6. role changes weighting
for role in sales marketing finance managerial; do
  curl -s -X POST "$BASE/api/v1/compat" -H "Content-Type: application/json" \
    -d "{\"chart_a_id\":\"$A\",\"chart_b\":{\"chart_id\":\"$ANDRES_ID\"},\"reason\":\"employee\",\"role\":\"$role\"}" \
    | jq -r '"\(.role): \(.score)"'; done

# 7. raw chart_b (no UUID)
curl -s -X POST "$BASE/api/v1/compat" -H "Content-Type: application/json" -d '{
  "chart_a_id":"'$A'","chart_b":{"name":"Test","date":"1985-07-12","time":"14:30",
  "place":{"lat":4.7,"lon":-74.07,"tz":"America/Bogota"}},"reason":"friend"}' | jq '.headline, .chart_b_id'

# 8. Spanish
curl -s -X POST "$BASE/api/v1/compat" -H "Content-Type: application/json" \
  -d "{\"chart_a_id\":\"$A\",\"chart_b\":{\"chart_id\":\"$ANDRES_ID\"},\"reason\":\"business\",\"language\":\"es\"}" | jq -r '.headline, .layers[0].line'

# 9. jargon scan
curl -s ... | jq -r '.headline,.detail,.layers[].line' | \
  grep -E "(Brahmin|Kshatriya|Varna|Bhakoot|Yoni|Nadi|Graha Maitri|navamsa|[0-9]+(st|nd|rd|th) house)" \
  && echo "JARGON LEAK" || echo "clean"

# 11. existing endpoint regression (shape intact, strings stripped)
curl -s -X POST "$BASE/api/v1/compatibility" -H "Content-Type: application/json" \
  -d "{\"chart_id_a\":\"$A\",\"chart_id_b\":\"$ANDRES_ID\",\"compatibility_type\":\"business\"}" | jq '.overall.score_pct, .ashtakoot.total'

# 12. cache hit (same generated_at within the day)
curl -s ... | jq -r '.generated_at'; sleep 5; curl -s ... | jq -r '.generated_at'
```

---

## Phase 2 (next prompt — do not build yet)
LK cross-conditions (`lk_cross_conditions.py`), `deep_read=true` per-layer `detail`
prose, Mercury cross-compat, real house-10/11 quality, graha-drishti aspects.
