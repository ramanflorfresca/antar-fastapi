# Significator validation harness

Turns "untuned" into "measured" for the two live v1 significator engines —
`d10_career` (career-field ranking) and `concern_engines` (funding / relationship
/ separation / health verdicts). Same discipline as `tests/hora_rules_prespecified.py`,
which is how the D-2 wealth chain was proven dead (p=0.962).

## The rule you must follow (or the number is worthless)
1. **Pre-register first.** Write the hypothesis + the chance baseline + the
   expected direction in `significator_rules_prespecified.md` and commit it
   **before** you assemble the cohort. See that file.
2. **Never test on the charts that generated the significations.** The
   `PLANET_CAREERS` / concern significator tables are classical defaults; any
   person whose chart was eyeballed while building or "fixing" a table is
   contaminated and must be excluded by name.
3. **Label from real, dated, on-the-record outcomes** — someone whose actual
   career field / funding event / marriage / separation / health event is a
   matter of record. No self-reported vibes, no fabricated charts.

## How to run
```bash
python3 tests/validation/run_significator_validation.py path/to/fixtures.json --out tests/validation/results_<date>.md
```
Pure-Python; needs no anthropic / supabase / network. With no path it runs
`fixtures.example.json` (dummy charts → everything "unavailable", proving the
pipeline works before you add data).

## Fixtures schema (`fixtures.json` = a JSON list of cases)
Every case needs a **real** `chart_data` — dump it from the live system for that
person (do not hand-build charts). Fields:

**career case**
```json
{ "id": "person-slug", "type": "career",
  "true_fields": ["engineering", "technology"],   // what they ACTUALLY do,
  "chart_data": { ...full chart dump... } }        // in the engine's vocabulary where possible
```
Scored: is a `true_field` in the engine's top-1 / top-3 ranked `careers[]`?
Chance = K / (#distinct fields in `PLANET_CAREERS`, currently 45), so hit@3 ≈ 0.067.

**concern case**
```json
{ "id": "person-slug", "type": "concern",
  "concern": "funding",              // funding|loan|relationship|separation|health
  "polarity_kind": "gain",           // "gain" (funding/relationship) or "risk" (separation/health)
  "outcome_positive": true,          // did the GOOD thing happen? (got funding / stayed together / stayed well)
  "chart_data": { ...dump... }, "dashas": { ...dump... } }
```
Scored: does the engine verdict's implied direction match `outcome_positive`?
Chance = 0.50. The mapping is verdict-vocabulary-aware (`_subject_level`):
"well supported"/"elevated" = subject HIGH; "not indicated"/"minor"/"steady" =
LOW; gain→high=positive, risk→high=negative.

## Reading the result
`hit@3 one-tailed p < 0.05` (career) or `accuracy p < 0.05` (concern) = the
engine beats chance on this cohort → the significations carry real signal, keep
them. `NOT distinguishable from chance` = same status as D-2 wealth: the METHOD
runs but the MAPPING isn't earning its keep — refine the significator sets (and
re-register) or down-rank the surface. A dead result is a valid, publishable
result — add a `negative_result_*.md` like the others in `tests/`.

## Getting real `chart_data`
The engines consume the same `chart_data`/`dashas` the live pipeline builds
(`planets`, `lagna`, `divisional_charts.d10`/`.d9`). Easiest source: pull the
stored chart row / the `/predict` context for a known `chart_id` and paste the
`chart_data` + `dashas` objects into a case. Keep a cohort of ≥15–20 per engine
for the binomial to have any power.
