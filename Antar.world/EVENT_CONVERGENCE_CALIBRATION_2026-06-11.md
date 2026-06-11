# Event Convergence Engine — Calibration Round 1 Findings
**Date:** 2026-06-11 · **Commits:** `da53085`, `b967a73` (on top of rebuild `464a9f2..4527b05`)
**Data:** 15 founder-confirmed events (Raman ×10, Rishipal ×5), real sidereal chronology 1960–2036 (`real_chronology_1960_2036.json`), full candidate tables via `scripts/event_convergence_harness.py --explain`.

---

## Headline numbers

| configuration | precision | painful-wrong |
|---|---|---|
| rebuild as briefed (point-wise DT lock) | 0/9 | 2 |
| + era-Jaimini + delivery lock + anchoring (current) | 2/10 (20%) | 2 |
| confirmed-marriage mode (anchor injected) | 3/10 (30%) | 2 |
| **ceiling** (perfect selection from qualifying sets) | **~7/12 (58%)** | — |
| acceptance gate | ≥60% | 0 |

The gate does not pass and **cannot pass even at ceiling** with the current lock definitions. Past-event signature stays OFF the launch path (as the brief already mandates).

## Finding 1 — the double transit, as specified, carries no signal (measured)

Activation at the 15 true event dates vs background (quarterly samples 1985–2025, same charts/targets):

| condition | at truth | background |
|---|---|---|
| Jupiter on event house | 40% | 33% |
| Saturn on event house | 27% | 32% |
| Jupiter on house lord | 33% | 34% |
| Saturn on house lord | 33% | 33% |
| Jupiter on D9 lord | 27% | 33% |
| Saturn on D9 lord | 20% | 33% |
| any 2-planet variant (4 tested) | 13–40% | 16–48% |

Every formulation tracks background. Two true events (Raman's 2nd child Oct 2003, Rishipal's divorce 2005–06) activate **nothing**. Sign-level graha-drishti double transit on house/lord/D9-lord targets, judged from Lagna and Moon, does not discriminate on this ground truth. It now sits as an *alternative* trigger (config `double_transit_enabled`), fully computed and traced, but the third lock defaults to the **karaka-PD delivery rule** (which does carry signal — see below).

**Founder decision needed:** is there a degree-based / bhava-based DT formulation, or should the year-gate be **Varshphal** per your own timing-paddhati doctrine (2026-06-05 memo: "Varshphal GATES the year")? Varshphal is not in this engine at all — it may be the missing Stage-3.

## Finding 2 — what does work

- **Vimsottari era-bracketing**: for every promised event, the true AD is in the candidate set.
- **Karaka-PD delivery** (your 4-chart derivation): true windows are repeatedly the karaka/lord-PD slices — Raman child→Jupiter PD, startup→Mercury PD, Rishipal both marriages→Venus PD.
- **Jaimini era votes** (chara AD level — locking at PD granularity was wrong; fixed): fires on the right era for Raman's divorce, marriage.
- **Relative anchoring** (Stage 4): with marriage confirmed, Raman's first child snaps to Aug–Dec 2001 (true: Nov 2001) — beating a wrong 3-lock 2005 window. Confirm-then-predict works the way an astrologer works.

## Finding 3 — why precision stays low anyway

Qualifying sets are 18–62 windows per event with 1–2 truth-holders: the locks admit ~30–50% of candidates instead of concentrating. Selection from such a set is structurally ~1-in-10 no matter the key (a 10-key grid scored 0–2/10 across all weightings). Rishipal exposes two more structural gaps: 3 of his 5 events have **zero** truth-holders at gate level (his children's significator eras are never flagged — Stage-1/2 coverage gap for Aquarius children, worth an astrology review of the 5H/9H significator set), and his child anchors to his **second** marriage — single-instance-per-event-type cannot represent remarriage lives.

## Shipped this round (deterministic, all committed)

1. Jaimini lock votes on the parent-AD era (Stage-2 doctrine: AD = year).
2. Third lock = karaka/lord-PD delivery, DT as alternative trigger; lock trace carries `trigger_source`.
3. Relative priors as hard bands: child −90d..+6y from marriage, 2nd child +9mo..+8y from 1st, divorce ≥3y after marriage; anchor = confirmed event if given, else engine's own pick; empty band → honest silence.
4. Painful asymmetry: `serious_partnership_ended` requires a KNOWN/confirmed prior partnership — never asserted on ignorance.
5. Selection: locks first, then delivering-PD + Vimsottari chain depth — never bare earliest.
6. `--explain` candidate tables + real-chronology replay (calibration now runs without swisseph).

## Decision points (founder)

1. **Stage-3 ruling** — degree-based DT, or Varshphal year-gate, or accept delivery-lock as the trigger.
2. **`major_relocation` houses** — still `4,3,12` in config; primary=4 silences all three of Raman's real moves at Stage-1 (`promise 1.0 < 2.0`). Proposed: `12,4,9`.
3. **Launch posture** — convergence stays ON (it kills the fabricated-divorce class and never pads) but blind dated-event precision is 20–30%; the defensible product NOW is confirm-then-predict (signature flow anchors, engine chains). Blind assertion needs the Stage-3 ruling + more ground-truth charts.
4. **Harleen + Shashi dates** — still missing; they are the only out-of-sample test of everything above.
