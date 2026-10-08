# Lovable prompt — Phase 9g: "Our call" — are we built to partner? (cofounder and business pairs)

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phase 9f. UI only. The backend is merged and adds fields to `reading.brief` (additive). It changes the **top of the Founders' brief** and adds a line per person.

The idea (owner): businesses don't fail, people do. Two people who work hard and think alike can carry a venture through years of struggle; two people who aren't built for partnership are better off with ONE owner and the other as a consultant paid in task-based equity. And a season that doesn't work now can work in a different one. The screen must say this in **plain words with no chart terms anywhere**: no houses, lords, dashas, planets, nakshatras.

## PROMPT STARTS HERE

You are working on the existing Antar web app, the Circle pair page, **Our reading** tab, state `on`, for pairs whose `reading.brief` is present (cofounder and business). UI only; show every string exactly as returned; do not publish; open a PR.

### 1. "Our call" card: the first thing in the brief
From `reading.brief.verdict` = `{key, title, line, lead, other}` and `reading.brief.phase` = `{status, line, better}` (phase can be null):
- A prominent card titled with `verdict.title` (this is the verdict: e.g. "Built to partner", "Partners, with clear lanes", "One founder, one advisor", "One owner, work by contract"), the sentence `verdict.line` under it, then `phase.line` as a second paragraph, then (if `phase.better` is non-null) `phase.better.line` in a muted style with a small calendar icon. Colors: `full_partners` green, `partners_with_lanes` neutral/accent, `founder_plus_advisor` amber, `solo_contract` amber. `phase.status` of `both_heavy` or `one_heavy` shows a small amber "Timing" tag; `clear` shows a green one. Use the words from the API for the tag text only if present, otherwise show no tag text.
- For `founder_plus_advisor`, if `verdict.lead` is the viewer's own first name (the first person in `people[]`), show nothing extra; the sentence already names both people.
- This card replaces nothing else: the existing fit badge, areas list and everything from Phase 9f follow below it.

### 2. Each person's card (in "The two of you"), new rows from `people[i]`
Add, between the role line and "How you work":
- **Temperament:** `temperament.trait` as one line (hide if `temperament` is null). Do not show any name for it.
- **Partnership:** `partnership.label` as a tag ("Built for partnership", "Could go either way", "Better leading alone"; color: partner green, either neutral, solo amber), then `partnership.reasons[]` as up to three short muted lines.
- **Right now:** `season.label` and `season.ends_label` as one line: "{season.label}, until {season.ends_label}" using the label exactly as returned; for a heavy season (`season.heavy` true) use the amber tone, otherwise the neutral tone. Hide if `season` is null.
Static strings to add (en/es/pt; hinglish Roman; hi falls back to English): "Right now" and "until". Everything else is returned by the API.

### Rules
- Show strings exactly as returned. Never add astrology terms, house numbers, planet names or star names anywhere. Never show or infer a prediction that the venture will work or fail; the bottom note from Phase 9f stays.
- Never recompute the verdict, the lean, or the seasons.
- No pricing text, no backend change, no new endpoint.

### Edge cases
- `verdict` always present when a brief is present; `phase` may be null: show only the verdict then.
- `partnership.reasons` may be empty: show only the tag.
- Works at 375 px and desktop.

### Acceptance checks (verify and say so in the PR)
- The first card in the brief is "Our call" with the verdict title and sentence, then the timing paragraph and, when present, the "what doesn't work now can work later" line.
- Each person's card shows a temperament line, a partnership tag with up to three reasons, and a "Right now" line.
- No chart terms appear anywhere in the new content (search the rendered text for house, lord, dasha, planet and star names).
- Screenshots at 375 px of: the Our call card (two different verdicts if you can), and a person card are attached to the PR.

### Out of scope (do not build)
Any prediction of funding or success, equity calculators or templates, other relation types, any backend or API change.

## PROMPT ENDS HERE
