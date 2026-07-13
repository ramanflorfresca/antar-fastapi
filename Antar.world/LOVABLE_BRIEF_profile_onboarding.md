# Lovable brief — capture the user's real profile (so predictions can be personal)

## Why
Predictions can only be tailored to a user's life if we know the basics — and
right now we don't. Live data:

| Field | Real answers captured |
|---|---|
| `marital_status` | **3 of 214** (211 "unknown") |
| `children_status` | **2 of 214** (212 the default "no_children_unsure") |
| `career_stage` | **~1 of 214** (213 the default "mid_career") |
| `current_city` | **22 of 214** (192 missing) |

So the engine has been guessing — telling a childless user about "the children
area," or computing daily timing for the country capital because it doesn't know
their city. The backend now (a) treats blanket defaults as "unknown" and (b) gates
predictions on real status. **The missing piece is the frontend actually asking.**

The backend endpoints already exist — this brief is wiring them into onboarding
(and a place to edit later).

## What to capture — 4 questions
Ask these once at onboarding (after the chart is created), and expose the same on
a **"Your details / Profile"** settings screen so users can update after a life
change. Every question is **skippable** — a skipped question must be sent as
**omitted / null, never a default value.**

| Question (plain wording) | Field | Allowed values (send exactly these strings) |
|---|---|---|
| "Are you currently…" | `marital_status` | `single` · `in_relationship` · `married` · `divorced` · `widowed` |
| "Do you have children?" | `children_status` | `no_children` · `has_children` · `expecting` |
| "Where are you in your work life?" | `career_stage` | `student` · `early_career` · `mid_career` · `senior` · `entrepreneur` · `between_jobs` · `retired` |
| "What city do you live in now?" | `current_city` + `current_country` | free-text city + ISO-2 country code (e.g. `US`) |

Do **not** preselect a default. "Prefer not to say" = skip = omit the field.

## The API contract (endpoints already live)
**Get chart-specific questions (optional, for conversational phrasing):**
`GET /api/v1/predict/patra-onboarding?chart_id=<id>&language=en`

**Save answers — one call, send only what was answered:**
```
POST /api/v1/user/patra
Authorization: Bearer <token>
{
  "chart_id": "<id>",
  "marital_status": "married",        // omit if skipped
  "children_status": "no_children",   // omit if skipped
  "career_stage": "entrepreneur",     // omit if skipped
  "current_city": "Albuquerque",      // omit if skipped
  "current_country": "US"             // omit if skipped
}
```
The backend writes only the fields you send (non-null), sets `patra_complete`, and
returns the user's life-stage. **`current_city`/`current_country` are newly
accepted** on this endpoint — sending them fixes the daily timing (it geocodes the
city → real coords + timezone).

## Behavior notes
- **Never send a placeholder.** An unanswered field must be absent from the JSON,
  not `"unknown"` / `"mid_career"` / `"no_children_unsure"`. The backend treats
  those legacy strings as unknown anyway, but new writes should be clean.
- **Editable later.** The same `POST /api/v1/user/patra` updates any subset — the
  settings screen just re-submits changed fields (divorced, new job, moved city).
- **Immediate payoff.** As soon as `current_city` is set, that user's Today timing
  switches from the country capital to their real city; and once
  `children_status`/`marital_status` are real, the reading stops guessing about
  kids/partners.

## HOW to ask — smart & low-friction (don't build a form wall)
A 4-question form at signup kills completion. Capture it these three ways instead:

1. **"Make it yours" — AFTER the first reading, not before.** Once they've seen
   value, show a dismissible card with one-tap **chips** (no text input), each
   step skippable, with progress dots. On each tap, PATCH that one field and
   advance; at the end re-render Today. Friendly chip labels map to the enum
   strings above.
2. **Just-in-time top-up (the smart part).** If a field is still unknown AND the
   current reading is about to lean on it, show a tiny inline chip pair instead of
   assuming — e.g. a relationship-heavy read with `marital_status` unknown →
   "Quick — are you partnered? [Single] [Partnered]". One tap, in context, then
   re-render. The question feels earned and the payoff is instant.
3. **Settings → "Your details".** The same four questions, always editable.

**City:** pre-fill from browser geolocation / IP and let the user just **confirm**
("You're in Albuquerque? ✓ Yes / Change") — never make them type it if we can guess.

**Auth:** `POST /api/v1/user/patra` needs a signed-in user. For a guest, run the
personalize step right after "Continue with Google" (the save-your-chart moment).

## Out of scope (backend handles)
- Geocoding the city, timezone, DST — all backend.
- Applying the profile to predictions (the "only tell them what's applicable"
  logic) — backend, already gating on these fields.
