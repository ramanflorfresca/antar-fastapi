# Lovable brief — Life Chapter "WHAT'S AHEAD" conviction: two honest tiers, plain words, calm colour

## Problem
Each upcoming-event card shows a coloured dot with a "How sure is this?" tooltip
that lists **three** tiers — High (green), Medium (amber), Low (hollow). Two
things confuse users:

1. **"High" can never occur.** The backend hard-caps conviction at `medium` until
   the D9/D10 divisional layer ships. So the green "High — plan around it" tier is
   advertised but **never appears** — every real card is amber or hollow.
2. **Amber reads as a warning.** On neutral or positive events ("A partnership
   window opens", "Family grows", "Something you create or lead") an amber/caution
   dot signals danger, which is wrong. And since every card is the same amber, the
   colour distinguishes nothing — the user is decoding a colour that carries no
   information.

## What the backend now sends
Every item in `life-arc` `predicted_events[]` — **and** every event under
`cycle_timeline[].events[]` — now includes:
- **`conviction`** — `"medium"` or `"low"` (the string; `"high"` will not occur).
- **`conviction_label`** — the plain word to display: **`"Likely"`** (medium) or
  **`"Early signal"`** (low). (Reserved `"Strong signal"` for a future High.)

## Changes
1. **Show the word, not just a colour.** Render `conviction_label` as a small
   text tag on the card (e.g. a subtle pill or caption: "Likely" / "Early
   signal"). The word is the primary signal; the dot is secondary.
2. **Collapse to two tiers in the tooltip.** Drop the "High" row entirely until
   the backend actually sends it. New "How sure is this?" copy:
   > Antar reads your chart through several independent lenses. This is how many
   > of them point to the same event in the same window.
   > • **Likely** — a clear signal, more than one lens agreeing. Worth planning around.
   > • **Early signal** — one lens so far, still forming. Worth watching, not acting on yet.
3. **One calm accent, not a traffic light.** Use the app's teal/green accent (the
   same as "You're here") for the **Likely** filled dot, and a hollow/outline dot
   for **Early signal**. Do **not** use amber/red — reserve warm-warning colours
   for genuinely adverse events only (none of these forward cards are adverse).
4. **Future-proof:** if `conviction === "high"` ever arrives, show
   `conviction_label` ("Strong signal") with a brighter/filled accent and you can
   re-introduce the third tooltip row then — but don't render it until it appears.

## Do NOT
- Do not invent your own conviction thresholds — render what the backend sends.
- Do not keep the three-colour legend "for completeness"; a tier that never
  appears is what caused the confusion.

---
Backend: `main.py` sets `conviction_label` on `predicted_events[]` and
`cycle_timeline[].events[]` (commit f25fb1e), map in `_CONVICTION_LABEL`.
Pairs with `LOVABLE_BRIEF_lifearc_event_labels.md` (render `label`/`detail`).
Owner ask 2026-09-23 (Harleen/Leena card: colours + "what we're predicting" unclear).
