"""Devanagari Hindi (`hi`) as a first-class language — and Hinglish untouched.

Owner rule: ZERO tolerance for answering in the wrong language. `hi` = Devanagari,
`hinglish` = Roman script; neither may silently become the other, and an unknown code
becomes English explicitly.
"""
import asyncio
import re

import pytest
from dotenv import load_dotenv

load_dotenv()

from antar_engine import lang_registry as R
from antar_engine import hindi_guard as G

DEV = re.compile(r"[ऀ-ॿ]")


@pytest.fixture(autouse=True)
def _no_network_translator(monkeypatch):
    """The default translator calls Haiku. Tests must never reach the network (a dev machine with a real
    key would otherwise make results depend on the model); an unavailable translator is the case that
    exercises the deterministic fallback."""
    async def down(_strings):
        raise RuntimeError("translator unavailable in tests")
    monkeypatch.setattr(G, "_default_translator", down)


def run(coro):
    return asyncio.run(coro)


# ── registry ────────────────────────────────────────────────────────────────

def test_registry_lists_the_five_picker_languages_plus_fr_in_picker_order():
    assert R.SUPPORTED_LANGUAGES == ("en", "hi", "hinglish", "es", "pt", "fr")
    assert R.LANGUAGE_LABELS["hi"] == "हिन्दी"
    assert R.LANGUAGE_LABELS["hinglish"] == "Hinglish"


@pytest.mark.parametrize("raw,want", [
    ("hi", "hi"), ("HI", "hi"), (" hi ", "hi"), ("hi-IN", "hi"), ("hi_IN", "hi"), ("hindi", "hi"),
    ("hinglish", "hinglish"), ("Hinglish", "hinglish"), ("hi-Latn", "hinglish"),
    ("es-CO", "es"), ("pt-BR", "pt"), ("fr", "fr"), ("en-GB", "en"),
])
def test_normalize_known_codes(raw, want):
    assert R.normalize_language(raw) == want


@pytest.mark.parametrize("raw", ["xx", "klingon", "his", "hin glish", "hinglsh", "ta", "bn", "zz-ZZ"])
def test_unknown_language_is_english_explicitly_never_hinglish(raw):
    assert R.normalize_language(raw) == "en"
    assert not R.is_supported(raw)


def test_empty_uses_the_default_not_a_guess():
    assert R.normalize_language("") == "en"
    assert R.normalize_language(None) == "en"
    assert R.normalize_language("", default="es") == "es"


def test_settings_endpoint_advertises_exactly_the_registry():
    import main
    assert main.SETTINGS_AVAILABLE_LANGS == list(R.SUPPORTED_LANGUAGES)
    assert "hi" in main.SETTINGS_AVAILABLE_LANGS and "hinglish" in main.SETTINGS_AVAILABLE_LANGS


def test_root_language_utils_shares_the_registry():
    import language_utils as LU
    assert LU.VALID_LANGUAGES == set(R.SUPPORTED_LANGUAGES)
    assert "Devanagari" in LU.build_language_instruction("hi")
    assert "Roman" in LU.build_language_instruction("hinglish")
    # resolve_language: unknown explicit value -> stored value -> English, never Hinglish
    assert LU.resolve_language({"language": "klingon"}, {"language": "hi"}) == "hi"
    assert LU.resolve_language({"language": "klingon"}, None) == "en"


# ── Devanagari measurement + guard predicates ───────────────────────────────

def test_ratio_hindi_english_hinglish_mixed():
    assert R.devanagari_ratio("आपका करियर इस साल मज़बूत है") == 1.0
    assert R.devanagari_ratio("Your career is strong this year") == 0.0
    assert R.devanagari_ratio("Aapka career is saal strong hai") == 0.0
    assert R.devanagari_ratio("") == 1.0 and R.devanagari_ratio("2026-10-07 87%") == 1.0
    assert 0.3 < R.devanagari_ratio("आपका career window अक्टूबर में खुलेगा") < 0.95


def test_is_mostly_devanagari():
    assert R.is_mostly_devanagari("अक्टूबर 2026 में Antar आपको बताएगा कि क्या करें")
    assert not R.is_mostly_devanagari("Aapka career window October mein khulega")
    assert not R.is_mostly_devanagari("Your window opens in October")


