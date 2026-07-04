#!/usr/bin/env python3
"""
lang_propagation_qa.py — regression for the language persistence &
propagation patch (2026-07-04). Import-light: only touches modules with no
heavy deps; main.py assertions are source-level.

Run: cd ~/antarai && source venv311/bin/activate && python antar_research/lang_propagation_qa.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def src(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


print("== language_utils ==")
import language_utils as LU

check("fr in VALID_LANGUAGES", "fr" in LU.VALID_LANGUAGES)
fr_block = LU.build_language_instruction("fr")
check("FR block exists", bool(fr_block))
check("FR block is native-composition", "Compose natively in French" in fr_block)
check("ES block native-composition", "Compose natively in Spanish" in LU.build_language_instruction("es"))
check("PT block native-composition", "Compose natively in Portuguese" in LU.build_language_instruction("pt"))
check("EN block empty (no-op)", LU.build_language_instruction("en") == "")
check("resolve_language honors fr", LU.resolve_language({"language": "fr"}) == "fr")
check("resolve_language rejects de -> en", LU.resolve_language({"language": "de"}) == "en")

print("== pt_readiness gate ==")
from antar_engine.pt_readiness import gate_language, PT_READY, FR_READY

check("pt semantics unchanged: home stays pt", gate_language("home", "pt") == "pt")
check("pt semantics unchanged: welcome -> en", gate_language("welcome", "pt") == "en")
check("fr middleware surface serves fr", gate_language("home", "fr") == "fr")
check("fr source-generated surface -> en", gate_language("welcome", "fr") == "en")
check("fr life-arc -> en", gate_language("life-arc", "fr") == "en")
check("unknown lang de -> en", gate_language("home", "de") == "en")
check("es never gated", gate_language("welcome", "es") == "es")
check("FR_READY mirrors PT_READY keys",
      set(FR_READY.keys()) == {k for k, v in PT_READY.items() if v is False},
      f"FR={sorted(FR_READY)}")

print("== i18n needs_language_prompt ==")
from antar_engine.i18n import detect_language, UI_STRINGS

fr = detect_language("FR")
check("FR residence -> en + needs_prompt=True",
      fr.language == "en" and fr.needs_language_prompt is True)
de = detect_language("DE")
check("DE residence -> en + needs_prompt=True",
      de.language == "en" and de.needs_language_prompt is True)
us = detect_language("US")
check("US residence -> en, no prompt", us.language == "en" and not us.needs_language_prompt)
br = detect_language("BR")
check("BR residence -> pt, no prompt", br.language == "pt" and not br.needs_language_prompt)
mx = detect_language("MX")
check("MX residence -> es_MX", mx.language == "es" and mx.variant == "es_MX")
pref = detect_language("FR", user_preference="fr")
check("explicit preference wins, kills prompt",
      pref.language == "fr" and not pref.needs_language_prompt)
uspr = detect_language("US", birth_country="MX")
check("US+MX birth still prompts (unchanged)", uspr.needs_language_prompt is True)

print("== translation_middleware (source-level; module imports config) ==")
tm = src("antar_engine/translation_middleware.py")
check("SUPPORTED_LANGUAGES has fr", 'SUPPORTED_LANGUAGES = ("es", "pt", "fr")' in tm)
check("translator target map has fr", '"fr": "French (France)"' in tm)

print("== main.py (source-level) ==")
m = src("main.py")
check("chart/create honors explicit language_preference",
      'getattr(request, "language_preference", None)\n            in ("en", "es", "pt", "fr", "hi", "hinglish")' in m)
check("settings whitelist has fr",
      'SETTINGS_AVAILABLE_LANGS = ["en", "es", "pt", "fr", "hi", "hinglish"]' in m)
check("signature translates es/pt/fr",
      'endpoint_name="signature"' in m and '_sig_lang in ("es", "pt", "fr")' in m)
check("CompatibilityStartRequest has language",
      'name_b:             str = "Person B"\n    language:           Optional[str] = "en"' in m)
check("run_layer1_llm call passes language",
      'employee_role=_emp_role,\n        language=(request.language or "en"),' in m)
check("next_question localized", "Quer analisar o alinhamento" in m)

print("== compatibility_session_engine (source-level; module imports openai) ==")
c = src("antar_engine/compatibility_session_engine.py")
check("run_layer1_llm has language param",
      'employee_role: str = "",\n    language: str = "en",' in c)
check("layer1 system prompt carries language block",
      '{"role":"system","content":_lang_block + "You are a master Vedic astrologer' in c)

print("== ui_strings authoring gap (content task, not this patch) ==")
en_keys = sorted(UI_STRINGS.get("en", {}).keys())
fr_keys = set(UI_STRINGS.get("fr", {}).keys())
missing_fr = [k for k in en_keys if k not in fr_keys]
print(f"  EN keys: {len(en_keys)} | FR keys present: {len(fr_keys)} | "
      f"FR MISSING: {len(missing_fr)}")
print("  -- FR authoring list (hand to translators) --")
for k in missing_fr:
    print("   ", k)

print(f"\n== RESULT: {PASS} passed, {FAIL} failed ==")
sys.exit(1 if FAIL else 0)
