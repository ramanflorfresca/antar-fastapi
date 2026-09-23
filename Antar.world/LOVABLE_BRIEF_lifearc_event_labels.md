# Lovable brief — Life Chapter "What's ahead" event labels (render backend labels)

## Problem
On the Life Chapter → "WHAT'S AHEAD" timeline, event cards show vague/wrong text:
"Family grows", "Family grows again" (same date, duplicated), "A meaningful moment".
The backend now emits a **corrected, life-stage-aware label per event** — the FE
must render *that*, instead of its own event_type→text map.

## What the backend now sends
Each item in `life-arc` `predicted_events[]` may now include two new fields:
- **`label`** — the user-facing card title (already plain, already age/gender-corrected).
- **`detail`** — one plain sentence explaining it (good for the ⓘ tooltip / sub-line).

Example (a 51-year-old woman — a 5th-house signal correctly reframed away from childbirth):
```json
{ "event_type": "creative_venture", "window_start": "2026-11-…",
  "label": "Something you create or take charge of",
  "detail": "A 5th-house opening — a creative project or venture you bring to life, or a student / protégé you take on. Not a child at this stage.",
  "reframed_from": "family_expansion_first" }
```
And when childbirth *is* plausible (e.g. a younger user or a man):
```json
{ "event_type": "family_expansion_first",
  "label": "A child may join the family",
  "detail": "A likely addition to your immediate family — a birth, an adoption, or a child you take in." }
```

## Changes
1. **Render `label` as the card title when present** (fall back to the existing
   event_type map only when `label` is absent). This immediately fixes
   "Family grows" → the corrected wording, with no FE astrology logic needed.
2. **Render `detail` in the ⓘ tooltip / expandable** (fall back to existing copy).
3. **The backend already de-duplicates** family-expansion events landing in the
   same window, so "Family grows" + "Family grows again" on the same date should
   no longer appear. If you also de-dupe client-side, key on
   `event_type + window_start(month)` so you don't collapse genuinely distinct events.
4. **The domain chip** (FAMILY / RELATIONSHIP / WORK) can stay; but for a
   `reframed_from` / `creative_venture` event, prefer a neutral chip
   (e.g. "CREATIVE" or "WORK") over "FAMILY".

## Do NOT
- Do not invent your own age/gender logic for childbirth — the backend owns it now.
- Do not relabel a 5th-house signal as "grandchild" (that's the 9th house; wrong).

---
Backend: `_life_arc_compute` in main.py now sets `label`/`detail`/`reframed_from`
on `predicted_events[]` (commit ae95954). Owner ask 2026-09-23 (Harleen/Lina case).
