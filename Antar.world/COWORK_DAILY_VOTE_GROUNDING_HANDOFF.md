# Daily reading — grounded in its own votes (evidence + house-anchored taxonomy + no-invention gate)

**Date:** 2026-07-08 · **Chart verified:** Raman Singh `a4c9d57b` · Capricorn lagna, MD Mars / AD Moon

Goal: close the gap where the narrator invented life-areas (father/network/expense) that were
never computed, and match Yasir Yogi's whole-life coverage + warmth — but computed, not cold-read.
Every beat now traces to a specific vote.

---

## What shipped (code — live on deploy)

| Fix | What | Files |
|---|---|---|
| **0** | Unblock `POST /api/v1/predict/day-deep` (was 500 on a `from __future__` ordering SyntaxError) | `antar_engine/deep_read.py` |
| **A** | First-class `evidence` object on every daily read (`votes/net/mag/chosen/lead_dir/dasha_tone`), admin/dev-visible, not rendered | `today_highlight.py`, `main.py` |
| **B** | Votes now tally **house-anchored life-areas** (father/home/children/partner/siblings/network/expense/…), collapsing to the legacy 5 coarse domains for all existing consumers | `life_areas.py` (new), `today_highlight.py`, `today_narration.py`, `main.py` |
| **B2** | **Source D — the dasha lord** (MD/AD): votes the areas it rules + occupies at a modest weight (decisive only on convergence), carries a plain tone tag as the through-line | `life_areas.py`, `today_highlight.py`, `today_narration.py`, `main.py` |
| **C** | **No-invention gate**: after the LLM writes, reject/regenerate if it names a life-area no source voted for | `today_narration.py`, `main.py` |
| **D.1** | **Top-N coverage**: narrate every area above a floor (cap 5, strongest first), not just top-2 — keeps the honest quiet day | `today_highlight.py` |
| **D.2** | **Warm voice** ("Dear {name}…") walking each computed area, through-line as connective tone, Antar timing as the close | `today_narration.py` (`NARRATION_STATIC` → `_fb_today`) |

**D.2 status — LIVE (2026-07-08):** the warm voice was flipped live by updating the
`llm_prompts` today/en row in place (v1→v2, via `patch_d_prompt_db_flip.py --apply`; the
table's `llm_prompts_one_live` constraint means UPDATE, never INSERT a second live row).
Rollback: restore the old body from `llm_prompts_today_en_v1.<ts>.bak.txt`. Registry live
cache TTL is 60s. `today_narration_cache` is keyed by engine fingerprint (not prompt
version), so pre-existing cold reads linger until they miss — purge that table to force warm
for all (costs a re-narration spike). Still pairs with the Lovable daily-render update so the
multi-beat body renders as intended.

---

## Before / after — Raman, 2026-07-08 (real chart)

### BEFORE — old 5-domain engine (top-2, no dasha)
```
votes:   C:lk_amplify:work:+3.5   C:lk_amplify:money:+3.5   A:moon_house4:relationships:+1.6
chosen:  [money, work]            ("relationships" 1.6 dropped)
read:    "A strong day for money and work."
         Money matters carry tailwind today — chase payments, send invoices…
         Visible effort pays off today — push execution…
```
Two tactical beats. The 4th-house (home/mother) signal was discarded; no father/network;
no chapter through-line; no warmth.

### AFTER — house-anchored votes + Source D + top-N + warm voice
```
votes:   C:lk_amplify:siblings:+3.5   C:lk_amplify:money:+3.5
         A:moon_house4:home:+1.6      D:dasha_mdh4:home:+1.5
         D:dasha_mdh10:work:+1.5      D:dasha_mdh11:network:+1.5
         D:dasha_adh3:siblings:+0.8   D:dasha_adh7:partner:+0.8
net:     siblings 4.3 · money 3.5 · home 3.1 · work 1.5 · network 1.5 · partner 0.8
chosen:  [siblings, money, home, work, network]   through-line: Mars → "forceful and direct"
```

**Every beat maps to a vote:**

| Beat | Grounded by |
|---|---|
| **siblings** — a sibling, a short trip, your own effort | LK `communication` (2nd) + AD Moon occupies 3rd |
| **money** — your savings, money you keep | LK `trade` (2nd) |
| **home** — home, your mother, a vehicle | Moon transiting the 4th today + MD Mars rules the 4th |
| **work** — your boss, a promotion, your reputation | MD Mars occupies the 10th |
| **network** — income, a payout, your friends | MD Mars rules the 11th |

**Warm narration (live sample, gate-passed):**
> Dear Raman, today has a forceful, direct quality — push hard, but don't bulldoze what matters.
> Your sibling or a short trip you've been putting off could move something real forward today;
> your own effort is the engine… Your savings and the money you keep are in a good spot… Home is
> quietly strong too; your mother or something tied to your home or a vehicle could bring
> unexpected support… At work, your boss is likely to notice you… Your network and income are
> also live; a payout, a goal crossing the finish line, or a friend coming through is genuinely
> possible today. The best window to act is between 11:52 am and 12:44 pm… Hold off on locking in
> any big commitments before 9:00 am.

Yogi's whole-life breadth and warmth — but father/mother/network appear **only because a source
voted** for them, and Antar's precise timing is the close he can't match.

---

## Verification (all pass)

1. **House-anchored + Source-D votes, evidence returned** — ✅ (see AFTER votes; `evidence` object present).
2. **Coverage ≥3 areas → ≥3 beats** — ✅ (Raman: 5 beats, previously would truncate to 2).
3. **No-invention gate** — ✅ forcing "father"/"expense" with no 9th/12th vote → rejected → template fallback.
4. **Honest quiet day preserved** — ✅ a no-vote day still returns `direction=quiet`, `chosen=[]`.
5. **Existing tests** — ✅ 27 passed (`test_today_drivers`, `test_house_significations`, `test_month_lk_diagnostic`).

---

## `day-deep` finding (answered)

The richer "Dear Raman" house-level reading runs through a **separate** path
(`deep_read.build_deep_read` — its own 12-house scan → themes → one Sonnet call), **not** the
5-domain vote system. It was 500ing on the `from __future__` SyntaxError (Fix 0). It already
computes all 12 houses deterministically, but its synth is only prompt-constrained — porting the
Fix-C no-invention gate to it is the recommended follow-up.

## Strategic note
This `vote → net → choose → grounded-narrate` pattern is now the cleanest deterministic engine in
the product. Once the warm voice is live it's the template to rebuild the Ask/`/predict` surface on.
