# Lovable prompt — "next shared window" line on the Circle list

Backend already live (`GET /api/v1/circle/{chart_id}`, antar-fastapi PR #290). Frontend only.

---

On the Circle home list, show one quiet line under each person in the **in_circle** state: the next stretch where the two of you overlap. Frontend only; do NOT compute windows, dates or wording yourself and do NOT add astrology logic.

**Data:** each item in `circle[]` with `state === "in_circle"` now has an additive field `next_shared_window`: either `null` or `{ "kind": "open" | "care", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "label": "<already localized sentence>" }`. Other states (invite_sent, private) never have it. The request is the same call you already make; optionally pass `tz_offset` (minutes, same value you send elsewhere) so "today" is the user's local date. No new request, no per-row fetch.

**Render:**
- If `next_shared_window` is non-null, show `label` verbatim as a single small secondary-text line under the person's name/relation row. Do not rewrite, translate, re-format or append to it; the server already localized it (en/es/pt/hinglish) from the `language` you pass.
- `kind: "open"` → neutral/positive treatment (the existing "open" accent used on the pair page). `kind: "care"` → the existing soft "care" treatment (amber-ish, never red, no warning icon, no alarm wording).
- If it is `null` or missing → render nothing. No placeholder, no "none", no skeleton, no empty line. Never reserve space for it.
- Tapping the line (or the row, as today) opens the existing Between us pair page; do not add a new route. Optionally pass `start` to scroll/highlight the matching window there, if it is trivial; skip otherwise.
- Do not show `start`/`end` yourself; the label already carries the range. Use them only for the optional highlight above.

**Guardrails:** it describes timing only. Don't add predictions, scores, emojis, countdowns ("in 3 days") or any text of your own. Don't show it on the private (not-yet-joined) rows. Don't cache it beyond the existing list query; it changes with the day. Don't block or delay the list on it (it is part of the same response).

**Acceptance:** a joined friend with an overlap shows e.g. "Your next shared open stretch: Oct 13 – Oct 17." under their name; a care overlap shows the softer "A shared stretch that asks for care…" line; a person with no overlap or unavailable windows shows no extra line and no layout gap; Spanish/Portuguese/Hinglish users see the server's text in their language; invite_sent and private rows are unchanged.