def test_sentence_guard_flags_one_english_sentence_in_a_hindi_paragraph():
    para = ("आपका समय इस महीने काफ़ी मज़बूत दिख रहा है और कामों में गति आएगी। Your window opens in May. "
            "इसलिए अपने सबसे ज़रूरी काम को पहले कीजिए और बाकी को बाद के लिए रखिए।")
    assert R.is_mostly_devanagari(para, 0.7)        # the paragraph ratio alone would pass it...
    assert not G.text_is_hindi(para)                # ...the sentence guard does not
    assert G.text_is_hindi("आपका समय अच्छा है। Antar आपको अक्टूबर 2026 बताएगा।")


# ── detector: Devanagari vs Hinglish vs English, short messages, names ──────

@pytest.mark.parametrize("text", ["मेरी शादी कब होगी?", "मदद", "हाँ", "राम", "मेरा करियर कैसा है", "कुंडली"])
def test_devanagari_is_hindi_even_when_short(text):
    assert R.detect_devanagari_language(text) == "hi"


@pytest.mark.parametrize("text", ["meri shaadi kab hogi?", "Raman", "Amik", "ok", "hi", "help", "Namaste",
                                   "Will I get the job?", "", None, "12345", "👍"])
def test_roman_text_and_names_are_not_devanagari(text):
    assert R.detect_devanagari_language(text) is None


def test_lone_devanagari_name_inside_an_english_question_does_not_flip_language():
    assert R.detect_devanagari_language("Should my friend राम join the company I am starting next year?") is None


def test_wa_lang_separates_hindi_hinglish_english():
    import main
    assert main._wa_lang("मेरा करियर कब बढ़ेगा?", "en") == "hi"
    assert main._wa_lang("मदद", "hinglish") == "hi"
    assert main._wa_lang("kya mujhe paisa milega is saal?", "en") == "hinglish"      # Hinglish unchanged
    assert main._wa_lang("meri shaadi kab hogi?") == "hinglish"
    assert main._wa_lang("Will I make good money doing defence deals with the government?", "hinglish") == "en"
    assert main._wa_lang("ok", "hi") == "hi"            # too short to decide -> the saved language
    assert main._wa_lang("Amik", "hinglish") == "hinglish"
    assert main._wa_lang("Amik", "klingon") == "en"     # unknown fallback -> English, not Hinglish


def test_ask_resolve_language():
    import main
    f = main._ask_resolve_language
    assert f("en", "मेरी शादी कब होगी?")[0] == "hi"
    assert f("en", "मेरी शादी कब होगी?")[1] == "hi"          # learned -> one-time offer, never auto-switch
    assert f("hi", "Will I get the job offer from the bank this year?")[0] == "en"
    # an explicit Hindi picker who types Roman Hindi keeps Devanagari (Hinglish is a different option)
    assert f("hi", "meri shaadi kab hogi?")[0] == "hi"
    assert f("hinglish", "meri shaadi kab hogi?")[0] == "hinglish"          # unchanged
    assert f("en", "meri shaadi kab hogi?")[0] == "hinglish"                # unchanged
    assert f("hinglish", "मेरी शादी कब होगी?")[0] == "hi"                    # the script is unambiguous
    assert f("es", "¿Cuándo me caso?")[0] == "es" and f("pt", "Quando vou me casar?")[0] == "pt"
    assert f("hi", "?")[0] == "hi"


def test_detection_never_changes_a_stored_language():
    """_ask_language_offer must only OFFER; the chart row is untouched unless the reader confirms."""
    import main
    calls = []

    class _T:
        def update(self, d):
            calls.append(d)
            return self

        def eq(self, *a):
            return self

        def execute(self):
            return self

    class _SB:
        def table(self, name):
            return _T()

    main._ask_language_offer(_SB(), "cid", "hi", {"language": "en", "locale_variant": ""})
    for d in calls:
        assert "language" not in d and "language_preference" not in d


# ── guard behaviour ─────────────────────────────────────────────────────────

def _fake_translator(mapping):
    async def tr(strings):
        return {k: mapping.get(v, "अनुवाद उपलब्ध नहीं") if False else mapping.get(v, v) for k, v in strings.items()}
    return tr


