# Lovable Brief — Today: "What's in play now" + a "Be ready" heads-up

New backend endpoint, additive (nothing else changes):

**`GET /api/v1/focus/{chart_id}`** →
```json
{
  "available": true,
  "focus":   { "whats_in_play": "Harmony & Connection",
               "one_action": "Create something beautiful this week. …" },
  "be_ready": { "kind": "a health-sensitive stretch", "when": "2026-01",
                "systems": 4, "prep": "build the rest/checkup habit now …" }
}
```
`be_ready` may be `null` (no converged window soon). `available:false` = chart data
incomplete — hide the section.

## Where + how to render (Today page)
1. **"What's in play for you now"** — a small card at the top of Today:
   - Title from `focus.whats_in_play` (already plain energy language — never a planet).
   - One line: `focus.one_action` (the single thing to do this week — the SAME
     energy as the daily practice + mantra + top remedy; they now all agree).
2. **"Be ready"** *(only if `be_ready` present)* — a quiet heads-up below it:
   - "Coming: **{be_ready.kind}** around **{be_ready.when}**."
   - Sub-line: `be_ready.prep` (how to prepare).
   - Tone: calm and empowering ("here's your runway"), never alarming. This is the
     coach anticipating — the thing that makes Antar feel proactive, not a lookup.

## Rules
- Never show planet names, house numbers, `systems`, or dates more than a few years
  out. `when` is a month-year; render as e.g. "early 2026".
- If `be_ready.kind` is the separation/health one, keep it gentle (a stretch to
  tend, not a doom forecast).
- Cache client-side per day; it's cheap but recomputes timing engines.

## Why
This is the spine of the "one intelligent guide": Today names the single FOCUS,
the daily action supports it, and a proactive window tells the user what's coming
and how to prepare. Same focus echoed across Ask, practices, remedies, and mantras
= it feels like one astrologer who knows you, not eight separate features.
