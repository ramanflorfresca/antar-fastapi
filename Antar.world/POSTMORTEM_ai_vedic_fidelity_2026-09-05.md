# Postmortem — "Are we a 100% AI Vedic astrologer?" (2026-09-05)

**Short answer: No — not 100%, on both halves of the phrase.**

- **AI half:** The system is *Claude-by-default* but **not Claude-guaranteed**. It is engineered to *always answer*, which means every generation path silently degrades — to DeepSeek, to a template, or to a canned string — with **no alerting**. During the recent incident, essentially every Claude call on the main paths was failing and running on **DeepSeek instead of Claude for an unknown period, invisibly.**
- **Vedic half:** The readings are **genuinely computed from real Vedic astrology** (~78% grounded overall), *not* an LLM inventing astrology-flavoured text. `/predict` is the real thing (~90%, deterministic resolver owns the verdict). `/daily` (~70%) and `/ask` (~75%) are grounded but narrated more loosely. There is also a graveyard of computed-but-dead engines and a couple of live-but-untuned ones.

So: **a real Vedic-computed engine with an AI narration layer — but the AI layer can fail invisibly, and the grounding is not uniform.**

---

## 1. The incident (root cause)

**What happened:** `requirements.txt` pinned `anthropic>=0.40.0` — *unpinned*. A routine redeploy ran `pip install` and pulled a newer Anthropic SDK that rejects the `temperature` keyword as the code passes it. Result: **every** `client.messages.create(...)` raised `AsyncMessages.create() got an unexpected keyword argument 'temperature'`.

**Blast radius:** In one 1,000-line log window there were **225** such failures, and **8** `[claude] error, falling back to DeepSeek` lines. Because `call_llm_claude` catches any error and falls back to DeepSeek (`main.py:2149`), the app kept answering — **on DeepSeek, not Claude** — for Ask/predict, and the daily engine fell back to templates. Nothing surfaced to users; nothing alerted.

**Not the schema, not app code.** `temperature` has been on those calls since the engines were written; the logging wrapper is unchanged since June; the anthropic line hadn't changed since July. The only thing that changed with zero code edits was the dependency version on redeploy. (My earlier "schema drift" framing was wrong — the `user_correlations.user_id does not exist` warning is a separate, long-standing, *caught* log, not this incident.)

**Honest caveat:** any Claude-dependent output produced during the outage window — including the Spanish `/predict` responses I "verified" earlier this session — was likely **DeepSeek output, not Claude.** Those checks validated the fallback model.

**Detection gap:** the outage was found only because you sent a raw log export. There is no alerting, and `/health` never probes the model.

### Fixes shipped (2026-09-04/05)
- `anthropic==0.40.0` pinned (`requirements.txt`) — a redeploy can't silently upgrade the SDK again. Service verified healthy after the rebuild.
- Retry-without-rejected-kwarg in the shared wrapper (`llm_log.py`) — covers every Claude call.
- `_safe_messages_create` on the daily path.
- SDK version now logged at startup (`main.py`).
- `PATCH /api/v1/me` made resilient (was 500-ing and could hang login bootstrap).

These close the *specific* hole. The *structural* silent-degradation design remains (see §2).

---

## 2. AI-integrity findings (the "AI" half)

**Every user-facing generation path is built to never surface an LLM failure** — it falls to DeepSeek, a template, or a canned string, and `plain_english` then reformats whatever it got into the same polished JSON. Ranked risks:

1. **Silent Claude→DeepSeek fallback with no telemetry** (`main.py:2149`). DeepSeek calls are *not logged* to `llm_call_log` (its client is unwrapped), so a fallback shows up only as a *drop in Claude volume*, never as an error.
2. **Runtime config can point prod at DeepSeek/Kimi** — the `llm_provider` row in `app_config` (default `anthropic`) routes Ask/predict **and** daily through the OpenAI-shape provider within ~20s of a DB write. One row silently swaps the brain. No guardrail, no banner.
3. **No health/alerting on the primary model.** `/health` is static; detection is entirely manual/pull-based (admin `llm-usage` / `compare`). The new kwarg-retry logs the retried call as *success*, so a recurrence would be invisible in the failure metric (detectable only via the `[llm-log] SDK rejected` log string).
4. **Observability holes:** the DeepSeek path, the `plain_english` httpx path, and three engines with their own unwrapped clients (`ask_intent`, `food_engine`, `readability`) never write to `llm_call_log` at all.
5. **DeepSeek-by-design surfaces** (career `main.py:11062`, Prashna verdict `17659`, follow-up `21108`, monthly briefing `894/8663`) — some of these were *never* Claude. `main.py:17659`'s comment even says "Call Claude to explain the verdict" while calling DeepSeek — the source itself misrepresents which model answers.

---

## 3. Vedic-grounding findings (the "Vedic" half) — ~78%

Real swisseph (Lahiri sidereal) → vimshottari dasha → gochar/transits → divisional (D9/D10) → yogas → natal promise → precision windows → **deterministic resolver**. This is genuine computation, not confabulation.

