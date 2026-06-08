# Ask Narration Contract — 5-Surface Audit
**Date:** 2026-06-07
**Charts tested:** `de0c6265` (Raman) + `062bc778` (RC)
**Question (Ask):** "how is speculation money flow today"
**Base:** https://antar-fastapi-production.up.railway.app

The 4 contract rules, abbreviated:
1. **VERDICT FIRST** — sentence 1 is the answer (or honest "reflective read")
2. **2–3 NAMED NOUNS** — concrete life-nouns from activated houses, not energy/domain words
3. **WINDOW** — specific date/range
4. **CONCRETE NEXT STEP** — real action tied to nouns, no trailing question

Plus the **generic test:** two charts on the same question must not produce substantially the same read.
Plus **project rule #12:** zero Sanskrit / planet / house-number / sign / "rising" in user-facing prose.

---

## Gap matrix

| Surface | R1 Verdict | R2 Named Nouns | R3 Window | R4 Concrete Step | Jargon Clean? | Generic test |
|---|---|---|---|---|---|---|
| **Ask /explore** | ⚠ borderline | ❌ **FAIL** | ❌ **FAIL** | ❌ **FAIL** (trailing question) | ✅ clean | ❌ **FAIL — identical openings on both charts** |
| **Today /home** | ✅ (gist) | ⚠ split — gist abstract, lkRead concrete | ✅ | ⚠ `do` vague, `lkRead.do` concrete | ❌ Kemadruma (3×), "Saturn cycle", mahadasha/antardasha | n/a (date-keyed) |
| **Month /monthly-deepdive** | ✅ | ✅ rich | ✅ | ⚠ mantra-only, no single action | ✅ prose clean | (different but both concrete — pass) |
| **Year /annual-plan** | ⚠ theme-first | ❌ **FAIL** (vitality/systems/foundations) | ✅ (peak_windows) | ❌ lists not action | ❌ "Capricorn rising" (chart 2) | reads share infrastructure-prosperity vibe |
| **Cycle /life-arc** | ⚠ archetype label only | ⚠ has nouns but **drowning in jargon** | ✅ | ✅ `preparation_advice` | ❌ **30 leaks** (Saturn/Mars/Rahu/Ketu, "3rd house", "sub-chapter", "micro-phase") | (chart 2 still generating — cache miss) |

Legend: ✅ pass · ⚠ partial · ❌ fail

---

## Evidence (the actual opening sentences)

### Ask — **FAILS the generic test (cardinal sin)**

Chart 1 (Raman): *"This is a reflection on the dynamic, not a timing prediction. Your speculation runway shows moderate structural support — you have some capital deployment capacity…"*

Chart 2 (RC): *"This is a reflection on the dynamic, not a timing prediction. Your speculation runway is under pressure — the blueprint shows structural weakness in how you deploy capital…"*

**Identical scaffolding.** Both: "reflection on the dynamic" → "speculation runway" → "structural" → "capital." Zero life-nouns. Both end on trailing question.

What the contract demands (worked example):
> "Money flow favors you today — especially hidden or higher-risk gains, and a senior or authority figure may back you. One catch: a document or deal detail can trip you up… Best window: late morning. Move: close the review on that contract before midday, not after."

### Today /home

- `gist` (chart 1): *"Good for thinking, not for pushing. One area is under pressure."* → verdict-first ✅, but the nouns are "thinking/pushing" (banned-class).
- `cause.text`: *"Your discipline and patience is moving through a slower phase around your rest and letting go today."* → energy-translation, no life-nouns.
- `lkRead.do` (the rich layer): *"Tell one person, plainly: 'I'm having a hard day…'. Eat warm food. Take a hot bath. Sleep early. Limit social media…"* → THIS is the contract done right (named actions, named nouns).
- **Jargon leaks:** `cycleName: "Saturn cycle"`, `phase.mahadasha.planet: "Saturn"`, `phase.antardasha.planet: "Rahu"`, and "Kemadruma" appears verbatim 3× in lkRead prose.

### Month /monthly-deepdive — **the reference implementation**

`overview` (chart 1): *"Raman, this month puts your partner, joint money, and your daily health routine front and center… your love and partnership energy and your identity and authority energy… But there's tension around shared resources, property matters with your mother, and communication breakdowns…"*

Nouns named: partner · joint money · daily health routine · career visibility · income · shared resources · property matters with your mother · communication breakdowns. **Eight concrete nouns in two sentences.** This is what the rest must look like.

### Year /annual-plan

Chart 1: *"JS, this year is about refining what you've built and protecting your vitality."* Two bugs in one line:
1. Wrong name — **chart belongs to Raman, gets addressed as "JS"** (name-resolution bug).
2. "vitality" / "systems" / "foundations" / "infrastructure" — entire summary is the banned-energy class.

