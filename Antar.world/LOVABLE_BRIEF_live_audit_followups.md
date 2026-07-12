# Lovable brief — live-audit follow-ups (2026-07-12)

Three frontend-only fixes from a live QA pass on antar.world. The rest of that
audit (debug-string leak, timing contradiction, "axis" jargon, em-dash casing,
copy-pasted Places cards) was fixed in the backend and is on `main`.

## 1. Confidence label contradicts the signal count (Ask / prediction card)
The card shows e.g. **`CONFIDENCE · HIGH`** next to **`2 of 4 systems agree`** —
HIGH next to half-agreement reads as a contradiction.

Root cause: two different things. The **tier** ("HIGH") is one backend field
(verdict strength). The **"N of 4"** is composed *in the frontend* by counting how
many of the four signal rows (Timing / Current sky / Chart patterns / Your
history) are ACTIVE. The backend never emits "N of 4", so only the frontend can
reconcile them.

**Fix (pick one):**
- **Copy (simplest):** relabel the sub-line `{n} of 4 signals active` instead of
  `{n} of 4 systems agree`. "Active" describes evidence breadth and no longer
  fights the tier word.
- **Logic:** derive the tier word from the count you already render:
  `≥3 → HIGH · 2 → MODERATE · ≤1 → LOW`, and use that instead of the raw tier.

## 2. Action label is force-title-cased
The "YOUR MOVE" line renders **"Act On The Money Decision within the window
shown"** — only the front clause is capitalised, which is a `text-transform:
capitalize` on the label. The backend sends **sentence case** ("Act on the money
decision…"). **Remove the `text-transform: capitalize`** from that element.

## 3. Places tier legend
Update the hardcoded legend to match the backend cutoffs:

**`FLOW ≥ 55 · MIXED 35–54 · STRAIN < 35`**

Better: drop the numbers and colour off the per-city `tier` string
("FLOW"/"MIXED"/"STRAIN") the backend already sends, so a future calibration
change can't desync the legend again.

---
_Optional hardening:_ the backend no longer emits `L1:`/`L2:` debug into
`factors[]`, but older cached predictions may still contain them — the frontend
can defensively drop any `factors` entry starting with `L1:` or `L2:`.
