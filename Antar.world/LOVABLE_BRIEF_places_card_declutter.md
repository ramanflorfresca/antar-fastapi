# Lovable Brief — Places card de-clutter (P2)

**Goal:** each recommended place should read in one glance. Today every card renders
signature + primary_reason + a 5-layer `reasons[]` + secondary_reasons + watch +
watch_outs + LK findings — a wall of text per city. Backend already returns a
concise summary; just render less by default.

## Render THIS per place card (default, collapsed)
From each item in `ranked_cities[]`:
1. **`{city}, {country}`** — title
2. **Tier chip** from `tier` → `FLOW` = "Great for {goal}" (green) · `MIXED` = "Mixed" (amber) · `STRAIN` = "Avoid for {goal}" (grey/red). *(Tier legend: FLOW ≥55 · MIXED 35–54 · STRAIN <35.)*
3. **One sentence** = `signature.one_line` (already jargon-free). Nothing else.
4. **One trade-off line** = the FIRST item of `watch` / `watch_outs` if present, prefixed "Trade-off: …". Skip if empty.
5. **Delta vs current home** = `delta` as a small "+N vs {current city}" pill.

That's it. No `reasons[]`, no `secondary_reasons`, no `lk_relocation_findings` on the face of the card.

## Behind a single "Why this?" expander (tap to open)
Only when the user taps: show `primary_reason`, then `reasons[]` grouped by layer
(NATAL / DASHA / AGE / INTENT / WATCH), then `lk_relocation_findings[]`. Everything
that's on the card today moves here.

## Named-city mode (positives AND negatives)
`POST /api/v1/places/city` for a typed city: same card, but ALWAYS show BOTH a
positive line and a trade-off line (owner: "give the positives and negatives on
it"). If `tier` is STRAIN, lead with the trade-off but still name one upside.

## Map
Call `GET /api/v1/places/lines/{chart_id}?concern={goal}` (NEW param) — it now
returns only the goal's ~3–6 lines (was 36) + ≤6 parans. Draw those only. Never
render the unfiltered 36-line map by default.

## Copy rules (unchanged)
Never show a planet, house number, sign, or "line/paran/navamsa". `signature.one_line`
and the tier chips are already stripped; keep it that way.
