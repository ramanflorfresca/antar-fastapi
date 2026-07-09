# Ask / `/predict` port — promise → timing → earned-confidence → grounded-narrate

Rebuild the Ask surface on the daily engine's clean spine (`vote → net → choose →
grounded-narrate + no-invention gate + evidence`), but adapted to Ask's shape: a
*question* fixes the scope, and the answer is derived, never asserted. Governs
the two known defects — **over-claimed confidence** and **jargon leaks**.

See also: `COWORK_DAILY_VOTE_GROUNDING_HANDOFF.md` (the spine this reuses).

## Confidence philosophy (the spec's north star)

Confidence is a **two-stage, gated product**, and it's a **dial toward agency —
never a dead "no"**:

1. **Promise** — is the event even on the table? Natal house/lord/karaka + the
   **yogas** that promise it, **confirmed in the divisional chart** that rules the
   matter (D9 marriage, D10 career, D2 wealth, D7 children).
2. **Timing** — *only if promised*, WHEN it ripens (dasha + transit + varshphal).

`confidence = promise × timing`. A weak/absent promise NEVER says "you don't have
this" — it **softens the tone and shifts weight onto agency** (remedy, mantra,
practice), because ~30% past-life + ~30% kundalini + ~30% willpower means effort
moves the needle. `agency_weight = 1 − promise` governs how hard the answer leans
on what-to-do vs. when-to-receive. Everything connects: prediction → action →
remedy → mantra → practice, as one graded output.

"Over-claimed confidence" = **stated > earned** (today the verdict comes from
timing locks alone, no promise gate; the narrator can assert "you will" when the
math earned "may"). The fix is EARNED confidence — bold when the chart is bold,
humble-but-actionable when thin — not blanket hedging.

## Slices

### ✅ Slice 1 — Promise engine + earned confidence + agency dial *(this commit)*
- **`antar_engine/ask_promise.py`** — `assess_promise(chart_data, houses, karakas,
  concern)` → `{promise∈[0,1], band, agency_weight, factors}` from four classical
  evidences: karaka dignity (D1), house-lord dignity + Sarvashtakavarga bindus,
  relevant yogas (dhana/raja/kalatra… vs. arishta/dosha), and **divisional
  confirmation** (D9/D10/D2/D7…). Pure, fail-open, decoupled (no circular import).
- **`build_convergence_timing`** now returns `promise`, `promise_band`,
  `promise_factors`, `agency_weight`, and `confidence = promise × timing-scalar`.
- **Over-claim guard:** strong timing + weak/absent promise → the opening sentence
  softens (enum unchanged) via `_soften_ask_phrase` — honest, keeps the window,
  leans to agency, never "you don't have this".
- Additive + fail-open: `promise=None` ⇒ byte-identical to prior behavior.
- Verified on Raman `a4c9d57b`: career (moderate promise + timing now) → conf 0.58;
  marriage (moderate promise, no window) → honest 0.08, agency 0.45; softening
  fires on weak/absent bands.

### ✅ Slice 1b — Era/context significations layer *(this commit)*
Sign-dignity alone read the nodes as "neutral" and never weighted the running
Mahadasha lord — so a Rahu-MD-in-11th (a textbook modern tech/fame/gains chapter)
scored as nothing.
- **`antar_engine/planet_significations.py`** — `ERA_SIGNIFICATIONS` (classical +
  modern per planet; Rahu-modern = technology / AI / media / fame / foreign /
  disruption); `contextual_strength(planet, chart_data)` scoring house-context
  (nodes are functional benefits in 3/6/11, 11th best for Rahu) + conjunction
  color + dispositor channel; `dasha_relevance(planet, concern, houses)`.
- **`assess_promise`** now scores node karakas contextually and adds the running
  MD/AD lord as the era's significator (weighted by relevance).
  `build_convergence_timing` extracts + passes the current lords. Fail-open.
- Verified on Raman `a4c9d57b`: Rahu reads at max strength 2.0 (11th + Sun/Venus
  + Mars-10th dispositor); career promise 0.58 → 0.67 (**strong**) under Rahu MD,
  wealth → 0.68, business → 0.78 — while marriage/children barely move (Rahu
  relevance 0.3), so no spurious inflation.

### ✅ Slice 2 — Agency-scaled narration + practice routing *(this commit)*
`agency_weight` now steers the answer, backend-only (response contract
read/next/timing/practices unchanged — no frontend change):
- **`consultation_prompt_block`** gains an AGENCY FRAMING line keyed to
  `promise_band`: strong → lead with timing, whisper the practice; moderate →
  balance; weak/absent → lead with what to DO (effort + remedy + practice),
  never fatalistic.
- **`/ask` consultation path** scales the practice-card count by `agency_weight`
  (`limit = clamp(round(1 + agency_weight·3.5), 1, 4)`): strong promise → 2
  cards, weak/absent → 4. `agency_weight=None` → default 3 (unchanged).

### ✅ Slice 3 — Verdict/enum honesty *(this commit)*
Slice 1 softened the opening for weak/absent promise but left the verdict enum +
client chip claiming SUPPORTED/LIKELY. `promise_adjusted_verdict(verdict, band)`
reconciles them — DOWNGRADE-only, existing enums:
`absent + (YES/SUPPORTED/LIKELY) → NOT_YET`; `weak + (YES/SUPPORTED) → LIKELY`.
Applied to `conv["verdict"]` (matches the softened opening + the prompt's stated
verdict) and to the `/ask` client chip (`_det_verdict`, incl. the event-engine
value). Fail-open (band=None → unchanged).

### ✅ Slice 4 — Weighted, continuous timing convergence *(this commit)*
Replaced the binary 2-of-3 cliff with a weighted `timing_score`: Vimshottari
primary (1.2), Chara (1.0), Varshphal (0.7); convergence bar = 1.2, so a lone
Vimshottari lock qualifies while Chara/Varshphal alone (< 1.2) still need a
second system. Confidence is now continuous (scaled by `timing_score / 2.9`).
Output contract preserved (`lock_count` kept; `timing_score` added).
- Verified on Raman: **wealth / business / property flip NOT_YET → SUPPORTED**
  (lone Vimshottari lock, score 1.2 — the primary timing system was being
  dismissed as "building phase"); **education stays NOT_YET** (score 0.7, a lone
  weak system — correct discrimination); marriage/children stay NO. The promise
  layer keeps the flips honest (wealth conf 0.56, business 0.64, not inflated).

### ✅ Slice 4b — net(t) temporal-overlap convergence *(this commit)*
Slice 4 summed ALL active systems' weights regardless of whether their windows
overlap in time — so two systems active in *different* windows could report
"converged" when they never coincide. Slice 4b builds `net(t)` over monthly
buckets: each active system adds its weight to the months its window covers; the
PEAK overlap is `timing_score`, and the contiguous run at/above the bar around
the peak is the window. Convergence now means the systems truly stack.
- Verified: overlapping Vim+Chara → peak 2.2, window = the stacked span;
  NON-overlapping → 1.2 (Vim alone, no false 2.2); lone weak (0.7) → no window.
- On Raman: identical to Slice 4 (his systems genuinely overlap) — no regression,
  strictly more correct for staggered-window charts.

Remaining (nice-to-have): systems returning MULTIPLE graded windows per period
(currently one window each) would let net(t) find secondary peaks too.

### ✅ Slice 5 — Jargon-leak gate on the Ask narration *(this commit)*
Finding: the `read`/`next` are ALREADY covered by a comprehensive
validate→regenerate→fail-closed voice-gate (`narration_validator.validate_narration`
catches planet/sign/house names, the full Sanskrit/system set — dasha, mahadasha,
nakshatra, lagna, karaka, vimshottari, jaimini, chara, varshphal — MD/AD codes,
energy constructions). The original "jargon leaks" defect was largely fixed by
that gate (`[ask-voice-gate 2026-06-16]`). The real remaining gap was **actions[]**,
which weren't validated on the happy path. Slice 5 closes it, respecting the
gate's deliberate no-blind-stripping design:
1. actions[] join the voice-gate's violation check → a jargon-y action triggers
   the same regenerate→fail-closed as the prose.
2. a final non-destructive net drops any residual jargon-carrying action after
   payload assembly (a list — safe to prune).
Note: `_AREA_MENTIONS`-style life-area no-invention was intentionally NOT ported —
the Ask question fixes one concern and the verdict is Python-authoritative, so
domain-drift isn't the failure mode; forcing it risks false rejects.

### Slice 6 — es/pt coverage
`_AREA_MENTIONS` and the softened phrases are EN-only; extend for the live LATAM
surface.

## When / how / what (how one scoped vote pool answers all three)
- **WHEN** — votes time-indexed → `net(t)` peak = the window.
- **HOW** — net polarity + magnitude of the scoped area now = the state read.
- **WHAT / SHOULD I** — net sign = decision; magnitude = conviction; factors +
  timing window = the grounded actions and when to act.
