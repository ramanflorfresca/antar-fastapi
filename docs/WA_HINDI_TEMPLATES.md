# Hindi (Devanagari) WhatsApp templates — review + submission runbook

Status: **drafted, NOT submitted.** Nothing is sent to Meta unless `--with-hindi` (or `--lang hi`) is passed *and* `--go`.
Locale: Meta `hi` (Devanagari). Hinglish stays under `en` (`WA_HINGLISH_LOCALE`), separate templates.

## 1. Native-speaker review (do first)

Review every body/button below. Rules Meta enforces: no variable first/last, none adjacent, buttons ≤ 20 chars, UTILITY must not read promotional.

### `antar_checkin_v1` — UTILITY

Variables: `{{1}}`='Harleen', `{{2}}`='Oct 2', `{{3}}`='a new client signs between Nov 2026 and Jan 2027'

> नमस्ते {{1}}, {{2}} को आपकी Antar रीडिंग में लिखा था: “{{3}}”। क्या यह हुआ? आपका उत्तर Antar को आपके लिए और सटीक बनाता है।

Buttons: **हाँ** (`1`, 3 chars) · **कुछ हद तक** (`2`, 9 chars) · **नहीं** (`3`, 4 chars) · **अभी पता नहीं** (`4`, 12 chars)

English source: Hi {{1}}, on {{2}} your Antar reading said: “{{3}}”. Did it happen? Your answer helps Antar get more accurate for you.

### `antar_window_alert_v1` — UTILITY

Variables: `{{1}}`='Harleen', `{{2}}`='your strongest money window', `{{3}}`='Oct 14'

> नमस्ते {{1}}, Antar में आपने जो अलर्ट चालू किया था: {{2}}, {{3}} को खुलता है। इसका पूरा लाभ कैसे उठाएँ, यह जानना हो तो यहीं उत्तर दीजिए।

Buttons: **कैसे उपयोग करूँ?** (`alert_how`, 16 chars) · **अलर्ट बंद करें** (`alert_stop`, 14 chars)

English source: Hi {{1}}, an alert you turned on in Antar: {{2}} opens on {{3}}. Reply here if you want to know how to make the most of it.

### `antar_chapter_alert_v1` — UTILITY

Variables: `{{1}}`='Harleen', `{{2}}`='Nov 12', `{{3}}`='building your reputation at work'

> नमस्ते {{1}}, Antar में आपने जो अलर्ट चालू किया था: आपकी रीडिंग का नया अध्याय {{2}} को शुरू होता है, और उसका केंद्र {{3}} है। इसे अच्छी तरह कैसे उपयोग करें, यहीं उत्तर देकर पूछिए।

Buttons: **कैसे उपयोग करूँ?** (`alert_how`, 16 chars) · **अलर्ट बंद करें** (`alert_stop`, 14 chars)

English source: Hi {{1}}, an alert you turned on in Antar: a new chapter in your reading begins on {{2}}, and it centres on {{3}}. Reply here to ask how to use it well.

### `antar_answer_ready_v1` — UTILITY

Variables: `{{1}}`='Harleen', `{{2}}`='When will my career take off?'

> नमस्ते {{1}}, “{{2}}” का Antar उत्तर तैयार है। देखने के लिए नीचे टैप कीजिए।

Buttons: **मेरा उत्तर दिखाइए** (`show_answer`, 17 chars)

English source: Hi {{1}}, your Antar answer to “{{2}}” is ready. Tap below to see it.

### `antar_policy_update_v1` — UTILITY

Variables: `{{1}}`='Harleen'

> नमस्ते {{1}}, हमने WhatsApp पर आपके डेटा को Antar कैसे संभालता है, इसे अपडेट किया है। रीडिंग यहीं मिलती रहें, इसके लिए अपडेट की गई डेटा नीति देखकर स्वीकार कीजिए।

Buttons: **स्वीकार करता हूँ** (`pol:yes`, 16 chars) · **स्वीकार नहीं** (`pol:no`, 12 chars)

English source: Hi {{1}}, we updated how Antar handles your data on WhatsApp. To keep your readings coming here, please review and accept the updated data policy.

