# Astrocartography — Deep-Dive & Redesign
*How to use it properly, and how to make it simple, smarter, accurate.*
2026-07-29

---

## DECISIONS LOCKED (2026-07-29)

1. **Goals = the Ask domains + peace/family/spiritual** (not the ad-hoc 7). One source of truth with the engines already built.
2. **Relocation chart = PRIMARY score; ACG lines = confirmer** (not 50/50). This is the "true" astrocartography.
3. **Candidate strategy = BOTH.** (a) Recommend the best places from the 996-city set for the goal; (b) if the user *names* a city, score THAT city and give its positives **and** negatives for the goal.
4. **Reuse the domain engines** (career/wealth/relationship/health/legal) evaluated on the *relocated* chart → a place's verdict is consistent with its Ask answer. *(Assumed yes — flag if not.)*

### Goal → houses / karakas (aligned to the Ask engines)

| Goal | Houses | Karakas / engine to reuse |
|---|---|---|
| Wealth / money | 2, 11 (+5, 9 fortune) | Jupiter, Venus · income/funding engine |
| Career | 10 (+6 for job) | Sun/Saturn/Mercury · D-10 career engine |
| Love / relationship | 7 (+5) | Venus, Darakaraka · D-9 · relationship engine |
| Health | 1, 6 (avoid 8/12 on angles) | lagna lord, Sun/Moon · health engine |
| Legal | 6 (+11 win), avoid 7/8/12 | Saturn, Jupiter (protection) · legal engine |
| Peace / home | 4 (+12 rest) | Moon, Venus |
| Family | 2, 4 (+9) | Jupiter, Moon |
| Spiritual | 9, 12 (+5) | Ketu, Jupiter |
| Business | 7, 10, 11 | Mercury, Rahu |

---

## Bottom line

You don't have a *missing-capability* problem — you have a **three-generations-of-code + unfiltered-output** problem. The pieces you want (Vedic relocation chart, goal-driven city ranking, a capped list) already exist in the live `places_*` engine. The "too many options per region" feeling comes from three specific, fixable sources — not from the concept.

The fix is a **methodology decision** ("what is the authoritative reading?") plus **four deletions/caps**. No big new build.

---

## 1. What astrocartography actually is (the 2–3 methods)

| Method | What it does | In our code? |
|---|---|---|
| **A. Relocation chart** *(your "true" method)* | Keep the birth moment — planet signs & dashas unchanged — but **recompute the Ascendant + house cusps for the new lat/long**, so planets shift houses. Re-read the whole chart from the relocated lagna. *One coherent chart per place.* | ✅ `places_relocation.compute_relocated_chart` (Lahiri, whole-sign house rotation) |
| **B. ACG planetary lines** *(the map)* | Per planet, 4 great-circle lines (rising/AC · setting/DC · culminating/MC · nadir/IC). Standing near a line "activates" that planet in that mode. | ✅ `places_lines.compute_all_lines` → **36 lines** (9 planets × 4 angles) + **parans** (line-crossing latitude bands) |
| **C. Local space / directional** | Compass-vector directions from the birthplace (travel *this way* for *this* planet). | ❌ absent |

**Key truth:** A and B answer *different questions*.
- **B (lines) says WHERE on the globe an energy concentrates** — good for scanning, but it's inherently ~36 lines × every region → visual overload.
- **A (relocation chart) says HOW a specific place re-shapes your whole chart** — coherent, holistic, one answer per place. This is the arbiter.

They are **not competitors** — B narrows the globe to candidates, A judges each candidate. That ordering is the whole design.

---

## 2. Where "too many options per region" actually comes from

Three distinct sources (all cited from the live code):

1. **The map dump.** `GET /api/v1/places/lines/{chart_id}` returns **all 36 lines + up to 60 parans unconditionally** (`main.py:11946`, `compute_parans(max_results=60)`) — up to **96 drawable objects, no goal filter**. This is the densest overload.
2. **A second, parallel "where to live" brain.** The **legacy recommender** (`astrocartography_recommender.py:148-165`) is *still wired into the predict flow* (`main.py:4904`) — a per-city × per-planet × per-line loop with stacked ×1.2–1.5 multipliers over **every** city. It produces a different answer than `places_*` and bypasses all the good scoring. Pure noise.
3. **Per-card density (not city count).** The live ranked list is *already* capped and de-clustered — **5–8 cities**, `_MAX_PER_LINE=2`, `_MAX_PER_COUNTRY=2`, `POPULATION_FLOOR=500k` (`places_concern.py:100-108, 427`). What overwhelms is **each card**: `signature` + `primary_reason` + multi-layer `reasons[]` (NATAL/DASHA/AGE/INTENT/WATCH) + `secondary_reasons` + `watch` + `watch_outs` + `lk_relocation_findings[]` (`main.py:11862-11889`).

So: the *list* isn't too long — the **map is unfiltered**, a **duplicate legacy engine runs in parallel**, and **each card says too much**.

Plus two consistency bugs:
- **Two city tables** — `astrocarto_cities.py` (171, legacy) vs `places_cities.json` (996, live).
- **Two scorers that can disagree** — `/places/city` returns `score_city_for_concern` (concern) OR `balanced_score` (fallback), and can show a **different tier** than the list for the same city (`main.py:12082-12100`, already logged as a mismatch).

---

## 3. The methodology decision (the important part)

**Make the RELOCATION CHART the authority; make LINES the candidate-finder; make PARANS a tertiary flavour. Always start from a GOAL.**

Concretely, the answer to "where should I live / would X place work for me?" is produced in this order:

