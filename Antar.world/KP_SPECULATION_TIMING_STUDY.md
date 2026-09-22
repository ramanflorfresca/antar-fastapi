# KP Speculation / Gambling Timing — Shadow Validation Study

**Status:** DESIGN (pre-registration). Gate is CLOSED — nothing ships until this
clears the bar. Prior: LOW (Rahu-illusion mechanism + two adjacent negatives:
[[business-vertical-timing-study]] and [[d2-wealth-tested-dead]] both closed
null). We are trying to FALSIFY, not confirm.

## 0. The one-line question

*Does the Moon's KP sub-lord (and the planetary hora) at the moment of play
predict the net win/loss of that window — AFTER removing the obvious behavioral
confounds (alcohol, fatigue, time-of-night, chasing, stake creep)?*

If the astrological signal only "works" because Rahu-sub windows happen to be
late-night-drunk-tired windows, there is no edge — just a clock for human
tilt. The whole study exists to separate those two.

## 1. Pre-registered hypotheses (directional, locked before data)

- **H1 (primary):** Mean net P&L per minute during **Rahu / Ketu** Moon-sub-lord
  windows is *lower* than during **Mercury / Jupiter / Venus** sub-lord windows,
  and this survives controlling for the confounds in §4.
- **H2:** Windows whose sub-lord is the **current Mahādaśā lord** (e.g. a Rahu-MD
  player in a Rahu sub-lord window) are net-negative more often than chance.
- **H3 (hora):** A malefic **hora** (Saturn/Mars/Rahu-ruled hour) is net-negative
  more often than a benefic hora — tested independently of the sub-lord.
- **H0 (the honest prior):** After confound control, none of the above holds —
  the apparent effect is behavioral, not astrological.

Each hypothesis gets a single pre-registered test and a single p-value. No
post-hoc re-slicing (that is how [[business-vertical-timing-study]] almost
fooled us).

## 2. Unit of analysis

The **sub-window**: a continuous stretch of one session during which the Moon's
KP sub-lord is constant (they last ~20 min–3 hr). Each session is auto-sliced at
every sub-lord boundary. This is deliberate — the user's own case ("winning till
2am, lost 2–5:30am") is a *within-session* shift, so session-level P&L would blur
the exact thing we're testing.

Minimum viable dataset: **≥ 400 sub-windows across ≥ 8 distinct players and ≥ 60
sessions.** N-of-1 is an anecdote (last night was an anecdote). Multi-player kills
the "it's just his personal tilt" alternative.

## 3. What to log per sub-window (shadow only, never surfaced)

Astro (computed, deterministic — we already have the engine):
- `sub_lord`, `star_lord`, `sub_sub_lord` (Moon, KP + Lahiri both — report the
  one pre-registered as primary: **KP/Krishnamurti ayanamsa**)
- `hora_lord`, `moon_sign`, `moon_nakshatra`
- `md_lord`, `ad_lord` (is the sub-lord == the dasha lord?)
- natal flags: Ketu-in-5th, 5th-lord dignity, Rahu/Venus 11th cluster (per-player)

Outcome:
- `net_units` for the window (signed), `minutes`, `net_per_min`
- `stake_avg`, `n_bets`, `hit_rate`

**Confounds (mandatory — the study is worthless without these):**
- `alcohol_units_cumulative` (the Rahu proxy — MUST be logged; the tequila is the
  prime confound and it *correlates with the Rahu-sub late window*)
- `hours_awake` / `hours_into_session` (fatigue)
- `local_clock_hour` (time-of-night captures both circadian dip and casino floor
  dynamics)
- `chasing_flag` (stake this window > 1.5× session baseline = tilt)
- `sleep_debt`, `caffeine` (optional)

Logging: a 30-second post-session form (or a live tap-logger). Honest self-report
of alcohol + chasing is the hard part; unreliable logs → discard the session.

## 4. Analysis (pre-registered)

1. **Raw look (descriptive only):** mean `net_per_min` by sub-lord. This is the
   "wow" table — and it is NOT evidence. It is where the confound hides.
