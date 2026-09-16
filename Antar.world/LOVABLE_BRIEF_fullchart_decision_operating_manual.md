# Lovable Brief — Full Chart → "Your Decision Operating Manual" (reframe)

Reframe the **Full Chart** page from an *astrology profile* into a **decision operating
manual**. Antar is a decision-**timing** tool, not a horoscope app — this page is currently
the most horoscope-looking surface we have (Sanskrit yogas, generic trait readings). This is
a **layout + copy** change. **All data already comes from the backend** (endpoints below);
do not compute or invent anything on the FE, and do not add new predictive claims.

> Companion urgent fix (do first, separate brief): `LOVABLE_BRIEF_fullchart_saved_people_score.md`
> — remove the numeric compat score from SAVED PEOPLE READINGS.

---

## Principle

Lead with **how the person decides and when to act** — the actionable/timing layer — and
push pure "personality" content down or out. Every line should help a decision: *what you're
good at deciding, the season you're in, what to lean on, what to watch, the one thing to
practice.* No Sanskrit. No numeric scores. No trait horoscopes.

---

## New section order (top → bottom)

### 1. HOW YOU DECIDE  *(lead with this)*
The archetype, **reframed as a decision style** — not "your personality type."
- **Source:** `GET /api/v1/chart/{chart_id}/overview` → `archetype { name, tagline, description }`.
- **Render:** big — `name` (e.g. "The Broker") as the decision-style headline, `tagline`
  ("cuts to the truth in every relationship") as the one-liner, `description` as 1–2 sentences.
- **Framing copy** (static section label): *"How you decide"* / *"Your decision style"*.
  Keep the archetype's own words; just frame them as *how this person moves*, not *who they are*.

### 2. THE CHAPTER YOU'RE IN  *(elevate — this is real decision-support)*
The current life chapter and **when it turns** — the single most decision-relevant fact.
- **Source:** `GET /api/v1/chart/{chart_id}/identity` → `current_period { maha, maha_ends, antar, next_maha }`.
- **Render:** "You're in your **{maha}** chapter" · "Turns **{maha_ends → next_maha}**"
  (e.g. *"Rahu chapter — turns Aug 2044 into Jupiter"*). This is already computed; keep it
  prominent near the top. Use the plain wording the backend sends; don't add planet jargon.
- Optional sub-line: current `antar` as the "sub-season" if you already render it elsewhere.

### 3. WHAT TO LEAN ON / WHAT TO MIND  *(the de-jargoned yogas + strengths)*
Two short lists — assets to lean on, and areas to work with. **Now fully jargon-free from
the backend** (no more "Raj Yoga (Mars-Mercury conjunction)").
- **Source (preferred):** `overview` → `strengths[]` (lean on) and `areas_to_mind[]` (mind).
  Both are already plain, decision-relevant sentences, split for you, and localized (es/pt/fr).
- **Alternative source:** `identity` → `yogas[]`, each now `{ name, effect, strength, kind }`
  where **`kind` = `"strength"` | `"mind"`** — group by `kind` if you render from here.
- **Render:** two labeled groups — **"What to lean on"** and **"What to mind"** — each a tight
  list of `name` + `effect`. No Sanskrit will appear; if you ever see a Sanskrit word, it's a
  backend bug (report it) — do **not** hardcode a FE translation.
- **Drop** the old raw **YOGAS** section header and the standalone "OVERALL STRENGTHS /
  AREAS OF TENSION" blocks — this section replaces all of them.

### 4. THE ONE THING TO PRACTICE  *(keep — tension → practice → streak loop)*
The existing practice + streak loop is genuine decision-support. Keep it, place it here.
- **Source:** `overview` → `enemy_alerts[]` (each has the practice + `progress { streak,
  done_today, completed_count }`).
- **Render:** as today — the practice, "DONE TODAY" state, and the streak. Frame it as
  *"The one thing to practice this season"* so it reads as action, not ritual.

### 5. YOUR PEOPLE  *(SAVED PEOPLE READINGS — band words, no digits)*
- **Source:** `GET /api/v1/network/{chart_id}` → `people[]` (`name`, `primary.badge`, `today`).
- **Render:** name + **band word** (Flows / Mixed / Friction) — **never a numeric score**
  (see the companion urgent brief). Tap-through to the person's day + compatibility unchanged.

---

## De-emphasize / collapse

- **Birth data + "See your chart"**: collapse into a small, secondary "Birth details / chart
  wheel" affordance (a tap-to-expand or a quiet footer link) — it's reference, not the lead.
- **Generic trait paragraphs** (the narrative "you are…" prose that isn't decision-relevant):
  drop, or fold the one useful sentence into §1.
- Anything that reads as a horoscope description with no decision attached: cut it.

---

## Guardrails (non-negotiable)

- **No Sanskrit anywhere.** All labels come from the backend already de-jargoned. Don't add
  a FE glossary or re-expose raw names.
- **No numeric compatibility scores.** Band words only.
- **No new predictive claims** — no "you will…", no magnitude/tier/ranking. Present what the
  backend sends; magnitude claims are falsified and must not be introduced on the FE.
- **Backend owns copy**, FE owns layout. If a string needs changing, it changes in FastAPI so
  es/pt/fr stay in sync — don't hardcode English strings on the FE.
- Pass `?language=` on every call so §1–§3 localize.

## Verify live (antar.world)

1. Hard-refresh with Service Worker + caches cleared; confirm the **bundle hash flips**.
2. Full Chart page reads top-down as: How you decide → The chapter you're in → Lean on / Mind
   → The one practice → Your people. Birth data is secondary.
3. Search the rendered page (and network payloads) for any Sanskrit yoga word or any digit in
   the people rows — there should be **none**.
4. Switch language to es/pt and confirm §1–§3 localize (they're translated server-side).
