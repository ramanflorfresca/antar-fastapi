# Lovable brief — "Continue with WhatsApp" sign-in (UI only)

**Rule:** the backend owns all logic. Build UI + wiring to the two endpoints below. Do NOT generate codes, validate
numbers, create users, or store anything about the code/number yourself.

Backend: antar-fastapi PR #233 (needs `sql_wa_login_codes.sql` run first). Until it is, `start` returns 503 → hide the button.

## What the user experiences
On the login screen, next to Google / Apple, a third option: **Continue with WhatsApp**.
- **Desktop:** click → a card shows a QR code ("Scan with your phone's camera"). They scan, WhatsApp opens with a
  pre-typed message, they tap Send. The page signs them in by itself within ~2 seconds.
- **Phone:** tap → WhatsApp opens directly with the pre-typed message; they tap Send, come back to the browser/app,
  and are signed in. (Same code path; just a button instead of a QR.)
No typing, no email, no link in the chat.

## Endpoints

### 1) Start — `POST /api/v1/auth/whatsapp/start`  (public, no auth header)
Optional query `?country=IN` (ISO-2, only if you already know it; the backend also reads the edge/IP country).
Response:
```json
{ "code": "K7Q2MX",
  "browser_token": "…secret, keep in memory only…",
  "expires_in_s": 120,
  "deep_link": "https://wa.me/17322035001?text=Hi%20Antar!%20Sign%20me%20in%3A%20K7Q2MX",
  "qr_text": "https://wa.me/…",          // render THIS as the QR
  "prefilled_text": "Hi Antar! Sign me in: K7Q2MX",
  "antar_number": "+17322035001", "country": "US" }
```
Errors: `503` = not enabled / not set up → hide the WhatsApp option. `429` = too many tries → "Too many attempts. Wait a few
minutes, or use Google / Apple."

### 2) Poll — `POST /api/v1/auth/whatsapp/poll`  body `{ "code": "...", "browser_token": "..." }`
Call every **2 seconds** while the card is open. Responses:
- `{"status":"pending"}` → keep waiting.
- `{"status":"expired"}` → stop polling; show the expired state (below). (Also what a wrong token returns — treat identically.)
- `{"status":"approved","token_hash":"…","type":"magiclink"}` → **one-time**. Immediately call
  `supabase.auth.verifyOtp({ token_hash, type })` with exactly those two values. Success = signed in; then continue
  the normal post-login routing (**/ask is the landing screen**, same as Google/Apple).
Stop polling after approved/expired, on card close, and when the tab is hidden for >30s (resume on focus if still < 120s).

## States (one card, same footprint as the other connect cards)
1. **Waiting** — QR (desktop) or "Open WhatsApp" primary button (phone, detect by touch/UA) + secondary "Show QR instead".
   Under it: "Tap **Send** in WhatsApp — I'll sign you in here." A small countdown ring/“Code valid 1:48”.
   Also a tiny link "Open WhatsApp manually" revealing `antar_number` and `prefilled_text` for anyone whose camera/link fails.
2. **Success** — brief check + "Signed in" (≤1s), then route.
3. **Expired** (120s or `expired`) — "That code timed out." + button **Get a new code** (calls start again; new token).
4. **Not set up / error** — hide the option entirely on 503; on network error show "Couldn't reach Antar — try again."
5. **No account for this number** is handled inside WhatsApp (the bot tells them to say "hi" and sets them up in chat).
   The browser just keeps waiting → expires. Add one line on the Waiting card: "New here? Send the message and I'll
   set you up in the chat."

## Copy (EN; add ES / PT / Hinglish through your existing i18n — keep the app's current language logic)
- Button: **Continue with WhatsApp**
- Heading: "Sign in with WhatsApp"
- Helper: "Scan with your phone's camera, then tap Send. No password, no email."
- Waiting: "Waiting for you to tap Send in WhatsApp…"
- Expired: "That code timed out." / "Get a new code"
- Privacy line under the card: "We only use your number to recognise your account." (no legal text here)

## Passkey step (after a successful WhatsApp sign-in only, once per device)
A dismissible sheet: "Use Face ID / fingerprint next time?" → [Yes, set it up] [Not now].
Use Supabase passkey/WebAuthn enrollment if enabled for the project; if it isn't, **skip this step silently** — do not
build a custom WebAuthn flow. "Not now" → remember per-device in localStorage (try/catch, UI-only preference).
Never block routing on it.

## Don'ts
- Don't persist `browser_token` or `code` anywhere (no localStorage/cookies/URL/query-string); keep them in component memory only.
- Don't log them to console/analytics.
- Don't show the QR on a card that is no longer polling (expired) — replace it with the Expired state.
- Don't call poll again after `approved` (the token_hash works once).
- Don't add consent checkboxes — consent happens inside WhatsApp.
- Don't mention prices/plans anywhere on this surface.
- Don't change the existing Google/Apple flows or the post-login destination.

## Accessibility / layout
- QR has `alt`/aria-label "QR code to sign in with WhatsApp"; the manual fallback is reachable by keyboard.
- Countdown announced politely (aria-live="polite", not every second — on expiry only).
- Works at 375px; button ≥ 44px tall; respects reduced-motion (no pulsing ring).

## Acceptance checklist
- [ ] Desktop: scan → Send → signed in within ~2–4s, lands on /ask
- [ ] Phone: button opens WhatsApp prefilled; Send → return → signed in
- [ ] Waiting 120s with no Send → Expired state → "Get a new code" works
- [ ] Reusing/refreshing after approval does not log in twice
- [ ] 503 hides the WhatsApp option; 429 shows the wait message
- [ ] No code/token appears in URL, storage, or console
