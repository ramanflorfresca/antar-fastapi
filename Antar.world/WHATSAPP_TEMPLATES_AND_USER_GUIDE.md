# WhatsApp — templates and user guide

Product role (owner, 2026-10-03): **WhatsApp is Antar's conversation and return channel**, not a second app.
Retention first, then acquisition. Antar only writes first for (1) "did it happen?" check-ins and
(2) alerts the person turned on. Everything else starts with the person.

---

## 1. Templates to submit (all UTILITY, EN / ES / PT-BR)

Source of truth: `antar_engine/wa_templates.py`. Hinglish readers receive the English version
(Meta has no Latin-script Hindi locale).

| Template | When it's sent | Variables | Buttons |
|---|---|---|---|
| `antar_checkin_v1` | A dated reading's window has passed and the person hasn't written in 24h (alerts on). Never for health, separation or pregnancy topics. | name · date it was said · what Antar said | Yes · Partly · No · Not sure yet |
| `antar_window_alert_v1` | An alert they turned on: a window opens | name · what opens · date | How do I use it? · Stop alerts |
| `antar_chapter_alert_v1` | An alert they turned on: a new chapter starts | name · date · what it centres on | How do I use it? · Stop alerts |
| `antar_answer_ready_v1` | An answer we owe them missed the 24h window | name · their question | Show my answer |

**English bodies**

- **Check-in:** Hi {{1}}, on {{2}} your Antar reading said: "{{3}}". Did it happen? Your answer helps Antar get more accurate for you.
- **Window alert:** Hi {{1}}, an alert you turned on in Antar: {{2}} opens on {{3}}. Reply here if you want to know how to make the most of it.
- **Chapter alert:** Hi {{1}}, an alert you turned on in Antar: a new chapter in your reading begins on {{2}}, and it centres on {{3}}. Reply here to ask how to use it well.
- **Answer ready:** Hi {{1}}, your Antar answer to "{{2}}" is ready. Tap below to see it.

Why they should pass as UTILITY: each is tied to something the person asked for or switched on.
None mentions prices, upgrades, offers or discounts; there's no hype or emoji; there's no variable
at the start or end of the body; no two variables sit side by side; and buttons are ≤20 characters.
A test enforces all of this.

**Risk:** Meta may still reclassify the alerts as MARKETING. If it does, they still work but cost
more per message, and people can mute them. The check-in and answer-ready templates are the
strongest utility cases.

## 2. On the day Twilio approves the Business Profile

1. Run, with your own credentials. They're read from the environment and never printed:
   ```bash
   TWILIO_ACCOUNT_SID=... TWILIO_AUTH_TOKEN=... venv311/bin/python scripts/twilio_create_templates.py
   ```
   This creates 12 contents (4 templates × 3 languages) and submits each to Meta. It prints the
   Railway variable for each, e.g. `WA_TPL_ANTAR_CHECKIN_V1_ES=HX…`.
2. When Meta approves each one (usually minutes to a day), set its variable in Railway. Until a
   variable is set, that template is never sent; check-ins fall back to push or the in-app card.
3. Set `WHATSAPP_INLINE_REPLIES=off` (REST replies, typing indicator, tap lists).

What's already wired:
- **Check-ins** use the template outside 24h.
- **Button taps:** Yes/Partly/No/Not sure record the outcome, "Stop alerts" turns alerts off, and
  "Show my answer" delivers the pending answer.

**Not built yet:** the jobs that *send* the window and chapter alerts and the answer-ready template. The templates and the button handling are ready for them.

## 3. What people should and shouldn't do (in-chat: `tips` / `consejos` / `dicas`)

**Do**
- Ask one question at a time, in your own words.
- Say what's going on ("I'm between jobs", "we just separated"). Antar uses what you tell it.
- Name the area and the time if you can ("my visa, this year").
- For a straight answer, start with **yes or no:**
- Travelling? Send "I'm in London" so "today" means your today.
- When Antar asks "did it happen?", answer honestly. It makes Antar more accurate.

**Don't**
- Never send passwords, bank or card numbers, ID numbers or OTP codes. Antar never asks for them.
- Don't treat a reading as medical, legal or financial advice, or as a reason to bet.
- Don't share someone else's birth details without their OK.

**What Antar will never do:** ask for money in the chat, or write first except for check-ins and
alerts you turned on. If you're in danger or thinking of harming yourself, contact local emergency
services now.

**Commands:** `STOP` disconnects · `stop alerts` / `parar alertas` · `help` / `ayuda` / `ajuda` · `tips`.

---

## 4. Lovable prompt — show the same guidance in the app

Paste below the line into Lovable.

---

Add a short "Using Antar on WhatsApp" section to (a) the Connect WhatsApp consent sheet, under the
consent checkboxes, collapsed by default, and (b) the FAQ page, as a new question
"How should I use Antar on WhatsApp?". Static copy only. No logic and no backend calls. EN / ES /
PT, following the app language.

EN copy:

**Do:** ask one question at a time · say what's going on — Antar uses what you tell it · start with
"yes or no:" for a straight answer · tell Antar if you're travelling · answer "did it happen?"
honestly.

**Never send:** passwords, bank or card numbers, ID numbers or OTP codes — Antar never asks for
them.

**Good to know:** readings are guidance, not medical, legal or financial advice, and never a reason
to bet · Antar never asks for money in the chat · it only writes first for check-ins and alerts you
turned on · reply STOP any time to disconnect, or "stop alerts" to stop alerts.

ES and PT: translate faithfully. Use "sí o no:" / "sim ou não:" for the yes-or-no prefix, and keep
STOP as-is.

Do not show prices anywhere in this section.
