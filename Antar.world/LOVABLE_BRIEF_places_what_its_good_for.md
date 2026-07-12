# Lovable brief — Places (astrocartography): show WHAT each city is good for + fix the tier legend

## Why
Two problems on the astrocartography screens:

1. **Cards only showed a score.** It was never clear *what* a city is good for.
   Every place carries a different energy — one is strong for relationships,
   another for structure/discipline, another for drive — and the card never said
   which. The backend now returns that per city as a **`signature`** object.
2. **The legend was wrong and the map read as all-STRAIN.** The scoring was
   recalibrated so FLOW is actually reachable, and the tier cutoffs moved. The
   hardcoded legend in the app (`FLOW ≥ 70`) never matched the backend and is now
   further out of date. It must read **FLOW ≥ 55 · MIXED 35–54 · STRAIN < 35**.

Both backend changes are **live** on `main`. This brief is the app-side render.

---

## Change 1 — render the new `signature` ("what it's good for")

### The data is already there
`POST /api/v1/places/concern` → each item in `ranked_cities[]` now includes a
**`signature`** object (may be `null` — see below):

```json
{
  "rank": 1,
  "city": "Chengdu",
  "country": "China",
  "country_code": "CN",
  "score": 55,
  "tier": "FLOW",
  "signature": {
    "best_for":  "Money through relationships & taste",
    "energy":    "relationships & taste",
    "axis":      "how you show up day to day",
    "from_line": true,
    "line":      "Its edge here: relationships & taste, landing on how you show up day to day — value tends to arrive this way."
  },
  "one_line": "…",
  "primary_reason": "…",
  "reasons": [ { "layer": "NATAL", "text": "…" }, … ],
  "watch": "…"
}
```

Field-by-field:
| field | type | use |
|---|---|---|
| `signature.best_for` | string | **The chip.** Short, e.g. "Money through relationships & taste". Render as a tag next to the score/tier. |
| `signature.energy` | string | The bare energy ("relationships & taste") if you want a shorter chip than `best_for`. |
| `signature.axis` | string \| null | Where it lands ("how you show up day to day"). `null` on the house-fallback case. |
| `signature.from_line` | bool | `true` = a real planetary line runs near the city (strong signal). `false` = background house support only (weaker — style it more muted). |
| `signature.line` | string | One-sentence expansion for the card body / drill-down. |

### What to render
1. **Chip on every city card**: `signature.best_for` as a tag beside the FLOW/MIXED/STRAIN
   badge. This is the headline fix — it's what tells the user what the place is *for*.
2. **Card body / expanded view**: `signature.line` as a short italic/secondary line
   under the headline (before the NATAL/TIMING/AGE reasons).
3. **`from_line: false`** → render the chip in a **muted / secondary** style (and you
   may prefix "Background: " or use a lighter weight). These cities have no strong line;
   the signature is a softer, house-based read.
4. **`signature: null`** → render **no chip** (a genuinely background match with nothing
   specific to name). Don't invent a placeholder; just omit it.

### Copy notes
- The `best_for` / `line` strings are **already user-facing and jargon-free** — render
  verbatim, do **not** post-process, translate, or append planet names.
- They're localized: send `language: "es"` in the request and the strings come back in
  Spanish. Don't build your own translations.
- Same `signature` object is also returned by `POST /api/v1/places/compare` (same shape).

---

## Change 2 — fix the tier legend + cutoffs

The score→tier mapping is now (backend source of truth):

| Tier | Score | Label idea |
|---|---|---|
| **FLOW** | **≥ 55** | "CLEAR" |
| **MIXED** | **35 – 54** | "TRADE-OFFS" |
| **STRAIN** | **< 35** | "PLAN AROUND IT" |

Action: wherever the legend is hardcoded (the screenshot showed
`FLOW (CLEAR) · ≥ 70  /  MIXED · 45–69  /  STRAIN · < 45`), change it to
**`FLOW ≥ 55 · MIXED 35–54 · STRAIN < 35`**.

> Better still: **don't hardcode the numbers.** The backend already sends the
> per-city `tier` string ("FLOW"/"MIXED"/"STRAIN") — colour and label off that,
> and treat the numeric ranges in the legend as descriptive only. Then future
> calibration tweaks won't desync the legend again.

### Expect more colour on the map now
After the recalibration, a chart's genuinely-strong concerns will surface real
**FLOW** (green) cities where before everything was STRAIN (red). This is correct —
e.g. a chart strong in Venus shows FLOW for *love* while *money/career* stay MIXED.
Most of the world still reads STRAIN for any single concern (you only have a few
planetary lines) — that's expected and honest, not a bug.

---

## Out of scope (backend already handles it)
- Jargon-stripping (no planet/house/sign names reach these fields).
- Scoring, ranking, de-clustering, caching — all backend.
- The regional-overview screen ("The world, sorted by what your chart wants"):
  it reads the same `ranked_cities`, so the `signature` chip can be reused there too
  if/when you want it, but that screen isn't required for this fix.
