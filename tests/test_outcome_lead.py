"""Outcome leads: legal / immigration / debt answers lead with a LEAN, never a binary chip or a
'Likely —' / 'No —' lead (live persona test 2026-10-12), and the legal detector understands es/pt/hinglish."""
import re
from pathlib import Path

import main
from antar_engine import immigration as imm, debt as dbt

BINARY_LEAD = re.compile(r"^\s*\*?\s*(yes|likely|not yet|no|s[ií]|es probable|probable|a[uú]n no|sim|prov[aá]vel|n[aã]o)\b",
                         re.I)


def test_legal_detector_spanish_portuguese_hinglish():
    for q in ("¿Voy a ganar mi demanda?", "Me van a demandar, ¿qué hago?", "¿Voy a ganar el juicio?",
              "¿Cómo va mi caso judicial?", "Tengo audiencia judicial la semana que viene",
              "Vou ganhar o processo?", "Tenho uma ação judicial contra mim", "Quando sai o julgamento?",
              "Mera mukadma kab khatam hoga?", "Kya main case jeet jaunga?",
              "Will I win my lawsuit?"):                      # English still works
        assert main._is_legal_q(q), q


def test_legal_detector_does_not_steal_everyday_words():
    for q in ("La demanda de mi producto está subiendo", "Tengo buen juicio para los negocios",
              "Meu processo seletivo vai bem?", "How is my love life?", "¿Cómo está mi dinero?",
              "Quando minha energia melhora?"):
        assert not main._is_legal_q(q), q


def test_immigration_lead_is_a_lean_not_a_forecast():
    for lang in ("en", "es", "pt"):
        for level, phase in (("weak", "mixed"), ("strong", "slow"), ("strong", "releasing"), ("some", "mixed")):
            t = imm.immigration_lead_phrase(level, phase, lang)
            assert t and t.endswith(".") and not BINARY_LEAD.match(t), (lang, level, phase, t)
            assert not re.search(r"approved|aprobad|aprovad|denied|rechazad|negad", t, re.I)
    assert "delay, not a denial" in imm.immigration_lead_phrase("strong", "slow", "en")


def test_debt_lead_is_a_lean_not_a_date():
    for lang in ("en", "es", "pt"):
        for lean in ("recoverable", "contested", "heavy"):
            for severe in (False, True):
                t = dbt.debt_lead_phrase(lean, severe, lang)
                assert t and t.endswith(".") and not BINARY_LEAD.match(t), (lang, lean, severe, t)
                assert not re.search(r"20\d\d|within the year|debt-free|libre de deudas|livre das d", t, re.I)


def test_owner_phrasings_route_to_their_engine():
    """The owner's own wording (2026-10-12): each lands on its engine AND the right concern."""
    from antar_engine.astrological_rules import detect_concern
    assert main._is_legal_q("whats happening with my case?")
    q = "what should i expect for my case with my creditor?"
    assert main._is_legal_q(q) and main._is_debt_q(q)
    q = "what will happen on my immigration date?"
    assert main._is_immigration_q(q) and detect_concern(q) == "foreign"     # was 'love' ("date")
    q = "will i get my green card?"
    assert main._is_immigration_q(q) and detect_concern(q) == "foreign"     # was 'general'
    assert main._is_debt_q("will i be able to loan off?")                    # matched nothing
    assert main._is_debt_q("when will i pay off my debt?")
    assert main._is_debt_q("Will I be able to repay my loan?")
    # no theft
    assert detect_concern("When is my best window for love?") == "love"
    assert not main._is_debt_q("Should I raise funding for my startup?")
    assert not main._is_immigration_q("Should I go on a date this weekend?")


def test_wired_into_main():
    src = (Path(__file__).resolve().parent.parent / "main.py").read_text()
    for needle in ("_ask_immigration_lead = immigration_lead_phrase(", "_ask_debt_lead = debt_lead_phrase(",
                   "[ask][outcome-lead] verdict chip suppressed", "_ask_conv[\"verdict_phrase\"] = _ask_immigration_lead",
                   "_ask_conv[\"verdict_phrase\"] = _ask_debt_lead", "or any(w in ql for w in _LEGAL_I18N)"):
        assert needle in src, needle
