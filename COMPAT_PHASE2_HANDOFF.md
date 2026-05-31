# Compatibility 6-Layer Surface — Phase 2 Handoff

**Status: PHASE 2 BUILT — all 5 modules compile, all offline checks green. Live curls + deploy pending (no network egress from the build sandbox).**

⚠️ Gating note: Phase 1's handoff gated Phase 2 on Phase 1 verifying clean live. The
build sandbox can't reach Railway, so I built against Phase 1 as authored. Run the
Phase 1 curls after deploy if you haven't yet.

Phase 2 turns the Phase 1 stubs into real astrology and adds the optional LLM
synthesis — **without restructuring the spine** (`Compatibility.py` untouched this
round) and **without shipping unverified Lal Kitab rules** (LK library is gated off).

---

## What shipped

### 1. Real synastry — `antar_engine/compatibility_synastry.py` (new)
Replaces three Phase-1 "default 50" stubs with standard Parashari computation:
- **`planet_dignity_score`** — exaltation 95 / own 80 / friend 65 / neutral 52 / enemy 38 / debilitation 20 (standard tables; reuses the spine's `SIGN_RULER`/`PLANET_FRIENDS`).
- **`house_quality_score`** — B's planets in A's house H, scored by dignity (benefic +5 / malefic −5). Replaces the engine's fixed 70/90/95/85 constants **and computes houses 10 & 11, which the engine never produced**.
- **`mercury_cross_compat`** — Mercury-to-Mercury harmony (the engine only did Venus/Mars).
- **`cross_aspect_harmony`** — cross-chart graha drishti to lagna + 7th (Mars 4/7/8, Jupiter 5/7/9, Saturn 3/7/10, all planets 7th); benefic aspects raise, malefic lower.

### 2. Layer mapping upgraded — `antar_engine/compatibility_layers.py` (edited)
- `communication.mercury_compatibility` → real Mercury cross-compat (was 50).
- `public.house_7 / house_10 / house_11` → real dignity-based house quality (was 95-fixed + two 50 stubs).
- **`friction` gained a 4th source `cross_aspect_harmony`**; re-weighted to `mutual_6_8 0.35 / nadi_dosha 0.25 / growth_areas 0.15 / cross_aspect_harmony 0.25`.
- `build_compat_response` now accepts `deep_read_details` (→ per-layer `detail`) and `lk_insights` (→ top-level key, only when non-empty), both jargon-stripped.

> **Expected score drift from Phase 1:** because `public`, `communication`, and `friction`
> now use real chart data instead of flat 50s, overall scores for the same pair will
> move vs Phase 1. That's the point — the numbers are now astrology-driven.

### 3. deep_read synthesis — `antar_engine/compatibility_deepread.py` (new)
`POST /api/v1/compat` now accepts **`deep_read: true`**. When set, each layer's reserved
`detail` field is filled by **Claude Sonnet** (`claude-sonnet-4-20250514`), framed
"how to use it" (FLOW/MIXED) or "how to work with it" (STRAIN), grounded only in the
computed layer scores/badges/lines + reason/role direction. Plain English, no jargon,
no gendered terms. Cached per `(layers-hash, reason, role, day)`. Fully graceful —
returns `{}` (no detail) if the client is unavailable or anything fails. The `detail`
key is in the translate allowlist, so es/pt deep reads translate automatically.

### 4. LK cross-conditions — `antar_engine/lk_cross_conditions.py` (new, **DISABLED**)
10-condition draft library (`ENABLED = False`, every condition `founder_confirmed=False`):
`sleeping_awakened, pitri_rin_clear, matri_rin_clear, mutual_6_8, cross_vish,
cross_guru_chandala, cross_shrapit, manglik_balance, kaal_sarp_relief, benefic_on_blank`.
`evaluate_cross_conditions(...)` returns `[]` while disabled, so **nothing here touches
the live response**. Each condition declares the layer it would inform and carries a
DRAFT predicate + user-facing line for your review. **Founder action to enable:** confirm
each predicate, set its `founder_confirmed=True`, then flip `ENABLED=True`. Same
build→gate→confirm pattern as Business-Fit Signatures.

---

## Offline verification (ran in sandbox — all green)

```
dignity Sun@Aries=95  Sun@Libra=20  Saturn@Capricorn=80          ✅
mercury cross-compat = 60 (real, was 50 stub)                     ✅
house quality A.10 = 90 (engine NEVER computed house 10)          ✅
cross_aspect_harmony = 44 (malefic aspects pulling below 60)      ✅
resolve_source: mercury/house_10/cross_aspect all non-stub        ✅
friction now has 4 sources                                        ✅
full response: 6 layers fixed order, valid score/label            ✅
deep_read_details attach to layer.detail + stripped               ✅
lk_insights absent when empty (contract stable while disabled)    ✅
LK gate: enabled=False, 10 conditions, 0 founder_confirmed, eval=[] ✅
all 5 modules py_compile                                          ✅
```
Not testable offline (guarded no-ops): the live Claude Sonnet deep_read call and es/pt
translation (no network/API key in the sandbox).

---

## Files touched
**New:** `compatibility_synastry.py`, `compatibility_deepread.py`, `lk_cross_conditions.py`
**Edited:** `compatibility_layers.py` (synastry wiring + deep_read/LK attach), `main.py` (via `patch_compat_phase2.py`: `deep_read` param, cache key, LK + deep_read hooks)
**Untouched:** `Compatibility.py` (spine), `compatibility_templates.py`

---

## Deploy (source files only — never patch scripts or .bak)
```bash
cd ~/antarai && source venv311/bin/activate
git add main.py \
        antar_engine/compatibility_layers.py \
        antar_engine/compatibility_synastry.py \
        antar_engine/compatibility_deepread.py \
        antar_engine/lk_cross_conditions.py \
        COMPAT_PHASE2_HANDOFF.md
git commit -m "feat: compat Phase 2 — real synastry (Mercury/house-dignity/graha-drishti), deep_read synthesis, gated LK library"
git push origin main
```

## Live verification (run after deploy)
```bash
BASE="https://antar-fastapi-production.up.railway.app"; A="de02bb52-d43a-4b09-be25-b45a07bfbf8a"
ANDRES_ID="6ec6311c-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

# deep_read populates per-layer detail
curl -s -X POST "$BASE/api/v1/compat" -H "Content-Type: application/json" \
 -d "{\"chart_a_id\":\"$A\",\"chart_b\":{\"chart_id\":\"$ANDRES_ID\"},\"reason\":\"business\",\"deep_read\":true}" \
 | jq '.layers[] | {key, badge, detail}'
# Expect: each layer has a non-empty "detail" paragraph (jargon-free).

# deep_read=false (default): no detail key
curl -s -X POST "$BASE/api/v1/compat" -H "Content-Type: application/json" \
 -d "{\"chart_a_id\":\"$A\",\"chart_b\":{\"chart_id\":\"$ANDRES_ID\"},\"reason\":\"business\"}" \
 | jq '.layers[0] | has("detail")'   # false

# public/communication scores now move with real synastry (not flat 50)
curl -s -X POST "$BASE/api/v1/compat" -H "Content-Type: application/json" \
 -d "{\"chart_a_id\":\"$A\",\"chart_b\":{\"chart_id\":\"$ANDRES_ID\"},\"reason\":\"business\"}" \
 | jq '.layers[] | select(.key=="public" or .key=="communication") | {key,badge}'

# LK stays invisible while disabled
curl -s ... | jq 'has("lk_insights")'   # false

# jargon scan incl. deep_read detail
curl -s ... -d '{...,"deep_read":true}' | jq -r '.headline,.detail,.layers[].line,.layers[].detail' \
 | grep -E "(Brahmin|Varna|Bhakoot|Yoni|Nadi|navamsa|[0-9]+(st|nd|rd|th) house)" && echo "LEAK" || echo "clean"
```

---

## Deferred / known limits (next round)
- LK library stays OFF until founder confirms the 10 predicates (then `founder_confirmed=True` + `ENABLED=True`).
- `cross_aspect_harmony` weighs aspects to lagna + 7th only; extending to 10th/4th and adding aspect *strength* by orb is a refinement.
- deep_read + response caches are in-process (per worker, reset on deploy) — move to Supabase if you want durable/cross-worker caching.
- Spine (`Compatibility.py`) still carries the audit's non-blocking items (yin_yang constant 70, dead birth_date params) — intentionally left, as Phase 2 reads the engine rather than rewriting it.
```
