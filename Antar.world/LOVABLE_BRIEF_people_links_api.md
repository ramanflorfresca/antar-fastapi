# Lovable brief: People links API (Relationship Integration Engine, phase 1)

Backend only. All logic lives in FastAPI; the UI just calls these and renders. Every route needs
`Authorization: Bearer <supabase access token>` and the caller must own `owner_chart_id`
(otherwise 401 signed-out, 404 not yours). Base: `/api/v1`.

## Relation enum (`relation`)
`child, spouse, romantic, parent, sibling, family, employee, boss, cofounder, business, advisor, friend`

Pickers should send `relation` plus an optional `relation_detail`. The API also accepts the plain word
and maps it, so `relation: "wife"` works. Mapping:

| User picks | relation | relation_detail |
|---|---|---|
| son / daughter | child | son / daughter |
| husband / wife | spouse | husband / wife |
| girlfriend / boyfriend / partner | romantic | girlfriend / boyfriend / partner |
| mother / father | parent | mother / father |
| brother / sister | sibling | brother / sister |
| manager / boss | boss (I report to them) | manager / boss |
| employee / report | employee (they report to me) | employee / report |
| co-founder, business partner, advisor/mentor, friend, in-laws/extended | cofounder, business, advisor, friend, family | none |

`employee` and `boss` also take an optional `role` (`sales|marketing|finance|managerial`, default `managerial`).
Gender is inferred from son/daughter/husband/wife/etc; send `gender` (`male|female`) for the rest.
Unknown relation => 422 `{error:"invalid_relation"}`.

## Person item (returned by every route)
```json
{
  "link_id": "uuid", "person_chart_id": "uuid",
  "relation": "child", "relation_detail": "son",
  "name": "Amik Singh", "gender": "male", "started_at": "...",
  "aliases": [{"id": "uuid", "alias": "Amik", "source": "name"}],
  "score": {"score": 71, "badge": "FLOW", "headline": "...", "compat_type": "child",
            "session_id": "uuid", "updated_at": "...", "access": "preview|null"}
}
```
`score` is the LATEST score for the CURRENT relation only (null if none yet). `access:"preview"`
means the usual compat slot rules apply (score/badge/headline only), same as `/compatibility/start`.
Use `link_id` for every edit/remove call.

## Endpoints
- `POST /people` body `{owner_chart_id, name, relation, relation_detail?, gender?, role?, birth_date, birth_time?, birth_city?, birth_country?, latitude?, longitude?, timezone?, aliases?: ["beta"], language?}`
  Creates the person chart, the link, the name aliases (full name + first name, plus any nicknames) and runs compat. Returns a person item (+ `created`).
- `GET /people/{owner_chart_id}` returns `{people: [person item], count}`. Current links only.
- `PATCH /people/{link_id}` body `{name?, gender?, birth_date?, birth_time?, birth_city?, birth_country?, role?, language?}`
  Edits the person's own chart (same chart, no duplicate on a birth-time change), recomputes it and re-scores.
  Returns the person item + `changed`, `recomputed`.
- `PATCH /people/{link_id}/relation` body `{relation, relation_detail?, role?, language?}`
  "Change relationship" (girlfriend to wife). Aliases and the person persist; compat re-runs with the new type; the old score is not returned. Returns the new person item, which carries a NEW `link_id` (the old one stops working: 404). Same relation again is a no-op (`changed:false`).
- `POST /people/{link_id}/aliases` body `{alias}` returns `{aliases:[...]}` (nicknames, max 60 chars).
- `DELETE /people/{link_id}/aliases/{alias_id}` returns `{success:true}`.
- `DELETE /people/{link_id}` removes the person: returns `{success:true, subchart_purged:bool}`.

## UI asks
Add Person form with relation picker + sub-choice and optional nickname field; Person screen with edit details,
"Change relationship", aliases list (add/remove), remove person. After a relation change, replace the
stored `link_id` with the one in the response.
