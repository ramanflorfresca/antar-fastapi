# Co-Star Education + Settings → Antar plan

Co-Star's "How does astrology work?" page (costarastrology.com/how-does-astrology-work,
inspected 2026-09-16) and its settings/about ecosystem are a masterclass in *teaching as
trust-building*. This doc: what's good, then Antar's own version — including ready-to-use
explainer copy (original, not Co-Star's) that leans into Antar's real edge: **Vedic + honest**
(we read the season not the date, we time with dashas, and we tell you how sure we are).

---

## 1. What's amazing (the patterns to steal)
- **Progressive-disclosure "101".** 8 numbered concepts, each a serif heading + ONE plain
  line + an expand arrow (→). You can skim the 8 in 20 seconds or go deep. No wall of text.
- **Education inside the product, not a blog.** "How it works", FAQ, a glossary, and "learn
  astrology" sit right in the app's about/settings — so using the app teaches you, which
  makes it feel authoritative and demystified at once.
- **The same restraint as everywhere else.** Monochrome, one serif, huge whitespace, faint
  line-art. The explainer looks like the product, so learning feels native.
- **Plain-language definitions of scary words.** They translate jargon (ascendant, houses,
  aspects, transits, orbs) into one friendly sentence each. Removes the intimidation moat.

**Antar's edge:** Co-Star explains tropical signs + Porphyry houses and stops at "biting
truth." Antar can explain something more trustworthy — sidereal + whole-sign, *dashas*
(real timing), and the honesty layer (confidence, no magnitude claims). That's a better
story, and no competitor tells it.

## 2. Deliverable A — "How Antar reads you" explainer (original copy, ready to use)
Same numbered, one-line-then-expand pattern. 8 cards. This copy is Antar's, written in the
house voice (warm, plain, honest). FE renders it; content can be hardcoded/curated (no LLM).

1. **What Antar actually does** — *The sky was in a specific arrangement the moment you were
   born, and it keeps moving. Antar reads your life in the context of that motion — and is
   honest about how sure each reading is.*
2. **Your birth chart** — *A map of the sky at the exact time and place you were born. Not a
   single "sign" — the whole picture: where every planet sat, and the life areas they light up.*
3. **We read the season, not the date** — *Antar uses the sidereal sky (the constellations as
   they truly sit today), so your chart describes the season of your life, not a horoscope
   pinned to a calendar date.*
4. **Your star (nakshatra)** — *The Moon's exact star at your birth. It colors your instincts
   and how each day's sky lands for you — finer-grained than a sun sign.*
5. **Houses = life areas** — *Your chart is divided into twelve areas — work, home, money,
   relationships, health… A planet "in" an area is where its energy plays out for you.*
6. **Dashas = your chapters** — *Vedic astrology's real superpower: your life runs in timed
   chapters, each ruled by a planet. This is how Antar can talk about WHEN, not just what —
   which season you're in now, and what's coming.*
7. **Transits = the sky today** — *Where the planets are right now, against where they were at
   your birth. This is what makes a day feel different — the moving sky meeting your fixed chart.*
8. **How sure we are** — *A day is only as strong as the agreement between independent
   readings. Antar shows you that conviction honestly — "strong alignment" vs "mixed read" —
   and never claims a size or an amount it can't back up. When we've tested something and it
   didn't hold, we don't ship it.*

Card 8 is the differentiator — put it last as the mic-drop. It ties straight to the shipped
convergence/confidence engine and the validate-first discipline.

## 3. Deliverable B — Settings / About surface (mapped to existing backend)
A polished settings hub that also educates. Sections, with what already exists:
- **You / birth details** — name, date, time, place. Surface the **birth-time confidence**
  state (`exact | approximate | unknown` / `needs_reconfirm`) plainly: "Add your birth time
  for sharper timing" — teaches WHY it matters (dashas/houses need it) without demanding
  rectification (per the owner rule: read the season, don't interrogate). *(Backend: chart
  record already carries this.)*
- **Language** — a simple toggle; **SELECTION WINS** (the user's pick is authoritative).
  *(Backend: `PATCH /api/v1/me/language` fans the choice to every chart — already built.)*
- **Notifications** — daily reading, big-transit heads-up. *(Backend: device_tokens /
  push exist per the mobile work.)*
- **How Antar reads you** — Deliverable A above (the trust page).
- **Glossary** — one-line plain definitions of Antar's own terms (dasha, nakshatra, house,
  transit, lagna, retrograde…). Curated table, localized; reuse the panchang plain-language
  maps already in the codebase where they fit.
- **Privacy & your data** — plain explanation + **delete my data / delete account**, which
  Antar already implements (chart tombstone purge; account delete for Apple 5.1.1(v)). Show
  it proudly — "your data is yours" is part of the same trust story.
- **About** — one honest paragraph: what Antar is, that it's Vedic, that it validates before
  it claims. Short, in-voice.

## 4. Build notes
- **Mostly FE + curated content.** The explainer and glossary are static/curated copy
  (hardcode or a tiny content JSON), localized via the existing i18n (they're fixed strings —
  prefer a curated table over per-request LLM translate, per the localization playbook).
- **No new engine work.** Settings wires endpoints that already exist (language, birth-time
  confidence, notifications, delete). The only "new" thing is content + screens.
- **Design:** adopt Co-Star's restraint — one serif for headings, generous whitespace, thin
  dividers, expand-on-tap — but in Antar's palette/voice. Learning should look like the app.

## 5. Recommendation
Ship **Deliverable A ("How Antar reads you")** first — it's pure content + one screen, it
directly sells Antar's honesty edge, and it's the cheapest high-trust win. Then fold the
settings sections in around it. I can turn either into a screen-by-screen Lovable build brief
(with the full localized glossary + explainer copy) — say which and I'll write it.
