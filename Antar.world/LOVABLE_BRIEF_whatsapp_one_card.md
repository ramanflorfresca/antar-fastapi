# Lovable brief — ONE WhatsApp card (signed-in app: web + Android)

**Supersedes** `LOVABLE_BRIEF_connect_whatsapp.md` for everything inside the signed-in app (onboarding step, login
popup, Settings row): build ONE component and reuse it everywhere. The separate sign-in-screen option is still
`LOVABLE_BRIEF_continue_with_whatsapp.md` (different surface: the user isn't signed in yet).

**Rule:** the backend owns all logic. UI + wiring only. Never build your own connected/not-connected logic, never
store phone numbers, codes or links, never add consent checkboxes (consent happens inside WhatsApp).

## The idea
Talking to Antar on WhatsApp should feel like texting your astrologer. The card has ONE job: show whether that
chat is open, and give ONE obvious button.

## One endpoint drives it
`GET /api/v1/messaging/whatsapp/status?country=<ISO2 optional>` (Authorization: Bearer). Poll/refresh: on mount, on
app foreground, and every 3s for up to 2 min while the "Waiting" state is showing. Fields you use:
```json
{ "state": "unavailable | not_connected | connected",
  "number_last4": "4821",          // only when connected
  "chart_name": "Raman",           // only when connected
  "antar_number": "+17322035001",  // display, e.g. "Antar on WhatsApp · +1 732 203 5001"
  "open_chat_link": "https://wa.me/17322035001",   // for Open chat
  "prompt": { "show": true } }     // popup only; see below
```
Render ONLY from `state`. `unavailable` → render nothing at all.

## Three states, one card (same footprint everywhere)

### A) `not_connected` — "Talk to Antar on WhatsApp"
- Headline: **Ask Antar on WhatsApp**
- Sub: "Like texting your astrologer. Ask anything, any time."
- **Phone / Android app:** primary button **Connect** → `POST /api/v1/messaging/link/start`
  body `{ "channel": "whatsapp", "country": "<ISO2 if known>" }` (Bearer) → open `deep_link` (WhatsApp opens with the
  message pre-typed; the person only taps Send).
- **Desktop web:** same call, render `qr_text` as a QR + "Scan with your phone's camera, then tap Send." + a small
  "Open on this computer" link to `deep_link`.
- After the tap/scan, switch to **Waiting** (below). Do not show consent checkboxes or Terms text; WhatsApp asks.
- Code is valid ~`expires_in_minutes`; if it lapses, replace QR with "Get a new code" (call link/start again).

### B) Waiting (UI state only, still `not_connected` from the API)
"Tap **Send** in WhatsApp — I'll connect you here." Spinner-free (subtle dots; respect reduced motion). Keep
refreshing status. The moment `state` becomes `connected` → state C with a brief success flourish (≤1s).
Give up waiting after 2 min → back to A with "Didn't go through? Try again."

### C) `connected`
- A green dot + **Connected · ••••{number_last4}** and a subtitle **Reading {chart_name}'s chart**.
- ONE primary button: **Open chat** → `open_chat_link` (new tab / WhatsApp app). No code, no pre-typed text.
- Under it, a muted line: "Just type your question. Voice notes work too."
- Overflow menu (⋯): **Alerts** toggle, **Offers & news** toggle (existing endpoints
  `POST /whatsapp/alerts`, `POST /whatsapp/marketing` — body `{enabled:boolean}`), **Disconnect**
  (`POST /whatsapp/unlink`, confirm sheet: "Antar will stop messaging you on WhatsApp. You can reconnect any time.").
  Never show the full number.

## Where the card appears (same component)
1. **Settings** — permanent row/section (all three states).
2. **Onboarding, after the chart is built** — one skippable step (state A only; skip → never nag during onboarding).
3. **Popup, once per account** — ONLY when `prompt.show === true`. Show the card in a modal. The backend records
   "shown/clicked" itself; on dismiss call the existing dismiss endpoint you already use for the popup. Never re-show
   if `prompt.show` is false. Never show to a connected user.
4. **Ask screen** — NO banner or card above the composer (App Store 4.3(b): /ask stays the clean landing screen).
   The only Ask-screen entry is the existing Settings/menu route.

## Copy (EN; use the app's i18n for ES / PT / Hinglish)
- Not connected: "Ask Antar on WhatsApp" / "Like texting your astrologer. Ask anything, any time." / **Connect**
- Waiting: "Tap Send in WhatsApp — I'll connect you here."
- Connected: "Connected · ••••4821" / "Reading Raman's chart" / **Open chat**
- Hint: "Just type your question. Voice notes work too."
- Failure: "Didn't go through? Try again."
Do not mention prices/plans anywhere on this card.

## Don'ts
- No logic about linked/unlinked beyond reading `state`.
- Don't store or log `code`, `deep_link`, `qr_text` (memory only).
- Don't create a second component for Settings vs onboarding vs popup — one component, a `variant` prop at most.
- Don't add anything to /ask.
- Don't change Google/Apple sign-in or post-login routing (/ask).

## Accessibility / layout
- 375px first; button ≥ 44px; QR has aria-label "QR code to connect Antar on WhatsApp".
- Status changes announced once via aria-live="polite".
- Works inside the Capacitor Android shell (it loads antar.world): `deep_link` must open via a normal anchor
  `target="_blank" rel="noopener"` so WhatsApp handles it.

## Acceptance checklist
- [ ] `state:"unavailable"` renders nothing
- [ ] Not connected → Connect → WhatsApp opens pre-typed → Send → card flips to Connected without a manual refresh
- [ ] Connected shows last-4 + chart name; **Open chat** opens WhatsApp with no code
- [ ] Alerts / Offers toggles and Disconnect work; full number never visible
- [ ] Popup appears once per account only when `prompt.show` is true
- [ ] Nothing added to the Ask screen
- [ ] Same component in Settings, onboarding step and popup
