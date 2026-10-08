# Lovable prompt — "Shared with" on the topic read windows

Backend already live (`GET /api/v1/chart/{chart_id}/topic-read`, antar-fastapi PR #293). Frontend only.

---

On the topic read screen (the one that shows a topic's **best window** and **watch window**), show who in the user's Circle has an overlapping window. Frontend only; do NOT compute overlaps, dates or names yourself and do NOT add astrology logic.

**Auth (important):** `shared_with` is Circle data, so the server only includes it when the request is authenticated as the chart's owner. Send the same `Authorization: Bearer <token>` header you use on the Circle calls (guests: the `X-Claim-Token` header, as on Circle). Without it the call works exactly as before and the field is simply absent. Do not add any new request: this is the same `topic-read` call, now with the auth header.

**Data:** `best_window` and `watch_window` (each may be `null`) can now carry an additive field:
`shared_with: [{ "chart_id": "...", "first_name": "Aarav", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" }]`
- `start`/`end` are the stretch where THEIR window overlaps THIS window (always inside it). Earliest first, at most 5.
- Absent (or empty) means nobody. Never assume it exists.

**Render, under the window it belongs to (best under best, watch under watch):**
- A small, quiet row of people: initial-avatar chips with the `first_name`, and beneath/next to each the overlap range formatted with the user's locale (e.g. `Intl.DateTimeFormat`, short month + day, e.g. "Oct 13 – 17"; if `start === end` just one date). No sentence, so no new copy to translate; do not invent wording like "also open for" — if you need a section label, reuse the existing localized word for the Circle/People (en/es/pt/hinglish) and add nothing else.
- Same tone as the window: neutral/positive accent under a best window, the existing soft "care" accent (amber, never red, no warning icon) under a watch window.
- Tapping a chip opens the existing Between us pair page for that `chart_id` (same route as the Circle list); do not add a route.
- If `shared_with` is missing or empty: render nothing. No placeholder, no "nobody", no skeleton, no reserved space.

**Guardrails:** show only what is in the payload: first name and the overlap dates. Never show the other person's own window, score, chart or anything else; never fetch their chart. No predictions, emojis, counts like "3 people", or countdowns. Don't hide or reorder the existing window content; this is purely additive. Don't block the read on it (it is in the same response). Don't cache it longer than the existing topic-read query: it changes when someone joins or leaves the Circle. Don't show it for the demo chart (the server won't send it).

**Acceptance:** an owner with a joined friend whose window overlaps sees the friend's chip and the overlap range under the matching window; with 7 overlapping friends only the 5 sent are shown; a care overlap sits under the watch window with the soft accent; no overlap, signed-out or guest-without-token → no extra UI and no layout gap; the rest of the topic read is unchanged in every language.
