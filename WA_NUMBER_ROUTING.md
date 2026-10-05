# WhatsApp number pool & templates

**Model.** Several US-registered WhatsApp business numbers; each user is dedicated to ONE by their
country. Code: `antar_engine/wa_numbers.py`. Config: env `WA_SENDERS` (JSON, see the module docstring).
Unset → the single `TWILIO_WHATSAPP_FROM`, i.e. nothing changes until the pool is configured.

| Rule | Why |
|---|---|
| assignment = sha256(user number) over the numbers serving their country (else language neighbours, else `"*"`) | deterministic, spread, no state, a ban on one number is contained to a country |
| the number a user last wrote to is stored in `messaging_links.context.sender` and always wins | the 24h window belongs to that business number; proactive sends reuse it |
| `paused: true` → no NEW users, existing keep theirs | drain a number gracefully |
| language narrows candidates only when a number declares `langs` and one matches | language belongs to the user, not the number; a number is never required to match |
| the wa.me button opens the number for the user's country (`country` field, else CF/Vercel country header) | first contact lands on the right number |

**Templates** (`antar_engine/wa_templates.py`): EN / ES / PT-BR / **Hinglish**, six templates
(check-in, window alert, chapter alert, answer-ready, policy-update, decision-window). Approved per
WABA, so every sender in one WABA shares the same ContentSids (`WA_TPL_<NAME>_<LANG>`). Hinglish is
submitted under `WA_HINGLISH_LOCALE` (default `en`); unapproved Hinglish falls back to English.
Submit with `python scripts/wa_submit_templates.py --go`.

**Owner steps** (not code): register each number in Twilio WhatsApp senders + Meta; set `WA_SENDERS`;
run the submit script; set the approved `WA_TPL_*` SIDs; point every sender's inbound webhook at the same URL.
Not built: marketing/news template (needs a `mkt_stop` handler), forecast-ready, daily-wisdom (Meta would
likely classify as marketing).
