# Lovable Brief — render remedies as TWO complementary tracks

Backend is shipped. Every remedy and the chart gemstone now carry a `track` and a
human `track_label`. The UI just needs to **group by `track`** so the two classical
tracks read as complementary, not contradictory.

## The data (already on the responses)
- `GET /api/v1/remedies/{chart_id}` → each remedy object has:
  - `track`: `"calm"` or `"strengthen"`
  - `track_label`: `"Calm what's testing you"` or `"Amplify your natural strength"`
- Practice schedule payload → `chart_gemstone` has `track: "strengthen"`, `track_label: "Amplify your natural strength"`.
- The daily/practice card + mantra already target the SAME planet as the `calm` remedies (backend guarantees this now).

## What to render
Two labelled sections, in this order:

1. **Calm what's testing you** *(track = "calm")*
   The focus of this chapter — the area under pressure. Group all `track:"calm"`
   remedies here. The FIRST one is the primary (it matches the daily practice +
   mantra — same energy). Show the mantra + practice alongside it as "this week's
   support for the same thing."

2. **Amplify your natural strength** *(track = "strengthen")*
   The gemstone (and any `track:"strengthen"` remedy). Frame as "what already
   works for you — lean into it," distinct from the calming track.

## Copy guidance
- One line under the two headers explaining they work TOGETHER:
  *"Two moves that go hand in hand: soften what's straining you, and lean into your natural strengths."*
- Never show planet names, house numbers, `source`, or `priority_label` (internal).
  Only `track_label`, `energy_language`, and the action text.
- If a track is empty, hide its header (don't show an empty section).

## Why
Before: the mantra could target one planet (pacify the afflicted) while the
gemstone targeted another (strengthen a benefic) — with no labels, that read as
the app contradicting itself. These are the two legitimate halves of classical
Vedic remedy; labelling them makes Antar feel like one coherent astrologer.

*Backend refs (for QA, not the UI): remedy `track` set in `remedy_selector.select_remedies`; gemstone `track` in `practice_engine.generate_practice_schedule`.*
