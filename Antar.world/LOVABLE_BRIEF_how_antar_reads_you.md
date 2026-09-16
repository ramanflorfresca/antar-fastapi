# Lovable Brief — "How Antar reads you" explainer

A Co-Star-style progressive-disclosure "101" that teaches what Antar does and, crucially,
sells Antar's honesty edge. **Pure FE + curated content — no backend, no LLM.** The copy is
final and original (below); the only work is the screen + wiring it into settings/about.

---

## Where it lives
- A standalone page reachable from **Settings / About** ("How Antar reads you") AND from a
  small "How does this work?" link on the Today card and the Chart screen.
- Its own route (e.g. `/how-it-works`).

## Screen — one page, 8 stacked cards
Match Co-Star's restraint: serif headings, generous whitespace, thin dividers between cards,
faint background line-art if it fits the theme. Each card:
- a small **number** (1–8),
- a **serif heading**,
- **one plain line** always visible,
- an **expand affordance** (→ / tap) that reveals the "more" paragraph.
Default state: all collapsed (skimmable in ~20s); tap any card to expand. Optional "expand
all". No images required.

## The content (FINAL copy — use verbatim; this is Antar's, not Co-Star's)

**1 — What Antar actually does**
Line: *The sky was in a specific arrangement the moment you were born, and it keeps moving.*
More: *Antar reads your life in the context of that motion — and, unlike a horoscope, it's
honest about how sure each reading is.*

**2 — Your birth chart**
Line: *A map of the sky at the exact time and place you were born.*
More: *Not a single "sign" — the whole picture: where every planet sat, and the life areas
they light up for you.*

**3 — We read the season, not the date**
Line: *Antar uses the real, current sky (sidereal), not a fixed calendar.*
More: *So your chart describes the season of your life you're actually in — not a daily
horoscope pinned to your birth date.*

**4 — Your star (nakshatra)**
Line: *The exact star the Moon sat in when you were born.*
More: *It colors your instincts and how each day's sky lands for you — much finer-grained
than a sun sign.*

**5 — Houses = your life areas**
Line: *Your chart is divided into twelve areas — work, home, money, love, health…*
More: *A planet "in" an area is simply where its energy tends to play out in your life.*

**6 — Dashas = your chapters**
Line: *Your life runs in timed chapters, each ruled by a planet.*
More: *This is Vedic astrology's real superpower and how Antar can talk about WHEN, not just
what — which season you're in now, and what's coming.*

**7 — Transits = the sky today**
Line: *Where the planets are right now, meeting where they were at your birth.*
More: *That meeting is what makes one day feel different from the next — the moving sky
against your fixed chart.*

**8 — How sure we are**
Line: *A day is only as strong as the agreement between independent readings.*
More: *Antar shows you that conviction honestly — "strong alignment" vs "mixed read" — and
never claims a size or an amount it can't back up. When we test something and it doesn't
hold, we don't ship it.*

> Card 8 is the differentiator and the emotional close — keep it last. It's the plain-English
> face of the shipped convergence/confidence engine + the validate-first discipline.

## Localization
- These are FIXED strings — **curate es/pt (and fr) translations in a table, do NOT
  LLM-translate per request** (per the localization playbook: curated tables for fixed UI
  copy — no latency/cost/drift). Store as `{en,es,pt,fr}` per line/more, or in the existing
  i18n string files.
- Keep numbers and the Sanskrit terms (nakshatra, dasha) as proper nouns; translate the
  surrounding prose.

## Design / voice rules
- Warm, plain, honest — Antar's voice, NOT Co-Star's snark. No jargon left unexplained.
- Adopt Co-Star's *restraint* (mono/serif, whitespace, thin dividers, expand-on-tap) in
  Antar's own palette. Learning should look like the rest of the app.
- No planet-glyph dump, no wall of text; the one-liners carry it, the "more" rewards a tap.

## Why
It's the cheapest high-trust win: it demystifies astrology for skeptics, teaches the words
users see elsewhere in the app (dasha, nakshatra, houses), and — uniquely — makes Antar's
honesty (confidence, no fake magnitude) a visible feature. No competitor tells this story.
