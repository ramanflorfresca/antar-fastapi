# antar_engine/kp — Krishnamurti Paddhati (KP) sub-system

A **parallel, isolated** house system powering (post-gate only) the **Ask** surface
(binary / timed questions) and **intraday windows**. It does **not** modify the
Lahiri / whole-sign base chart. KP runs a SECOND chart: **Placidus cusps + KP-Old
(Krishnamurti) ayanamsa + the 249-sub division**.

> **Doctrine:** Python computes the entire deterministic sub-lord chain; Claude
> only narrates the structured verdict bundle. **Zero KP jargon** on any user
> surface (no cuspal sub-lord / significator / house numbers / planet names).
> KP stays **quarantined** behind the backtest gate until it passes **and Raman
> approves**. No KP output reaches a user before then.

## Modules
- `kp_chart.py` — **A1**. Placidus cusps under `swe.SIDM_KRISHNAMURTI` (asserted
  before every ephemeris call), the verified 249-segment sub table, and
  `(sign-lord, star-lord, sub-lord)` resolution for every cusp and planet.
- `kp_significators.py` — **A2**. 4-level significator hierarchy + node agency,
  per-question house groupings, and the cuspal-sub-lord verdict engine
  (`{verdict, confidence 0-3, drivers}`) with the 11th-cusp materialization gate
  and Bhavat-Bhavam loss handling.
- `kp_horary.py` — **A3**. Number horary (1-249) cast for the moment of the
  question, Ruling Planets, and a Vimsottari-based timed window.
- `kp_backtest.py` — **A4. THE GATE.** Scores a binary-outcome validation set;
  opens the gate only at `>= 70%` hit-rate over `>= 8` cases. `is_gate_open()` is
  the single source of truth A5 must consult.

## Auditable doctrinal choices (all flagged in code headers)
- **Ayanamsa:** KP-Old (`swe.SIDM_KRISHNAMURTI`).
- **Node:** mean (Lahiri base uses true node — deliberately not shared).
- **249 = 243 sub cells + 6 sign-boundary splits** (30/90/150/210/270/330°);
  asserted at import.
- **Horary cusps:** number-anchored ascendant + moment Placidus cusp spacing.
- **Timing:** `DAYS_PER_YEAR = 365.25`; RP = civil weekday lord (sunrise day
  boundary is a documented foundation-build limitation).

## Run (on the mac venv — needs Swiss Ephemeris)
```
cd ~/antarai && source venv311/bin/activate
python -m antar_engine.kp.selftest        # A1-A3 smoke test
python -m antar_engine.kp.verify_a1       # A1 acceptance vs reference charts
python -m antar_engine.kp.kp_backtest     # A4 gate (RED until validation set added)
```

## To pass the gate (what's still needed from Raman)
1. **Reference KP charts** — fill `validation/kp_reference_charts.json`
   `expected_cusp_sublords` from a trusted KP source (KPStarOne / astro-seek KP
   mode), then `verify_a1` reports per-cusp match.
2. **Binary validation set** — copy `validation/kp_binary_validation.template.json`
   to `validation/kp_binary_validation.json` and fill real past questions with
   known yes/no (+ rough dates). `kp_backtest` then scores and writes
   `validation/kp_gate_status.json`.

**A5 (integration into Ask + intraday) is NOT built** — it runs only after the
gate passes and Raman gives the go.
