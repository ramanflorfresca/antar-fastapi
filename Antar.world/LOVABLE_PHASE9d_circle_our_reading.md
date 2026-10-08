# Lovable prompt — Phase 9d: "Our reading" (the joint reading, second opt-in)

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phases 9, 9b and 9c. UI only. The backend is built and merged; **the owner must run `sql_circle_reading.sql` once** (one column). Until then the switch reads as off and turning it on answers `503 circle_unavailable`: show the calm retry line and nothing else breaks.

What it is: a short joint reading of how the two people work together (a score, six areas, one thing to watch, a timing line), computed from both real charts. The first consent screen promised only "dates and each other's first name", so this needs a **second opt-in**: each person has their own switch for that person, **off by default**, and the reading shows **only while both are on**. Either turning theirs off hides it for both.

## PROMPT STARTS HERE

You are working on the existing Antar web app, the Circle pair page `/circle/:otherChartId`. UI only; use the endpoints below; show strings exactly as returned; do not publish; open a PR.

### 1. Own tab, nothing else changes
Add a two-tab control under the page header: **Windows** (the existing Between us content, completely unchanged: dates only) and **Our reading** (new). Default to Windows. Do **not** show any part of the reading in the page header or on the Windows tab. Tab labels in en/es/pt (hinglish Roman; hi falls back to English): "Windows" / "Our reading".

### 2. Data
- `GET /api/v1/circle/{chart_id}/pair/{other_chart_id}` already returns `reading: {state, mine, theirs}` and `my_sharing: {share_day, share_reading}`. Use `reading.state` to pick the screen without a second call.
- `GET /api/v1/circle/{chart_id}/pair/{other_chart_id}/reading?language=<lang>` returns `{state, mine, theirs, other_first_name, language, reading}`. Call it when the Our reading tab opens, and again after the switch changes. `reading` is non-null **only** when `state` is `on`.
- Switch: `PUT /api/v1/circle/{chart_id}/sharing/{other_chart_id}` body `{ "share_reading": true|false }` (send only that field; `share_day` is a separate switch and must not change). Update the switch optimistically and revert on error. `503 circle_unavailable` -> *"Couldn't change that right now. Try again in a little while."*
- Same auth as the rest of Circle (Bearer, or `X-Claim-Token` for a guest chart).

### 3. The four states of the tab (pick by `state`)
Always render the same **Share a joint reading** switch card at the bottom of the tab (seeded from `mine`), with the helper line *"Both of you choose to see it. You can turn it off any time and it disappears for both."* A matching **Share a joint reading** row also goes in the existing Privacy sheet and is the same switch (same state, same call).
1. **`off`** (neither is on): a card titled **"Our reading"** with *"A short read of how the two of you work together: a score, six areas, one thing to watch. It uses both charts and shows no birth details. It stays hidden until you both turn it on."* Then the switch.
2. **`waiting`** (only me): a card **"Waiting for {other_first_name}"** with *"Your reading appears when you both have it turned on. We don't tell you whether they've looked at this, and nothing is sent to them."* Then the switch (on).
3. **`they_on`** (only them): a card with an accent border: **"{other_first_name} turned on the joint reading"** with *"It shows a score and a short note for each part of how you work together. It uses only the two charts and shows no birth details. Turn yours on to see it."* Then the switch (off).
4. **`on`** (both): the reading (section 4), then the switch.

Rules for these states:
- Only a **yes** is ever visible. Never show anything that tells one person the other said no or hasn't looked. There is no badge, dot, push or notification for any state; the `they_on` card appears only on this tab (and the tab label itself never changes).
- If `state` is `on` but `reading` is `null` (the engine was unavailable): show *"The reading isn't available right now. Try again in a little while."* with a Retry, and keep the switch.

### 4. The reading (state `on`), from `reading`
Render, top to bottom, exactly what the API returns (no recalculation, no rewording):
- **Score card:** `badge` (MIXED / FLOWS / FRICTION as returned, styled with the same colors People uses) and `score` (0-100) large, then `headline`, then `summary`.
- **Areas list:** one row per `layers[]` in the order returned: `label` on the left, a status pill on the right showing `status_label` (colors: `flows` green, `needs_care` amber, `friction` red). Tapping a row expands its `headline` and `detail`. Show the numeric `score` of an area only inside the expanded row.
- **Watch** (from `watch_points`, if non-empty): the first item, with the label "Watch".
- **Timing** (from `timing.line`, if present): with the label "Timing".
- **Confidence** (from `confidence.line`, if present): one muted line under the list.
- Never show `catalysts` or any field not listed here unless a later prompt asks for it; never show a prediction of success, a pass/fail, or anything about birth details.

### Rules
- Show strings exactly as returned. The only new static strings are the tab labels, the four card texts above, the switch label and helper, "Watch", "Timing", and the two calm error lines (en/es/pt; hinglish Roman; hi falls back to English).
- Never store or log the reading or the state; no analytics events that include them.
- No pricing text. No backend or API change. Leave the Windows tab, share-day switch, Leave action and Ask chips exactly as they are.

### Edge cases
- If the pair is gone (`404 not_in_circle`) go back to `/circle` as on the rest of the page.
- Turning the switch off while on: the reading disappears for both; show the `they_on` or `off` card according to the next response.
- Language: pass `language=<ui lang>`; the text comes back in that language when a translation exists, otherwise English.
- Works at 375 px and desktop; loading uses the existing skeleton; errors are one calm line with Retry.

### Acceptance checks (verify and say so in the PR)
- Default tab is Windows and its content is unchanged; the reading appears nowhere else.
- With neither on: explainer + switch. Turning mine on: "Waiting for {name}" and no reading. When the other person is on and I am not: the accent "{name} turned on the joint reading" card. Both on: the reading. Either turning off hides it for both.
- The switch in the Privacy sheet and the one on the tab are the same state.
- The PUT sends only `share_reading`, and the share-day switch is unaffected.
- No state, badge or notification ever indicates that someone declined or hasn't looked.
- Screenshots at 375 px of all four states, the reading with one area expanded, and the Privacy sheet row are attached to the PR.

### Out of scope (do not build)
Showing the reading anywhere but its own tab, notifications about the switch, a "request their reading" button, sharing a private reading, any backend or API change.

## PROMPT ENDS HERE
