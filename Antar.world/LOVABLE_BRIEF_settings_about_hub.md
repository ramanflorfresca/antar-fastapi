# Lovable Brief — Settings / About hub (Deliverable B)

A polished settings + about surface that also *teaches* (Co-Star weaves education into
settings). **Almost entirely wiring of endpoints that already exist** + curated content;
no new engine work. Auth note: language/notifications/delete are per-user and need the
**bearer token** — guests get 401, so show a sign-in prompt for those rows.

---

## Screen — a settings list, grouped

### Group 1 — You
- **Birth details** — name, date, time, place. Read from `GET /api/v1/chart/{chart_id}`.
  Surface **`birth_time_accuracy`** (`exact | approximate | unknown`) plainly:
  - if not `exact`: a gentle nudge row → "Add your birth time for sharper timing" (explain
    WHY in one line: dashas + houses need the time). **Do NOT ask life-fact questions or
    rectify** (owner rule: we read the season, not interrogate the date).
  - Edit via **`PATCH /api/v1/me/charts/{chart_id}`** (birth fields incl. `birth_time_accuracy`).
- **Life facts** (optional, if surfaced): `PATCH /api/v1/user/patra`. Keep optional — never gate.

### Group 2 — Preferences
- **Language** — current from `GET /api/v1/me/language`; change via
  **`PATCH /api/v1/me/language`** (fans the choice to every chart). **SELECTION WINS** — the
  user's pick is authoritative; never override it. After change, refetch content in the new lang.
- **Notifications** — `GET /api/v1/me/notifications` returns the toggle shape (each item has a
  localized `label` + enabled state); save via **`PATCH /api/v1/me/notifications`** (send the
  changed toggle). Bearer required.

### Group 3 — Learn
- **How Antar reads you** → the explainer page (build per
  `LOVABLE_BRIEF_how_antar_reads_you.md`).
- **Glossary** → the terms page (curated content below). One-line plain definitions of the
  words users meet elsewhere in the app.

### Group 4 — Privacy & data (show it proudly — it's part of the trust story)
- **Delete this chart** → **`DELETE /api/v1/me/charts/{chart_id}`** (tombstone + PII purge).
- **Delete my account** → **`DELETE /api/v1/account/{chart_id}`** (removes the whole account;
  Apple Guideline 5.1.1(v)).
- **Both are irreversible** → require a strong confirm step (type-to-confirm or a clear modal:
  "This permanently deletes … and can't be undone."). On success, sign out / return to start.
- A one-line "Your data is yours — delete it anytime" note above these reinforces trust.

### Group 5 — About
- One honest paragraph (curated copy): *Antar reads your life through Vedic astrology — the
  real, current sky and your timed chapters (dashas). It's built to be honest: it shows you
  how sure each reading is, and it doesn't claim sizes or amounts it can't back up.*
- App version, links: Privacy Policy, Terms, Contact.

## Curated content — starter Glossary (final copy, Antar voice; localize via curated table)
- **Chart (birth chart)** — a map of the sky at your exact birth moment; the basis of everything.
- **Lagna (ascendant)** — the sign rising on the horizon when you were born; your starting point.
- **Rasi (Moon sign)** — the sign your Moon was in; your emotional baseline (Vedic uses the Moon, not the Sun).
- **Nakshatra (your star)** — the exact lunar mansion of your Moon; a finer layer than a sign.
- **House** — one of twelve life areas (work, home, money, love, health…); where a planet's energy plays out.
- **Dasha** — a timed life chapter ruled by a planet. **Mahadasha** = the long chapter; **antardasha** = the sub-chapter inside it. How Antar times things.
- **Transit (gochar)** — where a planet is right now, versus where it was at your birth; what makes today feel different.
- **Retrograde** — when a planet appears to move backward; a time to revisit rather than start.
- **Yoga** — a specific planetary combination with a known meaning.
- **Panchanga** — the "five limbs" of the day (including tithi + nakshatra); the day's quality.
> Keep Sanskrit terms as proper nouns; translate the surrounding definition. Prefer a curated
> `{en,es,pt,fr}` table over per-request LLM translation (fixed UI copy — no cost/drift).

## Rules
- **Enums stay enums:** `birth_time_accuracy`, language codes, notification keys — switch on
  them, never translate.
- **Auth:** language/notifications/delete need the bearer token; on 401 show a "sign in to
  manage" state, don't error.
- **Design:** Co-Star's restraint — grouped list, serif section headers, generous spacing,
  thin dividers — in Antar's palette/voice. Learning + settings should look like the app.
- **Localize** all labels/copy via the existing i18n (curated tables for the fixed strings).

## Why
Settings is where trust is won or lost: it's where the user controls their data, learns the
words, and sees that Antar is honest and privacy-respecting. Bundling education in (Co-Star's
move) makes the app feel like a guide, not a black box — and every row here wires an endpoint
that already exists.
