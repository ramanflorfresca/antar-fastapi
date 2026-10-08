# Lovable prompt — Phase 9: Circle (the People tab becomes two-sided)

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phases 7 and 8 (People list, add flow, relationship reading page). The backend is built, merged and live (PR 257); the owner runs `sql_circle.sql` once. Until that is run every Circle call degrades quietly (empty list, or a 503 `circle_unavailable` on writes), so this prompt can be built in parallel and must handle that state.

What is NOT in this prompt, and why:
- **Any matching of people by name, birth date, phone or email.** There is none, by design. A link is the only way two people connect. Do not build search, "people you may know", contact import or auto-link.
- **Sending the invite from Antar.** Antar never messages, emails or notifies the invitee. The inviter shares the link from their own phone (native share sheet or copy). No "send via WhatsApp/email from Antar" button.
- **Computing windows, overlaps, scores or confidence in the front end.** The API returns finished dated windows and finished sentences.
- **Group circles / a multi-person "council" Ask, push or WhatsApp reminders, "pending invite" notices for the invitee.** Deferred.
- **Pricing or plan text.** None, anywhere on these screens.

## PROMPT STARTS HERE

You are working on the existing Antar web app. Turn the **People** tab into **Circle**: a two-sided feature where a user can **invite** a person, the person opens a link, consents, enters their own birth details, and from then on **both** see a shared **"Between us"** page of dated windows where their two charts overlap. Today's private People keep working exactly as they do now. UI only: use the endpoints below, show strings exactly as returned, and do not compute or reword any reading. Do not publish; open a PR.

### 0. Ground rules (read first)
- **Tab and route:** rename the tab label to **Circle** (en "Circle", es "Círculo", pt "Círculo", hinglish "Circle"). New route `/circle`; keep `/people` as a redirect to `/circle` and keep `/people/:sessionId` (the private relationship reading) unchanged.
- **Auth for the calls below.** Signed in: send `Authorization: Bearer <token>`. Guest with a chart (no session): send header `X-Claim-Token: <antar_claim_token>` on the read/leave/sharing calls (it works only for an unclaimed chart; never put it in a URL, never log it). Creating, cancelling and resending an invite **require a signed-in user**; a guest sees the locked state (section 1).
- **Errors are `detail.error` codes** (HTTP 4xx/5xx with `{"detail":{"error":"…"}}`). Map each code to one calm line (listed per screen). Never show a red error box or the raw code.
- **Fail-open:** if `GET /api/v1/circle/{chart}` returns an empty `circle`, show the normal empty state. A 503 `circle_unavailable` on a write shows "Circle isn't available right now. Try again in a little while." and keeps what the user typed.
- **Copy:** every new static string below must exist in English, Spanish and Portuguese (Hinglish uses Roman script; Hindi falls back to English). Everything else comes from the API.
- **Privacy, enforced in the UI:** the other person's birth details, private reads, questions, notes and Ask history are **never** shown on any Circle screen, and no Circle screen links to them. Only first names, the relation, and the windows.

