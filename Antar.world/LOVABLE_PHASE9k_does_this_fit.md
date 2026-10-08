# Lovable prompt — Phase 9k: one-tap "Does this fit?" on the Our reading tab

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phase 9h. UI only; the backend is merged. Nobody can read everyone's chats and users will not write in to say a reading was wrong, so the tab asks ONE short question at a time, answered in one tap, and the answers feed the accuracy board.

## PROMPT STARTS HERE

You are working on the existing Antar web app, the Circle pair page, **Our reading** tab, state `on`. UI only; show every string exactly as returned; do not publish; open a PR.

### The calls
- `GET /api/v1/circle/{chart_id}/pair/{other_chart_id}/feedback?language=<lang>&tz_offset=<minutes>` returns either `{ "item": null }` (nothing to ask) or `{ item, question, options: [{value, label}], context }`. `item` is `call`, `me` or `reading`; `value` is `yes`, `partly` or `no`; `context` is the text the question is about.
- `POST` the same path with `{ "item": "<item>", "answer": "<value>" }` returns `{ saved, already_answered, outcome, thanks, next }`. `next` is the next question (same shape as the GET) or `null`.
- Same auth as the rest of Circle (Bearer, or `X-Claim-Token` for a guest chart). `409 not_on` means the reading is not on: show nothing.

### Where it shows
Only in the Our reading tab, only in state `on`, only when the GET returns an `item`. Show it as a small **card at the very bottom of the tab**, above the note, never as a popup, never as a banner, never outside this tab.
- The card: `question` as the heading; under it, when `item` is `call`, the call card is the thing above it, so show nothing more; for `me` show `context` as a muted quote of the card about the viewer; for `reading` show nothing more.
- Three equal buttons from `options` in the order returned (labels as returned: "Yes, it fits", "Partly", "No, not really"). One tap saves.
- After a tap: show `thanks` for 2 seconds, then replace the card with the `next` question if there is one; if `next` is null, remove the card. Never show more than one question at once.
- If the POST fails, keep the card and show one calm line: "Couldn't save that. Try again."

### Rules
- Show strings exactly as returned. No scores, no streaks, no rewards, no "help us improve" copy beyond what the API returns. Do not ask again after an answer (the API handles the timing, about every 90 days).
- The answer is private to the person who gave it: never show it to the other person and never show whether the other person answered.
- Do not log or store the question text or the answer in analytics. No notifications or badges. No pricing text. No backend or API change.

### Acceptance checks (verify and say so in the PR)
- With both switches on, the tab ends with a "Does this fit?" card asking about the call first; one tap saves, shows the thanks, then asks about the viewer's own card, then the overall reading, then the card disappears.
- Reloading the page after answering does not show the answered question again.
- With the reading off, waiting or they_on there is no card.
- The two people see their own questions independently.
- Screenshots at 375 px of the card for each of the three questions are attached to the PR.

### Out of scope (do not build)
Free-text feedback, rating scales, showing results, any other placement, any backend or API change.

## PROMPT ENDS HERE
