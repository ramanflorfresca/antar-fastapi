# Business-Timing / Dasha-Fortune study — pre-registered spec

Status: **CLOSED — NEGATIVE RESULT (2026-09-16).** H1 not supported. Do NOT ship
any business timing/vertical predictor to /ask. See "Final result" below.

## Final result (n=29; AA-only n=18)
Ran the pre-registered test (win-period fortune > loss-period fortune, MD+AD at
event dates) on the expanded cohort:
- **Full n=29:** win>loss 15/26 non-tie (58%), mean diff +0.23, one-sided p=0.279.
- **AA-only n=18 (birth-certificate times — best data):** 9/16 non-tie (56%),
  **mean diff +0.00**, p=0.402.
- **Null (labels swapped):** 11/26, symmetric (p=0.84) — as expected.

**The effect shrank to zero as data quality/quantity improved** (+0.59 at n=11 →
+0.23 at n=29 → +0.00 AA-only). That is the regression-to-the-mean signature of a
spurious small-sample signal. **Business venture success does not track the
running dasha lord's dignity in this data.** Same class of result as the D-2
wealth study — a plausible hypothesis, tested, falsified.

Caveats (why the door isn't 100% shut, but we still don't ship): the raw fortune
model is crude (D-9 dropped in the raw pipeline, coarse dignity weights,
approximate historical timezones, event-year granularity). A far more
sophisticated model *might* find something — but there is **no evidence** for it,
and the cleanest data sits dead on chance, so shipping would be a prediction
built on hope. If ever revisited: fix D-9/AD parity, confirm every time on
astro.com in a browser, pre-register a richer model, and require p<0.05 on AA-only.

---
## (Original pre-registration below — kept for the record)

## Background
- "Which vertical suits a chart" (naive sector→planet strength) was **falsified**
  in blind test: it inverted Akash (flagged his services win as a trap) and
  Shashi (rated his EV disaster #1). Dead — same fate as the D-2 wealth study.
- Reframed to **timing**: does venture fortune track the dignity of the running
  dasha lord? Engine: `antar_engine/business_timing.py`.
- **Magnitude/tier claims (billionaire vs millionaire) are OUT of scope** — that
  class was empirically falsified (D-2 wealth study). Only ordinal
  period-fortune is studied.

## Pre-registered hypothesis (LOCKED — do not change post-hoc)
**H1:** For an entrepreneur, the combined dasha-lord fortune during a documented
major business SUCCESS is **greater** than during a documented major FAILURE.

- **Fortune** = `business_timing.planet_fortune` = D-1 dignity + nature-aware
  placement (upachaya/Harsha: malefics/nodes strong in 3/6/11; benefics weak in
  6/8/12) + D-9 dignity/vargottama − node-shadow.
- **Period fortune at a date** = `0.6·fortune(MD lord) + 0.4·fortune(AD lord)`,
  MD/AD looked up at `<event-year>-07-01`.
- **Primary test:** one-sided binomial over the cohort (count win>loss),
  threshold **p < 0.05**. Secondary: mean(win − loss) with a permutation null.
- **Controls:** (a) label-swap null (randomly relabel win/loss → expect ~50%);
  (b) placebo score (a random planet's fortune → expect ~50%). Both MUST look null.

## Cohort criteria
- Founders/owners (not salaried execs).
- Birth time **Rodden AA or A**, confirmed on astro.com/Astro-Databank IN A
  BROWSER (search snippets are not sufficient — the agent's list needs this check).
- ≥1 documented major SUCCESS year and ≥1 documented major FAILURE year,
  ideally >2 years apart.
- Target **n = 30–50** (power: a true ~65% effect needs ~40 for p<0.05).

## Harness
- `GET /api/v1/debug/btiming-raw?birth_date&birth_time&lat&lng&tz` → computes a
  chart from raw birth data (no DB write) and returns `planet_fortune`, full
  `maha` + `antar` timelines, and `business_timing`. Same ephemeris + vimsottari
  as production; internally consistent across the cohort.
- Study runner: `/tmp/cohort_study2.py` (MD+AD resolution). Move into the repo
  (`scripts/`) when the cohort is finalized.
- NOTE: the raw pipeline's D-9 and antardasha may differ slightly from a given
  STORED production chart (older charts computed via a different path), but the
  cohort is scored entirely by this one pipeline, so it is internally consistent.

## Results so far
### n = 11 (birth times AA/A per search snippets — NOT yet browser-confirmed)
- MD-only: win>loss 5/7 non-tie (4 ties), mean diff +0.44.
- **MD+AD: win>loss 7/11 (0 ties), mean win 0.99 vs loss 0.40, diff +0.59, one-sided p = 0.274.**
- Inversions: Steve Jobs, Larry Flynt, Coppola, Branson.
- Verdict: **stable weak positive lean (~64%), NOT significant.** Direction held
  across MD→MD+AD resolution. Underpowered at n=11.

Cohort v1 (need browser-confirmed times): Trump AA, Martha Stewart AA, Steve Jobs
AA, Ted Turner AA, Hugh Hefner AA, Larry Flynt AA, Coppola AA, Coco Chanel AA,
Walt Disney A, Richard Branson A, Oprah A. (Excluded: Ford B, Hilton DD, Musk
noon, Kroc/Ellison/Hershey/Wynn no time.)

## Next steps (resumable)
1. **Expand cohort to ~30** — more founders with AA/A times + documented rise+bust
   dates (agent + browser confirmation).
2. **Browser-confirm every birth time** on astro.com (exact minute + Rodden rating).
3. Re-run `cohort_study2.py`; run the two null controls.
4. Only if H1 clears p<0.05 AND controls look null → consider a *soft* /ask
   surface ("you're in a strong vs lean dasha chapter"), never a venture/tier promise.
5. If it does not clear → document as a negative result (like D-2 wealth) and
   ship only the existing field-level + potential-band read.
