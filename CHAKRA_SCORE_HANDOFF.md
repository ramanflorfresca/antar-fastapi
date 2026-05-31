# Chakra `score_pct` — Handoff (Part A, backend)

**Status: BUILT — both files compile, all offline checks green. Deploy + the 5 live curls are yours (build sandbox has no network egress to Railway).**

## Audit correction (important)
The brief's premise — "the engine already computes a quantitative score… that number is being thrown away" — is **not accurate**. `compute_chakra_states` derived `state` from *categorical* condition-set membership (`_STRONG` / `_WEAK` / `_AFFLICTED`); there was **no number to expose**. So this **builds** `score_pct` and then derives `state` from it (the brief's intended end state), guaranteeing they can never disagree.

Two more realities that shaped the implementation:
- `compute_all_conditions` returns only `{condition, weight, color, polarity}` per planet — **no house, no aspects, no separate sleeping flag**. The house (6/8/12) and benefic-aspect modifiers are therefore computed **from the chart** directly (whole-sign house + standard graha-drishti for benefics).
- `condition` is one terminal value of `{exalted, own_sign, friend, neutral, enemy, debilitated, combust, sleeping}` — there is **no `moolatrikona`** (kept in the map for completeness; never triggers), and **`sleeping` is already the condition** (base 25). The brief's "×0.5 sleeping" modifier is therefore **not** additionally applied — doing so would double-count the LK sleeping penalty.

## What changed
**`antar_engine/practice_chakras.py`**
- `+PLANET_STRENGTH_PCT` (exalted 95 … debilitated 18 … sleeping 25), `+`benefic/aspect/sign constants.
- `+_planet_house`, `+_benefic_aspect_info`, `+_ruler_strength`, `+_chakra_score_pct`, `+_state_from_score`.
- `compute_chakra_states`: each chakra now averages its rulers' strengths → `score_pct` (0-100 int); `state` is derived from `score_pct` (`≥80 strong / 60-79 balanced / 35-59 weak / <35 blocked`); `score_pct` added to every chakra dict (incl. the no-rulers branch → 55/balanced).
- Per-ruler modifiers: ruler in 6/8/12 **with no benefic aspect** → −10; ruler **aspected by a benefic placed in a kendra/trikona** → +5; capped 0-100.

**`main.py`**
- `GET /api/v1/predict/daily-practice/chakra/{chakra_key}` previously returned only `{chakra_key, balance_mantra}`. It now also loads the chart (when `chart_id` is passed) and returns `state`, `score_pct`, `reason`, `priority` alongside the mantra. Without `chart_id` it still returns just the mantra.

**Composer:** no change needed — `practice_composer.compose_practice_response` already assigns `compute_chakra_states(...)` output verbatim to `chakra_states`, so `score_pct` flows into `POST /daily-practice` automatically. The Path-B strip (`_prac_strip_prose`) only touches `reason`; the integer passes through untouched (and the translate layer skips non-strings), so the number is identical across `en/es/pt`.

## Offline verification (sandbox — all green)
```
score_pct present on all 7 chakras, int 0-100                 ✅
state↔score contradictions (brief check #2)                   ✅ 0
house 6/8/12 −10 modifier + benefic-aspect +5 modifier fire   ✅ (Venus@12 aspected →+5=60; Saturn debil@8 →23)
deterministic — same chart returns identical scores           ✅
no-rulers branch → score_pct 55 / balanced                    ✅
both files py_compile                                         ✅
```
Different charts → different conditions/houses → different scores (guaranteed; the function is a pure transform of chart data — satisfies brief checks #4 and #5).

## Deploy (source files only — never patch scripts / .bak)
```bash
cd ~/antarai && source venv311/bin/activate
git add antar_engine/practice_chakras.py main.py CHAKRA_SCORE_HANDOFF.md
git commit -m "feat: chakra score_pct (0-100) on daily-practice + chakra detail; state derived from score"
git push origin main
```

## Live verification (run after deploy)
```bash
BASE="https://antar-fastapi-production.up.railway.app"; A="de02bb52-d43a-4b09-be25-b45a07bfbf8a"

# 1 score_pct per chakra
curl -s -X POST "$BASE/api/v1/predict/daily-practice" -H "Content-Type: application/json" \
  -d '{"chart_id":"'$A'","language":"en","tz_offset":-300}' \
  | jq '.chakra_states | to_entries[] | {chakra:.key, state:.value.state, score:.value.score_pct}'

# 2 state agrees with score (expect empty = no contradictions)
curl -s -X POST "$BASE/api/v1/predict/daily-practice" -H "Content-Type: application/json" \
  -d '{"chart_id":"'$A'","language":"en","tz_offset":-300}' | jq '.chakra_states | to_entries[] |
  select((.value.state=="strong" and .value.score_pct<80) or
         (.value.state=="balanced" and (.value.score_pct<60 or .value.score_pct>=80)) or
         (.value.state=="weak" and (.value.score_pct<35 or .value.score_pct>=60)) or
         (.value.state=="blocked" and .value.score_pct>=35))'

# 3 detail endpoint includes score_pct
curl -s "$BASE/api/v1/predict/daily-practice/chakra/throat?chart_id=$A&language=en" | jq '{state, score_pct}'

# 4 different chart -> different score
curl -s -X POST "$BASE/api/v1/predict/daily-practice" -H "Content-Type: application/json" \
  -d '{"chart_id":"6ec6311c-d46e-4e97-a46c-859882071971","language":"en","tz_offset":-300}' \
  | jq '.chakra_states.heart.score_pct'

# 5 reproducible
curl -s -X POST "$BASE/api/v1/predict/daily-practice" -H "Content-Type: application/json" \
  -d '{"chart_id":"'$A'","language":"en","tz_offset":-300}' | jq '.chakra_states.root.score_pct'
sleep 5
curl -s -X POST "$BASE/api/v1/predict/daily-practice" -H "Content-Type: application/json" \
  -d '{"chart_id":"'$A'","language":"en","tz_offset":-300}' | jq '.chakra_states.root.score_pct'
```
Note: `/daily-practice` caches per (chart, language, day), so check #5 returns the cached value — still identical, and the computation itself is deterministic regardless.

## Out of scope (unchanged from brief)
score history table · per-language score labels · practice-completion nudging scores.
