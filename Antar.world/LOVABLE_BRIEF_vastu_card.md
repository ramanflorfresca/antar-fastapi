# Lovable brief — the Vastu card (Practices)

## Why
Antar now reads Vastu through the user's chart (Vastu-Jyotish, Parashari-based). The backend
decides everything — which directions support this person, which way to sleep, work and eat,
where common household objects sit best, and which area of the home is in focus during the
current life period. **The app only renders.** Do not compute, reorder, filter, or reword
anything: no direction logic, no object rules, no "good/bad" decisions in the front end.

Backend: `GET /api/v1/vastu/{chart_id}?language=<code>` (PR antar-fastapi#560).
**It is OFF in production behind a flag.** While off it returns
`{ "available": false, "reason": "disabled" }`. Build the card so that `available: false`
(for any reason, including `chart not found`) renders **nothing at all** — no empty card, no
error, no placeholder. When the owner turns the flag on, the card appears with no redeploy.

## Where it lives
A **Vastu** card in **Practices**, beside the Ayurveda card. Not in Rituals, not a new tab.
Title it "Vastu" (use the response's `headline`, don't hardcode).

## The response (all text is already plain language and already translated for `language`)
```json
{
  "available": true,
  "headline": "Your Vastu",
  "directions": {
    "sleep_head":  { "zone": "S",  "label": "South", "status": "strong", "why": "…" },
    "work_facing": { "zone": "E",  "label": "East",  "status": "strong", "why": "…" },
    "eat_facing":  { "zone": "E",  "label": "East",  "status": "steady", "why": "…" },
    "keep_light":  [ { "zone": "W", "label": "West", "why": "…" } ]
  },
  "zones": [
    { "zone": "E", "label": "East", "status": "strong", "status_label": "Supports you",
      "governs": "…", "place_here": ["…"], "keep_out": ["…"], "care_note": "…" }
    /* 8 entries, clockwise from East: E SE S SW W NW N NE */
  ],
  "objects": [
    { "id": "elephant_statues", "label": "Elephant statues",
      "best": ["South-West", "West"], "avoid": ["North-East", "South-East"],
      "note": "…", "contested": true,
      "for_you": { "best": ["South-West"], "tip": "…" } }
  ],
  "period": {
    "available": true,
    "focus":      { "scope_label": "This stretch", "label": "South", "status": "strong",
                    "status_label": "Supports you", "until_label": "Mar 2028",
                    "do": "…", "avoid": "…" },
    "background": null
  },
  "info": { "title": "…", "what_it_is": "…", "what_it_does": "…",
            "how_worked_out": "…", "what_it_isnt": "…" },
  "disclaimer": "…",
  "meta": { "tradition": "vastu_jyotish_parashari", "rules_verified": false, "version": "0.1" }
}
```

Key facts to design around:
- `status` is one of `strong` | `steady` | `needs_care` (codes — never show them).
  Show **`status_label`** ("Supports you" / "Neutral for you" / "Needs a lighter touch").
- `zone` / `id` / `src` / `meta` are machine codes. Use `zone` only as a stable key and for the
  compass position; **never display them**. Display `label`.
- Most users will have **few** flagged zones. The backend caps "needs a lighter touch" at 2 and
  "supports you" at 3. Most zones will be `steady`. Design for a calm card, not a red/green dashboard.
- `period.available` can be `false` (no zone needs attention right now). Then hide the period
  section entirely — don't show a "nothing" message. `period.background` can be `null`.
- `keep_light` can be an empty list. `place_here` / `keep_out` / `care_note` can be empty or absent.

## Layout — one card, four parts, top to bottom

### 1. Header with the (i) info button
- Left: `headline`. Right: a small **ⓘ** icon button.
- **Hover (desktop) / tap (mobile)** opens a popover/sheet from `info`:
  `title` as heading, then `what_it_is`, `what_it_does`, `how_worked_out`, `what_it_isnt` as four
  short labelled paragraphs. Close on tap-outside / Esc. It must be keyboard reachable
  (focusable button, `aria-label` from `info.title`, popover dismissible with Esc).
- Never auto-open. Never put this text anywhere else on the card.

### 2. "Your directions" (the top answer)
Three rows, each: a label (use the key names below — see Strings), the direction in large text
(`label`), and the one-line `why` in muted text.
- Sleep: head toward `directions.sleep_head`
- Work: face `directions.work_facing`
- Eat: face `directions.eat_facing`

Then, if `keep_light` is non-empty, one muted line per item: "`label` — `why`". Soft tone (amber or
neutral), **not red, no warning icon**. These are gentle, not alarms.

### 3. "Right now" (dasha line) — only if `period.available`
A compact block: `focus.scope_label` + `focus.label` + `focus.until_label` ("until Mar 2028"),
then `focus.do` and `focus.avoid` as two short lines. If `background` is non-null, show it as a
second, quieter block below. Use the same soft palette as `status`.

### 4. Compass + objects (expandable, collapsed by default)
- **Compass**: an 8-segment ring/grid in clockwise order from `zones[]`. Each segment shows `label`
  and is tinted by `status` (strong = brand accent, steady = neutral, needs_care = soft amber).
  Tapping a segment expands its detail below: `status_label`, `governs`, `care_note` (if present),
  "Good here": `place_here`, "Keep out": `keep_out`. Hide a sub-list that is empty.
- **Objects**: a list titled by the string below; each row = `label`, expands to show
  "Best in": `for_you.best` (if non-empty, else `best`), "Avoid in": `avoid`, `note`, and
  `for_you.tip` if non-empty. If `contested` is `true`, show a small "Traditions differ" tag
  next to the label (the `note` already explains how).
  Do **not** reorder or filter rows; render in the order given.

### Footer
`disclaimer` in small muted text. Nothing else.

## Strings
Only the *structural* labels below live in the front end (add to the i18n files for
en / es / pt / hi / hinglish). Everything else comes translated from the API.
- "Your directions", "Sleep: head toward", "Work: face", "Eat: face"
- "Right now", "Good here", "Keep out", "Best in", "Avoid in", "Objects", "Home map"
- "Traditions differ"
Do not translate API fields on the client, and do not hardcode any English fallback for them.

## Tone and design rules (non-negotiable)
- **No fear.** No red, no warning icons, no "bad", "unlucky", "dosha". "Needs a lighter touch" is
  the strongest wording on the card.
- **No planet, house, sign or Sanskrit names anywhere in the UI.** The API never sends them; don't add any.
- **No religious imagery** in the card chrome (no deity icons, no temple/church glyphs). Compass and
  neutral line icons only. The app is faith-neutral.
- Do not add a "Verified" badge or any claim of accuracy. `meta.rules_verified` is for internal use;
  never render it. The `disclaimer` is the only claim the card makes.
- Reuse the Ayurveda card's container, spacing, and type scale so the two sit together.

## States
- `available: false` or request failure → render nothing.
- Loading → the same skeleton as the Ayurveda card.
- Fetch once per chart per session; no polling. Refetch on chart switch and on language change.

## Auth / chart binding
Call with the **active chart's id**, exactly as the Ayurveda and Today cards do. When the user
switches chart, refetch and drop the previous chart's data immediately (no flash of the old chart).

## Acceptance checklist
1. Flag off → no Vastu card, no console error, no layout gap.
2. Flag on, chart with flagged zones → directions, soft-amber "keep light" lines, compass tints.
3. Flag on, chart with nothing flagged and no period → directions + compass only; no empty sections.
4. ⓘ opens on hover and tap, closes on Esc and outside tap, is keyboard focusable.
5. Elephant row shows "Traditions differ"; "Best in" uses `for_you.best` when present.
6. es and hinglish render the API text untouched; only the structural labels come from i18n.
7. No planet/house/Sanskrit words, no red, no religious icons visible anywhere.
