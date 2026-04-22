# Output Strip Refactor — Call Site Audit (Phase 2)

Audit of every live Claude `messages.create` call site in the repo, produced
as the implementation checklist for Phase 3 of the centralized output-strip
refactor. Each row specifies how that site's response should be routed through
`apply_user_facing_strips(field_type=…)` from `antar_engine/output_strips.py`.

Legend for the target column:
- `plain` — full strip (instruments + Vedic + day names + planets + scores).
- `headline` — same layers as plain, caller typically also truncates.
- `evidence` — minimal strip (instruments + day names); keeps Vedic depth + scores.
- `window` — instruments + day names; Panchang terms preserved (UI glosses them).
- `skip` — not user-facing text (enum, number, UUID, etc.); no strip.

Line numbers reflect `main` as of commit `2901764` and will drift. Use the
landmark function names when writing Phase 3 patch scripts.

## Audit table

| File:line | Function / endpoint | Response format | User-facing fields (plain) | Evidence fields | Window fields | Current strips | Target `field_type` mapping |
|---|---|---|---|---|---|---|---|
| `main.py:1412` | `/predict` main — primary question-answering Claude call | JSON object (via `plain_english.py` post-processor) | `plain_summary`, `action_item`, `signal_line`, `timing_window` (when a date-range sentence) | `why_this` | — | `plain_english._strip_jargon` on `plain_summary`, `action_item`, `signal_line` (5 sites in `plain_english.py`) | `plain_summary`, `action_item`, `signal_line`, `timing_window` → `plain` · `why_this` → `evidence` · `verdict`, `confidence`, `language` → `skip` |
| `main.py:2906` | `_get_or_generate_upcoming_themes_llm` → `/chart/{id}/past-events` "upcoming themes" section | JSON object | `themes[].text` (narrative), `themes[].title` | — | — | None | `themes[].text`, `themes[].title` → `plain` · `themes[].id`/date fields → `skip` |
| `main.py:13086` | `build_transit_behavioral_block` — builds the `[BEHAVIORAL TRANSIT CONTEXT]` block that gets **injected into the /predict prompt as input** | Plain-text multi-line block | Entire block | — | — | None — prompt itself forbids jargon, but no post-strip | Entire return string → `plain` (defense in depth; downstream `/predict` strip also catches leaks, but cheap to apply here) |
| `main.py:13490` | `_call_claude_wow_hint` → daily-week "WOW" hint v1 | Plain-text single sentence | Entire hint | — | — | `_sanitize_wow_hint` (day-name strip only, per FIX 14b) | Return string → `plain`. `_sanitize_wow_hint` becomes redundant — remove in Phase 5 |
| `main.py:13591` | v2 `_call_claude_wow_hint` — daily-week WOW hint v2 | Plain-text single sentence | Entire hint | — | — | `_sanitize_wow_hint` (day-name strip only) | Return string → `plain`. Same dedup cleanup as v1 |
| `antar_engine/daily_prediction_engine.py:968` | daily-week signal main-pass Claude call | JSON object (`llm_signal`) | `senal_de_hoy`, `verdict_subline`, `observa_hoy_text`, `haz_hoy[]`, `evita_hoy[]` | `el_movimiento` | `windows[].text` | **After FIX 2901764**: `_strip_day_names_from_signal` + `_strip_all_jargon_from_signal` (local shim) | Replace local shim with: per-field calls to `apply_user_facing_strips`. Specifically: plain fields → `plain`; `el_movimiento` → `evidence`; `windows[].text` → `window`; `verdict_emoji`, `verdict_label`, `score`, `date` → `skip` |
| `antar_engine/daily_prediction_engine.py:1042` | daily-week signal **corrective-retry** Claude call (same schema as :968) | JSON object (same schema) | Same as :968 | Same | Same | Same (the strip is applied to the retry result too) | Same mapping as :968 |
| `antar_engine/weekly_briefing.py:199` | `/weekly-briefing/{id}` paid-tier | JSON object | `weekly_focus`, `best_day.reason`, `caution_day.reason`, `domains.{career,wealth,love,health}.signal`, `one_action` | — | — | None | All enumerated text fields → `plain`. `best_day.date`, `caution_day.date`, `domains.*.trend` → `skip` |
| `antar_engine/monthly_deepdive.py:197` | `/monthly-deepdive/{id}` paid-tier | JSON object | `month_theme`, `overview`, `priority_actions[].action`, `best_week.reason`, `caution_week.reason`, `monthly_mantra` | `strong_planets[]`, `weak_planets[]` (planet-name arrays; power-user depth) | — | None | Narrative fields → `plain` · planet-name arrays → `evidence` (don't strip planet names from lists) · dates/numbers → `skip` |
| `antar_engine/annual_planning.py:224` | `/annual-plan/{id}` paid-tier | JSON object | `year_theme`, `year_summary`, `peak_windows.{name,reason}`, `build_this_year[]`, `protect_this_year[]`, `release_this_year[]`, `year_mantra` | — | — | None | All enumerated text fields / arrays → `plain` · `peak_windows.start`/`end` dates, `quarter` enum → `skip` |
| `antar_engine/welcome_signal.py:805` | `/welcome/{id}` v1 — onboarding 3-signal payload | JSON object (3-signal structure) | `signal_1.headline`, `signal_1.body`, `signal_2.thread`, `signal_3.headline`, `signal_3.body` | `signal_2.events[]` (event titles, keep proper nouns) | — | None | Narrative → `plain` · `signal_2.events[]` → `evidence` (proper nouns/dates) · `signal_3.domain` enum → `skip` |
| `antar_engine/welcome_signal_v2.py:584` | `/welcome/{id}` v2 — onboarding 3-signal payload | JSON object (3-signal structure) | `signal_1.headline`, `signal_1.body`, `signal_2.headline`, `signal_2.body`, `signal_3.headline`, `signal_3.body`, `three_findings[].headline`, `three_findings[].body` | — | — | None | All headline/body/list text → `plain` · `chapter_name` treat as `headline` (short, user-visible) · metadata fields → `skip` |
| `antar_engine/system_prompt_builder.py:320` | utility Claude call — **only referenced from a possibly dead `/api/chat` path; verify before migrating** | Plain-text string | Full response if user-facing | — | — | None | If confirmed dead: mark for deletion. If alive: `plain` |

## Call sites needing a quick decision

1. **`system_prompt_builder.py:320`** — appears to be a test/utility call, not a live endpoint. Before Phase 3, `grep -rn "system_prompt_builder.generate" main.py antar_engine/` to confirm it's actually called at runtime. If not, drop from migration plan and delete in a cleanup PR.
2. **`welcome_signal.py:805` vs `welcome_signal_v2.py:584`** — the brief lists both. Confirm whether v1 is still reachable through `/welcome/…`, or if the endpoint always routes through v2 now. If v1 is dead, skip its migration and deprecate the file.
3. **`main.py:13086` (`build_transit_behavioral_block`)** — technically intermediate (goes into a prompt, not to the user). Applying `field_type='plain'` here is cheap defense-in-depth but not strictly required, since the downstream `/predict` Claude call runs its own strip via `plain_english.py`. Treat as **low priority** in the Phase 3 migration order.

## Phase 3 migration order (safety-first)

Each step is one commit + one deploy + one curl verification before the next:

1. `welcome_signal_v2.py:584` — lowest traffic, cleanest schema.
2. `welcome_signal.py:805` — if still live (see decision #2).
3. `weekly_briefing.py:199`.
4. `monthly_deepdive.py:197`.
5. `annual_planning.py:224`.
6. `main.py:13490` + `main.py:13591` (both WOW hints) — single patch; remove `_sanitize_wow_hint` once the central call covers day names.
7. `daily_prediction_engine.py:968` and `:1042` — replace `_strip_all_jargon_from_signal` shim with per-field `apply_user_facing_strips` calls. The shim stays for one deploy cycle as a safety net.
8. `main.py:2906` — upcoming themes.
9. `main.py:13086` — transit behavioral block (defense-in-depth, optional).
10. `main.py:1412` — `/predict` main. Highest regression risk. Runs last. Full curl matrix (ES + EN, career/love/health/wealth question types) before it ships.
11. `system_prompt_builder.py:320` — only if still live.

## Known duplications that Phase 3 will eliminate

- `main.py::_INSTRUMENT_TRANSLATIONS` — already duplicated into `output_strips._INSTRUMENT_TRANSLATIONS`. After Phase 3, the `main.py` copy is deleted and `_translate_instrument_name` imports from `output_strips`.
- `plain_english._strip_jargon` — will become a deprecated wrapper around `output_strips._strip_planet_names` in Phase 5.
- `daily_prediction_engine._strip_day_names_from_signal` — same treatment; becomes a wrapper around `output_strips._strip_day_names`.
- `daily_prediction_engine._strip_all_jargon_from_signal` (added by FIX I/J/K/L) — the shim gets removed in step 7 once the central call covers every field explicitly.
- `main.py::_sanitize_wow_hint` — becomes redundant after step 6; deleted in a cleanup PR.
