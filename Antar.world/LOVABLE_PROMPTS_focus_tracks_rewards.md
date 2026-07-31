# Lovable prompts — Focus / Today · Two-track Remedies · Coach reward copy

All three back-ends are LIVE. Paste these into Lovable **one at a time**, let each
finish building and preview it, then do the next. Same API base URL + auth headers
as the app's existing `/api/v1/*` calls. Never render planet names, house numbers,
or internal fields (`source`, `priority_label`, `systems`).

---

## PROMPT 1 — Today: "What's in play now" + "Be ready" + commitment

```
On the Today page, add a card at the TOP fed by a new backend endpoint. Use the same API base URL and auth headers as our other /api/v1 calls.

Fetch: GET /api/v1/focus/{chartId}
Response:
{
  "available": true,
  "focus":   { "whats_in_play": "Harmony & Connection", "one_action": "…" },
  "be_ready": { "kind": "a health-sensitive stretch", "when": "2026-01", "prep": "…" },
  "anushthana": { "days": 12, "message": "You've tended … for 12 days — 9 more to a 40-day anushthana. Runway toward …", "days_to_next": 9, "next_at": 40, "completed_cycle": 21 }
}

Render, using our existing card styling:
1. A "What's in play for you now" card: heading = focus.whats_in_play; one line below = focus.one_action.
2. Under it, a warm one-liner = anushthana.message (encouragement, never pressure). Optionally a thin progress bar toward anushthana.next_at.
3. If be_ready is not null, a smaller CALM heads-up card beneath: "Coming: {be_ready.kind} around {when}." then a muted sub-line = be_ready.prep. Format be_ready.when ("YYYY-MM") as friendly text e.g. "early 2026". Tone: empowering ("here's your runway"), never alarming.

Rules: if available is false or the call errors, hide the whole block silently (no error). If anushthana.days is 0, show its message as a gentle invitation to begin. Never show planet names, house numbers, "systems", raw dates, or any "streak lost / level up" language. Do not change anything else on Today.
```

---

## PROMPT 2 — Practice → ACTIVE tab: two complementary tracks

```
On the Practice tab's ACTIVE sub-tab, rebuild the "All active remediations" list as TWO labelled sections, and switch its data source to GET /api/v1/remedies/{chartId} (use the existing, currently-unused fetchRemedies helper; same API base + auth).

Each remedy from that endpoint has: track ("calm" | "strengthen"), track_label, and plain-language action / mantra / gemstone text. ALSO keep the existing practice cards + mantra_of_the_day from the practice schedule payload — do not drop them; place them in the "calm" section (they share the same focus).

Render two sections, in order (skip a section that has no items):
1. "Calm what's testing you" — the practice card(s) + mantra_of_the_day + every remedy with track === "calm". The first item is the primary.
2. "Amplify your natural strength" — the chart gemstone (track:"strengthen") + any remedy with track === "strengthen".

Add one intro line under the two headers:
"Two moves that go hand in hand: soften what's straining you, and lean into your natural strengths."

Rules: never show "source", "priority_label", planet names, or house numbers — only track_label, the energy/plain-language text, and the action. Keep our existing card styling and the ACTIVE tab's other elements (streaks etc.) unchanged.
```

---

## PROMPT 3 — Milestone rewards in the coach's voice

```
When the streak or practice endpoints return an awards[] array (each award has: kind, amount, for, message), show the award's `message` as the celebration copy — it is already written in a warm coach voice that acknowledges the person's consistency.

Do NOT render "you earned N credits", "level up", "streak unlocked", or points. The `message` is the headline; the credit amount may show small/secondary. Never show "streak lost" or guilt language anywhere. If there are multiple awards, show each message on its own line.
```

---

## After you publish
1. Log in with your Google session in the published app.
2. Tell me it's live — I'll audit it through the browser (Today card, Practice → ACTIVE two tracks, a reward moment, an Ask answer, the Places screen) and come back with specific questions to tune the model further.
