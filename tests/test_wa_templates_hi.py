"""Devanagari Hindi WhatsApp templates: drafted, NOT submitted. Nothing here may reach Meta by accident."""
import re
import subprocess
import sys

import pytest

from antar_engine import wa_templates as wt, wa_alerts as wal, lang_registry as R

DEV = re.compile(r"[ऀ-ॿ]")


def test_hindi_is_drafted_for_all_eight_templates_with_the_same_variables_and_handler_ids():
    assert len(wt.TEMPLATES) == 8
    cats = sorted(t["category"] for t in wt.TEMPLATES.values())
    assert cats.count("UTILITY") == 6 and cats.count("MARKETING") == 2
    for name, t in wt.TEMPLATES.items():
        body = t["body"]["hi"]
        assert R.devanagari_ratio(re.sub(r"\{\{\d\}\}|STOP OFFERS|Antar|Practice|WhatsApp", "", body)) > 0.9, name
        assert set(re.findall(r"\{\{(\d+)\}\}", body)) == set(t["variables"]), name
        assert [b for _, b in t["buttons"]["hi"]] == [b for _, b in t["buttons"]["en"]], name


def test_hindi_marketing_templates_keep_the_opt_out_and_no_prices():
    for n in ("antar_news_v1", "antar_offer_v1"):
        assert "STOP OFFERS" in wt.TEMPLATES[n]["body"]["hi"]
        assert wt.marketing_text_ok(wt.TEMPLATES[n]["body"]["hi"].replace("{{", "").replace("}}", ""))
    for k, v in wt.NEWS_ITEMS.items():
        assert all(wt.marketing_text_ok(x) for x in v["hi"]), k
        assert all(DEV.search(x) for x in v["hi"]), k


def test_hindi_price_wording_is_refused_in_offers():
    for bad in ("50% छूट", "नया प्लान खरीदिए", "प्रीमियम में अपग्रेड", "कीमत सिर्फ ₹99", "जल्दी करें"):
        assert not wt.marketing_text_ok(bad), bad
    assert wt.marketing_text_ok("एक अतिरिक्त सप्ताह की रोज़ की सूचनाएँ")


def test_hindi_is_submitted_under_locale_hi_and_hinglish_stays_separate(monkeypatch):
    monkeypatch.delenv("WA_HINGLISH_LOCALE", raising=False)
    p = wt.content_payload("antar_checkin_v1", "hi")
    assert p["language"] == "hi" and p["friendly_name"] == "antar_checkin_v1_hi"
    assert wt.content_payload("antar_checkin_v1", "hinglish")["language"] == "en"
    assert wt.env_key("antar_news_v1", "hi") == "WA_TPL_ANTAR_NEWS_V1_HI"


def test_unapproved_hindi_falls_back_to_english_never_hinglish(monkeypatch):
    for k in ("WA_TPL_ANTAR_CHECKIN_V1_HI", "WA_TPL_ANTAR_CHECKIN_V1_HINGLISH"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("WA_TPL_ANTAR_CHECKIN_V1_EN", "HXen")
    monkeypatch.setenv("WA_TPL_ANTAR_CHECKIN_V1_HINGLISH", "HXhg")
    assert wt.template_sid("antar_checkin_v1", "hi") == "HXen"
    assert wt.served_lang("antar_checkin_v1", "hi") == "en"
    monkeypatch.setenv("WA_TPL_ANTAR_CHECKIN_V1_HI", "HXhi")
    assert wt.template_sid("antar_checkin_v1", "hi") == "HXhi"
    assert wt.served_lang("antar_checkin_v1", "hi") == "hi"
    assert wt.template_sid("antar_checkin_v1", "hinglish") == "HXhg"


def test_submit_scripts_do_not_create_hindi_unless_asked(capfd):
    for script, extra in (("scripts/wa_submit_templates.py", []), ("scripts/twilio_create_templates.py", ["--dry-run"])):
        base = subprocess.run([sys.executable, script] + extra, capture_output=True, text=True, timeout=60)
        assert base.returncode == 0, base.stderr[-300:]
        assert "_hi" not in base.stdout.replace("_hinglish", "") and "/hi " not in base.stdout, script
    withhi = subprocess.run([sys.executable, "scripts/wa_submit_templates.py", "--with-hindi"],
                            capture_output=True, text=True, timeout=60)
    assert withhi.stdout.count("/hi (hi,") == 8                      # all eight, locale hi, dry run only
    assert "submitted" not in withhi.stdout


def test_alert_variables_are_hindi_for_devanagari_and_unchanged_for_hinglish():
    from datetime import date
    alert = {"alert_type": "dasha_turn", "window_start": "2026-11-12"}
    r = wal.render(alert, "hi", "राम", lord="Saturn")
    assert DEV.search(r["variables"]["3"]) and r["variables"]["2"] == "12 नवंबर"
    assert r["text"].startswith("नमस्ते राम") and DEV.search(r["how_q"])
    assert wal.render(alert, "hi", "", lord="Saturn")["variables"]["1"] == "मित्र"
    h = wal.render(alert, "hinglish", "", lord="Saturn")                     # Hinglish unchanged
    assert h["variables"]["1"] == "dost" and h["variables"]["2"] == "Nov 12"
    assert h["variables"]["3"] == wal.CHAPTER_THEME["en"]["Saturn"]
    w = wal.render({"alert_type": "wealth_window", "window_start": "2026-10-14"}, "hi", "राम")
    assert DEV.search(w["variables"]["2"])


def test_log_body_matches_the_template_actually_sent(monkeypatch):
    monkeypatch.delenv("WA_TPL_ANTAR_CHECKIN_V1_HI", raising=False)
    assert wt.served_lang("antar_checkin_v1", "hi") == "en"