def test_guard_translates_english_and_hinglish_sentences_in_place():
    pay = {"mode": "explore", "verdict": "YES",
           "read": "आपका समय अच्छा है। Your career window opens in October. आगे बढ़िए।",
           "next": "Aap is hafte apna CV bhejiye aur follow up kijiye.",
           "followups": [{"q": "When will my career take off?", "title": "Timing"}, {"q": "मेरा पैसा कैसा है?"}]}
    tr = _fake_translator({
        "Your career window opens in October.": "आपके करियर की खिड़की अक्टूबर में खुलेगी।",
        "Aap is hafte apna CV bhejiye aur follow up kijiye.": "इस हफ़्ते अपना सीवी भेजिए और फ़ॉलो-अप कीजिए।",
        "When will my career take off?": "मेरा करियर कब उड़ान भरेगा?",
        "Timing": "समय",
    })
    out = run(G.enforce_hindi(pay, tr))
    assert out["read"] == "आपका समय अच्छा है। आपके करियर की खिड़की अक्टूबर में खुलेगी। आगे बढ़िए।"
    assert out["next"].startswith("इस हफ़्ते")
    assert out["mode"] == "explore" and out["verdict"] == "YES"          # structural keys untouched
    assert out["followups"][0]["q"].startswith("मेरा करियर कब")
    assert G.text_is_hindi(out["read"]) and G.text_is_hindi(out["next"])


def test_guard_falls_back_deterministically_when_translation_fails():
    pay = {"mode": "explore", "read": "Your timing is strong in October and November this year.",
           "next": "Send the proposal this week please.", "why": "Because of the dasha period you are in.",
           "suggested_questions": ["How is my money?", "मेरा करियर कब बढ़ेगा?"],
           "followups": [{"q": "How is my love life?", "title": "Love"}],
           "disclaimer": "Not advice, an analysis of timing."}

    async def boom(_):
        raise RuntimeError("translator down")

    out = run(G.enforce_hindi(pay, boom))
    assert out["read"] == R.fallback_text("read", "hi") and G.text_is_hindi(out["read"])
    assert out["next"] == R.fallback_text("next", "hi")
    assert out["why"] == R.fallback_text("why", "hi")
    assert out["suggested_questions"] == ["मेरा करियर कब बढ़ेगा?"]      # English chip dropped, Hindi one kept
    assert out["followups"] == []                                       # whole chip element dropped
    assert "disclaimer" not in out                                      # never ship an English disclaimer to hi
    assert not any(re.search(r"[A-Za-z]{4,}", v) for v in (out["read"], out["next"], out["why"]))


def test_guard_rejects_a_translator_that_returns_english_again():
    async def still_english(strings):
        return {k: v for k, v in strings.items()}

    out = run(G.enforce_hindi({"read": "Your timing is strong in October.", "next": ""}, still_english))
    assert out["read"] == R.fallback_text("read", "hi")


def test_guard_leaves_clean_hindi_alone_and_makes_no_translator_call():
    called = []

    async def tr(strings):
        called.append(strings)
        return strings

    pay = {"mode": "explore", "read": "आपका समय अक्टूबर 2026 से मज़बूत है, Antar के अनुसार।", "next": "सीवी भेजिए।"}
    out = run(G.enforce_hindi(dict(pay), tr))
    assert out == pay and not called


def test_hindi_fallbacks_are_devanagari_and_english_fallbacks_exist():
    for k in ("read", "next", "why", "generic"):
        assert R.is_mostly_devanagari(R.fallback_text(k, "hi"), 0.95)
    assert R.fallback_text("read", "es") == R.fallback_text("read", "en")     # explicit English, not Hinglish
    assert R.fallback_text("read", "hinglish") == R.fallback_text("read", "en")


def test_ask_endpoint_guard_runs_only_for_hindi():
    import main

    class Req:
        def __init__(self, language, question):
            self.language, self.question = language, question

    async def go(lang, q):
        res = {"mode": "explore", "read": "Your timing is strong in October.", "next": "Send it."}
        return await main._ask_hindi_finalize(dict(res), Req(lang, q))

    assert run(go("en", "How is my money?"))["read"].startswith("Your timing")          # untouched
    assert run(go("hinglish", "meri shaadi kab hogi?"))["read"].startswith("Your timing")
    out = run(go("hi", "मेरी शादी कब होगी?"))
    assert G.text_is_hindi(out["read"]) and G.text_is_hindi(out["next"])
    assert out["read"] == R.fallback_text("read", "hi") or DEV.search(out["read"])


def test_ask_guard_rewrites_a_json_response_and_keeps_status_and_headers():
    import json
    import main
    from starlette.responses import JSONResponse

    class Req:
        language, question = "hi", "मेरी शादी कब होगी?"

    resp = JSONResponse(status_code=200, headers={"X-Test": "1"},
                        content={"mode": "explore", "read": "Your timing is strong.", "locked": False,
                                 "suggested_questions": ["How is my money?"]})
    out = run(main._ask_hindi_finalize(resp, Req()))
    body = json.loads(out.body)
    assert out.status_code == 200 and out.headers["x-test"] == "1"
    assert G.text_is_hindi(body["read"]) and body["suggested_questions"] == [] and body["locked"] is False


