# Antar Compatibility Endpoint — API Contract (source of truth)

Powers the COMPAT screen — two-chart compatibility with the Venn-style
alignment diagram + 6-layer breakdown.

Frontend reference: `AntarCompat.jsx`. Both Cowork and Lovable reference THIS.

---

## Endpoints

```
GET  /api/v1/compatibility/charts?chart_id={user_chart}                # list saved partner charts
GET  /api/v1/compatibility/{chart_a}/{chart_b}?relationship={type}&language=en
POST /api/v1/compatibility/charts                                       # add a new partner chart
DELETE /api/v1/compatibility/charts/{id}                                # remove a saved partner chart
```

The verdict endpoint takes two chart IDs and a relationship type; the
relationship gates *which layers of the chart are weighted* (a romantic read
emphasizes Venus and the 7th house; a co-founder read emphasizes the 10th
and Saturn-Mars dynamics; etc).

---

## Relationship types (fixed)

| id | label | sub |
|---|---|---|
| `romantic`  | Romantic Partner | Emotional connection, attraction, long-term potential |
| `business`  | Business Partner | Work style, trust, financial alignment |
| `cofounder` | Co-Founder       | Personality fit, pressure handling, shared vision |
| `friend`    | Friend / Social  | Energy match, communication, mutual growth |
| `family`    | Family           | Parents, children, siblings, family dynamics |
| `employee`  | Employee         | Role fit, work ethic, reliability — **you are the employer evaluating a hire** (requires `role`) |

### Employee role sub-selector

When `relationship=employee`, the request also carries a `role` (sent as
`employee_role` to the session endpoint). Direction is fixed: chart A is the
employer/senior, chart B is the person being evaluated for the role.

| role id | label |
|---|---|
| `sales` | Sales |
| `marketing` | Marketing |
| `product` | Product |
| `leadership` | Leadership |
| `operations` | Operations |
| `engineering` | Engineering |
| `customer_support` | Customer Support |

---

## Response — `GET /api/v1/compatibility/charts?chart_id=...`

Lists the user's saved partner charts for the relationship picker.

```jsonc
{
  "chart_id": "...",
  "saved": [
    { "id": "andres",  "name": "Andres",  "initial": "A",
      "relationship": "cofounder", "born": "Cancer lagna · Colombia" },
    { "id": "harleen", "name": "Harleen", "initial": "H",
      "relationship": "business",  "born": "Operating partner" }
  ]
}
```

## Response — `GET /api/v1/compatibility/{chart_a}/{chart_b}?relationship=cofounder`

```jsonc
{
  "chart_a": "...", "chart_b": "...",
  "relationship": "cofounder",
  "language": "en",
  "generated_at": "...",

  "left":  { "initial": "R", "name": "Raman" },
  "right": { "initial": "A", "name": "Andres" },

  "score": 78,                          // 0..100 — drives Venn-overlap width + glow
  "label": "Strong fit",                // "Locked",  "Strong fit", "Workable", "Friction", etc.
  "headline": "A high-trust co-founder match — your edges complement.",
  "detail": "You bring the engine and the urgency; they bring the steadying hand and emotional intelligence. The combination is naturally complementary for building.",

  // 6 layers — always all 6, ordered as below.
  "layers": [
    {
      "key": "soul",
      "name": "Soul Alignment",
      "passed": true,                   // true → teal, false → amber
      "badge": "Mutual Lock",           // 1-3 word verdict
      "line": "Your deepest drives mutually see each other — a karmic resonance you can feel.",
      "detail": "How to use it: this layer carries you when other layers strain. Lean into shared purpose conversations when friction surfaces elsewhere."
    },
    { "key": "chemistry",   "name": "Working Chemistry",   "passed": true,  "badge": "Strong",        "line": "Day-to-day collaboration flows...", "detail": "..." },
    { "key": "public",      "name": "Public Image",        "passed": true,  "badge": "Power Pair",    "line": "The world reads you as a credible duo...", "detail": "..." },
    { "key": "lifepath",    "name": "Life Path",           "passed": true,  "badge": "Aligned",       "line": "Your dasha periods are running in the same direction for the next several years.", "detail": "..." },
    { "key": "communication","name": "Communication",      "passed": false, "badge": "Asymmetric",    "line": "You move faster than they do. Hold space for processing or it strains.", "detail": "How to work with it: name the pattern before stress hits..." },
    { "key": "friction",    "name": "Friction Points",     "passed": false, "badge": "Watch this",    "line": "When stress hits, you push; they withdraw. Name the pattern early.", "detail": "..." }
  ]
}
```

## Mutations

### `POST /api/v1/compatibility/charts`

Body:
```jsonc
{ "owner_chart_id": "...", "name": "Andres", "birth_date": "1986-07-12", "birth_time": "08:15", "birth_place": "Bogotá, Colombia", "relationship": "cofounder" }
```

Creates a partner chart, returns it in the `saved` shape.

### `DELETE /api/v1/compatibility/charts/{id}`

Removes a saved partner chart.

---

## Field rules

- **`score`** 0..100, drives the Venn overlap width and the glow on the
  center number. Never null.
- **`label`** short verdict — 2-3 words. Suggested set: `"Locked"`,
  `"Strong fit"`, `"Workable"`, `"Friction"`, `"Hard pass"`. Engine picks.
- **`headline`** one sentence summarizing the read.
- **`detail`** one short paragraph elaborating.
- **`layers`** ALWAYS all 6, in order: soul, chemistry, public, lifepath,
  communication, friction. Each has `passed` (true/false), `badge` (1-3
  word verdict), `line` (one sentence), `detail` (one short paragraph
  framed as "how to use it" or "how to work with it").
- **Relationship gates the weighting** — romantic emphasizes Venus/7th,
  cofounder emphasizes 10th/Saturn-Mars, family emphasizes Moon/4th, etc.
  All 6 layers return regardless; weights shift the `score` and which
  layers pass/strain.
- **No Sanskrit/Vedic jargon** in user-facing strings. Internal planetary
  reasoning stays server-side.
- Translate `headline`, `detail`, `badge`, `line`, layer `detail` at
  response time from English source. `label` is a token — translate it too.
- Cache per `(chart_a, chart_b, relationship, language, dasha_boundary)`.