- **`/predict` ≈ 90%.** `resolve_domain_verdict` (`verdict_resolver.py:771`) is a pure no-LLM function that OWNS the verdict/timing/move; the LLM is hard-constrained both prompt-side (FIXED FACTS block) and output-side (verdict override, `main.py:7596`). The ~10% gap: the underlying `_score_date` is a *simplified heuristic* Vedic model (fixed favorable-planet/house tables, hand-set thresholds), not classically exhaustive.
- **`/daily-signal` ≈ 70%.** Fed real transit/dasha/ashtakavarga/tara/Chara compute + a deterministic day-score, but the reader-facing prose is LLM-written with a *narrow* no-invention gate (only blocks invented proper nouns in 4 fields) and **accept-with-warnings** on retry failure — no hard verdict-pin like `/predict`.
- **`/ask` ≈ 75%.** Real per-concern engines + computed intraday windows, but **no single owned verdict** and a larger LLM surface; leans on jargon strippers.

### Engine status
- **LIVE + consumed:** chart, transits, vimshottari, precision_windows, verdict_resolver, natal_promise, divisional (D9/D10), yoga_engine, ashtakavarga, jaimini (karakas/Chara), rarity, ashtottari, daily_transit_analyzer.
- **LIVE but UNTUNED-v1 (math real, significations unvalidated):** `d10_career.py`, `concern_engines.py`.
- **DEAD / unwired in production:** ~~`hora_chart.py`, `wealth_channel.py`, `lagna_answer.py`, `av_conviction.py`~~ — **THIS LIST WAS WRONG.**
  - **CORRECTION (2026-09-05, on P2 investigation):** based on "0 refs in main.py", it missed the `main.py → predictions.py → engine` chain. Reality: `hora_chart`/`wealth_channel`/`lagna_answer` are **LIVE and consumed** — `build_layered_predictions` (called in `/predict`, main.py:5809) runs them, and `predictions_to_context_block` injects `lagna_answer` into the reading prompt when available. They also already handle the tested-dead D-2 result **honestly**: `lagna_answer` wealth returns an explicit refusal to give a date, surfacing only the channel shape (`lagna_answer.py:~226`). `av_conviction.py` is **not** dead junk either — it's a deliberate **shadow-mode** module (kill switch default `shadow`; "requires Raman's explicit sign-off" to activate). `hora_chart` also has a test. **Nothing here should be deleted.**
- **COMPUTED but unused in live paths:** `yogini_dasha.py`, `narayana_dasha.py`.

### Confabulation risk
Contained, not eliminated. Highest residual: `/daily` prose isn't cross-checked against the computed blocks (a planet/house claim in the vibe text isn't verified to match the transit compute). `/ask` has a wide narration surface with no single deterministic verdict. Untuned `d10_career`/`concern_engines` are presented to the narrator as authoritative — "grounded but possibly wrong," distinct from confabulation.

---

## 4. What "100%" would require (prioritized)

**P0 — make the AI layer honest & observable**
1. Log the **resolved provider + model on every generation**, and record DeepSeek/fallback calls in `llm_call_log` as an explicit `fallback` outcome (today they're invisible).
2. **Alert** on any `[claude] error, falling back` or `[llm-log] SDK rejected` occurrence (Slack/Sentry/webhook) — turn a silent outage into a page.
3. Add a real **`/health` model probe** (or startup assertion) that fails loudly when the Claude client is unavailable or `llm_provider != anthropic`.

**P1 — tighten grounding**
4. Give `/daily` a **claim-to-source check** (or a verdict-pin like `/predict`) so narrated specifics must match the computed transit/dasha/ashtakavarga blocks; stop accepting-with-warnings silently.
5. Give `/ask` a **single deterministic verdict owner** (reuse `resolve_domain_verdict`) instead of distributed engine narration.

**P2 — clean the graveyard & validate** *(2026-09-05: the "graveyard" was mostly a false alarm — see §3 correction)*
6. ~~Remove the DEAD engines~~ → **DONE / N/A.** Investigation found no deletable dead engines: `hora_chart`/`wealth_channel`/`lagna_answer` are live + consumed + already honest about tested-dead D-2; `av_conviction` is a deliberate shadow module awaiting sign-off. Nothing deleted (correct call). Only down-label shipped: added an UNTUNED-v1 caveat to `concern_engines.py` (`d10_career.py` already had one).
7. Validate or down-label the UNTUNED-v1 significations in `d10_career`/`concern_engines` (the math is real; the mappings aren't proven).
8. Fix the misleading DeepSeek-by-design comments (e.g. `main.py:17659`) and decide deliberately which surfaces *should* be Claude.

---

## 5. Bottom line

We are a **genuinely Vedic-computed system** (not an LLM guessing) with an **AI narration layer that is not guaranteed to be the AI we think it is.** The incident proved the AI half can go fully degraded and invisible. Vedic grounding is strong on `/predict`, softer on `/daily` and `/ask`, with dead and untuned engines around the edges.

"100% AI Vedic astrologer" is not the current state. The fastest path to trustworthy is **P0 (observability + alerting)** — so the AI half can never again be silently wrong — followed by pinning down the daily/ask grounding.