def test_ask_guard_fails_closed_on_the_language_if_it_crashes(monkeypatch):
    import main
    from antar_engine import hindi_guard

    class Req:
        language, question = "hi", "मेरी शादी कब होगी?"

    async def boom(_):
        raise RuntimeError("guard bug")

    monkeypatch.setattr(hindi_guard, "enforce_hindi", boom)
    out = run(main._ask_hindi_finalize({"mode": "explore", "read": "English read text here."}, Req()))
    assert G.text_is_hindi(out["read"]) and DEV.search(out["read"])


# ── translator / gate wiring ────────────────────────────────────────────────

def test_translator_supports_hi_and_gates_on_script():
    from antar_engine import translation_middleware as tm
    assert "hi" in tm.SUPPORTED_LANGUAGES
    assert tm._hindi_bad("Your window opens in October")
    assert tm._hindi_bad("Aapka career window khulega")
    assert tm._hindi_bad("आपका career window opens in October soon")      # half-translated
    assert not tm._hindi_bad("आपकी समय-खिड़की अक्टूबर में खुलेगी, Antar के अनुसार")
    assert not tm._hindi_bad("2026-10-07") and not tm._hindi_bad("87%")


def test_hindi_translator_prompt_requires_devanagari():
    from antar_engine.translation_glossary import build_translation_system_prompt as b
    p = b("Hindi (Devanagari script only — never Roman-script Hindi)", "hi")
    assert "DEVANAGARI" in p and "NEVER Roman-script" in p and "राहु" in p
    assert "DEVANAGARI" not in b("Spanish (LATAM neutral)", "es")


def test_hindi_dates_are_localized_without_the_llm():
    from antar_engine.translation_middleware import localize_date_str
    assert localize_date_str("Sun 15 Nov", "hi") == "रवि 15 नवंबर"
    assert localize_date_str("Oct 2026", "hi") == "अक्टूबर 2026"
    assert localize_date_str("Sun 15 Nov", "es") == "dom 15 nov"               # es unchanged


def test_translate_dict_for_hi_only_sends_non_devanagari_values(monkeypatch):
    from antar_engine import translation_middleware as tm
    sent = {}

    async def fake_call(strings, lang):
        sent.update(strings)
        return {k: "आपकी खिड़की अक्टूबर में खुलेगी।" for k in strings}

    async def no_cache(**kw):
        return None

    async def no_save(**kw):
        return None

    monkeypatch.setattr(tm, "_call_translator", fake_call)
    monkeypatch.setattr(tm, "get_cached_translation", no_cache)
    monkeypatch.setattr(tm, "save_translation", no_save)
    data = {"headline": "Your window opens in October", "note": "यह पहले से हिन्दी है", "count": 3}
    out = run(tm.translate_dict(data, language="hi", fields_to_translate=["headline", "note"],
                                endpoint_name="t", chart_id="c"))
    assert list(sent.values()) == ["Your window opens in October"]
    assert out["note"] == "यह पहले से हिन्दी है" and out["headline"].startswith("आपकी")
    assert "_translation_status" not in out


def test_translate_dict_for_hi_flags_and_does_not_cache_residual_english(monkeypatch):
    from antar_engine import translation_middleware as tm
    saved = []

    async def fake_call(strings, lang):
        return dict(strings)                    # translator gave up: English kept

    async def no_cache(**kw):
        return None

    async def save(**kw):
        saved.append(kw)

    monkeypatch.setattr(tm, "_call_translator", fake_call)
    monkeypatch.setattr(tm, "get_cached_translation", no_cache)
    monkeypatch.setattr(tm, "save_translation", save)
    out = run(tm.translate_dict({"headline": "Your window opens in October"}, language="hi",
                                fields_to_translate=["headline"], endpoint_name="t", chart_id="c"))
    assert out["_translation_status"] == "partial_english"
    assert not saved                             # pinned English must never be cached for Hindi