2. **The real test — mixed-effects logistic / linear regression:**
   `net_per_min ~ is_rahu_ketu_sub + hora_malefic + (dasha_lord==sub_lord)`
   **+ alcohol_units + hours_into_session + local_clock_hour + chasing_flag**,
   random intercept per player.
   The astrological terms must stay significant *with the confounds in the model.*
   If `is_rahu_ketu_sub` loses significance once `alcohol_units` and
   `hours_into_session` enter → **H0 confirmed, feature dead.**
3. **Effect-size bar, not just p:** to be worth shipping, the astro term must
   move the win-probability by a *practically meaningful* margin AND the model's
   out-of-sample directional accuracy on held-out sessions must be **≥ 70%**
   (pre-registered bar, same as the gate). p<0.05 on a tiny effect is not enough.
4. **Case-control cross-check:** matched pairs of windows — same player, same
   alcohol band, same hour-of-night — differing only in sub-lord. If the effect
   is real it survives matching. (This is the design that killed D-2 wealth.)

## 5. Kill criteria (declare dead, write it up, move on)

- After 400 windows, `is_rahu_ketu_sub` is not significant with confounds in → dead.
- Or it's significant but out-of-sample directional accuracy < 70% → dead (not
  reliable enough to ever surface).
- Or the effect vanishes under case-control matching → dead (it was the confound).
- Partial result (e.g. the *danger* direction holds but not the *favorable*
  direction) → ship ONLY the protective/avoidance framing (§6), never a "play now".

Precedent to honor: business-timing and D-2 wealth both looked promising in the
raw table and collapsed on the clean cohort. Expect the same here; be glad if it
doesn't.

## 6. What may EVER be exposed, and how

Even a PASS does not unlock a "best time to bet" timer. Ordered by how defensible:

1. **Protective / walk-away timeline (harm reduction)** — "your judgment is most
   compromised in this band (Rahu sub + late + alcohol); step away." Ships first,
   defensible even on a weak PASS, because it reduces loss and never promises a win.
2. **Risk-awareness, not a green-light** — favorable windows framed as "clearer
   judgment, for decisions" — never "bet here to win."
3. A literal win-timer: only on a strong PASS (≥70% OOS, effect survives all
   confounds, replicated on a second cohort), and even then behind an explicit
   "this is a tendency, not a promise; gamble responsibly" guard + the existing
   speculation-safety layer. Realistically: unlikely, given the prior.

## 7. Why the honest expectation is H0

Rahu's whole signature is that the *entry* feels lucky and the un-booked gain
evaporates — i.e. the "hot" window and the "cold" window are the *same* window,
separated only by whether you walked. That is behavioral (booking discipline),
and it co-moves with alcohol and fatigue. The most likely true finding is: **the
clock predicts when people TILT, not when the cards fall.** Which is still useful
— as a protection tool, not a betting edge. Build that; test the rest honestly.

---

## Appendix A — Session logger: implementation scope

Goal: capture clean, per-sub-window P&L with minimal player burden, astro
auto-filled server-side. **Shadow-only** — the logger never returns a reading,
verdict, or "you'll win"; it only records. Gated behind a feature flag +
explicit consent; honors the existing speculation-safety layer.

### A.1 The burden problem, and the design that solves it
The study needs P&L at the **sub-window** grain (~20 min–3 hr), but a player
won't log after every hand. Solution: the player logs a **chip-balance
checkpoint** only at natural moments — sit-down, each drink, each break,
cash-out (a 5-second tap each). The SERVER slices the session at every Moon
sub-lord boundary and allocates the P&L delta between consecutive checkpoints
across the sub-windows they span (pro-rata by minutes; exact when a checkpoint
lands on a boundary). Two checkpoints (start+end) is the floor (session-level
only, weak); more checkpoints = finer, stronger windows. That keeps each entry
~5–30 seconds and still yields window-level data.

