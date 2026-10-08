# Lovable prompt — Phase 9e: "What to do" replaces "What to be mindful of"

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phase 9d. UI only. The backend field is live and additive: `moves` on the relationship page data and on the joint reading. No new endpoint.

Why: the relationship page's **"What to be mindful of with {name}"** section shows colour-and-weekday remedies ("Wear white or pastel on Friday", "Wear green on Wednesday", "Create something beautiful this week") with checkboxes and **MARK DONE**. They are about the reader's own chart, not about the other person, and have nothing to do with how two people actually work together. They are replaced by two or three plain things the two of you can do, from the areas that score lowest.

## PROMPT STARTS HERE

You are working on the existing Antar web app. UI only; use the data below; show strings exactly as returned; do not publish; open a PR.

### 1. Relationship page `/people/:sessionId` (the private reading)
- **Remove** the section "What to be mindful of with {name}" entirely: the collapsible header ("{n} things to tend"), every card in it (title, tension sentence, "flares most in…", the checkbox lines, the colour/day hint, the "steadily tending…" line) and the **MARK DONE** buttons. Do not move them anywhere on this page. (The colour, day and practice suggestions already live in Practice; do not add them elsewhere.)
- **Add** a section **"What to do"** in the same place (below "How it breaks down"). Data: `moves` from `GET /api/v1/compatibility/session/{session_id}?language=<lang>`: an array of `{area, area_label, text}` (0 to 3 items, weakest area first, already in the page language).
  - Each item: `area_label` as a small muted label, then `text` as the main line, one item per row, no checkboxes, no MARK DONE, no progress state. Plain text rows, same typography as the "How it breaks down" rows.
  - If `moves` is empty or missing, **hide the whole section** (no placeholder). An empty list means every area is flowing.
- Everything else on this page is unchanged (badge, names line, headline, Between you cards, breakdown, Ask chips, Invite to Between us, Your notes with its Edit).

### 2. Our reading tab on the Circle pair page
In the reading (state `on`) from `GET /api/v1/circle/{chart_id}/pair/{other_chart_id}/reading`, `reading.moves` has the same shape. Show a **"What to do"** section directly under the areas list and above Watch, with the same rows. Hide it when empty. Do not show it in any other state.

### Rules
- Show `area_label` and `text` exactly as returned. The only new static string is the section title **"What to do"** (en "What to do", es "Qué hacer", pt "O que fazer", hinglish "Kya karein"; hi falls back to English).
- No colours, weekdays, gemstones, mantras or "wear…" suggestions anywhere in this section, and no checkbox or "done" state. Do not compute or reword anything.
- No pricing text. No backend or API change.

### Acceptance checks (verify and say so in the PR)
- On `/people/:sessionId` the "What to be mindful of" section and every MARK DONE are gone, and nothing replaces them except "What to do" (when `moves` is non-empty).
- "What to do" shows at most three rows, each with the muted area label and the line, with no checkboxes or buttons.
- With every area flowing (empty `moves`) the section is absent.
- On the Our reading tab (state `on`) "What to do" appears under the areas list and above Watch; in other states it does not appear.
- Language switch (en / es / pt) changes the rows.
- Screenshots at 375 px of the relationship page with "What to do" and of the Our reading tab are attached to the PR.

### Out of scope (do not build)
Moving the old remedy cards elsewhere, a checklist or progress for the moves, editing the moves, any backend or API change.

## PROMPT ENDS HERE