def test_gate_language_serves_hi_on_translated_surfaces_and_en_explicitly_elsewhere():
    from antar_engine.pt_readiness import gate_language as g
    assert g("home", "hi") == "hi" and g("day-deep", "hi-IN") == "hi"
    assert g("welcome", "hi") == "en" and g("weekly-briefing", "hi") == "en"     # explicit, logged
    assert g("home", "hinglish") == "en" and g("home", "hi-Latn") == "en"        # unchanged: never Hindi
    assert g("home", "klingon") == "en"
    assert g("home", "pt-BR") == "pt" and g("home", "es") == "es"


# ── legacy "hi" == Roman-Hinglish traps ─────────────────────────────────────

def test_devanagari_reader_never_gets_the_roman_hinglish_tables():
    from antar_engine import answer_disclaimer as d, saved_decisions as sd, outcomes as oc
    from antar_engine import ask_followups as af, answer_polish as ap, speculation_policy as sp
    from antar_engine import ask_subject_person as asp
    for dom in ("health", "money", "legal", "fertility"):
        hi = d._TEXT[dom]["hindi"]
        assert R.is_mostly_devanagari(hi, 0.9)
        assert d.disclaimer_for(dom, "x", language="hi") == hi
        assert d.disclaimer_for(dom, "x", language="hinglish") == d._TEXT[dom]["hi"]   # Hinglish unchanged
    title, body = sd.push_message({"language": "hi", "question": "Q?"})
    assert R.is_mostly_devanagari(title, 0.9) and DEV.search(body)
    assert sd.push_message({"language": "hinglish", "question": "Q?"})[0] == "Aapki window khul gayi"
    assert "दिसंबर" in oc.checkin_note("2026-12-05T00:00:00Z", "hi")
    assert oc.checkin_note("2026-12-05T00:00:00Z", "hinglish") == "Antar aapse December mein dobara poochhega."
    assert af._lang("hi") == "en" and af._lang("hinglish") == "hi"
    assert ap._lang("hi") == "en" and ap._lang("hinglish") == "hi"
    assert sp._lang("hi") == "en" and sp._lang("hinglish") == "hinglish"
    assert asp._lang("hi") == "en" and asp._lang("hinglish") == "hinglish"


def test_hinglish_directive_and_hindi_directive_are_different():
    import main
    h, hl = main._ask_lang_directive("hi"), main._ask_lang_directive("hinglish")
    assert "Devanagari" in h and "NEVER write Hindi in Roman" in h
    assert "Do NOT use Devanagari" in hl and "Roman/Latin" in hl


# ── WhatsApp copy ───────────────────────────────────────────────────────────

def test_every_whatsapp_string_has_a_hindi_column_with_the_same_placeholders():
    import string
    import main

    def fields(s):
        return {f for _, f, _, _ in string.Formatter().parse(s) if f}

    missing = [k for k, v in main._WA_L.items() if "hi" not in v]
    assert not missing, f"no Hindi for WhatsApp keys: {missing}"
    for k, v in main._WA_L.items():
        assert fields(v["hi"]) == fields(v["en"]), k
        assert DEV.search(v["hi"]), k
    # consent, help and the core error strings read as Hindi, not Hinglish
    for k in ("policy_prompt", "help", "failed", "too_many", "bad_code", "policy_ok", "policy_no"):
        assert R.devanagari_ratio(re.sub(r"\*[A-Za-z .:/–1-3-]+\*|https?://\S+|\{[a-z]+\}", "", main._WA_L[k]["hi"])) > 0.55, k   # some quote English in-app button labels
    assert "*ACCEPT*" in main._WA_L["policy_prompt"]["hi"] and "*STOP*" in main._WA_L["policy_prompt"]["hi"]
    assert main._wa_text("welcome", "hi", name="राम").startswith("✅ जुड़ गया")
    assert main._wa_text("welcome", "hinglish", name="Ram").startswith("✅ Connected")     # unchanged
    assert main._wa_text("welcome", "klingon", name="Ram").startswith("✅ Connected — I'm reading")  # English
    assert len(main._WA_AREA_Q["hi"]) == 3 and all(DEV.search(q) for q in main._WA_AREA_Q["hi"])


def test_whatsapp_onboarding_and_login_have_hindi():
    from antar_engine import wa_onboarding as wo, wa_login as wl
    for k, v in wo.T.items():
        assert DEV.search(v["hi"]), k
    for k, v in wl.T.items():
        assert DEV.search(v["hi"]), k
    assert wo.parse_name("मेरा नाम राम है") == "राम"
    assert wo.parse_dob("१४ मार्च १९९०") == ("1990-03-14", False)
    assert wo.parse_tob("पता नहीं") == ("12:00", "unknown")
    assert wo.parse_yes_no("हाँ") == "yes" and wo.parse_yes_no("नहीं") == "no"
    assert wo.parse_name("Raman") == "Raman"                                              # Latin unchanged


