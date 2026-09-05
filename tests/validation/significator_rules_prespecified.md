# Significator rules — PRE-REGISTERED

Fill this in and **commit it before assembling the cohort.** Timestamp is the
whole defence (this repo has 20+ dead hypotheses; at least two died because they
were invented after seeing a flattering chart). Modelled on
`tests/hora_rules_prespecified.py`.

---

## H1 — d10_career field ranking

**Hypothesis:** the person's real career field appears in the engine's top-3
ranked `careers[]` more often than chance.

**Chance baseline:** 3 / 45 distinct fields = **0.067** (hit@3). Also report hit@1
vs 1/45 = 0.022.

**Direction (one-tailed):** hit-rate **> chance**.

**Decision rule:** one-tailed binomial p < 0.05 over the cohort → the D-1/D-10/
Amatyakaraka significator voting carries real signal, keep `PLANET_CAREERS` as v1.
p ≥ 0.05 → not earning its keep; refine the significations (and re-register) or
stop presenting the ranked list as authoritative.

**Excluded by name (contaminated — used while building/adjusting the tables):**
_(list any chart you eyeballed while writing PLANET_CAREERS / d10_career)_

**Cohort (assembled AFTER this file is committed):** _n = ___; source ____

---

## H2 — concern_engines verdict direction

**Hypothesis:** the engine verdict's implied direction matches the real outcome
more often than a coin flip, per concern:
- funding / loan (gain): "supported" ⇔ the funding/loan actually came through.
- relationship (gain): "supported" ⇔ a significant relationship actually formed.
- separation (risk): "elevated" ⇔ a separation/serious strain actually occurred.
- health (risk): "elevated" ⇔ a real health event actually occurred.

**Chance baseline:** **0.50**.

**Direction (one-tailed):** accuracy **> 0.50**.

**Decision rule:** one-tailed binomial p < 0.05 per concern (min n≈15) → that
concern's significator set carries signal. p ≥ 0.05 → untuned; refine or
down-label that concern.

**Windowing note (do this honestly):** a verdict is a *present-state* read. Only
score a concern case where the outcome falls in (or adjacent to) the period the
engine was scored against — otherwise you are testing timing you did not claim.

**Excluded by name:** _(charts used while building concern_engines significators)_

**Cohort:** _n = ___ per concern; source ____

---

## Results log
Run `run_significator_validation.py`, paste the report into
`results_<date>.md`, and if a hypothesis dies write it up as
`negative_result_<name>.md` (a dead result is a real result).
