# Lovable Brief — "Did it hold?" check-back on the topic-first Ask home

UI only. The backend is done (antar-fastapi PR #246). **Do not compute, re-word, translate or
filter anything**: every string below (question, option labels, thanks) arrives already written
in the person's language. Render it verbatim. Do not add a "Did this feel right?" prompt — this
replaces it. A feeling is weak evidence; this asks after a window has actually ended.

## What it is
After a dated window we showed on a topic (a good stretch, or a caution) has **passed**, ask the
person once, in one line: did it hold? Their answer is the real accuracy signal. Hits and misses
count equally, so never nudge toward "yes".

## API (no auth header needed; the chart id is the key, so guests work the same as signed-in users)

**1. Fetch what is due**
`GET /api/v1/chart/{chart_id}/topic-checkbacks?language={ui language}`
```json
{"count": 1, "checkbacks": [{
  "id": "6b1f0c52-…",
  "topic": "money", "topic_label": "Money", "kind": "best", "scale": "month",
  "window": {"start": "2026-10-14", "end": "2026-10-20", "label": "Oct 14 – Oct 20"},
  "question": "Your money window, Oct 14 – Oct 20, has passed. Did it hold?",
  "options": [
    {"value": "yes", "label": "Yes, it held"},
    {"value": "no", "label": "No, it didn't"},
    {"value": "not_sure", "label": "Not sure yet"}],
  "reask": false, "language": "en"}]}
```
- Returns **one** item by default (one question at a time). Leave `limit` off.
- `kind` is `"best"` (a good stretch) or `"watch"` (a caution). Wording and option labels already
  differ ("Yes, it held" vs "Yes, it mattered"); do not branch on it for copy. Use it only for an
  optional tiny accent (e.g. a calm teal dot for best, an amber dot for watch).
- `count: 0` or any error or network failure → **render nothing, silently**. Never show an error
  or empty state for this.
- `reask: true` means they said "Not sure yet" before; the `question` already begins with
  "Last time you weren't sure yet." Render identically.
- Pass `language` as the UI language (`en`, `es`, `pt`, `hinglish`; send `hi` as-is, the server
  falls back to English).

**2. Answer**
`POST /api/v1/chart/{chart_id}/topic-checkbacks/{id}/answer?language={ui language}`
body `{"answer": "yes" | "no" | "not_sure"}` — send the option's `value`.
```json
{"saved": true, "already_answered": false, "outcome": "yes", "id": "6b1f…",
 "thanks": "Thanks — noted. Hits and misses both help us get this right."}
```
- Show `thanks` for ~2.5 s in place of the card, then re-fetch the list; if another is due it
  appears (still one at a time), otherwise the slot disappears.
- `already_answered: true` (double tap, another device) is **not** an error: show `thanks` the same.
- `404` or `503` → keep the card, show nothing alarming; let them tap again. No toast with codes.

## Where
On the topic-first Ask home, **above the topic tiles**, as a single quiet card. It is also fine to
show the same card at the top of an opened topic read **for that topic** (`topic` matches). Fetch
on mount and on app foreground; do not poll.

## Look
- One compact card, same radius and surface as existing cards, not a modal, not a banner, never
  blocks the tiles. Dismissible only by answering (no X); it simply returns next visit if ignored.
- `question` as the card text (it contains the date range; keep it on 2–3 lines max, wrap, no truncation).
- Three equal-weight buttons in a row (stack vertically under ~360 px): `options[].label`.
  **Equal weight**: no primary-colored "Yes", no default selection. "Not sure yet" is the same
  size, just lighter text.
- Disable all three on tap and show a small inline spinner on the tapped one; optimistic UI is
  fine but fall back to the card if the POST fails.
- Tap targets ≥ 44 px, readable in light and dark, respects the app's existing language switcher
  and RTL/long-string wrapping (Hinglish and Spanish labels run longer).

## Don'ts
- No percentages, streaks, rewards, scores or "help us improve" copy beyond the returned `thanks`.
- No prices or plan mentions anywhere near it.
- Do not re-ask on the client, store answers locally, or hide the card based on local state:
  the server decides what is due and never asks a closed question twice.
- Do not touch `/api/v1/outcomes/*` or the Yes/No "did it happen?" card; this is a separate card
  for topic windows and the two may both appear (topic card first on Ask home, Yes/No card in
  its existing spot).
- Do not change existing topic-read or topics rendering.

## Acceptance
1. With no due items the home looks exactly as today (no gap, no placeholder).
2. A due item shows its `question` and three equal buttons in the UI language.
3. Tapping posts the `value`, shows `thanks`, then the card disappears or shows the next one.
4. Network failure on GET → nothing rendered; on POST → card stays, no error text.
5. Works for a guest (no token) exactly as for a signed-in user.
