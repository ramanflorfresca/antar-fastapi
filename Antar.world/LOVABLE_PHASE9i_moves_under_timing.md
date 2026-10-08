# Lovable prompt — Phase 9i: "What to do" advice rows under Timing (Our reading tab)

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phases 9e to 9h. UI only. The backend already returns the advice rows (`moves`) for every pair, including business and cofounder pairs; nothing more is needed on the server. This prompt fixes where they sit and makes sure they render for business pairs.

Where the data is: `GET /api/v1/circle/{chart_id}/pair/{other_chart_id}/reading` returns `reading.moves` (always, when the reading is on) and, for pairs with a brief, the same list as `reading.brief.moves`. Each row is `{area, area_label, text}`: 0 to 3 plain things to do, weakest area first, already in the viewer's language.

## PROMPT STARTS HERE

You are working on the existing Antar web app, the Circle pair page, **Our reading** tab, state `on`. UI only; show every string exactly as returned; do not publish; open a PR.

### 1. Put "What to do" directly under Timing
- **When a brief is present** (`reading.brief` non-null, which is every relation type, cofounder and business included): in the brief, the order is now **Timing**, then **What to do**, then **What not to do**, then the note. Use `reading.brief.moves`.
- **When there is no brief** (the brief could not be built): show **What to do** under the areas list, above the Watch line, using `reading.moves`.
- Never show the section twice on one screen.

### 2. The rows
- Section title: **"What to do"** (en "What to do", es "Qué hacer", pt "O que fazer", hinglish "Kya karein"; hi falls back to English).
- One row per item, at most three: `area_label` as a small muted label, `text` as the main line. Plain text rows: no checkboxes, no buttons, no "done" state, no icons implying completion.
- Hide the whole section (title included) when `moves` is empty or missing. An empty list means every area is flowing.

### Rules
- Show `area_label` and `text` exactly as returned. No colours, weekdays, gemstones, mantras or "wear..." suggestions anywhere in this section. Do not compute, reorder or reword the rows.
- Only on the Our reading tab, only in state `on`. No notifications or badges.
- No pricing text. No backend or API change.

### Acceptance checks (verify and say so in the PR)
- For a cofounder or business pair with both switches on and weak areas, "What to do" appears directly under Timing and above "What not to do", with up to three rows (for example "Communication and trust: Put decisions in writing: who decided what, and by when.").
- With every area flowing there is no "What to do" section.
- The section never appears in any state other than `on`, and never twice.
- Screenshots at 375 px of a business pair's Timing and What to do rows are attached to the PR.

### Out of scope (do not build)
Checklists or progress for the rows, editing them, new advice text, any backend or API change.

## PROMPT ENDS HERE
