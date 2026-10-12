# Paste-ready message for Lovable — Places: new place-card lines + cautions

Copy everything below the line into the Lovable chat.

---

**Places screens: render four new backend fields. UI-only: do NOT compute, score, rank, re-order, translate or reword anything on the client. Render the strings exactly as the API returns them.**

The backend for this is live on production (the antar-fastapi API). Nothing changes in how places are scored or ordered; these are extra explanation lines on each place card.

### Where the fields arrive (same three endpoints you already call)

| Endpoint | Where the place objects are |
|---|---|
| `POST /api/v1/places/concern` | `ranked_cities[]` |
| `POST /api/v1/places/potential` | `places[]` and `bigger_move` |
| `POST /api/v1/places/prescribe` | each fix in `within_reach[]` and `bigger_move` |

Every field below is optional: it can be missing, `null`, `[]` or `{}`. **Render nothing for an empty value. No placeholder, no "not available", no layout jump.**

### 1. `varga` — "Deeper check" (array, 0–2 items)

```json
"varga": [ { "varga": "D9", "polarity": "friction"|"supportive", "text": "…" } ]
```
- Only appears for **love** and **career / business**. Empty for everything else, including `overall`.
- `friction` comes first when present.
- Never show the `varga` code (D9/D10), the words navamsa/dashamsa, planet names, or house numbers.
- Label above the lines (localized): **"Deeper check"** / **"Revisión más profunda"**.

### 2. `drishti` — "Influences" (object or null)

```json
"drishti": { "polarity": "supportive"|"testing", "text": "…" }
```
- Only for love, career, business, health, and only when the backend finds an imbalance. Otherwise `null`.
- Shows in the same block as `varga`, directly under it.

### 3. `feel` — "How it tends to feel" (string or null)

- A single plain sentence about the day-to-day feel of the place. Present for every concern.
- Neutral caption, no positive/caution colour. Label (localized): **"How it tends to feel"** / **"Cómo suele sentirse"**.
- Reads last in the block: **deeper check → influences → feel**.

### 4. `watch_outs` — cautions (array of 0–2 strings)

- **Now returned on all three endpoints** (it used to be only `/places/concern`).
- The hard cautions come first, so **the first string is the most important one**. Give it a visibly stronger treatment than the second: the app's existing amber caution style, icon + text (not colour alone). **Never red.**
- Compact list card: show the first one as a single line with a "Watch" marker; show both on the expanded card.
- On `/places/prescribe` fix cards, the first caution must be visible on the card itself. **Do not hide it behind the "lift" / fix-strength badge.** A fix that comes with a caution has to say so.
- **Do not hide, dim, or re-sort a place because it has a caution.** The backend decides ranking.
- Strings may be long. Clamp to 3 lines with "more" on expand; never cut mid-sentence on the expanded card.

### Rules that apply to all four

1. Verbatim. Don't paraphrase, shorten, translate, or add words. The lines are deliberately hedged ("reads as…", "asks for more effort than the line alone suggests"). Turning them into promises is a product violation.
2. None of these fields may change a place's tier badge, score, rank or order.
3. Colour: `supportive` = soft positive marker; `friction` / `testing` / any caution = the existing amber caution marker. Never red, never a warning banner.
4. Don't stack alarms: if `varga` and `drishti` are both cautionary, give the first the caution marker and render the rest as normal-weight text.
5. Never show these words anywhere in the UI: *navamsa, dashamsa, varga, drishti, aspect, nakshatra, D9, D10*, or planet names / house numbers.
6. Spanish returns Spanish strings. Portuguese currently returns **English** strings for these fields. Render them as-is (don't machine-translate, don't break layout).
7. Works on the compact list card and the expanded card on all three screens. On compact lists, `varga`/`drishti`/`feel` can live in the expanded state only.

### Done when

- [ ] Love and career/business places show "Deeper check"; other concerns show nothing extra and no empty gap.
- [ ] `drishti` appears only when non-null, directly under the deeper-check lines; `feel` appears last.
- [ ] First `watch_outs` string is the strongest caution on the card; max two; amber, not red.
- [ ] `/places/potential` and `/places/prescribe` cards show cautions; prescribe shows the first on the fix card.
- [ ] Nothing about a place's rank, tier or badge changed.
- [ ] Missing / `null` / `[]` for any field renders cleanly with no layout jump or console error.
- [ ] None of the forbidden words appear anywhere in the UI.
- [ ] Spanish shows Spanish strings; Portuguese shows English strings without breaking.

If anything here seems to need logic on the client (sorting, scoring, hiding, rewording), stop and ask instead of implementing it. The answer is a backend change.

---

## Notes for Raman (not part of the message)

- Full reference version with sample strings: `Antar.world/LOVABLE_BRIEF_places_varga_and_watchouts.md`. Lovable can't read local files, so the message above is self-contained.
- Publishing from Lovable is your step; Claude's work ends at the backend. After Lovable builds it, check one love chart and one career chart in English and Spanish.
- To see real values first, call `/places/concern` for a test chart (`love`, then `career`) and look at `ranked_cities[0]`.