def test_whatsapp_commands_and_consent_replies_in_devanagari():
    from antar_engine import messaging as m
    assert m.parse_wa_command("मदद")[0] == "help"
    assert m.parse_wa_command("अलर्ट बंद")[0] == "alerts_off"
    assert m.parse_wa_command("बंद")[0] == "unlink"
    assert m.parse_wa_command("help")[0] == "help" and m.parse_wa_command("madad")[0] == "help"
    assert m.parse_policy_reply("स्वीकार") == "yes" and m.parse_policy_reply("स्वीकार नहीं") == "no"
    assert m.parse_policy_reply("ACCEPT") == "yes" and m.parse_policy_reply("nahi") == "no"
    assert m.parse_optin_reply("हाँ।") == "yes" and m.parse_optin_reply("नहीं") == "no"


def test_saved_whatsapp_language_hi_is_devanagari_not_hinglish(monkeypatch):
    import main

    class Q:
        def __init__(self, val):
            self.val = val

        def select(self, *_):
            return self

        def eq(self, *_):
            return self

        def limit(self, *_):
            return self

        def execute(self):
            class R_:
                pass

            r = R_()
            r.data = [{"language_preference": self.val, "language": None}]
            return r

    for stored, want in [("hi", "hi"), ("hinglish", "hinglish"), ("hi-Latn", "hinglish"), ("es", "es"),
                         ("pt-BR", "pt"), ("en", "en"), ("klingon", None), ("fr", None)]:
        class SB:
            def table(self, _):
                return Q(stored)
        monkeypatch.setattr(main, "supabase", SB())
        assert main._wa_saved_lang("cid") == want, stored


def test_whatsapp_templates_hindi_goes_to_english_not_hinglish():
    from antar_engine import wa_templates as wt
    assert wt.wa_lang("hi") == "en"
    assert wt.wa_lang("hinglish") == "hinglish" and wt.wa_lang("hi-Latn") == "hinglish"
    assert wt.wa_lang("pt-BR") == "pt_BR" and wt.wa_lang("es") == "es"
    assert wt.meta_locale("hinglish") == "en"
    cats = sorted(t["category"] for t in wt.TEMPLATES.values())
    assert cats.count("UTILITY") == 6 and cats.count("MARKETING") == 2


def test_voice_note_script_decides_hindi_vs_hinglish():
    from antar_engine import messaging as m
    assert m._STT_LANG["hin"] == "hi" and m._STT_LANG["hi"] == "hi"


# ── settings endpoints ──────────────────────────────────────────────────────

def test_patch_me_language_accepts_hi_and_hinglish_and_rejects_junk(monkeypatch):
    import main
    from fastapi.testclient import TestClient
    writes = []

    class T:
        def __init__(self, name):
            self.name = name

        def update(self, d):
            writes.append((self.name, d))
            return self

        def eq(self, *a):
            return self

        def execute(self):
            class R_:
                data = []
            return R_()

    class SB:
        def table(self, name):
            return T(name)

    monkeypatch.setattr(main, "supabase", SB())
    monkeypatch.setattr(main, "_st_identity", lambda a: ("u1", "u@x"))
    monkeypatch.setattr(main, "_st_get_profile", lambda uid: next(
        ({"language": d["language"]} for n, d in reversed(writes) if n == "profiles" and "language" in d), {}))
    monkeypatch.setattr(main, "_st_user_charts", lambda uid: [])
    client = TestClient(main.app)
    r = client.patch("/api/v1/me/language", json={"interface": "klingon"}, headers={"Authorization": "Bearer x"})
    assert r.status_code == 400 and r.json()["available"] == list(R.SUPPORTED_LANGUAGES)
    for sent, stored in [("hi", "hi"), ("hinglish", "hinglish"), ("hi-IN", "hi"), ("pt-BR", "pt")]:
        writes.clear()
        main._st_cache_bust("u1")
        r = client.patch("/api/v1/me/language", json={"interface": sent}, headers={"Authorization": "Bearer x"})
        assert r.status_code == 200, (sent, r.text)
        assert any(n == "profiles" and d["language"] == stored for n, d in writes), (sent, writes)
        assert r.json()["interface"] == stored and r.json()["available"] == list(R.SUPPORTED_LANGUAGES)
        assert r.json()["labels"]["hi"] == "हिन्दी"
