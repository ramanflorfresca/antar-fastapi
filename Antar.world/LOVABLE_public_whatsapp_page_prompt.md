# Lovable prompt — public "Antar on WhatsApp" page (/whatsapp) — Twilio / Meta opt-in evidence

Flow (owner, 2026-10-06): **QR / button first, consent in WhatsApp.** The person scans the QR (or taps the button,
or texts START); WhatsApp opens; the FIRST thing Antar sends is the consent message (Terms + Privacy + agree to
receive messages, reply ACCEPT). Nothing is linked or processed until they reply ACCEPT. Then Antar asks two
OPTIONAL questions (alerts? offers & news?), each defaulting to no.

Twilio needs PUBLIC evidence of: the QR step, the exact consent wording, and the keyword + number. This page
shows all three to anyone (no sign-in) and works for real.

**Before pasting:** replace `<<ANTAR_WHATSAPP_NUMBER>>` (display format, e.g. +1 732 203 5001),
`<<DIGITS>>` (digits only, e.g. 17322035001) and `<<SUPPORT EMAIL>>`.

```
Create a PUBLIC page at /whatsapp (no sign-in needed), linked from the footer as "WhatsApp" next to Terms /
Privacy, in EN / ES / PT with the existing language switcher (?lang=es|pt also works). Our usual style. No prices.

Title: "Antar on WhatsApp"
Intro: "Ask Antar about your life, timing and decisions from WhatsApp — the same reading as the app. You choose
what we send you, and you can stop anytime."

SECTION 1 — "Connect in three steps"
  1. "Scan the QR code with your phone's camera (or tap 'Open WhatsApp' on your phone)."
  2. "WhatsApp opens with a message ready — press Send."
  3. "Antar replies with our Terms and Privacy Policy. Reply ACCEPT to agree. Nothing is connected or processed
     until you do."
Show a QR code of https://wa.me/<<DIGITS>>?text=START (use qrcode.react, 220px, white quiet zone) and, on phones,
a button "Open WhatsApp" with the same link. (Signed-in users who open this page get their personal code instead:
call POST /api/v1/messaging/link/start {channel:"whatsapp"} and use the returned deep_link for the QR/button.)

SECTION 2 — "What you'll see in WhatsApp"  (this is the consent evidence — render it as a WhatsApp-style chat
bubble from "Antar", exact text, in the page language):
  EN: "Antar on WhatsApp — To continue, please accept our Terms (antar.world/terms) and Privacy Policy
       (antar.world/privacy), and agree to receive your answers and check-ins from Antar on WhatsApp.
       Reply ACCEPT to continue, or NO if you don't accept. You can send STOP anytime."
       with two buttons under the bubble: [Accept] [Don't accept]
  ES: "Antar en WhatsApp — Para continuar, acepta nuestros Términos (antar.world/terms) y nuestra Política de
       tratamiento de datos (antar.world/privacy), y autoriza recibir tus respuestas y seguimientos de Antar por
       WhatsApp. Responde ACEPTO para continuar, o NO si no aceptas. Puedes enviar STOP cuando quieras."
       buttons [Acepto] [No acepto]
  PT: "Antar no WhatsApp — Para continuar, aceite nossos Termos (antar.world/terms) e nossa Política de tratamento
       de dados (antar.world/privacy), e autorize receber suas respostas e acompanhamentos da Antar pelo WhatsApp.
       Responda ACEITO para continuar, ou NÃO se não aceitar. Você pode enviar STOP a qualquer momento."
       buttons [Aceito] [Não aceito]
  Then two more bubbles, labelled "Optional — off unless you say yes":
    "Optional: would you like an alert when a strong window opens for you?"  [Yes] [No thanks]
    "Optional: would you like occasional offers and news from Antar on WhatsApp?"  [Yes] [No thanks]
  (ES/PT translations: "Opcional: ¿quieres una alerta cuando se abra una ventana fuerte para ti?" /
   "Opcional: ¿quieres recibir ofertas y novedades ocasionales de Antar por WhatsApp?" — PT: "Opcional: quer um
   alerta quando uma janela forte se abrir para você?" / "Opcional: quer receber ofertas e novidades ocasionais da
   Antar pelo WhatsApp?")
  "Terms" and "Privacy Policy" in the bubble are real links to /terms and /privacy.

SECTION 3 — "Or text us"
  Big line: "Text START to <<ANTAR_WHATSAPP_NUMBER>> on WhatsApp."
  ES: "Envía EMPEZAR al <<ANTAR_WHATSAPP_NUMBER>> por WhatsApp."   PT: "Envie COMEÇAR para <<ANTAR_WHATSAPP_NUMBER>> no WhatsApp."
  "You'll get the message shown above first. Reply ACCEPT to continue."

SECTION 4 — "What we send, and how to stop"
  • Answers to the questions you ask, and confirmations about your connection.
  • Check-ins ("did it happen?") about past answers.
  • Alerts — only if you said yes to alerts.   • Offers & news — only if you said yes to offers.
  Message frequency varies with how you use Antar. Message and data rates may apply.
  Stop anytime: send STOP to disconnect; "stop alerts" or "stop offers" to turn those off; or Settings → WhatsApp
  in the app. Help: send HELP, or email <<SUPPORT EMAIL>>.  Links: Terms (/terms) · Privacy Policy (/privacy).

Footer note: "WhatsApp is a trademark of Meta Platforms, Inc."
data-testid: wa-public-page, wa-public-qr, wa-public-consent-bubble, wa-public-keyword.
```

## Notes for Raman
- Give Twilio **https://antar.world/whatsapp** for all three opt-in questions, plus screenshots of sections 1–3.
- The in-app Connect sheet should now be just the QR / button + one line ("Antar will ask you to accept our Terms
  and Privacy Policy in WhatsApp"); no checkboxes. The backend no longer requires consent from the app.
