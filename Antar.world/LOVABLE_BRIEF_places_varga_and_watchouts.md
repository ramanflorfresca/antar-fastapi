# Lovable brief — Places: render `varga`, `feel`, `drishti` and the sharper watch-outs

> **Backend status:** PRs antar-fastapi #414 (house-lord karakas + trap-line watch-outs), #415 (`varga`),
> #416 (veto watch-outs), #417 (dasha multiplier), #419 (condition/dig-bala, no UI), #420 (`feel`, `drishti`,
> four more watch-outs). Check they are merged to `main` and deployed before
> building; until then the fields below are simply absent (the FE must tolerate that).
> **UI-only work. Do not compute, score, re-order, or re-word anything on the client.**

## Why
Two things now carry more of the astrocartography reading, and neither is visible in the app yet:

1. **A "deeper chart" confirmation line per place** (`varga`). A line and a house shift say *where* the energy
   lands; the deeper partnership chart (for love) or working-life chart (for career/business) says whether
   that place can actually *carry* it. It is one plain sentence, supportive or cautionary.
2. **Hard-caution watch-outs.** Combinations that read badly whatever the average score says (e.g. the
   area's own engine is stalled in that place; the current chapter works against moving there) now lead the
   existing `watch_outs`. They must not be buried or styled like a mild note.

## Change 1 — render `varga`

### Where it arrives
A new array **`varga`** on each place card, on all three Places endpoints:

| Endpoint | Where |
|---|---|
| `POST /api/v1/places/concern` | `ranked_cities[].varga` |
| `POST /api/v1/places/potential` | `places[].varga` |
| `POST /api/v1/places/prescribe` | each fix in `within_reach[]` / `bigger_move` → `varga` |

```json
"varga": [
  { "varga": "D9", "polarity": "friction",
    "text": "Seen through the deeper partnership chart for this place, your discipline and structure lands on harder ground — closeness here asks for more work than the line alone suggests." },
  { "varga": "D9", "polarity": "supportive",
    "text": "Seen through the deeper partnership chart for this place, your relationships and taste lands on supportive ground — a relationship here reads as able to deliver what the line suggests." }
]
```

- **Present only for** love (`D9`) and career / business (`D10`). For money, health, peace, family, and for
  `overall` it is an **empty array** `[]` (or absent). Render nothing — no placeholder, no "not available".
- **0, 1 or 2 items.** Neutral placements are omitted by the backend. A `friction` item is always first.
- `text` is already plain language and already localized (en/es). **Render it verbatim.** Never show the
  `varga` code (`D9`/`D10`), the word "navamsa"/"dashamsa", planet names, or house numbers to the user.

### How to render
- A single quiet line (or two) **under the place's main reason / "what changes here"**, above the watch-outs.
  Small leading glyph only: a soft check-style marker for `supportive`, a caution marker for `friction`
  (use the app's existing tone colours; `friction` = the existing amber/caution treatment, **not** red).
- Optional label above it, localized: **"Deeper check"** (en) / **"Revisión más profunda"** (es).
- Collapsed by default on the compact list card; shown on the expanded card / place detail. On
  `/places/prescribe` fix cards, show it in the expanded state only.
- **Never** let `varga` change a place's tier, badge, rank or order. It is a qualifier, not a score.

### Copy rule
Do not paraphrase. These lines are deliberately hedged ("reads as able to…", "asks for more work than the
line alone suggests"). Rewording them into promises ("you will meet someone here") is a product violation.

## Change 1b — render `feel` and `drishti` (PR #420)

Two more descriptive fields on the **same cards and endpoints as `varga`** (`ranked_cities[]`, `places[]`,
prescribe fixes). Both are `null` when unavailable. Both are qualifiers only: no score, no tier, no ordering.

```json
"feel":    "Day to day, life in this place is likely to feel warm, social and pleasure-seeking.",
"drishti": { "polarity": "supportive",
             "text": "Supportive influences (your relationships and taste / …) look onto the partnership side of this place, easing it." }
```

- **`feel`** is a plain string, present for every concern whenever the place could be computed. Render it as
  a quiet one-line "How it tends to feel" caption (localized label: **"How it tends to feel"** / **"Cómo suele sentirse"**)
  near the place's headline or signature, in a neutral tone (no caution/positive colour). Expanded card only on compact lists.
- **`drishti`** is present **only for love, career, business and health**, and only when the backend finds an
  imbalance (otherwise `null` — render nothing). `polarity` is `"supportive"` or `"testing"`:
  `supportive` = soft positive marker; `testing` = the existing amber caution marker (not red). Put it directly
  under the `varga` lines (same "Deeper check" group) so the three — `varga`, `drishti`, `feel` — read as one
  "how this place sits for you" block, in that order: **deeper check → influences → feel**.
- Render `text` and `feel` **verbatim**; never show "drishti", "aspect", "nakshatra", planet names or house numbers.
- If both `varga` and `drishti` are testing/friction, do not stack two alarming blocks: show the first caution
  with its marker and the rest as normal-weight lines.

## Change 2 — surface the sharper `watch_outs`

### No new field
New caution kinds arrive in the **existing** fields — `ranked_cities[].watch_outs` (array of strings, up to 2)
and `ranked_cities[].watch` (the single most important). The backend now puts the hard cautions **first**, so
the first string is the one that matters most. If the app already renders `watch_outs`, this is mostly a
**styling/priority** change; if it only renders `watch`, nothing else is needed.

The strings that can now appear (examples, en):

- "The part of your chart that carries *{area}* falls into a house of loss and endings in this place — the
  engine of this area runs stalled here, whatever the lines promise."
- "Your current chapter is led by *…*, and in this place it lands in a house of loss and endings — the timing
  leans against moving here for *{area}*."
- "Your *…* — the core support for *{area}* — is weak in you and lands in a hard house here — …"
- "A hard, testing line … runs close to the partnership point of this place — closeness here tends toward
  friction before it settles." (love only)
- "Your line of *…* runs close here, and in your chart it belongs to the side of life that pulls energy away
  from *{area}* — a line that looks helpful can come with more friction than it promises."
- (PR #420) "The planet that anchors your whole chart falls into a house of loss and endings in this place — your
  general vitality and footing run lower here, whatever else the lines promise." (any concern)
- (PR #420) "Your line of *…* — which in your chart governs sudden change and what is hidden — runs close to a
  main point of this place — expect upheaval or hidden costs to surface more readily here."
- (PR #420) "A restless, destabilising line (*…*) runs close to the self or career point of this place — fast rises
  are possible, but so is instability."
- (PR #420) "Your *…* — a core support for love — is weak in you and its line runs close to the partnership point of
  this place — closeness here may feel thinner than the line suggests." (love only)

### How to render
- **First watch-out = caution row, visually distinct** from the supportive reasons (the existing amber caution
  style; icon + text, not just a colour). The second, if present, uses the same style but lighter.
- Show on the compact card as **one line with a "Watch" marker**, full list on expand.
- **Do not hide a place because it has a watch-out** and do not re-sort by it. The backend decides ranking.
- Strings are final copy — render verbatim, no truncation mid-sentence (clamp to 3 lines with "more" on expand).

## Known gaps (backend, not for Lovable to work around)
- ~~`/places/potential` and `/places/prescribe` do not return `watch_outs`~~ — **fixed (PR #422)**: `places[]`,
  `bigger_move`, and every prescribe fix (`within_reach[]`, `bigger_move`) now carry `watch_outs` (array of up
  to 2 strings, hard cautions first). Render exactly as on `/places/concern`. On `/potential` show them on the
  expanded place card; on `/prescribe` show the first one on the fix card (a fix that comes with a caution must
  say so — never hide it behind the lift badge).
- Portuguese: the new watch-outs and `varga` lines fall back to **English** for `pt` (Places has no pt
  template bank yet). Localize `pt` only after the backend adds them; don't machine-translate on the client.

## Acceptance checklist
- [ ] Love and career/business places show the "Deeper check" line(s); other concerns show nothing extra and no empty gap.
- [ ] `friction` lines read as caution (amber), `supportive` as a soft positive; neither changes the tier badge or order.
- [ ] No "D9"/"D10", "navamsa", planet names or house numbers appear anywhere in the UI.
- [ ] The first `watch_outs` string is visually the strongest caution on the card; second is lighter; at most two.
- [ ] `varga` missing / `[]` / `null` and `watch_outs` missing / `[]` all render without errors or layout jumps.
- [ ] Spanish renders the Spanish strings; `pt` shows the (English) strings without breaking layout.
- [ ] Works on `/places/concern`, `/places/potential` and `/places/prescribe` cards.
- [ ] `feel` shows as a neutral one-line caption on every card that has it; `null` renders nothing.
- [ ] `drishti` appears only for love/career/business/health when non-null; `supportive` = soft positive, `testing` = amber; neither alters tier/order.
- [ ] The three qualifiers read in order — deeper check, influences, feel — and never produce two stacked alarming blocks.
- [ ] No "drishti", "aspect", "nakshatra", planet names or house numbers visible anywhere.
- [ ] With up to two watch-outs, the hard ones (lord stalled, chapter against the move, etc.) are the ones shown first.