**Step 0 — Goal.** One pick: *wealth · career · love · health · peace · family · business.* This alone selects the 3–4 relevant planets/houses and **discards the other ~32 lines.** (`CONCERN_MAP` already defines karakas/angles/houses/neg-houses/weights per goal — reuse it.)

**Step 1 — Candidate set (lines narrow the globe).** Don't scan 996 cities blindly. Take the user's actual options *or* the cities near the goal's **benefic** lines (Jupiter/Venus/Sun/Moon for the goal) and away from **malefic** lines (Saturn/Mars/Rahu/Ketu). This is the only place lines drive selection.

**Step 2 — Relocation-chart judgement (the arbiter).** For each candidate, **recompute the chart** and score how the goal's houses/karakas land there — *reusing the domain engines we just built*:
- wealth → 2nd/11th lords + Jupiter/Venus, angular
- career → 10th + the D-10 reading, angular Sun/Saturn
- love → 7th + Venus/Darakaraka + D-9
- health → 1st/lagna-lord strong, malefics *out* of 1/8 (Harṣa in 6th is fine)
- peace → 4th + Moon unafflicted, benefics on angles
Malefics landing on the relocated 1/4/7/10 (angles) or the goal's karaka = **veto**, not a footnote.

**Step 3 — Rank & cut.** Nearest-to-goal, highest relocation score, capped at **3 places**. One verdict + one reason + one trade-off each.

Why this ordering is "accurate": the relocation chart is the only view that integrates *your whole chart* with the place. Lines alone tell you a planet is angular there but not whether that helps *your* goal given *your* dignities, dashas, and yogas. Using lines as the map and the relocation chart as the judge is exactly the "smart" combination.

---

## 4. The simplification plan (prioritised, mostly deletions)

**P0 — Kill the duplicate brain.** Remove the legacy `recommend_cities` call from the predict flow (`main.py:4904`); route every "where" question through `places_concern`. *One answer path.* (Biggest single win, lowest risk.)

**P1 — Goal-filter the map.** `/places/lines` should return **only the goal's lines** (it already computes `filter_concern_lines` for `/places/concern`'s `map_lines` — apply the same to the map endpoint) and **cap parans to ~6** (or hide until zoom). 96 objects → ~8.

**P2 — Thin the card.** Per place, show exactly: **Place · one verdict chip (Great/Good/Mixed/Avoid *for this goal*) · one plain sentence why · one trade-off.** Move the multi-layer reasons/LK-findings behind a "why" expander. (All backend fields already exist — this is a render/verbosity change, per `LOVABLE_BRIEF_places_what_its_good_for.md`.)

**P3 — Elevate the relocation chart in the score.** Today `score_city_for_concern` is line-proximity-weighted with relocated-house support as a *secondary* term (`places_concern.py:196-417`). Flip the emphasis so the **relocated-chart goal-fit is primary** and line-proximity is the confirmer — matching the methodology above and your "true astrocartography" intent.

**P4 — Consolidate.** One city table (`places_cities.json`, 996, has a `rankable` flag), one scorer (`score_city_for_concern` everywhere, kill `balanced_score` divergence), delete the dead generations (`astrocartography.py` v1 + 6 `.bak` files, `astrocartography_v2.py`, `astrocarto_cities.py`, the 410'd routes).

---

## 5. The UX (simple / smart / accurate)

**One screen, three questions max, three answers max.**

1. **"What would you improve by moving?"** → goal chip. *(No line jargon, ever.)*
2. **"Anywhere you're considering?"** *(optional)* → if given, judge those; if blank, recommend.
3. **Result: ≤3 place cards.** Each: **City, Country · one verdict for the goal · one sentence why · one trade-off.** A muted "current home vs here" delta. A single "See the chart behind this" expander for the curious.

Map: optional, **goal-filtered only** (2–4 lines), never the 36-line spaghetti by default.

The felt experience: *"For wealth, Singapore and Dubai lift your money houses; Dubai also sits on your Jupiter line — strongest. London would put Saturn on your ascendant — avoid for this."* Three sentences, not forty lines.

---

## 6. What to reuse vs delete

**Reuse (it's good and genuinely Vedic — Lahiri sidereal, whole-sign):**
- `places_relocation.compute_relocated_chart` — the arbiter.
- `places_lines.compute_all_lines` + `filter_concern_lines` — candidate-finder / map.
- `places_concern.CONCERN_MAP`, tiers (55/35), de-clustering, population floor — the ranking spine.
- The domain engines we just shipped (career/wealth/relationship/health) — plug them into Step 2.

**Delete / retire:**
- Legacy recommender path in predict (`main.py:4904`) and `astrocartography_recommender.py`.
- `astrocartography.py` (v1, ASC lines are stubs anyway) + its 6 `.bak/.bak2-5` files.
- `astrocartography_v2.py` and the 410'd routes.
- `astrocarto_cities.py` (171-city legacy table).

---

## 7. Open questions for you

1. **Goal list** — is `money/career/love/health/peace/family/business` the right 7, or do you want it mapped to the Ask domains we built (add *legal*, *spiritual*)?
2. **Relocation vs line weighting** — you called the relocation chart the "true" one. Confirm we make it the *primary* score (P3) and lines the confirmer, not 50/50.
3. **Candidate strategy** — recommend from the 996-city set, or lean on "places the user is actually considering" (typed in)? The former needs the P1 line-filter to avoid globe-scan; the latter is simpler and more accurate per person.
4. **Do you want the relocation chart itself to reuse the new domain engines** (career/wealth/relationship/health evaluated on the relocated chart), so a place's verdict is consistent with the Ask answers? *(I'd strongly recommend yes — one source of truth.)*
