# Lovable brief: new People relationship types (spouse, sibling) + layer flag

Backend is live-ready; the UI only needs to render what the API already sends. No logic in the FE.

## 1. Relationship picker
`GET /api/v1/compatibility/reasons?language=&chart_id=` now returns 12 reasons, in display order:

romantic, **spouse**, cofounder, business, advisor, friend, family, **sibling**, parent, child, employee, boss-or-manager

New ids: `spouse` ("My husband or wife"), `sibling` ("My brother or sister"). Labels, questions and sublabels come
from the endpoint (en/es/pt) - if the picker is rendered from the endpoint nothing else is needed. If any key list is
hard-coded in the FE, add `spouse` and `sibling`.

Copy change to expect: `romantic` sublabel is now "Dating, a relationship still taking shape" and `family`
is now "In-laws, extended family" (siblings and spouses have their own types).

## 2. Labels for saved connections
`compat_type` strings on `/compatibility/sessions/{chart_id}`, `/network/{chart_id}` and
`/compatibility/session/{id}` can now be `spouse` or `sibling`. Any local `compat_type -> label` map needs those two
(fall back to the `/reasons` label, never to "Cofounder" or "Romantic").
Old saved sessions stored as `marriage` are read as `spouse` by the backend.

## 3. Unknown type = HTTP 422
`POST /compatibility/start` with an unrecognised `compat_type` now returns 422
`{"error":"invalid_compat_type","message":...}` instead of silently reading as cofounder. Send one of the ids above.

## 4. `applicable` on each layer
Each layer in `layers[]` has a new boolean `applicable`. It is `false` when the layer carries no weight for that
relationship (for example Chemistry in a parent, child, sibling, advisor, family or employee read). Suggested
treatment: still show it if you like, but visually de-emphasise it (or hide it) when `applicable` is false, and do not
count it in any "x of 6 layers" summary. `weight_in_this_reason` is unchanged.

## 5. Reopen
`GET /compatibility/session/{id}` now also returns `role` (employee / boss-or-manager readings) and re-scores with it.
No UI change required; show it wherever the role is shown after /start.
