# Relationship bands — pre-registered validation spec

Status: **OPEN — NOT YET TESTABLE (written 2026-10-12, before any data was analysed).**
First run on our own users (2026-10-12): 11 ever-married people, 4 divorced/separated: **NOT TESTABLE**; smallest detectable odds ratio 50+.
Rules under test live in `antar_engine/relationship_foundation.py` (layer 2), `relationship_pattern.py` (layer 1) and
`relationship_timing.py` (layer 3). They are v1 classical defaults. Nothing about them has been checked against real outcomes.

## Why this exists
The product now says things about people's relationships from these rules (a bond that "asks for more deliberate care", a stretch that
"runs on romance, not commitment", a season that is a "fight, not a final break"). The earlier studies (business timing n=29, D-2 wealth,
Hora) all started as plausible hypotheses and ended on chance once the data was clean. These rules get the same treatment: pre-register,
test against a control, remove what does not beat chance.

## Hypotheses (LOCKED - do not change after looking at data)
**H1 (primary - the foundation band).** Among people who have ever been married, those whose natal chart reads **fragile**
(`analyze_foundation(chart)["foundation"]["band"] == "fragile"`) have a **higher** rate of divorce or separation than those who do not.
- Test: one-sided Fisher exact on the 2x2 (fragile vs not) x (divorced/separated vs still married). Pass bar: **p < 0.05**.
- Cohort that counts: **Rodden AA or A only** (birth time from a certificate or equally reliable). Lower-rated charts are reported, never decisive.
- Effect size reported with a Woolf CI. A significant p with a CI that includes 1.2 is "weak", not "validated".

**H2 (components).** Same test for each part of the band separately: sustenance = fragile; spouse-indicator state in {detached, burdened};
navamsa verdict = weak. Bonferroni across the three (alpha 0.05 / 3).

**H3 (continuous score).** The band's underlying score ranks divorced/separated above still-married: AUC > 0.5 with permutation p < 0.05.

**H4 (timing - layer 3, needs dated events).** For people with dated marriage / divorce events, the running-period **season**
(`classify_season`) at the event date, versus the SAME person's random adult dates (within-person control, >=20 random dates each):
- the season is **ending or friction** more often at a divorce/separation date than at random dates, and
- the season is **opening** more often at a marriage date than at random dates.
Test: paired permutation across people; pass bar p < 0.05 on AA/A only.

**H5 (layer 1).** Love-style `falls_in_easily` is over-represented among people with >=2 marriages/divorces versus `slow_then_steady`.

## Controls (must look null, or the result is discarded)
- **Label-swap null:** outcomes shuffled 5,000 times; the real statistic must beat the shuffled distribution, not just cross a p-value.
- **Placebo band:** a random assignment with the same share of "fragile"; its p-value must not be small.
- **Power:** reported with every run. A run whose minimum detectable odds ratio is above ~4 is **not evidence either way** and is labelled so.

## Data needed (and why we cannot run it yet)
- Our own users: 14 ever-married charts with a known outcome (9 married, 5 separated/divorced), no reliable birth-time grading, no dated
  marriage/divorce events. At that size even a true odds ratio of 3 is detected less than a quarter of the time, and after removing duplicate birth records only 11 people remain: this is **not testable**.
- Needed for H1 (80% power, one-sided alpha 0.05, ~30% fragile, 20-40% base rate of divorce/separation): about **110-120** ever-married people to
  detect an odds ratio of 3, about **250-325** for an odds ratio of 2, and **700-1,000** for 1.5. The runner prints the figure for the actual cohort.
- Needed for H4: dated marriage/divorce events with AA/A birth times. Source: the Astro-Databank research export requested in
  `ASTRODIENST_data_request_email.md` (Marriage, Divorce/Separation, Relationship start/end, Rodden AA/A). Public-figure marital histories
  must come from the export or a cited source - never from memory.
- Run: `venv311/bin/python antar_research/validate_relationship_bands.py --csv <export.csv>` (columns documented in the script header).

## What a result changes in the product
- **H1/H3 pass:** the band may be described to users as a tendency worth attention (still never a verdict, still soft for married readers).
- **H1/H3 fail on adequate power:** the fragile/mixed/sound wording is **removed from user-facing text**; the engine can stay as an internal
  signal only. Same policy as the D-2 wealth and business-timing rules.
- **Underpowered:** nothing changes except that this document and the PR keep saying "unvalidated".