### `antar_decision_window_v1` — UTILITY

Variables: `{{1}}`='Harleen', `{{2}}`='changing jobs', `{{3}}`='Oct 14'

> नमस्ते {{1}}, आपने Antar से “{{2}}” के समय पर नज़र रखने को कहा था। जो समय-खिड़की आपने सहेजी थी, वह {{3}} को खुलती है। बात करनी हो तो यहीं उत्तर दीजिए।

Buttons: **मैं क्या करूँ?** (`alert_how`, 14 chars) · **रिमाइंडर बंद** (`alert_stop`, 12 chars)

English source: Hi {{1}}, you asked Antar to watch the timing for “{{2}}”. The window you saved opens on {{3}}. Reply here if you want to talk it through.

### `antar_news_v1` — MARKETING

Variables: `{{1}}`='Harleen', `{{2}}`='save a decision and Antar watches its window', `{{3}}`='Tell Antar what you are deciding and it will message you when the timing opens.'

> नमस्ते {{1}}, Antar में नया: {{2}}। {{3}} समाचार और ऑफ़र बंद करने के लिए कभी भी STOP OFFERS लिख दीजिए।

Buttons: **Antar से पूछें** (`own`, 14 chars) · **ऑफ़र बंद करें** (`mkt_stop`, 13 chars)

English source: Hi {{1}}, new in Antar: {{2}}. {{3}} Reply STOP OFFERS any time to stop news and offers.

### `antar_offer_v1` — MARKETING

Variables: `{{1}}`='Harleen', `{{2}}`='an extra week of daily alerts', `{{3}}`='Oct 31'

> नमस्ते {{1}}, Antar सदस्यों के लिए एक सूचना: {{2}}। यह {{3}} तक खुला है। ये संदेश बंद करने के लिए कभी भी STOP OFFERS लिख दीजिए।

Buttons: **Antar से पूछें** (`own`, 14 chars) · **ऑफ़र बंद करें** (`mkt_stop`, 13 chars)

English source: Hi {{1}}, a note for Antar members: {{2}}. Open until {{3}}. Reply STOP OFFERS any time to stop these messages.

## 2. Submit (after review)

```bash
python scripts/wa_submit_templates.py --with-hindi                 # dry run: lists the 8 hi templates
python scripts/wa_submit_templates.py --go --lang hi --only antar_checkin_v1   # one first, to see Meta's verdict
python scripts/wa_submit_templates.py --go --lang hi --only antar_window_alert_v1   # …then the rest, one by one
```

MARKETING (`antar_news_v1`, `antar_offer_v1`) is a separate paid Meta category and an owner decision (existing rule); submit the 6 UTILITY first.

## 3. After Meta approves

Set on Railway, one per approved template: `WA_TPL_ANTAR_CHECKIN_V1_HI`, `WA_TPL_ANTAR_WINDOW_ALERT_V1_HI`, `WA_TPL_ANTAR_CHAPTER_ALERT_V1_HI`, `WA_TPL_ANTAR_ANSWER_READY_V1_HI`, `WA_TPL_ANTAR_POLICY_UPDATE_V1_HI`, `WA_TPL_ANTAR_DECISION_WINDOW_V1_HI` (and `WA_TPL_ANTAR_NEWS_V1_HI`, `WA_TPL_ANTAR_OFFER_V1_HI`).

Until a `_HI` ContentSid is set, a Hindi reader gets the **English** template (never Hinglish) — `template_sid` / `served_lang`.

## 4. So a Hindi template is not sent with English variables

- `wa_alerts.render` now produces Hindi window text, chapter themes, dates and the how-to question for `hi`; Hinglish keeps its existing (English) variables.
- Greeting fallback when the first name is unknown: `मित्र` (`wa_templates.default_first_name`).
- Known gap: `antar_checkin_v1` `{{3}}` is the person's stored claim text in whatever language that answer was written — an older English claim inside a Hindi template is possible.
- Known gap: `antar_decision_window_v1` `{{2}}` is the saved decision's question text (user language).
