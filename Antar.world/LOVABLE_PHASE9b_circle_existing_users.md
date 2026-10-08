# Lovable prompt — Phase 9b: invitee who already has an Antar account

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phase 9 (Circle) is built. UI only: no backend change and no new endpoint. The backend already accepts an invite with a signed-in user's own chart (`POST /api/v1/circle/invite/{code}/accept` with `Authorization: Bearer` and that chart's `chart_id`).

Why this exists: on the deployed invitee landing (`/c/:code`) there is no way to say "I already have an account". A person who has an Antar account but opens the link signed out (the usual case: WhatsApp's in-app browser, a new phone, a different browser) is sent to the birth-details form and ends up with a **second, duplicate guest chart**. The pair then hangs off that duplicate and not off their real chart. This prompt closes that gap.

What is NOT in this prompt, and why:
- **Any matching of the invitee to an account** (by name, phone, email, birth data). None, by design. The link is the only proof; the person chooses to sign in.
- **A notification to the invitee** ("you have a pending invite"). Antar never contacts them.
- **Changes to the inviter side, the pair page, or the backend.**

## PROMPT STARTS HERE

You are working on the existing Antar web app. Fix the invitee landing `/c/:code` so a person who already has an Antar account joins with their **real chart** and never gets a duplicate. UI only; use the existing endpoints; show strings exactly as returned; do not publish; open a PR.

### Who can arrive, and what each sees
Decide in this order when the page has loaded `GET /api/v1/circle/invite/{code}` with `status: "valid"` (the used / expired cards are unchanged):

1. **Signed in (a Supabase session exists).** Skip any birth-details step. Use the account's **primary chart** (`profiles.primary_chart_id` / the active chart the app already uses). If the account has **more than one chart**, show a small step before Continue: heading *"Which chart should join {inviter_first_name}'s circle?"*, a list of the account's charts by name (first name only), the primary one preselected, and a **Continue** button. Never ask a signed-in person for birth details. Then the normal consent screen, then accept (below).
2. **Signed out, no local chart.** The consent screen has **Continue** (new here: goes to the birth-details form as today) and, directly under it, a text button **"Already on Antar? Sign in"** (see section 2).
3. **Signed out, with a local guest chart** (`antar_chart_id` + `antar_claim_token` in storage). Show **Continue** (joins with that guest chart, as today) and the same **"Already on Antar? Sign in"** button. Add one muted line under them: *"Signing in uses your account's chart instead of the one on this device."*

Never auto-pick a path for a signed-out visitor, and never show the sign-in button to someone who is already signed in.

### 2. "Already on Antar? Sign in"
- Opens the existing Google / Apple sign-in (same order and components as the Save sheet and `/auth`; Google/Apple first). Do **not** add email/password here.
- Before leaving the page, persist ONLY the return target: `antar_return_to = "/c/<code>"` (the code is already in the URL; do not store the invite link anywhere else, do not log it, do not put it in analytics; report page views as `/c/:code`). In the iOS/Android shell, persist it **before** opening the external browser and read it on the return deep-link.
- **Do NOT call `POST /api/v1/chart/claim` in this path**, even if a guest chart is in storage. The visitor chose their existing account; claiming the leftover guest chart would add a second chart to it. Leave the guest chart where it is (the normal Save-my-chart flow can still claim it later, only if the person asks).
- After sign-in succeeds, restore the session, navigate to `antar_return_to`, clear it, and continue as case 1 above (primary chart, or the chart picker if there are several). The consent screen shows again with the share-my-day switch **off**.
- If sign-in is cancelled or fails, return to the consent screen on the same invite with one calm line *"Sign-in didn't finish. You can try again or continue as new."* Nothing was accepted.
- If the signed-in account turns out to be the inviter's own (`409 cannot_invite_yourself` on accept) show *"This invite is from your own account."* and a Go to Antar button.

### 3. Accepting (all paths)
`POST /api/v1/circle/invite/{code}/accept` with `{ "chart_id": "<the chosen chart>", "share_day": <switch value> }`:
- Signed-in paths: send `Authorization: Bearer <access token>` and **no** `claim_token`.
- Guest-chart path: unchanged (`claim_token` from storage, no Authorization).
It is idempotent (double tap, reload, or returning from sign-in returns the same pair). On success show the existing **Done** screen: *"You're in {other_first_name}'s circle"* with **See Between us** (-> `/circle/{other_chart_id}`). For a signed-in person the secondary **Save my chart** button is **not shown** (they already have an account).
Errors, as in Phase 9: `409 invite_used`, `410 invite_expired`, `409 cannot_invite_yourself`, `403 demo_chart`, `403 not_your_chart` (re-fetch the account's charts once, then a calm retry line), `503 circle_unavailable`.

### 4. The inviter's name before sign-in
The consent screen already shows *"{inviter_first_name} invited you to Between us. As {inviter_first_name}'s {relation.label}."* so the person knows who it is from before deciding to sign in. Keep that visible on the sign-in step's return as well (do not reload to a blank screen).

### Rules
- No new endpoints and no new request fields. No search, no suggestions, no "we found your account".
- Never show another person's birth details, chart ids, or whether anyone else was invited.
- Never store or log the invite code outside the URL and `antar_return_to`; clear `antar_return_to` once used.
- Copy: the new strings (*"Already on Antar? Sign in"*, the guest-chart helper line, the chart-picker heading, the sign-in-didn't-finish line) in English, Spanish and Portuguese; hinglish in Roman script; Hindi falls back to English.
- Everything about Phase 9 screens not mentioned here stays as it is.

### Edge cases
- A signed-in person with one chart sees no picker and no extra step: Continue accepts with that chart.
- Opening the link on a device where a *different* person is signed in is not detectable; the signed-in account is used. (They can sign out and reopen the link; do not add a "not you?" step.)
- Returning from sign-in after the invite expired or was used shows the matching card.
- Back button after sign-in lands on the consent screen, never on `/auth`.
- Works at 375 px and desktop; respects the iOS safe area; Capacitor shell opens `https://antar.world/c/<code>` in the app when installed.

### Acceptance checks (verify and say so in the PR)
- Signed in, one chart: open `/c/<code>` -> consent -> Continue -> accepted with the existing primary chart; **no** `POST /chart/create`, **no** `POST /chart/claim` in the network tab; the account still has the same number of charts.
- Signed in, several charts: the picker appears with the primary preselected; the chosen chart is the one sent as `chart_id`.
- Signed out, no local chart: "Already on Antar? Sign in" -> Google/Apple -> back on `/c/<code>` signed in -> accepted with the primary chart; no duplicate chart created (compare chart counts before and after).
- Signed out with a leftover guest chart: choosing Sign in does **not** call `/chart/claim`; choosing Continue still works exactly as before (claim token path).
- The share-my-day switch is off after returning from sign-in; the pair page opens for the signed-in user with the same windows the inviter sees.
- Cancelling sign-in returns to the consent screen with the calm line; nothing was accepted.
- Screenshots at 375 px of: the consent screen with the new link, the chart picker, the sign-in-didn't-finish line, and the Done screen for a signed-in user (no Save button) are attached to the PR.

### Out of scope (do not build)
Account matching or suggestions, notifications to the invitee, email/password sign-in on this page, any change to the inviter screens, the pair page, or any backend/API.

## PROMPT ENDS HERE
