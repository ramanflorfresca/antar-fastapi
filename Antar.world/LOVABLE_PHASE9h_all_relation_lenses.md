# Lovable prompt — Phase 9h: the brief for EVERY relation type (lenses)

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phases 9f and 9g. UI only. The backend is merged: `reading.brief` now exists for **all twelve relation types**, each read through its own lens. Cofounder and business keep the venture brief (Phases 9f and 9g); every other relation gets the same page with the differences below. No new endpoint.

`reading.brief.lens` is the relation (`cofounder`, `business`, `employee`, `boss`, `advisor`, `spouse`, `romantic`, `parent`, `child`, `sibling`, `family`, `friend`) and `reading.brief.family` is one of `work_partner` (cofounder, business), `work_hier` (employee, boss), `counsel` (advisor), `close` (the rest).

## PROMPT STARTS HERE

You are working on the existing Antar web app, the Circle pair page, **Our reading** tab, state `on`. UI only; show every string exactly as returned; do not publish; open a PR.

### 1. Show the brief for any relation, not just cofounder and business
Render the brief whenever `reading.brief` is non-null, whatever the relation. Keep the Phase 9f layout and the Phase 9g call + structure cards. The sections adapt as follows.

### 2. What is the same for every lens
- The **call** card (`phase.call_title`, `phase.line`, `phase.better.line`): same layout. The words differ by lens (for example "A delicate time", "Fine, with patience", "A calm time" for close relations); show them as returned, colored by `phase.call` (`not_now` red/amber, `with_structure` amber, `good_now` green).
- **Right now** per person (`people[i].season`), **Timing**, **What not to do** (`donts`), **What to do** (`moves`) and the bottom **note**: unchanged.

### 3. What changes by `family`
- **`work_partner`** (cofounder, business): exactly Phases 9f and 9g (role tag, "Partnership" tag, balance line with the driver/anchor split).
- **All other families:** each person's card has **no role tag** (`role_label` and `role_line` are null: hide them) and **no "Partnership" tag** (`partnership` is null). Instead show `bond` when it is non-null: `bond.label` as a tag ("Well supported", "Steady", "Needs extra care"; colors green / neutral / amber) and `bond.reasons[]` as up to three short muted lines. If `bond` is null, show neither.
- **Structure card** (`verdict`): for non-venture lenses `verdict.key` is `natural_fit`, `workable_with_care` or `needs_patience` (green / neutral / amber); `verdict.title` and `verdict.line` as returned. `verdict.lead` and `verdict.other` are null.
- **Balance** (`balance`): for non-venture lenses `balance.kind` is `pace_differs` or `pace_close`, and `balance.tail` is an empty string (hide it). Render `balance.line` as the paragraph.
- **Timing** lists only the topics that matter for that relation (the API already filters); render as in Phase 9f.

### 4. Consent copy for the switch (the `off` and `they_on` cards) by `relation.key`
Use these texts (en/es/pt; hinglish Roman; hi falls back to English) instead of the Phase 9d explainer, for every relation:
- cofounder, business: the Phase 9f text.
- employee, boss, advisor: "A short read of how the two of you fit in this working relationship: how each of you tends to show up, when to be careful, and what to avoid. It uses both charts and shows no birth details. It stays hidden until you both turn it on."
- spouse, romantic, parent, child, sibling, family, friend: "A short read of this relationship: how supported each of you is in it, when to go gently, and what to avoid. It uses both charts and shows no birth details. It stays hidden until you both turn it on."

### Rules
- Show strings exactly as returned. Never add astrology terms, prediction, advice of your own, or any label implying the relationship will last or end. Never recompute verdicts or levels.
- The only new static strings are the two consent texts above (plus the cofounder one from 9f).
- No pricing text. No backend or API change.

### Edge cases
- `bond` can be null for a person: render the card without that tag.
- `moves` can be empty: hide the section. `phase` can be null: show only the verdict.
- Works at 375 px and desktop.

### Acceptance checks (verify and say so in the PR)
- A cofounder pair looks exactly as in 9f/9g. A friend, spouse, parent, child, sibling, family, boss, employee and advisor pair each show the brief with no role or partnership tags, the bond tags, the lens's structure card, the pace balance line and their own call words.
- The consent text differs for the three groups above.
- Screenshots at 375 px of a spouse pair and a boss/employee pair (call, structure, a person card) are attached to the PR.

### Out of scope (do not build)
New relation types, any change to the venture brief, any prediction, any backend or API change.

## PROMPT ENDS HERE
