# Narration Contract — Baseline Scorecard
**Date:** 2026-06-07
**Gate module:** `antar_engine/narration_contract.py` (measurement-only, not wired)
**Runner:** `Antar.world/run_narration_contract_baseline.py`
**Charts:** `de0c6265` (Raman) + `062bc778` (RC)
**Ask question:** "how is speculation money flow today"

---

## Headline

**BASELINE: 0 / 12 surfaces pass the contract.**

This is the measurement we'll improve against. Every surface, on both charts, fails at least one of the 4 rules (R1 verdict / R2 nouns / R3 window / R4 action) or carries a rule-#12 jargon leak. Month carries the strongest noun layer but fails R4 (no imperative action field). Year and Cycle fail on rule #12 and noun-poverty together.

The gate calibrates against the contract's own worked example:

- ✅ "Money flow favors you today — especially hidden or higher-risk gains, and a senior or authority figure may back you …" → **passes**
- ❌ "Today the energy around resources and gains is active; there may be potential for financial movement …" → **fails** (R2 + R4 + energy leaks)

---

## Scorecard

Legend: V = verdict-first · N = concrete-noun count · W = window · A = concrete action · Energy = banned-word hits · Jargon = rule-#12 leak categories

### Chart 1 — Raman (`de0c6265`)

| Surface | V | N | W | A | Energy | Jargon | Pass |
|---|---|---|---|---|---|---|---|
| Ask /explore | ✓ | 1 | ✗ | ✗ | capacity, channel, dynamic, structural… | — | ❌ |
| Today /home gist | ✓ | 0 | ✗ | ✓ | — | — | ❌ |
| Today /home lkRead | ✗ | 0 | ✓ | ✓ | — | **skt** (Kemadruma ×3) | ❌ |
| Month /monthly-deepdive | ✓ | **8** | ✓ | ✗ | support | — | ❌ |
| Year /annual-plan | ✓ | 0 | ✓ | ✗ | systems, vitality | — | ❌ |
| Cycle /life-arc | ✗ | 3 | ✓ | ✓ | — | **planet** (Saturn/Mars/Rahu/Ketu) | ❌ |

### Chart 2 — RC (`062bc778`)

| Surface | V | N | W | A | Energy | Jargon | Pass |
|---|---|---|---|---|---|---|---|
| Ask /explore | ✓ | 2 | ✓ | ✗ | capacity, dynamic, runway… | — | ❌ |
| Today /home gist | ✓ | 0 | ✓ | ✓ | momentum | — | ❌ |
| Today /home lkRead | ✗ | 0 | ✓ | ✓ | — | — | ❌ |
| Month /monthly-deepdive | ✓ | 4 | ✓ | ✗ | breakthroughs, growth | — | ❌ |
| Year /annual-plan | ✗ | 1 | ✓ | ✗ | growth, infrastructure | **sign, skt** (Capricorn rising) | ❌ |
| Cycle /life-arc | ✗ | 0 | ✗ | ✗ | — | — | ❌ (cache miss — re-pull after warm) |

---

## What each surface needs to flip to pass

| Surface | Cheapest path to pass |
|---|---|
| **Ask /explore** | (1) Add a window — every read needs a date/range. (2) Replace the "reflection on the dynamic / speculation runway / capital deployment / structural" stencil with 2–3 nouns from the question's domain houses. (3) Make `next` a concrete imperative action, not "Ask yourself…". |
| **Today /home gist** | Today carries a window + an imperative `do` field — but the gist has zero concrete nouns. Inject 2–3 nouns from the day's activated houses into the gist (today.gist is currently 1 sentence of energy-speak; needs to be 2 sentences with names). |
| **Today /home lkRead** | Strip "Kemadruma" → describe the condition in plain language. Add an explicit window inside lkRead (current ✓ comes from outer `range`). |
| **Month /monthly-deepdive** | Add a single `concrete_action` field — one sentence with an imperative verb tied to a named noun ("Close the review on the contract you've been delaying this week"). The overview already has 4–8 nouns and a window; only R4 is missing. |
| **Year /annual-plan** | Replace "vitality / systems / foundations / infrastructure / growth" with domain-specific nouns from the year's peak windows. Strip "Capricorn rising" leak. Add a concrete next-step. Fix the "JS" name bug (chart 1 only). |
| **Cycle /life-arc** | Route diagnostic prose through `output_strips.apply_user_facing_strips(field_type='plain')` to kill planet/house/sub-chapter leaks. Translate "Saturn major / Rahu sub-chapter" to a chapter-shift label without planet names. The structure is already there; only the noun layer needs to replace the planet layer. |

