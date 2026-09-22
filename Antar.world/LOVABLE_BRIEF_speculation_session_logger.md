# Lovable brief — Speculation Session Logger (shadow research screen)

## What this is (and what it is NOT)
A minimal, **opt-in** screen for a user to log a real gambling/speculation session
so we can research whether KP timing (Moon sub-lord + hora) predicts win/loss —
under a **closed gate**, purely for data collection. It is **not** a betting tool.

**Hard tone rules (do not violate):**
- **NEVER show a prediction, verdict, "lucky window", or any reading.** The screen
  only records. The API returns a `windows` count — **do not display it as a signal.**
- **Do NOT gamify.** No streaks, confetti, points, "you're up!" celebration, or
  win animations. Logging a loss should feel calm and neutral, never rewarding.
- **Opt-in only**, behind a Settings toggle. Include a responsible-gambling line +
  link. Let the user delete their log anytime.
- Backend is already built; this brief is the UI + the one API call.

## Where it lives
- Settings → new **"Session log (research)"** row, hidden unless a feature flag /
  opt-in is on. Tapping it opens the logger. (Or a route `/speculation-log`.)
- First open shows the **consent card** (below) before anything else.

## Screen 1 — Consent / intro (first open only)
Plain card, no imagery:
> **Session log**
> This is a private research log. If you play, you can record the session so we
> can study whether timing patterns hold up. It shows you no prediction and is
> not advice to gamble. Your log is yours — delete it anytime.
> _If gambling stops being fun, help is available: 1-800-522-4700 (US) /
> your local line._
- Buttons: **"I understand — start logging"** (sets opt-in) · **"Not now"**.

## Screen 2 — Active session (the core)
State machine: `idle → active → ending`.

**idle:** one primary button **"Start session"**.
- On tap: capture `started_at = now` (ISO, UTC) and request **device geolocation**
  (see §Location). Move to `active`. Persist the in-progress session to local
  storage so it survives app close (sessions run for hours).

**active:** a calm running screen:
- Top: elapsed time (mm:ss / h:mm), started-at time. No P&L judgement, no colours.
- A **big "＋ Checkpoint"** button — the main interaction. Opens the checkpoint
  sheet (§Screen 3). Tapped at sit-down (auto-prompt the first one as "buy-in"),
  at each drink, each break, and cash-out.
- A list of logged checkpoints (time · balance · optional 🍸/☕ note), read-only.
- Secondary button **"End session"** → Screen 4.

## Screen 3 — Checkpoint sheet (~5-second entry)
- **Chip balance** (number input, required) — "How much do you have right now?"
- Optional one-tap toggles: **"had a drink"** (each tap +1 to a running alcohol
  counter for the session), **"break"**, **"cash-out"** (note only).
- Save → appends `{at: now(UTC ISO), chip_balance, alcohol_units_cumulative (running), note}`.
- The FIRST checkpoint is auto-labelled the **buy-in**; encourage a checkpoint at
  every drink/break so the windows are fine-grained.

## Screen 4 — End session (the confounds — important)
Collected in one short form (these fields are the scientific core; keep it quick):
- **Final balance** (number) → if no cash-out checkpoint yet, this becomes the last one.
- **Alcohol tonight** — pre-filled from the drink toggles, **editable** (a single
  number of drinks). Mandatory-ish (0 is fine; blank discouraged).
- **Were you chasing losses at any point?** — Yes / No toggle (`chasing_flag`).
- **Game type** — chips: Poker · Table · Slots · Sports · Crypto/markets · Other.
- Optional: **Notes** (free text), **"this log is unreliable"** checkbox
  (→ `valid: false`; we keep but exclude it — for "too drunk to log accurately").
- Primary button **"Finish & log"** → POST (§API) → Screen 5.

## Screen 5 — Confirmation (deliberately dull)
> **Logged. Thank you.**
> Nothing to see here — this just helps the research. Take care of yourself.
> _[responsible-gambling line + link again]_
- Single button **"Done"**. **Do NOT** show the `windows` count, any timing, or a
  reading. No "come back and play at X".

## API — the one call (backend already built)
`POST /api/v1/speculation/session` (only works when the server flag
`SPECULATION_LOGGER=on`; otherwise 404 — handle gracefully: "Logging isn't
enabled yet").

Body:
```json
{
  "chart_id": "<active chart id>",
  "started_at": "2026-09-22T02:30:00Z",
  "ended_at":   "2026-09-22T09:30:00Z",
  "lat": 42.2176, "lng": -73.8646, "tz_offset": -4,
  "game_type": "poker",
  "net_units": 1500,                     // final_balance - buy_in (signed)
  "unit_currency": "USD",                // or "unit"
  "stake_baseline": 50,                  // optional typical bet size
  "alcohol_units_total": 4,
  "chasing_flag": true,
  "sleep_debt_hrs": null,                // optional
  "valid": true,
  "notes": "",
  "checkpoints": [
    {"at": "2026-09-22T02:30:00Z", "chip_balance": 1000, "alcohol_units_cumulative": 0, "note": "buy-in"},
    {"at": "2026-09-22T04:00:00Z", "chip_balance": 2200, "alcohol_units_cumulative": 2, "note": "drink"},
    {"at": "2026-09-22T06:00:00Z", "chip_balance": 3000, "alcohol_units_cumulative": 3, "note": "peak"},
    {"at": "2026-09-22T09:30:00Z", "chip_balance": 0,    "alcohol_units_cumulative": 4, "note": "cash-out"}
  ]
}
```
Response: `{ "logged": true, "session_id": "...", "windows": N }` — treat as success;
**ignore/hide `windows`.** On 404 (flag off) or error, show a neutral "couldn't
log right now" and keep the local draft so nothing is lost.

## Location (§)
- The session happens **where the player IS**, which may differ from their saved
  city (a casino trip). Request **device geolocation at "Start session"** and send
  `lat`/`lng`. If denied, omit them — the backend falls back to the chart's current
  location (less accurate; that's fine).
- `tz_offset` = the device's current UTC offset in **hours** (e.g. EDT = -4). Send it.
- All timestamps in **UTC ISO-8601** (`...Z`).

## Persistence & edge cases
- Keep the in-progress session (start time + checkpoints) in local storage; restore
  it if the app is closed/reopened mid-session. Offer "Resume" or "Discard".
- If the user never ends a session, don't auto-submit; let them resume or discard.
- Idempotency: optionally include a client-generated `session_uuid` in the body and
  reuse it on retry so a flaky network doesn't double-log (backend can dedupe).

## Data sensitivity
Behavioral-sensitive (like health data). Don't cache balances in analytics; don't
show amounts on any shared/social surface. The backend purges on chart delete.

---
Backend: `POST /api/v1/speculation/session`, engine `antar_engine/kp/kp_moment.py`,
tables `Antar.world/speculation_log_tables.sql`, spec `KP_SPECULATION_TIMING_STUDY.md`.
Owner ask 2026-09-22. Shadow-only; ship behind the opt-in flag.