Chart 2: *"…your Capricorn rising's natural discipline meets opportunities for methodical advancement… laying brick by brick the infrastructure…"* — leaks "Capricorn rising" (rule #12) and uses identical "infrastructure" abstraction.

### Cycle /life-arc — **worst contract + worst jargon**

`diagnostic.what_to_avoid[0]`: *"Forcing major public launches…—Saturn's pressure on your 3rd house makes these uphill battles"* → planet + house-number.
`diagnostic.next_phase_shift.label`: *"Saturn major / Rahu sub-chapter begins"* → raw chapter labels.
`diagnostic.current_stuckness_sources[1].source`: *"Saturn in 3rd house from Moon transit"* → full jargon stack.

30 prose-jargon leaks counted in the life-arc payload alone. Per memory `project_house_noun_template_from_cycle`, life-arc was supposed to be the **reference** for house→noun translation. The structure is there (dated shift, sources, next-step), but the **noun layer is missing on top of the planet names** — they leak through.

---

## Ranked fix list (next sprint)

### P0 — contract + rule-#12 hard violations
1. **Life-arc strip layer.** 30 prose leaks. Either route diagnostic prose through `output_strips.apply_user_facing_strips` with `field_type='plain'`, or rewrite the upstream narrator to emit house→noun translations (per `project_house_noun_template_from_cycle`, the structure is already there). The user-facing prose must never read "Saturn / Rahu sub-chapter."
2. **/ask generic-test failure.** Identical scaffolding across charts. Verdict-bypass for "no event recipe" cases is being filled by a hardcoded "reflection on the dynamic / speculation runway / structural" stencil. Replace with: when no event recipe fires, narrator must still pull 2–3 nouns from the chart's activated houses for the question's domain (money → 2/11 nouns; relocation → 4/places nouns) and end with a real next-step, not a self-reflection prompt.
3. **/ask trailing question.** Per contract: "ends the read. No trailing question." `next` is currently always a reflective question. Either drop `next` or make it a concrete action.
4. **/annual-plan name leak.** "JS" instead of "Raman" on chart 1. Name resolution is reaching the wrong column (likely `name` vs `first_name` vs onboarding stem).
5. **/annual-plan "Capricorn rising" leak.** Rule #12 violation — strip sign + "rising"/"ascendant" from year prose.
6. **/home `cycleName: "Saturn cycle"`.** Frontend-facing label. Route through energy translation (e.g. "your discipline cycle").

### P1 — contract weakness
7. **/home today gist.** Verdict-first works; nouns don't. Pull 2–3 nouns from the day's activated houses into the gist, not just `lkRead`. Today.do should mirror `lkRead.do`'s concreteness.
8. **/annual-plan summary.** Strip the banned-energy lexicon (vitality / systems / foundations / infrastructure) and replace with named nouns from the year's peak_windows (e.g. "May/June: a career conversation with a senior figure" not "career momentum builds in distinct waves").
9. **/ask `next` redesign.** Standardize as one concrete action tied to a noun named in the read. No "Ask yourself…" anywhere.

### P2 — gate infrastructure (the contract enforcement)
10. **Build `antar_engine/narration_contract.py`** with: `assert_verdict_first()`, `count_concrete_nouns(read, evidence_houses)`, `has_window()`, `has_concrete_action()`, plus the banned-energy lexicon and the house→noun map. Wire it as a hard gate on the 5 surfaces — non-conforming output gets re-prompted or falls back to a template.

---

## Pass/fail summary

| Surface | Contract grade | Rule-12 grade |
|---|---|---|
| Ask | **F** (fails 3 of 4 + generic test) | A |
| Today | C (mixed) | C (Kemadruma + cycleName leaks) |
| Month | B+ (reference) | A |
| Year | D (no nouns + name bug) | D (Capricorn rising) |
| Cycle | C structurally / F on jargon | F (30 leaks) |

The cure for "all predictions are generic" is the **same fix repeated 5 times**: pull domain-activated nouns from the evidence block, name them in sentence 1–3, ground them in a window, end with one action. Month already does it — copy that pattern.

---

## Gaps in this audit (for follow-up)

- /life-arc chart 2 returned `{status:"generating", retry_after_ms:3000}` (cache miss). Re-run after warm-up to confirm the 30-leak count holds on a second chart.
- Generic-test only run on /ask with one question. Should be extended to today/month/year on a date that produces different transit signatures across 2 charts (less critical — these are date-keyed not question-keyed, so duplication risk is lower).
- Contract rule R4 ("one concrete next step") was scored softly on `do` fields. A stricter pass would require an imperative verb + named object in the SAME sentence.