### 1. Circle home (`/circle`)
Call `GET /api/v1/circle/{chart_id}?language=<lang>`. Response: `{circle:[…], counts:{in_circle,invite_sent,private}, limits:{max_pending_invites,invite_valid_days}}`. Each item has a `state`:
- **`in_circle`** (they accepted): first name, `relation.label`, a small "Between us" chip showing the pair's best shared window only if you already have it (do not fetch it per row; just the name + relation + a chevron). Tap opens the **Pair page** (`/circle/:otherChartId`, section 4). If `their_day.shared` is true and `their_day.available` is true show `their_day.one_line` under the name; otherwise show nothing about their day.
- **`invite_sent`**: first name (what you typed), `relation.label`, status line from `status`: `pending` -> "Invite sent"; `expired` -> "Invite expired". **Never show "declined" or "ignored"**; the API deliberately does not tell you, and you must not guess. Tap opens the **Share sheet** (section 3) for that invite. If `can_resend` is false hide Resend.
- **`private`** (today's People, unchanged): name, `relation.label`, the existing badge/`today` glance, tap opens `/people/:sessionId` using `session_id`. These rows get a small, quiet **"Private"** tag. If the same person was invited, the API already shows them as the invite or the pair, not twice.

Order: In your circle first, then Invite sent, then Private. Section headers with counts ("In your circle · 2", "Invite sent · 1", "Private · 3"); hide an empty section. A pinned **"+ Add someone"** button opens the add flow (section 2).

Empty state (no items at all): one calm card: heading **"Your circle"**, body *"Add someone close to you. Invite them to see where your timing lines up, or keep them private."*, button **Add someone**.

**Guest state:** keep the Phase 2 locked state (muted "Sample" card + **Save your chart to add people**). Do not call the Circle endpoints without a chart.

### 2. Add flow (relation, then Invite or Keep private)
Reuse the Phase 7 add flow's first two screens unchanged: name ("What's their name?") and **"How are they related to you?"** from `GET /api/v1/compatibility/types?language=<lang>` (use the entry's `label`, send its `id` as the relation). Then a new last choice screen, **"How do you want to add {name}?"**, two large cards:
1. **Invite {name}** — sub-line *"They open a link, add their own birth details, and you both see where your timing overlaps. You decide when to share the link."* Recommended (first, accent edge).
2. **Keep {name} private** — sub-line *"You enter their birth details yourself. Only you see it. They are never told."* Continues into the existing Phase 7 steps and the existing compatibility start call, **unchanged**.

Choosing **Invite**: `POST /api/v1/circle/invites` body `{ "chart_id": "<yours>", "relation": "<the chosen id>", "first_name": "<first word of the name>", "language": "<ui lang>", "private_chart_id": "<only when inviting from an existing private person's card; else omit>" }`. Success returns `{invite_id, link, expires_at}` -> open the **Share sheet** (section 3). A "Invite instead" action on a private person's card calls the same endpoint with `private_chart_id` set to that person's `chart_id`; the private reading stays untouched and keeps working for you.
Errors: `409 already_invited` (response carries `detail.invite_id`) -> open that invite's Share sheet instead. `429 too_many_pending_invites` -> *"You have 10 invites waiting. Cancel one to add another."* `429 daily_invite_limit` -> *"That's the limit for today. Try again tomorrow."* `422 unknown_relation` / `first_name_required` -> go back to the step. `403 not_your_person` -> generic retry line. A guest tapping Invite is sent to the Save sheet first ("Save your chart to invite people").

### 3. Share sheet (an invite you sent)
Shown right after creating an invite, and when tapping an `invite_sent` row.
- Heading **"Invite {name}"**. Body: *"Share this link from your own phone. Antar doesn't contact them. It works once and expires in {invite_valid_days} days."* Show the link in a read-only field with **Copy** and a primary **Share** button (native share sheet via `navigator.share`, falling back to Copy). Suggested share text (the user can edit it in their share target): *"{inviter first name} invited you to compare timing on Antar: {link}"*.
- **Important:** the raw link exists **only in the create/resend response**. When opening a sheet from a list row there is no link to show. In that case show **Share again**, which calls `POST /api/v1/circle/{chart_id}/invites/{invite_id}/resend` (new link, the old one stops working, fresh {invite_valid_days} days) and then shows the new link. Never cache or store the link anywhere (no localStorage, no analytics, no URL params).
- Status line: `pending` -> "Waiting for {name}" with the expiry date from `expires_at`; `expired` -> "This invite expired." with **Share again**.
- **Cancel invite** (text button, confirm): `DELETE /api/v1/circle/{chart_id}/invites/{invite_id}`. The link stops working. `429 resend_limit` -> *"This invite has been resent as many times as allowed. Cancel it and make a new one."*
- Never say whether they opened or declined it.

### 4. Pair page — "Between us" (`/circle/:otherChartId`)
Call `GET /api/v1/circle/{chart_id}/pair/{other_chart_id}?scale=month&language=<lang>&tz_offset=<minutes>`. A **Month / Season** toggle sets `scale` (`month` | `season`) and re-calls. `404 not_in_circle` -> go back to `/circle` with a calm toast *"This isn't in your circle anymore."* (this is also what both people see after one leaves).

Layout, top to bottom (one column on phones, max width ~640 px centered on desktop, same type scale as the redesigned app):
1. **Header:** back arrow, **"Between us"**, then "{You} + {other_first_name} · {relation.label}".
2. **Headline card:** `headline.text` verbatim. If `headline.window` is null the text already says there is no shared open window; show it plainly with no empty-state illustration and no apology.
3. **Topics list:** for each entry in `topics` (already in the standard order): a row with `label`, and the earliest `best` window's `label` (dates) in the green "Best" style; a muted "Care" chip if `care` is non-empty. If `has_overlap` is false show the row's `note` verbatim, muted. Tap a topic row to expand all its `best` windows (green) and `care` windows (amber, caption **"One or both of you needs care"** from the API's care reasoning, do not invent your own). Each window shows `label` and `days`. **Never extend, merge, round or invent a window.**
4. **"Why this window" sheet:** tapping a window's info icon opens the same Why sheet the topic read uses, fed by that window's `reasoning` (`bullets`, `based_on`, `confidence.level`/`confidence.note`). The `reasoning` object has exactly the topic-read shape, so reuse the component.
5. **Their day:** a card only when `their_day.shared` is true. If `available` is true show `one_line` (and the band color as elsewhere); if shared but not available show nothing. When not shared, **do not show a card or any hint that they could share** (it would pressure them).
6. **Ask for two:** the `ask_chips` (up to 4: sign, money, work, love). Tapping one opens the normal Ask flow with `text` prefilled and sent exactly as a typed question (the backend answers from the shared windows).
7. **Between you (inviter only):** if `between_us.available` is true show the badge (`badge`, same colors as People) with the label **"Your earlier read"** and a link to `/people/:session_id`. When false, render nothing.
8. **Privacy controls** (a "Privacy" row that opens a sheet):
   - **Share my day with {name}** toggle, seeded from `my_sharing.share_day`, default off. Helper text: *"They'll see a one-line glance at your day, nothing else. You can turn it off any time."* Call `PUT /api/v1/circle/{chart_id}/sharing/{other_chart_id}` `{ "share_day": true|false }`; update optimistically and revert on error.
   - **Leave** (destructive, confirm): *"Leave this circle? The shared page disappears for both of you. Neither of your charts is deleted."* `POST /api/v1/circle/{chart_id}/pair/{other_chart_id}/leave`, then back to `/circle` with a toast *"You left."*

Do not display `pair_id`, chart ids, or `since` as user text. Do not show any number the API does not return (no scores, no percentages).

### 5. Invitee landing (`/c/:code`) — public, no login needed
This is the page the invited person lands on from a link like `https://antar.world/c/<code>`. It must work for: (a) a signed-out person with no Antar chart, (b) a signed-out person who already has a guest chart, (c) a signed-in person.

1. On load call `GET /api/v1/circle/invite/{code}` (no auth). Response: `{inviter_first_name, relation:{key,label}, status, language}`. **Use `language` as the page language** (it is the inviter's choice for this person), unless the visitor has already chosen one in the app. `404` -> render the same card as `used`.
   - `status: "valid"` -> continue.
   - `status: "used"` -> *"This link has already been used."* with a Go to Antar button.
   - `status: "expired"` -> *"This invite has expired. Ask {inviter_first_name} for a new one."* (If `inviter_first_name` is null just say "Ask them".)
2. **Welcome + consent screen:** heading *"{inviter_first_name} invited you to Between us"*, sub-line *"As {inviter_first_name}'s {relation.label}."* (`relation.label` is already phrased for the invitee). Three plain bullets:
   - *"You enter your own birth details. {inviter_first_name} never sees them."*
   - *"You both see only the dates where your timing overlaps, and each other's first name."*
   - *"You can leave any time. Nothing else is shared unless you choose."*
   A **Share my day with {inviter_first_name}** switch, **off** by default, with the same helper text as section 4.8. Primary **Continue**, secondary text link **No thanks** which calls `POST /api/v1/circle/invite/{code}/decline` (needs nothing; always succeeds) and shows a calm *"Okay. Nothing was shared."* with a Go to Antar link. Do not ask for a reason, do not show a confirm.
3. **Birth details:** if the visitor is signed in with a chart, skip this and use their primary chart (a small "Using your chart" line with **Use a different chart** only if they own more than one). Otherwise run the **existing birth-data flow** (Phase 1 / guest identity brief) to create a guest chart: `POST /api/v1/chart/create` with no auth, and store the returned `claim_token` as `antar_claim_token` and `chart_id` as `antar_chart_id`, exactly as that brief says. Do not ask for any extra field.
4. **Accept:** `POST /api/v1/circle/invite/{code}/accept` body `{ "chart_id": "<their chart>", "claim_token": "<only for a guest chart>", "share_day": <switch value> }`, with `Authorization: Bearer` when signed in. It is **idempotent**: a double tap or reload returns the same result, so disable the button while in flight but treat a repeat as success. Success `{status:"accepted", other_first_name, relation, …}` -> **Done** screen.
   Errors: `409 invite_used` -> the "already used" card. `410 invite_expired` -> the "expired" card. `409 cannot_invite_yourself` -> *"This invite is from your own account."* `404 chart_not_found` / `403` -> restart the birth step once, then a generic retry line. `403 demo_chart` -> *"The demo can't join a circle. Create your own chart first."* `503 circle_unavailable` -> the retry line.
5. **Done:** heading **"You're in {other_first_name}'s circle"**, body *"You'll both see where your timing lines up. You can change what you share any time."*, primary **See Between us** (navigates to `/circle/{other_chart_id}`), secondary **Save my chart** (guest only: opens the Save sheet; after Google/Apple sign-in the existing `/chart/claim` call runs unchanged; the pair does not change when the chart is claimed). A guest who hasn't signed in can already open the pair page using `X-Claim-Token`.

The landing page must **never** show: the inviter's birth details, chart id, anything about their readings, or whether anyone else was invited.

### 6. Check-backs (nothing new to build)
Shared windows are asked about later through the **existing** "Did it hold?" card (`GET /api/v1/chart/{id}/topic-checkbacks`, answer endpoint unchanged). The question text for a shared window comes from the API ("Your shared Money window … Did it hold for the two of you?"). Render it exactly like any other check-back. Do not add a separate flow.

### 7. Rules
- Show all reading text exactly as returned. Do not hard-code window dates, sentences, or confidence wording.
- Never reveal whether an invite was declined or ignored. Never reveal the other person's birth data, notes, private reads, questions or Ask history, anywhere.
- Never store or log invite links, codes or claim tokens (no localStorage for the link, no console, no analytics events with the URL; redact `/c/<code>` in any analytics page-view path as `/c/:code`).
- No prices, plans or upgrade prompts. No "send from Antar" buttons. No contact import or search.
- Keep every existing People behaviour (private add, delete/rename, notes, MARK DONE) exactly as it is.

### Edge cases
- Inviter's list refreshes after: create, resend, cancel, leave, and when the app returns to the foreground.
- A pair whose other chart was deleted simply disappears from the list (the API drops it); the pair page returns `404 not_in_circle`.
- The same person opening their own invite link while signed in as the inviter sees the "from your own account" card.
- Loading uses the existing skeleton; errors are one calm line with Retry.
- Works at 375 px and desktop, respects the iOS safe area, and the native shell (Capacitor) opens `https://antar.world/c/<code>` links in the app when installed (universal/app link) and in the browser otherwise.

### Acceptance checks (verify and say so in the PR)
- Circle home shows the three sections from one `GET /circle/{chart}` call; private rows open the old reading; no row ever says "declined".
- Add flow: Invite creates a link via `POST /circle/invites` and opens the Share sheet; Keep private sends the exact same payload as before (compare in the network tab).
- Share sheet: link shown only right after create/resend; Share again/Cancel work; the link is not in storage, console or URL.
- Pair page: month/season toggle, Best (green) and Care (amber) windows verbatim, Why sheet fed by `reasoning`, no overlap shows the API's `note`, Their day card only when shared, Ask chips send prefilled questions, share-day toggle and Leave work, and a left pair 404s to `/circle`.
- Invitee landing: valid / used / expired states; decline records nothing and needs no login; accept works for a guest (claim token) and a signed-in user, is safe on double tap, and ends on the Done screen; the guest can claim later and the pair persists.
- en / es / pt render; hinglish Roman; hi falls back to English.
- Screenshots at 375 px of: Circle home (all three sections), Share sheet, Pair page (with and without overlap), Why sheet, Privacy sheet, invitee landing (valid, used), consent, Done; plus one desktop pair page — attached to the PR.

### Out of scope (do not build)
Search or auto-matching of people, contact import, sending invites from Antar (email/WhatsApp/SMS), groups or a multi-person Ask, push/WhatsApp reminders, any score/percentage, any backend change, any pricing text.

## PROMPT ENDS HERE
