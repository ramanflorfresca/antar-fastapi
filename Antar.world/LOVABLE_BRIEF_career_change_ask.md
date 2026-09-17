# Lovable Brief — Surface career/business-change questions on Ask

**Status:** Backend LIVE (antar-fastapi commit `10e7012`, 2026-09-16). FE work is
discoverability + a render check only — **no new endpoint, no new response fields.**

## What changed on the backend

Ask Antar now answers career/business-**change** questions — a career switch,
quitting a job, starting your own business, a business pivot, a change in
direction — with a real life-chapter **timing** verdict (the WHEN + the nature of
the change: chosen vs forced, own-venture vs new-job vs status shift).

It comes back through the **existing** `POST /api/v1/predict` response, populating
the **same answer-card fields you already render** for move/legal/health questions:

| field | example value |
|---|---|
| `signal_line` | "The most likely window for a career change is around 2026." |
| `timing_window` | "around 2026" |
| `action_item` | "Lay the groundwork now — skills, network, a runway of savings; don't force the exit early. The window opens around 2026." |
| `plain_summary` | (narrated prose, same as today) |

**Do NOT add or expect any new keys.** There is no score, tier, badge, or
success-probability for these questions — the verdict is intentionally **timing +
nature only** (we time the change, we never claim whether it succeeds).

## FE work — two changes only

### 1. Discoverability — add career-change starter prompts
On the Ask page's suggested-question chips/examples, add this cluster alongside
the existing love / money / health / move ones:

- "Should I change my career?"
- "Is it time to switch jobs?"
- "Should I quit and start my own business?"
- "Is a business pivot coming for me?"

Tapping a chip submits the text verbatim to `/api/v1/predict`, exactly like a
typed question. No special routing.

### 2. Verify the answer card handles a chapter-level window
For these questions the answer is **chapter-level**, identical in shape to what
residence/legal/health already return:

- `timing_window` is a chapter phrase like **"around 2026"** — NOT an intraday
  "next 24–48h" / "reassess in 3 weeks" string.
- `signal_line` is a full sentence, not a fragment.

Confirm the card:
- renders the sentence and window without truncation,
- does **not** append any "today / this week / right now" daily framing to a
  chapter answer,
- shows `action_item` in the existing action slot.

If move/legal/health answers already render correctly on this card (they do),
career-change needs no card changes — just the starter prompts in step 1.

## Do NOT
- Do not add a new API call, hook, or type — it's the existing predict response.
- Do not add success/probability/"good vs bad" styling or a verdict badge for
  these — render the text as-is.
- Do not gate it behind a paywall differently from other Ask questions.

## Test questions (any chart)
"Should I change my career?" · "When should I switch careers?" · "Should I quit my
job and start my own business?" · "Is a business pivot coming for me?" — each
should return a `signal_line` about a career-change window + a groundwork
`action_item`, with a year-level `timing_window`.