---

## Step-2 priority (using baseline)

Surfaces ranked by **how many contract axes they fail** (Ask first — failing 4 of 4 axes on chart 1):

1. **Ask** — 3–4 failing axes (R3, R4, partial R2). The "stencil" failure is also the generic-test failure.
2. **Year** — 3 failing axes + rule-#12 leak on chart 2.
3. **Cycle** — 1–4 failing axes + 30 rule-#12 leaks on chart 1 (the worst rule-#12 failure in the codebase).
4. **Today gist** — 1 failing axis (R2) but it's the headline field. Quick win.
5. **Month** — 1 failing axis (R4). Add one field; ship.

Step-2 (your sequencing) tackles 1, 2, 4 (kill generic). Step-3 tackles 3, plus year + today jargon strips. Steps 1–3 will move the baseline from 0/12 toward a target of 10–12/12 on the re-run.

---

## Calibration notes (for the gate)

The gate makes a few principled judgment calls. Documenting so future tweaks don't undo them:

- **"flow" is not hard-banned.** The contract's GOOD example uses "Money flow favors you today" — `flow` is the tail of a concrete noun phrase. The gate flags `flow` only when it stands without a concrete left-modifier (e.g. "good flow today" → ❌; "money flow" → ✅).
- **"energy" carve-out for the rule-#12 translation idiom.** Phrases like "your discipline and patience energy" (the planet-name replacement) do not trip the banned-energy detector — the `[word] and [word] energy` pattern is recognized as the translation layer.
- **Concrete-action requires an imperative verb at sentence-start.** "I act where I'm strong" (mantra) does not count — it's a self-commitment, not a directive. The contract demands a directive.
- **Verdict-first allows two paths:** (a) explicit opener (Yes / Likely / Not yet / "Raman, …" / "Today …") or (b) a directional verb in sentence 1 (favors / supports / blocks / works for …).
- **House-noun match is substring-based on head nouns** ("gains" matches "hidden or higher-risk gains"). Keep entries SHORT to maximize legitimate hits.

---

## Files

- `antar_engine/narration_contract.py` — gate module (pure-Python, no I/O)
- `Antar.world/run_narration_contract_baseline.py` — measurement runner
- `Antar.world/narration_contract_baseline.json` — machine-readable score dump
- `Antar.world/ASK_NARRATION_CONTRACT_AUDIT_2026-06-07.md` — the audit that produced this contract

---

## Step-1 commit (Raman runs `git push`)

```
cd ~/antarai && source venv311/bin/activate
python -c "import ast; ast.parse(open('antar_engine/narration_contract.py').read())"
python Antar.world/run_narration_contract_baseline.py   # confirm 0/12 baseline locally
git add antar_engine/narration_contract.py \
        Antar.world/run_narration_contract_baseline.py \
        Antar.world/ASK_NARRATION_CONTRACT_AUDIT_2026-06-07.md \
        Antar.world/NARRATION_CONTRACT_BASELINE_2026-06-07.md \
        Antar.world/narration_contract_baseline.json
git commit -m "feat: narration_contract gate + baseline scorecard (0/12)"
git push origin main
```

No endpoint changes in this commit. Gate is measurement-only — runs in CI / locally; not wired into any /api route until step 5.
