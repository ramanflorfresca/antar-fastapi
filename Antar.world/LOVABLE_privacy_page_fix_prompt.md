# Lovable prompt — fix the Privacy page (/privacy)

**Before pasting:** fill the four `<<…>>` values in the block (company legal address, Colombian tax/ID number,
the privacy contact email you want, and today's date). Do **not** let Lovable publish any `<<…>>` text — the
live page already shows one placeholder (`[PRIVACY CONTACT EMAIL]`) and that is what we're fixing.
Have a lawyer read the result before you publish (US, India DPDP, Brazil LGPD, Colombia Ley 1581, Argentina 25.326).

```
Update the Privacy page at /privacy. Keep the page layout, the EN / ES / PT switcher and the footer. Content
changes only — no new design. All three languages must say the same thing.

1) The page must open in the language passed as ?lang=es or ?lang=pt (WhatsApp links to
   https://antar.world/privacy?lang=es). If no ?lang, keep today's behaviour.

2) Replace every "[PRIVACY CONTACT EMAIL]" with <<PRIVACY EMAIL, e.g. hello@antar.world>>. Never show square-bracket
   placeholders anywhere on the page.

3) Change "Last updated" to <<DATE, e.g. October 5, 2026>>.

4) In the "Antar on WhatsApp" section, replace the sentence
     "What we don't do: we don't sell your number, share it for others' marketing, or send you marketing on WhatsApp."
   with:
     "What we don't do: we don't sell your number or share it for others' marketing. We only send you offers or
     news on WhatsApp if you turned on 'Offers & news' — it is off unless you switch it on, and you can turn it off
     anytime in Settings or by sending 'stop offers'."
   and add these two bullets to that section's list of what we process:
     • "Your choices about WhatsApp alerts and offers, and when you made them."
     • "Voice notes you send: the audio is transcribed to text by our speech-to-text provider (ElevenLabs) so we can
       answer it; we keep the text, not the audio."
   and add to "Your choices": "Send 'stop alerts' or 'stop offers' on WhatsApp to turn those off."

5) In "4. Third-Party Services", make the list match what we actually use:
   Google and Apple sign-in; Supabase (database and hosting); Stripe and Razorpay (payments); Anthropic and DeepSeek
   (AI that writes the answers); Twilio and WhatsApp/Meta (WhatsApp messages); ElevenLabs (voice-note
   transcription); Google Analytics (usage). Keep "These services have their own privacy policies."

6) Add a new section at the end, before "Contact", titled
   EN "Colombia — Personal Data Processing Policy (Ley 1581 de 2012)"
   ES "Colombia — Política de Tratamiento de Datos Personales (Ley 1581 de 2012)"
   PT "Colômbia — Política de Tratamento de Dados Pessoais (Lei 1581 de 2012)"
   with these sub-points (write them fully in each language):
   a. Responsible party (Responsable del tratamiento): Antar Life Navigation, Inc., <<ADDRESS>>,
      <<ID/NIT if any>>, email <<PRIVACY EMAIL>>.
   b. Purposes (Finalidades): create your account and reading from your birth details; answer your questions in the
      app and on WhatsApp; send the check-ins, alerts and offers you chose; process payments; support; improve the
      service; meet legal obligations.
   c. Authorisation (Autorización): we process your data only with your prior, express and informed authorisation,
      given when you create your account, when you connect WhatsApp in the app, or when you reply ACEPTO to our
      message on WhatsApp. We keep a record of when and how you gave it.
   d. Your rights (Derechos): know, update and correct your data; ask for proof of your authorisation; be told how
      your data is used; withdraw your authorisation and ask for deletion; file complaints with the Superintendencia
      de Industria y Comercio (SIC); access your data free of charge.
   e. How to exercise them (Procedimiento): email <<PRIVACY EMAIL>> with your name, the email or phone on your
      account, and your request. Queries (consultas) are answered within 10 business days; claims (reclamos) within
      15 business days, extendable as the law allows with notice to you. You can also delete your account in-app
      (Delete account).
   f. International transfers: your data is stored and processed in the United States and by the providers in
      section 4; by accepting you authorise these transfers.
   g. Sensitive data: we don't ask for sensitive data. Please don't send health or other sensitive details unless
      you choose to; answering such questions is optional.
   h. Validity (Vigencia): this policy applies from <<DATE>> and while we process your data; we'll tell you about
      material changes and ask you to accept them again on WhatsApp.

7) Keep "8. Children's Privacy". Add one sentence: "On WhatsApp, Antar is for people aged 18 and over."
   (WhatsApp Business messaging for adults keeps us inside Meta's policy.)

Do not change any other page. Do not change routes. Publishing stays manual.
```

## Notes for Raman (not part of the prompt)
- The WhatsApp acceptance message links to `https://antar.world/privacy?lang=es|pt` (point 1 makes that open in
  the right language). When a dedicated Colombian policy page exists, set `WA_POLICY_URL` in Railway to it.
- The provider list in point 5 is what the code uses today: Claude (Anthropic) with DeepSeek as the fallback,
  Twilio for WhatsApp, ElevenLabs for voice notes, Stripe/Razorpay for payments. Re-check before publishing if any
  of those change.
- Point 7's "18+ on WhatsApp" is a recommendation — drop it if you prefer 13+ everywhere, but check Meta's policy.
- Wording change ⇒ consider bumping `WA_CONSENT_VERSION` (messaging.py) so everyone re-accepts the updated
  policy on WhatsApp; I can do that once the page is published.
