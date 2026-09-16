# Lovable brief — Enemy-house remedies across 4 surfaces (+ progress + badge)

**Backend is already live.** This is a **frontend-only** brief. Do NOT recompute
any astrology in the client — every field below is delivered by the API. Render
what you're given; keep the plain-language voice (no house numbers, no Sanskrit).

## What "enemy house" means (for your copy, not the user)
A planet sitting in a sign ruled by its natural adversary creates a recurring,
low-grade tension in one life area. It is **not** a curse or a verdict — it's a
"tension to tend." Each alert ships with a concrete remedy that pacifies the
afflicted planet. Some remedies matter most **this year** (the planet rules the
user's annual chart); the rest are a steady background practice.

## The `enemy_alert` object (identical on every surface)
```jsonc
{
  "practice_id": "saturn_enemy_remedy",   // stable id — use for MARK DONE
  "planet": "Saturn",                      // internal; DO NOT show raw to user
  "energy_label": "Discipline & Structure",// plain label — show THIS, not planet
  "why": "Discipline turns into self-punishment when pushed too hard.",
  "active_when": "under deadline pressure",// when the tension flares
  "severity": "high",                      // high | moderate | low
  "domain": "career",                      // career|money|love|health|home|...
  "color": "#8B5CF6",                      // accent for the card
  "remedies": ["Volunteer at a shelter…", "Wear black or navy on Saturday"],
  "remedy_why": "Steadily tending your discipline & structure eases this tension…",
  "active_this_year": true,                // year_lord match → do it now
  "priority": "year",                      // "year" | "ongoing" | null
  "timing": "This is its year — … do these remedies intensively now…"
}
```
Ordering: the API already sorts **year-priority first, then ongoing.** Preserve
array order. Localization (es/pt) is handled server-side — just pass the user's
language param through on the fetch; render whatever comes back.

**Voice rule:** lead each card with `energy_label`, never the raw `planet` name.
Badge `active_this_year === true` cards with a small "This year" chip in `color`.

---

## Surface 1 — Practice tab: "Enemy-house remedy plan"
- **Endpoint:** `GET /api/v1/practices/{chart_id}/schedule?language={lang}`
- **Field:** `schedule.enemy_alerts[]`
- Weekly-cached server-side. If a user just refreshed their chart and the list
  looks stale, refetch with `?refresh=true` (use sparingly — it bypasses cache).
- Render a section **"Tensions to tend"** under the existing practice list. One
  card per alert: `energy_label` (title) · `why` · `active_when` (small, muted) ·
  `remedies` (checklist) · `timing` (footnote). Year-priority cards on top with
  the "This year" chip.
- **MARK DONE:** `POST /api/v1/practices/{chart_id}/complete` with body
  `{ "practice_id": "<alert.practice_id>", "user_note": "" }`. Response returns
  `{ streak_count, message, awards }` — show the streak toast you already show
  for other practices. (Enemy remedies flow through the SAME completion path.)

## Surface 2 — Full Chart page: "Tensions to tend" section (with progress)
- **Endpoint:** `GET /api/v1/chart/{chart_id}/overview?language={lang}`
- **Field:** `enemy_alerts[]` — here each alert ALSO carries **`progress`**:
```jsonc
"progress": { "completed_count": 3, "done_today": true,
              "last_completed_at": "2026-09-15", "streak": 3 }
```
- Add the section AFTER strengths / areas-to-mind. Same card layout as Surface 1,
  plus a progress row per card:
  - `streak > 0` → "🔥 {streak}-day streak"
  - `done_today === true` → show MARK DONE as a filled/checked state ("Done today")
  - `done_today === false` → active MARK DONE button (same POST as Surface 1)
  - `completed_count === 0` → no streak line, just the button.
- If `enemy_alerts` is empty → hide the section entirely (a clean chart is good news).

## Surface 3 — People / Compatibility reading
- **Endpoints:** `POST /api/v1/compatibility/start` and
  `GET /api/v1/compatibility/session/{session_id}`
- **Field:** `person_enemy_alerts[]` — the **connection person's** enemy alerts
  (same object shape; no `progress` here — it's the other person's chart).
- Render a short "What to be mindful of with {name}" block inside the reading:
  one line per alert using `energy_label` + `why`. Keep it gentle — this is about
  understanding the other person, not judging them. Do NOT show remedies here
  (you can't do someone else's remedy); `why` + `active_when` only.

## Surface 4 — Settings → Charts card: enemy-count badge
- **Endpoint:** `GET /api/v1/me/charts`
- **New fields per chart:** `enemy_count` (total) and `enemy_priority_count`
  (year-active subset).
- On each chart card, if `enemy_count > 0`, show a small badge:
  - `"{enemy_count} to tend"` in a muted style, and
  - if `enemy_priority_count > 0`, accent it: `"{enemy_priority_count} this year"`.
- Tapping the badge deep-links to that chart's Full Chart page → "Tensions to
  tend" section (Surface 2).
- This surface exposes a **count only** (no planet/sign names) on purpose — keep
  it that way.

---

## Acceptance
1. Practice tab shows the remedy plan; MARK DONE increments the streak toast.
2. Full Chart "Tensions to tend" shows per-card streak + "Done today" state that
   persists after reload (it reads real completion history).
3. Compatibility reading shows the connection person's mindful-of lines (no
   remedies, no raw planet names).
4. Settings → Charts shows "N to tend / M this year" badges; empty charts show none.
5. es/pt: switch language → all copy AND remedy text come back translated; dates
   inside any timing text render in the local month (server handles this).
