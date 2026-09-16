# Lovable Brief — Full Chart → SAVED PEOPLE READINGS: remove the numeric score

**Priority: URGENT (Apple 4.3 re-review is LIVE and this page is reviewer-reachable).**
This is a **FE-only** change. No backend change is needed — the data is already there.

---

## The problem

On the **Full Chart** page (the "who you are" page: birth data, archetype, YOUR CHART,
yogas, strengths, areas to mind), the **SAVED PEOPLE READINGS** list at the bottom still
renders a **numeric compatibility score** per row (e.g. a small amber **"59"** / **"68"**).

We already removed numeric compat scores everywhere else (People tab, connection cards):
we show a **band WORD**, never a digit. This one component was missed. It must match.

## The fix

For every saved-person row in SAVED PEOPLE READINGS, **delete the numeric score element**
and render the **band word** instead — reusing the **exact same band-label component/logic
already shipped on the People tab** (so styling and i18n are inherited, not re-invented).

Band word (from the compat score band):

| Backend `badge` | Score range | Word to show |
|-----------------|-------------|--------------|
| `FLOW`          | ≥ 75        | **Flows**    |
| `MIXED`         | 50–74       | **Mixed**    |
| `STRAIN`        | < 50        | **Friction** |

Use the same three words and the same visual treatment the People tab already uses. Do not
introduce a new mapping — if the People-tab rows already render this word from a shared
helper/component, import that here.

## Where to get the word (pick whichever matches how this component already loads data)

- **If the row already has a `badge` field** (FLOW/MIXED/STRAIN) — e.g. it reads from
  `GET /api/v1/network/{chart_id}` (`people[].primary.badge` / `people[].relationships[].badge`)
  — just render `badge` → word via the table above. Easiest path.
- **If the component only has a numeric `score`** (reading `compatibility_sessions` directly) —
  derive the band with the **same thresholds** above (≥75 Flows / ≥50 Mixed / else Friction).
  Prefer switching this component to consume `GET /api/v1/network/{chart_id}`, which already
  returns `badge` per relationship and dedupes people — same source the People tab uses.

**Do not** render `score` anywhere in these rows — not as a ring, not as a subtitle, not on
hover. The digit must be gone from the DOM, not just visually hidden.

## Verify live (antar.world)

1. Hard-refresh with Service Worker + caches cleared (the app ships a SW).
2. Confirm the **bundle hash flips** (new build actually served).
3. On the Full Chart page, scroll to SAVED PEOPLE READINGS and confirm **no digit renders**
   in any row — only **Flows / Mixed / Friction**. Check a person in each band if possible.
4. Confirm the People tab is unchanged (we're matching it, not altering it).

## Guardrails

- FE-only. No new endpoint, no backend edit.
- Reuse the People-tab band-word component — don't fork a second implementation.
- Keep the rest of SAVED PEOPLE READINGS (name, relationship type, tap-through) intact.
