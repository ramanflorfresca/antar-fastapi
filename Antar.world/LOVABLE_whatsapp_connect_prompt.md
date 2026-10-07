# Lovable prompt — Connect WhatsApp (onboarding step + login popup + Settings)

Flow (owner, 2026-10-06): **one tap / one scan. No checkboxes in the app.** The app asks the backend for a
personal connect link; the backend picks Antar's WhatsApp number from the person's country (India → +1 978 213
1475, everyone else → +1 732 203 5001). On a phone the link opens WhatsApp with "Hi Antar! Connect my account: K7Q2MX" already typed → tap Send.
On a computer we show the same link as a QR → scan with the phone camera → WhatsApp opens → Send. Antar then asks
the person to accept Terms + Privacy IN WhatsApp, then asks two optional questions (alerts, offers). Done.

```
Build "Connect WhatsApp" for the Antar web app (the Android / iOS apps load the same site). The backend owns all
logic: which number, the code, consent. The UI only asks for a link and shows it. Never ask for or show a phone
number field.

API (Supabase JWT as Authorization: Bearer):
  GET  /api/v1/messaging/whatsapp/status  -> { available, linked, number_last4, chart_name, ... }
  POST /api/v1/messaging/link/start  body { channel: "whatsapp", country: <ISO-2 from the device locale if known> }
       -> { deep_link, qr_text, antar_number, code, expires_in_minutes }

THE CONNECT CARD (one reusable component, used in 3 places below)
  Title "Get your answers on WhatsApp". One line: "Ask Antar anything from WhatsApp — same reading as the app."
  Small line: "WhatsApp will ask you to accept our Terms and Privacy Policy before anything is sent."
  On a PHONE (narrow screen or Capacitor.isNativePlatform()):
     big button "Connect WhatsApp" → call link/start → window.location.href = deep_link.
     (WhatsApp opens a chat with Antar's number with "Hi Antar! Connect my account: K7Q2MX" already typed —
     the person never types or looks up a number; they just tap Send.)
  On a COMPUTER: call link/start when the card opens and show qr_text as a QR (qrcode.react, 220px, white quiet
     zone) with: "Scan with your phone camera — WhatsApp opens with a message ready. Tap Send." and a small
     "or open https://wa.me/… on your phone" link (the deep_link). Show a 15-minute countdown; "Get a new code"
     when it expires.
  While it's open, poll GET /status every 3s; when linked === true → success: "Connected ✓ — finish in WhatsApp
     (accept the terms there)." and close after 2s. Never show the full number; only antar_number as text.

PLACE 1 — NEW USERS (onboarding)
  Right after the birth details are saved and the first reading is shown, show the connect card as an onboarding
  step "Stay in touch on WhatsApp" with [Connect WhatsApp] and a quiet "Skip for now". It must be skippable.

PLACE 2 — EXISTING USERS (one-time login popup)
  After sign-in on web / Android / iOS, read GET /status. Show the connect card as a centred modal ONLY when
  status.prompt.show === true (the backend decides: once per account, never for connected users).
  When it appears: POST /api/v1/messaging/whatsapp/prompt {event:"shown"}.
  "Connect WhatsApp" (button or QR) calls link/start — that records the click automatically.
  "Not now" / closing it: POST /api/v1/messaging/whatsapp/prompt {event:"dismissed"}.
  Also keep a localStorage flag so it can't reappear in the same browser even if a call fails.

PLACE 3 — Settings → WhatsApp
  Not linked → the connect card. Linked → "Connected …<number_last4>" + Alerts toggle
  (POST /api/v1/messaging/whatsapp/alerts {enabled}) + Offers & news toggle
  (POST /api/v1/messaging/whatsapp/marketing {enabled}) + "Disconnect" (POST /api/v1/messaging/whatsapp/unlink).

Rules: no checkboxes for consent in the app (consent happens in WhatsApp); no prices; friendly one-line errors;
if status.available is false, hide every WhatsApp entry point.
data-testid: wa-connect-card, wa-connect-button, wa-qr, wa-onboarding-step, wa-login-popup, wa-settings.
```

## Notes for Raman
- The number choice is automatic (backend `WA_SENDERS`): India → 978, everyone else → 732. The app should pass
  the device's country if it has it; otherwise the backend uses the chart's country, then the IP's.
- Existing connected users (you, Andres, Shashi, Harleen) don't need to do anything: their links carry over; they
  just message the number they're shown.
