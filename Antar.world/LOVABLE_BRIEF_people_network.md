# Lovable Brief — People → a living Network (Track A)

Turn the existing People tab from a compatibility *checker* into a living **Network**:
your people, how each one's day is going, tap-through to their day + your compatibility.
Everything below reuses shipped engines; the ONLY new backend is one read-through digest
endpoint (spec in §1). Add-a-person keeps both paths: **from your network** (someone you
already added) or **manually** (new person by birth details).

---

## 1. NEW backend endpoint (spec) — `GET /api/v1/network/{chart_id}`

One cached call that returns the user's people + each person's *today glance*. Additive;
does not change any existing endpoint.

**Request:** `GET /api/v1/network/{chart_id}?language=en`

**Response:**
```json
{
  "available": true,
  "people": [
    {
      "connection_chart_id": "6ec6311c-…",
      "name": "Andres",
      "relationships": [
        { "session_id": "…", "compat_type": "cofounder", "score": 61, "badge": "FLOW" }
      ],
      "primary": { "session_id": "…", "compat_type": "cofounder", "score": 61, "badge": "FLOW" },
      "today": {
        "available": true,
        "band": "steady",              // steady | light | lighter-touch | friction  (from day_energy)
        "direction": "positive",       // positive | adverse | quiet
        "one_line": "A steady day for them."   // GENERIC, from (band,direction) — never their private reading
      }
    }
  ],
  "count": 1
}
```

**Behaviour / implementation notes (for the backend build):**
- **People source:** query `compatibility_sessions` where `chart_id_a = {chart_id}`
  (`select id, chart_id_b, name_b, compat_type, score, created_at`, order by `created_at`
  desc). **Dedupe by `chart_id_b`** → one person per row; `primary` = most-recent
  relationship, `relationships[]` = all of them (same two people can have multiple reasons).
  (The existing `/compatibility/sessions/{id}` list does NOT return `chart_id_b`, which is
  why the digest reads the table directly.)
- **Today glance:** for each distinct `chart_id_b`, **read the warm cache only** —
  `_daily_surface_get(chart_id_b, "daily-signal", language, <today in that chart's tz>, "")`.
  If present → pull `day_energy.band` + `direction` → map to `one_line` via a fixed
  per-(band,direction) template table (localized es/pt/fr). **Do NOT synchronously compute
  a full daily-signal for cold connections** (N people × several-sec LLM builds = a slow
  endpoint) — a cold person returns `today.available:false`. Optionally fire a
  background prewarm for cold `chart_id_b`s so the *next* load is warm (fire-and-forget).
- **Privacy (important):** `one_line` is a GENERIC phrase derived only from band+direction
  (e.g. "A tender day for them — be gentle."), **never** the person's own narration/headline
  (which can contain private specifics), and the endpoint returns **no birth data** for
  connections — just name + glance + compat scores the owner already generated.
- **Fail-open:** a per-connection error → that person's `today.available:false`; the
  endpoint never 500s on one bad row. `available:false` at top level only if `chart_id`
  itself is bad → FE shows the empty state.
- **Cost:** it's all cache reads (the per-person cards are already cached from the confidence
  rollout), so it's cheap and fannable; safe to call on every Network-tab open.

*(This endpoint is specced, not yet built — say the word and I'll implement + deploy it.)*

---

## 2. Screen 1 — Network list (the People/Network tab landing)

Replace the current "recent checks" list with **"Your people"**.

**Data:** `GET /api/v1/network/{chart_id}?language=` (§1).

**Layout — one row per person:**
- Left: avatar or initial circle.
- Name (`name`) + relationship label (`primary.compat_type` → the localized reason label
  from `/compatibility/reasons`).
- **Today glance:** a small dot + one word from `today.band`
  (steady=calm/green-ish, light=soft, lighter-touch=amber, friction=muted-red-but-gentle),
  and optionally `today.one_line` as a sub-line. If `today.available:false`, show a neutral
  "—" / "checking in…", never an error.
- Right: the compat `primary.score` as a small ring/number + `badge` (FLOW/MIXED/…), so the
  list doubles as an at-a-glance relationship health strip.
- Tap row → Screen 3 (person detail).

**Top of screen:** an **"Add a person"** button → Screen 2.

**Empty state** (`count:0`): a warm prompt — "Add the people who matter and see how your
days line up." + the Add button. (This is the Co-Star "better together" hook.)

**Rules:** send `language` on the call; render `band`/`direction` off the enums (don't
recompute); never show planet names or birth data here.

## 3. Screen 2 — Add a person (two paths)

A chooser, then the relationship picker (the picker already exists from the People-tab brief).

**Path A — From your network** (someone already added):
- Show the list of existing people (reuse §1 `people[]`, or a light "saved people" list).
- Pick one → go straight to the reason picker (their `connection_chart_id` becomes
  `chart_id_b`). No re-entry of birth details.

**Path B — Add manually** (new person):
- Birth details form: name, birth date, time (optional — drives `confidence`), city/country
  (geocode → lat/lng/tz). Same fields the current New-person flow collects.

**Then (both paths) → Relationship picker:**
- `GET /api/v1/compatibility/reasons?language=&chart_id=` → chips: romantic, cofounder,
  business, friend, family, employee, boss-or-manager.
- If the reason has `needs_role:true` (employee/boss) → sub-picker: sales|marketing|finance|managerial.
- Submit → `POST /api/v1/compatibility/start` with `chart_id_a` + (`chart_id_b` for Path A,
  OR birth fields for Path B) + `compat_type` + `role?`. Response = the full result → Screen 3.
- Handle preview/locked (additional people beyond the first): show preview + `POST
  /api/v1/compat/slots/checkout` (one-time unlock, never a subscription wall).

## 4. Screen 3 — Person detail ("how they are" over "how you two work")

Two stacked sections — the heart of the network feel.

**Section 1 — Their today** (top):
- From §1's `today` for this `connection_chart_id` (or refetch a single glance):
  band word + `one_line`. Calm, non-invasive framing. If unavailable, hide this section
  rather than show a placeholder.

**Section 2 — Your compatibility** (the existing result screen, unchanged):
- `GET /api/v1/compatibility/session/{session_id}?language=` (recomposes the full rich
  shape incl. forward-dasha). Render: score ring + `badge`, "A + B · <reason>", `headline`,
  `summary`, **WHERE YOU FLOW** (`catalysts`) / **WHERE THERE'S FRICTION** (`watch_points`).
- **Deeper layers:** `POST /api/v1/compatibility/continue` `{session_id, layer}`.
- **Change relationship:** re-run the reason picker for the same person (Path A) → new/updated
  session.

## 5. Cross-cutting rules
- **i18n:** pass `language` on every call; `band`/`direction`/`compat_type`/`badge` are
  STABLE enums — switch styling on them, never translate them. `one_line`, `headline`,
  `summary`, `catalysts`, `watch_points`, reason labels arrive already localized.
- **Privacy:** the Network never exposes a connection's birth data or their private daily
  reading — only name, a generic day glance, and the compat scores the owner generated.
- **Caching:** the digest is a cheap cache read; safe to call on tab open. Client-cache per
  day is fine.
- **Fail-soft everywhere:** a missing glance or a cold connection shows a neutral state,
  never an error card.

## 6. Why
This is Co-Star's retention loop — "see how your people are doing" — but with Antar's edge:
each person's day is a *real, precise* read from our own daily engine (band + honest
direction), not a sun-sign blurb. The list becomes a reason to open the app daily; the
compat detail is the depth. Same engines you've already validated; one small digest endpoint
makes it one fast call.
