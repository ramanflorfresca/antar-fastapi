# Lovable prompt — Phase 9j: a smarter "add a person" (date, time, where they were born, where they live now)

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phase 7 (the add-a-person flow). UI only for the date, time and place inputs; the backend is merged: a one-line parser endpoint and two optional "lives now" fields. The relationship step, the name step and the last Invite / Keep private step are unchanged.

Why: today a person adds someone by typing a date with slashes, a clock time with a separate AM/PM tap, then a city, then a country, step by step. It should feel like typing a sentence. And the flow never asks where the person lives now.

## PROMPT STARTS HERE

You are working on the existing Antar web app, the add-a-person flow (the "3 of 6 When was {name} born?", "4 of 6 What time?" and the place screens). UI only; keep every existing endpoint call and payload unchanged, except the one optional addition in section 4. Do not publish; open a PR.

### 1. "When was {name} born?" — a field that formats as you type
- One text field, numeric keyboard on phones. As the user types digits, insert the separators for them in the display order the app already uses (day / month / year; if the user's language or country is US, month / day / year): typing `15101990` shows `15 / 10 / 1990`. Never require typing a slash.
- Show a live confirmation under the field as soon as the date is complete and valid, in words: **"15 October 1990"**. An impossible date (31 February, a future date, before 1900) shows one calm line, not a red error: *"That date doesn't exist. Check the day and month."*
- Also accept a typed month name or a pasted full date in any common form ("15 Oct 1990", "Oct 15, 1990", "15 de octubre de 1990"): if the field contains letters or the user pastes text, treat it as the **one-line shortcut** in section 5.
- Keep the "Day / month / year" hint. **Continue** is enabled only for a valid date. Do not ask the user to pick from a calendar widget unless they tap a small calendar icon at the end of the field.

### 2. "What time?" — one field, AM/PM that sets itself
- One field. As the user types, insert the colon for them (`230` shows `2:30`). If the hour is 13 to 23 (or they type 24-hour style) set the 24-hour meaning automatically and hide AM/PM. Otherwise show the **AM / PM** segmented control with **neither selected**; the user must tap one (never assume). Typing `p` or `a` after the time (`2:30p`, `2:30 pm`) selects it.
- Under the field, four quick chips for when the time is only roughly known: **Morning**, **Afternoon**, **Evening**, **Night**. Tapping one fills an approximate time (08:00, 14:00, 18:30, 22:00) and marks the birth time as **approximate**. Keep the existing button **"I don't know their birth time"** (unknown).
- Send the existing birth-time fields exactly as today; for chips and "I don't know" the app already knows the time is not exact.
- Live confirmation in words under the field once valid: **"2:30 in the afternoon"**.

### 3. Where they were born, and where they live now — one screen
- Keep the birth-place field and its autocomplete exactly as it works today (same component, same latitude / longitude / timezone it already sends).
- On the same screen, directly under it, add a second field: **"Where do they live now?"** with the same autocomplete component. Next to it a chip **"Same place"** that copies the birth place, and a quiet text button **"Skip"**. It is optional: Continue works with it empty.
- Send it with the existing add-person request as the new optional fields `current_city_b` and `current_country_b` (and `current_latitude_b`, `current_longitude_b`, `current_timezone_b` when the autocomplete already returns coordinates). Omit them when skipped.
- Helper line under the second field: *"Where someone lives now shapes how their present timing is read."* (en/es/pt; hinglish Roman; hi falls back to English).

### 4. The one request change (additive)
`POST /api/v1/compatibility/start` accepts these new optional fields: `current_city_b`, `current_country_b`, `current_latitude_b`, `current_longitude_b`, `current_timezone_b`. Everything else in the payload is unchanged. Also stop sending the placeholder `name_a`: the backend now uses the user's own first name (send `name_a` only if the app has a real one).

### 5. The one-line shortcut (optional but recommended)
On the date screen (and anywhere the user pastes a long line into the date field), if the text contains more than a date, call `POST /api/v1/people/parse-birth` with `{ "text": "<what they typed or pasted>", "date_order": "dmy" | "mdy" | null }` and the user's `Authorization`. The response:
`{ birth_date, date_ambiguous, birth_time, time_precision, time_ambiguous, city_text, place: {city, latitude, longitude, timezone} | null, missing: [...] }`.
- Show a **confirm card** titled "Is this right?" with the understood date ("15 October 1990"), time ("2:30 in the afternoon", or "Not sure" for `time_precision` `approximate` / `unknown`) and place (`place.city`), each as a tappable chip that jumps to the matching screen to edit. A **"Looks right"** button prefills the whole flow and skips to the "lives now" screen.
- If `date_ambiguous` is non-null (for example `["1990-05-04","1990-04-05"]`), ask once: **"Which is it?"** with the two dates written out in words, and remember the choice as `date_order` for the next lines this user types. Never pick one for them.
- If `time_ambiguous` is non-null (two candidates), show **"2:30 AM or 2:30 PM?"** as two buttons.
- Anything in `missing` is simply asked on its normal screen. If the endpoint fails or returns nothing useful, fall back silently to the normal step-by-step flow.

### Rules
- Never guess a date, an AM/PM or a place silently. Never send a birth detail to any new place other than the existing add-person request and the parse endpoint above. Do not store the typed line.
- Never show astrology terms. No pricing text. No other backend or API change.
- Works at 375 px and desktop, respects the iOS safe area; the progress count ("n of 6") stays accurate.

### Acceptance checks (verify and say so in the PR)
- Typing `15101990` shows `15 / 10 / 1990` and "15 October 1990"; `31022000` shows the calm invalid-date line; no slash was typed.
- Typing `230` then tapping PM shows "2:30 in the afternoon"; typing `1430` sets 24-hour and hides AM/PM; the quick chips mark the time approximate; "I don't know" still works.
- The place screen has birth place and "Where do they live now?" together, with "Same place" and "Skip"; the add-person request carries the optional `current_*_b` fields only when filled.
- Pasting `15 Oct 1990, 2:30 pm, Hyderabad` shows the confirm card with date, time and place; `04/05/1990` asks "Which is it?"; `2:30` with no AM/PM asks "2:30 AM or 2:30 PM?"; failure falls back to the normal flow.
- The request no longer sends the placeholder "Person A"; the reading header shows the user's own first name.
- Screenshots at 375 px of the date field, the time field, the combined place screen and the confirm card are attached to the PR.

### Out of scope (do not build)
A calendar-first date picker, asking for contacts, any change to the relationship step or the Invite / Keep private step, any new backend or API change.

## PROMPT ENDS HERE
