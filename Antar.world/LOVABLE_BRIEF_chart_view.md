# Lovable Brief — The Chart, as an object you own (Track B)

A Co-Star-style "Chart" surface: a clean **wheel** + a plain **"planet in sign (house)" list**
with short reads. **Pure FE** — every field comes from chart endpoints that already exist and
already localize via `?language`. Antar's differentiator: this is a **Vedic sidereal,
whole-sign** chart (house = sign), not Co-Star's tropical circle — lean into that.

---

## Where it lives
- Its own **Chart** screen (tab or from the profile), plus a "See your chart" link on Today
  and in Settings → "How Antar reads you".

## Data sources (all live, all take `?language=`)
- **`GET /api/v1/chart/{chart_id}`** — the geometry. `planets` = {Sun, Moon, Mars, Mercury,
  Jupiter, Venus, Saturn, Rahu, Ketu} each `{sign, house, degree, longitude, nakshatra,
  sign_index, nakshatra_lord}`; `lagna` `{sign, degree, sign_index}`; `moon_sign`, `sun_sign`,
  `current_mahadasha`. (Positions are factual — sign/nakshatra/planet names are proper nouns,
  don't translate.)
- **`GET /api/v1/chart/{chart_id}/overview`** — `archetype` {name, tagline, description,
  strength, blind_spot}, `strengths[]`, `areas_to_mind[]`. → the identity header.
- **`GET /api/v1/chart/{chart_id}/identity`** — `ascendant` {sign, degree, ruled_by},
  `sun`/`moon` {sign, house, nakshatra, house_label}, `current_period` {maha, antar,
  maha_ends, next_maha}, `yogas[]`, `reading`. → key placements + chapter.
- **`GET /api/v1/chart/{chart_id}/signature`** — `planet_signatures[planet]` {mode, sign,
  field, nakshatra} (Antar's own archetype vocab). → the per-planet one-liner.

## Screen layout (top → bottom)

### 1. Identity header — "the shape of you"
- Big: `overview.archetype.name` + `archetype.tagline` (e.g. "THE DISCOVERER — Finds what
  others walk past.").
- A one-line identity strip like Co-Star's "You · ☾ … · ↑ …": from `identity` →
  **Asc {ascendant.sign} · ☉ {sun.sign} · ☾ {moon.sign}** (Vedic leads with Moon + ascendant).
- Optional: `archetype.description` as expandable "more".

### 2. The wheel (SVG, thin line-art)
Whole-sign, so it's **12 equal 30° sectors, one per sign** — geometry:
- Draw an outer ring split into 12 sectors; label each with its **sign** (glyph or name).
- **House 1 = the ascendant's sign** (`lagna.sign_index`); houses run in zodiacal order from
  there. Mark the ascendant (a line/arrow at `lagna` — traditionally the left/9-o'clock).
- **Place each planet** by `sign_index * 30 + degree` (its absolute longitude) around the
  ring, drawn as its glyph; cluster/offset when two share a sign so glyphs don't overlap.
- Keep it monochrome + thin-stroke like Co-Star. **Aspect lines: optional** — Vedic drishti
  differs from Western aspects, so either omit them (cleanest) or draw Vedic aspects later; do
  NOT copy Western aspect geometry.
- If a `retrograde` flag is present on a planet, mark it `℞`; if absent, skip (don't assume).
- Two acceptable styles — pick one: **(a) sidereal circle** (most Co-Star-adjacent, familiar)
  or **(b) North-Indian square** (authentic Vedic diamond, houses fixed). Recommend (a) for
  familiarity; (b) is the traditionalist option.

### 3. Planet rows — "planet in sign (house · nakshatra)"
A scrollable list, one row per graha (this is the Co-Star "planet in sign" list, Vedic-ized):
- **Row title:** `{Planet} in {sign} · {house_label} house` (e.g. "Sun in Taurus · 4th house").
- **Sub-line (nakshatra):** "★ {nakshatra}" (finer than a sign — a nice Vedic touch).
- **One-line read (expand):** from `signature.planet_signatures[planet]` — e.g. a phrase built
  from {mode, field} ("Builds in the field of Discovery"), or the plain significance. Keep it
  one line; tap to expand if you add more.
- Order: luminaries first (Sun, Moon), then Mercury→Saturn, then Rahu/Ketu.

### 4. Your chapter + yogas (optional, high-value)
- **Current chapter:** from `identity.current_period` — "You're in your **{maha}** chapter
  (until {maha_ends}), sub-period {antar}." Ties the static chart to live timing (dashas) —
  the thing Co-Star can't do.
- **Yogas:** `identity.yogas[]` — name + one-line effect, as small cards.

## Rules
- **Proper nouns stay:** planet, sign, nakshatra names + enums (`mode`, `field`) are NOT
  translated; the reading prose (archetype description, strengths, yoga effects, `reading`)
  IS localized — just pass `?language=` (these endpoints run `@translate_response`).
- **Whole-sign is the model:** house = sign; don't compute Placidus/Porphyry cusps. `house`
  and `house_label` are given — use them.
- **Design:** Co-Star restraint — one serif, whitespace, thin-line wheel, expand-on-tap rows,
  monochrome + one accent. In Antar's palette/voice.
- **Fail-soft:** if `signature`/`overview` is unavailable, still render the wheel + factual
  rows from `/chart/{id}` (which is always present).

## Why
The chart is the identity object users return to — Co-Star makes it a recurring motif. Antar's
version is *more*: a real sidereal Vedic wheel, nakshatras (finer than signs), and the current
dasha chapter overlaid — so the chart isn't just "who you are" but "who you are, and the season
you're in." All from endpoints that already exist and already localize.
