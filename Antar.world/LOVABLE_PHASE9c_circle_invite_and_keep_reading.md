# Lovable prompt — Phase 9c: invite AND keep your own reading (add now, invite later)

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phase 9 and 9b. UI only. One small backend field is already live (`private_read` on Circle list items); no new endpoint.

Why this exists: today the add flow forces a choice. **Invite** creates nothing for the person until they accept (no chart, no reading), and **Keep private** means no invite. The owner wants both: add a cofounder, get **your own reading right away**, and invite them to the shared "Between us" page too, now or later.

How it works (no change to consent): the private reading is built only from the birth details **you** type; it stays yours. The invite is separate: when they accept they enter **their own** details, and the shared page uses their real chart. Your private reading is never shown to them, and it is never turned into the shared page.

## PROMPT STARTS HERE

You are working on the existing Antar web app, Circle screens. UI only; use the endpoints below; show strings as returned; do not publish; open a PR.

### 1. Add flow: three choices instead of two
On the last add screen ("How do you want to add {name}?") show:
1. **Invite {name}** (as today): link only, no reading until they join.
2. **Keep {name} private** (as today): you enter their details, only you see it.
3. **Both: read now, invite too** (new, between the two, recommended when the relation is Cofounder, Business partner, Friend, Partner, Spouse, Sibling): sub-line *"You get your own reading now from the details you enter. They get a link to join, and you both see Between us once they do."*
Choosing **Both**: run the existing private add steps (birth details, then the existing compatibility start call, unchanged). On success you have the new person's `chart_id` (the connection's chart id the People list already uses). Then immediately call `POST /api/v1/circle/invites` with `{ chart_id: <yours>, relation: <chosen id>, first_name: <first name>, language, private_chart_id: <that new person's chart_id> }` and open the **Share sheet**. If the invite call fails, keep the private person (nothing is lost) and show *"Added privately. We couldn't create the invite. You can invite {name} later."* with a retry.

### 2. Invite later, from a private person
On a private person's card (list row menu and the person detail header) add **"Invite {name} to Between us"**. It opens a small confirm sheet: *"Send {name} a link. Your private reading stays yours and they never see it."* then calls `POST /api/v1/circle/invites` with `private_chart_id` set to that person's `chart_id`, the relation already on the card, and their first name; then the Share sheet. `409 already_invited` -> open that invite's Share sheet instead (`detail.invite_id`).

### 3. Keep the reading reachable (the new `private_read` field)
`GET /api/v1/circle/{chart_id}` now returns, on `invite_sent` and `in_circle` items you created from a private person, a **`private_read`** object: `{chart_id, session_id, score, badge, compat_type, today, note}` (otherwise `null`; it is **never** present for the person who accepted). Use it so inviting never hides your reading:
- On the **Invite sent** row, show the same small badge and note line the private row showed (from `private_read.badge` / `.note`), and a secondary action **"Open my reading"** -> `/people/{private_read.session_id}` (the existing relationship page). Tapping the row itself still opens the Share sheet.
- On the **In your circle** row and the pair page header, show a link **"My private reading"** -> the same page, only when `private_read` is non-null. The pair page's existing "Your earlier read" card (`between_us`) stays as it is.
- The person is shown **once** (as the invite or the pair), never also as a Private row. The API already does this.
- If the private person is later removed, `private_read` becomes `null` and the links disappear; the invite keeps working.

### Rules
- Never show a private reading, note, score or birth detail to the invitee, and never on the pair page's shared parts.
- Do not auto-send anything: Antar never contacts the invitee; the inviter shares the link from their own phone.
- Do not reword readings. New strings in English, Spanish and Portuguese (hinglish Roman; Hindi falls back to English): the third choice and its sub-line, "Invite {name} to Between us" and its confirm line, "Open my reading", "My private reading", the invite-failed line.
- Everything else in Phases 9 and 9b is unchanged.

### Edge cases
- Relations where a shared reading makes little sense (Child, Parent) still allow Both; do not hide it.
- A person already in the circle (accepted) has no "Invite" action.
- Expired invite row keeps showing "Open my reading"; **Share again** mints a new link as before.
- Works at 375 px and desktop; loading and error states as in Phase 9.

### Acceptance checks (verify and say so in the PR)
- **Both** creates the private person (same payload as the old add) and the invite in sequence; the Share sheet opens; the list then shows ONE row (Invite sent) with the badge/note and "Open my reading" that opens the old reading page.
- "Invite {name} to Between us" on an existing private person creates the invite with `private_chart_id`; the Private row becomes the Invite sent row; the reading is still reachable.
- After the person accepts, the row is In your circle with "My private reading"; the invitee's own list shows no such link.
- Invite failure after a successful private add keeps the person and offers a retry.
- Screenshots at 375 px of: the three-choice screen, the confirm sheet, an Invite sent row with "Open my reading", and an In your circle row with "My private reading".

### Out of scope (do not build)
Turning a private reading into the shared page, sharing a private reading with the invitee, auto-sending the link, any backend or API change.

## PROMPT ENDS HERE
