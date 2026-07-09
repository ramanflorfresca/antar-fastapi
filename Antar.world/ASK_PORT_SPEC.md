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

### Slice 2 — Agency-scaled narration + remedy/practice routing
Wire `agency_weight` into the answer: high promise → whisper the practice, lead
with timing; low promise → lead with the remedy/mantra/practice for that window.
Hook already exists — `build_convergence_timing.relevant_planets` is computed
"to pick domain-matched practices" and `patch_ask_domain_practices` wires them;
formalize the inverse-to-promise weighting.

### Slice 3 — Verdict/enum honesty
Reconcile the client-facing verdict chip with promise. Today the enum (SUPPORTED/
LIKELY/…) is timing-only; decide whether a weak-promise SUPPORTED should downgrade
the chip (using existing enums, no new ones) so the chip matches the softened copy.

### Slice 4 — Unify the timing locks into weighted, time-indexed votes
Replace the binary 2-of-3 `_vimshottari_lock`/`_chara_lock`/`_varshphal_lock` with
signed weighted votes over the horizon → `net(t)`; the peak crossing the threshold
is the "when". Removes the brittle 2-of-3 cliff (a lone strong system stops reading
as "building phase"); confidence becomes continuous.

### Slice 5 — No-invention gate + jargon scrub on the Ask narration
Port the daily `_AREA_MENTIONS` no-invention gate + `output_strips` onto the Ask
`read`/narration so it can only speak to computed factors — the jargon-leak fix.

### Slice 6 — es/pt coverage
`_AREA_MENTIONS` and the softened phrases are EN-only; extend for the live LATAM
surface.

## When / how / what (how one scoped vote pool answers all three)
- **WHEN** — votes time-indexed → `net(t)` peak = the window.
- **HOW** — net polarity + magnitude of the scoped area now = the state read.
- **WHAT / SHOULD I** — net sign = decision; magnitude = conviction; factors +
  timing window = the grounded actions and when to act.
