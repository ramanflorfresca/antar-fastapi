# Lovable brief — Today card: warm multi-beat "Dear {name}…" reading

## Why
The Today daily reading shifted (2026-07-08) from a terse two-item to-do list to a
**warm, whole-life reading** — a "Dear {name}, here's how your day is moving…"
walk through every life-area the engine actually computed, ending on the precise
timing window. The backend change is **live**. The app should render it as a warm,
readable multi-beat card, not a single dense block.

## The data is already there
`GET /api/v1/daily-signal/{chart_id}` (also `POST` with a body) returns, among
other fields:

```json
{
  "headline":  "Dear Raman, today nearly every corner of your life has wind behind it.",
  "highlight": "Dear Raman, today has a forceful, direct quality — push hard, but don't bulldoze what matters. Your sibling or a short trip you've been putting off could move something real forward today… Your savings and the money you keep are in a good spot… Home is quietly strong too; your mother or something tied to your home or a vehicle could bring support… At work, your boss is likely to notice you… Your network and income are also live… The best window to act is between 11:52 am and 12:44 pm… Hold off on locking in any big commitments before 9:00 am.",
  "direction": "positive",           // "positive" | "adverse" | "quiet"
  "strength":  "high",               // "high" | "medium" | "low"
  "highlight_areas": ["siblings","money","home","work","network"],   // fine life-areas that fired
  "highlight_domains": ["work","money","relationships"],             // coarse rollup
  "todays_move": {                   // the timing close (a.k.a. "hora")
    "best_window":  "11:52 am - 12:44 pm",
    "best_for":     "the work that needs to be seen — ship it, present it, push the decision",
    "avoid_window": "7:30 am - 9:00 am",
    "avoid_what":   "locking in big commitments or forcing a decision"
  },
  "todays_nudge": "…",               // optional one-line action; omitted on quiet days
  "narration_source": "claude",      // "claude" = warm LLM read; absent = deterministic fallback
  "evidence": { … },                 // ADMIN/DEV ONLY — never render
  "_debug_reasoning": { … }          // ADMIN/DEV ONLY — never render
}
```

## What to render
1. **Title** = `headline` (already a warm characterizing line, ≤ ~90 chars).
2. **Body** = `highlight`, rendered as a **warm multi-paragraph reading**, not one
   block. Each beat is its own short paragraph (see "Paragraph breaks" below).
   Comfortable line-height, generous paragraph spacing — this should read like a
   note from someone who knows you, on mobile.
3. **Timing close** = a small "Your move" strip from `todays_move`:
   - "Best window" chip → `best_window` + `best_for`
   - "Ease off" chip → `avoid_window` + `avoid_what` (show only if present)
   - If `todays_nudge` is present, show it as the single call-to-action line.
4. **Direction accent** — tint/icon by `direction` (`positive` = warm/up,
   `adverse` = caution, `quiet` = calm/neutral) and `strength` for emphasis.
5. **Quiet days** (`direction: "quiet"`, `highlight_areas: []`) — the `highlight`
   is a short honest "quiet day" note; render it plainly, skip the beat treatment.

## Paragraph breaks — pick one
The warm `highlight` currently arrives as **one flowing string**. Two options:
- **Frontend-only (ship today):** render `highlight` with sensible paragraph
  styling; optionally split into paragraphs on sentence groups for breathing room.
- **Backend-assisted (recommended, small change):** we add explicit paragraph
  breaks (`\n\n`) between beats, or a structured `beats[]` array
  (`[{area, text}]`) aligned to `highlight_areas`, so the app renders clean
  per-beat paragraphs (or cards) with zero heuristics. **Tell us which and we'll
  ship it** — `beats[]` is the cleaner contract if you want per-area cards or
  icons.

## Do NOT render
`evidence` and `_debug_reasoning` are the internal audit trail (votes → net →
chosen → dasha tone). They must stay dev/admin-only and never reach the UI.

## Acceptance
- A day that lit ≥3 life-areas shows ≥3 distinct beats (paragraphs), each about a
  real life-area — not a single paragraph and not a 2-item to-do list.
- The reading opens warmly with the name and closes on the concrete timing window.
- No astrology/jargon appears (backend already scrubs; if any leaks, tell us).
- Quiet days render as a calm single note, not a manufactured multi-beat.
