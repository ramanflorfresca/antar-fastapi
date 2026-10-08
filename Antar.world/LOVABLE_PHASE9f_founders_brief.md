# Lovable prompt — Phase 9f: the Founders' brief (cofounder and business pairs)

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phases 9 to 9e. UI only. The backend is built; no new endpoint. It extends "Our reading" (Phase 9d): when the pair's relation is **cofounder** or **business**, the reading response also carries `reading.brief`. Other relations have no brief and keep the Phase 9d reading unchanged.

What it is: what you would want an astrologer to tell you about you and a cofounder: how each of you works, who should lead what, when to be careful, what not to do, how to balance it. It **describes** how two people tend to work and when to be careful. It never says funding will come, a venture will work, or a date is lucky, and it says so on the screen.

## PROMPT STARTS HERE

You are working on the existing Antar web app, the Circle pair page, **Our reading** tab, state `on`. UI only; use the data below; show strings exactly as returned; do not publish; open a PR.

### 1. When it shows
Only when `GET /api/v1/circle/{chart_id}/pair/{other_chart_id}/reading` returns `state: "on"` and `reading.brief` is non-null. If `brief` is missing (other relations, or the brief could not be built) show the Phase 9d reading exactly as before. Never show the brief in any other state.

### 2. Consent copy (the switch explainer changes for these pairs)
The Phase 9d explainer promised "a score, six areas, one thing to watch". For a pair whose `relation.key` is `cofounder` or `business` (from the pair page data), use this text instead on the `off` card and on the `they_on` card (en/es/pt, hinglish Roman, hi falls back to English):
*"A short read of how the two of you work together: how each of you tends to work, who covers what, when to be careful, and what to avoid. It uses both charts and shows no birth details. It stays hidden until you both turn it on."*
The switch, the helper line and the four states are otherwise unchanged. (Reason: the brief shows each person's working style to the other, so the consent must say so.)

### 3. Layout of the brief (top to bottom, inside the Our reading tab)
Everything below comes from `reading.brief`; render it exactly as returned.
1. **Fit** (`fit`): the badge and score card as in Phase 9d (`fit.badge`, `fit.score`, `fit.headline`). The existing areas list from `reading.layers` follows this section as before.
2. **The two of you** (`people[]`, the viewer is always first): two cards, stacked on phones and side by side on desktop. Each card: first name; `role_label` as a tag with `role_line` under it; **How you work** (`how_you_work`, 1 to 2 short lines); **Strong at** (`strong_at[]`: `title` bold, `effect` as the muted line under it); **Watch for** (`watch_for[]` the same way; if empty show `watch_for_none` in muted text, never an empty box).
3. **Balance** (`balance`): `balance.line` as the main paragraph, then `balance.tail` as a muted line.
4. **Timing** (`timing`): `timing.line` first. Then, if `timing.shared_open` is non-empty, a green "Shared open" list (`label` and `range` per row); then, if `timing.careful` is non-empty, an amber **"Careful stretches"** list (`label` and `range` per row). Then each item of `timing.shifts[]` as one muted sentence (`line`).
5. **What not to do** (`donts[]`): up to three numbered lines, exactly as returned.
6. **What to do** (`moves[]`): the Phase 9e rows (`area_label` muted, `text` main). If Phase 9e is not built yet, build this section here.
7. **Note** (`note`): one muted line at the very bottom, always shown. Do not remove it or shorten it.

### Rules
- Show every string exactly as returned. The only new static strings are the section titles: "The two of you", "How you work", "Strong at", "Watch for", "Balance", "Timing", "Shared open", "Careful stretches", "What not to do" (en/es/pt; hinglish Roman; hi falls back to English), and the replaced consent text above.
- Never add a prediction, a success claim, a "lucky" or "best day" label, or any fund-raising advice of your own. Never show birth details or chart ids.
- Never recompute roles, dates or windows. Never store or log the brief; no analytics events containing it.
- No notifications, badges or hints about the brief anywhere outside the Our reading tab.
- No pricing text. No backend or API change.

### Edge cases
- `watch_for` empty for a person: show `watch_for_none`. `strong_at` empty: hide that block.
- `timing.shared_open` empty and `careful` empty: show only `timing.line`.
- `balance.kind` can be `split`, `two_drivers`, `two_anchors` or `even`: render the same way for all.
- Works at 375 px and desktop; long date ranges wrap.

### Acceptance checks (verify and say so in the PR)
- For a cofounder pair with both switches on, the Our reading tab shows fit, the areas list, then the sections above in order; for a friend pair it shows only the Phase 9d reading.
- The explainer on the `off` and `they_on` cards uses the new consent text for cofounder and business pairs only.
- Each person sees themselves first in "The two of you"; both people see the same roles and the same careful stretches.
- No section appears in any state other than `on`; turning either switch off removes the whole brief for both.
- The bottom note is always present.
- Screenshots at 375 px of the brief (top, two cards, balance and timing, what not to do) are attached to the PR.

### Out of scope (do not build)
Briefs for other relation types, anything that predicts funding or success, sharing or exporting the brief, any backend or API change.

## PROMPT ENDS HERE
