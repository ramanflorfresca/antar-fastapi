# Lovable prompt — Phase 9g: "Our call" — are we built to partner? (cofounder and business pairs)

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phase 9f. UI only. The backend is merged and adds fields to `reading.brief` (additive). It changes the **top of the Founders' brief** and adds a line per person.

The idea (owner): businesses don't fail, people do. Two people who work hard and think alike can carry a venture through years of struggle; two people who aren't built for partnership are better off with ONE owner and the other as a consultant paid in task-based equity. And a season that doesn't work now can work in a different one. The screen must say this in **plain words with no chart terms anywhere**: no houses, lords, dashas, planets or stars. (The chapter and stretch wording, such as "illusion" or "growth and wisdom", is plain language returned by the API.)

## PROMPT STARTS HERE

You are working on the existing Antar web app, the Circle pair page, **Our reading** tab, state `on`, for pairs whose `reading.brief` is present (cofounder and business). UI only; show every string exactly as returned; do not publish; open a PR.

### 1. "Our call" card: the first thing in the brief
Two parts, both from `reading.brief`:
- **The call (timing), from `phase`** = `{status, call, call_title, line, better}` (`phase` can be null). A prominent card headed by `phase.call_title` ("Not now", "Possible, with structure" or "A good time"), colored by `phase.call`: `not_now` red/amber, `with_structure` amber, `good_now` green. Under it show `phase.line` verbatim (it names who is in which stretch and until when), then, if `phase.better` is non-null, `phase.better.line` in a muted style with a small calendar icon ("What doesn't work now can work later: from {date}…").
- **The structure, from `verdict`** = `{key, title, line, lead, other}`. A second, quieter card directly under the call: `verdict.title` ("Built to partner", "Partners, with clear lanes", "One founder, one advisor" or "One owner, work by contract") and `verdict.line`. Colors: `full_partners` green, `partners_with_lanes` neutral, `founder_plus_advisor` and `solo_contract` amber.
- If `phase` is null show only the structure card. Nothing else in the brief moves: the fit badge, areas list and everything from Phase 9f follow below.

### 2. Each person's card (in "The two of you"), new rows from `people[i]`
Add, between the role line and "How you work":
- **Temperament:** `temperament.trait` as one line (hide if `temperament` is null). Never show a name for it.
- **Partnership:** `partnership.label` as a tag ("Built for partnership", "Could go either way", "Better leading alone"; color: partner green, either neutral, solo amber), then `partnership.reasons[]` as up to three short muted lines.
- **Right now:** from `season` = `{label, effect, tone, heavy, position, ends_label, chapter_ends}` (hide if `season` is null): show `season.label` exactly as returned (it is a full sentence that already names the long chapter with its end date, where the person is inside it (first or last stretch, with the stretch's end date) and, in the last stretch, what comes next), then `season.effect` as the muted line under it. Do not add "until …" yourself. Tone colors: `clouded` red/amber, `testing` amber, `steady` neutral, `favorable` green.
Static string to add (en/es/pt; hinglish Roman; hi falls back to English): "Right now". Everything else is returned by the API.

### Rules
- Show strings exactly as returned. Never add astrology terms, house numbers, planet names or star names anywhere. Never show or infer a prediction that the venture will work or fail; the bottom note from Phase 9f stays.
- Never recompute the verdict, the lean, or the seasons.
- No pricing text, no backend change, no new endpoint.

### Edge cases
- `verdict` is always present when a brief is present; `phase` may be null: show only the structure card then.
- `partnership.reasons` may be empty: show only the tag.
- Works at 375 px and desktop.

### Acceptance checks (verify and say so in the PR)
- The first card in the brief is the call ("Not now" / "Possible, with structure" / "A good time") with its sentence and, when present, the "what doesn't work now can work later" line; the structure card (verdict) sits directly under it.
- Each person's card shows a temperament line, a partnership tag with up to three reasons, and a "Right now" line with its effect sentence.
- No chart terms appear anywhere in the new content (search the rendered text for house, lord, dasha, planet and star names).
- Screenshots at 375 px of: the Our call card (two different verdicts if you can), and a person card are attached to the PR.

### Out of scope (do not build)
Any prediction of funding or success, equity calculators or templates, other relation types, any backend or API change.

## PROMPT ENDS HERE
