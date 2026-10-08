# Lovable prompt — edit birth details + current city (Settings)

Backend already supports this (`PATCH /api/v1/me/charts/{chart_id}`). Frontend only.

---

Add "Edit birth details" and "Where you live now" to Settings → My chart. Frontend only; do NOT add backend or astrology logic.

**Endpoint:** `PATCH {API}/api/v1/me/charts/{chart_id}` with `Authorization: Bearer <supabase access token>` and a JSON body containing ONLY the fields the user changed:
`{ "birth_date": "YYYY-MM-DD", "birth_time": "HH:MM", "birth_place": "City", "birth_country": "Country", "current_city": "City", "current_country": "Country", "name": "..." }`
Response: `{ chart: { id, first_name/name, birth_date, birth_time, birth_city, ... }, rebuild: { purge, dashas, jaimini, lal_kitab, yogas }, rebuild_complete: boolean }` (`rebuild`/`rebuild_complete` appear only after a birth-details save; each step is `"ok"` or `"failed: ..."`). Errors: 401 = signed out, 404 = not your chart, 500 `{error:"recompute failed", detail}` = the place could not be found or the chart could not be built.

**Two separate sections, two separate Save buttons:**

1. **Birth details** (date, time, birthplace city + country). Pre-fill from the chart. Use the same city autocomplete as onboarding, and always send `birth_country` together with `birth_place` (the server geocodes the pair). Send only changed fields. Before saving, show a confirm dialog: "Changing your birth details rebuilds your whole chart. Your readings and predictions will change. Continue?" While saving (the rebuild takes a few seconds) show a blocking "Rebuilding your chart…" state on the button, not a full-page spinner, and disable the form. If birth time is unknown, keep the existing "unknown time" option from onboarding and send the same value onboarding sends.

2. **Where you live now** (current city + country). Saving it does NOT rebuild the chart — it only updates today's local timing and place-based readings. No confirm dialog; save inline with a small "Saved" toast.

**After a successful save:** invalidate and refetch every chart-keyed query: chart, bootstrap, daily-signal, daily-week, topics, topic-read, streak, people. For a birth-details save, also clear any locally cached Today/Month/Year card for that chart so stale readings never show. Then show the toast "Chart updated". If `rebuild_complete` is `false`, show instead: "Chart updated — some readings are still updating. Pull to refresh in a minute." and refetch once after 30 seconds. Never show the raw `rebuild` step errors.

**Errors:** on 500, keep the form open with the user's values, and show "We couldn't find that place — pick a city from the list" (do not show the raw `detail`). On 401, send to sign-in. Never lose what the user typed.

**Guardrails:** validate date not in the future and time is HH:MM before sending. Don't let the user edit birth details of a chart they do not own (hide the section for People/connection charts). Do not call this endpoint on every keystroke or on page load.

**Acceptance:** `rebuild_complete:false` shows the "still updating" note and one delayed refetch; edit birth time → confirm → "Rebuilding your chart…" → Today and Chart screens show the new lagna within seconds, no stale card; edit current city → no rebuild, no confirm, saved toast; bad city → inline message, form values preserved.
