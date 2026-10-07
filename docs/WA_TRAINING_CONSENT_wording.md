# WhatsApp training consent — draft wording (`wa-train-2026-10-06`)

DRAFT for the owner and counsel. Not legal advice. Bump `WA_TRAINING_CONSENT_VERSION` in
`antar_engine/messaging.py` on ANY change — everyone is then asked again.

## Principles
- **Separate and optional.** Asked after the Terms/Privacy acceptance and the alerts/offers questions,
  as its own question. Never ticked by default, never a condition of using Antar, no change to the
  service if the answer is no.
- **Plain about what it is.** Says what is kept, what is removed, who sees it, and how to stop.
- **Not retroactive.** Only messages sent after the yes are ever used.
- **Withdraw any time** by replying `STOP TRAINING` in the chat (an in-app Settings toggle is a Lovable follow-up). Plain `STOP` still disconnects WhatsApp entirely, which also ends training use. Withdrawal
  removes the person from every future export immediately.

## Question (sent in chat, two tap buttons: Yes / No thanks)

**English**
> One more choice, and it's entirely optional. Can Antar learn from your conversations to become a
> better astrologer? If you say yes, we use your chat messages and Antar's replies from now on, after
> removing your name, phone number, email, links and birth date, to train and improve Antar's own AI.
> Your chats are never sold or shared with advertisers, and Antar works exactly the same if you say no.
> You can change your mind any time by replying STOP TRAINING.
> Buttons: **Yes, help Antar learn** · **No thanks**

**Español**
> Una elección más, totalmente opcional. ¿Puede Antar aprender de tus conversaciones para ser mejor
> astrólogo? Si dices que sí, usaremos tus mensajes y las respuestas de Antar a partir de ahora —tras
> quitar tu nombre, teléfono, correo, enlaces y fecha de nacimiento— para entrenar y mejorar la IA
> propia de Antar. Tus chats nunca se venden ni se comparten con anunciantes, y Antar funciona igual
> si dices que no. Puedes cambiar de opinión cuando quieras respondiendo PARAR ENTRENAMIENTO.
> Botones: **Sí, ayudar a Antar** · **No, gracias**

**Hinglish**
> Ek aur choice, bilkul optional. Kya Antar aapki baatcheet se seekh sakta hai taaki ek behtar
> astrologer ban sake? Agar aap haan kehte hain, to ab se aapke messages aur Antar ke jawab — aapka naam,
> phone number, email, links aur janm tithi hata kar — Antar ke apne AI ko train karne mein use honge.
> Aapki chats kabhi bechi ya advertisers ke saath share nahi hoti, aur na kehne par Antar bilkul
> waise hi kaam karta hai. Kabhi bhi man badle to STOP TRAINING bhej dein.
> Buttons: **Haan, Antar ki madad karo** · **Nahi, shukriya**

## Confirmation after Yes (and after withdrawing)
- EN: "Thank you — Antar will learn from your chats from now on. Reply STOP TRAINING any time."
- ES: "Gracias — Antar aprenderá de tus chats desde ahora. Responde PARAR ENTRENAMIENTO cuando quieras."
- Hinglish: "Shukriya — Antar ab se aapki chats se seekhega. Kabhi bhi STOP TRAINING bhej dein."
- After withdrawing — EN: "Done. Antar won't use your chats for learning from now on." (ES: "Listo. Antar ya no usará tus chats para aprender." · Hinglish: "Ho gaya. Antar ab aapki chats se nahi seekhega.")

## Privacy-policy text to add (needs counsel)
Purpose (training Antar's own models), data (WhatsApp messages and Antar's replies after consent,
de-identified), legal basis (consent, withdrawable), retention, who processes it (name any model-training
vendor), no sale, withdrawal route, and that withdrawal stops future use but cannot un-train a model
already trained (say so). Check: GDPR Art. 6/7/21, India DPDP (consent notice in plain language),
Colombia Ley 1581 (prior express authorization), Argentina Ley 25.326, Brazil LGPD Art. 8, and Meta's
WhatsApp Business policy on use of message content.

## Hard rules for the build
1. **Wired (2026-10-06):** the question follows the offers question (only once the columns exist) and `STOP TRAINING` / `PARAR ENTRENAMIENTO` / `PARAR TREINAMENTO` withdraw. Still to do: an in-app toggle.
2. Under-18s: Antar does not collect age; decide whether to exclude or to ask before any export.
3. Sensitive content (health, finances, relationships, self-harm) — decide an exclusion list before training.
4. Training-grade output is the export only (`scripts/export_wa_training.py`): consented, post-consent,
   scrubbed, pseudonymous. Raw `wa_messages` is never fed to a model.
