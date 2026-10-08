# Lovable prompt — Phase 9l: "Connect WhatsApp" in one tap, where people already are

Paste everything under "PROMPT STARTS HERE" into Lovable. UI only. No backend change: the endpoints below already exist and work for people who show a phone number and for people who hide it behind a WhatsApp user ID (fixed in the backend today).

The problem: Connect WhatsApp is buried (More, then Settings, then Connect). Some people never find it, and the ones who do go through a settings screen. It should be one tap from the places people already use, with no configuration.

## PROMPT STARTS HERE

You are working on the existing Antar web app. Make **Connect WhatsApp** a one-tap action that sits where people already are. UI only; use the existing endpoints; show strings exactly as returned; do not publish; open a PR.

### 1. Where it shows (only while not connected)
Call `GET /api/v1/messaging/whatsapp/status` once per session (you already do). Use `state`: `unavailable` (show nothing anywhere), `not_connected`, `connected`.
- **Ask home** and **Today**: a slim card directly under the page header, one line plus one button: **"Get Antar on WhatsApp"** and a **Connect** button. Small x to dismiss it for 7 days (remember it in localStorage; never hide the entries below).
- **More menu**: **WhatsApp** as the FIRST row, with **Connect** (or "Connected" with a check mark when linked).
- **Settings**: keep the existing row, unchanged.
- When `state` is `connected`: replace the card with nothing, and in More show **Open chat** (`open_chat_link` from the status response).
Never put it behind a second screen: every entry above starts the connect action below directly.

### 2. The connect action (one tap, no settings)
Tapping **Connect** anywhere:
1. Call `POST /api/v1/messaging/link/start` with `{ "channel": "whatsapp" }` (and the user's country if the app already has it as `country`). Do this **at the tap**, never on page load: the code lives 15 minutes.
2. The response has `deep_link` (opens WhatsApp with "Hi Antar! Connect my account: CODE" already typed), `qr_text` (the same link, for a QR), `prefilled_text`, `code`, `antar_number`, `expires_in_minutes`.
3. **On a phone** (touch device or narrow viewport): immediately open `deep_link` (new tab or `window.location`), and show a small sheet behind it: **"Press Send in WhatsApp"** with the steps below. On the native app shell open it with the system handler.
4. **On desktop**: a sheet with the QR (render `qr_text`), the line **"Scan with your phone's camera, or open WhatsApp Web"** with a button that opens `deep_link`, and the code in small type as a fallback.
5. Steps shown in the sheet, three short lines: **1. Press Send** (the message is already written), **2. Reply ACCEPT** (to agree to the Terms and Privacy, in the chat), **3. Done**. No other fields, no checkboxes, no configuration.

### 3. Know when it worked, without the user doing anything
While the sheet is open, poll `GET /api/v1/messaging/whatsapp/status` every 3 seconds. When `linked` is true:
- Replace the sheet content with **"Connected"** and a check mark, the last digits shown as `number_last4` ("…8335") when present, a one-line **"Ask me anything on WhatsApp"**, and an **Open chat** button (`open_chat_link`). Auto-close after the user taps Done.
- Update the status everywhere (the cards disappear, More shows Connected) without a reload.
If the sheet is open for more than `expires_in_minutes`, quietly call `link/start` again and refresh the QR / link; never show an expired code. Stop polling when the sheet closes.

### 4. Copy
New strings (en/es/pt; hinglish in Roman script; hi falls back to English): "Get Antar on WhatsApp", "Connect", "Press Send in WhatsApp", "Reply ACCEPT", "Connected", "Ask me anything on WhatsApp", "Open chat", "Scan with your phone's camera, or open WhatsApp Web". Everything else is returned by the API.

### Rules
- Never ask for a phone number, never show a form, never send people to Settings to connect. Do not mention a number format: some people have a phone number and some have a WhatsApp user ID, and both work.
- No pricing text. No analytics event containing the code or the link.
- Works at 375 px and desktop; respects the iOS safe area.

### Acceptance checks (verify and say so in the PR)
- A signed-in, not-connected user sees the WhatsApp card on Ask and on Today and the first row in More; one tap on any of them starts the connect action (no intermediate screen).
- On a phone the tap opens WhatsApp with the message already typed; on desktop it shows the QR and the open-in-WhatsApp button.
- After the user sends the message and replies ACCEPT, the sheet turns to "Connected" on its own within a few seconds and the cards disappear.
- The code is created at the tap; leaving the sheet open past 15 minutes refreshes the QR on its own.
- A connected user sees no card and an Open chat row in More; `unavailable` shows nothing anywhere.
- Screenshots at 375 px of the Ask card, the More row, the phone sheet and the Connected state, plus one desktop QR sheet, are attached to the PR.

### Out of scope (do not build)
Any change to the Settings page beyond leaving it as is, phone-number entry, alerts or marketing opt-in screens, any backend change.

## PROMPT ENDS HERE
