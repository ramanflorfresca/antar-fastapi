# Lovable prompt — Connect WhatsApp (consent screen, onboarding step, Settings, Ask banner)

Paste the block below into Lovable (Build mode). Backend is live; **run `sql_wa_marketing_consent.sql`
first** (Lovable SQL) so the offers opt-in can be stored.

```
Build "Connect WhatsApp" for the Antar web app (the iOS/Android apps load this same site). The backend owns
all logic and consent records — the UI only shows the choices and calls the API. Never send a phone number
from the app: the user proves their number by sending a message from WhatsApp.

API base: https://antar-fastapi-production.up.railway.app (send the Supabase JWT as Authorization: Bearer).

STATUS — GET /api/v1/messaging/whatsapp/status
 -> { available, linked, number_last4, chart_name, alerts_opt_in, marketing_opt_in,
      consent_version, marketing_consent_version, antar_number }
 If available === false, hide every WhatsApp entry point.

## 1. The consent sheet (ONE screen, used everywhere)
Title: "Get your answers on WhatsApp". Short line: "Ask Antar anything from WhatsApp — same reading as the app."
Three controls, in this order:
  [x] REQUIRED checkbox, unticked by default, Connect disabled until ticked:
      "I agree to the Terms and Privacy Policy and to receive my answers and check-ins from Antar on WhatsApp."
      (Terms and Privacy are links.)
  ( ) OPTIONAL toggle, OFF by default: "Alerts — tell me when a strong window opens for me."
  ( ) OPTIONAL toggle, OFF by default: "Offers & news — occasional updates and offers from Antar."
Small print: "You can turn alerts or offers off anytime in Settings, or by sending 'stop alerts' / 'stop offers'.
Send STOP to disconnect."
Rules: the two optional toggles must NEVER be pre-ticked, never bundled into the required box, never required
to continue. Do not show prices here.

Primary button "Connect WhatsApp":
  POST /api/v1/messaging/link/start
  { channel: "whatsapp", consent_accepted: true, consent_version: <status.consent_version>,
    alerts_opt_in: <toggle>, marketing_opt_in: <toggle> }
  -> { deep_link, code, expires_in_minutes, instructions }
  On a PHONE (narrow screen or Capacitor.isNativePlatform()): window.location.href = deep_link (opens WhatsApp
  with "LINK <code>" typed in; the user taps Send).
  On a LAPTOP / desktop: show a QR code of deep_link (use the `qrcode.react` package, 220px, with a white quiet
  zone) + the text "Scan with your phone's camera — WhatsApp opens with a message ready; tap Send." + a small
  "Or message +<antar_number>: LINK <code>". Show a 15-minute countdown from expires_in_minutes.
  Then poll GET /status every 3s (up to 15 min) until linked === true -> success state:
  "Connected ✓ — WhatsApp …<number_last4> reads <chart_name>'s chart." + a button "Open WhatsApp".
  400 { error: "consent_required" } -> re-show the sheet (the wording changed); never retry silently.

## 2. Arriving from WhatsApp (people who messaged Antar first)
Route /wa/connect?t=<token> (the bot sends this link — the backend env WHATSAPP_CONNECT_URL points here). If signed out: sign in / sign up first, then return
here keeping t. Show the SAME consent sheet, but the button calls:
  POST /api/v1/messaging/whatsapp/connect
  { token: t, consent_accepted: true, consent_version, alerts_opt_in, marketing_opt_in }
  -> { linked: true, number_last4 } -> success state. 400 "link expired" -> "This link expired — send any message
  to Antar on WhatsApp to get a new one."

## 3. New users — onboarding step
After the chart is created and the first reading shows, ONE optional card: "Get your answers on WhatsApp too"
[Connect] [Not now]. Connect opens the consent sheet. It must be skippable; never block onboarding on it.
Show it once; if skipped, don't show it again in onboarding.

## 4. Existing users
- Settings → "WhatsApp" row: not linked -> "Connect" (opens the sheet). Linked -> "Connected …<last4>" with
  three controls:
    Alerts toggle  -> POST /api/v1/messaging/whatsapp/alerts { enabled }
    Offers & news toggle -> POST /api/v1/messaging/whatsapp/marketing { enabled }
    "Disconnect" (confirm) -> POST /api/v1/messaging/whatsapp/unlink
  Toggles reflect status.alerts_opt_in / status.marketing_opt_in; re-fetch status after each change.
- On the Ask screen, a dismissible one-line banner for users who are NOT linked: "Ask Antar on WhatsApp →"
  opens the sheet. Show at most once a week; never after they dismiss it twice.

## Rules
- Never collect or display the full phone number; only number_last4.
- Never pre-tick anything. The required box and the two optional toggles are separate controls.
- Loading/skeleton on status; friendly one-line errors; no raw JSON.
- data-testid: wa-consent-required, wa-alerts-toggle, wa-offers-toggle, wa-connect, wa-qr, wa-status,
  wa-disconnect, wa-onboarding-card, wa-ask-banner.
```

## Notes for Raman (not part of the prompt)
- Consent is captured **in the app** and stored on the link row with time + wording version
  (`consent_version`, `marketing_consent_version`) — your evidence for Meta / regulators.
- Marketing templates can't be sent to anyone who didn't tick Offers: `wa_templates.send` blocks a
  MARKETING-category template unless the recipient's link opted in under the current wording.
- Get the final consent wording reviewed by a lawyer (US/TCPA, India/DPDP, Brazil/LGPD, Colombia/Argentina).
- The deep link uses `TWILIO_WHATSAPP_FROM`, which is still the Twilio sandbox number until your own number is
  connected to the WhatsApp Business Account.
- **Path 2 (people who message Antar first) is OFF in production today**: `WHATSAPP_LINK_SECRET` and
  `WHATSAPP_CONNECT_URL` are unset in Railway, so the bot currently tells unknown numbers to connect from the
  app. Once Lovable ships `/wa/connect`, set `WHATSAPP_CONNECT_URL=https://antar.world/wa/connect` and
  `WHATSAPP_LINK_SECRET` (any long random string) in Railway to turn it on.