### A.2 Data model (3 tables — DDL via Lovable Cloud, see [[backend-frontend-ownership]])
- **`speculation_sessions`**: `id`, `chart_id` (fk), `started_at`, `ended_at`,
  `lat`, `lng`, `tz_offset`, `game_type` (poker/slots/table/sports/crypto/…),
  `net_units` (signed, session total), `unit_currency`, `stake_baseline`,
  `alcohol_units_total`, `chasing_flag` (bool, self-report), `sleep_debt_hrs`
  (opt), `valid` (bool — false if self-report unreliable), `notes`, `created_at`.
- **`speculation_checkpoints`**: `id`, `session_id` (fk), `at_ts`,
  `chip_balance` (running), `alcohol_units_cumulative`, `note` (drink/break/…).
- **`speculation_windows`** (DERIVED, server-written, never user-entered):
  `id`, `session_id`, `window_start`, `window_end`, `minutes`,
  `sub_lord`, `star_lord`, `sub_sub_lord`, `hora_lord`, `moon_sign`,
  `moon_nakshatra`, `md_lord`, `ad_lord`, `is_dasha_sub` (sub_lord==md_lord),
  `ayanamsa` (kp|lahiri — one row-set each for cross-check),
  `net_units` (allocated), `net_per_min`. This is the analysis table for §4.

### A.3 Astro engine (server-side, deterministic — mostly already built)
`kp_moment(ts_utc, lat, lng, chart) -> dict`:
- Moon sidereal longitude via swisseph (KP/Krishnamurti **and** Lahiri) →
  `star_lord`, `sub_lord`, `sub_sub_lord` via the Vimshottari-proportion
  subdivision (the exact code from the retrospective reads — lift it into
  `antar_engine/kp_moment.py`).
- `hora_lord` from sunrise/sunset + Chaldean order for that weekday+location
  (reuse `hora_karana` / the NOAA sunrise calc already used).
- `md_lord`, `ad_lord` from the player's `dasha_periods` at `ts`.
- `sub_lord_boundaries(session_start, session_end, lat, lng)` → the timestamps
  where the Moon sub-lord changes in-session (Moon moves ~0.5°/hr; walk it) —
  drives the window slicing in A.1.

### A.4 Endpoints
- `POST /api/v1/speculation/session` — body: session envelope + `checkpoints[]`.
  On write: validate → compute `sub_lord_boundaries` → slice → fill
  `speculation_windows` (both ayanamsas) → allocate P&L. Returns `{logged: true}`
  ONLY (no reading — shadow). Idempotent on client-supplied `session_uuid`.
- `PATCH …/session/{id}` — add a checkpoint / close the session (re-slice).
- `GET /api/v1/admin/speculation/export?since=…` — admin-gated CSV/JSON dump for
  the §4 regression. Never exposed to normal clients.

### A.5 Client UX (FE, later)
A minimal, non-gamified logger (deliberately dull — do NOT make loss-logging
fun): "Start session" (captures ts + location) → a big "＋ checkpoint" tap
(balance + optional drink toggle) → "End session" (final balance + a one-tap
alcohol total + a chasing yes/no). No prediction shown, ever. One reassurance
line + a link to responsible-gambling resources. Behind a settings flag; opt-in.

### A.6 Guardrails
- Shadow-only; feature-flagged; consent-gated; no reading/verdict returned.
- Never message "favorable to play"; the logger is silent by design.
- `valid=false` sessions (drunk-illegible self-report) excluded from analysis,
  not deleted.
- PII: no venue names / amounts-as-currency required (units are fine); the log is
  behavioral-sensitive — treat like health data, purge on chart delete.

### A.7 Effort (rough)
Engine lift + `kp_moment.py` (~½ day, code exists) · 3 tables via Lovable (~½ day)
· 2 endpoints + slicing/allocation (~1–1.5 days) · admin export (~½ day) ·
FE logger (~1–2 days). ~1 week to a shadow-collecting MVP. Then it's a *data-
collection wait* (≥60 sessions / ≥8 players) before §4 can even run — that wait,
not the code, is the long pole.

---
Owner ask 2026-09-22. Engine (Moon KP sub-lord + hora, both ayanamsas) already
exists from the retrospective reads; next concrete step if greenlit is A.3+A.4
(shadow-only), then the collection wait.
