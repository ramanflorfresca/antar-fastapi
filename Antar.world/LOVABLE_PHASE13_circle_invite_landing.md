# Lovable prompt — Phase 13: the invite link is a localized signup landing

Paste everything under "PROMPT STARTS HERE" into Lovable, after Phases 9 to 12. UI only. The backend is built (branch `feat/circle-invite-landing`); no new tables.

Why this exists: the Circle link already works, but it read in the inviter's language and the landing carried no reason to join. Now the inviter picks the language the invitee will read it in, gets a ready-to-send note, and the landing sells the signup in the visitor's own language. Consent is unchanged: nothing exists about the invitee until they accept, so the landing shows copy and the inviter's first name only, never results.

## PROMPT STARTS HERE

You are working on the existing Antar web app, Circle screens. UI only; use the endpoints below; show strings as returned; do not publish; open a PR.

### 1. Inviter: share sheet
After `POST /api/v1/circle/invites` succeeds (the existing call), the Share sheet gains:
- A **language chip row** (on the last add step, before the invite is created) titled "Language {name} will read it in": English, Español, Português, Hinglish. Default = the inviter's current app language. Hindi (Devanagari) is not offered.
- The call now accepts an optional `invitee_language` (en | es | pt | hinglish). The response adds `share: { language, message }`. `message` is the paste-ready note, already containing the link, written in the invitee's language.
- Show `share.message` in a text bubble. Primary button **Send on WhatsApp** opens `https://wa.me/?text=<encodeURIComponent(share.message)>`; secondary **Copy link** and the native share sheet (`navigator.share({ text: share.message })`) where available.
- The language is chosen on the screen BEFORE the invite is created (the last add step), because it is stored on the invite. Do not mint a second link just to change language.
- Footer line: "Antar never contacts {name}. You send it from your phone." (EN/ES/PT/hinglish).

### 2. Invitee: landing at `/c/<code>`
- Detect the visitor's language from the browser (`navigator.language`: es*, pt*, hi-Latn or hi* -> hinglish only if the user picks it; otherwise en). Call `GET /api/v1/circle/invite/{code}?language=<detected>`.
- Show a **language chip row** at the top. Tapping a chip re-calls the same endpoint with that `language` and re-renders. Remember the choice in memory for the signup steps.
- Render from the response, no client text for these: `landing.headline`, `landing.sub`, `landing.bullets[]` (each with a check icon), button `landing.cta`, ghost link `landing.decline`, small print `landing.privacy`. Also use `relation.label` where the design shows the relation.
- `status`: `valid` shows the above. `used` or `expired` shows a calm "This link has been used or has expired. Ask {inviter_first_name} to send a new one." (EN/ES/PT/hinglish) with no CTA. A 404 shows the same expired state.
- **CTA** goes to signup/sign-in with the invite code and chosen language carried in app state (not in the URL as personal data), then birth details, then accept.
- **Not now** calls `POST /api/v1/circle/invite/{code}/decline` and shows a short thank-you. It needs no account.
- No results, scores, dates or guessed data on this page. Ever.

### 3. After signup: accept
- After the invitee has their own chart, call `POST /api/v1/circle/invite/{code}/accept` with `{ chart_id, claim_token?, share_day, language }` where `language` is the one they read the landing in. The backend saves it as their language only if their chart had none.
- Then route to the existing "Between us" page for that pair and render it in that language (send `language` on the pair calls).
- Errors: 409 `invite_used` / `cannot_invite_yourself`, 410 `invite_expired`, 403 `demo_chart` use the existing Circle error treatment.

### Rules
- Never show the inviter anything about the invitee beyond the existing Circle rules; never show the invitee the inviter's private reading.
- Do not reword backend strings. New UI-only strings (language row title, Send on WhatsApp, Copy link, expired state, thank-you, footer line) in English, Spanish, Portuguese and hinglish Roman.
- No emoji, no pricing, no plan names.

### Acceptance checks (verify and say so in the PR)
- Share sheet: choosing Español produces a Spanish note containing the link; WhatsApp opens with that exact text.
- Landing in a Spanish browser renders Spanish on first paint; tapping English swaps every landing string and keeps the choice through signup.
- `used` and `expired` links show the calm state with no CTA; Not now records nothing and needs no account.
- After accept, the Between us page opens in the chosen language and a brand-new account's language is that language.
- 375 px screenshots of: share sheet, landing in two languages, expired state.

### Out of scope (do not build)
Any teaser built from the invitee's data, Hindi Devanagari copy, auto-sending the link, any backend or API change.

## PROMPT ENDS HERE
