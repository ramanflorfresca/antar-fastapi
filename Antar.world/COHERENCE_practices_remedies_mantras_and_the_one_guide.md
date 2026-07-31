# Practices · Remedies · Mantras — accuracy audit + the "one intelligent guide" vision
2026-07-31

---

## PART 1 — Are practices, remedies, and mantras accurate & consistent?

### Verdict
**Partly.** Practice + mantra + the practice-card's own remedy text are **already coherent** — they all read ONE `primary_planet` (`_select_primary_planet` ← `_score_planet_convergence`, `practice_engine.py:922/1044`), the planet the most timing systems currently point to (dasha lord, karaka, varshphal, **sleeping planet**, etc.). That part is right.

**But the user-facing REMEDIES, the GEMSTONE, the LK-annual remedies, and the Ask-flow practices are four MORE independent planet-pickers** — none of them read that primary planet. So for the same chart, the practices screen can say "focus on planet A" while the remedies screen prescribes for planet B.

### The five selection paths (each can name a different planet)
| Output | Selector | Drives off | Polarity |
|---|---|---|---|
| Practice + mantra | `_select_primary_planet` (`practice_engine.py:1044`) | chart convergence (afflicted/active/sleeping) | pacify |
| **Remedies (screen/PDF/predict)** | `remedy_selector.select_remedies` (`remedy_selector.py:234`) | **question keywords → domain planets** | pacify |
| Gemstone | `select_chart_gemstone` (`practice_engine.py:850`) | **strong benefic** (yogakaraka/lagna-lord) | **strengthen (opposite!)** |
| LK-annual remedies | `lk_varshphal_year` (`main.py:25818`) | annual chart | mixed |
| Ask practices | `relevant_planets` from `build_convergence_timing` (`main.py:18184`) | domain lock/lord/karaka | pacify |

**Where a mismatch actually reaches the user:** `/predict` fuses remedy_selector (`main.py:5626`) + practice engine (`main.py:6573`) into one answer; the **PDF life report** bundles both; the **practices schedule** co-locates practice/mantra with the (benefic) gemstone. There is **no cross-engine consistency check** anywhere.

### The important nuance (don't "fix" this wrong)
The gemstone being a *benefic* while the mantra targets the *afflicted* planet is **not a bug** — classical Vedic remedy legitimately does BOTH: **strengthen** your natural strength (gemstone for a benefic) AND **pacify** what's testing you (mantra/donation for the afflicted). The bug is that we present them as if they're the same "your planet," with no labels — so they read as contradictory. The real incoherence is **remedy_selector naming a different *afflicted* planet than the practice/mantra's afflicted planet.**

### The fix — one FOCUS, two clearly-labelled tracks
1. **One "focus planet" = the convergence primary, as the single source of truth for all PACIFICATION.** Route `remedy_selector` and the Ask-flow practices through `_select_primary_planet`'s convergence map. The question/domain keyword becomes a **tie-breaker**, not the driver. (Convergence is already tier-1 inside remedy_selector — make it authoritative, not one of four tiers.)
2. **Present TWO tracks, each labelled in plain life-language (no planet names):**
   - **"Calm what's testing you now"** → mantra + donation + fasting + practice — all for the *focus* planet.
   - **"Amplify your natural strength"** → gemstone + the benefic's supportive practice — for the yogakaraka/lagna-lord.
   Complementary, not contradictory — once the user sees *why* there are two.
3. **One consistency assertion before surfacing:** `practice.planet == mantra.planet == pacify_remedy.planet`; log + fall back to the focus planet on mismatch. (Today there's zero such check.)
4. **Merge the three static planet→content tables** (`practice_engine.MANTRAS/REMEDIES/AWAKENING`, `remedy_engine.PLANET_REMEDIES`, offline `generate_mantras.py`) into one source so the mantra/gemstone/charity for a planet are identical everywhere.
5. **One shared fallback** (today: practice→Jupiter, remedy→domain logic, gemstone→None diverge silently).

**Net:** ~1 real accuracy bug (remedy vs practice can target different afflicted planets) + 1 presentation bug (two legit tracks shown as one, unlabelled). Both fixable by routing pacification through the existing `primary_planet` and labelling the two tracks.

---

## PART 2 — Making Antar a simple, smart, intelligent astrologer & life coach

### What's already true (the moat)
Deterministic engines do the astrology; the LLM only narrates in plain life-language. Career, relationships, legal, health, residence, wealth each read the real chart (D-1/D-9/D-10 + dashas + Chara + LK varshphal) and converge multiple systems on real dates. That is a genuine astrologer. The philosophy — every answer ends in **agency** (reading → the one thing to do → when it ripens; confidence as a dial, never a dead "no") — is the life coach.

### The one idea that turns 8 features into one guide: **the FOCUS**
At any moment a chart has ONE area/planet most in play (the convergence primary). Make that the spine everything hangs on:
- **Today** names the focus ("this is a stretch where your discipline is being tested").
- **Ask** answers in terms of it.
- **Practices / remedies / mantras** all support that one focus (Part 1).
- **Places** weighs a move for that focus.
One focus, echoed across every surface = the feeling of *one mind that knows you.* That coherence IS the intelligence; scattered-but-correct features feel like a database.

### Five moves
1. **One coherent voice from one chart-truth.** Everything reads the same focus + the same life-facts. (Part 1 is the first proof of this — fix it and the rest follows.)
2. **Simple surface, deep engine.** The user ever sees three things: *where am I now · the one thing to do · what's coming.* Never planets/houses/dashas.
3. **Proactive coach, not a lookup tool.** We already compute forward windows (marriage opening, health-sensitive stretch, career shift, move window). Surface them *ahead of time* with "here's how to be ready" — via Today + notifications — instead of only on request.
4. **Memory of the person.** A coach remembers profession, status, goals, and last week's action. The life-fact gate captures some; deepen it so answers get more personal and the "action this week" builds on the last one.
5. **Focus, not firehose.** Name the one area that needs support now; make practice + remedy + mantra reinforce it; keep everything else one tap away.

### Concrete next steps (prioritised)
- **P0 — unify pacification on the focus planet** (route remedy_selector + Ask practices through `_select_primary_planet`; add the consistency assertion). *Highest trust-per-effort.*
- **P1 — label the two remedy tracks** ("calm what's testing you" vs "amplify your strength") on the practices screen, predict, and PDF.
- **P2 — merge the three planet→content tables** into one.
- **P3 — surface the focus on Today** ("what's in play for you now" + the one action) so the whole app visibly orbits one thing.
- **P4 — proactive windows** — push the nearest converged life-window (marriage/health/career/move) with a "be ready" action.

*This doc pairs with `ASK_confidence_philosophy` (agency dial), the domain engines shipped this session, and the astrocartography deep-dive (same "one engine, plain voice" principle).*
